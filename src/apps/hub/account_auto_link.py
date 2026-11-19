"""D-385: Domínio bank accounts listed in the import form and linked from the OFX."""

from __future__ import annotations

import re
from typing import Any

from django.db.models import Q, QuerySet

from apps.hub.account_discovery_suggest import NOT_CHECKING, plain, suggested_inflow_side
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationLedgerMapping,
)

AUTO_PREFIX = "dominio:"
AUTO_EVIDENCE = "Vínculo automático na importação pelo OFX (D-385)."


class AutoLinkError(ValueError):
    pass


def _owners(record: ReconciliationCompanyDiscovery) -> list[int]:
    return [int(item["chart_company_code"]) for item in record.facts.get("chart_links", [])]


def _bank_accounts(discovery: Any, office: Any, plans: set[int]) -> dict[int, list[Any]]:
    if not plans:
        return {}
    groups = ReconciliationDiscoveredChartAccount.objects.filter(
        discovery=discovery,
        organization=office,
        chart_company_code__in=plans,
        row__account_type_raw="S",
        row__account_name_raw__icontains="banc",
    )
    lookup = Q()
    found = False
    for group in groups:
        name = plain(group.row.get("account_name_raw"))
        prefix = str(group.row.get("classification_raw") or "").strip()
        if prefix and not any(word in name for word in NOT_CHECKING):
            lookup |= Q(chart_company_code=group.chart_company_code) & Q(
                row__classification_raw__startswith=prefix
            )
            found = True
    if not found:
        return {}
    result: dict[int, list[Any]] = {}
    accounts = (
        ReconciliationDiscoveredChartAccount.objects.filter(
            lookup, discovery=discovery, organization=office
        )
        .exclude(row__account_type_raw="S")
        .order_by("chart_company_code", "row__classification_raw", "account_code")
    )
    for account in accounts:
        row = account.row or {}
        if str(row.get("account_status_raw") or "").strip() == "I":
            continue
        if any(word in plain(row.get("account_name_raw")) for word in NOT_CHECKING):
            continue
        result.setdefault(account.chart_company_code, []).append(account)
    return result


def bank_chart_options(companies: QuerySet[ClientCompany]) -> list[dict[str, str]]:
    """Unlinked bank accounts of each company's Domínio chart, as extra select options."""

    from apps.hub.account_discovery import _consistent_company, latest_consistent_discovery

    company = companies.select_related("organization").first()
    if company is None:
        return []
    office = company.organization
    discovery = latest_consistent_discovery(office)
    if discovery is None:
        return []
    records = list(
        ReconciliationCompanyDiscovery.objects.filter(
            discovery=discovery, organization=office, company__in=companies
        )
        .select_related("company")
        .order_by("company__name")
    )
    plans = {plan for record in records for plan in _owners(record)}
    accounts = _bank_accounts(discovery, office, plans)
    linked = {
        (
            str(mapping.scope.get("company_code")),
            int(mapping.scope.get("chart_company_code") or 0),
            int(mapping.scope.get("bank_account_code") or 0),
        )
        for mapping in ReconciliationLedgerMapping.objects.filter(
            organization=office, financial_account__active=True
        ).only("scope")
    }
    options = []
    for record in records:
        if not any(accounts.get(plan) for plan in _owners(record)):
            continue
        record.discovery = discovery
        if not _consistent_company(record):
            continue
        code = str(record.company.dominio_code or "")
        for plan in _owners(record):
            for account in accounts.get(plan, []):
                if (code, plan, account.account_code) in linked:
                    continue
                name = str(account.row.get("account_name_raw") or "Conta do Domínio").strip()
                options.append(
                    {
                        "value": f"{AUTO_PREFIX}{account.pk}",
                        "label": f"{name} · conta {account.account_code} (vincula pelo OFX)",
                        "company_id": str(record.company_id),
                    }
                )
    return options


def link_from_ofx(
    *,
    office: Any,
    company: ClientCompany,
    chart_account_id: str,
    content: bytes,
    actor: Any,
    authorized_companies: QuerySet[ClientCompany],
    request: Any = None,
) -> FinancialAccount:
    """Create the bank link of one chart account from the OFX identity (D-385)."""

    from apps.hub.account_discovery import (
        _consistent_company,
        latest_consistent_discovery,
        prepared_account_facts,
    )
    from apps.hub.account_discovery_review import confirm_discovered_account
    from apps.hub.reconciliation import read_ofx_account_identity

    identity = read_ofx_account_identity(content)
    discovery = latest_consistent_discovery(office)
    record = (
        ReconciliationCompanyDiscovery.objects.filter(
            discovery=discovery, organization=office, company=company
        )
        .select_related("company", "discovery")
        .first()
    )
    if discovery is None or record is None or not _consistent_company(record):
        raise AutoLinkError("O plano de contas desta empresa não está disponível para vincular.")
    account = ReconciliationDiscoveredChartAccount.objects.filter(
        pk=chart_account_id,
        discovery=discovery,
        organization=office,
        chart_company_code__in=_owners(record),
    ).first()
    if account is None:
        raise AutoLinkError("Escolha uma conta do plano desta empresa.")
    month = max(identity.last_date.strftime("%Y-%m"), "2026-09")
    prepared = prepared_account_facts(record, account, month=month)
    if not prepared.get("valid") or prepared.get("blocking_reason"):
        raise AutoLinkError("Esta conta precisa de revisão antes do vínculo; nada foi importado.")
    existing = prepared.get("existing_financial_account_id")
    if prepared.get("collection_ready") and existing:
        return FinancialAccount.objects.get(pk=existing, company=company)
    branches = [int(code) for code in prepared.get("branches") or []]
    own = int(company.dominio_code) if re.fullmatch(r"[0-9]+", company.dominio_code or "") else 0
    branch = own if own in branches or not branches else branches[0]
    values: dict[str, Any] = {
        "bank_code": identity.bank_id,
        "account_reference": identity.account_reference,
        "bank_inflow_side": suggested_inflow_side(account.row or {}) or "debit",
        "branch_code": branch,
        "chart_owner_confirmed": True,
        "branch_scope_confirmed": True,
        "bank_association_confirmed": True,
        "account_active_and_postable": True,
    }
    confirmed = {name: values[name] for name in prepared.get("pending_fields", [])}
    confirmed["evidence_reference"] = AUTO_EVIDENCE
    result = confirm_discovered_account(
        company_discovery=record,
        chart_account=account,
        month=month,
        actor=actor,
        authorized_companies=authorized_companies,
        expected_revision=str(prepared.get("revision") or ""),
        confirmed_data=confirmed,
        request=request,
    )
    return result["financial_account"]
