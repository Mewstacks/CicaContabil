"""Tipos de trabalho RPA do FGTS Digital (registrados em ``FgtsConfig.ready``)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ProductModule
from apps.rpa import registry
from apps.rpa.registry import RpaKind

KIND_SOURCE = "fgts.fonte"
KIND_CHECK = "fgts.conferir"
KIND_EMIT = "fgts.emitir"
#: Compartilha a sessão interativa da máquina com Folha e Admissões.
DESKTOP_GROUP = "dominio_desktop"
#: Depois de entrar nesta fase o agente pode já ter clicado em emitir: não se repete sozinho.
EMIT_PHASE = "emissao"


def _s() -> Any:
    from . import services

    return services


def _need(*keys: str) -> Any:
    def check(payload: dict[str, Any]) -> None:
        for key in keys:
            if payload.get(key) in (None, ""):
                raise registry.RpaError("validacao", f"Carga sem {key}.")

    return check


registry.register(
    RpaKind(
        code=KIND_SOURCE,
        module_code=ProductModule.Code.FGTS,
        label="Apuração do FGTS no Domínio (leitura)",
        lease_seconds=300,
        max_attempts=2,
        validate_payload=_need("year", "month"),
        validate_result=lambda r: _s().validate_source_result(r),
        on_success=lambda job: _s().on_source_success(job),
        result_keys=frozenset({"groups", "pendencies"}),
    )
)
registry.register(
    RpaKind(
        code=KIND_CHECK,
        module_code=ProductModule.Code.FGTS,
        label="Conferência no portal do FGTS Digital (sem emitir)",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=600,
        max_attempts=2,
        validate_payload=_need("item_id", "root", "deadline"),
        validate_result=lambda r: _s().validate_check_result(r),
        on_success=lambda job: _s().on_check_success(job),
        on_failure=lambda job: _s().on_check_failure(job),
        result_keys=frozenset({"portal_cents", "portal_due"}),
    )
)
registry.register(
    RpaKind(
        code=KIND_EMIT,
        module_code=ProductModule.Code.FGTS,
        label="Emissão da guia no FGTS Digital",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=600,
        max_attempts=1,  # nunca uma segunda tentativa automática de emitir
        irreversible_phases=frozenset({EMIT_PHASE}),
        validate_payload=_need("item_id", "root", "expected_cents", "deadline"),
        validate_result=lambda r: _s().validate_emit_result(r),
        prepare_claim=lambda job: _s().prepare_emission_claim(job),
        on_success=lambda job: _s().on_emit_success(job),
        on_failure=lambda job: _s().on_emit_failure(job),
        on_uncertain=lambda job: _s().on_emit_uncertain(job),
        result_keys=frozenset({"portal_cents", "portal_due", "sha256"}),
    )
)
