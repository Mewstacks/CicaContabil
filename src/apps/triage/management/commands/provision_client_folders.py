"""Plan or queue the creation of client folders for the Windows agent (dry run by default)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.folders import queue_inventory, queue_provision


class Command(BaseCommand):
    help = "Planeja (padrão) ou enfileira (--apply) a criação das pastas dos clientes."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="slug do escritório")
        parser.add_argument("--company", help="código Domínio de uma empresa")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--inventory", action="store_true", help="enfileira só a leitura")

    def handle(self, *args: Any, **options: Any) -> None:
        office = Organization.objects.filter(slug=options["organization"]).first()
        if office is None:
            raise CommandError("Escritório não encontrado.")
        if options["inventory"]:
            job = queue_inventory(office)
            self.stdout.write(f"inventário na fila: {job.id}")
            return
        company = None
        if options["company"]:
            company = ClientCompany.objects.filter(
                organization=office, dominio_code=options["company"]
            ).first()
            if company is None:
                raise CommandError("Empresa não encontrada.")
        try:
            plans = queue_provision(office, company=company, apply=options["apply"])
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        verb = "enfileiradas" if options["apply"] else "planejadas"
        for item, paths in plans:
            self.stdout.write(f"{item.dominio_code} {item.name}: {len(paths)} pastas {verb}")
        self.stdout.write(f"{len(plans)} empresas")
