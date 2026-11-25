from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.crosscheck.demo import populate_demo as populate_crosscheck
from apps.organizations.models import Membership, Organization
from apps.profitability.demo import populate_demo as populate_profitability


class Command(BaseCommand):
    help = "Preenche os módulos do escritório de demonstração com dados fictícios (repetível)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", default="escritorio-demo")

    def handle(self, *args: Any, **options: Any) -> None:
        office = Organization.objects.filter(
            slug=options["slug"], is_demo=True, is_active=True
        ).first()
        if office is None:
            raise CommandError("O slug precisa identificar um escritório de demonstração ativo.")
        owner = (
            User.objects.filter(
                organization_memberships__organization=office,
                organization_memberships__role=Membership.Role.OWNER,
            ).first()
            or User.objects.filter(organization_memberships__organization=office).first()
        )
        if owner is None:
            raise CommandError("O escritório de demonstração não tem usuário.")
        self.stdout.write(f"Lucrums: {populate_profitability(office)}")
        self.stdout.write(f"Contraprova: {populate_crosscheck(office, owner)} conferências")
