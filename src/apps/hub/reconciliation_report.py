"""Account/period conference with unmatched amounts in both directions, without closing gates."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    IndependentLedgerRecord,
    MovementReconciliation,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import ReconciliationError, _source_bytes


@transaction.atomic
def build_source_report(
    source: ReconciliationSourceFile,
    *,
    start: date | None = None,
    end: date | None = None,
    opening_ledger_cents: int | None = None,
) -> dict[str, Any]:
    if source.origin != "bank_statement" or source.financial_account_id is None:
        raise ReconciliationError(
            "Selecione um extrato bancário com conta financeira identificada."
        )
    account = source.financial_account
    assert account is not None
    if account.organization_id != source.organization_id or account.company_id != source.company_id:
        raise ReconciliationError("Conta financeira fora da empresa do extrato.")
    ClientCompany.objects.select_for_update().get(
        pk=source.company_id, organization_id=source.organization_id
    )
    if source.runs.filter(state__in=["waiting", "processing"]).exists():
        raise ReconciliationError(
            "Aguarde o processamento do extrato antes de conferir o relatório."
        )
    latest = source.runs.order_by("-created_at", "-pk").first()
    protection_notice_only = (
        latest is not None
        and latest.stage == "rules_reapplied"
        and isinstance(latest.errors, list)
        and latest.error_count == len(latest.errors) == 1
        and isinstance(latest.errors[0], dict)
        and latest.errors[0].get("code") == "protected_movements"
    )
    if (
        latest is None
        or latest.state in {"failed", "canceled"}
        or (latest.error_count and not protection_notice_only)
    ):
        raise ReconciliationError(
            "Corrija ou retome o processamento do extrato antes da conferência."
        )
    content = _source_bytes(source)
    if hashlib.sha256(content).hexdigest() != source.content_hash:
        raise ReconciliationError("O hash do extrato diverge; restaure o arquivo original.")
    movements = list(source.movements.order_by("occurred_on", "source_key"))
    dates = [m.occurred_on for m in movements if m.occurred_on]
    if not dates or len(dates) != len(movements):
        raise ReconciliationError(
            "Extrato sem movimentos datados completos; confira o processamento."
        )
    bank_evidence = None
    if source.kind == "pdf":
        from apps.hub.bank_evidence import read_sicredi_pdf

        bank_evidence = read_sicredi_pdf(content)
    basis = "reported_pdf_period" if bank_evidence else "imported_movement_dates"
    reported_start = bank_evidence.period_start if bank_evidence else min(dates)
    reported_end = bank_evidence.period_end if bank_evidence else max(dates)
    start, end = start or reported_start, end or reported_end
    if start > end:
        raise ReconciliationError("O início do período deve ser anterior ou igual ao fim.")
    movements = [
        m for m in movements if m.occurred_on is not None and start <= m.occurred_on <= end
    ]
    records = list(
        IndependentLedgerRecord.objects.filter(
            organization=source.organization,
            financial_account=account,
            entry__occurred_on__range=(start, end),
        ).select_related("accounting_entry", "entry")
    )
    allocations = list(
        MovementReconciliation.objects.filter(
            organization=source.organization,
            state="confirmed",
            movement__in=movements,
        ).values("movement_id", "entry_id", "amount_cents")
    )
    # Source capacity consumed by another statement is still consumed here.
    ledger_allocations = list(
        MovementReconciliation.objects.filter(
            organization=source.organization,
            state="confirmed",
            entry_id__in=[r.entry_id for r in records],
        ).values("entry_id", "amount_cents")
    )
    bank_used: Counter[Any] = Counter()
    ledger_used: Counter[Any] = Counter()
    for allocation in allocations:
        bank_used[allocation["movement_id"]] += allocation["amount_cents"]
    for ledger_allocation in ledger_allocations:
        ledger_used[ledger_allocation["entry_id"]] += ledger_allocation["amount_cents"]
    bank_rows: list[dict[str, Any]] = []
    for movement in movements:
        assert movement.occurred_on is not None
        used = bank_used[movement.pk]
        bank_rows.append(
            {
                "reference": str(movement.pk),
                "date": movement.occurred_on.isoformat(),
                "direction": movement.direction,
                "amount_cents": abs(movement.amount_cents),
                "allocated_cents": used,
                "remaining_cents": abs(movement.amount_cents) - used,
            }
        )
    ledger_rows: list[dict[str, Any]] = []
    for record in records:
        entry = record.accounting_entry
        used = ledger_used[record.entry_id]
        ledger_rows.append(
            {
                "reference": str(record.pk),
                "date": entry.occurred_on.isoformat(),
                "direction": entry.direction,
                "amount_cents": entry.amount_cents,
                "allocated_cents": used,
                "remaining_cents": entry.amount_cents - used,
            }
        )
    bank_net = sum(m.amount_cents for m in movements)
    ledger_net = sum(
        r["amount_cents"] * (1 if r["direction"] == "inflow" else -1) for r in ledger_rows
    )
    full_pdf_period = bank_evidence and start == reported_start and end == reported_end
    opening_bank = bank_evidence.opening_cents if bank_evidence and full_pdf_period else None
    closing_bank = bank_evidence.closing_cents if bank_evidence and full_pdf_period else None
    warnings = ["A cobertura do Razão depende da conferência da fonte pela contadora."]
    if protection_notice_only:
        warnings.append("A reaplicação preservou os movimentos com decisões humanas ou contábeis.")
    if basis == "imported_movement_dates":
        warnings.append(
            "Período baseado nos movimentos importados; cobertura integral não comprovada."
        )
    if not records:
        warnings.append("Nenhum Razão independente recebido para esta conta e período.")
    if opening_ledger_cents is None:
        warnings.append(
            "Saldo inicial do Razão não informado; fechamento de saldos não comprovado."
        )
    if source.kind == "pdf":
        warnings.append(
            "Confira a equivalência entre a conta exibida no PDF e a conta selecionada."
        )
    return {
        "version": "reconciliation-conference-v1",
        "generated_at": timezone.now().isoformat(),
        "homologated": False,
        "read_only": True,
        "coverage_confirmed": False,
        "source_id": str(source.pk),
        "source_hash": source.content_hash,
        "company_id": str(source.company_id),
        "financial_account_id": str(account.pk),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "period_basis": basis,
        "bank_count": len(bank_rows),
        "ledger_count": len(ledger_rows),
        "bank_net_cents": bank_net,
        "ledger_net_cents": ledger_net,
        "period_difference_cents": bank_net - ledger_net,
        "opening_bank_cents": opening_bank,
        "closing_bank_cents": closing_bank,
        "opening_ledger_cents": opening_ledger_cents,
        "calculated_closing_ledger_cents": (
            opening_ledger_cents + ledger_net if opening_ledger_cents is not None else None
        ),
        "bank_unmatched_count": sum(r["remaining_cents"] != 0 for r in bank_rows),
        "ledger_unmatched_count": sum(r["remaining_cents"] != 0 for r in ledger_rows),
        "bank_rows": bank_rows,
        "ledger_rows": ledger_rows,
        "warnings": warnings,
    }


def render_conference_csv(report: dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Conferência bancária e Razão", "cobertura e aceite pendentes"])
    for key in [
        "generated_at",
        "source_hash",
        "period_start",
        "period_end",
        "period_basis",
        "bank_count",
        "ledger_count",
        "bank_net_cents",
        "ledger_net_cents",
        "period_difference_cents",
        "opening_bank_cents",
        "closing_bank_cents",
        "opening_ledger_cents",
        "calculated_closing_ledger_cents",
    ]:
        writer.writerow([key, report[key] if report[key] is not None else "não informado"])
    for warning in report["warnings"]:
        writer.writerow(["Atenção", warning])
    writer.writerow(
        [
            "fonte",
            "referência",
            "data",
            "direção",
            "valor_centavos",
            "alocado_centavos",
            "pendente_centavos",
        ]
    )
    for side in ["bank", "ledger"]:
        for row in report[f"{side}_rows"]:
            writer.writerow(
                [
                    side,
                    row["reference"],
                    row["date"],
                    row["direction"],
                    row["amount_cents"],
                    row["allocated_cents"],
                    row["remaining_cents"],
                ]
            )
    return output.getvalue().encode("utf-8-sig")
