"""Bounded, read-only client for the official NFS-e ADN contributor distribution API."""

from __future__ import annotations

import base64
import binascii
import gzip
import io
import json
import ssl
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError

PRODUCTION_BASE_URL = "https://adn.nfse.gov.br/contribuintes"
TRIAL_BASE_URL = "https://adn.producaorestrita.nfse.gov.br/contribuintes"
MAX_RESPONSE_BYTES = 12_000_000
MAX_DOCUMENT_BYTES = 4_000_000
TIMEOUT_SECONDS = 45


class AdnError(RuntimeError):
    code = "adn_error"
    transient = False


class AdnTransportError(AdnError):
    code = "transport"
    transient = True


class AdnAuthenticationError(AdnError):
    code = "certificate_rejected"


class AdnPayloadError(AdnError):
    code = "provider_payload"


@dataclass(frozen=True)
class AdnDocument:
    nsu: int
    xml: str
    access_key: str = ""
    document_type: str = ""
    generated_at: str = ""


@dataclass(frozen=True)
class AdnPage:
    status: str
    documents: tuple[AdnDocument, ...]
    last_nsu: int
    max_nsu: int
    processed_at: str = ""


class Transport(Protocol):
    def __call__(
        self, url: str, *, headers: dict[str, str], context: ssl.SSLContext
    ) -> tuple[int, bytes]: ...


def _urlopen_transport(
    url: str, *, headers: dict[str, str], context: ssl.SSLContext
) -> tuple[int, bytes]:
    request = Request(url, method="GET")  # noqa: S310 - caller pins an official base URL
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:  # noqa: S310
            return int(response.status), response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        return int(exc.code), exc.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, URLError) as exc:
        raise AdnTransportError(
            "O ADN NFS-e não respondeu. Uma nova tentativa será agendada."
        ) from exc


class AdnClient:
    def __init__(
        self,
        *,
        environment: str,
        ssl_context: ssl.SSLContext,
        transport: Transport | None = None,
    ) -> None:
        if environment not in {"trial", "production"}:
            raise ValueError("NFSE_ADN_ENVIRONMENT deve ser 'trial' ou 'production'.")
        self.base_url = TRIAL_BASE_URL if environment == "trial" else PRODUCTION_BASE_URL
        self.ssl_context = ssl_context
        self.transport = transport or _urlopen_transport

    def fetch_page(self, *, last_nsu: int, cnpj: str) -> AdnPage:
        if last_nsu < 0:
            raise ValueError("O NSU não pode ser negativo.")
        digits = "".join(character for character in cnpj if character.isdigit())
        if len(digits) != 14:
            raise ValidationError("A empresa precisa de um CNPJ válido para consultar o ADN.")
        query = urlencode({"lote": "true", "cnpjConsulta": digits})
        url = f"{self.base_url}/DFe/{last_nsu}?{query}"
        status, raw = self.transport(
            url,
            headers={"Accept": "application/json", "User-Agent": "CICA-NFSe/1.0"},
            context=self.ssl_context,
        )
        if len(raw) > MAX_RESPONSE_BYTES:
            raise AdnPayloadError("O ADN devolveu um lote maior que o limite de segurança.")
        if status in {401, 403}:
            raise AdnAuthenticationError(
                "O ADN recusou o certificado para este CNPJ. Confira titularidade e validade."
            )
        if status == 429 or status >= 500:
            raise AdnTransportError(f"O ADN está temporariamente indisponível (HTTP {status}).")
        if status >= 400:
            raise AdnError(f"O ADN recusou a consulta (HTTP {status}).")
        return parse_page(raw, requested_nsu=last_nsu)


def parse_page(raw: bytes, *, requested_nsu: int) -> AdnPage:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdnPayloadError("O ADN devolveu uma resposta ilegível.") from exc
    if not isinstance(payload, dict):
        raise AdnPayloadError("O ADN devolveu um formato de resposta inesperado.")
    status = _text(payload, "StatusProcessamento", "statusProcessamento", "status")
    rows = _value(payload, "LoteDFe", "loteDFe", "documentos", default=[])
    if rows is None:
        rows = []
    if not isinstance(rows, list) or len(rows) > 50:
        raise AdnPayloadError("O lote ADN excedeu o contrato de 50 documentos.")
    documents: list[AdnDocument] = []
    previous = requested_nsu
    for row in rows:
        if not isinstance(row, dict):
            raise AdnPayloadError("O lote ADN contém um documento inválido.")
        nsu = _integer(row, "NSU", "nsu")
        if nsu <= previous:
            raise AdnPayloadError("O ADN devolveu NSUs fora de ordem ou repetidos.")
        previous = nsu
        encoded = _text(row, "ArquivoXml", "arquivoXml", "XML", "xml")
        if not encoded:
            raise AdnPayloadError(f"O documento NSU {nsu} não trouxe XML.")
        documents.append(
            AdnDocument(
                nsu=nsu,
                xml=decode_xml(encoded),
                access_key=_text(row, "ChaveAcesso", "chaveAcesso")[:80],
                document_type=_text(row, "TipoDocumento", "tipoDocumento")[:80],
                generated_at=_text(row, "DataHoraGeracao", "dataHoraGeracao")[:40],
            )
        )
    last_nsu = _optional_integer(payload, "UltimoNSU", "ultimoNSU", "ultNSU", "ultimoNsu")
    if last_nsu is None:
        last_nsu = documents[-1].nsu if documents else requested_nsu
    max_nsu = _optional_integer(payload, "MaxNSU", "maxNSU", "maxNsu")
    if max_nsu is None:
        max_nsu = last_nsu
    if last_nsu < requested_nsu or (documents and last_nsu < documents[-1].nsu):
        raise AdnPayloadError("O checkpoint devolvido pelo ADN retrocedeu.")
    if max_nsu < last_nsu:
        raise AdnPayloadError("O maior NSU devolvido pelo ADN é inconsistente.")
    return AdnPage(
        status=status,
        documents=tuple(documents),
        last_nsu=last_nsu,
        max_nsu=max_nsu,
        processed_at=_text(payload, "DataHoraProcessamento", "dataHoraProcessamento")[:40],
    )


def decode_xml(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("<"):
        raw = stripped.encode("utf-8")
    else:
        try:
            raw = base64.b64decode(stripped, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise AdnPayloadError("O ADN devolveu um XML codificado de forma inválida.") from exc
    if raw.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_DOCUMENT_BYTES + 1)
        except (OSError, EOFError) as exc:
            raise AdnPayloadError("O ADN devolveu um XML compactado inválido.") from exc
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise AdnPayloadError("Um XML do ADN excedeu o limite de segurança.")
    try:
        xml = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AdnPayloadError("O XML do ADN não está em UTF-8.") from exc
    if not xml.lstrip().startswith("<") or "<!DOCTYPE" in xml.upper():
        raise AdnPayloadError("O documento devolvido pelo ADN não é um XML fiscal seguro.")
    return xml


def _value(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return default


def _text(payload: dict[str, Any], *keys: str) -> str:
    value = _value(payload, *keys, default="")
    return value if isinstance(value, str) else str(value) if value is not None else ""


def _integer(payload: dict[str, Any], *keys: str) -> int:
    value = _optional_integer(payload, *keys)
    if value is None:
        raise AdnPayloadError("O documento ADN não informou um NSU válido.")
    return value


def _optional_integer(payload: dict[str, Any], *keys: str) -> int | None:
    value = _value(payload, *keys)
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
