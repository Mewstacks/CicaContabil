from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import PayrollPeriodSnapshot
from apps.hub.payroll_activities import sync_payroll_activity
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Recompõe atividades de conferência a partir das fotografias locais da folha."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")
        pairs = (
            PayrollPeriodSnapshot.objects.filter(organization=office, company__organization=office)
            .order_by()
            .values_list("company_id", "competence")
            .distinct()
        )
        count = 0
        for company_id, competence in pairs.iterator():
            sync_payroll_activity(company_id=company_id, competence=competence)
            count += 1
        self.stdout.write(f"Competências conferidas: {count}. Nenhuma consulta externa realizada.")
