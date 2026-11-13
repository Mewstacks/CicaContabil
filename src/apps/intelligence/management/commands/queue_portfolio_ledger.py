"""Explicit reviewed per-account monthly jobs; defaults to read-only preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import FinancialAccount
from apps.hub.title_persistence import authorize_title_account
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    canonical_hash,
    contract_hash,
    strict_json,
    validate_scope,
)


class Command(BaseCommand):
    help = "Prepara coleta mensal com plano/conta/contagens revisados; não descobre vínculos."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "agent", "account", "actor", "scope-file", "evidence"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--allow-financial-capture", action="store_true")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        try:
            account = (
                FinancialAccount.objects.select_for_update()
                .select_related("company", "organization")
                .get(pk=options["account"], organization_id=options["organization"])
            )
            actor = User.objects.get(pk=options["actor"], is_active=True)
            authorize_title_account(account, actor)
            agent = EdgeAgent.objects.select_for_update().get(
                pk=options["agent"],
                organization_id=account.organization_id,
                is_official=True,
                status="active",
            )
            with Path(options["scope_file"]).open("rb") as stream:
                content = stream.read(32_769)
            if len(content) > 32_768:
                raise ValueError
            scope = validate_scope(strict_json(content))
            if (
                account.company.dominio_code != str(scope["company_code"])
                or account.ledger_code != str(scope["bank_account_code"])
                or not isinstance(options["evidence"], str)
                or not 1 <= len(options["evidence"].strip()) <= 240
            ):
                raise ValueError
        except (ValueError, TypeError, OSError, ObjectDoesNotExist, PermissionDenied):
            raise CommandError("Confira acesso atual, conta, escopo e evidência privada.") from None
        revision, digest = canonical_hash(scope), contract_hash()
        existing = NativeLedgerCollection.objects.filter(
            agent=agent, financial_account=account, scope_revision=revision
        ).first()
        if existing and (existing.scope != scope or existing.contract_hash != digest):
            raise CommandError("Coleta existente incompatível; não foi alterada.")
        created = False
        if options["allow_financial_capture"] and existing is None:
            existing = NativeLedgerCollection.objects.create(
                organization_id=account.organization_id,
                agent=agent,
                financial_account=account,
                scope=scope,
                scope_revision=revision,
                contract_hash=digest,
                requested_by=actor,
                evidence_reference=options["evidence"].strip(),
            )
            created = True
            record_event(
                action="intelligence.portfolio_ledger_requested",
                actor=actor,
                organization=account.organization,
                target=existing,
                metadata={
                    "scope_revision": revision,
                    "contract_hash": digest,
                    "requires_source_review": True,
                },
            )
        self.stdout.write(
            json.dumps(
                {
                    "queued": existing is not None,
                    "created": created,
                    "job_id": str(existing.pk) if existing else None,
                    "scope_revision": revision,
                    "contract_hash": digest,
                    "requires_capability": "portfolio_scope",
                    "requires_source_review": True,
                }
            )
        )
