"""Tela de consentimento do gateway MCP externo (D-333).

Tudo que o DOT valida continua valendo (cliente, redirecionamento exato, PKCE S256). Aqui entram
regras a mais: `resource` obrigatorio e igual ao recurso do gateway, PKCE S256 ja na primeira
tela, consentimento sempre pedido (o `approval_prompt=auto` do cliente e ignorado), o escritorio
escolhido entre os da pessoa e o vinculo (pessoa, cliente) -> escritorio que o endpoint le a cada
chamada. O vinculo, a revogacao e os codigos antigos so mudam se a autorizacao de fato der certo.

O login e o segundo fator vêm do `LOGIN_URL` e do middleware de MFA, que segue a politica da
conta (quem ainda nao cadastrou o segundo fator entra como entra no resto do CICA).
"""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import parse_qs, urlsplit

from django import forms
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.csp import CSP
from oauth2_provider.forms import AllowForm
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_grant_model,
    get_refresh_token_model,
)
from oauth2_provider.views import AuthorizationView

from apps.audit.services import record_event
from apps.mcpgateway import conf
from apps.mcpgateway.models import McpConsent
from apps.organizations.models import Membership


def _memberships(user: Any) -> list[Membership]:
    return list(
        Membership.objects.select_related("organization")
        .filter(user=user, is_active=True, organization__is_active=True)
        .order_by("organization__name")
    )


class OrganizationAllowForm(AllowForm):
    organization = forms.ChoiceField(label="Escritório", choices=())

    def __init__(self, *args: Any, user: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices = [(str(m.organization_id), m.organization.name) for m in _memberships(user)]
        self.fields["organization"].choices = choices
        if len(choices) == 1:
            self.fields["organization"].initial = choices[0][0]


def _bad_target() -> HttpResponse:
    response = JsonResponse(
        {
            "error": "invalid_target",
            "error_description": "O parametro resource deve ser o recurso deste servidor.",
        },
        status=400,
    )
    response["Cache-Control"] = "no-store"
    return response


def _resource_ok(values: list[str]) -> bool:
    return values == [conf.resource_url()]


def _bad_pkce() -> HttpResponse:
    response = JsonResponse(
        {
            "error": "invalid_request",
            "error_description": "Use code_challenge_method=S256.",
        },
        status=400,
    )
    response["Cache-Control"] = "no-store"
    return response


def _issued_code(response: HttpResponse) -> bool:
    if response.status_code != 302:
        return False
    return "code" in parse_qs(urlsplit(str(response["Location"])).query)


def _form_action_source(redirect_uri: str) -> str | None:
    parts = urlsplit(redirect_uri)
    if not parts.scheme or not parts.hostname:
        return None
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    if parts.hostname in {"127.0.0.1", "::1", "localhost"}:
        return f"{parts.scheme}://{host}:*"  # loopback: a porta muda a cada execucao
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


class McpAuthorizationView(AuthorizationView):
    template_name = "mcpgateway/authorize.html"
    form_class = OrganizationAllowForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not conf.enabled():
            return HttpResponse(status=404)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["redirect_host"] = urlsplit(str(context.get("redirect_uri", ""))).netloc
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not _resource_ok(request.GET.getlist("resource")):
            return _bad_target()
        if request.GET.get("code_challenge_method") != "S256":
            return _bad_pkce()
        query = request.GET.copy()
        query["approval_prompt"] = "force"  # o cliente nao escolhe pular o consentimento
        request.GET = query  # type: ignore[assignment]
        response = super().get(request, *args, **kwargs)
        if response.status_code == 200:
            source = _form_action_source(str(request.GET.get("redirect_uri", "")))
            if source:
                # `form-action 'self'` tambem vale para o redirecionamento depois do POST no
                # Chromium: sem a origem do cliente o botao Autorizar nao leva a lugar nenhum.
                policy = dict(settings.SECURE_CSP)
                policy["form-action"] = [CSP.SELF, source]
                response._csp_config = policy
        return response

    def form_valid(self, form: forms.Form) -> HttpResponse:
        if not _resource_ok(str(form.cleaned_data.get("resource", "")).split()):
            return _bad_target()
        allow = bool(form.cleaned_data.get("allow"))
        with transaction.atomic():
            if allow:
                application = get_application_model().objects.get(
                    client_id=form.cleaned_data["client_id"]
                )
                self._bind(application, form.cleaned_data["organization"])
            response = super().form_valid(form)
            if allow and not _issued_code(response):
                transaction.set_rollback(True)  # nada do vinculo vale se nao saiu codigo
        return response

    def _bind(self, application: Any, organization_id: str) -> None:
        membership = next(
            m for m in _memberships(self.request.user) if str(m.organization_id) == organization_id
        )
        consent, created = McpConsent.objects.select_for_update().get_or_create(
            user=self.request.user,
            application=application,
            defaults={"organization": membership.organization},
        )
        if not created and consent.organization_id != membership.organization_id:
            revoked = revoke_tokens(user=self.request.user, application=application)
            # codigo ainda nao trocado, emitido para o escritorio antigo, tambem morre
            get_grant_model().objects.filter(
                user=self.request.user, application=application
            ).delete()
            record_event(
                action="mcpgateway.tokens_revoked",
                actor=self.request.user,
                organization=consent.organization,
                request=self.request,
                metadata={"reason": "office_changed", "refresh_tokens": revoked},
            )
            consent.organization = membership.organization
            consent.save(update_fields=["organization", "updated_at"])
        record_event(
            action="mcpgateway.consent_granted",
            actor=self.request.user,
            organization=membership.organization,
            request=self.request,
            metadata={
                "client_ref": hashlib.sha256(application.client_id.encode()).hexdigest()[:16],
                "client_name": str(application.name)[:80],
                "scope": conf.required_scope(),
            },
        )


def revoke_tokens(*, user: Any, application: Any) -> int:
    """Revoga os tokens de refresh e os de acesso da pessoa neste cliente (efeito imediato)."""
    count = 0
    for token in get_refresh_token_model().objects.filter(
        user=user, application=application, revoked__isnull=True
    ):
        token.revoke()
        count += 1
    get_access_token_model().objects.filter(user=user, application=application).update(
        expires=timezone.now()
    )
    return count
