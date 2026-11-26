"""Refaz a conferência dos documentos que esperavam uma guia ou um documento par.

A referência pode chegar depois do recibo (a guia da Central é importada no dia seguinte):
nada dispara por si, então este comando fecha a lacuna e pode rodar em agenda.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.closing import services
from apps.closing.models import ClosingConference, ClosingDocument
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Reconfere documentos sem referência (um escritório, ou todos com o módulo ligado)."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--office", default="", help="Slug do escritório; vazio = todos.")

    def handle(self, *args: object, **options: Any) -> None:
        offices = Organization.objects.filter(
            is_active=True,
            productmodule__code="closing",
            productmodule__enabled=True,
        )
        if options["office"]:
            offices = offices.filter(slug=options["office"])
            if not offices.exists():
                raise CommandError("Escritório não encontrado ou sem o módulo ligado.")
        redone = 0
        for office in offices.distinct():
            pairs = (
                ClosingDocument.objects.filter(
                    organization=office,
                    state=ClosingDocument.State.ACCEPTED,
                    company__isnull=False,
                    competence__isnull=False,
                    conferences__outcome=ClosingConference.Outcome.WAITING,
                )
                .values_list("company_id", "competence")
                .distinct()
            )
            for company_id, competence in pairs:
                company = office.clientcompany_set.filter(pk=company_id).first()
                redone += services.reevaluate_waiting(
                    office, company=company, competence=competence
                )
        self.stdout.write(self.style.SUCCESS(f"{redone} documentos reconferidos."))
