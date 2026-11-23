"""Queue only the D-338 pilot on the existing official identity/account."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.hub.models import FinancialAccount
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import canonical_hash, contract_hash, validate_scope


class Command(BaseCommand):
    help = "Enfileira o piloto nativo D-338 sem alterar pareamento, DSN ou escopo de empresas."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--agent", required=True)
        parser.add_argument("--account", required=True)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        agent = (
            EdgeAgent.objects.select_for_update()
            .filter(
                id=options["agent"],
                organization_id=options["organization"],
                is_official=True,
                status="active",
            )
            .first()
        )
        account = (
            FinancialAccount.objects.select_for_update()
            .select_related("company")
            .filter(
                id=options["account"],
                organization_id=options["organization"],
                company__organization_id=options["organization"],
                company__dominio_code="212",
                active=True,
                ledger_code="8",
            )
            .first()
        )
        if agent is None or account is None or not account.account_reference:
            raise CommandError("Agente/conta fora do escopo D-338; nenhuma alteração executada.")
        scope = validate_scope(
            {
                "company_code": 212,
                "chart_company_code": 212,
                "branch_code": 212,
                "bank_account_code": 8,
                "absent_account_code": 0,
                "bank_inflow_side": "debit",
                "period_start": "2026-09-01",
                "period_end_exclusive": "2026-10-01",
                "expected_source_rows": 177,
                "expected_lots": 163,
                "expected_bank_effects": 163,
            }
        )
        job, created = NativeLedgerCollection.objects.get_or_create(
            organization_id=options["organization"],
            agent=agent,
            financial_account=account,
            scope_revision=canonical_hash(scope),
            defaults={"scope": scope, "contract_hash": contract_hash()},
        )
        self.stdout.write(
            json.dumps(
                {
                    "job_id": str(job.id),
                    "created": created,
                    "state": job.state,
                    "scope_revision": job.scope_revision,
                }
            )
        )
