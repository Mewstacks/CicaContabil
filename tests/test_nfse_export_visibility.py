from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, IntegrationArtifact, NfseExport
from apps.hub.services import create_document_and_artifact, create_nfse_export
from apps.hub.views import _visible_nfse_exports
from apps.organizations.models import Membership, Organization


class NfseExportVisibilityTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self):
        self.office = Organization.objects.create(name="History", slug="history-scope")
        self.user = User.objects.create_user("history@example.test", "safe-password-123")
        self.member = Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OPERATOR
        )
        self.companies = [
            ClientCompany.objects.create(organization=self.office, name=f"Company {index}")
            for index in range(2)
        ]
        self.grant = CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=self.member,
            company=self.companies[0],
            modules=["nfse"],
            is_active=True,
        )
        self.documents = []
        for index, company in enumerate(self.companies):
            document, _, _ = create_document_and_artifact(
                company=company,
                original_xml=(
                    f"<NFSe id='{index}'><infNFSe>"
                    "<valores><vLiq>1</vLiq></valores></infNFSe></NFSe>"
                ),
                normalized_data={},
            )
            IntegrationArtifact.objects.create(
                organization=self.office,
                document=document,
                accumulator_code="A1",
                applied_rule="Synthetic test",
                confidence=100,
            )
            self.documents.append(document)
        self.allowed = create_nfse_export(
            organization=self.office, documents=self.documents[:1], actor=self.user
        )
        self.denied = create_nfse_export(
            organization=self.office, documents=self.documents[1:], actor=self.user
        )
        self.mixed = create_nfse_export(
            organization=self.office, documents=self.documents, actor=self.user
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.pk)
        session.save()
        self.url = reverse("hub:nfse-center") + "?view=exports"

    def test_history_and_download_only_expose_fully_authorized_packages(self):
        page = self.client.get(self.url)
        self.assertEqual(list(page.context["nfse_exports"]), [self.allowed])
        for export in (self.denied, self.mixed):
            self.assertNotContains(page, export.content_hash[:12])
            self.assertEqual(
                self.client.post(reverse("hub:nfse-export-download", args=[export.pk])).status_code,
                404,
            )
        response = self.client.post(reverse("hub:nfse-export-download", args=[self.allowed.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"PK"))
        self.grant.is_active = False
        self.grant.save(update_fields=["is_active"])
        revoked = self.client.get(self.url)
        self.assertEqual(revoked.context["nfse_exports"].paginator.count, 0)
        self.assertEqual(
            self.client.post(
                reverse("hub:nfse-export-download", args=[self.allowed.pk])
            ).status_code,
            404,
        )

    def test_scope_filter_runs_in_sql_before_pagination(self):
        context = {
            "office": self.office,
            "membership": self.member,
            "companies": ClientCompany.objects.filter(pk=self.companies[0].pk),
        }
        with self.assertNumQueries(1):
            self.assertEqual(
                list(_visible_nfse_exports(context).order_by("-created_at")[:1]), [self.allowed]
            )
        self.allowed.documents.clear()
        self.assertFalse(_visible_nfse_exports(context).exists())

    def test_legacy_backfill_rejects_malformed_missing_and_cross_tenant_references(self):
        migration = import_module("apps.hub.migrations.0067_nfseexport_documents")
        self.allowed.documents.clear()
        other = Organization.objects.create(name="Foreign", slug="foreign-history")
        foreign = ClientCompany.objects.create(organization=other, name="Foreign")
        foreign_doc, _, _ = create_document_and_artifact(
            company=foreign, original_xml="<nfse id='foreign' />", normalized_data={}
        )
        snapshots = [
            [],
            {"documents": None},
            {"documents": [{}]},
            {"documents": [{"document_id": "invalid"}]},
            {"documents": [{"document_id": str(foreign_doc.pk)}]},
            {"documents": [{"document_id": "00000000-0000-0000-0000-000000000001"}]},
        ]
        broken = [
            NfseExport.objects.create(
                organization=self.office,
                document_count=1,
                content_hash=f"{index:064x}",
                snapshot=snapshot,
            )
            for index, snapshot in enumerate(snapshots)
        ]
        migration.link_existing_documents(apps, SimpleNamespace(connection=connection))
        self.assertEqual(list(self.allowed.documents.all()), self.documents[:1])
        for export in broken:
            self.assertFalse(export.documents.exists())
        migration.link_existing_documents(apps, SimpleNamespace(connection=connection))
        self.assertEqual(self.allowed.documents.count(), 1)

    def test_export_creation_rejects_empty_duplicate_and_foreign_selections(self):
        foreign = Organization.objects.create(name="Other", slug="foreign-create")
        for office, documents in (
            (self.office, []),
            (self.office, self.documents[:1] * 2),
            (foreign, self.documents),
        ):
            with (
                self.subTest(office=office.pk, documents=len(documents)),
                self.assertRaises(ValueError),
            ):
                create_nfse_export(organization=office, documents=documents, actor=self.user)
