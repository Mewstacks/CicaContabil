from __future__ import annotations

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts import totp
from apps.accounts.models import RecoveryCode, TotpDevice, User

SESSION_KEY = "mfa_verified_device"
ISSUER = "CICA"


def has_platform_exemption(user: User) -> bool:
    """Return whether the platform account explicitly bypasses MFA.

    The flag is an explicit administrative exception and therefore wins over a
    historical TOTP device or any tenant preference.
    """

    from apps.platform.models import PlatformAccess

    return PlatformAccess.objects.filter(user=user, mfa_required=False).exists()


def is_required(user: User) -> bool:
    """Who must present a second factor.

    Platform access follows its explicit policy. Customer accounts are never
    forced to enroll, but once a customer voluntarily confirms a TOTP device it
    protects subsequent sessions.
    """

    from apps.platform.models import PlatformAccess

    access = PlatformAccess.objects.filter(user=user).only("mfa_required").first()
    if access is not None:
        return access.mfa_required
    return is_enrolled(user)


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


def confirm_enrollment(device: TotpDevice, code: str) -> bool:
    """Confirm the authenticator without issuing a second set of credentials."""

    counter = totp.verify(device.secret, code)
    if counter is None:
        return False
    with transaction.atomic():
        device.confirmed_at = timezone.now()
        device.last_counter = counter
        device.save(update_fields=["confirmed_at", "last_counter", "updated_at"])
        # Recovery codes were removed from the product. Clear any historical
        # rows when an authenticator is enrolled again.
        RecoveryCode.objects.filter(user=device.user).delete()
    return True


def check_code(user: User, code: str) -> bool:
    """Accept only a fresh authenticator code."""

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
    return False


def mark_verified(request: HttpRequest) -> None:
    request.session[SESSION_KEY] = True
    request.session.cycle_key()


def session_is_verified(request: HttpRequest) -> bool:
    return bool(request.session.get(SESSION_KEY))
