"""AC-11.2 (upload) e AC-11.9: envio manual pelo mesmo pipeline, escopo escritório + empresa."""

from __future__ import annotations

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership
from apps.triage.models import DocumentType, TriageItem, TriagePolicy
from apps.triage.services import archive_internal, decide_item, update_review_fields
from apps.triage.transitions import TriageStatus
from triage_v2_support import PDF, CleanScanner, TriageV2Case


class UploadCase(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.url = reverse("hub:triage-upload")

    def pdf(self, name: str = "extrato.pdf", extra: bytes = b"") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, PDF + extra, content_type="application/pdf")

    def post(self, *files: SimpleUploadedFile, **data: object) -> object:
        with (
            patch("apps.triage.security.ClamdScanner.from_settings", return_value=CleanScanner()),
            self.captureOnCommitCallbacks(execute=True),
        ):
            return self.client.post(self.url, {"documents": list(files), **data})

    def operator(self) -> User:
        user = User.objects.create_user("op-up@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office, membership=membership, company=self.company,
            modules=[ProductModule.Code.TRIAGE], capabilities=["read", "write"],
        )
        return user


class UploadFlowTests(UploadCase):
    def test_form_renders_with_the_accepted_formats(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ".pdf")
        self.assertNotContains(response, ".zip")

    def test_upload_reaches_review_through_scan_and_extraction(self) -> None:
        response = self.post(self.pdf(), company=str(self.company.pk))
        self.assertRedirects(response, reverse("hub:triage"))
        item = TriageItem.objects.get()
        self.assertEqual(item.origin, TriageItem.Origin.UPLOAD)
        self.assertEqual(item.company, self.company)
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertIsNone(item.mailbox)
        self.assertTrue(
            AuditEvent.objects.filter(action="triage.item.received_upload").exists()
        )

    def test_upload_can_be_approved_and_archived(self) -> None:
        document_type = DocumentType.objects.create(
            organization=self.office, code="extrato", label="Extrato",
            name_template="{codigo}_EXTRATO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        self.post(self.pdf(), company=str(self.company.pk))
        item = TriageItem.objects.get()
        item = update_review_fields(
            item=item, actor=self.owner, company=self.company, document_type=document_type,
            period_label="2026-09", counterparty_token="", final_name="417_EXTRATO_202609.pdf",
        )
        decide_item(item=item, actor=self.owner, decision="archive", reason="")
        archived = archive_internal(item=item, actor=self.owner)
        self.assertEqual(archived.status, TriageStatus.ARCHIVED)

    def test_without_a_company_an_admin_leaves_it_to_extraction(self) -> None:
        self.post(self.pdf())
        self.assertIsNone(TriageItem.objects.get().company)

    def test_several_files_in_one_post(self) -> None:
        self.post(self.pdf("a.pdf", b"a"), self.pdf("b.pdf", b"b"))
        self.assertEqual(TriageItem.objects.count(), 2)

    def test_same_bytes_close_as_duplicate(self) -> None:
        self.post(self.pdf("a.pdf"))
        self.post(self.pdf("b.pdf"))
        second = TriageItem.objects.get(original_name="b.pdf")
        self.assertEqual(second.status, TriageStatus.REJECTED)
        self.assertIsNotNone(second.duplicate_of)

    def test_unsupported_format_empty_and_oversized_are_refused(self) -> None:
        bad = SimpleUploadedFile("setup.exe", b"MZ")
        self.post(bad)
        self.post(SimpleUploadedFile("vazio.pdf", b""))
        with patch("apps.triage.intake_policy.MAX_ATTACHMENT_BYTES", 10):
            self.post(self.pdf("grande.pdf"))
        self.assertEqual(TriageItem.objects.count(), 0)

    def test_zip_follows_the_office_switch(self) -> None:
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as package:
            package.writestr("a.pdf", PDF)
        archive = SimpleUploadedFile("p.zip", buffer.getvalue())
        self.post(archive)
        self.assertEqual(TriageItem.objects.count(), 0)
        TriagePolicy.objects.create(organization=self.office, open_archives=True)
        self.post(SimpleUploadedFile("p.zip", buffer.getvalue()))
        member = TriageItem.objects.get(origin=TriageItem.Origin.ARCHIVE)
        self.assertEqual(member.original_name, "a.pdf")
        self.assertEqual(member.status, TriageStatus.AWAITING_REVIEW)

    def test_get_only_and_post_only_methods(self) -> None:
        self.assertEqual(self.client.put(self.url).status_code, 405)


class UploadScopeTests(UploadCase):
    def test_company_of_another_office_is_refused(self) -> None:
        other = self.make_office("e11-up-other")
        stranger = ClientCompany.objects.create(organization=other, name="X", dominio_code="1")
        response = self.post(self.pdf(), company=str(stranger.pk))
        self.assertEqual(response.status_code, 400)  # type: ignore[attr-defined]
        self.assertEqual(TriageItem.objects.count(), 0)

    def test_type_of_another_office_is_refused(self) -> None:
        other = self.make_office("e11-up-other2")
        foreign = DocumentType.objects.create(
            organization=other, code="x", label="X", name_template="{codigo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        response = self.post(self.pdf(), document_type=str(foreign.pk))
        self.assertEqual(response.status_code, 400)  # type: ignore[attr-defined]
        self.assertEqual(TriageItem.objects.count(), 0)

    def test_operator_must_choose_a_company_inside_the_grant(self) -> None:
        self.login(self.operator())
        self.assertEqual(self.post(self.pdf()).status_code, 400)  # type: ignore[attr-defined]
        outside = ClientCompany.objects.create(
            organization=self.office, name="Fora", dominio_code="77"
        )
        self.assertEqual(
            self.post(self.pdf(), company=str(outside.pk)).status_code,  # type: ignore[attr-defined]
            400,
        )
        self.assertEqual(TriageItem.objects.count(), 0)
        self.post(self.pdf(), company=str(self.company.pk))
        self.assertEqual(TriageItem.objects.get().company, self.company)

    def test_module_disabled_blocks(self) -> None:
        ProductModule.objects.filter(organization=self.office).update(enabled=False)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_demo_office_refuses_uploads(self) -> None:
        self.office.is_demo = True
        self.office.save()
        self.assertEqual(self.post(self.pdf()).status_code, 403)  # type: ignore[attr-defined]
        self.assertEqual(TriageItem.objects.count(), 0)

    def test_login_required(self) -> None:
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
