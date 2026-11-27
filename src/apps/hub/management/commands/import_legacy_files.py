"""Grava no storage do CICA os arquivos de um pacote do HubFedrizzi. Idempotente."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.hub.legacy_files import import_files
from apps.hub.legacy_import import BundleError
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Liga os arquivos do pacote (recibos, relatórios FAP) aos registros nativos."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--org", required=True, help="slug do escritório")
        parser.add_argument("--bundle", required=True, help="zip ou pasta do pacote completo")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        organization = Organization.objects.filter(slug=str(options["org"])).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        path = Path(str(options["bundle"]))
        if not path.exists():
            raise CommandError("Pacote não encontrado.")
        try:
            report = import_files(
                organization=organization, path=path, dry_run=bool(options["dry_run"])
            )
        except BundleError as exc:
            raise CommandError(str(exc)) from exc
        for line in report.lines():
            self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS("simulado" if options["dry_run"] else "concluído"))
