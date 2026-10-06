"""D-277 phase 4: the office's profile of a client and default owners per area."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAccessGrant,
    CompanyAreaResponsible,
    OperationalActivity,
)
from apps.hub.operations import generate_monthly_activities
from apps.organizations.models import Membership, Organization


class CompanyProfileTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            "owner@example.test", "safe-password-123", full_name="Dona"
        )
        self.operator = User.objects.create_user(
            "ana@example.test", "safe-password-123", full_name="Ana Martins"
        )
        self.office = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )
        operator_membership = Membership.objects.create(
            organization=self.office, user=self.operator, role=Membership.Role.OPERATOR
        )
        # Identity comes from an external source: name/CNPJ are not editable here.
        self.company = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Vila Nova",
            cnpj_masked="12.345.678/0001-95",
            external_key="dominio:0101",
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=operator_membership,
            company=self.company,
            capabilities=["*"],
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def _post_profile(self, **values: str):  # type: ignore[no-untyped-def]
        payload = {
            "action": "update_profile",
            "profile-tax_regime": "simples",
            "profile-state_registration": "096/1234567",
            "profile-municipal_registration": "55443",
            "profile-contact_name": "Marta",
            "profile-contact_email": "marta@padaria.example",
            "profile-contact_phone": "(51) 99999-0000",
            "profile-responsible_fiscal": str(self.operator.pk),
            **values,
        }
        return self.client.post(reverse("hub:company-detail", args=[self.company.pk]), payload)

    def test_profile_is_editable_even_when_identity_comes_from_the_source(self) -> None:
        page = self.client.get(reverse("hub:company-detail", args=[self.company.pk]))
        self.assertContains(page, "Editar perfil")
        self.assertNotContains(page, 'data-modal-open="company-edit-dialog"')

        response = self._post_profile()

        self.assertEqual(response.status_code, 302)
        self.company.refresh_from_db()
        self.assertEqual(self.company.tax_regime, ClientCompany.TaxRegime.SIMPLES)
        self.assertEqual(self.company.contact_email, "marta@padaria.example")
        self.assertEqual(
            CompanyAreaResponsible.objects.get(company=self.company, area="fiscal").user,
            self.operator,
        )
        event = AuditEvent.objects.get(action="hub.company.profile_updated")
        self.assertIn("contact_email", event.metadata["changed_fields"])
        self.assertNotIn("marta@padaria.example", str(event.metadata))
        page = self.client.get(reverse("hub:company-detail", args=[self.company.pk]))
        self.assertContains(page, "Simples Nacional")
        self.assertContains(page, "Fiscal · Ana Martins")

    def test_unassigned_template_falls_back_to_the_area_owner(self) -> None:
        CompanyAreaResponsible.objects.create(
            organization=self.office, company=self.company, area="fiscal", user=self.operator
        )
        template = ActivityTemplate.objects.create(
            organization=self.office,
            code="apuracao",
            title="Conferir apuração",
            area="fiscal",
            internal_due_day=10,
            due_month_offset=1,
        )
        assignment = ActivityTemplateAssignment.objects.create(
            organization=self.office, company=self.company, template=template
        )

        generate_monthly_activities(
            assignments=[assignment], competence=date(2026, 9, 1), actor=None, request=None
        )

        self.assertEqual(OperationalActivity.objects.get().assigned_to, self.operator)

    def test_area_owner_without_access_is_not_used(self) -> None:
        outsider = User.objects.create_user("fora@example.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=outsider, role=Membership.Role.OPERATOR
        )
        CompanyAreaResponsible.objects.create(
            organization=self.office, company=self.company, area="fiscal", user=outsider
        )
        template = ActivityTemplate.objects.create(
            organization=self.office, code="apuracao", title="Conferir apuração", area="fiscal"
        )
        assignment = ActivityTemplateAssignment.objects.create(
            organization=self.office, company=self.company, template=template
        )

        generate_monthly_activities(
            assignments=[assignment], competence=date(2026, 9, 1), actor=None, request=None
        )

        self.assertIsNone(OperationalActivity.objects.get().assigned_to)

    def test_companies_list_shows_and_filters_by_regime(self) -> None:
        self.company.tax_regime = ClientCompany.TaxRegime.PRESUMIDO
        self.company.save()
        ClientCompany.objects.create(organization=self.office, name="Sem regime")

        listing = self.client.get(reverse("hub:companies"), {"regime": "presumido"})
        missing = self.client.get(reverse("hub:companies"), {"regime": "nao_informado"})

        self.assertContains(listing, "Lucro Presumido")
        self.assertContains(listing, "Padaria Vila Nova")
        self.assertNotContains(listing, "Sem regime")
        self.assertContains(missing, "Sem regime")
        self.assertNotContains(missing, "Padaria Vila Nova")
