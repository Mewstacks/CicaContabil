# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.models import AssistantSettings
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Armazena localmente a chave Claude cifrada; a chave não é enviada ao CRMew."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        api_key = getpass("Chave Claude da conta deste escritório (não será exibida): ").strip()
        if len(api_key) < 12:
            raise CommandError("Chave Claude inválida.")
        assistant_settings, _created = AssistantSettings.objects.get_or_create(
            organization=organization
        )
        assistant_settings.claude_api_key = api_key
        assistant_settings.save(update_fields=["claude_api_key", "updated_at"])
        self.stdout.write(self.style.SUCCESS("Chave Claude local cifrada configurada."))
