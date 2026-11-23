"""D-393: run the direct-use routine on every active bank account of one office.

Activates the valid Razão-derived DE-PARA drafts and posts the rule-classified movements the
Razão does not have. Only works for an office listed in CICA_DIRECT_USE_ORGANIZATION_IDS.
Without ``--apply`` it only reports what exists, writing nothing.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.depara_ledger import create_drafts, ledger_rules
from apps.hub.direct_use import direct_use_enabled, run_for_organization
from apps.hub.models import FinancialAccount, JournalEntry, ReconciliationRule
from apps.organizations.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Uso direto (D-393): ativa regras pelo Razão e gera lançamentos do que falta."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        organization = Organization.objects.filter(pk=options["organization"]).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        if not direct_use_enabled(organization):
            raise CommandError(
                "Escritório fora de CICA_DIRECT_USE_ORGANIZATION_IDS (ou demo/inativo)."
            )
        accounts = list(
            FinancialAccount.objects.filter(organization=organization, active=True).select_related(
                "company", "organization"
            )
        )
        if not options["apply"]:
            states: dict[str, int] = {}
            for account in accounts:
                for rule, _evidence in ledger_rules(account):
                    states[rule.state] = states.get(rule.state, 0) + 1
            self.stdout.write(
                json.dumps(
                    {
                        "apply": False,
                        "accounts": len(accounts),
                        "razao_rules": states,
                        "approved_entries": JournalEntry.objects.filter(
                            organization=organization, state=JournalEntry.State.APPROVED
                        ).count(),
                    },
                    sort_keys=True,
                )
            )
            return
        for account in accounts:
            try:
                create_drafts(account)
            except Exception:  # suggestions are refreshed best effort, as in D-392
                logger.exception("Sugestões DE-PARA não atualizadas para a conta %s", account.pk)
        results = run_for_organization(organization)
        totals: dict[str, int] = {}
        for item in results:
            for key, value in item.items():
                if isinstance(value, int):
                    totals[key] = totals.get(key, 0) + value
        totals["errors"] = sum(1 for item in results if "error" in item)
        totals["active_razao_rules"] = sum(
            1
            for account in accounts
            for rule, _evidence in ledger_rules(account)
            if rule.state == ReconciliationRule.State.ACTIVE
        )
        self.stdout.write(
            json.dumps({"apply": True, "accounts": len(accounts), **totals}, sort_keys=True)
        )
