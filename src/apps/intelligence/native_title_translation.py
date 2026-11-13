"""Bind explicit human financial decisions to retained fiscal facts, without matching banks."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import FinancialAccount, ReconciliationTitleSnapshot
from apps.hub.title_contract import TitleContractError, validate_title_snapshot
from apps.hub.title_persistence import authorize_title_account, import_title_snapshot
from apps.intelligence.native_title_comparison import TitleSourceEvidence, _key, _load, _validated
from apps.intelligence.native_title_contract import canonical_hash, manifest


def row_reference(family: str, kind: str, row: dict[str, Any]) -> str:
    spec = manifest()["families"][family]
    return canonical_hash([family, kind, _key(row, spec, kind)])


def translate_reviewed_titles(
    *,
    evidence: TitleSourceEvidence,
    review: dict[str, Any],
    company_key: str,
    account_reference: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The human supplies component semantics; source dates/identity/principal stay literal.

    The retained month cannot prove lifetime balances or bank linkage. Every payment
    component of each selected installment must be represented, including zero/withholding.
    Unsupported cases must wait for review rather than being silently dropped.
    """
    raw = _validated(evidence)
    if (
        not isinstance(review, dict)
        or set(review) != {"source_sha256", "evidence_reference", "decisions"}
        or review["source_sha256"] != evidence.expected_sha256
        or not isinstance(review["evidence_reference"], str)
        or not 1 <= len(review["evidence_reference"].strip()) <= 240
        or not isinstance(review["decisions"], list)
        or not 1 <= len(review["decisions"]) <= 100
    ):
        raise TitleContractError(
            "Revisão exige fonte íntegra, evidência e até 100 parcelas explícitas."
        )
    families = {f["name"]: f for f in raw["families"]}
    contract = manifest()
    titles: dict[str, Any] = {}
    provenance, seen = [], set()
    for decision in review["decisions"]:
        if (
            not isinstance(decision, dict)
            or set(decision)
            != {"family", "installment_reference", "kind", "principal_field", "settlements"}
            or decision["family"] not in families
        ):
            raise TitleContractError("Decisão financeira incompatível.")
        family = decision["family"]
        spec = contract["families"][family]
        parts = {
            row_reference(family, "installments", p): p for p in families[family]["installments"]
        }
        reference = decision["installment_reference"]
        if not isinstance(reference, str) or reference not in parts or reference in seen:
            raise TitleContractError("Parcela ausente ou repetida na revisão.")
        seen.add(reference)
        part = parts[reference]
        identity = _key(part, spec, "installments")
        field = decision["principal_field"]
        if (
            not isinstance(field, str)
            or not field.startswith(("vlor_", "vbru_"))
            or field not in part
            or not isinstance(part[field], str)
        ):
            raise TitleContractError("Selecione explicitamente o campo de principal conferido.")
        principal = Decimal(part[field]) * 100
        if principal <= 0 or principal != principal.to_integral_value():
            raise TitleContractError("Principal da origem exige revisão específica.")
        payments = {
            row_reference(family, "payments", p): p
            for p in families[family]["payments"]
            if _key(p, spec, "installments") == identity
        }
        settlements: list[dict[str, Any]] = []
        used: set[str] = set()
        mapped: list[dict[str, Any]] = []
        if not isinstance(decision["settlements"], list):
            raise TitleContractError(
                "Informe as decisões de todas as baixas da parcela selecionada."
            )
        for event in decision["settlements"]:
            if not isinstance(event, dict) or set(event) != {"payment_references", "normalized"}:
                raise TitleContractError("Baixa exige referências de origem e decisão normalizada.")
            refs = event["payment_references"]
            row = event["normalized"]
            if (
                not isinstance(refs, list)
                or not refs
                or not all(isinstance(r, str) for r in refs)
                or len(set(refs)) != len(refs)
                or used.intersection(refs)
                or not set(refs).issubset(payments)
                or not isinstance(row, dict)
            ):
                raise TitleContractError("Componente ausente, repetido ou de outra parcela.")
            posted = {payments[r][spec["payment_date_field"]] for r in refs}
            numbers = {payments[r][spec["payment_number_field"]] for r in refs}
            stable_key = canonical_hash(sorted(refs))
            if (
                len(posted) != 1
                or len(numbers) != 1
                or row.get("key") != stable_key
                or row.get("posted_on") != next(iter(posted))
            ):
                raise TitleContractError(
                    "Baixa deve preservar identidade, data e número de origem."
                )
            used.update(refs)
            settlements.append(row)
            mapped.append({"settlement_key": stable_key, "payment_references": sorted(refs)})
        if used != set(payments):
            raise TitleContractError(
                "Há componentes sem decisão; não omitir retenção, zero ou estorno."
            )
        title_key = canonical_hash([family, identity[:2]])
        title = titles.setdefault(
            title_key, {"key": title_key, "kind": decision["kind"], "installments": []}
        )
        if title["kind"] != decision["kind"]:
            raise TitleContractError("A natureza do mesmo título não pode divergir.")
        title["installments"].append(
            {
                "key": reference,
                "due_on": part[spec["due_field"]],
                "principal_cents": int(principal),
                "outstanding_cents": None,
                "settlements": settlements,
            }
        )
        provenance.append(
            {
                "title_key": title_key,
                "installment_key": reference,
                "principal_field": field,
                "settlements": mapped,
            }
        )
    payload = {
        "contract": "titles-normalized-v1",
        "company_key": company_key,
        "account_reference": account_reference,
        "as_of": (
            date.fromisoformat(evidence.scope["period_end_exclusive"]) - timedelta(days=1)
        ).isoformat(),
        "settlements_complete": False,
        "titles": list(titles.values()),
    }
    validate_title_snapshot(payload, company_key=company_key, account_reference=account_reference)
    return payload, provenance


@transaction.atomic
def import_reviewed_native_titles(
    *, organization_id: UUID, capture_id: UUID, actor: User, review: dict[str, Any]
) -> tuple[ReconciliationTitleSnapshot, bool]:
    job, evidence = _load(capture_id, organization_id, actor)
    account = (
        FinancialAccount.objects.select_for_update()
        .select_related("company", "organization")
        .get(pk=job.financial_account_id, organization_id=organization_id)
    )
    authorize_title_account(account, actor)
    payload, provenance = translate_reviewed_titles(
        evidence=evidence,
        review=review,
        company_key=str(account.company_id),
        account_reference=account.account_reference,
    )
    snapshot, created = import_title_snapshot(
        financial_account=account,
        content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        actor=actor,
        evidence_reference=review["evidence_reference"],
    )
    prior = snapshot.evidence_reference
    # The snapshot retains the normalized facts; the immutable audit binds each
    # financial decision to raw components and the original capture/hash.
    if created:
        record_event(
            action="hub.reconciliation.native_titles_translated",
            actor=actor,
            organization=account.organization,
            target=snapshot,
            metadata={
                "capture_id": str(job.pk),
                "source_sha256": evidence.expected_sha256,
                "review_sha256": canonical_hash(review),
                "provenance": provenance,
                "bank_linkage": "unproven",
                "settlements_complete": False,
                "evidence_reference": prior,
            },
        )
    return snapshot, created
