"""Preview by default; a raw financial capture requires an explicit approved request."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import FinancialAccount
from apps.hub.title_persistence import authorize_title_account
from apps.intelligence.agent_scope import ACTIVE_PORTFOLIO_VERSION
from apps.intelligence.models import EdgeAgent, NativeTitleCollection
from apps.intelligence.native_title_contract import canonical_hash, contract_hash, validate_scope


class Command(BaseCommand):
    help = (
        "Prepara captura fiscal bruta; só enfileira com confirmação explícita de coleta financeira."
    )

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "agent", "account", "actor", "scope", "evidence"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--allow-financial-capture", action="store_true")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        try:
            with Path(options["scope"]).open("rb") as stream:
                content = stream.read(16385)
            if len(content) > 16384:
                raise ValueError
            scope = validate_scope(json.loads(content, object_pairs_hook=unique))
            actor = User.objects.get(pk=options["actor"], is_active=True)
            agent = EdgeAgent.objects.select_for_update().get(
                pk=options["agent"],
                organization_id=options["organization"],
                is_official=True,
                status="active",
            )
            if (
                not isinstance(agent.sync_scope, dict)
                or agent.sync_scope.get("version") != ACTIVE_PORTFOLIO_VERSION
            ):
                raise ValueError
            account = (
                FinancialAccount.objects.select_for_update(of=("self",))
                .select_related("company", "organization")
                .get(
                    pk=options["account"],
                    organization_id=options["organization"],
                    company__organization_id=options["organization"],
                    company__dominio_code="212",
                    ledger_code="8",
                    active=True,
                )
            )
            authorize_title_account(account, actor)
            evidence = options["evidence"].strip()
            if not evidence or len(evidence) > 240:
                raise ValueError
        except (
            OSError,
            ValueError,
            User.DoesNotExist,
            FinancialAccount.DoesNotExist,
            EdgeAgent.DoesNotExist,
            PermissionDenied,
            ValidationError,
        ):
            raise CommandError(
                "Escopo, referência ou acesso atual incompatível com a captura fiscal."
            ) from None
        revision, contract = canonical_hash(scope), contract_hash()
        if not options["allow_financial_capture"]:
            self.stdout.write(
                json.dumps(
                    {
                        "queued": False,
                        "capture_id": scope["capture_id"],
                        "scope_revision": revision,
                        "contract_hash": contract,
                        "requires_financial_capture_approval": True,
                        "requires_semantic_review": True,
                    }
                )
            )
            return
        job = NativeTitleCollection.objects.filter(pk=scope["capture_id"]).first()
        created = job is None
        if job is not None and (
            job.organization_id != account.organization_id
            or job.agent_id != agent.id
            or job.financial_account_id != account.id
            or job.requested_by_id != actor.id
            or job.scope_revision != revision
            or job.contract_hash != contract
            or job.evidence_reference != evidence
        ):
            raise CommandError("Identidade de captura já usada com outro contexto.")
        if job is None:
            job = NativeTitleCollection.objects.create(
                id=scope["capture_id"],
                organization=account.organization,
                agent=agent,
                financial_account=account,
                requested_by=actor,
                evidence_reference=evidence,
                scope=scope,
                scope_revision=revision,
                contract_hash=contract,
            )
            record_event(
                action="intelligence.native_titles_requested",
                actor=actor,
                organization=account.organization,
                target=job,
                metadata={
                    "scope_revision": revision,
                    "contract_hash": contract,
                    "evidence_reference": evidence,
                    "requires_semantic_review": True,
                },
            )
        self.stdout.write(
            json.dumps({"job_id": str(job.id), "created": created, "state": job.state})
        )
