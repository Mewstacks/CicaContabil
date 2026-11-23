"""The closed registry of Integra Contador services.

A caller names a service by key, never an endpoint or a payload of its own. That keeps the
adapter free of any injection surface, and the same reasoning applies to a paid API where a
forged request costs the office money. The registry holds the 99 services in production of the
official catalog (15/10/2026); the data lives in `catalog_table` and every rule below is derived
from it and checked by `tests/test_integra_catalog_registry.py` against the official page and
against the allowlist and blocklist of docs/pesquisa/serpro-integra-contador-mcp.md (appendix A).
"""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

from apps.integra.catalog_table import (
    ROWS,
    EffectClass,
    ResponseFormat,
    Row,
    Verb,
    parcelamento_rows,
)

__all__ = [
    "SERVICES",
    "EffectClass",
    "ResponseFormat",
    "ServiceSpec",
    "Verb",
    "copilot_services",
    "service",
    "service_by_ids",
    "services_by_effect",
]

# Serpro does not bill anything sent to /Apoiar or /Monitorar; 200, 202 and 403 on the other
# three paths are billed (research report, section 1.6).
_UNBILLED_VERBS = frozenset({Verb.APOIAR, Verb.MONITORAR})

# The copilot and the external MCP may call a service by themselves only when it is a pure
# reading (class A, the 68 services of the allowlist) or the one document the report releases:
# the SITFIS report, which the cross-check "debts x paid guides" needs. The other three
# read-only documents (payment proof, CCMEI, renunciation proof) stay off until the owner
# decides; everything else needs a human to confirm each call.
_COPILOT_DOCUMENTS = frozenset({("SITFIS", "RELATORIOSITFIS92")})

_VERB_EFFECTS: dict[Verb, frozenset[EffectClass]] = {
    Verb.CONSULTAR: frozenset({EffectClass.READ, EffectClass.READ_LEGAL}),
    Verb.MONITORAR: frozenset({EffectClass.READ}),
    Verb.APOIAR: frozenset({EffectClass.READ, EffectClass.SUPPORT}),
    Verb.EMITIR: frozenset({EffectClass.DOCUMENT, EffectClass.GUIDE, EffectClass.WRITE}),
    Verb.DECLARAR: frozenset({EffectClass.DECLARE}),
}


@dataclass(frozen=True)
class ServiceSpec:
    key: str
    id_sistema: str
    id_servico: str
    versao_sistema: str
    verb: Verb
    label: str
    billable: bool
    _: KW_ONLY
    effect_class: EffectClass
    response_format: ResponseFormat
    # May the copilot or an external MCP client call it without a human in the loop?
    copilot_allowed: bool
    # Must a human confirm each call (legal effect, emission, declaration, token)?
    needs_confirmation: bool
    # Relative path of the service page in the official documentation.
    doc_page: str
    # False when neither the page nor its examples state the versaoSistema.
    versao_confirmada: bool = True

    def __post_init__(self) -> None:
        if self.effect_class not in _VERB_EFFECTS[self.verb]:
            raise ValueError(f"{self.key}: classe {self.effect_class} não combina com {self.verb}.")
        if self.billable is (self.verb in _UNBILLED_VERBS):
            raise ValueError(f"{self.key}: faturamento contradiz o verbo {self.verb}.")
        if self.needs_confirmation is self.copilot_allowed:
            raise ValueError(f"{self.key}: confirmação humana e uso livre do copiloto divergem.")
        if self.copilot_allowed and self.effect_class not in {
            EffectClass.READ,
            EffectClass.DOCUMENT,
        }:
            raise ValueError(f"{self.key}: o copiloto só chama leitura e documento.")
        identifiers = (self.id_sistema, self.id_servico)
        if not self.versao_sistema or not all(value.isupper() for value in identifiers):
            raise ValueError(f"{self.key}: identificadores do Serpro inválidos.")

    @property
    def versao(self) -> str:
        """The `versaoSistema` sent in `pedidoDados` (alias of `versao_sistema`)."""

        return self.versao_sistema


def _spec(row: Row) -> ServiceSpec:
    copilot = row.effect is EffectClass.READ or (row.id_sistema, row.id_servico) in (
        _COPILOT_DOCUMENTS
    )
    return ServiceSpec(
        key=row.key,
        id_sistema=row.id_sistema,
        id_servico=row.id_servico,
        versao_sistema=row.versao,
        verb=row.verb,
        label=row.label,
        billable=row.verb not in _UNBILLED_VERBS,
        effect_class=row.effect,
        response_format=row.fmt,
        copilot_allowed=copilot,
        needs_confirmation=not copilot,
        doc_page=row.page,
        versao_confirmada=row.confirmada,
    )


def _build() -> dict[str, ServiceSpec]:
    registry: dict[str, ServiceSpec] = {}
    seen: set[tuple[str, str]] = set()
    for row in (*ROWS, *parcelamento_rows()):
        spec = _spec(row)
        ids = (spec.id_sistema, spec.id_servico)
        if spec.key in registry or ids in seen:
            raise ValueError(f"Serviço repetido no registro: {spec.key} {ids}.")
        registry[spec.key] = spec
        seen.add(ids)
    return registry


SERVICES: dict[str, ServiceSpec] = _build()
_BY_IDS: dict[tuple[str, str], ServiceSpec] = {
    (spec.id_sistema, spec.id_servico): spec for spec in SERVICES.values()
}


def service(key: str) -> ServiceSpec:
    try:
        return SERVICES[key]
    except KeyError as exc:
        raise ValueError(f"Serviço {key!r} não está no catálogo.") from exc


def service_by_ids(id_sistema: str, id_servico: str) -> ServiceSpec:
    """Resolve an official (idSistema, idServico) pair; anything else is refused."""

    try:
        return _BY_IDS[(id_sistema, id_servico)]
    except KeyError as exc:
        raise ValueError(
            f"Serviço {id_sistema}/{id_servico} não está no catálogo do Integra Contador."
        ) from exc


def services_by_effect(effect_class: EffectClass) -> tuple[ServiceSpec, ...]:
    return tuple(spec for spec in SERVICES.values() if spec.effect_class is effect_class)


def copilot_services() -> tuple[ServiceSpec, ...]:
    """The services a copilot or an external MCP client may call without a human."""

    return tuple(spec for spec in SERVICES.values() if spec.copilot_allowed)
