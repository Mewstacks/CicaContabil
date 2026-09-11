from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from apps.platform.models import Invitation


def send_invitation_email(*, invitation: Invitation, activation_url: str) -> None:
    """Deliver the activation link out of band.

    The link is a bearer credential: anyone holding it acts as the invited person.
    Showing it to whoever issued the invitation would hand that person an access
    path into the tenant they just created.
    """

    send_mail(
        subject=f"Acesso ao HubContador — {invitation.organization.name}",
        message=(
            f"{invitation.organization.name} criou um acesso para você no HubContador.\n\n"
            f"{activation_url}\n\n"
            "O link expira em 7 dias e só pode ser usado uma vez."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        fail_silently=False,
    )
