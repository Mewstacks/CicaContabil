from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from apps.integra.catalog import ServiceSpec

CPF_LENGTH = 11
CNPJ_LENGTH = 14
_DIGITS = re.compile(r"\D+")


class PersonType:
    """The `tipo` discriminator Integra Contador expects alongside every `numero`."""

    CPF = 1
    CNPJ = 2


@dataclass(frozen=True)
class Party:
    """One of contratante / autorPedidoDados / contribuinte."""

    numero: str

    @property
    def digits(self) -> str:
        return _DIGITS.sub("", self.numero)

    @property
    def tipo(self) -> int:
        if len(self.digits) == CPF_LENGTH:
            return PersonType.CPF
        if len(self.digits) == CNPJ_LENGTH:
            return PersonType.CNPJ
        raise ValueError(f"{self.numero!r} não é um CPF nem um CNPJ.")

    def as_payload(self) -> dict[str, Any]:
        return {"numero": self.digits, "tipo": self.tipo}


def build(
    *,
    spec: ServiceSpec,
    contratante: Party,
    autor_pedido: Party,
    contribuinte: Party,
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
