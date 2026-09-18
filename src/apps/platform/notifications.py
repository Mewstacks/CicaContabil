from __future__ import annotations

from smtplib import SMTPException

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.platform.models import Invitation


class TransactionalEmailError(RuntimeError):
    """A delivery failure safe to surface as an operational form error."""


def send_transactional_email(*args, **kwargs) -> None:
    try:
        delivered = send_mail(*args, fail_silently=False, **kwargs)
    except (ImproperlyConfigured, OSError, SMTPException) as exc:
        raise TransactionalEmailError("E-mail transacional indisponível.") from exc
    if delivered != 1:
        raise TransactionalEmailError("E-mail transacional indisponível.")


def send_invitation_email(*, invitation: Invitation, activation_url: str) -> None:
    """Deliver the activation link out of band.

    The link is a bearer credential: anyone holding it acts as the invited person.
    Showing it to whoever issued the invitation would hand that person an access
    path into the tenant they just created.
    """

    send_transactional_email(
        subject=f"Acesso ao CICA — {invitation.organization.name}",
        message=(
            f"{invitation.organization.name} criou um acesso para você no CICA.\n\n"
            f"{activation_url}\n\n"
            "O link expira em 7 dias e só pode ser usado uma vez."
        ),
        # The developer-console transport supplies the configured sender.  Do
        # not pin an environment default here: that would silently bypass it.
        from_email=None,
        recipient_list=[invitation.email],
        html_message=render_to_string(
            "platform/emails/invitation.html",
            {
                "activation_url": activation_url,
                "organization_name": invitation.organization.name,
            },
        ),
    )
