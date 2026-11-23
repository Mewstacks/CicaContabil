"""Tags de template do modo procuração (D-304): leitura única por requisição, sem N+1."""

from __future__ import annotations

from typing import Any

from django import template

from apps.hub.models import NfseSync

register = template.Library()

TONES = {
    NfseSync.ProcuracaoStatus.OK: "is-active",
    NfseSync.ProcuracaoStatus.MISSING: "is-warning",
    NfseSync.ProcuracaoStatus.UNKNOWN: "is-muted",
    NfseSync.ProcuracaoStatus.ERROR: "is-danger",
}


@register.filter
def cnpj_mask(value: object) -> str:
    """`12345678000195` -> `12.345.678/0001-95`; anything else comes back as it was."""

    text = str(value or "")
    if len(text) != 14 or not text.isalnum():
        return text
    return f"{text[:2]}.{text[2:5]}.{text[5:8]}/{text[8:12]}-{text[12:]}"


@register.simple_tag(takes_context=True)
def procuracao_mode(context: template.Context) -> bool:
    """True when the active office collects NFS-e by procuração; legacy offices: False."""

    from apps.hub.navigation import _procuracao_mode

    return _procuracao_mode(context)


@register.simple_tag(takes_context=True)
def procuracao_state(context: template.Context, company: Any) -> dict[str, str]:
    """State of one company's procuração. One query per request for the whole office."""

    request = context["request"]
    states: dict[Any, str] | None = getattr(request, "_hub_procuracao_states", None)
    if states is None:
        office = context.get("office")
        states = (
            dict(
                NfseSync.objects.filter(
                    organization=office, credential_mode=NfseSync.CredentialMode.PROCURACAO
                ).values_list("company_id", "procuracao_status")
            )
            if office is not None
            else {}
        )
        request._hub_procuracao_states = states
    status = NfseSync.ProcuracaoStatus(states.get(company.pk, NfseSync.ProcuracaoStatus.UNKNOWN))
    return {"status": status.value, "label": status.label, "tone": TONES[status]}
