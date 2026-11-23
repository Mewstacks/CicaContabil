"""D-385: Domínio bank accounts listed in the import form and linked from the OFX."""

from __future__ import annotations

import re
from datetime import timedelta
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
    month: str | None = None,
    linked_scope: dict[str, Any] | None = None,
) -> FinancialAccount:
    """Create the bank link of one chart account from the OFX identity (D-385).

    ``month``/``linked_scope`` (D-396) confirm one more month of an existing link with the
    branch and bank side that link already uses.
    """

    from apps.hub.account_discovery import (
        _consistent_company,
        latest_consistent_discovery,
        prepared_account_facts,
    )
    from apps.hub.account_discovery_review import confirm_discovered_account
    from apps.hub.reconciliation import read_ofx_account_identity

    identity = read_ofx_account_identity(content)
    refuse_foreign_account(office, company, identity.account_reference)  # D-397
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
    month = month or max(identity.last_date.strftime("%Y-%m"), "2026-09")
    prepared = prepared_account_facts(record, account, month=month)
    if not prepared.get("valid") or prepared.get("blocking_reason"):
        raise AutoLinkError("Esta conta precisa de revisão antes do vínculo; nada foi importado.")
    existing = prepared.get("existing_financial_account_id")
    if prepared.get("collection_ready") and existing:
        return FinancialAccount.objects.get(pk=existing, company=company)
    branches = [int(code) for code in prepared.get("branches") or []]
    own = int(company.dominio_code) if re.fullmatch(r"[0-9]+", company.dominio_code or "") else 0
    branch = own if own in branches or not branches else branches[0]
    inflow_side = suggested_inflow_side(account.row or {}) or "debit"
    if linked_scope is not None:
        branch = int(linked_scope["branch_code"])
        inflow_side = str(linked_scope["bank_inflow_side"])
    values: dict[str, Any] = {
        "bank_code": identity.bank_id,
        "account_reference": identity.account_reference,
        "bank_inflow_side": inflow_side,
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


def ofx_months(content: bytes) -> list[str]:
    """Every month the OFX covers, from September/2026 on (D-396)."""
    from apps.hub.reconciliation import read_ofx_account_identity

    identity = read_ofx_account_identity(content)
    months, current = [], identity.first_date.replace(day=1)
    while current <= identity.last_date:
        if current.strftime("%Y-%m") >= "2026-09":
            months.append(current.strftime("%Y-%m"))
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        if len(months) > 24:
            break
    return months


def confirm_ofx_months(
    *,
    office: Any,
    account: FinancialAccount,
    content: bytes,
    actor: Any,
    authorized_companies: QuerySet[ClientCompany],
    request: Any = None,
) -> list[str]:
    """D-396: confirm the months of this OFX for a link made by the import itself (D-385) or of
    a direct-use office, so the Razão of every covered month can be requested."""
    from apps.hub.account_discovery import latest_consistent_discovery
    from apps.hub.account_discovery_review import KIND
    from apps.hub.direct_use import direct_use_enabled
    from apps.hub.ledger_requests import discovery_mapping_month_allowed
    from apps.hub.reconciliation import read_ofx_account_identity

    mapping = ReconciliationLedgerMapping.objects.filter(financial_account=account).first()
    if mapping is None:
        return []
    provenance = mapping.provenance
    if not isinstance(provenance, dict) or provenance.get("kind") != KIND:
        return []
    automatic = any(
        isinstance(item, dict) and item.get("note") == AUTO_EVIDENCE
        for item in provenance.get("confirmations", [])
    )
    if not (automatic or direct_use_enabled(office)):
        return []
    if read_ofx_account_identity(content).account_reference != account.account_reference:
        return []
    discovery = latest_consistent_discovery(office)
    chart = ReconciliationDiscoveredChartAccount.objects.filter(
        discovery=discovery,
        organization=office,
        chart_company_code=mapping.scope.get("chart_company_code"),
        account_code=mapping.scope.get("bank_account_code"),
    ).first()
    if discovery is None or chart is None:
        return []
    confirmed = []
    for month in ofx_months(content):
        mapping.refresh_from_db()
        if discovery_mapping_month_allowed(account, mapping, month):
            continue
        link_from_ofx(
            office=office,
            company=account.company,
            chart_account_id=str(chart.pk),
            content=content,
            actor=actor,
            authorized_companies=authorized_companies,
            request=request,
            month=month,
            linked_scope=mapping.scope,
        )
        confirmed.append(month)
    return confirmed


STATEMENT_PREFIX = "extrato:"


def statement_only_options(
    companies: QuerySet[ClientCompany], chart_options: list[dict[str, str]]
) -> list[dict[str, str]]:
    """D-393: companies without a bank account in the Domínio chart (or without a chart)."""

    from apps.hub.direct_use import direct_use_enabled

    company = companies.select_related("organization").first()
    if company is None or not direct_use_enabled(company.organization):
        return []
    with_chart = {item["company_id"] for item in chart_options}
    # D-397 item 7: a company already linked to the Razão keeps using its bank account.
    with_chart |= {
        str(pk)
        for pk in FinancialAccount.objects.filter(
            company__in=companies, active=True
        ).exclude(ledger_code="").values_list("company_id", flat=True)
    }
    return [
        {
            "value": f"{STATEMENT_PREFIX}{item.pk}",
            "label": "Conta do extrato, lida do OFX (sem Razão)",
            "company_id": str(item.pk),
        }
        for item in companies.order_by("name")
        if str(item.pk) not in with_chart
    ]


def link_statement_only(
    *, office: Any, company: ClientCompany, content: bytes, actor: Any, request: Any = None
) -> FinancialAccount:
    """D-393: bank account identified only by the OFX, with no ledger code nor Razão mapping."""

    from apps.audit.services import record_event
    from apps.hub.direct_use import direct_use_enabled
    from apps.hub.reconciliation import read_ofx_account_identity

    if not direct_use_enabled(office) or company.organization_id != office.pk:
        raise AutoLinkError("Escolha uma conta da lista.")
    identity = read_ofx_account_identity(content)
    if not identity.account_reference:
        raise AutoLinkError("O OFX não informa a conta bancária; nada foi importado.")
    refuse_foreign_account(office, company, identity.account_reference)  # D-397
    existing = FinancialAccount.objects.filter(
        organization=office, company=company, account_reference=identity.account_reference
    ).first()
    if existing is not None:
        if not existing.active:
            raise AutoLinkError("Esta conta está inativa nesta empresa; nada foi importado.")
        return existing
    label = " ".join(
        part
        for part in (
            f"Banco {identity.bank_id}" if identity.bank_id else "Banco",
            identity.branch_id,
            identity.account_id,
        )
        if part
    )
    account = FinancialAccount.objects.create(
        organization=office,
        company=company,
        name=f"{label} (extrato)"[:160],
        bank_code=identity.bank_id[:20],
        account_reference=identity.account_reference,
        ledger_code="",
    )
    record_event(
        action="hub.reconciliation.statement_account_created",
        actor=actor,
        organization=office,
        target=account,
        request=request,
        metadata={"decision": "D-393", "company_id": str(company.pk)},
    )
    return account


def refuse_foreign_account(office: Any, company: ClientCompany, account_reference: str) -> None:
    """D-397: an OFX whose bank account belongs to another company of the office is refused."""
    if not account_reference:
        return
    other = (
        FinancialAccount.objects.filter(organization=office, account_reference=account_reference)
        .exclude(company=company)
        .select_related("company")
        .first()
    )
    if other is not None:
        raise AutoLinkError(
            f"Este extrato é da conta bancária já cadastrada na empresa {other.company.name}. "
            "Confira a empresa escolhida; nada foi importado."
        )
