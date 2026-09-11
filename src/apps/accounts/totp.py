from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

DIGITS = 6
PERIOD_SECONDS = 30
SECRET_BYTES = 20


def generate_secret() -> str:
    """A base32 secret, the encoding every authenticator app expects."""

    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii").rstrip("=")


def counter_at(moment: float | None = None) -> int:
    return int((moment if moment is not None else time.time()) // PERIOD_SECONDS)


def code_for(secret: str, counter: int, *, digits: int = DIGITS) -> str:
    """RFC 6238 / RFC 4226 HOTP over the stdlib HMAC primitive."""

    padding = "=" * (-len(secret) % 8)
    key = base64.b32decode(secret.upper() + padding, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10**digits)).zfill(digits)


def verify(secret: str, code: str, *, at: float | None = None, drift: int = 1) -> int | None:
    """Return the counter the code belongs to, or None.

    The caller stores that counter and refuses anything at or below it, so a code
    observed in transit cannot be replayed inside its own validity window.
    """

    candidate = "".join(character for character in code if character.isdigit())
    if len(candidate) != DIGITS:
        return None
    current = counter_at(at)
    for offset in range(-drift, drift + 1):
        counter = current + offset
        if counter >= 0 and hmac.compare_digest(code_for(secret, counter), candidate):
            return counter
    return None


def provisioning_uri(secret: str, *, account: str, issuer: str) -> str:
    label = quote(f"{issuer}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD_SECONDS}"
    )
