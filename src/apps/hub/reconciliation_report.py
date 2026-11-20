"""Account/period conference with unmatched amounts in both directions, without closing gates."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter
from datetime import date, datetime
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    IndependentLedgerRecord,
    MovementReconciliation,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import ReconciliationError, _source_bytes


def report_period_params(params: QueryDict) -> dict[str, date | None]:
    """Reject ambiguous dates instead of silently enlarging the requested report."""
    parsed: dict[str, date | None] = {"start": None, "end": None}
    try:
        for name in parsed:
            values = params.getlist(name)
            if not values:
                continue
            if len(values) != 1:
                raise ValueError
            value = date.fromisoformat(values[0])
            if value.isoformat() != values[0]:
                raise ValueError
            parsed[name] = value
        if parsed["start"] and parsed["end"] and parsed["start"] > parsed["end"]:
            raise ValueError
    except (TypeError, ValueError):
        raise ReconciliationError(
            "Confira o período solicitado; use datas válidas no formato AAAA-MM-DD."
        ) from None
    return parsed


def _plain_reference(value: Any) -> str:
    return str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else ""


def _source_position(reference: Any) -> str:
    if not isinstance(reference, dict):
        return ""
    for field, label in (("page", "Página"), ("row", "Linha"), ("fitid", "OFX")):
        value = _plain_reference(reference.get(field))
        if value:
            return f"{label} {value}"
    for field, label in (("rows", "Linhas"), ("row_codes", "Registros")):
        rows = reference.get(field)
        if isinstance(rows, list):
            labels = [_plain_reference(row) for row in rows]
            if labels and all(labels):
                return label + " " + ", ".join(labels)
    return ""


def _record_in_scope(record: IndependentLedgerRecord, source: ReconciliationSourceFile) -> bool:
    account = source.financial_account
    assert account is not None
    entry = record.accounting_entry
    return bool(
        record.organization_id == source.organization_id
        and record.financial_account_id == source.financial_account_id
        and record.source_file.organization_id == source.organization_id
        and record.source_file.company_id == source.company_id
        and record.source_file.financial_account_id == source.financial_account_id
        and record.source_file.origin == "accounting"
        and record.entry.organization_id == source.organization_id
        and record.entry.company_id == source.company_id
        and record.entry.movement_id is None
        and entry.organization_id == source.organization_id
        and entry.company_id == source.company_id
        and entry.data_source.organization_id == source.organization_id
        and entry.account_reference == account.account_reference
        and entry.occurred_on == record.entry.occurred_on
        and record.bank_line.organization_id == source.organization_id
        and record.bank_line.entry_id == record.entry_id
        and record.bank_line.account_code == account.ledger_code
        and record.bank_line.amount_cents == entry.amount_cents
    )


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
    if any(
        movement.organization_id != source.organization_id
        or movement.company_id != source.company_id
        or movement.financial_account_id != source.financial_account_id
        for movement in movements
    ):
        raise ReconciliationError(
            "Há movimentos fora da empresa ou conta do extrato; solicite revisão."
        )
    dates = [m.occurred_on for m in movements if m.occurred_on]
    if not dates or len(dates) != len(movements):
        raise ReconciliationError(
            "Extrato sem movimentos datados completos; confira o processamento."
        )
    bank_evidence = None
    if source.kind == "pdf":
        from apps.hub.bank_evidence import read_sicredi_pdf

        bank_evidence = read_sicredi_pdf(content)
    ofx_balance = None
    if source.kind == "ofx":
        from apps.hub.reconciliation import read_ofx_statement_balance

        ofx_balance = read_ofx_statement_balance(content)
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
        ).select_related("accounting_entry__data_source", "entry", "source_file", "bank_line")
    )
    if any(not _record_in_scope(record, source) for record in records):
        raise ReconciliationError(
            "Há registros do Razão fora do escopo da fonte; solicite revisão."
        )
    movement_ids = {movement.pk for movement in movements}
    record_entry_ids = {record.entry_id for record in records}
    allocations = list(
        MovementReconciliation.objects.filter(
            Q(movement_id__in=movement_ids) | Q(entry_id__in=record_entry_ids),
            state="confirmed",
        ).values(
            "organization_id",
            "movement_id",
            "entry_id",
            "amount_cents",
            "movement__organization_id",
            "movement__company_id",
            "movement__financial_account_id",
            "movement__source_file__organization_id",
            "movement__source_file__company_id",
            "movement__source_file__financial_account_id",
            "movement__source_file__origin",
            "entry__organization_id",
            "entry__company_id",
            "entry__movement_id",
            "entry__purpose",
            "entry__independent_source__financial_account_id",
        )
    )
    bank_used: Counter[Any] = Counter()
    ledger_used: Counter[Any] = Counter()
    for allocation in allocations:
        if (
            any(
                allocation[field] != source.organization_id
                for field in (
                    "organization_id",
                    "movement__organization_id",
                    "movement__source_file__organization_id",
                    "entry__organization_id",
                )
            )
            or any(
                allocation[field] != source.company_id
                for field in (
                    "movement__company_id",
                    "movement__source_file__company_id",
                    "entry__company_id",
                )
            )
            or any(
                allocation[field] != source.financial_account_id
                for field in (
                    "movement__financial_account_id",
                    "movement__source_file__financial_account_id",
                )
            )
            or allocation["movement__source_file__origin"] != "bank_statement"
            or allocation["entry__movement_id"] == allocation["movement_id"]
            or (
                allocation["entry__independent_source__financial_account_id"] is not None
                and (
                    allocation["entry__independent_source__financial_account_id"]
                    != source.financial_account_id
                    or allocation["entry_id"] not in record_entry_ids
                )
            )
            or (
                allocation["entry__purpose"] == "source_ledger"
                and allocation["entry_id"] not in record_entry_ids
            )
        ):
            raise ReconciliationError("Há alocações fora da empresa ou conta; solicite revisão.")
        if allocation["movement_id"] in movement_ids:
            bank_used[allocation["movement_id"]] += allocation["amount_cents"]
        # Capacity consumed by another statement in the same account remains consumed.
        if allocation["entry_id"] in record_entry_ids:
            ledger_used[allocation["entry_id"]] += allocation["amount_cents"]
    bank_rows: list[dict[str, Any]] = []
    for movement in movements:
        assert movement.occurred_on is not None
        used = bank_used[movement.pk]
        if used > abs(movement.amount_cents):
            raise ReconciliationError("A alocação excede o movimento; solicite revisão.")
        bank_rows.append(
            {
                "reference": str(movement.pk),
                "date": movement.occurred_on.isoformat(),
                "direction": movement.direction,
                "amount_cents": abs(movement.amount_cents),
                "allocated_cents": used,
                "remaining_cents": abs(movement.amount_cents) - used,
                "history": movement.original_description or movement.description,
                "document": movement.document_number,
                "source_name": source.original_filename,
                "source_position": _source_position(movement.source_reference),
                "source_hash": source.content_hash,
            }
        )
    ledger_rows: list[dict[str, Any]] = []
    for record in records:
        entry = record.accounting_entry
        used = ledger_used[record.entry_id]
        if used > entry.amount_cents:
            raise ReconciliationError("A alocação excede o registro do Razão; solicite revisão.")
        ledger_rows.append(
            {
                "reference": str(record.pk),
                "date": entry.occurred_on.isoformat(),
                "direction": entry.direction,
                "amount_cents": entry.amount_cents,
                "allocated_cents": used,
                "remaining_cents": entry.amount_cents - used,
                "history": record.entry.history or entry.description,
                "document": _plain_reference(
                    record.source_reference.get("document")
                    if isinstance(record.source_reference, dict)
                    else None
                ),
                "source_name": record.source_file.original_filename,
                "source_position": _source_position(record.source_reference),
                "source_hash": record.source_file.content_hash,
            }
        )
    bank_net = sum(m.amount_cents for m in movements)
    ledger_net = sum(
        r["amount_cents"] * (1 if r["direction"] == "inflow" else -1) for r in ledger_rows
    )
    full_pdf_period = bank_evidence and start == reported_start and end == reported_end
    opening_bank = bank_evidence.opening_cents if bank_evidence and full_pdf_period else None
    closing_bank = bank_evidence.closing_cents if bank_evidence and full_pdf_period else None
    ofx_balances = ofx_balance.balances_for(start, end) if ofx_balance else None
    if ofx_balances is not None:
        opening_bank, closing_bank = ofx_balances
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
    if ofx_balances is not None:
        warnings.append(
            "Saldos do banco calculados pelo saldo final informado no OFX e pelos "
            "movimentos do próprio arquivo."
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


def _money(cents: int | None) -> str:
    if cents is None:
        return "Não informado"
    sign = "-" if cents < 0 else ""
    units, remainder = divmod(abs(cents), 100)
    return f"{sign}R$ {units:,}".replace(",", ".") + f",{remainder:02}"


def report_presentation_context(
    source: ReconciliationSourceFile, report: dict[str, Any]
) -> dict[str, Any]:
    """Present all report rows without changing the stable technical CSV contract."""
    if (
        report["source_id"] != str(source.pk)
        or report["company_id"] != str(source.company_id)
        or report["financial_account_id"] != str(source.financial_account_id)
        or report["source_hash"] != source.content_hash
    ):
        raise ReconciliationError("Relatório fora da empresa, conta ou fonte solicitada.")
    sections = []
    for key, label in (("bank", "Extrato bancário"), ("ledger", "Razão independente")):
        rows = []
        for row in report[f"{key}_rows"]:
            confirmed = row["amount_cents"] > 0 and row["remaining_cents"] == 0
            partial = row["allocated_cents"] > 0 and not confirmed
            rows.append(
                {
                    **row,
                    "date_label": date.fromisoformat(row["date"]).strftime("%d/%m/%Y"),
                    "direction_label": {"inflow": "Entrada", "outflow": "Saída"}.get(
                        row["direction"], "Não informada"
                    ),
                    "amount_label": _money(row["amount_cents"]),
                    "allocated_label": _money(row["allocated_cents"]),
                    "remaining_label": _money(row["remaining_cents"]),
                    "state": "confirmed" if confirmed else "partial" if partial else "pending",
                    "state_label": "Conferido"
                    if confirmed
                    else "Parcial"
                    if partial
                    else "A conferir",
                }
            )
        sections.append(
            {
                "key": key,
                "label": label,
                "rows": rows,
                "count": len(rows),
                "pending_count": sum(row["state"] != "confirmed" for row in rows),
            }
        )
    balances = [
        {"label": label, "value": _money(report[key])}
        for key, label in (
            ("opening_bank_cents", "Saldo inicial do banco"),
            ("closing_bank_cents", "Saldo final do banco"),
            ("opening_ledger_cents", "Saldo inicial do Razão"),
            ("calculated_closing_ledger_cents", "Saldo final calculado do Razão"),
        )
    ]
    generated = datetime.fromisoformat(report["generated_at"])
    sources = {
        ("Extrato bancário", source.original_filename, source.content_hash): {
            "label": "Extrato bancário",
            "name": source.original_filename,
            "hash": source.content_hash,
            "hash_label": "Hash do arquivo verificado",
        }
    }
    for row in report["ledger_rows"]:
        sources.setdefault(
            ("Razão", row["source_name"], row["source_hash"]),
            {
                "label": "Razão",
                "name": row["source_name"],
                "hash": row["source_hash"],
                "hash_label": "Hash registrado na importação",
            },
        )
    return {
        "report_source": source,
        "report_data": report,
        "report_sections": sections,
        "report_balances": balances,
        "report_sources": list(sources.values()),
        "report_period_label": (
            f"{date.fromisoformat(report['period_start']):%d/%m/%Y} a "
            f"{date.fromisoformat(report['period_end']):%d/%m/%Y}"
        ),
        "report_generated_label": timezone.localtime(generated).strftime("%d/%m/%Y às %H:%M:%S %z"),
        "report_bank_net_label": _money(report["bank_net_cents"]),
        "report_ledger_net_label": (
            _money(report["ledger_net_cents"]) if report["ledger_count"] else "Sem registros"
        ),
        "report_difference_label": (
            _money(report["period_difference_cents"])
            if report["ledger_count"]
            else "Não comparável"
        ),
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
