"""Leitura em streaming da EFD ICMS/IPI (SPED Fiscal).

Só os registros que o Contraprova compara são decodificados e interpretados: 0000 (cabeçalho),
C100/C190 (documentos e analítico de NF/NF-e) e D100/D190 (CT-e). Os demais são apenas
contados, para provar a integridade do arquivo com 9900 e 9999. Um documento por vez fica na
memória: o consumidor recebe cada C100/D100 já com os seus C190/D190 e pode descartá-lo.

Os números dos campos seguem o Guia Prático da EFD ICMS/IPI, onde REG é o campo 01. O legado
lia por posição e rotulava errado (o campo 10 do C100 é DT_DOC, não CFOP; os campos 3, 6, 7 e
11 do C190 são CFOP, BC, ICMS e IPI); aqui cada campo tem nome e número do leiaute.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO, Literal

from .money import MoneyError, sped_cents, sped_rate

MAX_LINE_BYTES = 1024 * 1024
MAX_ISSUES = 200

_DATE_8 = re.compile(r"\d{8}")
_BOM = b"\xef\xbb\xbf"

# Todo registro de bloco C/D que não é filho de C100/D100 (nível 2 ou abertura/fechamento de
# bloco) fecha o documento corrente. Registro C/D desconhecido é tratado como filho: o
# analítico só se liga ao documento do seu próprio tipo, então o risco é um aviso, não um
# vínculo errado.
_DOCUMENT_BREAKERS = frozenset(
    {
        b"C001",
        b"C300",
        b"C350",
        b"C400",
        b"C495",
        b"C500",
        b"C600",
        b"C700",
        b"C800",
        b"C860",
        b"C990",
        b"D001",
        b"D300",
        b"D350",
        b"D400",
        b"D500",
        b"D600",
        b"D695",
        b"D700",
        b"D990",
    }
)

# (atributo, número do campo no Guia Prático)
_C100_TEXT: tuple[tuple[str, int], ...] = (
    ("ind_oper", 2),
    ("ind_emit", 3),
    ("cod_part", 4),
    ("cod_mod", 5),
    ("cod_sit", 6),
    ("ser", 7),
    ("num_doc", 8),
    ("key", 9),
)
_C100_DATES: tuple[tuple[str, int], ...] = (("dt_doc", 10), ("dt_es", 11))
_C100_MONEY: tuple[tuple[str, int], ...] = (
    ("vl_doc", 12),
    ("vl_desc", 14),
    ("vl_abat_nt", 15),
    ("vl_merc", 16),
    ("vl_frt", 18),
    ("vl_seg", 19),
    ("vl_out_da", 20),
    ("vl_bc_icms", 21),
    ("vl_icms", 22),
    ("vl_bc_icms_st", 23),
    ("vl_icms_st", 24),
    ("vl_ipi", 25),
    ("vl_pis", 26),
    ("vl_cofins", 27),
    ("vl_pis_st", 28),
    ("vl_cofins_st", 29),
)
_C100_MIN_FIELDS = 29

_D100_TEXT: tuple[tuple[str, int], ...] = (
    ("ind_oper", 2),
    ("ind_emit", 3),
    ("cod_part", 4),
    ("cod_mod", 5),
    ("cod_sit", 6),
    ("ser", 7),
    ("sub", 8),
    ("num_doc", 9),
    ("key", 10),
    ("tp_cte", 13),
    ("chv_ref", 14),
)
_D100_DATES: tuple[tuple[str, int], ...] = (("dt_doc", 11), ("dt_es", 12))
_D100_MONEY: tuple[tuple[str, int], ...] = (
    ("vl_doc", 15),
    ("vl_desc", 16),
    ("vl_serv", 18),
    ("vl_bc_icms", 19),
    ("vl_icms", 20),
    ("vl_nt", 21),
)
_D100_MIN_FIELDS = 25

# Analítico: C190 tem 12 campos e D190 tem 9.
_C190_MONEY: tuple[tuple[str, int], ...] = (
    ("vl_opr", 5),
    ("vl_bc_icms", 6),
    ("vl_icms", 7),
    ("vl_bc_icms_st", 8),
    ("vl_icms_st", 9),
    ("vl_red_bc", 10),
    ("vl_ipi", 11),
)
_C190_MIN_FIELDS = 12
_D190_MONEY: tuple[tuple[str, int], ...] = (
    ("vl_opr", 5),
    ("vl_bc_icms", 6),
    ("vl_icms", 7),
    ("vl_red_bc", 8),
)
_D190_MIN_FIELDS = 9

#: Todos os valores monetários de documento que o motor guarda, na ordem do leiaute.
DOCUMENT_MONEY_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys([name for name, _ in _C100_MONEY] + [name for name, _ in _D100_MONEY])
)


class EfdFormatError(ValueError):
    """O arquivo não é uma EFD ICMS/IPI legível; `code` identifica o motivo."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class EfdIssue:
    severity: Literal["error", "warning"]
    code: str
    message: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class EfdHeader:
    cod_ver: str
    cod_fin: str
    dt_ini: date
    dt_fin: date
    nome: str
    cnpj: str
    cpf: str
    uf: str
    ie: str
    cod_mun: str
    ind_perfil: str
    ind_ativ: str

    @property
    def competence(self) -> str:
        """Mês de DT_INI no formato AAAA-MM (a EFD é mensal)."""

        return f"{self.dt_ini.year:04d}-{self.dt_ini.month:02d}"


@dataclass(frozen=True, slots=True)
class Analytic:
    line: int
    reg: str
    cst_icms: str
    cfop: str
    aliq: int | None
    vl_opr: int | None
    vl_bc_icms: int | None
    vl_icms: int | None
    vl_bc_icms_st: int | None
    vl_icms_st: int | None
    vl_red_bc: int | None
    vl_ipi: int | None
    cod_obs: str


@dataclass(slots=True)
class EfdDocument:
    reg: str
    line: int
    ind_oper: str = ""
    ind_emit: str = ""
    cod_part: str = ""
    cod_mod: str = ""
    cod_sit: str = ""
    ser: str = ""
    sub: str = ""
    num_doc: str = ""
    key: str = ""
    chv_ref: str = ""
    tp_cte: str = ""
    dt_doc: date | None = None
    #: DT_E_S no C100 e DT_A_P no D100.
    dt_es: date | None = None
    money: dict[str, int | None] = field(default_factory=dict)
    analytics: list[Analytic] = field(default_factory=list)

    @property
    def matching_key(self) -> str:
        """Chave de ligação: a chave de acesso ou, sem ela, o que identifica o documento."""

        if self.key:
            return self.key
        parts = (self.reg, self.ind_oper, self.ind_emit, self.cod_mod, self.ser)
        return ":".join((*parts, self.sub, self.num_doc, self.cod_part))


@dataclass(frozen=True, slots=True)
class EfdSummary:
    header: EfdHeader | None
    physical_lines: int
    encoding: str
    line_ending: str
    counts: dict[str, int]
    issues: tuple[EfdIssue, ...]
    issue_overflow: int

    @property
    def errors(self) -> tuple[EfdIssue, ...]:
        return tuple(item for item in self.issues if item.severity == "error")

    @property
    def warnings(self) -> tuple[EfdIssue, ...]:
        return tuple(item for item in self.issues if item.severity == "warning")


def _field(fields: Sequence[str], number: int) -> str:
    index = number - 1
    return fields[index].strip() if index < len(fields) else ""


def _decode(line: bytes) -> tuple[str, bool]:
    """UTF-8 estrito; só se falhar cai para Latin-1 (nunca `replace`)."""

    try:
        return line.decode("utf-8"), False
    except UnicodeDecodeError:
        return line.decode("latin-1"), True


def _parse_date(text: str) -> date | None:
    if not _DATE_8.fullmatch(text):
        return None
    try:
        return date(int(text[4:]), int(text[2:4]), int(text[:2]))
    except ValueError:
        return None


def parse_header_line(line: bytes) -> tuple[EfdHeader, bool]:
    """Interpreta o registro 0000 de uma EFD ICMS/IPI.

    Devolve o cabeçalho e se foi preciso cair para Latin-1. Recusa EFD-Contribuições, que
    também começa por 0000 mas tem outro leiaute.
    """

    if line.startswith(_BOM):
        line = line[len(_BOM) :]
    line = line.rstrip(b"\r\n")
    if not line.startswith(b"|0000|") or not line.endswith(b"|"):
        raise EfdFormatError(
            "sem_0000", "A primeira linha não é o registro 0000: o arquivo não é uma EFD."
        )
    text, latin = _decode(line)
    fields = text.split("|")[1:-1]
    if len(fields) < 15 or not _DATE_8.fullmatch(fields[3]) or not _DATE_8.fullmatch(fields[4]):
        raise EfdFormatError(
            "nao_icms_ipi",
            "O arquivo não é uma EFD ICMS/IPI: o registro 0000 não tem o leiaute do SPED Fiscal "
            "(EFD-Contribuições não é aceita aqui).",
        )
    dt_ini = _parse_date(fields[3])
    dt_fin = _parse_date(fields[4])
    if dt_ini is None or dt_fin is None or dt_fin < dt_ini:
        raise EfdFormatError("periodo_invalido", "O período do registro 0000 é inválido.")
    header = EfdHeader(
        cod_ver=_field(fields, 2),
        cod_fin=_field(fields, 3),
        dt_ini=dt_ini,
        dt_fin=dt_fin,
        nome=_field(fields, 6),
        cnpj=_field(fields, 7).upper(),
        cpf=_field(fields, 8),
        uf=_field(fields, 9).upper(),
        ie=_field(fields, 10),
        cod_mun=_field(fields, 11),
        ind_perfil=_field(fields, 14),
        ind_ativ=_field(fields, 15),
    )
    return header, latin


def peek_header(stream: BinaryIO) -> EfdHeader:
    """Só a primeira linha do arquivo: serve ao processo web sem ler o resto."""

    stream.seek(0)
    first = stream.readline(MAX_LINE_BYTES + 1)
    stream.seek(0)
    header, _ = parse_header_line(first)
    return header


_TRAILER = re.compile(rb"\|9999\|(\d+)\|")


def peek_trailer(stream: BinaryIO) -> int | None:
    """Total de linhas declarado no 9999, lendo só o fim do arquivo."""

    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(max(0, size - 8192))
    tail = stream.read(8192)
    stream.seek(0)
    found = _TRAILER.findall(tail)
    return int(found[-1]) if found else None


class EfdReader:
    """Percorre o arquivo uma vez; `documents()` entrega C100/D100 já com o analítico.

    Terminada a iteração, `summary()` traz cabeçalho, contagens, codificação e problemas.
    Um primeiro registro que não é uma 0000 de EFD ICMS/IPI levanta `EfdFormatError` na hora.
    Problemas `error` encontrados depois (arquivo truncado, totais que não batem) tornam o
    arquivo inutilizável para a conferência; `warning` não impede, mas é mostrado.
    """

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._header: EfdHeader | None = None
        self._issues: list[EfdIssue] = []
        self._overflow = 0
        self._counts: Counter[bytes] = Counter()
        self._physical_lines = 0
        self._latin = False
        self._crlf = 0
        self._lf = 0
        self._done = False

    # -- problemas -----------------------------------------------------------------------
    def _issue(
        self,
        severity: Literal["error", "warning"],
        code: str,
        message: str,
        line: int | None = None,
    ) -> None:
        if len(self._issues) >= MAX_ISSUES:
            self._overflow += 1
            return
        self._issues.append(EfdIssue(severity, code, message, line))

    def _warn(self, code: str, message: str, line: int | None = None) -> None:
        self._issue("warning", code, message, line)

    def _fields(self, line: bytes) -> list[str]:
        text, latin = _decode(line)
        self._latin = self._latin or latin
        return text.split("|")[1:-1]

    def _money(self, text: str, line: int, reg: str, number: int) -> int | None:
        try:
            return sped_cents(text)
        except MoneyError:
            self._warn(
                "valor_invalido",
                f"{reg} linha {line}: o campo {number:02d} não é um número válido.",
                line,
            )
            return None

    # -- registros -----------------------------------------------------------------------
    def _document(self, reg: str, fields: Sequence[str], line: int) -> EfdDocument:
        if reg == "C100":
            text_spec, date_spec, money_spec = _C100_TEXT, _C100_DATES, _C100_MONEY
            minimum = _C100_MIN_FIELDS
        else:
            text_spec, date_spec, money_spec = _D100_TEXT, _D100_DATES, _D100_MONEY
            minimum = _D100_MIN_FIELDS
        if len(fields) < minimum:
            self._warn(
                "campos_curtos",
                f"{reg} linha {line}: {len(fields)} campos; o leiaute tem {minimum}.",
                line,
            )
        doc = EfdDocument(reg=reg, line=line)
        for attribute, number in text_spec:
            setattr(doc, attribute, _field(fields, number))
        doc.key = doc.key.upper()
        for attribute, number in date_spec:
            raw = _field(fields, number)
            parsed = _parse_date(raw)
            if raw and parsed is None:
                self._warn(
                    "data_invalida",
                    f"{reg} linha {line}: o campo {number:02d} não é uma data válida.",
                    line,
                )
            setattr(doc, attribute, parsed)
        for attribute, number in money_spec:
            doc.money[attribute] = self._money(_field(fields, number), line, reg, number)
        return doc

    def _analytic(self, reg: str, fields: Sequence[str], line: int) -> Analytic:
        if reg == "C190":
            spec, minimum, obs_field = _C190_MONEY, _C190_MIN_FIELDS, 12
        else:
            spec, minimum, obs_field = _D190_MONEY, _D190_MIN_FIELDS, 9
        if len(fields) < minimum:
            self._warn(
                "campos_curtos",
                f"{reg} linha {line}: {len(fields)} campos; o leiaute tem {minimum}.",
                line,
            )
        values = {
            name: self._money(_field(fields, number), line, reg, number) for name, number in spec
        }
        try:
            aliq = sped_rate(_field(fields, 4))
        except MoneyError:
            aliq = None
            self._warn("valor_invalido", f"{reg} linha {line}: alíquota inválida.", line)
        return Analytic(
            line=line,
            reg=reg,
            cst_icms=_field(fields, 2),
            cfop=_field(fields, 3),
            aliq=aliq,
            vl_opr=values.get("vl_opr"),
            vl_bc_icms=values.get("vl_bc_icms"),
            vl_icms=values.get("vl_icms"),
            vl_bc_icms_st=values.get("vl_bc_icms_st"),
            vl_icms_st=values.get("vl_icms_st"),
            vl_red_bc=values.get("vl_red_bc"),
            vl_ipi=values.get("vl_ipi"),
            cod_obs=_field(fields, obs_field),
        )

    # -- leitura -------------------------------------------------------------------------
    def _physical(self) -> Iterator[tuple[int, bytes | None]]:
        """Linhas físicas; `None` no lugar de uma linha maior que o teto (já consumida)."""

        line_no = 0
        while True:
            raw = self._stream.readline(MAX_LINE_BYTES + 1)
            if not raw:
                return
            line_no += 1
            if len(raw) > MAX_LINE_BYTES and not raw.endswith(b"\n"):
                while True:
                    chunk = self._stream.readline(MAX_LINE_BYTES)
                    if not chunk or chunk.endswith(b"\n"):
                        break
                yield line_no, None
                continue
            yield line_no, raw

    def documents(self) -> Iterator[EfdDocument]:
        current: EfdDocument | None = None
        declared: dict[str, int] = {}
        declared_total: int | None = None
        trailer_line = 0

        for line_no, raw in self._physical():
            if trailer_line:
                if raw is None or raw.strip():
                    self._warn(
                        "conteudo_apos_9999",
                        f"Há conteúdo depois do registro 9999 (linha {line_no}).",
                        line_no,
                    )
                continue
            self._physical_lines = line_no
            if raw is None:
                self._warn(
                    "linha_longa",
                    f"A linha {line_no} passa de {MAX_LINE_BYTES} bytes e foi ignorada.",
                    line_no,
                )
                continue
            if line_no == 1 and raw.startswith(_BOM):
                raw = raw[len(_BOM) :]
                self._warn("bom", "O arquivo começa com BOM UTF-8.", 1)
            if b"\x00" in raw:
                self._warn("nul", f"A linha {line_no} tem byte nulo e foi ignorada.", line_no)
                continue
            if raw.endswith(b"\r\n"):
                self._crlf += 1
            elif raw.endswith(b"\n"):
                self._lf += 1
            line = raw.rstrip(b"\r\n")
            if line_no == 1:
                self._read_header(line)
            if not line:
                self._warn("linha_vazia", f"A linha {line_no} está vazia.", line_no)
                continue
            if line[:1] != b"|" or line[-1:] != b"|" or len(line) < 6 or line[5:6] != b"|":
                self._warn(
                    "delimitadores",
                    f"A linha {line_no} não está no formato |REGISTRO|…| do SPED.",
                    line_no,
                )
                continue
            reg = line[1:5]
            self._counts[reg] += 1

            if reg == b"0000":
                if line_no != 1:
                    self._issue(
                        "error",
                        "0000_repetido",
                        f"Registro 0000 repetido na linha {line_no}.",
                        line_no,
                    )
            elif reg in (b"C100", b"D100"):
                if current is not None:
                    yield current
                current = self._document(reg.decode("ascii"), self._fields(line), line_no)
            elif reg in (b"C190", b"D190"):
                name = reg.decode("ascii")
                wanted = "C100" if name == "C190" else "D100"
                if current is not None and current.reg == wanted:
                    current.analytics.append(self._analytic(name, self._fields(line), line_no))
                else:
                    self._warn(
                        "analitico_orfao",
                        f"{name} na linha {line_no} sem {wanted} antes dele.",
                        line_no,
                    )
            elif reg == b"9900":
                fields = self._fields(line)
                try:
                    declared[_field(fields, 2)] = int(_field(fields, 3))
                except ValueError:
                    self._issue(
                        "error",
                        "9900_invalido",
                        f"O 9900 da linha {line_no} não traz uma quantidade válida.",
                        line_no,
                    )
            elif reg == b"9999":
                trailer_line = line_no
                try:
                    declared_total = int(_field(self._fields(line), 2))
                except ValueError:
                    self._issue(
                        "error", "9999_invalido", "O 9999 não traz a quantidade de linhas.", line_no
                    )
            elif current is not None and (reg in _DOCUMENT_BREAKERS or reg[:1] not in (b"C", b"D")):
                yield current
                current = None

        if current is not None:
            yield current
        self._finish(declared, declared_total, trailer_line)

    def _read_header(self, line: bytes) -> None:
        header, latin = parse_header_line(line)
        self._header = header
        self._latin = self._latin or latin

    def _finish(
        self, declared: dict[str, int], declared_total: int | None, trailer_line: int
    ) -> None:
        if declared_total is None:
            if not any(item.code == "9999_invalido" for item in self._issues):
                self._issue(
                    "error",
                    "sem_9999",
                    "O arquivo não termina no registro 9999: está incompleto.",
                )
        elif declared_total != trailer_line:
            self._issue(
                "error",
                "total_9999",
                f"O 9999 declara {declared_total} linhas e o arquivo tem {trailer_line}: "
                "está incompleto ou foi alterado.",
                trailer_line,
            )
        actual = {key.decode("ascii", "replace"): total for key, total in self._counts.items()}
        for register, quantity in sorted(declared.items()):
            if actual.get(register, 0) != quantity:
                self._issue(
                    "error",
                    "contagem_9900",
                    f"O 9900 declara {quantity} registros {register} e o arquivo tem "
                    f"{actual.get(register, 0)}.",
                )
        if self._crlf and self._lf:
            self._warn("fim_de_linha_misto", "O arquivo mistura CRLF e LF.")
        self._done = True

    def summary(self) -> EfdSummary:
        if not self._done:
            raise RuntimeError("summary() só vale depois de percorrer documents() até o fim")
        return EfdSummary(
            header=self._header,
            physical_lines=self._physical_lines,
            encoding="latin-1" if self._latin else "utf-8",
            line_ending="CRLF" if self._crlf >= self._lf else "LF",
            counts={key.decode("ascii", "replace"): total for key, total in self._counts.items()},
            issues=tuple(self._issues),
            issue_overflow=self._overflow,
        )
