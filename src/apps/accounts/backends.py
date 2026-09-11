from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import BaseBackend

from apps.accounts.models import User


class IdentifierBackend(BaseBackend):
    """Authenticate by e-mail or by a unique, exact full name.

    Full names are deliberately accepted only when they identify exactly one active
    account. This keeps a convenient sign-in option without allowing a duplicate
    display name to select an arbitrary user.
    """

    def authenticate(
        self,
        request: Any | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        identifier = str(kwargs.get("identifier") or kwargs.get("email") or username or "").strip()
        if not identifier or password is None:
            return None

        user = User.objects.filter(email__iexact=identifier, is_active=True).first()
        if user is None:
            matches = list(User.objects.filter(full_name__iexact=identifier, is_active=True)[:2])
            user = matches[0] if len(matches) == 1 else None
        if user is None:
            # Argon2 is deliberately slow, so returning before hashing would make an
            # unknown identifier answer measurably faster than a known one and turn the
            # login form into an account-enumeration oracle. Pay the same cost either way.
            User().set_password(password)
            return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id: Any) -> User | None:
        return User.objects.filter(pk=user_id, is_active=True).first()
