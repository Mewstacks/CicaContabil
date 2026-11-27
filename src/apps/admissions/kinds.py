"""Tipo de trabalho RPA das Admissões (registrado em ``AdmissionsConfig.ready``)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ProductModule
from apps.rpa import registry
from apps.rpa.registry import RpaKind

KIND = "admissions.cadastrar"
DESKTOP_GROUP = "dominio_desktop"
#: Depois de entrar nesta fase o agente pode já ter clicado em gravar.
WRITE_PHASE = "gravando"


def _s() -> Any:
    from . import services

    return services


registry.register(
    RpaKind(
        code=KIND,
        module_code=ProductModule.Code.ADMISSIONS,
        label="Cadastro de empregado novo no Domínio",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=900,
        max_attempts=1,  # nunca uma segunda inclusão automática
        irreversible_phases=frozenset({WRITE_PHASE}),
        transient_claim=True,
        validate_payload=lambda p: _s().validate_payload(p),
        validate_result=lambda r: _s().validate_result(r),
        prepare_claim=lambda job: _s().prepare_claim(job),
        on_success=lambda job: _s().on_success(job),
        on_failure=lambda job: _s().on_failure(job),
        on_uncertain=lambda job: _s().on_uncertain(job),
        result_keys=frozenset({"domain_code", "checks_ok", "divergences"}),
    )
)
