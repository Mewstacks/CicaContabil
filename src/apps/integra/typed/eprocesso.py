"""EPROCESSO: processes of the taxpayer (service 271, consulta por interessado).

Source: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-e-processo/eprocesso/ (servicos/consultar_processos, exemplos/retorno_consultar_processos,
changelog). The other services of the system (272, 273, 274) are not read here.

Decisions that are not obvious:

* The service takes no `dados` ("Envie \"\""), so there is no request model.
* The answer is NOT paginated ("O retorno não tem paginação. A lista traz todos os processos"):
  `dados` is a plain list ordered from the newest protocol to the oldest. A taxpayer without
  processes gets `[]` with the message Sucesso-EPROCESSO-SC_002.
* The page documents `status` as String(3) and the example shows `"200"`. The engine requires a
  number, so a three-digit text status is converted here before the engine opens the answer.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any

from apps.integra.typed.base import Fmt, J, Model, open_envelope
from apps.integra.typed.registry import TypedService


@dataclass(frozen=True, kw_only=True)
class Processo(Model):
    numero_do_processo: Annotated[str, J("numeroDoProcesso")]
    relacao_do_interessado_com_o_processo: Annotated[
        str | None, J("relacaoDoInteressadoComOProcesso")
    ] = None
    data_de_protocolo: Annotated[date | None, J("dataDeProtocolo", fmt=Fmt.BR_DATE)] = None
    tipo_do_processo: Annotated[str | None, J("tipoDoProcesso")] = None
    subtipo_do_processo: Annotated[str | None, J("subtipoDoProcesso")] = None
    localizacao: Annotated[str | None, J("localizacao")] = None
    situacao: Annotated[str | None, J("situacao")] = None
    ultimo_encaminhamento_externo: Annotated[str | None, J("ultimoEncaminhamentoExterno")] = None


def _numeric_status(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    status = payload.get("status")
    if isinstance(status, str) and re.fullmatch(r"\d{3}", status):
        return {**payload, "status": int(status)}
    return payload


def read_processos(payload: Mapping[str, Any]) -> tuple[Processo, ...]:
    """CONSPROCPORINTER271: all the processes of the taxpayer; no process is an empty tuple."""

    return Processo.parse_many(open_envelope(_numeric_status(payload)).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("eprocesso.processos", None, read_processos),
)
