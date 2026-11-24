"""AUTENTICAPROCURADOR/ENVIOXMLASSINADO81: send the signed Termo de Autorização, get a token.

Source: .../solucoes/integra-contador-gerenciador/autenticaprocurador/servicos/
envio_de_xml_assinado/. A support service (class G): it is not in the typed registry of reads.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope


@dataclass(frozen=True, kw_only=True)
class EnviarTermo(Request):
    """`dados`: the signed XML of the term, in base64."""

    xml: Annotated[bytes, J("xml", fmt=Fmt.XML)]


@dataclass(frozen=True, kw_only=True)
class TokenProcurador(Model):
    autenticar_procurador_token: Annotated[str, J("autenticar_procurador_token")]
    data_hora_expiracao: Annotated[
        datetime | None, J("data_hora_expiracao", fmt=Fmt.ISO_DATETIME)
    ] = None


def read_token(payload: Mapping[str, Any]) -> TokenProcurador:
    return TokenProcurador.parse(open_envelope(payload).dados)
