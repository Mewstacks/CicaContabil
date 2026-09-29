from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import DreAccountMapping, DreMappingSet
from apps.organizations.models import Membership, Organization


class DreMappingEditorTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Escritorio", slug="dre-editor")
        self.user = User.objects.create_user(email="admin@example.test", password="senha-segura")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.ADMIN
        )
        self.client.force_login(self.user)
        self.url = reverse("hub:dre-mapping-editor")

    def data(self, rows: list[tuple[str, str, str]]) -> dict[str, str]:
        payload = {
            "mapping-TOTAL_FORMS": "5",
            "mapping-INITIAL_FORMS": "0",
            "mapping-MIN_NUM_FORMS": "0",
            "mapping-MAX_NUM_FORMS": "250",
        }
        for index, (account, group, sign) in enumerate(rows):
            payload[f"mapping-{index}-account_code"] = account
            payload[f"mapping-{index}-group"] = group
            payload[f"mapping-{index}-sign"] = sign
        return payload

    def test_editor_creates_new_version_without_mutating_prior_rows(self) -> None:
        previous = DreMappingSet.objects.create(
            organization=self.organization,
            version=1,
            label="Anterior",
            is_active=True,
            created_by=self.user,
        )
        DreAccountMapping.objects.create(
            mapping_set=previous, account_code="3.01", group="Receita anterior", sign=-1
        )

        response = self.client.post(
            self.url, self.data([("3.01", "Receita", "-1"), ("4.01", "Despesa", "1")])
        )

        self.assertRedirects(response, self.url)
        previous.refresh_from_db()
        active = DreMappingSet.objects.get(organization=self.organization, is_active=True)
        self.assertFalse(previous.is_active)
        self.assertEqual(previous.mappings.get().group, "Receita anterior")
        self.assertEqual(active.version, 2)
        self.assertEqual(active.mappings.count(), 2)

    def test_editor_keeps_current_version_when_duplicate_account_is_invalid(self) -> None:
        current = DreMappingSet.objects.create(
            organization=self.organization,
            version=1,
            label="Atual",
            is_active=True,
            created_by=self.user,
        )

        response = self.client.post(
            self.url, self.data([("3.01", "Receita", "-1"), ("3.01", "Outra", "1")])
        )

        self.assertEqual(response.status_code, 200)
        current.refresh_from_db()
        self.assertTrue(current.is_active)
        self.assertEqual(DreMappingSet.objects.filter(organization=self.organization).count(), 1)
        self.assertContains(response, "aparece mais de uma vez")
