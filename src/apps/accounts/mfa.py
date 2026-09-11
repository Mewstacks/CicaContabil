from __future__ import annotations

import hashlib
import secrets

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts import totp
from apps.accounts.models import RecoveryCode, TotpDevice, User

SESSION_KEY = "mfa_verified_device"
RECOVERY_CODE_COUNT = 8
ISSUER = "HubContador"


def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().replace("-", "").casefold().encode()).hexdigest()


def is_required(user: User) -> bool:
    """Who must present a second factor.

    The platform console reaches across every tenant, so its operators always do.
    An office turns it on for its own members through the office profile.
    """

    from apps.hub.models import OfficeProfile
    from apps.platform.models import PlatformAccess

    if PlatformAccess.objects.filter(user=user, mfa_required=True).exists():
        return True
    return OfficeProfile.objects.filter(
        require_mfa=True,
        organization__memberships__user=user,
        organization__memberships__is_active=True,
    ).exists()


def device_for(user: User) -> TotpDevice | None:
    return TotpDevice.objects.filter(user=user).first()


def is_enrolled(user: User) -> bool:
    device = device_for(user)
    return device is not None and device.is_confirmed


def start_enrollment(user: User) -> TotpDevice:
    """Replace any unconfirmed device so an abandoned attempt cannot linger."""

    device = device_for(user)
    if device is not None and device.is_confirmed:
        return device
    if device is not None:
        device.delete()
    return TotpDevice.objects.create(user=user, secret=totp.generate_secret())


def provisioning_uri(device: TotpDevice) -> str:
    return totp.provisioning_uri(device.secret, account=device.user.email, issuer=ISSUER)


def confirm_enrollment(device: TotpDevice, code: str) -> list[str] | None:
    """Confirm the device and hand back the recovery codes, shown exactly once."""

    counter = totp.verify(device.secret, code)
    if counter is None:
        return None
    with transaction.atomic():
        device.confirmed_at = timezone.now()
        device.last_counter = counter
        device.save(update_fields=["confirmed_at", "last_counter", "updated_at"])
        return _issue_recovery_codes(device.user)


def _issue_recovery_codes(user: User) -> list[str]:
    RecoveryCode.objects.filter(user=user).delete()
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(3)}" for _ in range(RECOVERY_CODE_COUNT)]
    RecoveryCode.objects.bulk_create(
        [RecoveryCode(user=user, code_hash=_hash(code)) for code in codes]
    )
    return codes


def reissue_recovery_codes(user: User) -> list[str]:
    return _issue_recovery_codes(user)


def check_code(user: User, code: str) -> bool:
    """Accept a fresh authenticator code, or spend one recovery code."""

    device = device_for(user)
    if device is None or not device.is_confirmed:
        return False
    counter = totp.verify(device.secret, code)
    if counter is not None:
        if counter <= device.last_counter:
            # Already spent: refuse the replay rather than honour the rest of the window.
            return False
        device.last_counter = counter
        device.save(update_fields=["last_counter", "updated_at"])
        return True
    spent = RecoveryCode.objects.filter(
        user=user, code_hash=_hash(code), used_at__isnull=True
    ).update(used_at=timezone.now())
    return bool(spent)


def mark_verified(request: HttpRequest) -> None:
    request.session[SESSION_KEY] = True
    request.session.cycle_key()


def session_is_verified(request: HttpRequest) -> bool:
    return bool(request.session.get(SESSION_KEY))
