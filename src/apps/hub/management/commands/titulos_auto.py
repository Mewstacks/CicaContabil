"""D-394: interpret every captured title source of one direct-use office.

Without ``--apply`` it only counts captures per company, writing nothing.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.direct_use import direct_use_enabled
from apps.hub.models import ClientCompany
from apps.hub.title_auto import _captures, interpret_company
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Interpretação automática de títulos e baixas (D-394) para escritório em uso direto."

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
        companies = ClientCompany.objects.filter(
            organization=organization, active=True
        ).select_related("organization")
        if not options["apply"]:
            captures = {str(c.pk): len(_captures(c)) for c in companies}
            self.stdout.write(
                json.dumps(
                    {
                        "apply": False,
                        "companies_with_captures": sum(1 for n in captures.values() if n),
                        "captures": sum(captures.values()),
                    },
                    sort_keys=True,
                )
            )
            return
        totals: Counter[str] = Counter()
        for company in companies:
            for result in interpret_company(company):
                totals[str(result.get("status"))] += 1
                totals["installments_interpreted"] += int(result.get("interpreted", 0) or 0)
                totals["installments_skipped"] += int(result.get("skipped", 0) or 0)
        self.stdout.write(json.dumps({"apply": True, **totals}, sort_keys=True))
