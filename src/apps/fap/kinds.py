"""Tipo de trabalho RPA do FAP (registrado em ``FapConfig.ready``)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ProductModule
from apps.rpa import registry
from apps.rpa.registry import RpaKind

KIND = "fap.consultar"
#: O FAPWeb usa o navegador autenticado da sessão interativa, disputada por todo o RPA.
DESKTOP_GROUP = "dominio_desktop"


def _s() -> Any:
    from . import services

    return services


registry.register(
    RpaKind(
        code=KIND,
        module_code=ProductModule.Code.FAP,
        label="Consulta do FAP no portal (PDF oficial)",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=600,
        max_attempts=3,
        validate_payload=lambda p: _s().validate_payload(p),
        validate_result=lambda r: _s().validate_result(r),
        prepare_claim=lambda job: _s().prepare_claim(job),
        on_success=lambda job: _s().on_success(job),
        on_failure=lambda job: _s().on_failure(job),
        result_keys=frozenset({"status", "sha256", "message"}),
    )
)
