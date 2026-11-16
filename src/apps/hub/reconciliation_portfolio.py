"""Read-only monthly coverage of retained bank and independent ledger records."""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Exists, F, Max, OuterRef, Q, Subquery
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    NormalizedMovement,
    ReconciliationAccountCandidate,
    ReconciliationRun,
    ReconciliationSourceFile,
)

STATUS_LABELS = {
    "pending_mapping": "Vínculo de conta pendente",
    "missing_account": "Sem conta cadastrada",
    "missing_bank": "Sem extrato no mês",
    "missing_ledger": "Sem Razão no mês",
    "available": "Dados disponíveis para conferir",
    "review": "Exige revisão",
}
STATUS_PRIORITY = (
    "review", "pending_mapping", "missing_account", "missing_bank", "missing_ledger", "available",
)
FILTER_NAMES = ("month", "q", "company", "account", "status", "page")


def _month(value: str) -> tuple[date, date]:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError
    start = date.fromisoformat(f"{value}-01")
    return start, start.replace(day=calendar.monthrange(start.year, start.month)[1])


def _url(name: str, params: dict[str, Any], *, anchor: str = "") -> str:
    return reverse(name) + "?" + urlencode(params) + anchor


def _bank_integrity() -> Q:
    return Q(
        movements__organization_id=F("organization_id"),
        movements__company_id=F("company_id"),
        movements__financial_account_id=F("financial_account_id"),
        movements__run__organization_id=F("organization_id"),
        movements__run__source_file_id=F("pk"),
    ) & (
        Q(movements__direction="inflow", movements__amount_cents__gt=0)
        | Q(movements__direction="outflow", movements__amount_cents__lt=0)
    )


def _source_issue(source: Any) -> str:
    if source.undated_count or source.invalid_count:
        return "Há movimentos sem data ou com vínculo incompatível; revise a importação."
    if source.running:
        return "Aguarde o término do processamento."
    if source.latest_stage in {"mapping", "financial_account_review", "ocr_review"}:
        return "Revise a conta ou o formato antes de conferir este arquivo."
    protected = (
        source.latest_stage == "rules_reapplied"
        and source.latest_error_count == 1
        and isinstance(source.latest_errors, list)
        and len(source.latest_errors) == 1
        and isinstance(source.latest_errors[0], dict)
        and source.latest_errors[0].get("code") == "protected_movements"
    )
    if (
        source.latest_state is None
        or source.latest_state in {"failed", "canceled"}
        or (source.latest_error_count and not protected)
    ):
        return "Corrija ou retome o processamento deste arquivo."
    if not source.dated_count:
        return "Arquivo sem movimentos datados; a competência ainda não foi identificada."
    return ""


def portfolio_context(*, office: Any, companies: Any, params: Any,
                      can_manage: bool = False) -> dict[str, Any]:
    """Use the caller's authorized company scope; never open files or enqueue work.

    Counts describe retained data, not completeness or accounting approval. Status
    totals count companies with each situation and can overlap for multiple accounts.
    """
    companies = companies.filter(organization=office).order_by("name", "pk")
    errors: list[str] = []
    values: dict[str, str] = {}
    for name in FILTER_NAMES:
        candidates = params.getlist(name) if hasattr(params, "getlist") else [params.get(name, "")]
        if len(candidates) > 1:
            errors.append("Informe cada filtro uma única vez.")
        values[name] = str(candidates[0] or "").strip() if candidates else ""
    if "month" not in params:
        latest = NormalizedMovement.objects.filter(
            organization=office, company__in=companies,
            source_file__organization=office,
            source_file__company_id=F("company_id"),
            source_file__origin="bank_statement",
            source_file__financial_account_id=F("financial_account_id"),
            financial_account__organization=office,
            financial_account__company_id=F("company_id"),
            run__organization=office, run__source_file_id=F("source_file_id"),
        ).filter(
            Q(direction="inflow", amount_cents__gt=0)
            | Q(direction="outflow", amount_cents__lt=0),
        ).aggregate(latest=Max("occurred_on"))["latest"]
        values["month"] = (latest or timezone.localdate()).strftime("%Y-%m")
    try:
        start, end = _month(values["month"])
    except ValueError:
        errors.append("Informe uma competência válida no formato AAAA-MM.")
        start = end = None
    if len(values["q"]) > 100:
        errors.append("A pesquisa deve ter até 100 caracteres.")
    values["status"] = values["status"] or "all"
    if values["status"] not in {"all", *STATUS_LABELS}:
        errors.append("Escolha uma situação válida.")
    page_number = values["page"] or "1"
    if not re.fullmatch(r"[1-9][0-9]{0,8}", page_number):
        errors.append("Informe uma página válida.")
        page_number = "1"
    selected_company = None
    selected_account = None
    for name, model in (("company", ClientCompany), ("account", FinancialAccount)):
        if not values[name]:
            continue
        try:
            identifier = UUID(values[name])
        except (ValueError, TypeError):
            errors.append("Escolha uma empresa ou conta disponível na sua carteira.")
            continue
        query = companies if model is ClientCompany else FinancialAccount.objects.filter(
            organization=office, company__in=companies,
        )
        selected = query.filter(pk=identifier).first()
        if selected is None:
            errors.append("Escolha uma empresa ou conta disponível na sua carteira.")
        elif name == "company":
            selected_company = selected
            values[name] = str(selected.pk)
        else:
            selected_account = selected
            values[name] = str(selected.pk)
    if selected_company and selected_account and selected_account.company_id != selected_company.pk:
        errors.append("A conta não pertence à empresa selecionada.")
    filters = {name: values[name] for name in FILTER_NAMES if name != "page"}
    canonical_params = {name: value for name, value in filters.items() if value}
    querystring = urlencode(canonical_params)
    canonical_url = _url("hub:reconciliation-portfolio", {
        **canonical_params, "page": page_number,
    })
    empty_counts = dict.fromkeys(("all", *STATUS_LABELS), 0)
    context: dict[str, Any] = {
        "rows": [], "page": Paginator([], 25).get_page(1), "month": values["month"],
        "start": start, "end": end, "querystring": querystring,
        "errors": list(dict.fromkeys(errors)), "counts": empty_counts, "filters": filters,
        "canonical_url": canonical_url, "can_manage": can_manage,
    }
    if errors:
        return context
    assert start is not None and end is not None
    if selected_company:
        companies = companies.filter(pk=selected_company.pk)
    if selected_account:
        companies = companies.filter(pk=selected_account.company_id)
    if values["q"]:
        companies = companies.filter(
            Q(name__icontains=values["q"]) | Q(dominio_code__icontains=values["q"])
        )
    company_rows = list(companies.only("id", "name", "dominio_code"))
    company_ids = [company.pk for company in company_rows]
    pending_candidates = {} if selected_account else {
        row["company_id"]: row["total"]
        for row in ReconciliationAccountCandidate.objects.filter(
            organization=office, company_id__in=company_ids,
            state=ReconciliationAccountCandidate.State.PENDING,
        ).values("company_id").annotate(total=Count("pk"))
    }
    account_query = FinancialAccount.objects.filter(
        organization=office, company_id__in=company_ids,
    ).order_by("name", "pk")
    if selected_account:
        account_query = account_query.filter(pk=selected_account.pk)
    accounts = list(account_query)
    accounts_by_id = {account.pk: account for account in accounts}
    latest_run = ReconciliationRun.objects.filter(
        organization=office, source_file_id=OuterRef("pk"),
    ).order_by("-created_at", "-pk")
    selected_dates = Q(movements__occurred_on__range=(start, end))
    source_query = ReconciliationSourceFile.objects.filter(
        organization=office, company_id__in=company_ids, origin="bank_statement",
    )
    if selected_account:
        source_query = source_query.filter(financial_account=selected_account)
    sources = source_query.only(
        "id", "company_id", "financial_account_id", "original_filename", "kind", "created_at",
    ).annotate(
        bank_count=Count("movements", filter=selected_dates & _bank_integrity()),
        month_count=Count("movements", filter=selected_dates),
        dated_count=Count("movements", filter=Q(movements__occurred_on__isnull=False)),
        undated_count=Count("movements", filter=Q(movements__occurred_on__isnull=True)),
        invalid_count=Count(
            # The conference validates the whole retained file before slicing dates.
            # A bad relationship in another month must not advertise an openable file.
            "movements", filter=~_bank_integrity(),
        ),
        running=Exists(latest_run.filter(state__in=["waiting", "processing"])),
        latest_state=Subquery(latest_run.values("state")[:1]),
        latest_stage=Subquery(latest_run.values("stage")[:1]),
        latest_error_count=Subquery(latest_run.values("error_count")[:1]),
        latest_errors=Subquery(latest_run.values("errors")[:1]),
    ).order_by("-created_at", "-pk")
    sources_by_account: dict[Any, list[Any]] = defaultdict(list)
    unassigned: dict[Any, int] = defaultdict(int)
    for source in sources:
        if not (source.month_count or source.undated_count or not source.dated_count):
            continue
        account = accounts_by_id.get(source.financial_account_id)
        if account is None or account.company_id != source.company_id:
            unassigned[source.company_id] += 1
        else:
            sources_by_account[account.pk].append(source)
    records = IndependentLedgerRecord.objects.filter(
        organization=office, financial_account_id__in=accounts_by_id,
        entry__occurred_on__range=(start, end),
    )
    valid_record = Q(
        source_file__organization=office, source_file__origin="accounting",
        source_file__company_id=F("financial_account__company_id"),
        source_file__financial_account_id=F("financial_account_id"),
        entry__organization=office, entry__company_id=F("financial_account__company_id"),
        entry__movement__isnull=True,
        accounting_entry__organization=office,
        accounting_entry__data_source__organization=office,
        accounting_entry__company_id=F("financial_account__company_id"),
        accounting_entry__occurred_on=F("entry__occurred_on"),
        accounting_entry__account_reference=F("financial_account__account_reference"),
        accounting_entry__direction__in=["inflow", "outflow"],
        accounting_entry__amount_cents__gt=0,
        bank_line__organization=office, bank_line__entry_id=F("entry_id"),
        bank_line__account_code=F("financial_account__ledger_code"),
        bank_line__amount_cents=F("accounting_entry__amount_cents"),
    )
    ledger_counts = {
        row["financial_account_id"]: row
        for row in records.values("financial_account_id").annotate(
            total=Count("pk"), valid=Count("pk", filter=valid_record),
        )
    }
    accounts_by_company: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for account in accounts:
        issues: list[str] = []
        if not account.active:
            issues.append("Conta desativada; revise a configuração antes de novos usos.")
        if not account.account_reference.strip() or not account.ledger_code.strip():
            issues.append("A conta precisa de referência bancária e vínculo contábil explícitos.")
        ledger = ledger_counts.get(account.pk, {"total": 0, "valid": 0})
        if ledger["total"] != ledger["valid"]:
            issues.append("Há registros do Razão com vínculos incompatíveis; solicite revisão.")
        source_rows = []
        for source in sources_by_account[account.pk]:
            issue = _source_issue(source)
            if issue:
                issues.append(issue)
            source_rows.append({
                "source": source, "bank_count": source.bank_count,
                "status": "review" if issue else "available",
                "status_label": "Revisar importação" if issue else "Extrato recebido",
                "review_url": "" if issue else (
                    reverse("hub:reconciliation-source-review", kwargs={"source_id": source.pk})
                    + "?" + urlencode({
                        "start": start.isoformat(), "end": end.isoformat(),
                        "portfolio_return": canonical_url,
                    })
                ),
            })
        bank_count = sum(source["bank_count"] for source in source_rows)
        status = ("review" if issues else "missing_bank" if not bank_count
                  else "missing_ledger" if not ledger["valid"] else "available")
        actions = []
        if status == "available":
            actions.append({
                "label": "Abrir conferência", "url": source_rows[0]["review_url"],
            })
        if can_manage:
            if issues:
                actions.append({"label": "Conferir configuração", "url": _url(
                    "hub:reconciliation-configuration", {"company": account.company_id},
                )})
            if account.active and (not bank_count or not ledger["valid"]):
                origin = "bank_statement" if not bank_count else "accounting"
                actions.append({
                    "label": "Enviar extrato" if origin == "bank_statement" else "Buscar Razão",
                    "url": _url("hub:reconciliation-ledger-request", {
                        "company": account.company_id, "account": account.pk,
                        "month": values["month"],
                    }),
                })
        accounts_by_company[account.company_id].append({
            "account": account, "status": status, "status_label": STATUS_LABELS[status],
            "bank_count": bank_count, "ledger_count": ledger["valid"],
            "bank_source_count": len(source_rows), "sources": source_rows,
            "issues": list(dict.fromkeys(issues)), "actions": actions,
        })
    rows = []
    counts = empty_counts.copy()
    for company in company_rows:
        company_accounts = accounts_by_company[company.pk]
        statuses = {account["status"] for account in company_accounts} or {"missing_account"}
        candidate_count = pending_candidates.get(company.pk, 0)
        candidate_url = _url("hub:reconciliation-account-candidates", {
            "company": company.pk, "status": "pending",
        }) if candidate_count else ""
        if candidate_count:
            statuses.add("pending_mapping")
        if unassigned[company.pk]:
            statuses.add("review")
        ordered_statuses = [status for status in STATUS_PRIORITY if status in statuses]
        actions = [{"label": "Conferir configuração", "url": _url(
            "hub:reconciliation-configuration", {"company": company.pk},
        )}] if can_manage and (not company_accounts or unassigned[company.pk]) else []
        if candidate_count:
            actions = [{
                "label": "Revisar vínculos" if can_manage else "Ver vínculos pendentes",
                "url": candidate_url,
            }]
        row = {
            "company": company, "accounts": company_accounts,
            "status": ordered_statuses[0], "status_label": STATUS_LABELS[ordered_statuses[0]],
            "statuses": ordered_statuses,
            "bank_count": sum(account["bank_count"] for account in company_accounts),
            "ledger_count": sum(account["ledger_count"] for account in company_accounts),
            "unassigned_source_count": unassigned[company.pk], "actions": actions,
            "candidate_count": candidate_count, "candidate_url": candidate_url,
        }
        counts["all"] += 1
        for status in statuses:
            counts[status] += 1
        if values["status"] == "all" or values["status"] in statuses:
            rows.append(row)
    try:
        page = Paginator(rows, 25).page(page_number)
    except EmptyPage:
        context["errors"] = ["A página solicitada não está disponível para estes filtros."]
        return context
    context.update(rows=list(page.object_list), page=page, counts=counts)
    return context
