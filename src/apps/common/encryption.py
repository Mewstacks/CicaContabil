from __future__ import annotations

import base64
import hashlib
import hmac
import os
from functools import lru_cache
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.db import models

PREFIX = "enc:v1"


def _decode_key(encoded: str, key_id: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(encoded)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(f"Field encryption key {key_id!r} is not valid base64.") from exc
    if len(key) != 32:
        raise ImproperlyConfigured(f"Field encryption key {key_id!r} must decode to 32 bytes.")
    return key


@lru_cache(maxsize=32)
def _key(key_id: str) -> bytes:
    encoded = settings.FIELD_ENCRYPTION_KEYS.get(key_id)
    if not encoded:
        raise ImproperlyConfigured(f"Field encryption key {key_id!r} is unavailable.")
    return _decode_key(encoded, key_id)


def encrypt_text(value: str, *, associated_data: bytes = b"") -> str:
    if not value or value.startswith(f"{PREFIX}:"):
        return value
    key_id = settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID
    if not key_id:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_ACTIVE_KEY_ID is not configured.")
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key(key_id)).encrypt(nonce, value.encode(), associated_data)
    encoded_nonce = base64.urlsafe_b64encode(nonce).decode()
    encoded_ciphertext = base64.urlsafe_b64encode(ciphertext).decode()
    return f"{PREFIX}:{key_id}:{encoded_nonce}:{encoded_ciphertext}"


def decrypt_text(value: str, *, associated_data: bytes = b"") -> str:
    if not value or not value.startswith(f"{PREFIX}:"):
        return value
    try:
        prefix, version, key_id, encoded_nonce, encoded_ciphertext = value.split(":", 4)
        if f"{prefix}:{version}" != PREFIX:
            raise ValueError
        nonce = base64.urlsafe_b64decode(encoded_nonce)
        ciphertext = base64.urlsafe_b64decode(encoded_ciphertext)
        plaintext = AESGCM(_key(key_id)).decrypt(nonce, ciphertext, associated_data)
    except (ValueError, InvalidTag) as exc:
        raise SuspiciousOperation("Encrypted field authentication failed.") from exc
    return plaintext.decode()


def blind_index(value: str, *, namespace: str) -> str:
    secret = settings.PRIVACY_HMAC_KEY
    if not secret:
        raise ImproperlyConfigured("PRIVACY_HMAC_KEY is not configured.")
    normalized = value.strip().casefold().encode()
    message = namespace.encode() + b"\0" + normalized
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class EncryptedTextField(models.TextField):  # type: ignore[type-arg]
    description = "AES-256-GCM encrypted text"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("editable", True)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> str | None:
        if value is None:
            return value
        return decrypt_text(value)

    def to_python(self, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        return decrypt_text(value)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value is None:
            return value
        return encrypt_text(str(value))
