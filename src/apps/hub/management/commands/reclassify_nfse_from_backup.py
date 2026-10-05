from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.nfse_reclassification import reclassify_nfse_from_backup
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = (
        "Reaplica o backup Domínio às NFS-e salvas. Por padrão apenas calcula a prévia; "
        "use --apply para persistir evidências append-only."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="Slug exato do escritório.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste a reclassificação; sem esta opção nenhuma linha é alterada.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        slug = str(options["organization"]).strip()
        try:
            organization = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            raise CommandError("Escritório não encontrado pelo slug informado.") from exc
        try:
            summary = reclassify_nfse_from_backup(
                organization=organization,
                apply=bool(options["apply"]),
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(summary.payload(), ensure_ascii=False, sort_keys=True))
