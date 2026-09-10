from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.intelligence.models import Conversation
from apps.intelligence.retention import purge_expired_conversations
from apps.organizations.models import Organization


class RetentionTests(TestCase):
    def test_dry_run_then_delete_expired_conversation(self) -> None:
        organization = Organization.objects.create(name="Acme", slug="acme")
        conversation = Conversation.objects.create(organization=organization)
        Conversation.objects.filter(id=conversation.id).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        preview = purge_expired_conversations(organization=organization, apply=False)
        applied = purge_expired_conversations(organization=organization, apply=True)

        self.assertEqual(preview.eligible, 1)
        self.assertEqual(applied.deleted, 1)
        self.assertFalse(Conversation.objects.filter(id=conversation.id).exists())
