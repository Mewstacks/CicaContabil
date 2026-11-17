"""Append technical cadastral evidence without modifying candidates or human decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.account_candidates import SOURCE_FIELDS, AccountCandidateImportError, _prepare
from apps.hub.account_source_contract import (
    CONFIG_KEY,
    SCRIPT_SHA,
    Invalid,
    decode_account_details,
    validate_configured_row,
)
from apps.hub.models import ReconciliationAccountCandidate, ReconciliationAccountSourceDetail
from apps.organizations.models import Organization

VERSION = "reconciliation-account-source-details-v1"


class AccountSourceDetailError(ValueError):
    """Safe message without source identifiers, names or bank references."""


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        ).encode()
    ).hexdigest()


def _fingerprint(candidate: ReconciliationAccountCandidate) -> str:
    return _hash({key: getattr(candidate, key) for key in SOURCE_FIELDS})


def _facts(values: dict[str, Any]) -> str:
    return _hash({key: value for key, value in values.items() if key != "facts_sha256"})


def _consistent(
    detail: ReconciliationAccountSourceDetail, candidate: ReconciliationAccountCandidate
) -> bool:
    try:
        validate_configured_row(detail.row)
        proof = detail.provenance
        return bool(
            detail.organization_id == candidate.organization_id
            and candidate.company.organization_id == candidate.organization_id
            and candidate.company.dominio_code == str(candidate.source_company_code)
            and detail.candidate_id == candidate.pk
            and detail.candidate_source_sha256 == candidate.source_file_sha256
            and detail.portfolio_file_sha256 == candidate.portfolio_file_sha256
            and proof["version"] == VERSION
            and proof["execution_kind"] == "technical_preparation"
            and proof["script_sha256"] == SCRIPT_SHA
            and proof["candidate_fingerprint"] == _fingerprint(candidate)
            and proof["human_reviewed"] is False
            and proof["bank_mapping_inferred"] is False
            and proof["financial_collection_enabled"] is False
            and proof["row_sha256"] == _hash(detail.row)
            and proof["facts_sha256"] == _facts(proof)
            and proof["source_file_sha256"] == detail.source_file_sha256
            and proof["source_observed_at"] == detail.source_observed_at.isoformat()
            and proof["source_size_bytes"] == detail.source_size_bytes
            and tuple(detail.row[key] for key in CONFIG_KEY)
            == (candidate.source_company_code, candidate.chart_company_code, candidate.account_code)
            and detail.row["catalogue_matches"] == 1
            and detail.row["catalogue_account_code"] == candidate.account_code
            and isinstance(detail.row["account_name_raw"], str)
            and isinstance(proof["company_counts"], dict)
            and set(proof["company_counts"])
            == {"cash_accounts", "bank_references", "integration_account_configurations"}
            and all(type(n) is int and n >= 0 for n in proof["company_counts"].values())
        )
    except (AttributeError, KeyError, TypeError, ValueError, Invalid):
        return False


def latest_consistent_source_detail(
    candidate: ReconciliationAccountCandidate,
) -> ReconciliationAccountSourceDetail | None:
    """Latest observed source, never insertion order or fallback past a conflicting latest source.

    Different observation times select the newest. At the same time identical facts
    may use the lexically first hash; conflicting facts or an invalid latest row hide
    the complement instead of presenting an arbitrary name.
    """
    rows = list(
        ReconciliationAccountSourceDetail.objects.filter(candidate_id=candidate.pk).order_by(
            "-source_observed_at", "source_file_sha256"
        )
    )
    if not rows:
        return None
    latest = [row for row in rows if row.source_observed_at == rows[0].source_observed_at]
    if not all(_consistent(row, candidate) for row in latest):
        return None
    signatures = {
        _hash({"row": row.row, "counts": row.provenance["company_counts"]}) for row in latest
    }
    return latest[0] if len(signatures) == 1 else None


@transaction.atomic
def import_account_source_details(
    *,
    organization: Organization,
    portfolio_raw: bytes,
    accounts_raw: bytes,
    details_raw: bytes,
    expected_sha256: str,
    expected_size_bytes: int,
    request_reference: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Preview by default; serialize complete office verification and all inserts atomically."""
    if (
        type(apply) is not bool
        or not isinstance(request_reference, str)
        or not 1 <= len(request_reference.strip()) <= 240
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in request_reference)
    ):
        raise AccountSourceDetailError("Informe uma referência técnica válida para a preparação.")
    try:
        original = _prepare(
            organization=organization,
            portfolio_raw=portfolio_raw,
            accounts_raw=accounts_raw,
            lock=apply,
        )
        if original["to_create"] or not original["candidate_count"]:
            raise AccountSourceDetailError("As candidatas originais precisam estar registradas.")
        candidates = list(
            ReconciliationAccountCandidate.objects.filter(organization=organization)
            .select_related("company")
            .order_by("pk")
        )
        # _prepare verifies the full original company set and every SOURCE_FIELD.
        companies = {
            int(code)
            for code in organization.clientcompany_set.values_list("dominio_code", flat=True)
        }
        data = decode_account_details(
            details_raw,
            expected_sha256=expected_sha256,
            expected_size_bytes=expected_size_bytes,
            companies=companies,
            portfolio_sha256=original["sources"]["portfolio"]["input_file_sha256"],
        )
    except (AccountCandidateImportError, Invalid, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, AccountSourceDetailError):
            raise
        raise AccountSourceDetailError(
            "Confira arquivos, hashes e o escopo original das candidatas."
        ) from None
    configured = {
        tuple(row[key] for key in CONFIG_KEY): row
        for row in data["snapshot"]["configured_accounts"]
    }
    expected = {(c.source_company_code, c.chart_company_code, c.account_code) for c in candidates}
    if set(configured) != expected:
        raise AccountSourceDetailError(
            "As contas do complemento divergem das candidatas originais."
        )
    observed = datetime.fromisoformat(data["observed_at_utc"].replace("Z", "+00:00"))
    plans = []
    for candidate in candidates:
        row = configured[
            (candidate.source_company_code, candidate.chart_company_code, candidate.account_code)
        ]
        retained = candidate.evidence["candidate"]
        if (
            row["catalogue_matches"] != 1
            or any(
                row[key] != retained[key]
                for key in ("account_type_raw", "account_status_raw", "catalogue_matches")
            )
            or observed < candidate.source_observed_at
        ):
            raise AccountSourceDetailError("O catálogo diverge da origem ou não comprova a conta.")
        counts = {
            name: sum(
                item["company_code"] == candidate.source_company_code
                for item in data["snapshot"][name]
            )
            for name in ("cash_accounts", "bank_references", "integration_account_configurations")
        }
        proof = {
            "version": VERSION,
            "execution_kind": "technical_preparation",
            "script_sha256": SCRIPT_SHA,
            "candidate_fingerprint": _fingerprint(candidate),
            "source_file_sha256": expected_sha256,
            "source_size_bytes": expected_size_bytes,
            "source_observed_at": observed.isoformat(),
            "row_sha256": _hash(row),
            "company_counts": counts,
            "bank_mapping_inferred": False,
            "human_reviewed": False,
            "financial_collection_enabled": False,
        }
        proof["facts_sha256"] = _facts(proof)
        values = dict(
            organization=organization,
            candidate=candidate,
            source_file_sha256=expected_sha256,
            source_size_bytes=expected_size_bytes,
            source_observed_at=observed,
            candidate_source_sha256=candidate.source_file_sha256,
            portfolio_file_sha256=candidate.portfolio_file_sha256,
            row=row,
            provenance=proof,
        )
        existing = ReconciliationAccountSourceDetail.objects.filter(
            candidate=candidate, source_file_sha256=expected_sha256
        ).first()
        if existing is not None and any(
            getattr(existing, key) != value for key, value in values.items()
        ):
            raise AccountSourceDetailError(
                "Um complemento registrado diverge; nada foi substituído."
            )
        # Same observed timestamp must not offer contradictory facts to the UI.
        for previous in ReconciliationAccountSourceDetail.objects.filter(
            candidate=candidate, source_observed_at=observed
        ):
            if (
                not _consistent(previous, candidate)
                or previous.row != row
                or previous.provenance["company_counts"] != counts
            ):
                raise AccountSourceDetailError(
                    "Fontes do mesmo horário divergem; confira a origem."
                )
        plans.append((existing, values))
    manifest = _hash(
        [
            {
                "candidate": str(values["candidate"].pk),
                "facts": values["provenance"]["facts_sha256"],
            }
            for _, values in plans
        ]
    )
    report: dict[str, Any] = dict(
        version=VERSION,
        valid=True,
        company_count=len(companies),
        candidate_count=len(candidates),
        existing=sum(item is not None for item, _ in plans),
        to_create=sum(item is None for item, _ in plans),
        created=0,
        applied=apply,
        manifest_sha256=manifest,
        source_file_sha256=expected_sha256,
        source_size_bytes=expected_size_bytes,
        financial_accounts_created=0,
        ledger_accounts_created=0,
        human_review_performed=False,
        financial_collection_enabled=False,
    )
    if apply:
        for existing, values in plans:
            if existing is None:
                ReconciliationAccountSourceDetail.objects.create(
                    **values, request_reference=request_reference.strip()
                )
                report["created"] += 1
        if report["created"]:
            record_event(
                action="hub.reconciliation.account_source_details.imported",
                organization=organization,
                actor=None,
                metadata={
                    **report,
                    "request_reference": request_reference.strip(),
                    "execution_kind": "technical_preparation",
                },
            )
    return report
