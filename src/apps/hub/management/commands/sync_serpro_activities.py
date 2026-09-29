"""Rebuild local activity projections from persisted Serpro operation outcomes."""

from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.models import DctfWebDocument, FiscalGuide, ParcelamentoOperation
from apps.hub.module_activities import (
    sync_dctfweb_document_activity,
    sync_fiscal_guide_activity,
    sync_parcelamento_operation_activity,
)
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Reconcilia atividades com resultados Serpro já persistidos, sem chamar o fornecedor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")
        counts = {"guides": 0, "documents": 0, "operations": 0}
        for pk in (
            FiscalGuide.objects.filter(organization=office).values_list("pk", flat=True).iterator()
        ):
            sync_fiscal_guide_activity(pk)
            counts["guides"] += 1
        for pk in (
            DctfWebDocument.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator()
        ):
            sync_dctfweb_document_activity(pk)
            counts["documents"] += 1
        for pk in (
            ParcelamentoOperation.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator()
        ):
            sync_parcelamento_operation_activity(pk)
            counts["operations"] += 1
        self.stdout.write(
            "Resultados reconciliados: "
            f"{counts['guides']} guias, {counts['documents']} documentos, "
            f"{counts['operations']} operações. Nenhuma chamada externa realizada."
        )
