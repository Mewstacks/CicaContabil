"""D-400: confer the repeated-value groups already received, for one direct-use office.

Without ``--apply`` it lists the pairs the routine would confirm, writing nothing. With ``--apply``
it reruns the automatic confirmation (D-388/D-400) for every bank statement and every month whose
Razão already arrived, with the person who requested that Razão (or the technical user) as actor.
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.auto_confirm import _month_period, auto_confirm_exact
from apps.hub.direct_use import _ledger_months, direct_use_enabled
from apps.hub.models import FinancialAccount, ReconciliationSourceFile
from apps.hub.reconciliation_workbench import exact_conference_pairs
from apps.hub.title_robot import title_robot
from apps.intelligence.models import NativeLedgerCollection
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Valores repetidos (D-400): confere grupos do extrato e do Razão de mesmo tamanho."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--organization", required=True, type=uuid.UUID, help="UUID do escritório."
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        organization = Organization.objects.filter(pk=options["organization"]).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        if not direct_use_enabled(organization):
            raise CommandError(
                "Escritório fora de CICA_DIRECT_USE_ORGANIZATION_IDS (ou demo/inativo)."
            )
        pairs: list[dict[str, Any]] = []
        confirmed = 0
        for account in FinancialAccount.objects.filter(organization=organization, active=True):
            job = (
                NativeLedgerCollection.objects.filter(
                    financial_account=account, state=NativeLedgerCollection.State.IMPORTED
                )
                .select_related("requested_by")
                .order_by("-created_at")
                .first()
            )
            sources = ReconciliationSourceFile.objects.filter(
                organization=organization,
                financial_account=account,
                origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
            )
            for year, month_number in sorted(_ledger_months(account)):
                month = date(year, month_number, 1)
                for source in sources:
                    if options["apply"]:
                        actor = job.requested_by if job else title_robot()
                        confirmed += auto_confirm_exact(source=source, month=month, actor=actor)
                        continue
                    for movement, record in exact_conference_pairs(
                        source, _month_period(month), repeated=True
                    ):
                        pairs.append(
                            {
                                "date": movement.occurred_on.isoformat(),
                                "amount_cents": abs(movement.amount_cents),
                                "bank": (movement.original_description or movement.description)[
                                    :80
                                ],
                                "razao": (record.entry.history or "")[:80],
                            }
                        )
        result: dict[str, Any] = {"apply": bool(options["apply"])}
        if options["apply"]:
            result["confirmed"] = confirmed
        else:
            result["pairs"] = pairs
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=1))
