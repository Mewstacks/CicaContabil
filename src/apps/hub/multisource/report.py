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
        f"- Baixa automática de títulos: **{_percent(result.automatic_share)}** dos movimentos.",
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
    ):
        same = [p for p in parts if p.kind == kind]
        lines.append(f"- {label}: {len(same)} · {money(sum(p.amount_cents for p in same))}")
    lines[lines.index("## Títulos baixados na simulação")] = "## Partes identificadas"
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
