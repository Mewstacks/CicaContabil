from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.nfse_sync import refresh_nfse_facts
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = (
        "Grava lado, contraparte, valores, retenções e situação das NFS-e que ainda não os têm "
        "ou que foram lidas por uma versão anterior do extrator."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="Slug exato do escritório.")
        parser.add_argument("--batch", type=int, default=1000)

    def handle(self, *args: Any, **options: Any) -> None:
        slug = str(options["organization"]).strip()
        try:
            organization = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            raise CommandError("Escritório não encontrado pelo slug informado.") from exc
        total = 0
        while True:
            result = refresh_nfse_facts(limit=options["batch"], organization_id=organization.pk)
            total += result["updated"]
            self.stdout.write(json.dumps({"updated": total, "remaining": result["remaining"]}))
            if not result["updated"] or not result["remaining"]:
                break
