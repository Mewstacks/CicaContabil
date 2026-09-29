"""Rebuild every local module projection shown in the operational centre."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.audit.services import record_event
from apps.hub.dte_activities import sync_dte_activity
from apps.hub.models import (
    DctfWebDocument,
    DteMessage,
    FiscalGuide,
    OperationalActivity,
    ParcelamentoOperation,
    PayrollPeriodSnapshot,
    ReconciliationSourceFile,
    ReviewCase,
)
from apps.hub.module_activities import (
    sync_dctfweb_document_activity,
    sync_fiscal_guide_activity,
    sync_nfse_review_activity,
    sync_parcelamento_operation_activity,
    sync_triage_activity,
)
from apps.hub.payroll_activities import sync_payroll_activity
from apps.hub.reconciliation_activities import sync_reconciliation_activity
from apps.hub.reform_activities import sync_reform_activities
from apps.organizations.models import Organization
from apps.triage.models import TriageItem


class Command(BaseCommand):
    help = (
        "Recompõe projeções locais da central sem consultar fornecedores, emitir ou consumir saldo."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, type=UUID)

    @staticmethod
    def _recover(
        rows: Iterable[UUID], sync: Callable[[UUID], object]
    ) -> tuple[int, int]:
        completed = failures = 0
        for object_id in rows:
            try:
                sync(object_id)
                completed += 1
            except Exception:
                # Individual bridges keep their own transactional guarantees. Keep
                # advancing so a bad local record does not hide recoverable work.
                failures += 1
        return completed, failures

    def handle(self, *args: object, **options: object) -> None:
        office = Organization.objects.filter(pk=cast(UUID, options["organization"])).first()
        if office is None or office.is_demo:
            raise CommandError("Informe um escritório existente que não seja demonstração.")

        counts: dict[str, int] = {}
        failures: dict[str, int] = {}

        def recover(name: str, rows: Iterable[UUID], sync: Callable[[UUID], object]) -> None:
            counts[name], failures[name] = self._recover(rows, sync)

        recover(
            "nfse",
            ReviewCase.objects.filter(organization=office).values_list("pk", flat=True).iterator(),
            sync_nfse_review_activity,
        )
        recover(
            "triage",
            TriageItem.objects.filter(organization=office, company__isnull=False)
            .values_list("pk", flat=True)
            .iterator(),
            sync_triage_activity,
        )
        recover(
            "reconciliation",
            ReconciliationSourceFile.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator(),
            sync_reconciliation_activity,
        )
        payroll_pairs = (
            PayrollPeriodSnapshot.objects.filter(organization=office, company__organization=office)
            .order_by()
            .values_list("company_id", "competence")
            .distinct()
        )
        payroll_completed = payroll_failures = 0
        for company_id, competence in payroll_pairs.iterator():
            try:
                sync_payroll_activity(company_id=company_id, competence=competence)
                payroll_completed += 1
            except Exception:
                payroll_failures += 1
        counts["payroll"] = payroll_completed
        failures["payroll"] = payroll_failures
        recover(
            "dte",
            DteMessage.objects.filter(organization=office, company__organization=office)
            .values_list("pk", flat=True)
            .iterator(),
            sync_dte_activity,
        )
        recover(
            "radar",
            OperationalActivity.objects.filter(
                organization=office,
                company__organization=office,
                source_reform_alert__isnull=False,
            )
            .order_by()
            .values_list("source_reform_alert_id", flat=True)
            .distinct()
            .iterator(),
            lambda alert_id: sync_reform_activities(alert_id, organization_id=office.pk),
        )
        recover(
            "guides",
            FiscalGuide.objects.filter(organization=office).values_list("pk", flat=True).iterator(),
            sync_fiscal_guide_activity,
        )
        recover(
            "dctfweb",
            DctfWebDocument.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator(),
            sync_dctfweb_document_activity,
        )
        recover(
            "parcelamento",
            ParcelamentoOperation.objects.filter(organization=office)
            .values_list("pk", flat=True)
            .iterator(),
            sync_parcelamento_operation_activity,
        )
        summary = ", ".join(f"{name}={count}" for name, count in counts.items())
        failed = sum(failures.values())
        record_event(
            action="hub.activity.recovery_completed",
            organization=office,
            target=office,
            success=not failed,
            metadata={"domains": counts, "failures": failures},
        )
        self.stdout.write(
            "Central operacional recomposta localmente: "
            f"{summary}. Nenhuma chamada externa realizada."
        )
        if failed:
            failure_summary = ", ".join(
                f"{name}={count}" for name, count in failures.items() if count
            )
            raise CommandError(
                f"{failed} projeção(ões) falharam e precisam de análise: {failure_summary}."
            )
