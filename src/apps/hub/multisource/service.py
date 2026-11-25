"""Execução da simulação multifontes a partir dos arquivos do mês (D-409 a D-413).

Compartilhado pelo comando `simular_multifontes` e pela tela de fechamento: recebe os bytes de cada
fonte, lê, simula e monta os relatórios. Nada é gravado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.ledger_comparison import LedgerComparison
from apps.hub.multisource.matching import SimulationResult
from apps.hub.multisource.position_workbook import render_position_xlsx


@dataclass
class SimulationSources:
    statement: bytes
    collection: bytes | None = None
    receivables: bytes | None = None
    payables: bytes | None = None
    cashbook: bytes | None = None
    cashbook_sheet: str = "SICREDI"
    cash_sheets: Sequence[str] = ()
    reference_receivables: bytes | None = None
    reference_payables: bytes | None = None
    investment: bytes | None = None
    ledger_pdf: bytes | None = None
    ledger_csv: bytes | None = None
    documents: Sequence[tuple[str, bytes]] = ()  # (nome do arquivo, conteúdo)
    tax_id: str = ""
    loans: Sequence[bytes] = ()  # D-418: consulta de parcelas do empréstimo
    chart: Any = None  # D-420: plano de contas da empresa (contas sugeridas, a confirmar)
    cards: Sequence[bytes] = ()  # D-418: fatura do cartão


@dataclass
class SimulationOutput:
    period_start: date
    result: SimulationResult
    comparison: LedgerComparison | None
    reports: dict[str, str | bytes] = field(default_factory=dict)
    suggestions: Any = None  # D-420

    @property
    def period_label(self) -> str:
        return f"{self.period_start:%m/%Y}"


POSITION_LABELS = {
    "receivables": "posição a receber do mês anterior",
    "payables": "posição a pagar do mês anterior",
    "reference_receivables": "posição a receber do mês",
    "reference_payables": "posição a pagar do mês",
}


def run_simulation(sources: SimulationSources) -> SimulationOutput:
    """Lê as fontes e simula. Erros de leiaute viram `MultisourceError` legível para o usuário."""
    from apps.hub.bank_evidence import read_sicredi_pdf
    from apps.hub.multisource.client_cashbook import read_client_cashbook_xlsx
    from apps.hub.multisource.francesinha import read_francesinha_pdf
    from apps.hub.multisource.investment import read_investment_pdf
    from apps.hub.multisource.ledger_comparison import (
        compare_with_ledger,
        movements_from_ledger_csv,
        movements_from_pdf,
    )
    from apps.hub.multisource.matching import BankLine, simulate
    from apps.hub.multisource.report import (
        render_differences_csv,
        render_documents_csv,
        render_ledger_csv,
        render_ledger_summary,
        render_lines_csv,
        render_position_csv,
        render_summary,
    )
    from apps.hub.multisource.scanned_documents import read_scanned_pdf
    from apps.hub.multisource.title_position import PAYABLE, RECEIVABLE, read_title_position_xls
    from apps.hub.reconciliation_service import ReconciliationError

    try:
        statement = read_sicredi_pdf(sources.statement)
    except ReconciliationError as exc:
        raise MultisourceError(str(exc)) from exc
    if statement is None:
        raise MultisourceError("Extrato fora do leiaute Sicredi suportado (PDF de texto).")
    bank_lines = [
        BankLine(i, line.occurred_on, line.amount_cents, line.description, line.document)
        for i, line in enumerate(statement.lines, 1)
    ]
    collection = read_francesinha_pdf(sources.collection) if sources.collection else None
    positions = {}
    for name, kind in (
        ("receivables", RECEIVABLE),
        ("payables", PAYABLE),
        ("reference_receivables", RECEIVABLE),
        ("reference_payables", PAYABLE),
    ):
        content = getattr(sources, name)
        if not content:
            continue
        position = read_title_position_xls(content)
        if position.kind != kind:
            raise MultisourceError(
                f"O arquivo enviado como {POSITION_LABELS[name]} é de outro tipo."
            )
        if sources.tax_id and position.company_cnpj != sources.tax_id:
            raise MultisourceError(
                f"O CNPJ da {POSITION_LABELS[name]} é diferente do CNPJ da empresa escolhida."
            )
        positions[name] = position
    cashbook = None
    cash_accounts = []
    if sources.cashbook:
        workbook = read_client_cashbook_xlsx(sources.cashbook)
        cashbook = workbook.sheet(sources.cashbook_sheet)
        cash_accounts = [workbook.sheet(name) for name in sources.cash_sheets]
    elif sources.cash_sheets:
        raise MultisourceError("Abas sem extrato exigem o caixa do cliente.")
    if sources.ledger_pdf and sources.ledger_csv:
        raise MultisourceError("Envie o Razão em PDF ou em CSV, não os dois.")
    investment = read_investment_pdf(sources.investment) if sources.investment else None
    from apps.hub.multisource.credit import read_card_pdf, read_loan_pdf

    loans = [read_loan_pdf(content) for content in sources.loans]
    cards = [read_card_pdf(content) for content in sources.cards]
    documents = []
    for name, content in sources.documents:
        documents.extend(read_scanned_pdf(content, source=name, own_tax_id=sources.tax_id))
    ledger_movements = None
    if sources.ledger_pdf:
        from apps.hub.ledger_evidence import LedgerEvidenceError, read_dominio_ledger_pdf

        try:
            ledger_movements = movements_from_pdf(read_dominio_ledger_pdf(sources.ledger_pdf))
        except LedgerEvidenceError as exc:
            raise MultisourceError(str(exc)) from exc
    if sources.ledger_csv:
        ledger_movements = movements_from_ledger_csv(sources.ledger_csv)

    result = simulate(
        bank_lines,
        collection=collection,
        receivables=positions.get("receivables"),
        payables=positions.get("payables"),
        cashbook=cashbook,
        reference_receivables=positions.get("reference_receivables"),
        reference_payables=positions.get("reference_payables"),
        cash_accounts=cash_accounts,
        investment=investment,
        documents=documents,
        own_tax_id=sources.tax_id,
        loans=loans,
        cards=cards,
    )
    output = SimulationOutput(statement.period_start, result, None)
    if sources.chart is not None:
        from apps.hub.multisource.suggested_accounts import suggest_accounts

        output.suggestions = suggest_accounts(result, sources.chart)
    output.reports = {
        "resumo.md": render_summary(result, title=f"Simulação multifontes — {output.period_label}"),
        "movimentos.csv": render_lines_csv(result, output.suggestions),
        "posicao.csv": render_position_csv(result),
        "diferencas-posicao.csv": render_differences_csv(result),
    }
    if result.installments:
        output.reports["posicao-titulos.xlsx"] = render_position_xlsx(
            result, period=statement.period_start
        )  # D-417
    if documents:
        output.reports["documentos.csv"] = render_documents_csv(result)
    if output.suggestions is not None:
        from apps.hub.multisource.suggested_accounts import summary_lines

        output.reports["resumo.md"] += (
            "\n".join(summary_lines(output.suggestions, chart_size=len(sources.chart))) + "\n"
        )
    if ledger_movements is not None:
        output.comparison = compare_with_ledger(result, ledger_movements)
        output.reports["resumo.md"] += render_ledger_summary(output.comparison)
        output.reports["comparacao-razao.csv"] = render_ledger_csv(output.comparison)
    return output
