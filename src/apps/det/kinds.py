"""Tipo de trabalho RPA do DET (registrado em ``DetConfig.ready``)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ProductModule
from apps.rpa import registry
from apps.rpa.registry import RpaKind

KIND = "det.consultar"
#: O DET usa o navegador da sessão interativa, que Folha, FGTS e Admissões também disputam.
DESKTOP_GROUP = "dominio_desktop"


def _s() -> Any:
    from . import services

    return services


registry.register(
    RpaKind(
        code=KIND,
        module_code=ProductModule.Code.DET,
        label="Lista de mensagens não lidas do DET (somente leitura)",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=900,
        max_attempts=2,
        validate_payload=lambda p: _s().validate_payload(p),
        validate_result=lambda r: _s().validate_result(r),
        on_success=lambda job: _s().on_success(job),
        on_failure=lambda job: _s().on_failure(job),
        result_keys=frozenset({"results"}),
    )
)
