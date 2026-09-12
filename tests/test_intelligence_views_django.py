from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany
from apps.intelligence.models import AnswerFeedback, Conversation, LearningCandidate, Message
from apps.organizations.models import Membership, Organization


class IntelligenceViewsTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.owner = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization, user=self.owner, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Acme", dominio_code="001"
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def assistant_message(self) -> Message:
        conversation = Conversation.objects.create(
            organization=self.organization, company=self.company
        )
        return Message.objects.create(
            organization=self.organization,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Resposta rastreável.",
            evidence=[{"label": "Manual", "reference": "Procedimento", "detail": "Aprovado"}],
        )

    def test_assistant_requires_company_scope_and_keeps_conversation_in_that_company(self) -> None:
        page = self.client.get(reverse("intelligence:assistant"))
        invalid = self.client.post(reverse("intelligence:assistant"), {"question": ""})
        answered = self.client.post(
            reverse("intelligence:assistant"),
            {"question": "Quais são as pendências?", "company_id": str(self.company.id)},
        )

        self.assertEqual(page.status_code, 200)
        self.assertEqual(invalid.status_code, 200)
        self.assertContains(invalid, "Este campo é obrigatório")
        self.assertEqual(answered.status_code, 302)
        self.assertTrue(
            Conversation.objects.filter(
                organization=self.organization, company=self.company
            ).exists()
        )

    def test_feedback_and_learning_review_are_auditable_and_curator_gated(self) -> None:
        message = self.assistant_message()
        feedback = self.client.post(
            reverse("intelligence:feedback", args=[message.id]),
            {"verdict": AnswerFeedback.Verdict.NOT_HELPFUL, "comment": "Precisa citar a regra."},
        )
        stored_feedback = AnswerFeedback.objects.get(message=message, submitted_by=self.owner)
        candidate = LearningCandidate.objects.get(feedback=stored_feedback)

        center = self.client.get(reverse("intelligence:learning"))
        approved = self.client.post(reverse("intelligence:review", args=[candidate.id, "approve"]))
        candidate.refresh_from_db()

        self.assertRedirects(
            feedback, reverse("intelligence:assistant") + f"?conversation={message.conversation_id}"
        )
        self.assertEqual(center.status_code, 200)
        self.assertRedirects(approved, reverse("intelligence:learning"))
        self.assertEqual(candidate.status, LearningCandidate.Status.APPROVED)
        self.assertEqual(candidate.reviewed_by, self.owner)

        manager = User.objects.create_user("manager@example.test", "safe-password-123")
        Membership.objects.create(
            organization=self.organization, user=manager, role=Membership.Role.MANAGER
        )
        self.client.force_login(manager)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()
        forbidden = self.client.get(reverse("intelligence:learning"))
        self.assertEqual(forbidden.status_code, 403)
