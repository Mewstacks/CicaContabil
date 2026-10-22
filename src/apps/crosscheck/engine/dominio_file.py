"""Exportação do Domínio (CSV ou XLSX) com chave, UF e, opcionalmente, direção.

É o caminho por arquivo da ferramenta UF x Domínio, que funciona sem o agente: o escritório
exporta do Domínio a relação de notas com a UF do cliente/fornecedor e a envia. Colunas
aceitas (cabeçalho, sem acento e sem diferença de maiúscula): chave (`chave`, `chave_nfe`,
`chave nfe`), UF (`uf`, `sigl_est`, `sigla`) e direção (`direcao`, `tipo`, `sentido`) com
valores S/E ou saída/entrada. Sem cabeçalho, vale a ordem chave, UF, direção.
"""

from __future__ import annotations

import csv
import io
import unicodedata
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import BinaryIO

from .keys import is_well_formed

MAX_ROWS = 200_000
MAX_ISSUES = 50

_KEY_NAMES = {"chave", "chave_nfe", "chavenfe", "chave_de_acesso", "chave_acesso"}
_UF_NAMES = {"uf", "sigl_est", "sigla", "sigla_uf", "estado"}
_DIR_NAMES = {"direcao", "tipo", "sentido", "operacao"}
_DIRECTIONS = {"s": "S", "saida": "S", "saída": "S", "e": "E", "entrada": "E"}
UFS = frozenset(
    [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
        "EX",
    ]
)


class DominioFileError(ValueError):
    """Arquivo do Domínio ilegível ou grande demais; a mensagem é segura para a tela."""


@dataclass(frozen=True, slots=True)
class DominioRow:
    key: str
    direcao: str
    uf: str


@dataclass(slots=True)
class DominioReport:
    rows_read: int = 0
    rows_valid: int = 0
    issues: list[str] = field(default_factory=list)
    issue_overflow: int = 0

    def issue(self, message: str) -> None:
        if len(self.issues) >= MAX_ISSUES:
            self.issue_overflow += 1
        else:
            self.issues.append(message)


def _normalize(name: object) -> str:
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    return "_".join(text.strip().lower().replace("-", " ").split())


def _rows_csv(stream: BinaryIO) -> Iterator[list[str]]:
    raw = stream.read(MAX_ROWS * 120 + 1)
    if len(raw) > MAX_ROWS * 120:
        raise DominioFileError("O arquivo CSV é grande demais.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    sample = text[:4096]
    delimiter = max(";,\t", key=sample.count) if any(c in sample for c in ";,\t") else ";"
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        yield [cell.strip() for cell in row]


def _rows_xlsx(stream: BinaryIO) -> Iterator[list[str]]:
    from openpyxl import load_workbook  # type: ignore[import-untyped]
    from openpyxl.utils.exceptions import InvalidFileException  # type: ignore[import-untyped]

    try:
        workbook = load_workbook(stream, read_only=True, data_only=True)
    except (
        InvalidFileException,
        zipfile.BadZipFile,
        OSError,
        EOFError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        raise DominioFileError("O arquivo não é uma planilha XLSX válida.") from exc
    try:
        sheet = workbook.worksheets[0]
        for row in sheet.iter_rows(values_only=True):
            yield ["" if cell is None else str(cell).strip() for cell in row]
    finally:
        workbook.close()


def _column(header: list[str], names: set[str]) -> int | None:
    for index, cell in enumerate(header):
        if _normalize(cell) in names:
            return index
    return None


def iter_dominio_rows(
    stream: BinaryIO, name: str, report: DominioReport | None = None
) -> Iterator[DominioRow]:
    """Linhas válidas do arquivo; as inválidas viram avisos no `report`, nunca zero."""

    report = report if report is not None else DominioReport()
    lower = name.lower()
    if lower.endswith(".xlsx"):
        rows = _rows_xlsx(stream)
    elif lower.endswith(".csv") or lower.endswith(".txt"):
        rows = _rows_csv(stream)
    else:
        raise DominioFileError("Envie o Domínio em CSV ou XLSX.")

    key_col, uf_col, dir_col = 0, 1, 2
    first = True
    for line_no, row in enumerate(rows, start=1):
        if not any(row):
            continue
        if first:
            first = False
            found_key = _column(row, _KEY_NAMES)
            found_uf = _column(row, _UF_NAMES)
            if found_key is not None and found_uf is not None:
                key_col, uf_col = found_key, found_uf
                found_dir = _column(row, _DIR_NAMES)
                dir_col = -1 if found_dir is None else found_dir
                continue
            dir_col = 2
        report.rows_read += 1
        if report.rows_read > MAX_ROWS:
            raise DominioFileError(f"O arquivo tem mais de {MAX_ROWS} linhas.")
        key = (row[key_col] if key_col < len(row) else "").upper().replace(" ", "")
        uf = (row[uf_col] if uf_col < len(row) else "").upper()
        direction_raw = (row[dir_col] if 0 <= dir_col < len(row) else "").strip().lower()
        if not is_well_formed(key):
            report.issue(f"Linha {line_no}: a chave não tem 44 posições.")
            continue
        if uf not in UFS:
            report.issue(f"Linha {line_no}: a UF {uf[:6]!r} não é válida.")
            continue
        if direction_raw and direction_raw not in _DIRECTIONS:
            report.issue(f"Linha {line_no}: a direção {direction_raw[:12]!r} não é S nem E.")
            continue
        report.rows_valid += 1
        yield DominioRow(key=key, direcao=_DIRECTIONS.get(direction_raw, ""), uf=uf)
