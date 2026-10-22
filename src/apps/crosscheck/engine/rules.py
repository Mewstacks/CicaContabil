"""Regras de conferência do Contraprova (D-301), gravadas em cada conferência.

O legado escondia as regras no código: `CFOP_IGNORAR` copiado em cinco lugares, tolerância
fixa, crédito do Simples Nacional só em alguns arquivos. Aqui elas são um objeto pequeno,
validado, com os padrões de D-301, que viaja com a conferência (`snapshot`) e aparece no
relatório. Mudar uma regra é escolher outro valor na tela, nunca editar código.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

#: Entradas sem direito a crédito: o imposto não vai no SPED (nota (1) do C100), então a
#: diferença de ICMS/IPI contra o XML é esperada. É o conjunto que o legado usava para
#: esconder qualquer divergência; aqui só rebaixa ICMS/IPI e o achado continua listado.
DEFAULT_NO_CREDIT_CFOPS = frozenset(
    {"1406", "1407", "1551", "1556", "2406", "2407", "2551", "2556"}
)
DEFAULT_ICMS51_CFOPS = frozenset({"1551", "1556"})
OPTIONAL_ICMS51_CFOPS = ("2551", "2556")

OPERATIONS = {"E": "Entradas", "S": "Saídas", "A": "Entradas e saídas"}

#: Campos de SPED x XML: código -> rótulo. `vnf` é sempre o valor do documento (C100 contra
#: vNF; D100 contra vTPrest).
SPED_XML_FIELDS = {
    "vnf": "Valor do documento",
    "vicms": "ICMS",
    "vipi": "IPI",
    "vbc": "Base do ICMS",
    "vbcst": "Base do ICMS ST",
    "vst": "ICMS ST",
    "vprod": "Mercadorias",
    "vfrete": "Frete",
    "vseg": "Seguro",
    "vdesc": "Desconto",
    "voutro": "Outras despesas",
    "vpis": "PIS",
    "vcofins": "COFINS",
}
DEFAULT_SPED_XML_FIELDS = ("vnf", "vicms", "vipi")
ICMS_ONLY_FIELDS = ("vnf", "vicms")
#: Campos cuja diferença some quando a entrada não gera crédito.
CREDIT_RELATED = frozenset({"vicms", "vipi", "vbc", "vbcst", "vst"})

#: Campos de SPED x SPED: código -> (rótulo, tipo). `money` compara com tolerância; `text`, exato.
SPED_SPED_FIELDS: dict[str, tuple[str, str]] = {
    "vl_doc": ("Valor do documento", "money"),
    "vl_icms": ("ICMS", "money"),
    "vl_ipi": ("IPI", "money"),
    "vl_serv": ("Serviço", "money"),
    "vl_bc_icms": ("Base do ICMS", "money"),
    "vl_bc_icms_st": ("Base do ICMS ST", "money"),
    "vl_icms_st": ("ICMS ST", "money"),
    "vl_merc": ("Mercadorias", "money"),
    "vl_desc": ("Desconto", "money"),
    "vl_frt": ("Frete", "money"),
    "vl_seg": ("Seguro", "money"),
    "vl_out_da": ("Outras despesas", "money"),
    "vl_pis": ("PIS", "money"),
    "vl_cofins": ("COFINS", "money"),
    "cod_sit": ("Situação", "text"),
    "num_doc": ("Número", "text"),
    "ser": ("Série", "text"),
    "chv_ref": ("Chave referenciada", "text"),
}
DEFAULT_SPED_SPED_FIELDS = ("vl_doc", "vl_icms", "vl_ipi", "vl_serv", "cod_sit", "num_doc")

_CFOP = re.compile(r"\d{4}")
MAX_TOLERANCE_CENTS = 1000


@dataclass(frozen=True)
class RuleSet:
    tolerance_cents: int = 1
    operation: str = "E"
    fields: tuple[str, ...] = DEFAULT_SPED_XML_FIELDS
    no_credit_cfops: frozenset[str] = DEFAULT_NO_CREDIT_CFOPS
    icms51_cfops: frozenset[str] = DEFAULT_ICMS51_CFOPS
    include_analytic: bool = True
    version: int = 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "tolerance_cents": self.tolerance_cents,
            "operation": self.operation,
            "fields": list(self.fields),
            "no_credit_cfops": sorted(self.no_credit_cfops),
            "icms51_cfops": sorted(self.icms51_cfops),
            "include_analytic": self.include_analytic,
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> RuleSet:
        """Reconstrói as regras gravadas (para repetir uma conferência)."""

        defaults = cls()
        return cls(
            tolerance_cents=int(data.get("tolerance_cents", defaults.tolerance_cents)),
            operation=str(data.get("operation", defaults.operation)),
            fields=tuple(data.get("fields", defaults.fields)),
            no_credit_cfops=frozenset(data.get("no_credit_cfops", defaults.no_credit_cfops)),
            icms51_cfops=frozenset(data.get("icms51_cfops", defaults.icms51_cfops)),
            include_analytic=bool(data.get("include_analytic", defaults.include_analytic)),
            version=int(data.get("version", defaults.version)),
        )

    def operation_filter(self) -> tuple[str, str]:
        """Valores de IND_OPER aceitos no SPED: ('0','0') entradas, ('1','1') saídas, ambos."""

        return {"E": ("0", "0"), "S": ("1", "1")}.get(self.operation, ("0", "1"))

    def direction_filter(self) -> tuple[str, str]:
        """Direções do XML aceitas, pelo mesmo critério."""

        return {"E": ("E", "E"), "S": ("S", "S")}.get(self.operation, ("E", "S"))


def parse_cfop_list(text: str) -> tuple[frozenset[str], list[str]]:
    """`1551, 1556` / `1551;1556` / linhas -> (conjunto, erros)."""

    values: set[str] = set()
    errors: list[str] = []
    for token in re.split(r"[\s,;]+", text.strip()):
        if not token:
            continue
        if _CFOP.fullmatch(token):
            values.add(token)
        else:
            errors.append(f"CFOP inválido: {token[:12]}")
    return frozenset(values), errors


def build_rules(
    data: Mapping[str, Any],
    *,
    tool: str = "sped_xml",
    allowed_fields: Iterable[str] | None = None,
) -> tuple[RuleSet, list[str]]:
    """Valida as opções vindas da tela. Devolve as regras e os erros em português."""

    errors: list[str] = []
    defaults = RuleSet(
        operation="A" if tool == "sped_sped" else "E",
        fields=DEFAULT_SPED_SPED_FIELDS if tool == "sped_sped" else DEFAULT_SPED_XML_FIELDS,
    )

    try:
        tolerance = int(str(data.get("tolerance_cents", defaults.tolerance_cents)).strip())
    except ValueError:
        tolerance = defaults.tolerance_cents
        errors.append("Tolerância inválida: informe os centavos como número inteiro.")
    if not 0 <= tolerance <= MAX_TOLERANCE_CENTS:
        errors.append(f"Tolerância fora do limite: use de 0 a {MAX_TOLERANCE_CENTS} centavos.")
        tolerance = defaults.tolerance_cents

    operation = str(data.get("operation", defaults.operation)).strip().upper() or defaults.operation
    if operation not in OPERATIONS:
        errors.append("Operação inválida: escolha entradas, saídas ou ambas.")
        operation = defaults.operation

    catalog = set(SPED_SPED_FIELDS if tool == "sped_sped" else SPED_XML_FIELDS)
    if allowed_fields is not None:
        catalog &= set(allowed_fields)
    raw_fields = data.get("fields")
    if raw_fields is None:
        fields = defaults.fields
    else:
        selected = [str(item) for item in raw_fields]
        unknown = [item for item in selected if item not in catalog]
        if unknown:
            errors.append(f"Campo desconhecido: {unknown[0][:20]}")
        fields = tuple(dict.fromkeys(item for item in selected if item in catalog))
        if not fields:
            errors.append("Escolha ao menos um campo para conferir.")
            fields = defaults.fields

    no_credit = defaults.no_credit_cfops
    if "no_credit_cfops" in data:
        value = data["no_credit_cfops"]
        parsed, problems = parse_cfop_list(value if isinstance(value, str) else " ".join(value))
        errors.extend(problems)
        if not problems:
            no_credit = parsed

    icms51 = defaults.icms51_cfops
    if "icms51_cfops" in data:
        value = data["icms51_cfops"]
        parsed, problems = parse_cfop_list(value if isinstance(value, str) else " ".join(value))
        errors.extend(problems)
        if not problems and parsed:
            icms51 = parsed
        elif not problems:
            errors.append("Informe ao menos um CFOP para o ICMS 51.")

    include_analytic = bool(data.get("include_analytic", defaults.include_analytic))
    rules = RuleSet(
        tolerance_cents=tolerance,
        operation=operation,
        fields=fields,
        no_credit_cfops=no_credit,
        icms51_cfops=icms51,
        include_analytic=include_analytic,
    )
    return rules, errors


@dataclass(frozen=True)
class RuleLine:
    label: str
    value: str
    reason: str = field(default="")


def describe(rules: RuleSet, tool: str) -> list[RuleLine]:
    """As regras em linhas legíveis, para o relatório e para a tela do resultado."""

    lines = [
        RuleLine("Tolerância", f"{rules.tolerance_cents} centavo(s)", "inclusiva"),
        RuleLine("Operação", OPERATIONS.get(rules.operation, rules.operation)),
    ]
    if tool == "sped_sped":
        labels = [SPED_SPED_FIELDS[item][0] for item in rules.fields if item in SPED_SPED_FIELDS]
        lines.append(RuleLine("Campos", ", ".join(labels)))
        lines.append(
            RuleLine("Analítico", "conferido" if rules.include_analytic else "não conferido")
        )
    elif tool == "sped_xml":
        labels = [SPED_XML_FIELDS[item] for item in rules.fields if item in SPED_XML_FIELDS]
        lines.append(RuleLine("Campos", ", ".join(labels)))
        lines.append(RuleLine("CFOP sem crédito", ", ".join(sorted(rules.no_credit_cfops))))
    elif tool == "icms51":
        lines.append(RuleLine("CFOP do ICMS 51", ", ".join(sorted(rules.icms51_cfops))))
    return lines
