from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, OnboardingProgress, ProductModule
from apps.hub.onboarding import TOURS_BY_ID, tour_for_url_name
from apps.organizations.models import Membership, Organization


class OnboardingTourTests(TestCase):
    """The orientation opens once per person and version, and never hijacks a task."""

    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Orientação", slug="orientacao")
        self.user = User.objects.create_user("guia@example.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.NFSE, enabled=True
        )
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Empresa Guia", dominio_code="0101"
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def test_the_welcome_tour_opens_on_the_first_visit_and_not_after_completion(self) -> None:
        first = self.client.get(reverse("hub:dashboard"))

        self.assertContains(first, 'data-onboarding-id="welcome"')
        self.assertContains(first, 'data-onboarding-auto="true"')

        recorded = self.client.post(reverse("hub:onboarding-complete", args=["welcome"]))
        self.assertEqual(recorded.status_code, 204)

        second = self.client.get(reverse("hub:dashboard"))

        self.assertContains(second, 'data-onboarding-auto="false"')
        self.assertContains(second, "Como usar")

    def test_a_new_version_of_a_tour_opens_again(self) -> None:
        OnboardingProgress.objects.create(user=self.user, tour_id="welcome", version=1)
        self.assertContains(
            self.client.get(reverse("hub:dashboard")), 'data-onboarding-auto="false"'
        )

        OnboardingProgress.objects.filter(user=self.user, tour_id="welcome").update(version=0)

        self.assertContains(
            self.client.get(reverse("hub:dashboard")), 'data-onboarding-auto="true"'
        )

    def test_a_detail_screen_never_opens_an_orientation(self) -> None:
        detail = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertNotContains(detail, "data-onboarding-id")

    def test_every_module_tour_has_at_most_three_steps_and_a_way_out(self) -> None:
        for tour in TOURS_BY_ID.values():
            self.assertLessEqual(len(tour.steps), 3, tour.identifier)
            self.assertTrue(tour.url_names, tour.identifier)

        page = self.client.get(reverse("hub:dashboard"))

        self.assertContains(page, "data-onboarding-skip")
        self.assertContains(page, "data-onboarding-back")
        self.assertContains(page, "data-onboarding-close")

    def test_an_unknown_tour_is_refused_without_creating_progress(self) -> None:
        response = self.client.post(reverse("hub:onboarding-complete", args=["inexistente"]))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(OnboardingProgress.objects.filter(user=self.user).exists())

    def test_the_catalogue_only_anchors_tours_to_main_screens(self) -> None:
        self.assertIsNotNone(tour_for_url_name("dashboard"))
        self.assertIsNone(tour_for_url_name("company-detail"))
        self.assertIsNone(tour_for_url_name("review-detail"))
        self.assertIsNone(tour_for_url_name(None))
