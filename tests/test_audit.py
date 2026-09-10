from __future__ import annotations

from django.contrib.auth.signals import user_login_failed
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.common.encryption import blind_index


class AuditEventTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("audit@example.test", "safe-password-123")

    def test_audit_events_are_immutable_and_reject_sensitive_metadata(self) -> None:
        event = record_event(action="test.performed", actor=self.user, metadata={"result": "ok"})
        event.action = "test.changed"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
        with self.assertRaises(ValidationError):
            type(event).objects.filter(pk=event.pk).update(action="test.bulk_changed")

        with self.assertRaises(ValidationError):
            record_event(
                action="test.bad_metadata",
                actor=self.user,
                metadata={"context": {"email": "must-not-be-stored"}},
            )

    def test_failed_login_is_audited_with_a_hashed_username(self) -> None:
        request = RequestFactory().post("/login/", {"email": "victim@example.com"})
        user_login_failed.send(
            sender=None,
            credentials={"username": "victim@example.com"},
            request=request,
        )
        event = AuditEvent.objects.get(action="auth.login_failed")
        self.assertFalse(event.success)
        self.assertIsNone(event.actor)
        self.assertEqual(
            event.metadata["username_index"],
            blind_index("victim@example.com", namespace="audit-login-username"),
        )
        self.assertNotIn("victim@example.com", str(event.metadata))
