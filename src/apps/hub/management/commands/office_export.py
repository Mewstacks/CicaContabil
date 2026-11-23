"""Exporta os dados de um escritório em ZIP (LGPD art. 18, fim de contrato). Só leitura.

    manage.py office_export <slug> --output exportacao.zip
    manage.py office_export <slug> --dry-run        # só conta, não grava arquivo

Segredos nunca saem e o que ficou de fora consta no `manifest.json`. O arquivo tem dado pessoal e
fiscal: guardar e entregar por canal seguro, e apagar depois. Não apaga nada do escritório.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.offboarding import export_office
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Exporta os dados do escritório em um ZIP (somente leitura)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("slug", help="slug do escritório")
        parser.add_argument("--output", help="caminho do .zip a gravar")
        parser.add_argument("--dry-run", action="store_true", help="só conta, sem gravar arquivo")

    def handle(self, *args: Any, **options: Any) -> None:
        organization = Organization.objects.filter(slug=options["slug"]).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        if options["dry_run"] == bool(options["output"]):
            raise CommandError("Informe --output ou --dry-run (um dos dois).")
        destination = None if options["dry_run"] else Path(options["output"])
        if destination is not None and destination.exists():
            raise CommandError("O arquivo de saída já existe; escolha outro caminho.")
        result = export_office(organization, destination)
        for label, report in result.models.items():
            self.stdout.write(f"{label}: {report.rows}")
        self.stdout.write(f"equipe: {result.team_rows}")
        self.stdout.write(f"total: {result.total_rows}")
        if destination is not None:
            self.stdout.write(f"arquivo: {destination}")
            self.stdout.write(f"sha256: {result.sha256}")
