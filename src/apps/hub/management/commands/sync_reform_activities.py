from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import OperationalActivity
from apps.hub.reform_activities import sync_reform_activities
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Recompõe análises do Radar já vinculadas, sem coleta externa."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")
        ids = (
            OperationalActivity.objects.filter(
                organization=office,
                company__organization=office,
                source_reform_alert__isnull=False,
            )
            .order_by()
            .values_list("source_reform_alert_id", flat=True)
            .distinct()
        )
        count = sum(sync_reform_activities(pk, organization_id=office.pk) for pk in ids)
        self.stdout.write(f"Análises conferidas: {count}. Nenhuma coleta externa realizada.")
