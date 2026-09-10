# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.intelligence.retention import purge_expired_conversations
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Simula ou aplica retenção de conversas IA por escritório."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--apply", action="store_true", help="Apaga conversas elegíveis")

    def handle(self, *args, **options) -> None:
        for organization in Organization.objects.filter(is_active=True):
            result = purge_expired_conversations(organization=organization, apply=options["apply"])
            self.stdout.write(
                f"{organization.slug}: {result.eligible} elegível(is), "
                f"{result.deleted} removida(s)."
            )
        if not options["apply"]:
            self.stdout.write("Simulação concluída; use --apply para executar a remoção.")
