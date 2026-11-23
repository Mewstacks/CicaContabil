"""D-394: the technical author of automatic title interpretations; never a person, never a login."""

from __future__ import annotations

from typing import Any

from apps.accounts.models import User

ROBOT_EMAIL = "interpretacao-automatica@cica.invalid"
ROBOT_NAME = "CICA — interpretação automática"


def title_robot() -> User:
    user, created = User.objects.get_or_create(
        email=ROBOT_EMAIL, defaults={"full_name": ROBOT_NAME, "is_active": False}
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def is_title_robot(actor: Any) -> bool:
    return bool(
        isinstance(actor, User)
        and actor.email == ROBOT_EMAIL
        and not actor.is_active
        and not actor.has_usable_password()
    )
