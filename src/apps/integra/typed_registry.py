"""Every typed service (request model and reader) of the Integra Contador registry.

Kept outside `typed/__init__.py` on purpose: `parcelamento` imports `typed.base`, so a package
`__init__` that imported `parcelamento` would be circular.
"""

from __future__ import annotations

from apps.integra import parcelamento
from apps.integra.typed import (
    ccmei,
    defis,
    eprocesso,
    eventosatualizacao,
    mit,
    pagtoweb,
    pgdasd,
    pnrcontador,
    regimeapuracao,
    sicalc,
)
from apps.integra.typed.registry import TypedService

# Reads that already had their own reading code in the hub before E10 (not typed yet).
LEGACY_UNTYPED_READS = frozenset(
    {
        "procuracao.obter",
        "dte.situacao",
        "caixapostal.indicador",
        "caixapostal.mensagens",
        "dctfweb.xml",
        "dctfweb.recibo",
        "dctfweb.declaracao_completa",
        "pgmei.divida",
        "sitfis.protocolo",
    }
)


def _collect() -> dict[str, TypedService]:
    registry: dict[str, TypedService] = {}
    for module in (
        pgdasd, eventosatualizacao, pagtoweb, mit, defis, regimeapuracao, ccmei, sicalc,
        pnrcontador, eprocesso, parcelamento,
    ):
        for typed in module.TYPED_SERVICES:
            if typed.key in registry:
                raise ValueError(f"Serviço tipado repetido: {typed.key}.")
            registry[typed.key] = typed
    return registry


TYPED: dict[str, TypedService] = _collect()
