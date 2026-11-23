"""Compare retained fiscal facts without interpreting money, absence or reversal."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from apps.accounts.models import User
from apps.hub.models import FinancialAccount
from apps.hub.title_persistence import authorize_title_account
from apps.hub.title_requests import authorize_title_company, title_job_company
from apps.intelligence.models import CompanyTitleCollection, NativeTitleCollection
from apps.intelligence.native_title_contract import (
    FAMILIES,
    MAX_BYTES,
    canonical_hash,
    contract_hash,
    is_automatic_scope,
    manifest,
    review_summary,
    validate_scope,
    validate_snapshot,
)

VERSION = "dominio-title-source-comparison-v1"
KINDS = ("installments", "payments", "accounting_links")
CONTEXT_FIELDS = (
    "company_code",
    "comparison_bank_account_code",
    "period_start",
    "period_end_exclusive",
)
COUNTERS = ("added", "absent", "changed", "unchanged")


class NativeTitleComparisonError(ValueError):
    pass


@dataclass(frozen=True)
class TitleSourceEvidence:
    content: bytes
    scope: dict[str, Any]
    expected_sha256: str
    contract_sha256: str


def _validated(evidence: TitleSourceEvidence) -> dict[str, Any]:
    if (
        not isinstance(evidence.content, bytes)
        or not 1 <= len(evidence.content) <= MAX_BYTES
        or hashlib.sha256(evidence.content).hexdigest() != evidence.expected_sha256
        or evidence.contract_sha256 != contract_hash()
    ):
        raise NativeTitleComparisonError("Hash, tamanho ou contrato da fonte não confere.")
    try:
        return validate_snapshot(evidence.content, evidence.scope)
    except (ValueError, TypeError, KeyError) as error:
        raise NativeTitleComparisonError("Fonte fora do contrato fiscal.") from error


def _key(row: dict[str, Any], spec: dict[str, Any], kind: str) -> tuple[Any, ...]:
    company = "fili_lan" if kind == "accounting_links" else "codi_emp"
    identity: tuple[Any, ...] = (
        row[company],
        row[spec["note_field"]],
        row[spec["installment_field"]],
    )
    if kind != "installments":
        identity += (
            row[spec["payment_date_field"]],
            row[spec["payment_type_field"]],
            row[spec["payment_number_field"]],
        )
    if kind == "accounting_links":
        identity = (row["codi_emp"], row["nume_lan"], *identity, row["grupo"])
    return identity


def compare_title_sources(
    previous: TitleSourceEvidence, current: TitleSourceEvidence
) -> dict[str, Any]:
    before, after = _validated(previous), _validated(current)
    context = {key: previous.scope[key] for key in CONTEXT_FIELDS if key in previous.scope}
    if context != {key: current.scope[key] for key in CONTEXT_FIELDS if key in current.scope}:
        raise NativeTitleComparisonError("Fontes de recortes diferentes não são comparáveis.")
    same_capture = previous.scope["capture_id"] == current.scope["capture_id"]
    if same_capture and previous.expected_sha256 != current.expected_sha256:
        raise NativeTitleComparisonError("A mesma captura não pode ter conteúdos divergentes.")
    contract = manifest()
    total = dict.fromkeys(COUNTERS, 0)
    families: dict[str, Any] = {}
    for family in FAMILIES:
        old = next(item for item in before["families"] if item["name"] == family)
        new = next(item for item in after["families"] if item["name"] == family)
        groups = {}
        for kind in KINDS:
            left = {
                _key(row, contract["families"][family], kind): (index, row)
                for index, row in enumerate(old[kind], 1)
            }
            right = {
                _key(row, contract["families"][family], kind): (index, row)
                for index, row in enumerate(new[kind], 1)
            }
            counts = dict.fromkeys(COUNTERS, 0)
            changes = []
            # Row references disclose no fiscal identifiers or literal field values.
            identities = sorted(
                left.keys() | right.keys(),
                key=lambda identity: canonical_hash([family, kind, identity]),
            )
            for identity in identities:
                prior, latest = left.get(identity), right.get(identity)
                fields = []
                if prior is None:
                    state, counter = "new_in_current", "added"
                elif latest is None:
                    state, counter = "absent_from_current", "absent"
                else:
                    fields = sorted(key for key in prior[1] if prior[1][key] != latest[1][key])
                    state = counter = "changed" if fields else "unchanged"
                counts[counter] += 1
                if counter != "unchanged":
                    changes.append(
                        {
                            "state": state,
                            "key_sha256": canonical_hash([family, kind, identity]),
                            "previous_row": prior[0] if prior else None,
                            "current_row": latest[0] if latest else None,
                            "changed_fields": fields,
                        }
                    )
            for key in COUNTERS:
                total[key] += counts[key]
            groups[kind] = {"counts": counts, "changes": changes}
        families[family] = groups
    return {
        "version": VERSION,
        "previous": {
            "capture_id": previous.scope["capture_id"],
            "sha256": previous.expected_sha256,
        },
        "current": {"capture_id": current.scope["capture_id"], "sha256": current.expected_sha256},
        "context": context,
        "same_capture": same_capture,
        "counts": total,
        "families": families,
        "requires_semantic_review": True,
        "bank_linkage": "unproven",
        "absence_proves_reversal": False,
        "financial_actions_applied": 0,
    }


def _account(identifier: UUID, organization_id: UUID, actor: User) -> FinancialAccount:
    account = FinancialAccount.objects.select_related("company", "organization").get(
        pk=identifier,
        organization_id=organization_id,
        company__organization_id=organization_id,
    )
    authorize_title_account(account, actor)
    return account


def _load(
    identifier: UUID, organization_id: UUID, actor: User
) -> tuple[NativeTitleCollection | CompanyTitleCollection, TitleSourceEvidence]:
    return _load_checked(identifier, organization_id, actor=actor)


def load_capture_for_routine(
    identifier: UUID, organization_id: UUID
) -> tuple[NativeTitleCollection | CompanyTitleCollection, TitleSourceEvidence]:
    """D-394: same integrity checks, without a person's membership (direct-use routine only)."""
    return _load_checked(identifier, organization_id, actor=None)


def _load_checked(
    identifier: UUID, organization_id: UUID, *, actor: User | None
) -> tuple[NativeTitleCollection | CompanyTitleCollection, TitleSourceEvidence]:
    legacy = (
        NativeTitleCollection.objects.select_related("source_file", "financial_account__company")
        .filter(pk=identifier, organization_id=organization_id)
        .first()
    )
    company_job = (
        CompanyTitleCollection.objects.select_related("source_file", "company")
        .filter(pk=identifier, organization_id=organization_id)
        .first()
    )
    if legacy is None and company_job is None:
        raise NativeTitleCollection.DoesNotExist("Fonte ausente.")
    if legacy is not None and company_job is not None:
        raise NativeTitleComparisonError("Identificador ambíguo.")
    job = legacy if legacy is not None else company_job
    assert job is not None
    company = title_job_company(job)
    if actor is None:
        from apps.hub.direct_use import direct_use_enabled

        if not direct_use_enabled(company.organization):
            raise NativeTitleComparisonError("Fonte disponível só para revisão humana.")
        account = (
            FinancialAccount.objects.select_related("company", "organization").get(
                pk=job.financial_account_id,
                organization_id=organization_id,
                company__organization_id=organization_id,
            )
            if isinstance(job, NativeTitleCollection)
            else None
        )
    else:
        authorize_title_company(company, actor, write=False)
        account = (
            _account(job.financial_account_id, organization_id, actor)
            if isinstance(job, NativeTitleCollection)
            else None
        )
    scope = validate_scope(job.scope)
    source = job.source_file
    if (
        job.state != "captured"
        or company.organization_id != organization_id
        or is_automatic_scope(scope) != isinstance(job, CompanyTitleCollection)
        or str(job.pk) != scope["capture_id"]
        or job.completed_at is None
        or not job.evidence_reference.strip()
        or job.scope_revision != canonical_hash(scope)
        or str(scope["company_code"]) != company.dominio_code
        or (
            account is not None
            and str(scope["comparison_bank_account_code"]) != account.ledger_code
        )
        or source is None
        or source.organization_id != organization_id
        or source.company_id != company.pk
        or source.financial_account_id != (account.pk if account else None)
        or source.origin != "obligation"
        or source.kind != "json"
        or source.content_hash != job.content_hash
        or not 1 <= source.size_bytes <= MAX_BYTES
    ):
        raise NativeTitleComparisonError("Contexto da fonte retida não confere.")
    try:
        with source.content.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
    except Exception:
        # Storage backends expose different exception classes and private key names.
        raise NativeTitleComparisonError("Não foi possível ler a fonte privada.") from None
    evidence = TitleSourceEvidence(content, scope, job.content_hash, job.contract_hash)
    snapshot = _validated(evidence)
    if len(content) != source.size_bytes or job.result != review_summary(snapshot):
        raise NativeTitleComparisonError("Recibo ou arquivo da captura foi alterado.")
    return job, evidence


def compare_collected_titles(
    *, organization_id: UUID, previous_id: UUID, current_id: UUID, actor: User
) -> dict[str, Any]:
    """Operational preview under the existing title permission; no database writes."""
    previous_job, previous = _load(previous_id, organization_id, actor)
    if previous_id == current_id:
        current_job, current = previous_job, previous
    else:
        current_job, current = _load(current_id, organization_id, actor)
    if title_job_company(previous_job).pk != title_job_company(current_job).pk or getattr(
        previous_job, "financial_account_id", None
    ) != getattr(current_job, "financial_account_id", None):
        raise NativeTitleComparisonError("Contas de comparação diferentes.")
    result = compare_title_sources(previous, current)
    # Re-read current permission/account metadata after private storage I/O.
    company = title_job_company(previous_job)
    company.refresh_from_db()
    authorize_title_company(company, actor, write=False)
    if company.dominio_code != str(result["context"]["company_code"]):
        raise NativeTitleComparisonError("O contexto da empresa mudou durante a comparação.")
    if isinstance(previous_job, NativeTitleCollection):
        account = _account(previous_job.financial_account_id, organization_id, actor)
        if account.ledger_code != str(result["context"]["comparison_bank_account_code"]):
            raise NativeTitleComparisonError("O contexto da conta mudou durante a comparação.")
    return result
