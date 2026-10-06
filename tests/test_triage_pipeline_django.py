from __future__ import annotations

from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, OperationalActivity
from apps.organizations.models import Membership, Organization
from apps.triage.extraction import extract_item
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import (
    ChecklistEntry,
    DestinationProfile,
    DocumentType,
    Mailbox,
    TriageItem,
)
from apps.triage.security import ScannerUnavailable, ScanVerdict, scan_quarantined_item
from apps.triage.services import (
    archive_internal,
    decide_item,
    reprocess_item,
    update_review_fields,
)
from apps.triage.tasks import MAX_PIPELINE_ATTEMPTS, process_triage_item, recover_triage_pipeline
from apps.triage.transitions import InvalidTransition, TriageStatus


class CleanScanner:
    def scan(self, stream: object) -> ScanVerdict:
        return ScanVerdict("clean", "test")


class BrokenScanner:
    def scan(self, stream: object) -> ScanVerdict:
        raise ScannerUnavailable("offline")


class TriagePipelineTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Office", slug="triage-pipeline")
        self.company = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Sol",
            cnpj_masked="12.345.678/0001-95",
            dominio_code="417",
        )
        self.other_company = ClientCompany.objects.create(
            organization=self.office, name="Mercado Lua", dominio_code="533"
        )
        self.extrato = DocumentType.objects.create(
            organization=self.office,
            code="extrato-bancario",
            label="Extrato bancário",
            name_template="{codigo}_EXTRATO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DocumentType.objects.create(
            organization=self.office,
            code="folha",
            label="Folha de pagamento",
            name_template="{codigo}_FOLHA_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DestinationProfile.objects.create(organization=self.office)
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.IMAP,
            address="docs@office.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
        )
        self.user = User.objects.create_user("reviewer@office.test", "safe-password-123")

    def _released(self, *, filename: str, payload: bytes, subject: str = "") -> TriageItem:
        item = receive_email_attachment(
            mailbox=self.mailbox,
            message_id=f"m-{filename}",
            part_id="1",
            filename=filename,
            payload=payload,
            subject=subject,
            received_at=timezone.now(),
        ).item
        scan_quarantined_item(item=item, scanner=CleanScanner())
        return TriageItem.objects.get(pk=item.pk)

    def test_extraction_suggests_company_type_period_and_name_from_evidence(self) -> None:
        payload = b"<extrato><cnpj>12.345.678/0001-95</cnpj><ref>09/2026</ref></extrato>"
        item = self._released(filename="extrato_banco.xml", payload=payload)

        item = extract_item(item_id=item.pk)

        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.company, self.company)
        self.assertEqual(item.document_type, self.extrato)
        self.assertEqual(item.period_label, "2026-09")
        self.assertEqual(item.final_name, "417_EXTRATO_202609.xml")
        self.assertEqual(item.ai_fields["Empresa"]["evidencia"], "CNPJ no conteúdo")

    def test_ambiguous_evidence_leaves_fields_empty_for_review(self) -> None:
        payload = b"<doc><a>12.345.678/0001-95</a><p>08/2026</p><p>09/2026</p></doc>"
        item = self._released(filename="documento.xml", payload=payload)

        item = extract_item(item_id=item.pk)

        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.company, self.company)
        self.assertIsNone(item.document_type)
        self.assertEqual(item.period_label, "")
        self.assertEqual(item.final_name, "")

    def test_extraction_never_runs_before_release_and_is_idempotent(self) -> None:
        item = receive_email_attachment(
            mailbox=self.mailbox,
            message_id="m-raw",
            part_id="1",
            filename="extrato.xml",
            payload=b"<a/>",
            received_at=timezone.now(),
        ).item
        self.assertEqual(extract_item(item_id=item.pk).status, TriageStatus.QUARANTINED)
        scan_quarantined_item(item=item, scanner=CleanScanner())
        first = extract_item(item_id=item.pk)
        events = first.events.count()
        second = extract_item(item_id=item.pk)
        self.assertEqual(second.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(second.events.count(), events)

    def test_ingest_dispatches_scan_and_extraction_after_commit(self) -> None:
        with (
            patch("apps.triage.security.ClamdScanner.from_settings", return_value=CleanScanner()),
            self.captureOnCommitCallbacks(execute=True),
        ):
            item = receive_email_attachment(
                mailbox=self.mailbox,
                message_id="m-auto",
                part_id="1",
                filename="417_extrato_2026-09.xml",
                payload=b"<extrato/>",
                received_at=timezone.now(),
            ).item

        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.company, self.company)
        self.assertEqual(item.final_name, "417_EXTRATO_202609.xml")

    @override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=0)
    def test_missing_scanner_keeps_quarantine_and_recovery_does_not_loop(self) -> None:
        item = receive_email_attachment(
            mailbox=self.mailbox,
            message_id="m-noscan",
            part_id="1",
            filename="extrato.xml",
            payload=b"<a/>",
            received_at=timezone.now(),
        ).item

        self.assertEqual(process_triage_item(str(item.pk)), TriageStatus.QUARANTINED)
        item.refresh_from_db()
        self.assertEqual(item.safety_scan.verdict, "error")
        events = item.events.count()
        recover_triage_pipeline()
        self.assertEqual(item.events.count(), events)

    def test_reviewer_corrects_fields_then_archive_marks_checklist(self) -> None:
        item = extract_item(item_id=self._released(filename="anexo.xml", payload=b"<a/>").pk)
        self.assertIsNone(item.company)

        item = update_review_fields(
            item=item,
            actor=self.user,
            company=self.other_company,
            document_type=self.extrato,
            period_label="2026-09",
            counterparty_token="",
            final_name="533_EXTRATO_202609.xml",
        )
        self.assertTrue(item.events.filter(note__startswith="Corrigido: empresa").exists())

        decide_item(item=item, actor=self.user, decision="archive", reason="")
        archive_internal(item=item, actor=self.user)

        entry = ChecklistEntry.objects.get(
            company=self.other_company, document_type=self.extrato, period_label="2026-09"
        )
        self.assertEqual(entry.triage_item_id, item.pk)
        self.assertIsNotNone(entry.received_at)

    def test_review_fields_reject_bad_period_and_foreign_company(self) -> None:
        from django.core.exceptions import ValidationError

        item = extract_item(item_id=self._released(filename="a.xml", payload=b"<a/>").pk)
        foreign = ClientCompany.objects.create(
            organization=Organization.objects.create(name="Other", slug="triage-other"),
            name="Alheia",
        )
        for kwargs in (
            {"period_label": "09/2026", "company": None},
            {"period_label": "", "company": foreign},
        ):
            with self.assertRaises(ValidationError):
                update_review_fields(
                    item=item,
                    actor=self.user,
                    document_type=None,
                    counterparty_token="",
                    final_name="",
                    **kwargs,
                )


class TriageReviewScreenTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Office", slug="triage-screen")
        self.user = User.objects.create_user("owner@screen.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria Sol", dominio_code="417"
        )
        self.document_type = DocumentType.objects.create(
            organization=self.office,
            code="extrato",
            label="Extrato",
            name_template="{codigo}_EXTRATO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DestinationProfile.objects.create(organization=self.office)
        mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.IMAP,
            address="docs@screen.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
        )
        item = receive_email_attachment(
            mailbox=mailbox,
            message_id="m-screen",
            part_id="1",
            filename="anexo.xml",
            payload=b"<a>conteudo</a>",
            received_at=timezone.now(),
        ).item
        scan_quarantined_item(item=item, scanner=CleanScanner())
        self.item = extract_item(item_id=item.pk)
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def _enable_triage(self) -> None:
        from apps.hub.models import ProductModule

        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.TRIAGE, enabled=True
        )

    def test_reviewer_previews_and_corrects_unidentified_file(self) -> None:
        self._enable_triage()
        url = reverse("hub:triage-item", args=[self.item.id])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, reverse("hub:triage-preview", args=[self.item.id]))
        self.assertContains(page, 'name="final_name"')

        preview = self.client.get(reverse("hub:triage-preview", args=[self.item.id]))
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("sandbox", preview["Content-Security-Policy"])
        self.assertEqual(preview.content, b"<a>conteudo</a>")

        response = self.client.post(
            url,
            {
                "decision": "update_fields",
                "company": self.company.id,
                "document_type": self.document_type.id,
                "period_label": "2026-09",
                "counterparty_token": "",
                "final_name": "417_EXTRATO_202609.xml",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.company, self.company)
        self.assertEqual(self.item.final_name, "417_EXTRATO_202609.xml")

    def test_quarantined_file_has_no_preview(self) -> None:
        self._enable_triage()
        TriageItem.objects.filter(pk=self.item.pk).update(status=TriageStatus.QUARANTINED)
        response = self.client.get(reverse("hub:triage-preview", args=[self.item.id]))
        self.assertEqual(response.status_code, 404)


class TriageRetryDedupeReasonTests(TestCase):
    """Audit A-02 gaps: attempt cap + Reprocessar, content dedupe, correction reason."""

    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Office", slug="triage-retry")
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria Sol", dominio_code="417"
        )
        self.other_company = ClientCompany.objects.create(
            organization=self.office, name="Mercado Lua", dominio_code="533"
        )
        self.extrato = DocumentType.objects.create(
            organization=self.office,
            code="extrato",
            label="Extrato",
            name_template="{codigo}_EXTRATO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DestinationProfile.objects.create(organization=self.office)
        self.mailbox = self._mailbox(self.office, "docs@retry.test")
        self.user = User.objects.create_user("owner@retry.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )

    @staticmethod
    def _mailbox(office: Organization, address: str) -> Mailbox:
        return Mailbox.objects.create(
            organization=office,
            provider=Mailbox.Provider.IMAP,
            address=address,
            status=Mailbox.Status.ACTIVE,
            active=True,
        )

    def _receive(
        self, message_id: str, payload: bytes = b"<a/>", *, mailbox: Mailbox | None = None
    ) -> TriageItem:
        return receive_email_attachment(
            mailbox=mailbox or self.mailbox,
            message_id=message_id,
            part_id="1",
            filename=f"{message_id}.xml",
            payload=payload,
            received_at=timezone.now(),
        ).item

    def _released(self, message_id: str, payload: bytes | None = None) -> TriageItem:
        # Distinct bytes per item so content dedupe never interferes with these flows.
        item = self._receive(message_id, payload or f"<a>{message_id}</a>".encode())
        scan_quarantined_item(item=item, scanner=CleanScanner())
        return TriageItem.objects.get(pk=item.pk)

    @staticmethod
    def _rest(item: TriageItem) -> None:
        TriageItem.objects.filter(pk=item.pk).update(
            updated_at=timezone.now() - timedelta(minutes=30)
        )

    # 1. Retry with an attempt cap, and the manual Reprocessar.

    def test_failed_extraction_is_retried_until_the_cap(self) -> None:
        item = self._released("m-fail")
        with patch(
            "apps.triage.extraction.suggest", side_effect=ValidationError("Leitura falhou")
        ):
            self.assertEqual(process_triage_item(str(item.pk)), TriageStatus.FAILED)
            for _ in range(MAX_PIPELINE_ATTEMPTS + 2):
                self._rest(item)
                recover_triage_pipeline()
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.FAILED)
        self.assertEqual(item.pipeline_attempts, MAX_PIPELINE_ATTEMPTS)
        self.assertEqual(
            item.events.filter(note="Nova tentativa automática").count(),
            MAX_PIPELINE_ATTEMPTS - 1,
        )
        self._rest(item)
        self.assertEqual(recover_triage_pipeline(), 0)

    def test_recent_failure_waits_before_automatic_retry(self) -> None:
        item = self._released("m-fresh")
        TriageItem.objects.filter(pk=item.pk).update(status=TriageStatus.FAILED)
        self.assertEqual(recover_triage_pipeline(), 0)

    def test_reprocess_resets_budget_audits_and_runs_extraction(self) -> None:
        item = self._released("m-reprocess")
        TriageItem.objects.filter(pk=item.pk).update(
            status=TriageStatus.FAILED, pipeline_attempts=3
        )
        with self.captureOnCommitCallbacks(execute=True):
            reprocess_item(item=TriageItem.objects.get(pk=item.pk), actor=self.user)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.pipeline_attempts, 1)
        event = item.events.get(note="Reprocessamento solicitado")
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.from_status, TriageStatus.FAILED)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="triage.item.reprocessed", target_id=str(item.pk)
            ).exists()
        )

    def test_reprocess_refuses_other_states_and_demo_office(self) -> None:
        item = extract_item(item_id=self._released("m-review").pk)
        with self.assertRaises(InvalidTransition):
            reprocess_item(item=item, actor=self.user)
        TriageItem.objects.filter(pk=item.pk).update(status=TriageStatus.FAILED)
        Organization.objects.filter(pk=self.office.pk).update(is_demo=True)
        with self.assertRaises(ValidationError):
            reprocess_item(item=TriageItem.objects.get(pk=item.pk), actor=self.user)
        self.assertEqual(TriageItem.objects.get(pk=item.pk).status, TriageStatus.FAILED)

    def test_scan_error_in_quarantine_can_be_reprocessed(self) -> None:
        item = self._receive("m-scan-error", b"<scan/>")
        scan_quarantined_item(item=item, scanner=BrokenScanner())
        item = TriageItem.objects.select_related("safety_scan").get(pk=item.pk)
        self.assertEqual(item.status, TriageStatus.QUARANTINED)
        with (
            patch("apps.triage.security.ClamdScanner.from_settings", return_value=CleanScanner()),
            self.captureOnCommitCallbacks(execute=True),
        ):
            reprocess_item(item=item, actor=self.user)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)

    # 2. Content dedupe.

    def test_same_bytes_in_another_email_are_closed_as_duplicate(self) -> None:
        original = self._receive("m-first", b"<extrato>1</extrato>")
        with self.captureOnCommitCallbacks() as callbacks:
            receipt = receive_email_attachment(
                mailbox=self.mailbox,
                message_id="m-second",
                part_id="1",
                filename="copia.xml",
                payload=b"<extrato>1</extrato>",
                received_at=timezone.now(),
            )
        copy = receipt.item
        self.assertEqual(receipt.duplicate_kind, "content")
        self.assertEqual(callbacks, [])
        self.assertEqual(copy.duplicate_of, original)
        self.assertEqual(copy.status, TriageStatus.REJECTED)
        self.assertEqual(copy.rejection_reason, f"Duplicado de {original.original_name}")
        self.assertFalse(TriageItem.objects.filter(pk=copy.pk, safety_scan__isnull=False))
        self.assertEqual(self._receive("m-third", b"<extrato>1</extrato>").duplicate_of, original)

    def test_dedupe_ignores_rejected_originals_and_other_offices(self) -> None:
        rejected = self._receive("m-old", b"<x>1</x>")
        TriageItem.objects.filter(pk=rejected.pk).update(status=TriageStatus.REJECTED)
        self.assertIsNone(self._receive("m-new", b"<x>1</x>").duplicate_of)

        other = Organization.objects.create(name="Other", slug="triage-retry-other")
        foreign = self._receive(
            "m-foreign", b"<y>1</y>", mailbox=self._mailbox(other, "docs@other.test")
        )
        self.assertIsNone(self._receive("m-local", b"<y>1</y>").duplicate_of)
        self.assertIsNone(foreign.duplicate_of)

    # 3. Reason when overruling a classification.

    def _reviewed(self) -> TriageItem:
        item = extract_item(item_id=self._released("m-reason").pk)
        return update_review_fields(
            item=item,
            actor=self.user,
            company=self.company,
            document_type=self.extrato,
            period_label="2026-09",
            counterparty_token="",
            final_name="417_EXTRATO_202609.xml",
        )

    def test_changing_set_company_or_type_requires_reason(self) -> None:
        item = self._reviewed()
        kwargs = {
            "item": item,
            "actor": self.user,
            "company": self.other_company,
            "document_type": self.extrato,
            "period_label": "2026-09",
            "counterparty_token": "",
            "final_name": "533_EXTRATO_202609.xml",
        }
        with self.assertRaises(ValidationError):
            update_review_fields(**kwargs)
        with self.assertRaises(ValidationError):
            update_review_fields(**kwargs, reason="x" * 501)
        item.refresh_from_db()
        self.assertEqual(item.company, self.company)

        update_review_fields(**kwargs, reason="CNPJ do tomador é da filial")
        event = item.events.exclude(reason="").get()
        self.assertTrue(event.note.startswith("Corrigido: empresa"))
        self.assertEqual(event.reason, "CNPJ do tomador é da filial")
        # The pending review task follows the corrected company, with the move on record.
        activity = OperationalActivity.objects.get(source_triage_item=item)
        self.assertEqual(activity.company, self.other_company)
        self.assertTrue(
            activity.events.filter(
                event_type="triage_company_corrected", summary__contains="filial"
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="triage.item.review_fields_updated",
                metadata__reason="CNPJ do tomador é da filial",
            ).exists()
        )

    def test_renaming_only_needs_no_reason(self) -> None:
        item = self._reviewed()
        update_review_fields(
            item=item,
            actor=self.user,
            company=self.company,
            document_type=self.extrato,
            period_label="2026-08",
            counterparty_token="",
            final_name="417_EXTRATO_202608.xml",
        )
        item.refresh_from_db()
        self.assertEqual(item.period_label, "2026-08")

    # Screens.

    def _login(self) -> None:
        from apps.hub.models import ProductModule

        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.TRIAGE, enabled=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def test_failed_item_page_offers_reprocess_and_post_runs_it(self) -> None:
        self._login()
        item = self._released("m-screen-fail")
        TriageItem.objects.filter(pk=item.pk).update(
            status=TriageStatus.FAILED, pipeline_attempts=3
        )
        url = reverse("hub:triage-item", args=[item.id])
        page = self.client.get(url)
        self.assertContains(page, 'value="reprocess"')
        self.assertContains(page, "Reprocessar")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {"decision": "reprocess"})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)

    def test_reprocess_post_on_reviewable_item_changes_nothing(self) -> None:
        self._login()
        item = extract_item(item_id=self._released("m-screen-review").pk)
        url = reverse("hub:triage-item", args=[item.id])
        self.assertNotContains(self.client.get(url), 'value="reprocess"')
        self.client.post(url, {"decision": "reprocess"})
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertFalse(item.events.filter(note="Reprocessamento solicitado").exists())

    def test_queue_and_item_show_duplicate_chip_and_history_shows_reason(self) -> None:
        self._login()
        original = self._receive("m-chip-a", b"<chip/>")
        copy = self._receive("m-chip-b", b"<chip/>")
        TriageItem.objects.filter(pk__in=[original.pk, copy.pk]).update(company=self.company)
        original_url = reverse("hub:triage-item", args=[original.id])

        queue = self.client.get(reverse("hub:triage"))
        self.assertContains(queue, "triage-duplicate-chip")
        self.assertContains(queue, f'href="{original_url}"')
        detail = self.client.get(reverse("hub:triage-item", args=[copy.id]))
        self.assertContains(detail, f"Duplicado de {original.original_name}")

        item = self._reviewed()
        page_url = reverse("hub:triage-item", args=[item.id])
        self.assertContains(self.client.get(page_url), 'name="reason"')
        self.client.post(
            page_url,
            {
                "decision": "update_fields",
                "company": self.other_company.id,
                "document_type": self.extrato.id,
                "period_label": "2026-09",
                "counterparty_token": "",
                "final_name": "533_EXTRATO_202609.xml",
                "reason": "Filial correta",
            },
        )
        item.refresh_from_db()
        self.assertEqual(item.company, self.other_company)
        self.assertContains(self.client.get(page_url), "Motivo: Filial correta")
