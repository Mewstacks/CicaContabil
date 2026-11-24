from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from apps.integra.catalog import ServiceSpec

_SEPARATORS = re.compile(r"[./\-\s]+")


class PersonType:
    """The `tipo` discriminator Integra Contador expects alongside every `numero`."""

    CPF = 1
    CNPJ = 2


@dataclass(frozen=True)
class Party:
    """One of contratante / autorPedidoDados / contribuinte."""

    numero: str

    @property
    def normalized(self) -> str:
        return _SEPARATORS.sub("", self.numero).upper()

    @property
    def tipo(self) -> int:
        if re.fullmatch(r"[0-9]{11}", self.normalized):
            return PersonType.CPF
        if re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", self.normalized):
            return PersonType.CNPJ
        raise ValueError(f"{self.numero!r} não é um CPF nem um CNPJ.")

    def as_payload(self) -> dict[str, Any]:
        return {"numero": self.normalized, "tipo": self.tipo}


@dataclass(frozen=True)
class BatchParty:
    """The `contribuinte` of the batch services (EVENTOSATUALIZACAO): a list of CPFs (tipo 3) or
    of CNPJs (tipo 4) in `numero`, separated by comma, up to 1000. The retrieval of a request
    sends it empty."""

    numeros: tuple[str, ...]
    tipo: int = 4

    MAX_ITEMS = 1000

    def as_payload(self) -> dict[str, Any]:
        if self.tipo not in (3, 4):
            raise ValueError("O lote é de CPFs (tipo 3) ou de CNPJs (tipo 4).")
        if len(self.numeros) > self.MAX_ITEMS:
            raise ValueError("O lote aceita até 1.000 inscrições.")
        size = 11 if self.tipo == 3 else 14
        numbers = [_SEPARATORS.sub("", item).upper() for item in self.numeros]
        if any(not re.fullmatch(rf"[A-Z0-9]{{{size}}}", item) for item in numbers):
            raise ValueError("Inscrição fora do formato do lote.")
        return {"numero": ",".join(numbers), "tipo": self.tipo}


def build(
    *,
    spec: ServiceSpec,
    contratante: Party,
    autor_pedido: Party,
    contribuinte: Party | BatchParty,
    dados: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """The single request shape every Integra Contador service accepts.

    `dados` travels as a JSON *string* inside the envelope, not as a nested object.
    """

    if dados is None:
        payload = ""
    elif isinstance(dados, str):
        payload = dados
    else:
        payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    return {
        "contratante": contratante.as_payload(),
        "autorPedidoDados": autor_pedido.as_payload(),
        "contribuinte": contribuinte.as_payload(),
        "pedidoDados": {
            "idSistema": spec.id_sistema,
            "idServico": spec.id_servico,
            "versaoSistema": spec.versao_sistema,
            "dados": payload,
        },
    }
