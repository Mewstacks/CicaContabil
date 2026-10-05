from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.hub.demo_scenario import populate_operations
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Populate only an existing demo office with synthetic operational scenarios."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        office = Organization.objects.filter(
            slug=options["slug"], is_demo=True, is_active=True
        ).first()
        if office is None:
            raise CommandError("O slug precisa identificar um escritório de demonstração ativo.")
        try:
            result = populate_operations(office)
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
