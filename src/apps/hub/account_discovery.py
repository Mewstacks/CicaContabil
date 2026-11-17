"""Atomic catalogue preparation, without inventing bank mappings or human review."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record_event
from apps.hub.account_candidates import AccountCandidateImportError, _prepare
from apps.hub.account_discovery_contract import (
    SCRIPT_SHA,
    Invalid,
    decode_discovery,
    digest,
    validate_chart_row,
)
from apps.hub.account_source_contract import canonical, scope_hash
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    ReconciliationAccountCandidate,
    ReconciliationAccountDiscovery,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationLedgerMapping,
)
from apps.organizations.models import Organization

VERSION = "reconciliation-account-discovery-v1"


class AccountDiscoveryError(ValueError):
    """Safe diagnostics; never source names, company codes or bank identifiers."""


def _needs_storage_codec(value: Any) -> bool:
    if isinstance(value, str):
        return "\0" in value
    if isinstance(value, dict):
        return any(_needs_storage_codec(item) for item in value.values())
    if isinstance(value, list):
        return any(_needs_storage_codec(item) for item in value)
    return False


def _company_plans(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    counts = Counter(row["chart_company_code"] for row in snapshot["chart_accounts"])
    usage: dict[int, list[dict[str, Any]]] = defaultdict(list)
    configured: dict[int, list[dict[str, Any]]] = defaultdict(list)
    equivalent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for name, target in (
        ("observed_chart_usage", usage),
        ("configured_accounts", configured),
        ("equivalent_accounts", equivalent),
    ):
        for row in snapshot[name]:
            target[row["company_code"]].append(row)
    result = []
    for company in sorted(snapshot["companies"], key=lambda item: item["company_code"]):
        code = company["company_code"]
        owners = {code}
        if company["codi_pad_raw"]:
            owners.add(company["codi_pad_raw"])
        owners.update(
            row["chart_company_code"] for row in usage[code] + configured[code] + equivalent[code]
        )
        links = []
        for owner in sorted(owners):
            observed = [
                {key: row[key] for key in ("year", "month", "branch_code", "entry_count")}
                for row in usage[code]
                if row["chart_company_code"] == owner
            ]
            configured_codes = sorted(
                row["account_code"]
                for row in configured[code]
                if row["chart_company_code"] == owner
            )
            equivalent_codes = sorted(
                row["account_code"]
                for row in equivalent[code]
                if row["chart_company_code"] == owner
            )
            sources = []
            for present, kind in (
                (owner == code, "own_code_option"),
                (owner == company["codi_pad_raw"], "parameter_option"),
                (bool(observed), "observed_usage"),
                (bool(configured_codes), "configured_reference"),
                (bool(equivalent_codes), "equivalent_reference"),
            ):
                if present:
                    sources.append(kind)
            links.append(
                dict(
                    chart_company_code=owner,
                    sources=sources,
                    account_count=counts[owner],
                    observed_usage=sorted(
                        observed, key=lambda row: (row["year"], row["month"], row["branch_code"])
                    ),
                    configured_account_codes=configured_codes,
                    equivalent_account_codes=equivalent_codes,
                )
            )
        gaps = []
        if company["configuration_rows"] == 0:
            gaps.append("missing_accounting_parameters")
        if not usage[code]:
            gaps.append("no_observed_usage")
        if len({row["chart_company_code"] for row in usage[code]}) > 1:
            gaps.append("multiple_observed_plans")
        if len({row["branch_code"] for row in usage[code]}) > 1:
            gaps.append("multiple_observed_branches")
        has_accounts = any(link["account_count"] for link in links)
        has_reference = any(usage[code] or configured[code] or equivalent[code])
        state = "catalogued" if has_reference and has_accounts else "options_only"
        if not has_accounts:
            state = "no_accounts"
            gaps.append("no_catalogue_accounts")
        facts = dict(
            company=company,
            chart_links=links,
            source_window={
                "start": "2026-09-01",
                "end_exclusive": "2026-12-01",
            },
        )
        result.append(
            dict(
                source_company_code=code,
                coverage_state=state,
                facts=facts,
                gaps=gaps,
                facts_sha256=digest({"facts": facts, "gaps": gaps, "state": state}),
            )
        )
    return result


def _proof_signature(proof: dict[str, Any]) -> str:
    return digest({key: value for key, value in proof.items() if key != "integrity_sha256"})


def _stored_catalogue_digest(discovery: ReconciliationAccountDiscovery) -> str | None:
    """Check all retained accounts without materializing a second large list."""
    checksum = hashlib.sha256(b"[")
    first = True
    values = discovery.chart_accounts.order_by("chart_company_code", "account_code").values_list(
        "organization_id", "chart_company_code", "account_code", "row", "row_sha256"
    )
    for organization_id, owner, code, row, row_sha in values.iterator(chunk_size=500):
        validate_chart_row(row)
        if (
            organization_id != discovery.organization_id
            or owner != row["chart_company_code"]
            or code != row["account_code"]
            or row_sha != digest(row)
        ):
            return None
        if not first:
            checksum.update(b",")
        checksum.update(canonical(row).encode())
        first = False
    checksum.update(b"]")
    return checksum.hexdigest()


def _consistent_discovery(discovery: ReconciliationAccountDiscovery, *, deep: bool = False) -> bool:
    try:
        proof = discovery.provenance
        if not (
            proof["version"] == VERSION
            and proof["execution_kind"] == "technical_preparation"
            and proof["human_reviewed"] is False
            and proof["financial_collection_enabled"] is False
            and proof["integrity_sha256"] == _proof_signature(proof)
            and proof["source_file_sha256"] == discovery.source_file_sha256
            and proof["source_size_bytes"] == discovery.source_size_bytes
            and proof["source_observed_at"] == discovery.source_observed_at.isoformat()
            and discovery.script_sha256 == SCRIPT_SHA
            and proof["source_metadata_sha256"] == digest(discovery.source_metadata)
            and discovery.source_metadata["script_sha256"] == SCRIPT_SHA
            and discovery.source_metadata["company_codes_sha256"] == discovery.company_codes_sha256
            and len(proof["company_facts"]) == discovery.company_count
            and discovery.company_coverage.count() == discovery.company_count
            and discovery.chart_accounts.count() == discovery.chart_account_count
        ):
            return False
        codes = list(
            ClientCompany.objects.filter(organization_id=discovery.organization_id).values_list(
                "dominio_code", flat=True
            )
        )
        if len(codes) != discovery.company_count or any(
            not re.fullmatch(r"[1-9][0-9]*", code) for code in codes
        ):
            return False
        if scope_hash(int(code) for code in codes) != discovery.company_codes_sha256:
            return False
        return not deep or (
            proof["source_data_sha256"] == digest(discovery.source_data)
            and proof["chart_rows_sha256"] == _stored_catalogue_digest(discovery)
        )
    except (AttributeError, TypeError, KeyError, ValueError, Invalid):
        return False


def latest_consistent_discovery(
    organization: Organization,
) -> ReconciliationAccountDiscovery | None:
    """Never fall back past a conflicting/corrupted latest observation."""
    latest = (
        ReconciliationAccountDiscovery.objects.defer("source_data")
        .filter(organization=organization)
        .first()
    )
    if latest is None:
        return None
    rows = list(
        ReconciliationAccountDiscovery.objects.defer("source_data")
        .filter(
            organization=organization,
            source_observed_at=latest.source_observed_at,
        )
        .order_by("source_file_sha256")
    )
    if not all(_consistent_discovery(row) for row in rows):
        return None
    if len({row.provenance["content_sha256"] for row in rows}) != 1:
        return None
    return rows[0]


def _consistent_company(row: ReconciliationCompanyDiscovery) -> bool:
    try:
        row.clean()
        return bool(
            row.discovery.provenance["company_facts"][str(row.source_company_code)]
            == row.facts_sha256
        )
    except (AttributeError, TypeError, KeyError, ValueError, ValidationError):
        return False


def discovery_company_facts(
    company: ClientCompany, discovery: ReconciliationAccountDiscovery | None = None
) -> ReconciliationCompanyDiscovery | None:
    discovery = discovery or latest_consistent_discovery(company.organization)
    if discovery is None or discovery.organization_id != company.organization_id:
        return None
    row = (
        ReconciliationCompanyDiscovery.objects.select_related("discovery", "company")
        .defer("discovery__source_data")
        .filter(
            organization_id=company.organization_id,
            discovery=discovery,
            company=company,
        )
        .first()
    )
    return row if row is not None and _consistent_company(row) else None


def prepared_account_facts(
    company_discovery: ReconciliationCompanyDiscovery,
    chart_account: ReconciliationDiscoveredChartAccount,
    *,
    month: str,
) -> dict[str, Any]:
    """Combine one company/one shared catalogue account, with month-scoped evidence."""
    invalid = dict(
        valid=False, reason="source_unavailable", pending_fields=[], collection_ready=False
    )
    try:
        if not isinstance(month, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", month):
            return {**invalid, "reason": "invalid_month"}
        selected = date.fromisoformat(month + "-01")
        if selected < date(2026, 9, 1):
            return {**invalid, "reason": "invalid_month"}
        latest = latest_consistent_discovery(company_discovery.organization)
        if (
            latest is None
            or latest.pk != company_discovery.discovery_id
            or chart_account.discovery_id != latest.pk
            or chart_account.organization_id != company_discovery.organization_id
            or not _consistent_company(company_discovery)
        ):
            return invalid
        validate_chart_row(chart_account.row)
        chart_account.clean()
        link = next(
            (
                item
                for item in company_discovery.facts["chart_links"]
                if item["chart_company_code"] == chart_account.chart_company_code
            ),
            None,
        )
        if link is None:
            return invalid
        observed = [
            item
            for item in link["observed_usage"]
            if item["year"] == selected.year and item["month"] == selected.month
        ]
        kinds = []
        for kind, field in (
            ("configured_reference", "configured_account_codes"),
            ("equivalent_reference", "equivalent_account_codes"),
        ):
            if chart_account.account_code in link[field]:
                kinds.append(kind)
        if observed:
            kinds.append("observed_usage")
        branches = sorted({item["branch_code"] for item in observed})
        known = {
            key: chart_account.row[key]
            for key in (
                "chart_company_code",
                "account_code",
                "classification_raw",
                "account_type_raw",
                "account_status_raw",
                "inactive_on_raw",
            )
        }
        known.update(
            name=chart_account.row["account_name_raw"],
            company_code=company_discovery.source_company_code,
        )
        pending = [
            "bank_code",
            "account_reference",
            "bank_inflow_side",
            "bank_association_confirmed",
            "account_active_and_postable",
        ]
        if not observed:
            pending.append("chart_owner_confirmed")
        if len(branches) == 1 and branches[0] > 0:
            known["branch_code"] = branches[0]
        else:
            pending.append("branch_code")
            if len(branches) > 1:
                pending.append("branch_scope_confirmed")
        candidate = ReconciliationAccountCandidate.objects.filter(
            organization_id=company_discovery.organization_id,
            company_id=company_discovery.company_id,
            chart_company_code=chart_account.chart_company_code,
            account_code=chart_account.account_code,
        ).first()
        accounts = list(
            FinancialAccount.objects.filter(
                organization_id=company_discovery.organization_id,
                company_id=company_discovery.company_id,
                ledger_code=str(chart_account.account_code),
                active=True,
            )
        )
        existing_id = None
        mapping_revision = None
        collection_ready = False
        prior_review_proof = None
        if len(accounts) == 1:
            from apps.hub.ledger_requests import _mapping, discovery_mapping_month_allowed

            mapping = _mapping(accounts[0])
            stored_mapping = ReconciliationLedgerMapping.objects.filter(
                financial_account=accounts[0]
            ).first()
            fields = mapping.get("fields", {})
            if (
                mapping["ready"]
                and fields.get("chart_company_code") == chart_account.chart_company_code
            ):
                existing_id = str(accounts[0].pk)
                mapping_revision = mapping["revision"]
                collection_ready = discovery_mapping_month_allowed(
                    accounts[0], stored_mapping, month
                )
                if collection_ready:
                    known.update(
                        bank_code=accounts[0].bank_code,
                        account_reference=accounts[0].account_reference,
                        bank_inflow_side=fields["bank_inflow_side"],
                        branch_code=fields["branch_code"],
                    )
                    pending = []
                elif stored_mapping is not None:
                    previous = stored_mapping.provenance
                    confirmations = previous.get("confirmations", [])
                    valid_previous = [
                        item
                        for item in confirmations
                        if (
                            isinstance(item, dict)
                            and isinstance(item.get("month"), str)
                            and discovery_mapping_month_allowed(
                                accounts[0], stored_mapping, item["month"]
                            )
                        )
                    ]
                    confirmed = {
                        field
                        for item in valid_previous
                        for field in item.get("confirmed_fields", [])
                    }
                    banking = {
                        "bank_code",
                        "account_reference",
                        "bank_inflow_side",
                        "bank_association_confirmed",
                    }
                    if banking <= confirmed:
                        known.update(
                            bank_code=accounts[0].bank_code,
                            account_reference=accounts[0].account_reference,
                            bank_inflow_side=fields["bank_inflow_side"],
                            bank_association_confirmed=True,
                        )
                        pending = [field for field in pending if field not in banking]
                        prior_review_proof = dict(
                            mapping_id=str(stored_mapping.pk),
                            mapping_revision=mapping_revision,
                            fields=sorted(banking),
                        )
                    if "account_active_and_postable" in confirmed:
                        for item in valid_previous:
                            previous_chart = ReconciliationDiscoveredChartAccount.objects.filter(
                                pk=item["source_identity"]["chart_account_id"],
                                organization_id=company_discovery.organization_id,
                            ).first()
                            if previous_chart is not None and all(
                                previous_chart.row[key] == chart_account.row[key]
                                for key in (
                                    "account_type_raw",
                                    "account_status_raw",
                                    "inactive_on_raw",
                                )
                            ):
                                known["account_active_and_postable"] = True
                                pending = [
                                    field
                                    for field in pending
                                    if field != "account_active_and_postable"
                                ]
                                break
        proof = dict(
            execution_kind="technical_preparation",
            human_reviewed=False,
            source_file_sha256=latest.source_file_sha256,
            catalogue_row_sha256=chart_account.row_sha256,
            company_facts_sha256=company_discovery.facts_sha256,
            name="CTCONTAS.nome_cta",
            chart_link=dict(kinds=kinds, month=month, proven=bool(observed)),
        )
        source_revision = digest(
            {
                "discovery_id": str(latest.pk),
                "company_id": str(company_discovery.company_id),
                "chart_account_id": str(chart_account.pk),
                "month": month,
                "proof": proof,
            }
        )
        if prior_review_proof is not None:
            proof["previous_human_review"] = prior_review_proof
        old_candidate_revision = None
        if candidate is not None:
            from apps.hub.account_candidate_review import candidate_revision

            old_candidate_revision = candidate_revision(candidate)
        blocking_reason = None
        if candidate is not None and candidate.state == "dismissed":
            blocking_reason = "previously_dismissed_candidate"
        elif 0 in branches and not collection_ready:
            blocking_reason = "unsupported_observed_branch"
        result = dict(
            valid=True,
            month=month,
            known_fields=known,
            proof=proof,
            pending_fields=pending,
            branches=branches,
            observed_periods=sorted(
                {f"{item['year']:04d}-{item['month']:02d}" for item in link["observed_usage"]}
            ),
            existing_candidate_id=str(candidate.pk) if candidate else None,
            existing_candidate_state=candidate.state if candidate else None,
            existing_financial_account_id=existing_id,
            collection_ready=collection_ready,
            source_revision=source_revision,
            blocking_reason=blocking_reason,
        )
        result["revision"] = digest(
            {
                **result,
                "discovery_id": str(latest.pk),
                "company_id": str(company_discovery.company_id),
                "chart_account_id": str(chart_account.pk),
                "mapping_revision": mapping_revision,
                "candidate_revision": old_candidate_revision,
                "existing_accounts": [
                    {
                        "id": str(account.pk),
                        "name": account.name,
                        "bank_code": account.bank_code,
                        "account_reference": account.account_reference,
                        "ledger_code": account.ledger_code,
                        "active": account.active,
                    }
                    for account in accounts
                ],
            }
        )
        return result
    except (AttributeError, KeyError, TypeError, ValueError, Invalid, ValidationError):
        return invalid


@transaction.atomic
def import_account_discovery(
    *,
    organization: Organization,
    portfolio_raw: bytes,
    accounts_raw: bytes,
    discovery_raw: bytes,
    expected_sha256: str,
    expected_size_bytes: int,
    request_reference: str,
    apply: bool = False,
    expected_manifest: str | None = None,
) -> dict[str, Any]:
    """Preview first; add only technical evidence, as one atomic/idempotent office operation."""
    if (
        type(apply) is not bool
        or not isinstance(request_reference, str)
        or not 1 <= len(request_reference.strip()) <= 240
        or any(ord(char) < 32 or ord(char) == 127 for char in request_reference)
    ):
        raise AccountDiscoveryError("Informe uma referência técnica válida.")
    try:
        original = _prepare(
            organization=organization,
            portfolio_raw=portfolio_raw,
            accounts_raw=accounts_raw,
            lock=apply,
        )
        if original["to_create"]:
            raise AccountDiscoveryError("Registre as candidatas da origem antes da descoberta.")
        companies = list(ClientCompany.objects.filter(organization=organization).order_by("pk"))
        by_code = {int(company.dominio_code): company for company in companies}
        portfolio_sha = original["sources"]["portfolio"]["input_file_sha256"]
        data = decode_discovery(
            discovery_raw,
            expected_sha256=expected_sha256,
            expected_size_bytes=expected_size_bytes,
            companies=set(by_code),
            portfolio_sha256=portfolio_sha,
        )
    except (Invalid, AccountCandidateImportError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, AccountDiscoveryError):
            raise
        raise AccountDiscoveryError(
            "Confira arquivos, hashes e escopo original da descoberta."
        ) from None
    observed = datetime.fromisoformat(data["observed_at_utc"].replace("Z", "+00:00"))
    if _needs_storage_codec(data):
        raise AccountDiscoveryError(
            "A fonte contém U+0000 e exige representação reversível antes da persistência. "
            "O arquivo original deve ser preservado; nada foi preparado."
        )
    snapshot = data["snapshot"]
    plans = _company_plans(snapshot)
    metadata = {key: value for key, value in data.items() if key != "snapshot"}
    source_data = {key: value for key, value in snapshot.items() if key != "chart_accounts"}
    charts = sorted(
        snapshot["chart_accounts"], key=lambda row: (row["chart_company_code"], row["account_code"])
    )
    content_sha = digest(data)
    proof = dict(
        version=VERSION,
        execution_kind="technical_preparation",
        human_reviewed=False,
        financial_collection_enabled=False,
        source_file_sha256=expected_sha256,
        source_size_bytes=expected_size_bytes,
        source_observed_at=observed.isoformat(),
        source_metadata_sha256=digest(metadata),
        source_data_sha256=digest(source_data),
        content_sha256=content_sha,
        chart_rows_sha256=digest(charts),
        company_facts={str(row["source_company_code"]): row["facts_sha256"] for row in plans},
    )
    proof["integrity_sha256"] = _proof_signature(proof)
    values = dict(
        organization=organization,
        source_file_sha256=expected_sha256,
        source_size_bytes=expected_size_bytes,
        source_observed_at=observed,
        script_sha256=SCRIPT_SHA,
        portfolio_file_sha256=portfolio_sha,
        company_codes_sha256=scope_hash(by_code),
        company_count=len(companies),
        chart_account_count=len(charts),
        source_metadata=metadata,
        source_data=source_data,
        provenance=proof,
    )
    existing = ReconciliationAccountDiscovery.objects.filter(
        organization=organization, source_file_sha256=expected_sha256
    ).first()
    if existing is not None:
        if any(getattr(existing, field) != value for field, value in values.items()):
            raise AccountDiscoveryError("A descoberta registrada diverge; nada foi substituído.")
        stored_charts = list(existing.chart_accounts.order_by("chart_company_code", "account_code"))
        stored_companies = list(
            existing.company_coverage.select_related("company", "discovery")
            .defer("discovery__source_data")
            .order_by("source_company_code")
        )
        if (
            not _consistent_discovery(existing, deep=True)
            or [row.row for row in stored_charts] != charts
            or any(
                row.row_sha256 != digest(row.row)
                or row.organization_id != organization.pk
                or row.chart_company_code != row.row["chart_company_code"]
                or row.account_code != row.row["account_code"]
                for row in stored_charts
            )
            or len(stored_companies) != len(plans)
            or any(not _consistent_company(row) for row in stored_companies)
        ):
            raise AccountDiscoveryError(
                "A descoberta registrada perdeu integridade; nada foi substituído."
            )
    for same_time in ReconciliationAccountDiscovery.objects.filter(
        organization=organization, source_observed_at=observed
    ):
        if (
            not _consistent_discovery(same_time)
            or same_time.provenance["content_sha256"] != content_sha
        ):
            raise AccountDiscoveryError("Fontes do mesmo horário divergem; confira a descoberta.")
    manifest = digest(
        {
            "source": expected_sha256,
            "proof": proof,
            "companies": {str(code): str(company.pk) for code, company in by_code.items()},
        }
    )
    if expected_manifest is not None and (
        not isinstance(expected_manifest, str)
        or not hmac.compare_digest(expected_manifest, manifest)
    ):
        raise AccountDiscoveryError("A prévia mudou; confira o lote antes de aplicar.")
    report = dict(
        version=VERSION,
        valid=True,
        applied=apply,
        source_file_sha256=expected_sha256,
        source_size_bytes=expected_size_bytes,
        manifest_sha256=manifest,
        company_count=len(companies),
        chart_account_count=len(charts),
        chart_owner_count=len(snapshot["chart_owners"]),
        coverage_counts=dict(Counter(row["coverage_state"] for row in plans)),
        existing=1 if existing else 0,
        to_create=0 if existing else 1,
        created=0,
        chart_accounts_created=0,
        company_coverage_created=0,
        financial_accounts_created=0,
        human_review_performed=False,
        financial_collection_enabled=False,
    )
    if apply and existing is None:
        discovery = ReconciliationAccountDiscovery.objects.create(
            **values, request_reference=request_reference.strip()
        )
        ReconciliationDiscoveredChartAccount.objects.insert_validated(
            [
                ReconciliationDiscoveredChartAccount(
                    organization=organization,
                    discovery=discovery,
                    chart_company_code=row["chart_company_code"],
                    account_code=row["account_code"],
                    row=row,
                    row_sha256=digest(row),
                )
                for row in charts
            ],
            batch_size=500,
        )
        for row in plans:
            ReconciliationCompanyDiscovery.objects.create(
                organization=organization,
                discovery=discovery,
                company=by_code[row["source_company_code"]],
                **row,
            )
        report.update(
            created=1, chart_accounts_created=len(charts), company_coverage_created=len(plans)
        )
        record_event(
            action="hub.reconciliation.account_discovery.imported",
            organization=organization,
            actor=None,
            metadata={key: value for key, value in report.items() if key != "coverage_counts"},
        )
    return report
