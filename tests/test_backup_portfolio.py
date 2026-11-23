"""D-319: the office whose registry is a backup says who it still serves."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.backup_bridge import complete_backup
from apps.hub.models import (
    Certificate,
    ClientCompany,
    DataSource,
    ImportBatch,
    NfseSync,
    OfficeProfile,
    ProductModule,
)
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.organizations.models import Membership, Organization


class BackupPortfolioPageTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("dono@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Backup", slug="backup")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        OfficeProfile.objects.create(organization=self.organization, legal_name="Backup Ltda")
        self.source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
            label="Backup Dominio Web",
            status=DataSource.Status.READY,
            capabilities=["companies"],
        )
        self.served = ClientCompany.objects.create(
            organization=self.organization,
            name="Padaria Vila Nova",
            cnpj_masked="12.345.678/0001-90",
            dominio_code="0101",
            data_source=self.source,
            external_key="0101",
        )
        self.gone = ClientCompany.objects.create(
            organization=self.organization,
            name="Transportes Guaiba",
            dominio_code="0102",
            data_source=self.source,
            external_key="0102",
            active=False,
        )
        self._login(self.user)

    def _login(self, user: User) -> None:
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_page_lists_the_backup_portfolio_with_its_dominio_codes(self) -> None:
        response = self.client.get(reverse("hub:backup-portfolio"))
        self.assertEqual(response.status_code, 200)
        listed = {company.name: company.dominio_code for company in response.context["companies"]}
        self.assertEqual(listed, {"Padaria Vila Nova": "0101", "Transportes Guaiba": "0102"})
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["portfolio_total"], 2)

    def test_situation_filter_separates_active_from_inactive(self) -> None:
        response = self.client.get(reverse("hub:backup-portfolio"), {"situacao": "inativa"})
        names = {company.name for company in response.context["companies"]}
        self.assertEqual(names, {"Transportes Guaiba"})

    def test_owner_deactivates_a_company_and_the_change_is_audited(self) -> None:
        response = self.client.post(
            reverse("hub:backup-portfolio"),
            {"action": "deactivate", "company_id": str(self.served.id)},
        )
        self.assertEqual(response.status_code, 302)
        self.served.refresh_from_db()
        self.assertFalse(self.served.active)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization, action="hub.company.activation_changed"
            ).exists()
        )

    def test_owner_reactivates_a_company(self) -> None:
        self.client.post(
            reverse("hub:backup-portfolio"),
            {"action": "activate", "company_id": str(self.gone.id)},
        )
        self.gone.refresh_from_db()
        self.assertTrue(self.gone.active)

    def test_filters_survive_the_redirect_after_a_change(self) -> None:
        response = self.client.post(
            reverse("hub:backup-portfolio"),
            {
                "action": "deactivate",
                "company_id": str(self.served.id),
                "q": "Padaria",
                "situacao": "ativa",
            },
        )
        self.assertIn("q=Padaria", response["Location"])
        self.assertIn("situacao=ativa", response["Location"])

    def test_a_member_cannot_change_the_portfolio(self) -> None:
        member = User.objects.create_user("membro@example.test", "safe-password-123")
        Membership.objects.create(
            organization=self.organization, user=member, role=Membership.Role.MEMBER
        )
        self._login(member)
        response = self.client.post(
            reverse("hub:backup-portfolio"),
            {"action": "deactivate", "company_id": str(self.served.id)},
        )
        self.assertEqual(response.status_code, 403)
        self.served.refresh_from_db()
        self.assertTrue(self.served.active)

    def test_an_invalid_action_is_refused_without_touching_the_company(self) -> None:
        response = self.client.post(
            reverse("hub:backup-portfolio"),
            {"action": "excluir", "company_id": str(self.served.id)},
        )
        self.assertEqual(response.status_code, 400)
        self.served.refresh_from_db()
        self.assertTrue(self.served.active)

    def test_the_action_travels_in_a_hidden_field_not_on_the_submit_button(self) -> None:
        """hub.js disables the button on submit, and a disabled button sends no value."""

        html = self.client.get(reverse("hub:backup-portfolio")).content.decode()
        self.assertIn('<input type="hidden" name="action" value="deactivate">', html)
        self.assertNotIn('name="action" value="deactivate"></button>', html)
        self.assertNotIn('type="submit" name="action"', html)

    def test_the_page_disappears_when_a_dominio_connector_owns_the_registry(self) -> None:
        IntelligenceConnector.objects.create(organization=self.organization, status="healthy")
        self.assertEqual(self.client.get(reverse("hub:backup-portfolio")).status_code, 404)

    def _settings_menu_has_the_page(self) -> bool:
        """The entry lives in the Configurações menu, rendered on every workspace page."""

        response = self.client.get(reverse("hub:settings"))
        return reverse("hub:backup-portfolio") in response.content.decode()

    def test_the_settings_menu_lists_the_page_for_a_backup_office(self) -> None:
        self.assertTrue(self._settings_menu_has_the_page())

    def test_the_settings_menu_drops_the_page_without_a_backup_source(self) -> None:
        self.source.delete()
        self.assertFalse(self._settings_menu_has_the_page())

    def test_the_settings_menu_drops_the_page_when_dominio_syncs(self) -> None:
        IntelligenceConnector.objects.create(organization=self.organization, status="healthy")
        self.assertFalse(self._settings_menu_has_the_page())


class BackupSnapshotCutTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Corte", slug="corte")
        self.source = DataSource.objects.create(
            organization=self.organization,
            kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
            label="Backup Dominio Web",
            status=DataSource.Status.PROCESSING,
            capabilities=["companies"],
        )
        self.agent = EdgeAgent.objects.create(
            organization=self.organization,
            label="Servidor",
            fingerprint="fingerprint",
            shared_secret="secret-for-tests",
        )
        self.snapshot = timezone.now()
        self.seen = ClientCompany.objects.create(
            organization=self.organization,
            name="Continua cliente",
            dominio_code="0101",
            data_source=self.source,
            external_key="0101",
            source_updated_at=self.snapshot,
        )
        self.absent = ClientCompany.objects.create(
            organization=self.organization,
            name="Saiu da carteira",
            dominio_code="0102",
            data_source=self.source,
            external_key="0102",
            source_updated_at=self.snapshot - timedelta(days=30),
        )

    def _batch(self, *, errors: list[dict[str, str]] | None = None) -> ImportBatch:
        return ImportBatch.objects.create(
            organization=self.organization,
            data_source=self.source,
            kind=ImportBatch.Kind.DOMINIO_BACKUP,
            status=ImportBatch.Status.PROCESSING,
            original_filename="escritorio.dom",
            content_hash="hash",
            source_snapshot_at=self.snapshot,
            mapping={"received_capabilities": ["companies"]},
            errors=errors or [],
        )

    def test_a_clean_backup_deactivates_whoever_it_omits(self) -> None:
        complete_backup(batch=self._batch(), agent=self.agent)
        self.seen.refresh_from_db()
        self.absent.refresh_from_db()
        self.assertTrue(self.seen.active)
        self.assertFalse(self.absent.active)

    def test_the_absent_company_is_kept_not_deleted(self) -> None:
        complete_backup(batch=self._batch(), agent=self.agent)
        self.assertTrue(ClientCompany.objects.filter(id=self.absent.id).exists())

    def test_a_backup_with_row_errors_does_not_cut_the_portfolio(self) -> None:
        complete_backup(
            batch=self._batch(errors=[{"code": "row_validation", "message": "linha 3"}]),
            agent=self.agent,
        )
        self.absent.refresh_from_db()
        self.assertTrue(self.absent.active)

    def test_a_batch_without_the_companies_capability_does_not_cut(self) -> None:
        batch = self._batch()
        batch.mapping = {"received_capabilities": ["accumulator_catalog"]}
        batch.save(update_fields=["mapping"])
        self.source.capabilities = ["accumulator_catalog"]
        self.source.save(update_fields=["capabilities"])
        complete_backup(batch=batch, agent=self.agent)
        self.absent.refresh_from_db()
        self.assertTrue(self.absent.active)


class DeactivatedCompanyInTheCollectionTests(TestCase):
    """Deactivating removes the company from the operating scope the collection reads."""

    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("coleta@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Coleta", slug="coleta")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        OfficeProfile.objects.create(organization=self.organization, legal_name="Coleta Ltda")
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.NFSE, enabled=True
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Saiu da carteira", dominio_code="0101"
        )
        self.certificate = Certificate.objects.create(
            organization=self.organization,
            company=self.company,
            label="A1",
            pfx_blob="dummy",
            password="dummy",
            fingerprint_sha256="b" * 64,
            valid_until=timezone.now() + timedelta(days=30),
        )
        NfseSync.objects.create(
            organization=self.organization,
            company=self.company,
            certificate=self.certificate,
            enabled=True,
            status=NfseSync.Status.RUNNING,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def _rows(self) -> list[dict[str, object]]:
        response = self.client.get(reverse("hub:nfse-center"), {"view": "collection"})
        self.assertEqual(response.status_code, 200)
        return list(response.context["nfse_sync_rows"])

    def test_an_active_company_is_listed_with_its_collection_status(self) -> None:
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], NfseSync.Status.RUNNING)
        self.assertTrue(rows[0]["enabled"])

    def test_a_deactivated_company_leaves_the_collection_list(self) -> None:
        """The operating scope is already active-only, so no stale row is shown."""

        self.company.active = False
        self.company.save(update_fields=["active"])
        self.assertEqual(self._rows(), [])
