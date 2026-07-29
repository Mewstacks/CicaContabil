from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.services import record_event


@pytest.mark.django_db
def test_audit_events_are_immutable_and_reject_sensitive_metadata(user: User) -> None:
    event = record_event(action="test.performed", actor=user, metadata={"result": "ok"})
    event.action = "test.changed"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        type(event).objects.filter(pk=event.pk).update(action="test.bulk_changed")

    with pytest.raises(ValidationError):
        record_event(
            action="test.bad_metadata",
            actor=user,
            metadata={"context": {"email": "must-not-be-stored"}},
        )
