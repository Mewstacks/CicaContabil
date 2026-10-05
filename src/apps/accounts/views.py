from __future__ import annotations

import io

import qrcode
import qrcode.image.svg
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.accounts import mfa
from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited
from apps.common.redirects import safe_next
from apps.platform.models import PlatformAccess
from apps.platform.services import has_platform_role


def _mfa_landing(user: User) -> str:
    if has_platform_role(
        user,
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.SUPPORT,
        PlatformAccess.Role.COMMERCIAL,
    ):
        return reverse("platform:dashboard")
    return reverse("hub:dashboard")


def _safe_mfa_next(request: HttpRequest, user: User, candidate: str | None) -> str:
    target = safe_next(request, candidate, fallback=_mfa_landing(user))
    if target == reverse("hub:dashboard") and _mfa_landing(user) == reverse("platform:dashboard"):
        return reverse("platform:dashboard")
    return target


class CodeForm(forms.Form):
    code = forms.CharField(
        label="Código",
        max_length=16,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "autocapitalize": "none",
                "inputmode": "numeric",
                "spellcheck": "false",
                "placeholder": "Código de acesso…",
            }
        ),
    )


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def setup(request: HttpRequest) -> HttpResponse:
    user = request.user
    assert isinstance(user, User)
    if mfa.has_platform_exemption(user) and not mfa.is_required(user):
        return redirect(_mfa_landing(user))
    if mfa.is_enrolled(user):
        return redirect("accounts:mfa-verify")

    device = mfa.device_for(user) if request.method == "POST" else mfa.start_enrollment(user)
    if device is None:
        return redirect("accounts:mfa-setup")
    next_url = _safe_mfa_next(request, user, request.POST.get("next") or request.GET.get("next"))
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not mfa.confirm_enrollment(device, form.cleaned_data["code"]):
            form.add_error("code", "Código inválido. Confira o aplicativo e tente o código atual.")
        else:
            mfa.mark_verified(request)
            record_event(action="accounts.mfa.enrolled", actor=user, request=request)
            return redirect(next_url)
    return render(
        request,
        "accounts/mfa_setup.html",
        {
            "form": form,
            "secret": device.secret,
            "uri": mfa.provisioning_uri(device),
            "next": next_url,
        },
    )


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def verify(request: HttpRequest) -> HttpResponse:
    user = request.user
    assert isinstance(user, User)
    if mfa.has_platform_exemption(user) and not mfa.is_required(user):
        return redirect(_mfa_landing(user))
    if not mfa.is_enrolled(user):
        return redirect("accounts:mfa-setup")
    if mfa.session_is_verified(request):
        return redirect(_mfa_landing(user))

    form = CodeForm(request.POST or None)
    if request.method == "POST" and rate_limited(
        f"mfa:{user.pk}:{client_ip(request)}",
        limit=settings.MFA_ATTEMPTS_PER_MINUTE,
        window_seconds=60,
    ):
        # A six-digit code is guessable at volume; the attempt budget is what makes it not.
        form.add_error(None, "Muitas tentativas. Aguarde um minuto.")
    elif request.method == "POST" and form.is_valid():
        if mfa.check_code(user, form.cleaned_data["code"]):
            mfa.mark_verified(request)
            record_event(action="accounts.mfa.verified", actor=user, request=request)
            return redirect(_safe_mfa_next(request, user, request.POST.get("next")))
        form.add_error("code", "Código inválido ou usado. Gere um novo código no autenticador.")
        record_event(action="accounts.mfa.failed", actor=user, request=request)

    return render(
        request,
        "accounts/mfa_verify.html",
        {
            "form": form,
            "next": _safe_mfa_next(
                request, user, request.POST.get("next") or request.GET.get("next")
            ),
        },
    )


@login_required
@require_http_methods(["GET"])
def enrollment_qr(request: HttpRequest) -> HttpResponse:
    """The provisioning URI as an SVG, so the secret never leaves this origin."""

    user = request.user
    assert isinstance(user, User)
    if mfa.has_platform_exemption(user) and not mfa.is_required(user):
        raise Http404
    device = mfa.device_for(user)
    if device is None or device.is_confirmed:
        raise Http404
    image = qrcode.make(
        mfa.provisioning_uri(device), image_factory=qrcode.image.svg.SvgPathImage, box_size=12
    )
    buffer = io.BytesIO()
    image.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="image/svg+xml")
    response["Cache-Control"] = "no-store"
    return response
