from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.common.encryption import EncryptedTextField
from apps.common.models import UUIDTimeStampedModel


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ("-date_joined",)

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.email = self.email.strip().casefold()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self) -> str:
        return self.email


class TotpDevice(UUIDTimeStampedModel):
    """One authenticator binding per account.

    ``last_counter`` is what stops a replay: a code observed in transit is refused
    once its own time step has been spent, instead of staying valid for the rest of
    the 30-second window.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="totp_device"
    )
    secret = EncryptedTextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_counter = models.BigIntegerField(default=0)

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None

    def __str__(self) -> str:
        return f"TOTP for {self.user_id}"


class RecoveryCode(UUIDTimeStampedModel):
    """A single-use way back in when the authenticator is lost. Stored hashed."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="recovery_codes"
    )
    code_hash = models.CharField(max_length=64, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "code_hash"), name="unique_recovery_code")
        ]
