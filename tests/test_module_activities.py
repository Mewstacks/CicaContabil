from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    AccumulatorHistoryEntry,
    AccumulatorRule,
    ClientCompany,
    CompanyAccessGrant,
    DctfWebDocument,
    DteMessage,
    FiscalGuide,
    IntegrationArtifact,
    JournalEntry,
    MovementReconciliation,
    NormalizedMovement,
    OperationalActivity,
    OperationalEvidence,
    ParcelamentoOperation,
    PayrollPeriodSnapshot,
    ProductModule,
    ReconciliationDecision,
    ReformAlert,
)
from apps.hub.module_activities import (
    sync_dctfweb_document_activity,
    sync_fiscal_guide_activity,
    sync_nfse_review_activity,
    sync_parcelamento_operation_activity,
    sync_triage_activity,
)
from apps.hub.operations import completion_requirements
from apps.hub.reconciliation_service import create_source_file
from apps.hub.reform_activities import request_reform_analysis
from apps.hub.services import create_document_and_artifact
from apps.organizations.models import Membership, Organization
from apps.triage.models import TriageItem


class NfseActivityBridgeTests(TestCase):
    def test_unified_recovery_records_partial_failure_after_continuing(self):
        self.capture()
        output = StringIO()

        with (
            patch(
                "apps.hub.management.commands.recover_operational_center."
                "sync_nfse_review_activity",
                side_effect=RuntimeError("projection failed"),
            ),
            self.assertRaisesMessage(CommandError, "nfse=1"),
        ):
            call_command(
                "recover_operational_center", organization=str(self.office.pk), stdout=output
            )

        self.assertIn("guides=0", output.getvalue())
        recovery_event = AuditEvent.objects.get(action="hub.activity.recovery_completed")
        self.assertFalse(recovery_event.success)
        self.assertEqual(recovery_event.metadata["domains"]["nfse"], 0)
        self.assertEqual(recovery_event.metadata["failures"]["nfse"], 1)

    def test_unified_recovery_rebuilds_only_local_module_projections(self):
        self.capture()
        output = StringIO()

        call_command(
            "recover_operational_center", organization=str(self.office.pk), stdout=output
        )

        self.assertTrue(
            OperationalActivity.objects.filter(
                organization=self.office, source_nfse_review__isnull=False
            ).exists()
        )
        rendered = output.getvalue()
        self.assertIn("nfse=1", rendered)
        self.assertIn("guides=0", rendered)
        self.assertIn("Nenhuma chamada externa realizada", rendered)
        recovery_event = AuditEvent.objects.get(action="hub.activity.recovery_completed")
        self.assertTrue(recovery_event.success)
        self.assertEqual(recovery_event.metadata["domains"]["nfse"], 1)
        self.assertFalse(any(recovery_event.metadata["failures"].values()))

    def test_unified_recovery_rebuilds_every_persisted_local_projection_without_provider(self):
        with patch("apps.hub.services.sync_nfse_review_activity"):
            self.capture()
        triage = TriageItem.objects.create(
            organization=self.office,
            company=self.company,
            original_name="recovery.pdf",
            status="received",
            content_hash="b" * 64,
        )
        ProductModule.objects.create(
            organization=self.office,
            code=ProductModule.Code.RECONCILIATION,
            enabled=True,
        )
        with patch("apps.hub.reconciliation_service.sync_reconciliation_activity"):
            source, _, _ = create_source_file(
                organization=self.office,
                company=self.company,
                filename="recovery.csv",
                content=b"Data;Historico;Valor\n12/09/2026;Recover;100,00\n",
                origin="bank_statement",
            )
        payroll = PayrollPeriodSnapshot.objects.create(
            organization=self.office,
            company=self.company,
            competence=date(2026, 9, 1),
            source_kind=PayrollPeriodSnapshot.SourceKind.ERP,
            source_reference="recovery-payroll",
            gross_pay_cents=100_000,
        )
        message = DteMessage.objects.create(
            organization=self.office,
            company=self.company,
            source_isn="recovery-dte",
            subject="Comunicacao para recuperar",
        )
        FiscalGuide.objects.create(
            organization=self.office,
            company=self.company,
            kind=FiscalGuide.Kind.MEI,
            reference="unified-guide",
            competence="09/2026",
            due_on=timezone.localdate(),
            integra_service_key="pgmei.das",
            status=FiscalGuide.Status.ISSUED,
            issue_attempt=1,
            issued_at=timezone.now(),
        )
        DctfWebDocument.objects.create(
            organization=self.office,
            company=self.company,
            kind=DctfWebDocument.Kind.RECEIPT,
            competence="09/2026",
            service_key="dctfweb.recibo",
            status=DctfWebDocument.Status.AVAILABLE,
            attempt=1,
            completed_at=timezone.now(),
        )
        ParcelamentoOperation.objects.create(
            organization=self.office,
            company=self.company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            service_key="parcsn.pedidos",
            status=ParcelamentoOperation.Status.EMPTY,
            attempt=1,
            completed_at=timezone.now(),
        )
        self.assertFalse(OperationalActivity.objects.exists())
        output = StringIO()

        call_command(
            "recover_operational_center", organization=str(self.office.pk), stdout=output
        )

        rendered = output.getvalue()
        for expected in (
            "nfse=1", "triage=1", "reconciliation=1", "payroll=1", "dte=1",
            "guides=1", "dctfweb=1", "parcelamento=1",
        ):
            self.assertIn(expected, rendered)
        self.assertEqual(OperationalActivity.objects.filter(organization=self.office).count(), 8)
        self.assertEqual(OperationalActivity.objects.filter(source_triage_item=triage).count(), 1)
        self.assertEqual(
            OperationalActivity.objects.filter(source_reconciliation_file=source).count(), 1
        )
        self.assertEqual(
            OperationalActivity.objects.filter(source_payroll_snapshot=payroll).count(), 1
        )
        self.assertEqual(OperationalActivity.objects.filter(source_dte_message=message).count(), 1)
        self.assertEqual(
            OperationalActivity.objects.filter(
                organization=self.office,
                source_fiscal_guide__isnull=False,
            ).count(),
            1,
        )
        self.assertEqual(
            OperationalActivity.objects.filter(
                organization=self.office,
                source_dctfweb_document__isnull=False,
            ).count(),
            1,
        )
        self.assertEqual(
            OperationalActivity.objects.filter(
                organization=self.office,
                source_parcelamento_operation__isnull=False,
            ).count(),
            1,
        )
        call_command(
            "recover_operational_center", organization=str(self.office.pk), stdout=StringIO()
        )
        self.assertEqual(OperationalActivity.objects.filter(organization=self.office).count(), 8)

    def test_unified_recovery_reprojects_only_human_selected_radar_links(self):
        ProductModule.objects.create(
            organization=self.office,
            code=ProductModule.Code.REFORM,
            enabled=True,
        )
        alert = ReformAlert.objects.create(
            source=ReformAlert.Source.RFB,
            external_key="recovery-radar",
            title="Publicacao selecionada",
            source_url="https://www.gov.br/receitafederal/teste",
            relevance=ReformAlert.Relevance.FISCAL,
            content_hash="c" * 64,
        )
        membership = Membership.objects.get(organization=self.office, user=self.user)
        activity = request_reform_analysis(
            alert_id=alert.pk,
            company_id=self.company.pk,
            membership=membership,
            actor=self.user,
            reason="Avaliar impacto para esta empresa.",
        )
        event_count = activity.events.count()

        output = StringIO()
        call_command(
            "recover_operational_center", organization=str(self.office.pk), stdout=output
        )

        self.assertIn("radar=1", output.getvalue())
        activity.refresh_from_db()
        self.assertEqual(activity.events.count(), event_count)
        self.assertEqual(
            OperationalActivity.objects.filter(source_reform_alert=alert).count(), 1
        )

    def test_each_resolution_preserves_its_own_evidence_after_reopening(self):
        self.capture()
        activity = OperationalActivity.objects.get()
        review = activity.source_nfse_review
        for code in ("100", "200"):
            AccumulatorRule.objects.create(
                organization=self.office,
                company=self.company,
                name=f"Rule {code}",
                accumulator_code=code,
            )
        url = reverse("hub:resolve-review", args=[review.pk])
        self.assertEqual(self.client.post(url, {"accumulator_code": "100"}).status_code, 302)
        first = activity.evidence_items.get()
        self.assertIn("100", first.summary)
        first_time = first.observed_at
        review.refresh_from_db()
        review.status = "open"
        review.save(update_fields=["status"])
        sync_nfse_review_activity(review.pk)
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "pending")
        self.assertEqual(self.client.post(url, {"accumulator_code": "200"}).status_code, 302)
        activity.refresh_from_db()
        review.refresh_from_db()
        self.assertEqual(activity.work_status, "completed")
        second = activity.evidence_items.exclude(pk=first.pk).get()
        self.assertIn("200", second.summary)
        self.assertEqual(second.observed_at, review.resolved_at)
        self.assertEqual(second.recorded_by_id, self.user.pk)
        first.refresh_from_db()
        self.assertEqual(first.observed_at, first_time)
        self.assertIn("100", first.summary)
        count = activity.events.count()
        sync_nfse_review_activity(review.pk)
        self.assertEqual(activity.evidence_items.count(), 2)
        self.assertEqual(activity.events.count(), count)
        history = AccumulatorHistoryEntry.objects.filter(
            organization=self.office,
            source=AccumulatorHistoryEntry.Source.HUMAN_REVIEW,
        )
        self.assertEqual(set(history.values_list("accumulator_code", flat=True)), {"100", "200"})
        self.assertEqual(history.count(), 2)
        self.assertEqual(completion_requirements(activity), ())

    def setUp(self):
        self.user = User.objects.create_user("bridge@example.test", "safe-password-123")
        self.office = Organization.objects.create(name="Bridge", slug="bridge")
        Membership.objects.create(organization=self.office, user=self.user, role="owner")
        self.company = ClientCompany.objects.create(organization=self.office, name="Empresa")
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.pk)
        session.save()

    def capture(self):
        return create_document_and_artifact(
            company=self.company,
            original_xml="<nfse id='bridge' />",
            normalized_data={"issued_at": "2026-09-12T12:00:00-03:00"},
        )

    def test_reconciliation_origin_scopes_file_and_preserves_search(self):
        ProductModule.objects.create(
            organization=self.office,
            code=ProductModule.Code.RECONCILIATION,
            enabled=True,
        )
        source, run, _ = create_source_file(
            organization=self.office,
            company=self.company,
            filename="scoped.csv",
            content=b"Data;Historico;Valor\n12/09/2026;First;100,00\n",
            origin="bank_statement",
        )
        other, other_run, _ = create_source_file(
            organization=self.office,
            company=self.company,
            filename="another.csv",
            content=b"Data;Historico;Valor\n12/09/2026;Other;200,00\n",
            origin="bank_statement",
        )
        activity = source.operational_activity
        movement = NormalizedMovement.objects.create(
            organization=self.office,
            company=self.company,
            source_file=source,
            run=run,
            source_key="1",
            amount_cents=10000,
            description="Selected movement",
        )
        NormalizedMovement.objects.create(
            organization=self.office,
            company=self.company,
            source_file=other,
            run=other_run,
            source_key="1",
            amount_cents=20000,
            description="Other movement",
        )
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, "Abrir arquivo na Conciliação")
        self.assertNotContains(detail, "Concluir atividade")
        page = self.client.get(detail.context["activity_origin"]["url"])
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["selected_reconciliation_source"], source)
        self.assertEqual([r.pk for r in page.context["reconciliation_runs"]], [run.pk])
        self.assertEqual([m.pk for m in page.context["normalized_movements"]], [movement.pk])
        self.assertContains(page, 'name="source_file"')
        self.assertContains(page, "Voltar à atividade")
        entry = JournalEntry.objects.create(
            organization=self.office,
            company=self.company,
            occurred_on=timezone.localdate(),
            history="Original entry",
        )
        relation = MovementReconciliation.objects.create(
            organization=self.office,
            movement=movement,
            entry=entry,
            amount_cents=10000,
        )
        for _ in range(21):
            ReconciliationDecision.objects.create(
                organization=self.office,
                reconciliation=relation,
                state="undone",
                amount_cents=10000,
                evidence={"note": "<script>unsafe</script>"},
                is_legacy_snapshot=True,
            )
        movement_url = reverse("hub:reconciliation-movement", args=[movement.pk])
        history = self.client.get(movement_url, {"candidate_page": "1"})
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, "Histórico das decisões")
        self.assertContains(history, "Autor não registrado")
        self.assertContains(history, "Registro legado preservado")
        self.assertContains(history, "Data da decisão não registrada")
        self.assertNotContains(history, "<script>unsafe</script>")
        self.assertContains(history, "&lt;script&gt;unsafe&lt;/script&gt;")
        self.assertEqual(len(history.context["reconciliation_decision_page"]), 20)
        self.assertContains(history, "candidate_page=1&amp;decision_page=2#decisoes")
        history = self.client.get(movement_url, {"decision_page": "2", "candidate_page": "1"})
        self.assertEqual(len(history.context["reconciliation_decision_page"]), 1)
        self.assertEqual(relation.decisions.count(), 21)
        member = Membership.objects.get(organization=self.office, user=self.user)
        member.role = "auditor"
        member.save(update_fields=["role"])
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=member,
            company=self.company,
            modules=[ProductModule.Code.RECONCILIATION],
            capabilities=["*"],
        )
        readonly = self.client.get(movement_url)
        self.assertContains(readonly, "Histórico das decisões")
        self.assertNotContains(readonly, "Salvar revisão")
        self.assertNotContains(readonly, 'name="evidence_note"')
        self.assertEqual(self.client.post(movement_url, {"action": "save"}).status_code, 403)
        member.role = "owner"
        member.save(update_fields=["role"])
        page = self.client.get(
            reverse("hub:reconciliation"),
            {
                "source_file": source.pk,
                "movement_q": "test",
                "processing_page": "2",
            },
        )
        self.assertContains(page, f"?source_file={source.pk}#movimentos")
        outsider = Organization.objects.create(name="Other", slug="source-outsider")
        other.organization = outsider
        other.save(update_fields=["organization"])
        for invalid in [str(other.pk), "invalid"]:
            response = self.client.get(reverse("hub:reconciliation"), {"source_file": invalid})
            self.assertEqual(response.status_code, 404)

    def test_capture_decision_and_replay_keep_single_activity_and_human_proof(self):
        document, _, review = self.capture()
        activity = OperationalActivity.objects.get(source_nfse_review=review)
        self.assertEqual(activity.competence.isoformat(), "2026-09-01")
        self.assertIsNone(activity.assigned_to)
        self.assertIsNone(activity.legal_due_on)
        self.assertIn("módulo NFS-e", completion_requirements(activity)[0])
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, reverse("hub:review-detail", args=[review.pk]))
        self.assertContains(detail, "Abrir revisão de NFS-e")
        self.assertNotContains(detail, "Concluir atividade")
        source = self.client.get(detail.context["activity_origin"]["url"])
        self.assertEqual(source.status_code, 200)
        self.capture()
        sync_nfse_review_activity(review.pk)
        self.assertEqual(OperationalActivity.objects.count(), 1)
        self.assertEqual(activity.events.count(), 1)
        AccumulatorRule.objects.create(
            organization=self.office,
            company=self.company,
            name="Validado",
            accumulator_code="100",
        )
        response = self.client.post(
            reverse("hub:resolve-review", args=[review.pk]),
            {
                "accumulator_code": "100",
            },
        )
        self.assertEqual(response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "completed")
        self.assertEqual(activity.processing_status, "processed")
        self.assertEqual(activity.obligation_status, "not_applicable")
        self.assertEqual(activity.completed_by, self.user)
        self.assertFalse(activity.requires_processing_closed)
        self.assertEqual(completion_requirements(activity), ())
        sync_nfse_review_activity(review.pk)
        self.assertEqual(activity.evidence_items.count(), 1)
        self.assertEqual(activity.events.count(), 2)
        self.assertEqual(IntegrationArtifact.objects.filter(document=document).count(), 1)
        evidence = OperationalEvidence.objects.get(activity=activity)
        self.assertEqual(evidence.recorded_by, self.user)
        self.assertIn("Não comprova importação", evidence.summary)

    def test_bridge_failure_rolls_back_review_artifact_and_accumulator_history(self):
        _, _, review = self.capture()
        AccumulatorRule.objects.create(
            organization=self.office,
            company=self.company,
            name="Validado",
            accumulator_code="100",
        )
        with (
            patch("apps.hub.views.sync_nfse_review_activity", side_effect=RuntimeError("failure")),
            self.assertRaises(RuntimeError),
        ):
            self.client.post(
                reverse("hub:resolve-review", args=[review.pk]), {"accumulator_code": "100"}
            )
        review.refresh_from_db()
        self.assertEqual(review.status, "open")
        self.assertFalse(IntegrationArtifact.objects.exists())
        self.assertFalse(AccumulatorHistoryEntry.objects.exists())
        self.assertEqual(review.operational_activity.work_status, "pending")

    def test_invalid_resolution_and_reopening_do_not_forge_completion(self):
        _, _, review = self.capture()
        review.status = "resolved"
        review.save()
        with self.assertRaises(ValidationError):
            sync_nfse_review_activity(review.pk)
        review.status = "open"
        review.save()
        activity = review.operational_activity
        activity.work_status = "completed"
        activity.save()
        sync_nfse_review_activity(review.pk)
        activity.refresh_from_db()
        self.assertEqual(activity.work_status, "pending")
        self.assertTrue(activity.events.filter(event_type="module_reopened").exists())

    def test_demo_capture_does_not_create_persisted_operational_task(self):
        self.office.is_demo = True
        self.office.save()
        self.capture()
        self.assertFalse(OperationalActivity.objects.exists())

    def test_recovery_command_and_original_emission_month(self):
        with patch("apps.hub.services.sync_nfse_review_activity"):
            _, _, review = create_document_and_artifact(
                company=self.company,
                original_xml="<nfse id='month-boundary' />",
                normalized_data={"issued_at": "2026-08-31T23:50:00-03:00"},
            )
        self.assertFalse(OperationalActivity.objects.exists())
        for _ in range(2):
            call_command("sync_nfse_activities", organization=self.office.pk, stdout=StringIO())
        activity = OperationalActivity.objects.get(source_nfse_review=review)
        self.assertEqual(activity.competence.isoformat(), "2026-08-01")
        self.assertEqual(activity.events.count(), 1)

    def test_triage_requires_archive_proof_and_recovers_without_duplicates(self):
        item = TriageItem.objects.create(
            organization=self.office,
            company=self.company,
            original_name="documento.pdf",
            status="pronto_para_arquivar",
            content_hash="a" * 64,
        )
        activity = sync_triage_activity(item.pk)
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, reverse("hub:triage-item", args=[item.pk]))
        self.assertNotContains(detail, "Concluir atividade")
        self.assertEqual(activity.work_status, "pending")
        self.assertIn("Confirme o arquivamento", completion_requirements(activity)[0])
        item.status = "falha_de_arquivamento"
        item.save()
        self.assertEqual(sync_triage_activity(item.pk).work_status, "blocked")
        item.status = "arquivado"
        item.save()
        self.assertEqual(sync_triage_activity(item.pk).work_status, "blocked")
        item.archived_at = timezone.now()
        item.destination_path = "local-confirmado/documento.pdf"
        item.destination_hash = item.content_hash
        item.save()
        activity = sync_triage_activity(item.pk)
        self.assertEqual(activity.work_status, "completed")
        self.assertEqual(completion_requirements(activity), ())
        event_count = activity.events.count()
        call_command("sync_triage_activities", organization=self.office.pk, stdout=StringIO())
        self.assertEqual(activity.events.count(), event_count)
        self.assertEqual(activity.evidence_items.count(), 1)
        self.assertEqual(activity.obligation_status, "not_applicable")

    def test_guide_projection_keeps_issuance_open_and_separates_payment(self):
        guide = FiscalGuide.objects.create(
            organization=self.office,
            company=self.company,
            kind=FiscalGuide.Kind.DAS,
            reference="bridge-guide",
            competence="09/2026",
            due_on=timezone.localdate(),
            integra_service_key="pgdasd.das",
            status=FiscalGuide.Status.READY,
        )
        activity = sync_fiscal_guide_activity(guide.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.PENDING)
        self.assertEqual(activity.payment_status, OperationalActivity.PaymentStatus.EXPECTED)
        self.assertEqual(activity.competence.isoformat(), "2026-09-01")
        self.assertIsNone(activity.assigned_to)
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, "Abrir guia")
        self.assertContains(detail, reverse("hub:guide-detail", args=[guide.pk]))
        guide.status = FiscalGuide.Status.ISSUED
        guide.issued_at = timezone.now()
        guide.issue_attempt = 1
        guide.issue_requested_by = self.user
        guide.save()
        activity = sync_fiscal_guide_activity(guide.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.PENDING)
        self.assertEqual(activity.assigned_to, self.user)
        self.assertEqual(activity.payment_status, OperationalActivity.PaymentStatus.GUIDE_AVAILABLE)
        self.assertEqual(
            activity.obligation_status, OperationalActivity.ObligationStatus.NOT_APPLICABLE
        )
        self.assertEqual(activity.evidence_items.count(), 1)
        event_count = activity.events.count()
        sync_fiscal_guide_activity(guide.pk)
        self.assertEqual(activity.events.count(), event_count)
        guide.status = FiscalGuide.Status.UNKNOWN
        guide.save(update_fields=["status"])
        activity = sync_fiscal_guide_activity(guide.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.BLOCKED)
        self.assertIn("confirmado", activity.blocked_reason)

    def test_dctfweb_projection_completes_document_retrieval_without_acceptance(self):
        document = DctfWebDocument.objects.create(
            organization=self.office,
            company=self.company,
            kind=DctfWebDocument.Kind.RECEIPT,
            competence="09/2026",
            service_key="dctfweb.recibo",
            status=DctfWebDocument.Status.QUEUED,
            requested_by=self.user,
            attempt=1,
        )
        activity = sync_dctfweb_document_activity(document.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.IN_PROGRESS)
        detail = self.client.get(reverse("hub:activity-detail", args=[activity.pk]))
        self.assertContains(detail, "Abrir central de Guias e DCTFWeb")
        document.status = DctfWebDocument.Status.AVAILABLE
        document.completed_at = timezone.now()
        document.save(update_fields=["status", "completed_at"])
        activity = sync_dctfweb_document_activity(document.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.COMPLETED)
        self.assertEqual(
            activity.obligation_status, OperationalActivity.ObligationStatus.NOT_APPLICABLE
        )
        self.assertEqual(activity.evidence_items.count(), 1)
        document.status = DctfWebDocument.Status.UNKNOWN
        document.save(update_fields=["status"])
        activity = sync_dctfweb_document_activity(document.pk)
        assert activity is not None
        self.assertEqual(activity.work_status, OperationalActivity.WorkStatus.BLOCKED)

    def test_parcsn_projection_distinguishes_das_from_completed_consultation(self):
        query = ParcelamentoOperation.objects.create(
            organization=self.office,
            company=self.company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            service_key="parcsn.pedidos",
            status=ParcelamentoOperation.Status.AVAILABLE,
            requested_by=self.user,
            attempt=1,
            completed_at=timezone.now(),
        )
        query_activity = sync_parcelamento_operation_activity(query.pk)
        assert query_activity is not None
        self.assertEqual(query_activity.work_status, OperationalActivity.WorkStatus.COMPLETED)
        das = ParcelamentoOperation.objects.create(
            organization=self.office,
            company=self.company,
            kind=ParcelamentoOperation.Kind.DAS,
            competence="202609",
            service_key="parcsn.das",
            status=ParcelamentoOperation.Status.AVAILABLE,
            requested_by=self.user,
            attempt=1,
            completed_at=timezone.now(),
        )
        das_activity = sync_parcelamento_operation_activity(das.pk)
        assert das_activity is not None
        self.assertEqual(das_activity.work_status, OperationalActivity.WorkStatus.PENDING)
        self.assertEqual(
            das_activity.payment_status, OperationalActivity.PaymentStatus.GUIDE_AVAILABLE
        )
        self.assertEqual(
            das_activity.obligation_status, OperationalActivity.ObligationStatus.NOT_APPLICABLE
        )
        detail = self.client.get(reverse("hub:activity-detail", args=[das_activity.pk]))
        self.assertContains(detail, "Abrir parcelamentos")

    def test_serpro_recovery_command_rebuilds_every_persisted_projection(self):
        FiscalGuide.objects.create(
            organization=self.office,
            company=self.company,
            kind=FiscalGuide.Kind.MEI,
            reference="recovery-guide",
            competence="09/2026",
            due_on=timezone.localdate(),
            integra_service_key="pgmei.das",
            status=FiscalGuide.Status.ISSUED,
            issue_attempt=1,
            issued_at=timezone.now(),
        )
        DctfWebDocument.objects.create(
            organization=self.office,
            company=self.company,
            kind=DctfWebDocument.Kind.DECLARATION,
            competence="09/2026",
            service_key="dctfweb.declaracao_completa",
            status=DctfWebDocument.Status.AVAILABLE,
            attempt=1,
            completed_at=timezone.now(),
        )
        ParcelamentoOperation.objects.create(
            organization=self.office,
            company=self.company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            service_key="parcsn.pedidos",
            status=ParcelamentoOperation.Status.EMPTY,
            attempt=1,
            completed_at=timezone.now(),
        )
        stdout = StringIO()
        call_command("sync_serpro_activities", organization=self.office.pk, stdout=stdout)
        self.assertIn("1 guias, 1 documentos, 1 operações", stdout.getvalue())
        self.assertEqual(OperationalActivity.objects.count(), 3)
        call_command("sync_serpro_activities", organization=self.office.pk, stdout=StringIO())
        self.assertEqual(OperationalActivity.objects.count(), 3)

    def test_triage_without_company_and_cross_office_links_never_gain_scope(self):
        item = TriageItem.objects.create(organization=self.office, original_name="unknown.pdf")
        self.assertIsNone(sync_triage_activity(item.pk))
        other = Organization.objects.create(name="Other", slug="other-triage")
        company = ClientCompany.objects.create(organization=other, name="Other")
        item.company = company
        item.save()
        with self.assertRaises(ValidationError):
            sync_triage_activity(item.pk)
        self.assertFalse(OperationalActivity.objects.exists())

    def test_antimalware_without_unix_socket_support_fails_explicitly(self):
        from apps.triage.security import ClamdScanner, ScannerUnavailable

        with (
            patch("apps.triage.security.socket.AF_UNIX", None, create=True),
            self.assertRaisesMessage(ScannerUnavailable, "Configure a porta local"),
        ):
            ClamdScanner(local_socket="/local/clamd.sock")._connect()
