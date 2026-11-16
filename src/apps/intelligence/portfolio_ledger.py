"""Atomic batches of explicitly reviewed monthly scopes; never discover bank mappings."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import FinancialAccount
from apps.hub.title_persistence import authorize_title_account
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger import _job_valid
from apps.intelligence.native_ledger_contract import canonical_hash, contract_hash, validate_scope

VERSION = "contad-portfolio-ledger-batch-v1"
MAX_ITEMS = 1000


class PortfolioBatchError(ValueError):
    def __init__(self, report: dict[str, Any]) -> None:
        super().__init__("Revise os itens indicados; nenhuma coleta do lote foi criada.")
        self.report = report


def _uuid(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Identificador incompatível.")
    return str(UUID(value))


@transaction.atomic
def prepare_portfolio_ledger_batch(
    *,
    organization_id: str,
    agent_id: str,
    actor_id: str,
    manifest: dict[str, Any],
    enqueue: bool = False,
) -> dict[str, Any]:
    """Read-only by default; any invalid item prevents every insertion in apply mode."""
    organization_id, agent_id, actor_id = map(_uuid, (organization_id, agent_id, actor_id))
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"version", "organization_id", "agent_id", "items"}
        or manifest["version"] != VERSION
        or _uuid(manifest["organization_id"]) != organization_id
        or _uuid(manifest["agent_id"]) != agent_id
        or not isinstance(manifest["items"], list)
        or not 1 <= len(manifest["items"]) <= MAX_ITEMS
    ):
        raise ValueError("Manifesto de carteira incompatível.")
    # Intake and every queue writer lock the same agent before account/job rows.
    agents = EdgeAgent.objects.all()
    if enqueue:
        agents = agents.select_for_update(of=("self",))
    agent = agents.get(
        pk=agent_id, organization_id=organization_id, is_official=True, status="active"
    )
    actor = User.objects.get(pk=actor_id, is_active=True)
    digest = contract_hash()
    items: list[dict[str, Any]] = []
    prepared: list[tuple[FinancialAccount, dict[str, Any], str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(manifest["items"], 1):
        result: dict[str, Any] = {"item": index, "state": "invalid", "issues": []}
        try:
            if not isinstance(item, dict) or set(item) != {
                "financial_account_id", "scope", "evidence_reference"
            }:
                raise ValueError
            account_id = _uuid(item["financial_account_id"])
            scope = validate_scope(item["scope"])
            evidence = item["evidence_reference"]
            if not isinstance(evidence, str) or not 1 <= len(evidence.strip()) <= 240:
                raise ValueError
            accounts = FinancialAccount.objects.select_related("company", "organization")
            if enqueue:
                accounts = accounts.select_for_update(of=("self",))
            account = accounts.get(pk=account_id, organization_id=organization_id)
            authorize_title_account(account, actor)
            if (
                account.company.dominio_code != str(scope["company_code"])
                or account.ledger_code != str(scope["bank_account_code"])
            ):
                raise ValueError
        except (ValueError, TypeError, ObjectDoesNotExist, PermissionDenied):
            result["issues"] = ["access_account_scope_or_evidence_invalid"]
            items.append(result)
            continue
        revision = canonical_hash(scope)
        result.update(
            financial_account_id=account_id,
            company_code=scope["company_code"],
            period_start=scope["period_start"],
            period_end_exclusive=scope["period_end_exclusive"],
            scope_revision=revision,
            job_id=None,
            created=False,
        )
        key = (account_id, scope["period_start"])
        if key in seen:
            result["issues"] = ["duplicate_account_month"]
            items.append(result)
            continue
        seen.add(key)
        existing = NativeLedgerCollection.objects.filter(
            agent=agent, financial_account=account
        )
        conflict = existing.filter(scope__period_start=scope["period_start"]).exclude(
            scope_revision=revision
        ).exists()
        job = existing.filter(scope_revision=revision).first()
        if conflict or (job and (job.scope != scope or job.contract_hash != digest)):
            result["issues"] = ["existing_scope_conflict"]
        elif job and not _job_valid(job, agent):
            result["issues"] = ["existing_job_requires_review"]
        else:
            # Existing jobs retain their actor, evidence and state, including review/failure.
            result.update(state=job.state if job else "ready", job_id=str(job.pk) if job else None)
            if job is None:
                prepared.append((account, scope, revision, evidence.strip()))
        items.append(result)
    report: dict[str, Any] = {
        "version": VERSION,
        "manifest_revision": canonical_hash(manifest),
        "contract_hash": digest,
        "dry_run": not enqueue,
        "valid": not any(item["issues"] for item in items),
        "created": 0,
        "requires_source_review": True,
        "automatic_recurrence_enabled": False,
        "items": items,
        "counts": dict(Counter(item["state"] for item in items)),
    }
    if enqueue and not report["valid"]:
        raise PortfolioBatchError(report)
    if enqueue:
        created: dict[tuple[str, str], NativeLedgerCollection] = {}
        for account, scope, revision, evidence in prepared:
            job = NativeLedgerCollection.objects.create(
                organization_id=organization_id,
                agent=agent,
                financial_account=account,
                scope=scope,
                scope_revision=revision,
                contract_hash=digest,
                requested_by=actor,
                evidence_reference=evidence,
            )
            record_event(
                action="intelligence.portfolio_ledger_requested",
                actor=actor,
                organization=account.organization,
                target=job,
                metadata={
                    "scope_revision": revision,
                    "contract_hash": digest,
                    "batch_revision": report["manifest_revision"],
                    "requires_source_review": True,
                },
            )
            created[(str(account.pk), revision)] = job
        for item in items:
            job = created.get((item["financial_account_id"], item["scope_revision"]))
            if job:
                item.update(state=job.state, job_id=str(job.pk), created=True)
        report["created"] = len(created)
        report["counts"] = dict(Counter(item["state"] for item in items))
    return report
