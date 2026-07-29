from __future__ import annotations

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.audit.services import record_event


@receiver(user_logged_in)
def audit_login(sender: object, request: object, user: object, **kwargs: object) -> None:
    record_event(action="auth.login", actor=user, request=request)


@receiver(user_logged_out)
def audit_logout(sender: object, request: object, user: object, **kwargs: object) -> None:
    record_event(action="auth.logout", actor=user, request=request)


@receiver(user_login_failed)
def audit_login_failure(
    sender: object,
    credentials: dict[str, object],
    request: object,
    **kwargs: object,
) -> None:
    record_event(action="auth.login_failed", request=request, success=False)
