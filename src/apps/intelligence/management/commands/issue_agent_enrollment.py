# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.agents import issue_enrollment
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Gera código único de 30 minutos para instalar um agente Domínio."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--minutes", type=int, default=30)

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            credentials = issue_enrollment(
                organization=organization, valid_for_minutes=options["minutes"]
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Código: {credentials.code}")
        self.stdout.write(f"Expira: {credentials.expires_at.isoformat()}")
