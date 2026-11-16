"""Import retained account configurations without creating usable financial accounts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.models import ClientCompany, ReconciliationAccountCandidate
from apps.hub.portfolio_readiness import prepare_portfolio_readiness
from apps.organizations.models import Organization

VERSION = "reconciliation-account-candidates-v1"
SOURCE_FIELDS = (
    "company_id",
    "source_company_code",
    "chart_company_code",
    "account_code",
    "case_reference",
    "source_key",
    "source_file_sha256",
    "portfolio_file_sha256",
    "source_observed_at",
    "evidence",
)


class AccountCandidateImportError(ValueError):
    """Safe operator message; no retained financial identifiers in exception text."""


def _prepare(
    *, organization: Organization, portfolio_raw: bytes, accounts_raw: bytes, lock: bool = False
) -> dict[str, Any]:
    if not isinstance(portfolio_raw, bytes) or not isinstance(accounts_raw, bytes):
        raise AccountCandidateImportError("Informe os dois perfis originais em bytes.")
    try:
        readiness = prepare_portfolio_readiness(portfolio_raw, accounts_raw)
    except (CatalogEvidenceError, TypeError, KeyError):
        raise AccountCandidateImportError(
            "Confira os perfis originais e sua proveniência."
        ) from None
    # Serialize imports for this office without blocking ordinary FK references in review/audit.
    offices = Organization.objects.all()
    if lock:
        offices = offices.select_for_update(no_key=True)
    try:
        organization = offices.get(pk=organization.pk)
    except Organization.DoesNotExist:
        raise AccountCandidateImportError("O escritório informado não está cadastrado.") from None
    companies_query = ClientCompany.objects.filter(organization=organization).order_by("pk")
    if lock:
        companies_query = companies_query.select_for_update()
    companies = list(companies_query.only("id", "dominio_code"))
    expected = {str(row["company_code"]) for row in readiness["companies"]}
    by_code = {company.dominio_code: company for company in companies}
    if not expected or set(by_code) != expected or len(by_code) != len(companies):
        raise AccountCandidateImportError(
            "Os códigos das empresas do escritório e dos perfis precisam coincidir integralmente."
        )
    sources = readiness["sources"]
    observed = datetime.fromisoformat(sources["configured_accounts"]["observed_at_utc"])
    expected_rows = []
    for company in readiness["companies"]:
        company_evidence = {
            key: value for key, value in company.items() if key != "configured_account_candidates"
        }
        for candidate in company["configured_account_candidates"]:
            expected_rows.append(
                {
                    "company_id": by_code[str(company["company_code"])].pk,
                    "source_company_code": candidate["company_code"],
                    "chart_company_code": candidate["chart_company_code"],
                    "account_code": candidate["account_code"],
                    "source_key": candidate["candidate_key"],
                    "source_file_sha256": sources["configured_accounts"]["input_file_sha256"],
                    "portfolio_file_sha256": sources["portfolio"]["input_file_sha256"],
                    "source_observed_at": observed,
                    "evidence": deepcopy(
                        {
                            "version": VERSION,
                            "sources": sources,
                            "candidate": candidate,
                            "company": company_evidence,
                            "period_start": readiness["period_start"],
                            "period_end_exclusive": readiness["period_end_exclusive"],
                        }
                    ),
                }
            )
    expected_rows.sort(
        key=lambda row: (row["source_company_code"], row["chart_company_code"], row["account_code"])
    )
    # The retained C01-C43 worksheet uses this global numeric order, before any UI filter.
    for position, row in enumerate(expected_rows, 1):
        row["case_reference"] = f"C{position:02}"
    existing_query = ReconciliationAccountCandidate.objects.filter(organization=organization)
    if lock:
        existing_query = existing_query.select_for_update()
    existing = {item.source_key: item for item in existing_query.order_by("pk")}
    expected_keys = {row["source_key"] for row in expected_rows}
    if set(existing) - expected_keys:
        raise AccountCandidateImportError(
            "A fonte diverge das candidatas já registradas; preserve a revisão e confira a origem."
        )
    candidates = []
    for row in expected_rows:
        saved = existing.get(row["source_key"])
        if saved is not None and any(
            getattr(saved, field) != row[field] for field in SOURCE_FIELDS
        ):
            raise AccountCandidateImportError(
                "A proveniência de uma candidata diverge; nenhuma informação será sobrescrita."
            )
        candidates.append(
            {
                **row,
                "company_id": str(row["company_id"]),
                "source_observed_at": observed.isoformat(),
                "candidate_id": str(saved.pk) if saved else None,
                "state": saved.state if saved else ReconciliationAccountCandidate.State.PENDING,
                "disposition": "existing" if saved else "create",
            }
        )
    manifest = {
        "organization_id": str(organization.pk),
        "sources": sources,
        "candidates": [{field: row[field] for field in SOURCE_FIELDS} for row in candidates],
    }
    return {
        "version": VERSION,
        "valid": True,
        "organization_id": str(organization.pk),
        "company_count": len(companies),
        "candidate_count": len(candidates),
        "companies_with_candidates": len({row["company_id"] for row in candidates}),
        "to_create": sum(row["disposition"] == "create" for row in candidates),
        "existing": len(existing),
        "created": 0,
        "applied": False,
        "sources": sources,
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "candidates": candidates,
        "financial_accounts_created": 0,
        "ledger_accounts_created": 0,
        "financial_collection_enabled": False,
        "human_review_performed": False,
    }


def preview_account_candidates(
    *, organization: Organization, portfolio_raw: bytes, accounts_raw: bytes
) -> dict[str, Any]:
    """Check full office coverage, identities and provenance without writing even audit rows."""
    return _prepare(
        organization=organization, portfolio_raw=portfolio_raw, accounts_raw=accounts_raw
    )


@transaction.atomic
def import_account_candidates(
    *,
    organization: Organization,
    portfolio_raw: bytes,
    accounts_raw: bytes,
    request_reference: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Default to preview; explicit apply creates pending candidates only, atomically."""
    if (
        type(apply) is not bool
        or not isinstance(request_reference, str)
        or not 1 <= len(request_reference.strip()) <= 240
        or any(ord(char) < 32 or ord(char) == 127 for char in request_reference)
    ):
        raise AccountCandidateImportError("Informe uma referência técnica válida para a execução.")
    report = _prepare(
        organization=organization,
        portfolio_raw=portfolio_raw,
        accounts_raw=accounts_raw,
        lock=apply,
    )
    if not apply:
        return report
    for row in report["candidates"]:
        if row["disposition"] != "create":
            continue
        values = {field: row[field] for field in SOURCE_FIELDS}
        values["source_observed_at"] = datetime.fromisoformat(values["source_observed_at"])
        candidate = ReconciliationAccountCandidate.objects.create(
            organization=organization, **values
        )
        row["candidate_id"] = str(candidate.pk)
        report["created"] += 1
    report["applied"] = True
    if report["created"]:
        record_event(
            action="hub.reconciliation.account_candidates.imported",
            actor=None,
            organization=organization,
            metadata={
                "request_reference": request_reference.strip(),
                "execution_kind": "technical_import",
                "manifest_sha256": report["manifest_sha256"],
                "company_count": report["company_count"],
                "candidate_count": report["candidate_count"],
                "created": report["created"],
                "source_file_sha256": report["sources"]["configured_accounts"]["input_file_sha256"],
                "portfolio_file_sha256": report["sources"]["portfolio"]["input_file_sha256"],
                "financial_accounts_created": 0,
                "financial_collection_enabled": False,
                "human_review_performed": False,
            },
        )
    return report
