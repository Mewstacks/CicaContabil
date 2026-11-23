"""AC-11.1 e AC-11.9: tela do catálogo, escopo escritório + empresa, isolamento."""

from __future__ import annotations

from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership
from apps.triage.models import ChecklistExpectation, DocumentType
from triage_v2_support import TriageV2Case


class CatalogViewCase(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.list_url = reverse("hub:triage-catalog")
        self.save_url = reverse("hub:triage-catalog-save")

    def operator(self, company: ClientCompany | None = None) -> User:
        user = User.objects.create_user("op-e11@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=membership,
            company=company or self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read", "write"],
        )
        return user

    def make_type(self, office=None, code="extrato", label="Extrato", **extra) -> DocumentType:  # type: ignore[no-untyped-def]
        return DocumentType.objects.create(
            organization=office or self.office,
            code=code,
            label=label,
            name_template="{codigo}_X_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
            **extra,
        )

    def payload(self, **over: object) -> dict[str, object]:
        data: dict[str, object] = {
            "label": "Guia de imposto",
            "code": "guia",
            "keywords": "das, darf\ngps",
            "name_template": "{codigo}_GUIA_{periodo}",
            "period_kind": DocumentType.PeriodKind.COMPETENCIA,
            "counterparty_kind": DocumentType.CounterpartyKind.NONE,
            "folder_template": "",
            "expected_default": "",
            "expected_regimes": ["simples", "mei"],
        }
        data.update(over)
        return data


class CatalogListTests(CatalogViewCase):
    def test_list_shows_only_this_offices_types(self) -> None:
        self.make_type(label="Extrato do escritório")
        other = self.make_office("e11-cat-other")
        self.make_type(other, label="Tipo secreto de outro")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extrato do escritório")
        self.assertNotContains(response, "Tipo secreto de outro")

    def test_empty_catalogue_offers_the_starter_set_to_an_admin(self) -> None:
        response = self.client.get(self.list_url)
        self.assertContains(response, "Carregar modelo contábil")
        self.assertContains(response, reverse("hub:triage-catalog-seed"))

    def test_nothing_is_seeded_by_just_opening_the_page(self) -> None:
        self.client.get(self.list_url)
        self.assertEqual(DocumentType.objects.filter(organization=self.office).count(), 0)

    def test_requires_login(self) -> None:
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)

    def test_module_disabled_blocks_the_page(self) -> None:
        ProductModule.objects.filter(organization=self.office).update(enabled=False)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_operator_reads_but_has_no_edit_controls(self) -> None:
        self.make_type(label="Extrato lido")
        self.login(self.operator())
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extrato lido")
        self.assertNotContains(response, "Novo tipo")
        self.assertNotContains(response, "Carregar modelo contábil")

    def test_editor_opens_for_new_and_for_an_existing_type(self) -> None:
        document_type = self.make_type(label="Editável")
        self.assertContains(self.client.get(self.list_url, {"novo": "1"}), 'name="keywords"')
        edit = self.client.get(self.list_url, {"editar": str(document_type.pk)})
        self.assertContains(edit, 'value="Editável"')

    def test_editing_a_type_of_another_office_is_a_404(self) -> None:
        other = self.make_office("e11-cat-other2")
        foreign = self.make_type(other, label="Alheio")
        self.assertEqual(
            self.client.get(self.list_url, {"editar": str(foreign.pk)}).status_code, 404
        )

    def test_inactive_types_are_listed_with_a_state(self) -> None:
        self.make_type(label="Desligado", active=False)
        self.assertContains(self.client.get(self.list_url), "Inativo")


class CatalogWriteTests(CatalogViewCase):
    def test_create_parses_keywords_and_regimes(self) -> None:
        response = self.client.post(self.save_url, self.payload())
        self.assertRedirects(response, self.list_url)
        created = DocumentType.objects.get(organization=self.office, code="guia")
        self.assertEqual(created.keywords, ["das", "darf", "gps"])
        self.assertEqual(sorted(created.expected_regimes), ["mei", "simples"])
        self.assertFalse(created.expected_default)
        self.assertTrue(AuditEvent.objects.filter(action="triage.catalog.type_created").exists())

    def test_code_defaults_to_the_slug_of_the_label(self) -> None:
        self.client.post(self.save_url, self.payload(code="", label="Nota de Débito"))
        self.assertTrue(
            DocumentType.objects.filter(organization=self.office, code="nota-de-debito").exists()
        )

    def test_duplicate_code_in_the_same_office_is_refused(self) -> None:
        self.make_type(code="guia")
        response = self.client.post(self.save_url, self.payload())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DocumentType.objects.filter(organization=self.office).count(), 1)

    def test_same_code_in_another_office_is_fine(self) -> None:
        other = self.make_office("e11-cat-other3")
        self.make_type(other, code="guia")
        self.assertRedirects(self.client.post(self.save_url, self.payload()), self.list_url)

    def test_invalid_regime_name_template_and_folder_are_refused(self) -> None:
        for bad in (
            {"expected_regimes": ["inexistente"]},
            {"name_template": "{inexistente}"},
            {"name_template": ""},
            {"folder_template": r"..\{company_name}"},
            {"label": ""},
        ):
            response = self.client.post(self.save_url, self.payload(**bad))
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(DocumentType.objects.count(), 0)

    def test_edit_updates_the_type_and_bumps_the_revision(self) -> None:
        document_type = self.make_type(code="guia", label="Antiga")
        response = self.client.post(
            self.save_url,
            self.payload(type_id=str(document_type.pk), label="Nova", code="outro-codigo"),
        )
        self.assertRedirects(response, self.list_url)
        document_type.refresh_from_db()
        self.assertEqual(document_type.label, "Nova")
        self.assertEqual(document_type.code, "guia")  # the code is the type's identity
        self.assertEqual(document_type.revision, 2)

    def test_editing_a_foreign_type_is_a_404_and_changes_nothing(self) -> None:
        other = self.make_office("e11-cat-other4")
        foreign = self.make_type(other, code="guia", label="Alheio")
        response = self.client.post(self.save_url, self.payload(type_id=str(foreign.pk)))
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.label, "Alheio")

    def test_operator_cannot_write(self) -> None:
        self.login(self.operator())
        self.assertEqual(self.client.post(self.save_url, self.payload()).status_code, 403)
        self.assertEqual(DocumentType.objects.count(), 0)

    def test_toggle_deactivates_and_reactivates(self) -> None:
        document_type = self.make_type()
        url = reverse("hub:triage-catalog-toggle", args=[document_type.pk])
        self.client.post(url)
        document_type.refresh_from_db()
        self.assertFalse(document_type.active)
        self.client.post(url)
        document_type.refresh_from_db()
        self.assertTrue(document_type.active)

    def test_toggle_of_a_foreign_type_is_a_404(self) -> None:
        other = self.make_office("e11-cat-other5")
        foreign = self.make_type(other)
        url = reverse("hub:triage-catalog-toggle", args=[foreign.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        foreign.refresh_from_db()
        self.assertTrue(foreign.active)

    def test_seed_loads_the_starter_set_once(self) -> None:
        url = reverse("hub:triage-catalog-seed")
        self.assertRedirects(self.client.post(url), self.list_url)
        first = DocumentType.objects.filter(organization=self.office).count()
        self.assertGreaterEqual(first, 7)
        self.client.post(url)
        self.assertEqual(DocumentType.objects.filter(organization=self.office).count(), first)

    def test_seed_by_an_operator_is_refused(self) -> None:
        self.login(self.operator())
        self.assertEqual(self.client.post(reverse("hub:triage-catalog-seed")).status_code, 403)
        self.assertEqual(DocumentType.objects.count(), 0)

    @override_settings(DEMO_SESSION_ISOLATION_READY=True)
    def test_demo_office_cannot_change_the_catalogue(self) -> None:
        self.office.is_demo = True
        self.office.save()
        self.assertEqual(self.client.post(self.save_url, self.payload()).status_code, 403)

    def test_get_on_write_endpoints_is_not_allowed(self) -> None:
        self.assertEqual(self.client.get(self.save_url).status_code, 405)
        self.assertEqual(self.client.get(reverse("hub:triage-catalog-seed")).status_code, 405)


class CatalogExceptionTests(CatalogViewCase):
    def setUp(self) -> None:
        super().setUp()
        self.document_type = self.make_type(expected_default=True)
        self.url = reverse("hub:triage-catalog-exception", args=[self.document_type.pk])

    def test_admin_sets_and_removes_a_company_exception(self) -> None:
        self.client.post(
            self.url,
            {"company": str(self.company.pk), "requirement": "waived", "action": "save"},
        )
        exception = ChecklistExpectation.objects.get(
            company=self.company, document_type=self.document_type
        )
        self.assertEqual(exception.requirement, "waived")
        self.client.post(self.url, {"company": str(self.company.pk), "action": "remove"})
        self.assertFalse(ChecklistExpectation.objects.exists())

    def test_setting_twice_updates_the_same_row(self) -> None:
        for requirement in ("waived", "expected"):
            self.client.post(
                self.url,
                {"company": str(self.company.pk), "requirement": requirement, "action": "save"},
            )
        self.assertEqual(ChecklistExpectation.objects.count(), 1)
        self.assertEqual(ChecklistExpectation.objects.get().requirement, "expected")

    def test_company_of_another_office_is_refused(self) -> None:
        other = self.make_office("e11-cat-other6")
        stranger = ClientCompany.objects.create(
            organization=other, name="Estranha", dominio_code="9"
        )
        response = self.client.post(
            self.url, {"company": str(stranger.pk), "requirement": "waived", "action": "save"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ChecklistExpectation.objects.exists())

    def test_exception_page_lists_only_own_exceptions(self) -> None:
        ChecklistExpectation.objects.create(
            organization=self.office, company=self.company,
            document_type=self.document_type, requirement="waived",
        )
        response = self.client.get(self.list_url, {"editar": str(self.document_type.pk)})
        self.assertContains(response, "Padaria Sol")

    def test_operator_cannot_set_exceptions(self) -> None:
        self.login(self.operator())
        response = self.client.post(
            self.url, {"company": str(self.company.pk), "requirement": "waived", "action": "save"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ChecklistExpectation.objects.exists())

    def test_exception_on_a_foreign_type_is_a_404(self) -> None:
        other = self.make_office("e11-cat-other7")
        foreign = self.make_type(other)
        url = reverse("hub:triage-catalog-exception", args=[foreign.pk])
        response = self.client.post(
            url, {"company": str(self.company.pk), "requirement": "waived", "action": "save"}
        )
        self.assertEqual(response.status_code, 404)
