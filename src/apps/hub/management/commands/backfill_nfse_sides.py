from __future__ import annotations

import json
from collections import Counter
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import NfseDocument, NfseDocumentSide
from apps.hub.nfse_sync import nfse_match_data
from apps.organizations.models import Organization

PAGE_SIZE = 200


class Command(BaseCommand):
    help = "Grava o lado (entrada/saída) e a contraparte das NFS-e que ainda não os têm."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="Slug exato do escritório.")

    def handle(self, *args: Any, **options: Any) -> None:
        slug = str(options["organization"]).strip()
        try:
            organization = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            raise CommandError("Escritório não encontrado pelo slug informado.") from exc
        # Paged by pk: production runs behind PgBouncer without server-side cursors.
        missing = list(
            NfseDocument.objects.filter(organization=organization, side__isnull=True)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        counts: Counter[str] = Counter()
        for start in range(0, len(missing), PAGE_SIZE):
            sides = []
            for document in NfseDocument.objects.filter(
                pk__in=missing[start : start + PAGE_SIZE]
            ).select_related("company"):
                data = nfse_match_data(document)
                direction = str(data.get("direction") or "")
                direction = direction if direction in {"provided", "taken"} else "unknown"
                counts[direction] += 1
                sides.append(
                    NfseDocumentSide(
                        organization_id=document.organization_id,
                        document=document,
                        direction=direction,
                        counterparty_ref=str(data.get("counterparty_ref") or "")[:80],
                        counterparty_name=str(data.get("counterparty_name") or "")[:160],
                    )
                )
            NfseDocumentSide.objects.bulk_create(sides, ignore_conflicts=True)
        self.stdout.write(json.dumps({"created": len(missing), **counts}, sort_keys=True))
