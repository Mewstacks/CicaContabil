"""Rebuild local operational projections; no provider calls or imports."""

from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import ReviewCase
from apps.hub.module_activities import sync_nfse_review_activity
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Reconcilia atividades com revisões NFS-e locais de um escritório explícito."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")
        count = 0
        for pk in (
            ReviewCase.objects.filter(organization=office).values_list("pk", flat=True).iterator()
        ):
            sync_nfse_review_activity(pk)
            count += 1
        self.stdout.write(f"Revisões reconciliadas: {count}. Nenhuma chamada externa realizada.")
