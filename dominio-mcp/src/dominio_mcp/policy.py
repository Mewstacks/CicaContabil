"""Politica de dados: classes, bloqueio, acesso por operacao e mascaras (D-319, T2.3).

O usuario Externo do Dominio le quase tudo, entao a decisao do que sai e **do MCP**, nao do banco.

Classes: `segredo` (nunca sai), `documento` (so CNPJ valido passa inteiro), `pessoal` (bloqueada
ate o dono liberar a categoria, sempre mascarada), `texto_livre` (mascarado por padrao de valor),
`normal` e `nao_classificada` (bloqueada ate `build-pack --aceitar`).

As regras ficam em `data/overlay/policy.yaml`; o hash do texto entra na versao do pack.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from importlib import resources
from typing import Any

import yaml

from dominio_mcp.catalog import Catalog, Column, Table
from dominio_mcp.config import PII_CATEGORIES
from dominio_mcp.values import Cell

PESSOAL_CATEGORIES = PII_CATEGORIES - {"documento"}
FILTER_OPS_ALL = frozenset(
    {"=", "!=", "<", "<=", ">", ">=", "in", "between", "prefix", "contains", "is_null", "not_null"}
)
AGGREGATES_ALL = frozenset({"count", "sum", "avg", "min", "max", "count_distinct"})
_DEFAULT_TEXT_TYPES = ("char", "varchar", "nvarchar", "long varchar", "long nvarchar", "text")
_DEFAULT_DOCUMENT_TYPES = ("char", "varchar", "numeric", "decimal", "bigint")
_DEFAULT_BINARY_TYPES = ("binary", "long binary", "varbinary", "image")
_TOP_KEYS = frozenset(
    {
        "version",
        "denied_tables",
        "denied_column_name_patterns",
        "denied_column_comment_patterns",
        "binary_types",
        "text_types",
        "document_types",
        "column_rules",
        "table_rules",
        "column_overrides",
    }
)


class PolicyError(Exception):
    pass


UNKNOWN_WIDTH = 10**9


class PolicyClass(StrEnum):
    SEGREDO = "segredo"
    DOCUMENTO = "documento"
    PESSOAL = "pessoal"
    TEXTO_LIVRE = "texto_livre"
    NORMAL = "normal"
    NAO_CLASSIFICADA = "nao_classificada"


@dataclass(frozen=True, slots=True)
class ColumnPolicy:
    klass: PolicyClass
    category: str | None
    rule: str
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Access:
    select: bool
    mask: str
    filter_ops: frozenset[str]
    group: bool
    order: bool
    aggregates: frozenset[str]
    suppress_small_groups: bool
    reason: str | None


def fold(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


# --- regras ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ColumnRule:
    id: str
    klass: PolicyClass
    category: str | None
    name_rx: tuple[re.Pattern[str], ...]
    comment_rx: tuple[re.Pattern[str], ...]
    types: frozenset[str]
    min_width: int


@dataclass(frozen=True, slots=True)
class _TableRule:
    id: str
    klass: PolicyClass
    category: str | None
    scope: str
    when_column: str | None
    table_rx: tuple[re.Pattern[str], ...]
    blocked_reason: str | None
    first: bool


def _rx(pattern: object, where: str) -> re.Pattern[str]:
    if not isinstance(pattern, str):
        raise PolicyError(f"{where}: padrao deve ser texto")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise PolicyError(f"{where}: expressao regular invalida ({exc})") from None


def _strings(value: object, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise PolicyError(f"{where}: deve ser uma lista de textos")
    return tuple(value)


def _class(value: object, where: str, allowed: frozenset[PolicyClass]) -> PolicyClass:
    try:
        klass = PolicyClass(str(value))
    except ValueError:
        raise PolicyError(f"{where}: classe desconhecida") from None
    if klass not in allowed:
        raise PolicyError(f"{where}: classe {klass.value} nao e permitida aqui")
    return klass


def _category(klass: PolicyClass, value: object, where: str) -> str | None:
    if klass is PolicyClass.PESSOAL:
        if value not in PESSOAL_CATEGORIES:
            raise PolicyError(f"{where}: categoria pessoal invalida")
        return str(value)
    if value is not None:
        raise PolicyError(f"{where}: categoria so vale para a classe pessoal")
    return None


@dataclass(frozen=True, slots=True)
class Policy:
    sha: str
    denied_tables: frozenset[str]
    _name_rx: tuple[re.Pattern[str], ...]
    _comment_rx: tuple[re.Pattern[str], ...]
    _binary: frozenset[str]
    _text: frozenset[str]
    _document: frozenset[str]
    _column_rules: tuple[_ColumnRule, ...]
    _table_rules: tuple[_TableRule, ...]
    _overrides: dict[tuple[str, str], ColumnPolicy] = field(default_factory=dict)

    @classmethod
    def from_text(cls, text: str) -> Policy:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            raise PolicyError("YAML invalido no arquivo de politica") from None
        if not isinstance(data, dict):
            raise PolicyError("o arquivo de politica deve ser um mapa")
        unknown = sorted(set(data) - _TOP_KEYS)
        if unknown:
            raise PolicyError(f"chave desconhecida na politica: {unknown[0]!r}")
        if data.get("version") != 1:
            raise PolicyError("versao da politica nao suportada (esperado 1)")

        text_types = frozenset(
            _strings(data.get("text_types"), "text_types") or _DEFAULT_TEXT_TYPES
        )
        document_types = frozenset(
            _strings(data.get("document_types"), "document_types") or _DEFAULT_DOCUMENT_TYPES
        )
        type_sets = {"text": text_types, "document": document_types}

        column_rules = tuple(
            _parse_column_rule(i, raw, type_sets)
            for i, raw in enumerate(_list(data.get("column_rules"), "column_rules"))
        )
        table_rules = tuple(
            _parse_table_rule(i, raw)
            for i, raw in enumerate(_list(data.get("table_rules"), "table_rules"))
        )
        overrides: dict[tuple[str, str], ColumnPolicy] = {}
        for i, raw in enumerate(_list(data.get("column_overrides"), "column_overrides")):
            where = f"column_overrides[{i}]"
            if not isinstance(raw, dict) or not {"table", "column", "class"} <= set(raw):
                raise PolicyError(f"{where}: precisa de table, column e class")
            klass = _class(
                raw["class"], where, frozenset(PolicyClass) - {PolicyClass.NAO_CLASSIFICADA}
            )
            category = _category(klass, raw.get("category"), where)
            key = (str(raw["table"]).lower(), str(raw["column"]).lower())
            overrides[key] = ColumnPolicy(klass, category, "column_overrides")

        return cls(
            sha=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            denied_tables=frozenset(
                t.lower() for t in _strings(data.get("denied_tables"), "denied_tables")
            ),
            _name_rx=tuple(
                _rx(p, "denied_column_name_patterns")
                for p in _strings(
                    data.get("denied_column_name_patterns"), "denied_column_name_patterns"
                )
            ),
            _comment_rx=tuple(
                _rx(p, "denied_column_comment_patterns")
                for p in _strings(
                    data.get("denied_column_comment_patterns"), "denied_column_comment_patterns"
                )
            ),
            _binary=frozenset(
                _strings(data.get("binary_types"), "binary_types") or _DEFAULT_BINARY_TYPES
            ),
            _text=text_types,
            _document=document_types,
            _column_rules=column_rules,
            _table_rules=table_rules,
            _overrides=overrides,
        )

    # --- classificacao -------------------------------------------------------------------------

    def classify_catalog(
        self,
        catalog: Catalog,
        accepted: Callable[[str, str], bool],
        view_approved: Callable[[Table], bool] = lambda table: False,
    ) -> dict[tuple[str, str], ColumnPolicy]:
        fk_cols: dict[str, set[str]] = {}
        for fk in catalog.foreign_keys:
            fk_cols.setdefault(fk.child_table.lower(), set()).update(
                c.lower() for c in fk.child_columns
            )
        result: dict[tuple[str, str], ColumnPolicy] = {}
        for tkey, tbl in catalog.tables.items():
            per_column = self.classify_table(
                tbl, frozenset(fk_cols.get(tkey, ())), accepted, view_approved=view_approved(tbl)
            )
            for ckey, cp in per_column.items():
                result[(tkey, ckey)] = cp
        return result

    def classify_table(
        self,
        table: Table,
        fk_columns: frozenset[str],
        accepted: Callable[[str, str], bool],
        *,
        view_approved: bool = False,
    ) -> dict[str, ColumnPolicy]:
        tkey = table.key
        if table.kind != "BASE" and not view_approved:
            # a view pode encapsular origem bloqueada: so entra com aprovacao por nome e hash
            blocked = ColumnPolicy(
                PolicyClass.NAO_CLASSIFICADA, None, "view_nao_aprovada", "view_nao_aprovada"
            )
            return {c.name.lower(): blocked for c in table.columns}
        fkeys = {c.lower() for c in fk_columns}
        pkeys = {c.lower() for c in table.primary_key}
        names = {c.name.lower() for c in table.columns}
        return {
            c.name.lower(): self._classify(table, c, tkey, pkeys | fkeys, names, accepted)
            for c in table.columns
        }

    def _classify(
        self,
        table: Table,
        column: Column,
        tkey: str,
        keys: set[str],
        names: set[str],
        accepted: Callable[[str, str], bool],
    ) -> ColumnPolicy:
        ckey = column.name.lower()
        name_f, comment_f = fold(column.name), fold(column.comment)
        ctype = column.type.lower()
        if tkey in self.denied_tables:
            return ColumnPolicy(PolicyClass.SEGREDO, None, "denied_tables", "tabela_de_credencial")
        if any(rx.search(name_f) for rx in self._name_rx):
            return ColumnPolicy(
                PolicyClass.SEGREDO, None, "denied_column_name_patterns", "coluna_de_credencial"
            )
        if any(rx.search(comment_f) for rx in self._comment_rx):
            return ColumnPolicy(
                PolicyClass.SEGREDO,
                None,
                "denied_column_comment_patterns",
                "comentario_de_credencial",
            )
        if ctype in self._binary:
            return ColumnPolicy(PolicyClass.SEGREDO, None, "binary_types", "coluna_binaria")
        override = self._overrides.get((tkey, ckey))
        if override is not None:
            return override
        tname_f = fold(table.name)
        for trule in self._table_rules:
            if trule.first and self._table_rule_hits(trule, tname_f, names, ckey, ctype, keys):
                return ColumnPolicy(trule.klass, trule.category, trule.id, trule.blocked_reason)
        # Largura desconhecida (ou zero) conta como enorme: a regra de largura minima nao pode
        # deixar texto longo ou documento sair como coluna normal por falta de metadado.
        width = column.width if column.width is not None and column.width > 0 else UNKNOWN_WIDTH
        # Texto livre e a classe mais fraca: regra de tabela (por empregado) vence dela, senao a
        # observacao de uma tabela de folha sairia so com mascara de CPF, e-mail e telefone.
        deferred: list[_ColumnRule] = []
        for rule in self._column_rules:
            if rule.klass is PolicyClass.TEXTO_LIVRE:
                deferred.append(rule)
            elif _column_rule_matches(rule, name_f, comment_f, ctype, width):
                return ColumnPolicy(rule.klass, rule.category, rule.id)
        for trule in self._table_rules:
            if not trule.first and self._table_rule_hits(trule, tname_f, names, ckey, ctype, keys):
                return ColumnPolicy(trule.klass, trule.category, trule.id, trule.blocked_reason)
        for rule in deferred:
            if _column_rule_matches(rule, name_f, comment_f, ctype, width):
                return ColumnPolicy(rule.klass, rule.category, rule.id)
        if accepted(tkey, ckey):
            return ColumnPolicy(PolicyClass.NORMAL, None, "aceita")
        return ColumnPolicy(PolicyClass.NAO_CLASSIFICADA, None, "sem_regra")

    def _table_rule_hits(
        self,
        rule: _TableRule,
        tname_f: str,
        names: set[str],
        ckey: str,
        ctype: str,
        keys: set[str],
    ) -> bool:
        if not _table_rule_applies(rule, tname_f, names):
            return False
        if rule.scope == "non_key" and ckey in keys:
            return False
        return not (rule.scope == "text" and ctype not in self._text)

    # --- acesso por operacao -----------------------------------------------------------------

    def access(self, cp: ColumnPolicy, allow_pii: frozenset[str]) -> Access:
        none: frozenset[str] = frozenset()
        if cp.blocked_reason is not None or cp.klass in (
            PolicyClass.SEGREDO,
            PolicyClass.NAO_CLASSIFICADA,
        ):
            reason = cp.blocked_reason or cp.klass.value
            return Access(False, "none", none, False, False, none, False, reason)
        if cp.klass is PolicyClass.NORMAL:
            return Access(True, "none", FILTER_OPS_ALL, True, True, AGGREGATES_ALL, False, None)
        if cp.klass is PolicyClass.DOCUMENTO:
            mask = "none" if "documento" in allow_pii else "documento"
            return Access(True, mask, frozenset({"=", "in"}), False, False, none, False, None)
        if cp.klass is PolicyClass.TEXTO_LIVRE:
            # Sem filtro: `contains` e `prefix` em texto livre confirmam, por contagem, o que a
            # mascara esconderia (um CPF pontuado, janelas curtas de digitos). So se le.
            return Access(True, "texto", none, False, False, none, False, None)
        category = cp.category or ""
        if category not in allow_pii:
            return Access(
                False, "none", none, False, False, none, False, f"pessoal_nao_liberado:{category}"
            )
        return Access(
            True, "pessoal", none, False, False, frozenset({"count", "sum", "avg"}), True, None
        )


def _list(value: object, where: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PolicyError(f"{where}: deve ser uma lista")
    return value


def _parse_column_rule(
    index: int, raw: object, type_sets: dict[str, frozenset[str]]
) -> _ColumnRule:
    where = f"column_rules[{index}]"
    if not isinstance(raw, dict) or "id" not in raw or "class" not in raw:
        raise PolicyError(f"{where}: precisa de id e class")
    allowed = frozenset({PolicyClass.DOCUMENTO, PolicyClass.PESSOAL, PolicyClass.TEXTO_LIVRE})
    klass = _class(raw["class"], where, allowed)
    types_value = raw.get("types")
    types: frozenset[str]
    if types_value is None:
        types = frozenset()
    elif isinstance(types_value, str) and types_value in type_sets:
        types = type_sets[types_value]
    else:
        raise PolicyError(f"{where}: types deve ser 'text' ou 'document'")
    min_width = raw.get("min_width", 0)
    if isinstance(min_width, bool) or not isinstance(min_width, int):
        raise PolicyError(f"{where}: min_width deve ser inteiro")
    return _ColumnRule(
        id=str(raw["id"]),
        klass=klass,
        category=_category(klass, raw.get("category"), where),
        name_rx=tuple(_rx(p, where) for p in _strings(raw.get("name"), where)),
        comment_rx=tuple(_rx(p, where) for p in _strings(raw.get("comment"), where)),
        types=types,
        min_width=min_width,
    )


def _parse_table_rule(index: int, raw: object) -> _TableRule:
    where = f"table_rules[{index}]"
    if not isinstance(raw, dict) or "id" not in raw or "class" not in raw:
        raise PolicyError(f"{where}: precisa de id e class")
    klass = _class(
        raw["class"],
        where,
        frozenset({PolicyClass.PESSOAL, PolicyClass.TEXTO_LIVRE, PolicyClass.SEGREDO}),
    )
    scope = str(raw.get("scope", "all"))
    if scope not in ("non_key", "all", "text"):
        raise PolicyError(f"{where}: scope invalido")
    when_column = raw.get("when_column")
    patterns = tuple(_rx(p, where) for p in _strings(raw.get("table_patterns"), where))
    if when_column is None and not patterns:
        raise PolicyError(f"{where}: precisa de when_column ou table_patterns")
    precedence = str(raw.get("precedence", "last"))
    if precedence not in ("first", "last"):
        raise PolicyError(f"{where}: precedence deve ser first ou last")
    return _TableRule(
        id=str(raw["id"]),
        klass=klass,
        category=_category(klass, raw.get("category"), where),
        scope=scope,
        when_column=None if when_column is None else str(when_column).lower(),
        table_rx=patterns,
        blocked_reason=None if raw.get("blocked_reason") is None else str(raw["blocked_reason"]),
        first=precedence == "first",
    )


def _column_rule_matches(
    rule: _ColumnRule, name_f: str, comment_f: str, ctype: str, width: int
) -> bool:
    if rule.types and ctype not in rule.types:
        return False
    if width < rule.min_width:
        return False
    if not rule.name_rx and not rule.comment_rx:
        return True
    return any(rx.search(name_f) for rx in rule.name_rx) or any(
        rx.search(comment_f) for rx in rule.comment_rx
    )


def _table_rule_applies(rule: _TableRule, tname_f: str, column_names: set[str]) -> bool:
    if rule.when_column is not None and rule.when_column not in column_names:
        return False
    return not rule.table_rx or any(rx.search(tname_f) for rx in rule.table_rx)


def load_policy() -> Policy:
    text = (
        resources.files("dominio_mcp")
        .joinpath("data/overlay/policy.yaml")
        .read_text(encoding="utf-8")
    )
    return Policy.from_text(text)


# --- valores: CNPJ, CPF e mascaras ---------------------------------------------------------------

_CNPJ_W1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_W2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_SHAPE = re.compile(r"[0-9A-Z]{12}[0-9]{2}")
_DOC_SHAPE = re.compile(r"[\d.\-/\s]+")
_CPF_RX = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RX = re.compile(
    r"(?<!\d)(?:\+?55\s?)?(?:\(\d{2}\)\s?|\d{2}\s)?9?\d{4}-\d{4}(?!\d)"
    r"|(?<!\d)\(\d{2}\)\s?9?\d{4}[\s-]?\d{4}(?!\d)"
    r"|(?<!\d)\+?55\d{10,11}(?!\d)"  # DDI e DDD sem pontuacao
    r"|(?<!\d)\d{10}(?!\d)"  # DDD e fixo sem pontuacao (11 digitos viram [cpf] antes)
)


def _cnpj_digit(base: str, weights: tuple[int, ...]) -> int:
    total = sum((ord(c) - 48) * w for c, w in zip(base, weights, strict=True))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cpf(value: str) -> bool:
    """CPF com os dois digitos verificadores conferidos (pontuacao e ignorada)."""
    digits = re.sub(r"[.\-\s]", "", value)
    if not re.fullmatch(r"\d{11}", digits) or len(set(digits)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(d) * w for d, w in zip(digits[:size], range(size + 1, 1, -1), strict=True))
        if digits[size] != str((total * 10) % 11 % 10):
            return False
    return True


def is_valid_cnpj(value: str) -> bool:
    """CNPJ numerico ou alfanumerico (letra vale ASCII - 48), com os dois digitos conferidos."""
    text = re.sub(r"[.\-/\s]", "", value).upper()
    if not _CNPJ_SHAPE.fullmatch(text) or len(set(text)) == 1:
        return False
    if text.startswith("000") and is_valid_cpf(text[3:]):
        # CPF preenchido com zeros ate 14 posicoes: cerca de 1,4% deles fecha como CNPJ por acaso
        # (medido em 200 mil CPFs validos). Na duvida e CPF e sai mascarado; o CNPJ real que cai
        # aqui (base 000xxxxx com final que tambem fecha como CPF) sai mascarado, sem dano.
        return False
    first = _cnpj_digit(text[:12], _CNPJ_W1)
    second = _cnpj_digit(text[:12] + str(first), _CNPJ_W2)
    return text[12:] == f"{first}{second}"


def _mask_cpf_digits(digits: str) -> str:
    return f"{digits[:3]}.***.***-{digits[-2:]}"


def _numeric_document(value: Cell) -> str | None:
    """Documento guardado como numero perdeu zeros a esquerda: reconstroi so se for valido."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    digits = str(int(value))
    if digits.startswith("-"):
        return None
    padded = digits.zfill(14)
    if len(padded) == 14 and is_valid_cnpj(padded):
        return padded
    return digits


def mask_document(value: Cell, *, allow: bool) -> Cell:
    """So CNPJ valido sai inteiro; CPF sai mascarado; o resto vira `***` (salvo `allow`)."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if is_valid_cnpj(text):
            return text
        if allow:
            return value
        if _DOC_SHAPE.fullmatch(text):
            digits = re.sub(r"\D", "", text)
            if len(digits) == 11:
                return _mask_cpf_digits(digits)
        return "***"
    numeric = _numeric_document(value)
    if numeric is None:
        return "***" if not allow else value
    if len(numeric) == 14 and is_valid_cnpj(numeric):
        return numeric
    if allow:
        return numeric
    return _mask_cpf_digits(numeric) if len(numeric) == 11 else "***"


def mask_pii(value: Cell, category: str) -> Cell:
    """Dado pessoal liberado pelo dono sai sempre mascarado; so CPF mantem um pouco de forma."""
    if value is None:
        return None
    if category == "cpf" and isinstance(value, str) and _DOC_SHAPE.fullmatch(value.strip()):
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11:
            return _mask_cpf_digits(digits)
    return "***"


def mask_text(value: str | None) -> str | None:
    """Mascara CPF, e-mail e telefone dentro de texto livre. Heuristica, nao garantia."""
    if value is None:
        return None
    masked = _CPF_RX.sub("[cpf]", value)
    masked = _EMAIL_RX.sub("[email]", masked)
    return _PHONE_RX.sub("[telefone]", masked)
