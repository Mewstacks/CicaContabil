"""D-73 measurement from frozen predictions and immutable owner reviews."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import (
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ReconciliationRun,
)
from apps.hub.title_persistence import (
    _bank_fingerprint,
    _bank_identity,
    _verify_bank_source,
    authorize_title_account,
)
from apps.intelligence.native_ledger_contract import canonical_hash
from apps.organizations.models import Membership

PREDICTION = "hub.reconciliation.acceptance_sample"
REVIEW = "hub.reconciliation.acceptance_review"


def _access(account: FinancialAccount, actor: User, *, owner: bool = False) -> None:
    authorize_title_account(account, actor)
    if (
        owner
        and not Membership.objects.filter(
            organization_id=account.organization_id,
            user=actor,
            is_active=True,
            role=Membership.Role.OWNER,
        ).exists()
    ):
        raise PermissionDenied("O proprietário deve revisar a amostra de aceite D-73.")


def _label(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 160:
        raise ValueError("Informe release ou evidência de revisão com até 160 caracteres.")
    return value.strip()


@transaction.atomic
def prepare_acceptance_sample(
    *, account: FinancialAccount, actor: User, movement_ids: list[str], release: str
) -> AuditEvent:
    account = (
        FinancialAccount.objects.select_for_update()
        .select_related("company", "organization")
        .get(pk=account.pk)
    )
    _access(account, actor)
    release = _label(release)
    if (
        not isinstance(movement_ids, list)
        or not 1 <= len(movement_ids) <= 1000
        or len(set(movement_ids)) != len(movement_ids)
    ):
        raise ValueError("Selecione de 1 a 1000 movimentos distintos.")
    movements = list(
        NormalizedMovement.objects.filter(
            pk__in=movement_ids,
            organization_id=account.organization_id,
            company_id=account.company_id,
            financial_account=account,
            source_file__origin="bank_statement",
            source_file__organization_id=account.organization_id,
            source_file__company_id=account.company_id,
            source_file__financial_account=account,
        )
        .select_related("source_file")
        .order_by("id")
    )
    if len(movements) != len(movement_ids):
        raise ValueError("Movimento ausente ou fora da fonte bancária desta conta.")
    facts: dict[str, Any] = {}
    verified = set()
    for movement in movements:
        if movement.source_file_id not in verified:
            _verify_bank_source(movement.source_file)
            verified.add(movement.source_file_id)
        fact_key = _bank_identity(movement)
        fact = {
            "fact_key": fact_key,
            "source_fingerprint": _bank_fingerprint(movement),
            "prediction": {
                "debit": movement.debit_account_code,
                "credit": movement.credit_account_code,
                "cost_center": movement.cost_center_code,
            },
            "automatic": movement.classification_source == "rule",
            "source_sha256": movement.source_file.content_hash,
            "movement_id": str(movement.pk),
        }

        def comparable(f: dict[str, Any]) -> dict[str, Any]:
            return {k: v for k, v in f.items() if k not in {"source_sha256", "movement_id"}}

        if fact_key in facts and comparable(facts[fact_key]) != comparable(fact):
            raise ValueError("O mesmo fato aparece com conteúdo ou classificação divergente.")
        facts[fact_key] = fact
    snapshot = {"release": release, "facts": sorted(facts.values(), key=lambda f: f["fact_key"])}
    digest = canonical_hash(snapshot)
    prior = AuditEvent.objects.filter(
        organization_id=account.organization_id,
        action=PREDICTION,
        target_id=str(account.pk),
        metadata__fingerprint=digest,
    ).first()
    if prior:
        return prior
    return record_event(
        action=PREDICTION,
        actor=actor,
        organization=account.organization,
        target=account,
        metadata={**snapshot, "fingerprint": digest, "requires_owner_review": True},
    )


@transaction.atomic
def review_acceptance_sample(
    *,
    account: FinancialAccount,
    actor: User,
    sample_id: str,
    expected: list[dict[str, Any]],
    evidence_reference: str,
    expected_source_facts: list[dict[str, Any]] | None = None,
) -> AuditEvent:
    account = (
        FinancialAccount.objects.select_for_update()
        .select_related("company", "organization")
        .get(pk=account.pk)
    )
    _access(account, actor, owner=True)
    sample = AuditEvent.objects.get(
        pk=sample_id,
        organization_id=account.organization_id,
        action=PREDICTION,
        target_id=str(account.pk),
        target_type="hub.financialaccount",
    )
    packet = acceptance_review_packet(account=account, actor=actor, sample_id=str(sample.pk))
    if expected_source_facts is not None and expected_source_facts != packet["facts"]:
        raise ValueError("Os fatos da ficha diferem da fonte congelada para revisão.")
    evidence = _label(evidence_reference)
    if not isinstance(expected, list) or len(expected) != len(sample.metadata["facts"]):
        raise ValueError("Revise todos os fatos da amostra, sem acrescentar cópias.")
    keys, seen = {f["fact_key"] for f in sample.metadata["facts"]}, set()
    accounts = set(
        LedgerAccount.objects.filter(
            company_id=account.company_id,
            organization_id=account.organization_id,
            active=True,
            accepts_entries=True,
        ).values_list("code", flat=True)
    )
    for row in expected:
        if (
            not isinstance(row, dict)
            or set(row) != {"fact_key", "debit", "credit", "cost_center"}
            or any(not isinstance(v, str) for v in row.values())
            or row["fact_key"] not in keys
            or row["fact_key"] in seen
            or row["debit"] not in accounts
            or row["credit"] not in accounts
            or row["debit"] == row["credit"]
            or len(row["cost_center"]) > 64
        ):
            raise ValueError("Resultado revisado exige fato único e contas válidas da empresa.")
        seen.add(row["fact_key"])
    result = {
        "sample_id": str(sample.pk),
        "sample_fingerprint": sample.metadata["fingerprint"],
        "expected": sorted(expected, key=lambda row: row["fact_key"]),
        "evidence_reference": evidence,
    }
    prior = AuditEvent.objects.filter(
        organization_id=account.organization_id,
        action=REVIEW,
        target_id=str(account.pk),
        metadata__sample_id=str(sample.pk),
    ).first()
    if prior:
        if prior.metadata != result:
            raise ValueError("Revisão já registrada é imutável; confira a evidência original.")
        return prior
    return record_event(
        action=REVIEW,
        actor=actor,
        organization=account.organization,
        target=account,
        metadata=result,
    )


def acceptance_report(
    *, account: FinancialAccount, actor: User, release: str, run_ids: list[str] | None = None
) -> dict[str, Any]:
    account = FinancialAccount.objects.select_related("company", "organization").get(pk=account.pk)
    _access(account, actor)
    release = _label(release)
    samples = list(
        AuditEvent.objects.filter(
            organization_id=account.organization_id,
            target_id=str(account.pk),
            target_type="hub.financialaccount",
            action=PREDICTION,
            metadata__release=release,
        ).order_by("occurred_at")
    )
    reviews = {
        e.metadata["sample_id"]: e
        for e in AuditEvent.objects.filter(
            organization_id=account.organization_id, target_id=str(account.pk), action=REVIEW
        )
    }
    facts: dict[str, Any] = {}
    conflicts: set[str] = set()
    unreviewed: set[str] = set()
    for sample in samples:
        review = reviews.get(str(sample.pk))
        if review is None:
            unreviewed.update(f["fact_key"] for f in sample.metadata["facts"])
            continue
        expected = {
            r["fact_key"]: {k: v for k, v in r.items() if k != "fact_key"}
            for r in review.metadata["expected"]
        }
        for fact in sample.metadata["facts"]:
            key = fact["fact_key"]
            comparison = {
                **{k: v for k, v in fact.items() if k not in {"source_sha256", "movement_id"}},
                "expected": expected[key],
            }
            if key in facts and facts[key] != comparison:
                conflicts.add(key)
            facts[key] = comparison
    automatic = [f for f in facts.values() if f["automatic"]]
    correct = sum(f["prediction"] == f["expected"] for f in automatic)
    # Integer arithmetic makes the 95% boundary exact; model confidence is never used.
    precision_passed = len(automatic) >= 200 and correct * 100 >= len(automatic) * 95
    durations, total_processed = [], 0
    if run_ids:
        runs = list(
            ReconciliationRun.objects.filter(
                pk__in=run_ids,
                organization_id=account.organization_id,
                source_file__financial_account=account,
                source_file__company_id=account.company_id,
                source_file__organization_id=account.organization_id,
            )
        )
        if len(runs) != len(set(run_ids)):
            raise ValueError("Processamento fora desta conta ou ausente.")
        for run in runs:
            if (
                run.started_at is None
                or run.completed_at is None
                or run.completed_at < run.started_at
                or run.state not in {"completed", "completed_alerts"}
            ):
                raise ValueError("Use processamentos encerrados com duração comprovada.")
            durations.append((run.completed_at - run.started_at).total_seconds())
            total_processed += run.processed_count
    return {
        "release": release,
        "reviewed_distinct_facts": len(facts),
        "unreviewed_distinct_facts": len(unreviewed - facts.keys()),
        "conflicting_facts": len(conflicts),
        "missing_to_200": max(0, 200 - len(facts)),
        "automatic_reviewed": len(automatic),
        "automatic_correct": correct,
        "precision_percent": round(100 * correct / len(automatic), 4) if automatic else None,
        "classification_threshold_passed": precision_passed and not conflicts,
        "measured_runs": len(durations),
        "measured_processed_items": total_processed,
        "max_run_seconds": max(durations) if durations else None,
        "company_processing_seconds": sum(durations) if durations else None,
        "performance_threshold_passed": bool(durations) and sum(durations) <= 300,
        "representative_workload_requires_owner_confirmation": True,
        "release_accepted": False,
        "remaining_gates": [
            "integrity_and_isolation",
            "recovery",
            "destination_import",
            "owner_release_signoff",
        ],
    }


def acceptance_review_packet(
    *, account: FinancialAccount, actor: User, sample_id: str
) -> dict[str, Any]:
    account = FinancialAccount.objects.select_related("company", "organization").get(pk=account.pk)
    _access(account, actor)
    sample = AuditEvent.objects.get(
        pk=sample_id,
        organization_id=account.organization_id,
        action=PREDICTION,
        target_type="hub.financialaccount",
        target_id=str(account.pk),
    )
    facts, expected = [], []
    verified = set()
    for fact in sample.metadata["facts"]:
        movement = NormalizedMovement.objects.select_related("source_file").get(
            pk=fact["movement_id"],
            financial_account=account,
            company_id=account.company_id,
            organization_id=account.organization_id,
            source_file__origin="bank_statement",
            source_file__organization_id=account.organization_id,
            source_file__company_id=account.company_id,
            source_file__financial_account=account,
        )
        if movement.source_file_id not in verified:
            _verify_bank_source(movement.source_file)
            verified.add(movement.source_file_id)
        if (
            movement.source_file.content_hash != fact["source_sha256"]
            or _bank_fingerprint(movement) != fact["source_fingerprint"]
        ):
            raise ValueError("A fonte de um fato da amostra mudou; confira o original.")
        facts.append(
            {
                "fact_key": fact["fact_key"],
                "movement_id": str(movement.pk),
                "date": movement.occurred_on.isoformat() if movement.occurred_on else None,
                "description": movement.original_description,
                "cash_cents": movement.amount_cents,
                "direction": movement.direction,
                "source_sha256": movement.source_file.content_hash,
            }
        )
        expected.append(
            {"fact_key": fact["fact_key"], "debit": "", "credit": "", "cost_center": ""}
        )
    # Keep predictions out of the worksheet for an independent reference review.
    return {
        "sample_id": str(sample.pk),
        "facts": facts,
        "expected": expected,
        "evidence_reference": "",
        "requires_owner_review": True,
    }
