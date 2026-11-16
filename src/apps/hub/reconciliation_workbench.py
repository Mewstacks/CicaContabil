"""A read-only bank/ledger workbench, independent of posting-account setup."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any
from urllib.parse import unquote, urlencode, urlsplit

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, QueryDict
from django.urls import reverse

from apps.hub.models import IndependentLedgerRecord, ReconciliationSourceFile
from apps.hub.reconciliation_bridge import compatible_record
from apps.hub.reconciliation_report import build_source_report, report_period_params
from apps.hub.reconciliation_service import ReconciliationError


def _local_return(candidate: str, expected_path: str) -> bool:
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return False
    decoded = unquote(candidate)
    return bool(
        candidate.startswith("/")
        and not candidate.startswith("//")
        and not parts.scheme
        and not parts.netloc
        and parts.path == expected_path
        and not parts.fragment
        and "\\" not in decoded
        and not any(ord(c) < 32 or ord(c) == 127 for c in decoded)
    )


def portfolio_return_url(request: HttpRequest) -> str:
    """Keep the portfolio filter context without accepting an arbitrary return URL."""
    values = request.GET.getlist("portfolio_return")
    if len(values) != 1:
        return ""
    candidate = values[0]
    return candidate if _local_return(candidate, reverse("hub:reconciliation-portfolio")) else ""


def conference_return_url(request: HttpRequest, source_id: object) -> str:
    """Only return to this movement's own source, never another tenant or host."""
    values = request.GET.getlist("return_to")
    if len(values) != 1:
        return ""
    candidate = values[0]
    fallback = reverse("hub:reconciliation-source-review", kwargs={"source_id": source_id})
    if not _local_return(candidate, fallback):
        return ""
    try:
        report_period_params(QueryDict(urlsplit(candidate).query))
    except ReconciliationError:
        return ""
    return candidate


def source_review_context(source: ReconciliationSourceFile, request: HttpRequest) -> dict[str, Any]:
    period = report_period_params(request.GET)
    report = build_source_report(source, **period)
    portfolio_return = portfolio_return_url(request)
    state = request.GET.get("state", "pending")
    if state not in {"all", "pending", "confirmed"}:
        state = "pending"
    query = request.GET.get("q", "").strip()[:100]
    bank_rows = {row["reference"]: row for row in report["bank_rows"]}
    ids = set(bank_rows)
    if state == "pending":
        ids = {
            key
            for key, row in bank_rows.items()
            if row["remaining_cents"] != 0 or row["amount_cents"] == 0
        }
    elif state == "confirmed":
        ids = {
            key
            for key, row in bank_rows.items()
            if row["remaining_cents"] == 0 and row["amount_cents"] > 0
        }
    movements = source.movements.filter(pk__in=ids).select_related(
        "source_file", "financial_account"
    )
    if query:
        movements = movements.filter(
            Q(original_description__icontains=query) | Q(description__icontains=query)
        )
    page = Paginator(movements.order_by("occurred_on", "source_key", "pk"), 50).get_page(
        request.GET.get("page")
    )
    visible = list(page.object_list)
    candidates: dict[tuple[Any, str, int], list[IndependentLedgerRecord]] = defaultdict(list)
    if visible:
        dates = {movement.occurred_on for movement in visible}
        for record in IndependentLedgerRecord.objects.filter(
            organization_id=source.organization_id,
            financial_account_id=source.financial_account_id,
            source_file__company_id=source.company_id,
            source_file__organization_id=source.organization_id,
            source_file__origin="accounting",
            entry__organization_id=source.organization_id,
            entry__company_id=source.company_id,
            entry__movement__isnull=True,
            entry__occurred_on__in=dates,
            accounting_entry__company_id=source.company_id,
            accounting_entry__organization_id=source.organization_id,
            accounting_entry__data_source__organization_id=source.organization_id,
        ).select_related(
            "entry",
            "accounting_entry__data_source",
            "source_file",
            "financial_account",
            "bank_line",
        ):
            entry = record.accounting_entry
            candidates[(entry.occurred_on, entry.direction, entry.amount_cents)].append(record)
    report_params = {key: value.isoformat() for key, value in period.items() if value is not None}
    if portfolio_return:
        report_params["portfolio_return"] = portfolio_return
    params = {"state": state, "q": query, **report_params}
    list_path = reverse("hub:reconciliation-source-review", kwargs={"source_id": source.pk})
    return_path = list_path + "?" + urlencode({**params, "page": page.number})
    items = []
    for movement in visible:
        row = bank_rows[str(movement.pk)]
        matches = [
            record
            for record in candidates.get(
                (movement.occurred_on, movement.direction, abs(movement.amount_cents)), []
            )
            if compatible_record(movement, record)
        ]
        confirmed = row["amount_cents"] > 0 and row["remaining_cents"] == 0
        partial = not confirmed and row["allocated_cents"] > 0
        items.append(
            {
                "movement": movement,
                "amount_brl": Decimal(row["amount_cents"]) / 100,
                "allocated_brl": Decimal(row["allocated_cents"]) / 100,
                "remaining_brl": Decimal(row["remaining_cents"]) / 100,
                "state": "confirmed" if confirmed else "partial" if partial else "pending",
                "state_label": "Conferido" if confirmed else "Parcial" if partial else "A conferir",
                "candidate_count": len(matches),
                "candidate_history": matches[0].entry.history if len(matches) == 1 else "",
                "detail_url": reverse(
                    "hub:reconciliation-movement", kwargs={"movement_id": movement.pk}
                )
                + "?"
                + urlencode({"return_to": return_path}),
            }
        )
    return {
        "conference_source": source,
        "conference_report": report,
        "conference_rows": items,
        "conference_page": page,
        "conference_query": query,
        "conference_state": state,
        "conference_querystring": urlencode(params),
        "conference_report_querystring": urlencode(report_params),
        "conference_portfolio_return_url": portfolio_return,
        "conference_period_start": period["start"].isoformat() if period["start"] else "",
        "conference_period_end": period["end"].isoformat() if period["end"] else "",
        "conference_confirmed_count": sum(
            row["amount_cents"] > 0 and row["remaining_cents"] == 0 for row in bank_rows.values()
        ),
        "conference_bank_net_brl": Decimal(report["bank_net_cents"]) / 100,
        "conference_ledger_net_brl": Decimal(report["ledger_net_cents"]) / 100,
        "conference_difference_brl": Decimal(report["period_difference_cents"]) / 100,
    }
