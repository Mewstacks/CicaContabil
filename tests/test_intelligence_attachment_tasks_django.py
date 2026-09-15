from __future__ import annotations

import base64
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.intelligence.models import ChatAttachment, Conversation, Message
from apps.intelligence.services import prior_attachment_cards
from apps.intelligence.tasks import analyze_attachment_task, retry_pending_attachments_task
from apps.organizations.models import Organization
from apps.platform.models import PlatformConfiguration


class AttachmentAnalysisTaskTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.conversation = Conversation.objects.create(
            organization=self.organization, title="Anexos"
        )
        self.message = Message.objects.create(
            organization=self.organization,
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Analise o anexo",
        )

    def attachment(self) -> ChatAttachment:
        return ChatAttachment.objects.create(
            organization=self.organization,
            conversation=self.conversation,
            message=self.message,
            original_name="pendencias.pdf",
            content_type="application/pdf",
            byte_size=8,
            content_hash="a" * 64,
            encrypted_content_b64=base64.b64encode(b"fake-pdf").decode(),
            status=ChatAttachment.Status.AWAITING_MODEL,
        )

    @patch(
        "apps.intelligence.tasks._analyze_with_private_model",
        return_value="Vencimento identificado.",
    )
    def test_worker_marks_attachment_analyzed_after_a_local_success(self, mocked_analysis) -> None:
        attachment = self.attachment()

        result = analyze_attachment_task.run(str(attachment.id))

        attachment.refresh_from_db()
        self.assertEqual(result["status"], "analyzed")
        self.assertEqual(attachment.status, ChatAttachment.Status.ANALYZED)
        self.assertEqual(attachment.analysis, "Vencimento identificado.")
        self.assertEqual(attachment.analysis_attempts, 1)
        mocked_analysis.assert_called_once_with(
            content=b"fake-pdf", content_type="application/pdf", name="pendencias.pdf"
        )

    @override_settings(INTELLIGENCE_ATTACHMENT_RETRY_LIMIT=2)
    @patch("apps.intelligence.tasks._analyze_with_private_model", return_value=None)
    def test_worker_stops_after_the_configured_retry_limit(self, _mocked_analysis) -> None:
        attachment = self.attachment()

        first = analyze_attachment_task.run(str(attachment.id))
        attachment.refresh_from_db()
        second = analyze_attachment_task.run(str(attachment.id))
        attachment.refresh_from_db()

        self.assertEqual(first["status"], ChatAttachment.Status.AWAITING_MODEL)
        self.assertEqual(second["status"], ChatAttachment.Status.FAILED)
        self.assertEqual(attachment.analysis_attempts, 2)
        self.assertEqual(attachment.analysis_error, "modelo_local_indisponivel")

    def test_previous_attachment_analysis_is_evidence_without_raw_attachment_content(self) -> None:
        attachment = self.attachment()
        attachment.status = ChatAttachment.Status.ANALYZED
        attachment.analysis = "Darf vence em 20/09."
        attachment.save(update_fields=["status", "analysis", "updated_at"])
        current = Message.objects.create(
            organization=self.organization,
            conversation=self.conversation,
            role=Message.Role.USER,
            content="E qual é o risco?",
        )

        cards = prior_attachment_cards(conversation=self.conversation, current_message=current)

        self.assertEqual(cards[0].detail, "Darf vence em 20/09.")
        self.assertNotIn("ZmFrZS1wZGY", cards[0].detail)

    @patch("apps.intelligence.tasks.analyze_attachment_task.delay")
    def test_periodic_retry_enqueues_identifiers_only(self, mocked_delay) -> None:
        PlatformConfiguration.objects.update_or_create(
            key="default", defaults={"local_multimodal_endpoint": "http://multimodal:8081"}
        )
        attachment = self.attachment()

        result = retry_pending_attachments_task.run()

        self.assertEqual(result, {"scheduled": 1})
        mocked_delay.assert_called_once_with(str(attachment.id))
