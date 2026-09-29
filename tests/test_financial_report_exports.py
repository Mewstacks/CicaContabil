from __future__ import annotations

from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import (
    AccountingBalanceSnapshot,
    ClientCompany,
    DreMappingSet,
    FinancialReportExport,
)
from apps.hub.reporting_exports import prepare_export, process_export
from apps.organizations.models import Membership, Organization


class FinancialReportExportTests(TestCase):
    def setUp(self) -> None:
        self.files = TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.files.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.organization = Organization.objects.create(name="Escritorio", slug="report-export")
        self.user = User.objects.create_user(email="report@example.com", password="senha-segura")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.ADMIN
        )
        self.company = ClientCompany.objects.create(organization=self.organization, name="Empresa")
        self.source = AccountingBalanceSnapshot.objects.create(
            organization=self.organization,
            company=self.company,
            competence=date(2026, 9, 1),
            source_kind=AccountingBalanceSnapshot.SourceKind.IMPORT,
            source_reference="balancete",
        )
        DreMappingSet.objects.create(
            organization=self.organization,
            version=1,
            label="Mapa",
            is_active=True,
            created_by=self.user,
        )

    def create_export(self) -> FinancialReportExport:
        return prepare_export(
            organization=self.organization,
            company_id=self.company.id,
            resource=FinancialReportExport.Resource.DRE,
            resource_id=self.source.id,
            export_format=FinancialReportExport.Format.PDF,
            actor=self.user,
        )

    @override_settings(
        CICA_REPORTING_URL="http://127.0.0.1:3080", CICA_REPORTING_SHARED_SECRET="secret"
    )
    @patch("apps.hub.reporting_exports.render_snapshot", return_value=b"%PDF-1.7 report")
    def test_worker_renders_private_artifact_from_verified_snapshot(self, renderer: object) -> None:
        export = self.create_export()

        self.assertEqual(process_export(str(export.id)), "ready")

        export.refresh_from_db()
        self.assertEqual(export.state, FinancialReportExport.State.READY)
        self.assertTrue(export.content.name.startswith("private/financial-reports/"))
        self.assertEqual(export.content_type, "application/pdf")
        self.assertEqual(export.output_sha256.__len__(), 64)
        assert hasattr(renderer, "assert_called_once")
        renderer.assert_called_once()  # type: ignore[attr-defined]

    @patch("apps.hub.reporting_exports.render_snapshot")
    def test_worker_does_not_render_when_requester_loses_company_access(
        self, renderer: object
    ) -> None:
        export = self.create_export()
        Membership.objects.filter(organization=self.organization, user=self.user).update(
            is_active=False
        )

        self.assertEqual(process_export(str(export.id)), "access_revoked")

        export.refresh_from_db()
        self.assertEqual(export.state, FinancialReportExport.State.FAILED)
        self.assertEqual(export.failure_code, "access_revoked")
        assert hasattr(renderer, "assert_not_called")
        renderer.assert_not_called()  # type: ignore[attr-defined]

    def test_download_revalidates_current_company_access_and_private_file(self) -> None:
        export = self.create_export()
        export.content.save("report.pdf", ContentFile(b"%PDF"), save=False)
        export.state = FinancialReportExport.State.READY
        export.content_type = "application/pdf"
        export.save()
        self.client.force_login(self.user)
        url = reverse("hub:financial-report-export-download", args=[export.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"%PDF")
        self.assertTrue(response.closed)
        Membership.objects.filter(organization=self.organization, user=self.user).update(
            is_active=False
        )
        self.assertEqual(self.client.get(url).status_code, 403)
