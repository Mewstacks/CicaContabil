"""Which account codes a company can post to (D-380).

A code is accepted when it is an active ``LedgerAccount`` that accepts entries, or
when it exists in the Domínio chart linked to the company in the latest consistent
account discovery and the source does not mark it as synthetic or inactive. Picking
the account and approving the entry stay human; Domínio validates again on import.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.hub.models import ClientCompany, LedgerAccount, ReconciliationDiscoveredChartAccount

# Literal CTCONTAS markers kept by the discovery reader.
SYNTHETIC_TYPE = "S"
INACTIVE_STATUS = "I"


def _catalogue_codes(company: ClientCompany, codes: set[int]) -> set[int]:
    from apps.hub.account_discovery import discovery_company_facts, latest_consistent_discovery

    if not codes:
        return set()
    discovery = latest_consistent_discovery(company.organization)
    if discovery is None:
        return set()
    record = discovery_company_facts(company, discovery)
    if record is None:
        return set()
    owners = [
        item["chart_company_code"]
        for item in record.facts.get("chart_links", [])
        if isinstance(item, dict) and isinstance(item.get("chart_company_code"), int)
    ]
    if not owners:
        return set()
    accepted: set[int] = set()
    rows = ReconciliationDiscoveredChartAccount.objects.filter(
        discovery=discovery,
        organization_id=company.organization_id,
        chart_company_code__in=owners,
        account_code__in=codes,
    ).values_list("account_code", "row")
    for code, row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("account_type_raw") or "").strip().upper() == SYNTHETIC_TYPE:
            continue
        if str(row.get("account_status_raw") or "").strip().upper() == INACTIVE_STATUS:
            continue
        accepted.add(code)
    return accepted


def invalid_account_codes(company: ClientCompany, codes: Iterable[str]) -> set[str]:
    """Return the codes that cannot receive entries for ``company``."""

    wanted = {str(code).strip() for code in codes if str(code or "").strip()}
    if not wanted:
        return set()
    ledger = set(
        LedgerAccount.objects.filter(
            organization_id=company.organization_id,
            company=company,
            code__in=wanted,
            active=True,
            accepts_entries=True,
        ).values_list("code", flat=True)
    )
    remaining = wanted - ledger
    numeric = {
        code: int(code)
        for code in remaining
        if code.isascii() and code.isdecimal() and 0 < int(code) <= 9_999_999
    }
    accepted = _catalogue_codes(company, set(numeric.values()))
    return {code for code in remaining if numeric.get(code) not in accepted}


def account_accepts_entries(company: ClientCompany, code: str) -> bool:
    return not invalid_account_codes(company, [code])
