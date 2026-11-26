"""Import a HubFedrizzi export bundle into one office. Idempotent; --dry-run rolls back."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.hub.legacy_import import BundleError, import_bundle
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Importa o pacote exportado do HubFedrizzi para um escritório."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--org", required=True, help="slug do escritório")
        parser.add_argument("--bundle", required=True, help="zip ou pasta do pacote")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--skip", action="append", default=[], help="tabela a pular (repetível)"
        )
        parser.add_argument(
            "--with-users", action="store_true", help="cria usuários sem senha (reset depois)"
        )

    def handle(self, *args: object, **options: object) -> None:
        organization = Organization.objects.filter(slug=str(options["org"])).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        path = Path(str(options["bundle"]))
        if not path.exists():
            raise CommandError("Pacote não encontrado.")
        try:
            report = import_bundle(
                organization=organization,
                path=path,
                dry_run=bool(options["dry_run"]),
                with_users=bool(options["with_users"]),
                skip=frozenset(str(name) for name in options["skip"]),  # type: ignore[attr-defined]
            )
        except BundleError as exc:
            raise CommandError(str(exc)) from exc
        for line in report.lines():
            self.stdout.write(line)
        self.stdout.write(
            self.style.SUCCESS("dry-run: nada gravado" if options["dry_run"] else "importado")
        )
