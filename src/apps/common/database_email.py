"""Transactional e-mail transport configured only in the developer console."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend

if TYPE_CHECKING:
    from apps.platform.models import PlatformConfiguration


def smtp_backend_for_configuration(
    configuration: PlatformConfiguration, *, fail_silently: bool = False
) -> SMTPEmailBackend:
    """Build an SMTP connection without ever returning the configured password."""

    required = {
        "servidor SMTP": configuration.transactional_email_host,
        "remetente": configuration.transactional_email_from,
    }
    missing = [label for label, value in required.items() if not value]
    if missing:
        raise ImproperlyConfigured(
            "E-mail transacional não está configurado: informe " + ", ".join(missing) + "."
        )
    return SMTPEmailBackend(
        host=configuration.transactional_email_host,
        port=configuration.transactional_email_port,
        username=configuration.transactional_email_username,
        password=configuration.transactional_email_password,
        use_tls=configuration.transactional_email_use_tls,
        use_ssl=False,
        timeout=10,
        fail_silently=fail_silently,
    )


class DatabaseEmailBackend(BaseEmailBackend):
    """Use the encrypted, developer-owned SMTP setup at message delivery time."""

    def _configuration(self) -> PlatformConfiguration | None:
        # Import lazily: Django imports mail backends while application registries start.
        from apps.platform.models import PlatformConfiguration

        return PlatformConfiguration.objects.filter(key="default").first()

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        if not email_messages:
            return 0
        configuration = self._configuration()
        if configuration is None:
            raise ImproperlyConfigured("E-mail transacional ainda não foi configurado.")
        for message in email_messages:
            # Django's ``send_mail(..., from_email=None)`` eagerly fills
            # DEFAULT_FROM_EMAIL. Treat that framework placeholder the same as
            # an omitted sender; do not override a sender an application flow
            # deliberately supplied.
            if not message.from_email or message.from_email == settings.DEFAULT_FROM_EMAIL:
                message.from_email = configuration.transactional_email_from
        return smtp_backend_for_configuration(
            configuration, fail_silently=self.fail_silently
        ).send_messages(email_messages)
