"""D-391: DE-PARA suggestions from the Razão booked by the office (propose, create, evaluate)."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.depara_ledger import create_drafts, evaluate, propose
from apps.hub.models import FinancialAccount


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "examples": result["examples"],
        "excluded_compound_or_partial": result["excluded_compound_or_partial"],
        "covered": result["covered"],
        "rejected": result["rejected"],
        "suggestions": [
            {
                "level": s.level,
                "label": s.label,
                "direction": s.direction,
                "debit": s.debit,
                "credit": s.credit,
                "support": s.support,
                "months": s.months,
            }
            for s in result["suggestions"]
        ],
        **{k: result[k] for k in ("created", "existing", "retired") if k in result},
    }


class Command(BaseCommand):
    help = "Sugere regras DE-PARA pelo Razão conferido (D-391): propose, create ou evaluate."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("action", choices=["propose", "create", "evaluate", "create-all"])
        parser.add_argument("--organization", required=True)
        parser.add_argument("--account", help="Obrigatório, exceto em create-all.")
        parser.add_argument("--month", help="AAAA-MM, para evaluate.")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["action"] == "create-all":
            totals = {"accounts": 0, "created": 0, "retired": 0, "failed": 0}
            for item in FinancialAccount.objects.select_related("company", "organization").filter(
                organization_id=options["organization"], active=True
            ):
                totals["accounts"] += 1
                try:
                    result = create_drafts(item)
                except Exception:  # one account never blocks the others
                    totals["failed"] += 1
                    continue
                totals["created"] += result["created"]
                totals["retired"] += result["retired"]
            self.stdout.write(json.dumps(totals, sort_keys=True))
            return
        if not options.get("account"):
            raise CommandError("Informe --account.")
        try:
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=options["account"], organization_id=options["organization"], active=True
            )
        except (FinancialAccount.DoesNotExist, ValueError) as exc:
            raise CommandError("Conta financeira não encontrada neste escritório.") from exc
        action = options["action"]
        try:
            if action == "propose":
                output = _summary(propose(account))
            elif action == "create":
                output = _summary(create_drafts(account))
            else:
                output = evaluate(account, month=options.get("month") or "")
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(output, ensure_ascii=False, sort_keys=True))
