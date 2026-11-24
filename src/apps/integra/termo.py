"""Termo de Autorização: the XMLDSig document that buys the `autenticar_procurador_token`.

When the author of the request (the office) is not the contractor of the Integra Contador (the
platform), Serpro asks for a term signed with the e-CNPJ of the author. The standard is
.../autenticaprocurador/padroes_tecnicos_assinatura_xml/: enveloped XMLDSig, RSA-SHA256,
inclusive C14N 1.0, only the end certificate in `X509Data`, no indentation, no hidden Unicode.

The document is written already in canonical form (sorted attributes, no self-closing tags), so
the bytes that are hashed and signed are exactly the bytes a verifier canonicalizes. The token
lives until midnight (Brasília) of the day after the term, and is cached until then.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from xml.etree.ElementTree import ParseError, canonicalize

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12
from defusedxml import ElementTree as SafeElementTree  # type: ignore[import-untyped]
from django.core.cache import cache
from django.core.exceptions import ValidationError

from apps.common.cnpj import normalize_cnpj
from apps.integra.client import IntegraClient
from apps.integra.errors import IntegraRequestError
from apps.integra.typed.autenticaprocurador import EnviarTermo, read_token
from apps.integra.typed.base import BRASILIA, normalize_cpf

TERMO_TEXTO = (
    "Autorizo a empresa CONTRATANTE, identificada neste termo de autorização como DESTINATÁRIO, "
    "a executar as requisições dos serviços web disponibilizados pela API INTEGRA CONTADOR, onde "
    "terei o papel de AUTOR PEDIDO DE DADOS no corpo da mensagem enviada na requisição do serviço "
    "web. Esse termo de autorização está assinado digitalmente com o certificado digital do "
    "PROCURADOR ou OUTORGADO DO CONTRIBUINTE responsável, identificado como AUTOR DO PEDIDO DE "
    "DADOS."
)
TERMO_AVISO_LEGAL = (
    "O acesso a estas informações foi autorizado pelo próprio PROCURADOR ou OUTORGADO DO "
    "CONTRIBUINTE, responsável pela informação, via assinatura digital. É dever do destinatário "
    "da autorização e consumidor deste acesso observar a adoção de base legal para o tratamento "
    "dos dados recebidos conforme artigos 7º ou 11º da LGPD (Lei n.º 13.709, de 14 de agosto de "
    "2018), aos direitos do titular dos dados (art. 9º, 17 e 18, da LGPD) e aos princípios que "
    "norteiam todos os tratamentos de dados no Brasil (art. 6º, da LGPD)."
)
TERMO_FINALIDADE = (
    "A finalidade única e exclusiva desse TERMO DE AUTORIZAÇÃO, é garantir que o CONTRATANTE "
    "apresente a API INTEGRA CONTADOR esse consentimento do PROCURADOR ou OUTORGADO DO "
    "CONTRIBUINTE assinado digitalmente, para que possa realizar as requisições dos serviços web "
    "da API INTEGRA CONTADOR em nome do AUTOR PEDIDO DE DADOS (PROCURADOR ou OUTORGADO DO "
    "CONTRIBUINTE)."
)

DSIG = "http://www.w3.org/2000/09/xmldsig#"
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"
DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
TOKEN_SAFETY_SECONDS = 60
_TOKEN_CACHE_PREFIX = "integra:termo-token"  # noqa: S105 - cache namespace, not a credential


def _attr(value: str) -> str:
    """Attribute value in canonical form (C14N 1.0)."""

    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace('"', "&quot;")
        .replace("\t", "&#x9;")
        .replace("\n", "&#xA;")
        .replace("\r", "&#xD;")
    )


def _clean(value: str, label: str) -> str:
    text = unicodedata.normalize("NFC", value).strip()
    if not text or any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in text):
        raise IntegraRequestError(f"{label} do termo está vazio ou tem caractere oculto.")
    return text


def _party(number: str, label: str) -> tuple[str, str]:
    digits = re.sub(r"[.\-/\s]", "", number)
    try:
        if re.fullmatch(r"\d{11}", digits):
            return normalize_cpf(digits), "PF"
        return normalize_cnpj(number), "PJ"
    except ValidationError:
        raise IntegraRequestError(f"Confira o número de {label} do termo.") from None


def build_termo_xml(
    *,
    destinatario_cnpj: str,
    destinatario_nome: str,
    autor_numero: str,
    autor_nome: str,
    assinado_em: date,
    vigencia: date,
) -> str:
    """The unsigned term, in canonical form."""

    if vigencia < assinado_em:
        raise IntegraRequestError("A vigência do termo não pode ser anterior à assinatura.")
    destinatario, destinatario_tipo = _party(destinatario_cnpj, "destinatário")
    if destinatario_tipo != "PJ":
        raise IntegraRequestError("O destinatário do termo é o CNPJ do contratante.")
    autor, autor_tipo = _party(autor_numero, "autor do pedido")
    nome_destinatario = _clean(destinatario_nome, "O nome do destinatário")
    nome_autor = _clean(autor_nome, "O nome do autor")
    dados = (
        "<dados>"
        '<sistema id="API Integra Contador"></sistema>'
        f'<termo texto="{_attr(TERMO_TEXTO)}"></termo>'
        f'<avisoLegal texto="{_attr(TERMO_AVISO_LEGAL)}"></avisoLegal>'
        f'<finalidade texto="{_attr(TERMO_FINALIDADE)}"></finalidade>'
        f'<dataAssinatura data="{assinado_em:%Y%m%d}"></dataAssinatura>'
        f'<vigencia data="{vigencia:%Y%m%d}"></vigencia>'
        f'<destinatario nome="{_attr(nome_destinatario)}" numero="{destinatario}" '
        'papel="contratante" tipo="PJ"></destinatario>'
        f'<assinadoPor nome="{_attr(nome_autor)}" numero="{autor}" '
        f'papel="autor pedido de dados" tipo="{autor_tipo}"></assinadoPor>'
        "</dados>"
    )
    return f"{DECLARATION}<termoDeAutorizacao>{dados}</termoDeAutorizacao>"


def _digest(data: bytes) -> bytes:
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(data)
    return hasher.finalize()


def _signed_info(digest_b64: str) -> str:
    return (
        f'<SignedInfo><CanonicalizationMethod Algorithm="{C14N}"></CanonicalizationMethod>'
        f'<SignatureMethod Algorithm="{RSA_SHA256}"></SignatureMethod>'
        '<Reference URI=""><Transforms>'
        f'<Transform Algorithm="{ENVELOPED}"></Transform>'
        f'<Transform Algorithm="{C14N}"></Transform></Transforms>'
        f'<DigestMethod Algorithm="{SHA256}"></DigestMethod>'
        f"<DigestValue>{digest_b64}</DigestValue></Reference></SignedInfo>"
    )


def _in_dsig_scope(signed_info: str) -> str:
    return signed_info.replace("<SignedInfo>", f'<SignedInfo xmlns="{DSIG}">', 1)


def _certificate_numbers(certificate: x509.Certificate) -> set[str]:
    subject = certificate.subject.rfc4514_string()
    return {
        token.upper()
        for token in re.findall(r"[A-Za-z0-9]{11,14}", subject.split(":")[-1])
        if len(token) in (11, 14)
    }


def sign_termo(xml: str, pfx_bytes: bytes, password: str) -> str:
    """Sign the term with the e-CNPJ or e-CPF of the author (enveloped XMLDSig, RSA-SHA256)."""

    try:
        key, certificate, _chain = pkcs12.load_key_and_certificates(
            pfx_bytes, password.encode() or None
        )
    except (TypeError, ValueError, UnsupportedAlgorithm):
        raise IntegraRequestError("Não foi possível abrir o certificado com esta senha.") from None
    if not isinstance(key, rsa.RSAPrivateKey) or certificate is None:
        raise IntegraRequestError("O certificado precisa ter chave RSA e certificado.")
    match = re.search(r'<assinadoPor [^>]*numero="([^"]+)"', xml)
    if match is None or match.group(1) not in _certificate_numbers(certificate):
        raise IntegraRequestError("O certificado não é do autor do pedido informado no termo.")
    body = xml.removeprefix(DECLARATION)
    digest = base64.b64encode(_digest(body.encode("utf-8"))).decode("ascii")
    info = _signed_info(digest)
    value = key.sign(_in_dsig_scope(info).encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    der = base64.b64encode(certificate.public_bytes(Encoding.DER)).decode("ascii")
    signature = (
        f'<Signature xmlns="{DSIG}">{info}'
        f"<SignatureValue>{base64.b64encode(value).decode('ascii')}</SignatureValue>"
        f"<KeyInfo><X509Data><X509Certificate>{der}</X509Certificate></X509Data></KeyInfo>"
        "</Signature>"
    )
    opened = body.removesuffix("</termoDeAutorizacao>")
    return f"{DECLARATION}{opened}{signature}</termoDeAutorizacao>"


def verify_termo(signed: str) -> bool:
    """Check digest and signature of a signed term the way a verifier would (C14N first)."""

    try:
        SafeElementTree.fromstring(signed.encode("utf-8"), forbid_dtd=True)
        parts = re.fullmatch(
            r"(?:<\?xml[^>]*\?>)?(<termoDeAutorizacao>.*?)"
            r"(<Signature xmlns=\"[^\"]+\">.*</Signature>)(</termoDeAutorizacao>)",
            signed,
            flags=re.S,
        )
        info = re.search(r"<SignedInfo>.*</SignedInfo>", signed, flags=re.S)
        value = re.search(r"<SignatureValue>([^<]+)</SignatureValue>", signed)
        der = re.search(r"<X509Certificate>([^<]+)</X509Certificate>", signed)
        digest = re.search(r"<DigestValue>([^<]+)</DigestValue>", signed)
        if not (parts and info and value and der and digest):
            return False
        document = canonicalize(parts.group(1) + parts.group(3), strip_text=False)
        if base64.b64encode(_digest(document.encode("utf-8"))).decode("ascii") != digest.group(1):
            return False
        canonical_info = canonicalize(_in_dsig_scope(info.group(0)), strip_text=False)
        public = x509.load_der_x509_certificate(base64.b64decode(der.group(1))).public_key()
        if not isinstance(public, rsa.RSAPublicKey):
            return False
        public.verify(
            base64.b64decode(value.group(1)),
            canonical_info.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (InvalidSignature, ParseError, ValueError, binascii.Error):
        return False
    return True


@dataclass(frozen=True)
class TermoSigner:
    """Everything needed to sign a fresh term each day; the secrets stay out of the repr."""

    pfx_bytes: bytes = field(repr=False)
    password: str = field(repr=False)
    autor_numero: str
    autor_nome: str
    destinatario_cnpj: str
    destinatario_nome: str

    def signed_xml(self, today: date) -> bytes:
        xml = build_termo_xml(
            destinatario_cnpj=self.destinatario_cnpj,
            destinatario_nome=self.destinatario_nome,
            autor_numero=self.autor_numero,
            autor_nome=self.autor_nome,
            assinado_em=today,
            vigencia=today + timedelta(days=1),
        )
        return sign_termo(xml, self.pfx_bytes, self.password).encode("utf-8")


def _next_midnight(now: datetime) -> datetime:
    local = now.astimezone(BRASILIA)
    return (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def obter_token(client: IntegraClient, signer: TermoSigner, *, now: datetime | None = None) -> str:
    """The `autenticar_procurador_token` of the author, bought once per day and cached."""

    moment = (now or datetime.now(BRASILIA)).astimezone(BRASILIA)
    identity = "\x00".join(
        (client.credentials.environment, client.credentials.contratante, signer.autor_numero)
    )
    cache_key = f"{_TOKEN_CACHE_PREFIX}:{hashlib.sha256(identity.encode()).hexdigest()}"
    cached: Any = cache.get(cache_key)
    if isinstance(cached, dict) and datetime.fromisoformat(cached["expires"]) > moment:
        return str(cached["token"])
    payload = client.call(
        "autenticaprocurador.termo",
        contribuinte=signer.autor_numero,
        autor_pedido=signer.autor_numero,
        dados=EnviarTermo(xml=signer.signed_xml(moment.date())).to_dados(),
    )
    token = read_token(payload)
    expires = _next_midnight(moment)
    if token.data_hora_expiracao is not None:
        expires = min(expires, token.data_hora_expiracao)
    ttl = int((expires - moment).total_seconds()) - TOKEN_SAFETY_SECONDS
    if ttl > 0:
        cache.set(
            cache_key,
            {"token": token.autenticar_procurador_token, "expires": expires.isoformat()},
            ttl,
        )
    return token.autenticar_procurador_token
