"""Relatórios da conferência: XLSX (todas as folhas), CSV por aba e TXT para copiar.

O XLSX é escrito em streaming (`write_only`) enquanto os achados chegam, então a memória não
cresce com o tamanho do resultado. A folha "Conferem" existe porque o banco guarda só o que
diverge: quem precisa provar o que conferiu baixa o XLSX (mesmo desenho do "Confere C100D100",
da Qive, com relatório de convergências e de divergências).

Texto que começa com `=`, `+`, `-`, `@`, tabulação ou retorno de carro é neutralizado antes de
virar célula ou campo CSV: o conteúdo vem de arquivo de terceiros e uma planilha aberta no
Excel executaria a fórmula.
"""

from __future__ import annotations

import contextlib
import csv
from collections.abc import Iterable, Mapping
from typing import Any, TextIO

from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.cell import WriteOnlyCell  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore[import-untyped]

from .findings import DIVERGENT, IGNORED, INFO, Finding, MatchedRow
from .money import plain
from .rules import SPED_SPED_FIELDS, SPED_XML_FIELDS, RuleLine
from .tools import ToolDef

XLSX_MAX_ROWS = 1_000_000
_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")
_STATUS_LABELS = {DIVERGENT: "Divergente", IGNORED: "Ignorada por regra", INFO: "Informativo"}
_OPERATION_LABELS = {"E": "Entrada", "S": "Saída", "": ""}
_DOC_LABELS = {"nfe": "NF-e", "cte": "CT-e", "c100": "C100", "d100": "D100"}
_HEADER_FILL = PatternFill("solid", fgColor="16352F")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_MONEY_FORMAT = "#,##0.00"
_FINDING_HEADERS = (
    "Chave",
    "Número",
    "Tipo",
    "Operação",
    "Campo",
    "{left}",
    "{right}",
    "Diferença",
    "CFOP",
    "Situação",
    "Observação",
)
_MATCHED_HEADERS = ("Chave", "Número", "Tipo", "Operação", "CFOP", "Campo", "{left}", "{right}")


def safe_text(value: object) -> str:
    """Neutraliza fórmula: prefixa apóstrofo no texto que o Excel interpretaria."""

    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_DANGEROUS) else text


def _money(cents: int | None) -> float | None:
    return None if cents is None else cents / 100


def finding_row(finding: Finding) -> list[Any]:
    """Linha de achado com o valor de cada lado em número (ou texto, quando for UF/situação)."""

    left: Any = _money(finding.left_cents) if finding.left_cents is not None else finding.left_text
    right: Any = (
        _money(finding.right_cents) if finding.right_cents is not None else finding.right_text
    )
    delta = _money(finding.delta_cents)
    return [
        finding.doc_key,
        finding.number,
        _DOC_LABELS.get(finding.doc_type, finding.doc_type),
        _OPERATION_LABELS.get(finding.operation, finding.operation),
        finding.field_label,
        left,
        right,
        delta,
        finding.cfop,
        _STATUS_LABELS.get(finding.status, finding.status),
        finding.message,
    ]


def csv_row(finding: Finding) -> list[str]:
    """Mesma linha em texto para CSV: números no formato de máquina, sem fórmula."""

    left = plain(finding.left_cents) if finding.left_cents is not None else finding.left_text
    right = plain(finding.right_cents) if finding.right_cents is not None else finding.right_text
    return [
        safe_text(value)
        for value in (
            finding.doc_key,
            finding.number,
            _DOC_LABELS.get(finding.doc_type, finding.doc_type),
            _OPERATION_LABELS.get(finding.operation, finding.operation),
            finding.field_label,
            left,
            right,
            plain(finding.delta_cents),
            finding.cfop,
            _STATUS_LABELS.get(finding.status, finding.status),
            finding.message,
        )
    ]


def csv_header(tool: ToolDef) -> list[str]:
    return [item.format(left=tool.left_label, right=tool.right_label) for item in _FINDING_HEADERS]


def write_csv(stream: TextIO, tool: ToolDef, findings: Iterable[Finding]) -> None:
    """CSV com `;` e UTF-8 com BOM (o Excel brasileiro abre sem assistente)."""

    writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
    writer.writerow(csv_header(tool))
    for finding in findings:
        writer.writerow(csv_row(finding))


def render_txt(tool: ToolDef, findings: Iterable[Finding], *, limit: int = 5000) -> tuple[str, int]:
    """Texto para copiar num chamado: um bloco por achado, no estilo do relatório antigo."""

    blocks: list[str] = []
    total = 0
    for finding in findings:
        total += 1
        if total > limit:
            continue
        lines = [
            f"{_DOC_LABELS.get(finding.doc_type, finding.doc_type)} - {finding.doc_key}"
            f" - Número: {finding.number}",
            f"  {finding.field_label or 'Documento'}: {finding.message}",
        ]
        if finding.cfop:
            lines.append(f"  CFOP: {finding.cfop}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks), total


class XlsxReport:
    """Escreve as folhas conforme os achados chegam; `finish` fecha e salva."""

    def __init__(self, tool: ToolDef, title: str) -> None:
        self._tool = tool
        self._workbook = Workbook(write_only=True)
        self._summary = self._workbook.create_sheet("Resumo")
        self._sheets: dict[str, Any] = {}
        self._rows: dict[str, int] = {}
        self.truncated: dict[str, int] = {}
        self._title = title
        self._done = False
        for tab in tool.tabs:
            self._open(tab.label, _FINDING_HEADERS)
        self._open("Conferem", _MATCHED_HEADERS)

    def _header(self, sheet: Any, headers: Iterable[str]) -> None:
        cells = []
        for text in headers:
            cell = WriteOnlyCell(
                sheet, value=text.format(left=self._tool.left_label, right=self._tool.right_label)
            )
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(vertical="center")
            cells.append(cell)
        sheet.append(cells)

    def _open(self, name: str, headers: Iterable[str]) -> None:
        sheet = self._workbook.create_sheet(name[:31])
        sheet.freeze_panes = "A2"
        for column, width in zip(
            "ABCDEFGHIJK", (46, 10, 8, 10, 28, 16, 16, 14, 14, 18, 60), strict=False
        ):
            sheet.column_dimensions[column].width = width
        self._header(sheet, headers)
        self._sheets[name] = sheet
        self._rows[name] = 1

    def _sheet_for(self, finding: Finding) -> str:
        if finding.status == IGNORED:
            for tab in self._tool.tabs:
                if IGNORED in tab.statuses:
                    return tab.label
        for tab in self._tool.tabs:
            if IGNORED in tab.statuses and tab.statuses == (IGNORED,):
                continue
            if finding.kind in tab.kinds:
                return tab.label
        return self._tool.tabs[0].label

    def _append(self, name: str, row: list[Any]) -> None:
        if self._rows[name] >= XLSX_MAX_ROWS:
            self.truncated[name] = self.truncated.get(name, 0) + 1
            return
        self._rows[name] += 1
        cells = []
        sheet = self._sheets[name]
        for value in row:
            if isinstance(value, float):
                cell = WriteOnlyCell(sheet, value=value)
                cell.number_format = _MONEY_FORMAT
                cells.append(cell)
            elif isinstance(value, str):
                cells.append(safe_text(value))
            else:
                cells.append(value)
        sheet.append(cells)

    def finding(self, finding: Finding) -> None:
        self._append(self._sheet_for(finding), finding_row(finding))

    def matched(self, row: MatchedRow) -> None:
        if not row.values:
            self._append(
                "Conferem",
                [row.doc_key, row.number, _DOC_LABELS.get(row.doc_type, row.doc_type),
                 _OPERATION_LABELS.get(row.operation, row.operation), row.cfop, "", None, None],
            )  # fmt: skip
            return
        for code, (left, right) in row.values.items():
            self._append(
                "Conferem",
                [
                    row.doc_key,
                    row.number,
                    _DOC_LABELS.get(row.doc_type, row.doc_type),
                    _OPERATION_LABELS.get(row.operation, row.operation),
                    row.cfop,
                    field_label(code),
                    _money(left),
                    _money(right),
                ],
            )

    def finish(
        self,
        path_or_file: Any,
        *,
        facts: Mapping[str, Any],
        rules: Iterable[RuleLine],
        files: Iterable[tuple[str, str]],
        counts: Mapping[str, int],
    ) -> None:
        sheet = self._summary
        sheet.column_dimensions["A"].width = 34
        sheet.column_dimensions["B"].width = 70
        title = WriteOnlyCell(sheet, value=safe_text(self._title))
        title.font = Font(bold=True, size=14)
        sheet.append([title])
        sheet.append([])
        for label, value in facts.items():
            sheet.append([label, safe_text(value)])
        sheet.append([])
        sheet.append(["Regras", ""])
        for line in rules:
            sheet.append(
                [line.label, safe_text(line.value + (f" ({line.reason})" if line.reason else ""))]
            )
        sheet.append([])
        sheet.append(["Arquivos", ""])
        for name, info in files:
            sheet.append([safe_text(name), safe_text(info)])
        sheet.append([])
        sheet.append(["Contagens", ""])
        for name, total in sorted(counts.items()):
            sheet.append([name, total])
        for name, lost in self.truncated.items():
            sheet.append([f"Linhas além do limite da folha {name}", lost])
        self._workbook.save(path_or_file)
        self._workbook.close()
        self._done = True

    def abort(self) -> None:
        """Descarta o relatório sem salvar (conferência que falhou ou foi cancelada).

        Sem fechar as folhas, o openpyxl deixa geradores suspensos que tentam escrever em arquivos
        já fechados quando o coletor de lixo os recolhe.
        """

        if self._done:
            return
        self._done = True
        for sheet in [*self._sheets.values(), self._summary]:
            with contextlib.suppress(Exception):
                sheet.close()
        with contextlib.suppress(Exception):
            self._workbook.close()


def field_label(code: str) -> str:
    """Rótulo do campo conferido (`vnf` -> Valor do documento)."""

    if code in SPED_XML_FIELDS:
        return SPED_XML_FIELDS[code]
    if code in SPED_SPED_FIELDS:
        return SPED_SPED_FIELDS[code][0]
    return code
