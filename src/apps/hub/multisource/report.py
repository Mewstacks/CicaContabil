"""Relatórios da simulação multifontes (D-409): resumo em Markdown e detalhes em CSV."""

from __future__ import annotations

import csv
import io
from collections import Counter

from apps.hub.multisource.common import money
from apps.hub.multisource.ledger_comparison import (
    MISSING,
    ONLY_LEDGER,
    OTHER_SPLIT,
    SAME_SPLIT,
    WINDOW_DAYS,
    LedgerComparison,
)
from apps.hub.multisource.matching import (
    AUTOMATIC,
    FLAGGED,
    IDENTIFIED,
    STATUS_LABELS,
    SimulationResult,
)
from apps.hub.multisource.title_position import PAYABLE, RECEIVABLE

KIND_LABELS = {RECEIVABLE: "a receber", PAYABLE: "a pagar"}


def _percent(value: float) -> str:
    return f"{value * 100:.1f}".replace(".", ",") + "%"


def render_summary(result: SimulationResult, *, title: str) -> str:
    total = len(result.lines)
    grand_total = sum(abs(r.bank.amount_cents) for r in result.lines)
    lines = [
        f"# {title}",
        "",
        "> Simulação (D-409): nenhum lançamento, regra, conciliação ou exportação foi criado.",
        "",
        "## Movimentos do extrato",
        "",
        "| Situação | Movimentos | Valor |",
        "|---|---:|---:|",
    ]
    for status in (AUTOMATIC, IDENTIFIED, FLAGGED):
        chosen = [r for r in result.lines if r.status == status]
        value = sum(abs(r.bank.amount_cents) for r in chosen)
        lines.append(f"| {STATUS_LABELS[status]} | {len(chosen)} | {money(value)} |")
    lines += [
        f"| **Total** | **{total}** | **{money(grand_total)}** |",
        "",
        "- Automático (títulos, aplicação ou transferência): "
        f"**{_percent(result.automatic_share)}** dos movimentos.",
        "- Identificados (títulos ou natureza pelo caixa): "
        f"**{_percent(result.identified_share)}**.",
        "",
        "## Títulos baixados na simulação",
        "",
    ]
    parts = [p for r in result.lines for p in r.parts]
    for kind, label in (
        ("receivable", "Recebimentos (valor nominal)"),
        ("payable", "Pagamentos"),
        ("interest", "Juros/multa recebidos — a classificar (Q-53)"),
        ("document", "Notas citadas no caixa e fora da posição de abertura (sem baixa)"),
        ("nature", "Natureza informada pelo caixa, sem título (conta pelo DE-PARA)"),
        ("transfer", "Transferências entre contas da empresa — contas a definir (Q-57)"),
        ("loan", "Parcelas de empréstimo — juros e principal a separar (Q-55)"),
        ("card", "Faturas do cartão — total ou por despesa a definir (Q-56)"),
    ):
        same = [p for p in parts if p.kind == kind]
        lines.append(f"- {label}: {len(same)} · {money(sum(p.amount_cents for p in same))}")
    lines[lines.index("## Títulos baixados na simulação")] = "## Partes identificadas"
    lines += _investment_section(result)
    lines += _transfers_section(result)
    lines += _credit_section(result)
    lines += _documents_section(result)
    lines += ["", "## Sinalizações", ""]
    flagged = [r for r in result.lines if r.status == FLAGGED]
    if not flagged:
        lines.append("Nenhuma.")
    reasons = Counter(_reason_group(reason) for r in flagged for reason in r.reasons)
    for reason, count in reasons.most_common():
        lines.append(f"- {reason}: {count}")
    lines += [
        "",
        f"- Linhas do caixa do cliente sem movimento no extrato: {len(result.unmatched_cashbook)}",
        f"- Títulos da francesinha sem cobrança correspondente no extrato: "
        f"{len(result.unmatched_collection)}",
        "",
        "## Posição de títulos",
        "",
        "| Tipo | Parcelas abertas na abertura | Saldo na abertura | Baixado na simulação "
        "| Saldo final |",
        "|---|---:|---:|---:|---:|",
    ]
    for kind in (RECEIVABLE, PAYABLE):
        keys = [k for k in result.installments if k[0] == kind]
        if not keys:
            continue
        opening = sum(result.installments[k].balance_cents for k in keys)
        closing = sum(result.closing[k] for k in keys)
        open_count = sum(1 for k in keys if result.installments[k].balance_cents > 0)
        lines.append(
            f"| {KIND_LABELS[kind]} | {open_count} | {money(opening)} | {money(opening - closing)} "
            f"| {money(closing)} |"
        )
    if result.differences:
        lines += [
            "",
            "### Comparação com a posição de referência do Domínio",
            "",
            "A referência pode já incluir baixas posteriores ao mês simulado; "
            "cada diferença precisa ser explicada, não é erro por si.",
            "",
            "| Tipo | Resultado | Parcelas | Valor na referência |",
            "|---|---|---:|---:|",
        ]
        grouped: Counter[tuple[str, str]] = Counter()
        values: Counter[tuple[str, str]] = Counter()
        for diff in result.differences:
            grouped[(diff.kind, diff.outcome)] += 1
            values[(diff.kind, diff.outcome)] += diff.reference_cents
        for (kind, outcome), count in sorted(grouped.items()):
            lines.append(
                f"| {KIND_LABELS[kind]} | {outcome} | {count} | {money(values[(kind, outcome)])} |"
            )
    if result.warnings:
        lines += ["", "## Avisos das fontes", ""] + [f"- {w}" for w in result.warnings]
    return "\n".join(lines) + "\n"


def _reason_group(reason: str) -> str:
    if "natureza diferente do habitual" in reason:
        return "natureza diferente da habitual para o mesmo CPF/CNPJ (R-12)"
    text = reason.split(": ", 1)[-1] if ": " in reason else reason
    if "há título do mesmo nome e valor" in text:
        return "documento citado difere do título aberto de mesmo nome e valor (confirmar)"
    if "documentos citados não estão em aberto" in text:
        return "parte dos documentos citados no caixa não está em aberto"
    for prefix in (
        "valor ",
        "nenhum título",
        "soma dos",
        "documento ",
        "cobrança",
        "movimento sem linha",
        "mais de uma",
        "sem caixa",
    ):
        if text.startswith(prefix):
            return {
                "valor ": "valor não confere com os títulos em aberto",
                "nenhum título": (
                    "título não está na posição de abertura (pode ser nota do próprio mês)"
                ),
                "soma dos": "soma dos documentos citados difere do valor",
                "documento ": "documento citado não está em aberto",
                "cobrança": "cobrança não fecha com a francesinha",
                "movimento sem linha": "movimento sem linha no caixa do cliente",
                "mais de uma": "mais de uma combinação possível",
                "sem caixa": "sem caixa do cliente e sem título de valor exato",
            }[prefix]
    return text


def render_lines_csv(result: SimulationResult) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(
        ["conta", "data", "valor", "historico", "situacao", "linhas_caixa", "partes", "motivos"]
    )
    for line in result.lines:
        writer.writerow(
            [
                line.bank.account,
                line.bank.occurred_on.strftime("%d/%m/%Y"),
                money(line.bank.amount_cents),
                line.bank.description,
                STATUS_LABELS[line.status],
                ",".join(str(r) for r in line.cashbook_rows),
                " | ".join(f"{p.label} = {money(p.amount_cents)}" for p in line.parts),
                " | ".join(line.reasons),
            ]
        )
    return out.getvalue()


def render_position_csv(result: SimulationResult) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["tipo", "titulo", "vencimento", "saldo_abertura", "baixado", "saldo_final"])
    for key, item in sorted(
        result.installments.items(), key=lambda kv: (kv[0][0], kv[1].party_name, kv[1].due_on)
    ):
        closing = result.closing[key]
        writer.writerow(
            [
                KIND_LABELS[key[0]],
                item.label,
                item.due_on.strftime("%d/%m/%Y"),
                money(item.balance_cents),
                money(item.balance_cents - closing),
                money(closing),
            ]
        )
    return out.getvalue()


def render_differences_csv(result: SimulationResult) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["tipo", "resultado", "titulo", "saldo_simulado", "saldo_referencia"])
    for diff in result.differences:
        writer.writerow(
            [
                KIND_LABELS[diff.kind],
                diff.outcome,
                diff.label,
                money(diff.simulated_cents),
                money(diff.reference_cents),
            ]
        )
    return out.getvalue()


def render_ledger_summary(comparison: LedgerComparison) -> str:
    """Seção do resumo com a comparação contra o Razão lançado pela contadora (D-410)."""
    total = len(comparison.lines)
    lines = [
        "",
        "## Comparação com o Razão lançado (conta bancária)",
        "",
        "| Resultado | Movimentos do extrato |",
        "|---|---:|",
    ]
    for outcome in (SAME_SPLIT, OTHER_SPLIT, MISSING):
        lines.append(f"| {outcome} | {comparison.count(outcome)} |")
    shifted = sum(1 for c in comparison.lines if c.shifted_days)
    lines += [
        f"| **Total** | **{total}** |",
        "",
        f"- Lançamentos do Razão sem movimento no extrato: {len(comparison.only_ledger)}",
        f"- Casados com data diferente (até {WINDOW_DAYS} dias): {shifted}",
        "",
        "### Contas de contrapartida usadas pela contadora (evidência para Q-50/Q-53)",
        "",
        "| Tipo de parte | Contas (ocorrências) |",
        "|---|---|",
    ]
    for group, counter in sorted(comparison.accounts.items()):
        accounts = ", ".join(f"{code} ({n})" for code, n in counter.most_common(6))
        more = f" e mais {len(counter) - 6}" if len(counter) > 6 else ""
        lines.append(f"| {group} | {accounts}{more} |")
    return "\n".join(lines) + "\n"


def render_ledger_csv(comparison: LedgerComparison) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(
        [
            "data",
            "valor",
            "historico_extrato",
            "resultado",
            "dias_de_diferenca",
            "lancamentos_razao",
        ]
    )
    for item in comparison.lines:
        writer.writerow(
            [
                item.line.bank.occurred_on.strftime("%d/%m/%Y"),
                money(item.line.bank.amount_cents),
                item.line.bank.description,
                item.outcome,
                item.shifted_days,
                " | ".join(
                    f"{m.reference} {m.occurred_on:%d/%m} {money(m.amount_cents)} "
                    f"contra {','.join(m.counterparts) or '-'}"
                    for m in item.movements
                ),
            ]
        )
    for movement in comparison.only_ledger:
        writer.writerow(
            [
                movement.occurred_on.strftime("%d/%m/%Y"),
                money(movement.amount_cents),
                movement.history,
                ONLY_LEDGER,
                "",
                f"{movement.reference} contra {','.join(movement.counterparts) or '-'}",
            ]
        )
    return out.getvalue()


def _credit_section(result: SimulationResult) -> list[str]:
    if not result.loans and not result.cards:
        return []
    lines = ["", "## Empréstimo e cartão (D-418)", ""]
    last = max((r.bank.occurred_on for r in result.lines), default=None)
    for loan in result.loans:
        paid = [
            p
            for p in result.lines
            for part in p.parts
            if part.source == f"empréstimo {loan.contract}"
        ]
        lines.append(
            f"- Empréstimo {loan.contract}: {loan.count} parcelas; {len(paid)} paga(s) no mês "
            "identificada(s) no extrato"
            + (
                f"; parcelas a vencer depois de {last:%d/%m/%Y}: {money(loan.open_after(last))}"
                if last
                else ""
            )
            + "."
        )
    for loan, item in result.loan_unmatched:
        lines.append(
            f"  - Parcela {item.number:03d} de {loan.contract} paga em "
            f"{item.paid_on:%d/%m/%Y} ({money(item.amount_cents)}) sem débito no extrato."
        )
    for card in result.cards:
        state = "sem débito no extrato" if card in result.cards_unmatched else "débito identificado"
        lines.append(
            f"- Fatura do cartão final {card.card}, venc. {card.due_on:%d/%m/%Y}: "
            f"{money(card.total_cents)} ({state})."
        )
        for item in card.expenses:
            lines.append(
                f"  - {item.occurred_on:%d/%m/%Y} {item.description}: {money(item.amount_cents)}"
            )
    lines.append(
        "- Juros e principal (Q-55) e lançamento da fatura (Q-56): a definir com a contabilidade."
    )
    return lines


def _transfers_section(result: SimulationResult) -> list[str]:
    if not result.transfers:
        return []
    lines = ["", "## Transferências entre contas da empresa (D-415)", ""]
    for pair in result.transfers:
        out, inc = pair.outgoing.bank, pair.incoming.bank
        lines.append(
            f"- {out.occurred_on:%d/%m/%Y} {pair.source_name} → {inc.occurred_on:%d/%m/%Y} "
            f"{pair.target_name}: {money(inc.amount_cents)}"
        )
    lines.append("- Como lançar e quais contas usar: a definir com a contabilidade (Q-57).")
    return lines


def _investment_section(result: SimulationResult) -> list[str]:
    statement = result.investment
    if statement is None:
        return []
    matched = [p for r in result.lines for p in r.parts if p.kind == "investment"]
    lines = [
        "",
        "## Aplicação financeira (D-411)",
        "",
        f"- Saldo anterior {money(statement.opening_cents)} → saldo atual "
        f"{money(statement.closing_cents)} (cadeia conferida).",
        "- Aplicações e resgates casados com o extrato bancário: "
        f"{len(matched)} movimentos do banco, "
        f"{money(sum(p.amount_cents for p in matched))}.",
        f"- Rendimentos a lançar na conta da aplicação: {money(statement.total('income'))}; "
        f"IRRF retido: {money(statement.total('income_tax'))}; "
        f"IOF: {money(statement.total('iof'))} (contas a definir, Q-54).",
    ]
    if result.investment_unmatched:
        lines.append("- Movimentos da aplicação sem par no extrato bancário:")
        labels = {"application": "aplicação", "redemption": "resgate"}
        for movement in result.investment_unmatched:
            lines.append(
                f"  - {movement.occurred_on:%d/%m/%Y} {labels[movement.kind]} "
                f"{money(movement.amount_cents)}"
            )
    return lines


def _documents_section(result: SimulationResult) -> list[str]:
    matches = result.documents
    if not matches:
        return []
    kinds = Counter(m.document.kind for m in matches)
    payments = [m for m in matches if m.document.is_payment and not m.document.uncertain]
    found = [m for m in payments if m.line is not None]
    by_account = Counter(m.line.bank.account for m in found if m.line is not None)
    missing = [m for m in payments if m.line is None]
    uncertain = [m for m in matches if m.document.uncertain and m.document.kind != "outro"]
    lines = [
        "",
        "## Documentos escaneados (D-412)",
        "",
        f"- Documentos lidos: {len(matches)} ("
        + ", ".join(f"{kind} {n}" for kind, n in kinds.most_common())
        + ").",
        f"- Documentos de pagamento com valor: {len(payments)}; com pagamento encontrado: "
        f"{len(found)} (" + ", ".join(f"{a} {n}" for a, n in by_account.most_common()) + ").",
        f"- Casados com valor lido diferente em um dígito (confirmar): "
        f"{sum(1 for m in found if m.note)}.",
        f"- Valor por extenso diferente do valor em algarismos (confirmar): "
        f"{sum(1 for m in matches if m.document.note)}.",
        f"- Títulos baixados pelo documento, sem linha no caixa (R-10): "
        f"{sum(1 for m in found if m.settled)}.",
        "- Pagamentos identificados só pelo documento, sem título na posição (R-10): "
        f"{sum(1 for m in found if m.line and not m.settled and _by_document(m))}.",
        "- Leitura incerta (confiança do OCR abaixo de 90, sem linha digitável): "
        f"{len(uncertain)}.",
    ]
    if missing:
        lines.append(
            "- Sem pagamento identificado — pode ter sido pago em dinheiro "
            "ou ser ressarcimento (R-11):"
        )
        for match in missing:
            document = match.document
            due = f" venc. {document.due_on:%d/%m/%Y}" if document.due_on else ""
            lines.append(f"  - {document.label}: {money(document.amount_cents or 0)}{due}")
    return lines


def render_documents_csv(result: SimulationResult) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(
        [
            "arquivo",
            "pagina",
            "tipo",
            "valor",
            "vencimento",
            "cnpj",
            "numero",
            "confianca_ocr",
            "linha_digitavel_valida",
            "pagamento",
            "baixa_pelo_documento",
            "observacao",
        ]
    )
    for match in result.documents:
        document = match.document
        payment = ""
        if match.line is not None:
            bank = match.line.bank
            payment = f"{bank.account} {bank.occurred_on:%d/%m/%Y} {money(bank.amount_cents)}"
        writer.writerow(
            [
                document.source,
                document.page,
                document.kind,
                money(document.amount_cents) if document.amount_cents else "",
                document.due_on.strftime("%d/%m/%Y") if document.due_on else "",
                ",".join(document.tax_ids),
                document.number,
                document.confidence,
                "sim" if document.boleto else "não",
                payment,
                "sim" if match.settled else "",
                "; ".join(n for n in (document.note, match.note) if n),
            ]
        )
    return out.getvalue()


def _by_document(match: object) -> bool:
    line = getattr(match, "line", None)
    return bool(line) and any(
        p.kind == "document" and p.source.startswith("documento ") for p in line.parts
    )
