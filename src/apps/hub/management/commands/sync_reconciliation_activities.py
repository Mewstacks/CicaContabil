from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import ReconciliationSourceFile
from apps.hub.reconciliation_activities import sync_reconciliation_activity
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Reconcilia atividades com o tratamento local dos arquivos de um escritório."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")
        count = 0
        for pk in (
            ReconciliationSourceFile.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator()
        ):
            sync_reconciliation_activity(pk)
            count += 1
        self.stdout.write(f"Arquivos reconciliados: {count}. Nenhuma leitura externa realizada.")
