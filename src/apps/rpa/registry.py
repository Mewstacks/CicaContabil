"""Catálogo de tipos de trabalho RPA.

Cada bloco (folha, FGTS, DET, FAP, admissões) registra os seus tipos em ``AppConfig.ready``.
O registro diz quem pode pedir o trabalho (``module_code``), se ele disputa o desktop da máquina
do agente (``exclusive_group``), quanto vale a reserva, quais fases não admitem repetição
(``irreversible_phases``) e como validar carga e resultado. O que o agente não conhece ou o
escritório não contratou nunca é entregue.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Validator = Callable[[dict[str, Any]], None]
Hook = Callable[..., None]


class RpaError(Exception):
    """Erro de regra do framework; ``code`` é estável para o chamador e o agente."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


@dataclass(frozen=True)
class RpaKind:
    code: str
    module_code: str
    label: str
    #: Trabalhos do mesmo grupo não rodam juntos no mesmo escritório (uma só sessão do desktop).
    exclusive_group: str = ""
    lease_seconds: int = 300
    max_attempts: int = 3
    #: Fases (informadas pelo agente no heartbeat) depois das quais repetir pode duplicar efeito.
    irreversible_phases: frozenset[str] = frozenset()
    validate_payload: Validator | None = None
    validate_result: Validator | None = None
    #: Chamados dentro da transação que fecha o trabalho: ``(job)``.
    on_success: Hook | None = None
    on_failure: Hook | None = None
    on_uncertain: Hook | None = None
    #: Chamado ao reservar: ``(job) -> dict`` mescla valores *voláteis* (flags, travas) na carga
    #: no instante da entrega, não do enfileiramento. Se levantar ``RpaError``, o trabalho é
    #: encerrado como ``bloqueado_por_trava`` e nunca chega ao agente.
    prepare_claim: Callable[..., dict[str, Any]] | None = None
    #: A carga mesclada no ``prepare_claim`` só viaja na resposta ao agente: nunca é gravada no
    #: trabalho (usado quando ela carrega dado pessoal, como a ficha de uma admissão).
    transient_claim: bool = False
    #: Chaves de ``result`` aceitas; o resto é descartado (nada de dado inesperado na nuvem).
    result_keys: frozenset[str] = field(default_factory=frozenset)


_KINDS: dict[str, RpaKind] = {}


def register(kind: RpaKind) -> RpaKind:
    existing = _KINDS.get(kind.code)
    if existing is not None and existing != kind:
        raise RuntimeError(f"Tipo RPA duplicado: {kind.code}")
    _KINDS[kind.code] = kind
    return kind


def get(code: str) -> RpaKind:
    try:
        return _KINDS[code]
    except KeyError:
        raise RpaError("kind_desconhecido", f"Tipo de trabalho desconhecido: {code}") from None


def known_codes() -> frozenset[str]:
    return frozenset(_KINDS)


def kinds() -> list[RpaKind]:
    return list(_KINDS.values())
