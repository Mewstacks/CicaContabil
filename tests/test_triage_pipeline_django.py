from __future__ import annotations

from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany
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
from apps.triage.security import ScanVerdict, scan_quarantined_item
from apps.triage.services import archive_internal, decide_item, update_review_fields
from apps.triage.tasks import process_triage_item, recover_triage_pipeline
from apps.triage.transitions import TriageStatus


class CleanScanner:
    def scan(self, stream: object) -> ScanVerdict:
        return ScanVerdict("clean", "test")


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
