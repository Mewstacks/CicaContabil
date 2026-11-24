"""T10.3: the Termo de Autorização (XMLDSig) and the token it buys, without calling the Serpro."""

from __future__ import annotations

import base64
import json
import re
import ssl
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from defusedxml import ElementTree as SafeElementTree  # type: ignore[import-untyped]
from django.core.cache import cache

from apps.integra.client import Credentials, IntegraClient
from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.termo import (
    TERMO_AVISO_LEGAL,
    TERMO_FINALIDADE,
    TERMO_TEXTO,
    TermoSigner,
    build_termo_xml,
    obter_token,
    sign_termo,
    verify_termo,
)
from apps.integra.typed.autenticaprocurador import EnviarTermo, read_token

BRT = timezone(timedelta(hours=-3))
DSIG = "http://www.w3.org/2000/09/xmldsig#"
CONTRATANTE = "11222333000181"
AUTOR = "11444777000161"


def _pfx(cnpj: str = AUTOR) -> tuple[bytes, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"ESCRITORIO TESTE:{cnpj}")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    blob = pkcs12.serialize_key_and_certificates(
        b"escritorio", key, certificate, None, serialization.BestAvailableEncryption(b"senha")
    )
    return blob, "senha"


@pytest.fixture(scope="module")
def pfx() -> tuple[bytes, str]:
    return _pfx()


def _xml(**overrides: Any) -> str:
    values: dict[str, Any] = {
        "destinatario_cnpj": CONTRATANTE,
        "destinatario_nome": "MEWSTACK LTDA",
        "autor_numero": AUTOR,
        "autor_nome": "ESCRITORIO TESTE",
        "assinado_em": date(2026, 11, 23),
        "vigencia": date(2026, 11, 24),
    }
    values.update(overrides)
    return build_termo_xml(**values)


def test_the_term_follows_the_official_layout_without_whitespace_or_hidden_characters() -> None:
    xml = _xml()

    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?><termoDeAutorizacao><dados>')
    assert "\n" not in xml and "\r" not in xml and "> <" not in xml
    root = SafeElementTree.fromstring(xml.encode())
    dados = root.find("dados")
    assert dados is not None
    assert [child.tag for child in dados] == [
        "sistema", "termo", "avisoLegal", "finalidade", "dataAssinatura", "vigencia",
        "destinatario", "assinadoPor",
    ]
    assert dados.find("sistema").attrib == {"id": "API Integra Contador"}  # type: ignore[union-attr]
    assert dados.find("termo").attrib["texto"] == TERMO_TEXTO  # type: ignore[union-attr]
    assert dados.find("avisoLegal").attrib["texto"] == TERMO_AVISO_LEGAL  # type: ignore[union-attr]
    assert dados.find("finalidade").attrib["texto"] == TERMO_FINALIDADE  # type: ignore[union-attr]
    assert dados.find("dataAssinatura").attrib == {"data": "20261123"}  # type: ignore[union-attr]
    assert dados.find("vigencia").attrib == {"data": "20261124"}  # type: ignore[union-attr]
    assert dados.find("destinatario").attrib == {  # type: ignore[union-attr]
        "numero": CONTRATANTE, "nome": "MEWSTACK LTDA", "tipo": "PJ", "papel": "contratante",
    }
    assert dados.find("assinadoPor").attrib == {  # type: ignore[union-attr]
        "numero": AUTOR, "nome": "ESCRITORIO TESTE", "tipo": "PJ", "papel": "autor pedido de dados",
    }
    for text in (TERMO_TEXTO, TERMO_AVISO_LEGAL, TERMO_FINALIDADE):
        assert text.isprintable() and "  " not in text
        assert not re.search(r"[​-‏‪-‮⁠﻿]", text)


def test_a_cpf_author_is_a_natural_person_and_bad_data_is_refused() -> None:
    xml = _xml(autor_numero="52998224725")
    assert 'numero="52998224725"' in xml and 'tipo="PF"' in xml
    for kwargs in (
        {"autor_numero": "123"},
        {"autor_numero": "11444777000162"},
        {"destinatario_cnpj": "123"},
        {"vigencia": date(2026, 11, 22)},
        {"autor_nome": ""},
        {"autor_nome": "NOME​OCULTO"},
    ):
        with pytest.raises(IntegraRequestError):
            _xml(**kwargs)


def test_special_characters_of_the_name_are_escaped() -> None:
    xml = _xml(autor_nome='A & B "C" <D>')

    root = SafeElementTree.fromstring(xml.encode())
    assert root.find("dados/assinadoPor").attrib["nome"] == 'A & B "C" <D>'  # type: ignore[union-attr]


def test_the_signature_is_enveloped_rsa_sha256_with_only_the_end_certificate(
    pfx: tuple[bytes, str],
) -> None:
    signed = sign_termo(_xml(), pfx[0], pfx[1])

    assert signed.count("<Signature ") == 1
    for uri in (
        "http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        "http://www.w3.org/2000/09/xmldsig#enveloped-signature",
        "http://www.w3.org/2001/04/xmlenc#sha256",
    ):
        assert uri in signed
    certificate = re.findall(r"<X509Certificate>([^<]+)</X509Certificate>", signed)
    assert len(certificate) == 1 and not re.search(r"\s", certificate[0])
    assert "<X509Data><X509Certificate>" in signed and "<KeyInfo>" in signed
    assert "\n" not in signed
    assert verify_termo(signed)


def test_the_signature_verifies_independently_of_the_signer(pfx: tuple[bytes, str]) -> None:
    signed = sign_termo(_xml(), pfx[0], pfx[1])

    # Digest: canonical form of the document without the Signature (enveloped transform).
    without = re.sub(r"<Signature.*</Signature>", "", signed, flags=re.S)
    canonical = ElementTree.canonicalize(without.split("?>", 1)[1], strip_text=False)
    digest = base64.b64encode(_sha256(canonical.encode())).decode()
    assert f"<DigestValue>{digest}</DigestValue>" in signed
    # Signature value: over the canonical SignedInfo, with the namespace in scope.
    info = re.search(r"<SignedInfo>.*</SignedInfo>", signed, flags=re.S)
    assert info is not None
    scoped = info.group(0).replace("<SignedInfo>", f'<SignedInfo xmlns="{DSIG}">', 1)
    canonical_info = ElementTree.canonicalize(scoped, strip_text=False)
    raw_value = re.search(r"<SignatureValue>([^<]+)</SignatureValue>", signed)
    raw_cert = re.search(r"<X509Certificate>([^<]+)</X509Certificate>", signed)
    assert raw_value is not None and raw_cert is not None
    public = x509.load_der_x509_certificate(base64.b64decode(raw_cert.group(1))).public_key()
    assert isinstance(public, rsa.RSAPublicKey)
    public.verify(
        base64.b64decode(raw_value.group(1)),
        canonical_info.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def _sha256(data: bytes) -> bytes:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    return digest.finalize()


def test_any_change_after_signing_breaks_the_signature(pfx: tuple[bytes, str]) -> None:
    signed = sign_termo(_xml(), pfx[0], pfx[1])

    assert verify_termo(signed)
    assert not verify_termo(signed.replace('data="20261124"', 'data="20301231"'))
    value = re.search(r"<SignatureValue>(.)", signed)
    assert value is not None
    flipped = "B" if value.group(1) == "A" else "A"
    tampered = signed.replace(f"<SignatureValue>{value.group(1)}", f"<SignatureValue>{flipped}", 1)
    assert not verify_termo(tampered)
    assert not verify_termo("<termoDeAutorizacao/>")


def test_a_certificate_for_another_cnpj_does_not_sign_the_term(pfx: tuple[bytes, str]) -> None:
    with pytest.raises(IntegraRequestError, match="certificado"):
        sign_termo(_xml(autor_numero="11222333000181"), pfx[0], pfx[1])
    with pytest.raises(IntegraRequestError, match="senha"):
        sign_termo(_xml(), pfx[0], "errada")


def test_the_request_carries_the_signed_xml_in_base64() -> None:
    request = EnviarTermo(xml=b"<termoDeAutorizacao/>")

    assert request.to_dados() == {"xml": base64.b64encode(b"<termoDeAutorizacao/>").decode()}


def test_the_token_answer_is_read() -> None:
    payload = {
        "status": 200,
        "dados": json.dumps(
            {
                "autenticar_procurador_token": "token-123",
                "data_hora_expiracao": "2026-11-24T00:00:00",
            }
        ),
    }

    token = read_token(payload)

    assert token.autenticar_procurador_token == "token-123"
    assert token.data_hora_expiracao == datetime(2026, 11, 24, tzinfo=BRT)
    with pytest.raises(IntegraPayloadError):
        read_token({"status": 200, "dados": "{}"})


CREDENTIALS = Credentials(
    consumer_key="key",
    consumer_secret="secret",
    certificate_path=Path("unused.pfx"),
    certificate_password="",
    contratante=CONTRATANTE,
    autor_pedido=CONTRATANTE,
    environment="trial",
)


class Gateway:
    def __init__(self, expiration: str = "2099-01-01T00:00:00") -> None:
        self.calls: list[dict[str, Any]] = []
        self.expiration = expiration

    def __call__(
        self, url: str, *, data: bytes, headers: dict[str, str], context: ssl.SSLContext | None
    ) -> tuple[int, bytes]:
        self.calls.append({"url": url, "data": data, "headers": headers})
        if url.endswith("/authenticate"):
            return 200, json.dumps(
                {"access_token": "a", "jwt_token": "j", "expires_in": 2008}
            ).encode()
        body = {
            "status": 200,
            "mensagens": [],
            "dados": json.dumps(
                {"autenticar_procurador_token": "tok", "data_hora_expiracao": self.expiration}
            ),
        }
        return 200, json.dumps(body).encode()


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


def _signer(pfx: tuple[bytes, str]) -> TermoSigner:
    return TermoSigner(
        pfx_bytes=pfx[0],
        password=pfx[1],
        autor_numero=AUTOR,
        autor_nome="ESCRITORIO TESTE",
        destinatario_cnpj=CONTRATANTE,
        destinatario_nome="MEWSTACK LTDA",
    )


def test_the_token_is_bought_once_with_the_term_and_reused_until_it_expires(
    pfx: tuple[bytes, str],
) -> None:
    gateway = Gateway()
    client = IntegraClient(CREDENTIALS, transport=gateway)
    now = datetime(2026, 11, 23, 10, 0, tzinfo=BRT)

    first = obter_token(client, _signer(pfx), now=now)
    second = obter_token(client, _signer(pfx), now=now + timedelta(hours=5))

    assert first == second == "tok"
    posts = [call for call in gateway.calls if "ENVIOXMLASSINADO81" in call["data"].decode()]
    assert len(posts) == 1
    body = json.loads(posts[0]["data"])
    assert posts[0]["url"].endswith("/Apoiar")
    assert body["autorPedidoDados"]["numero"] == AUTOR
    assert body["pedidoDados"]["versaoSistema"] == "1.0"
    signed = base64.b64decode(json.loads(body["pedidoDados"]["dados"])["xml"]).decode()
    assert verify_termo(signed)
    assert 'data="20261124"' in signed


def test_the_cached_token_dies_at_the_next_midnight_of_brasilia(pfx: tuple[bytes, str]) -> None:
    gateway = Gateway(expiration="2099-01-01T00:00:00")
    client = IntegraClient(CREDENTIALS, transport=gateway)
    now = datetime(2026, 11, 23, 23, 0, tzinfo=BRT)

    obter_token(client, _signer(pfx), now=now)
    obter_token(client, _signer(pfx), now=now + timedelta(minutes=30))
    assert len([c for c in gateway.calls if b"ENVIOXMLASSINADO81" in c["data"]]) == 1
    # After midnight the term must be signed again, even if the gateway said the token lives on.
    obter_token(client, _signer(pfx), now=now + timedelta(hours=2))
    assert len([c for c in gateway.calls if b"ENVIOXMLASSINADO81" in c["data"]]) == 2


def test_the_client_sends_the_authenticated_token_header_only_when_given() -> None:
    gateway = Gateway()
    client = IntegraClient(CREDENTIALS, transport=gateway)

    client.call("dte.situacao", contribuinte=AUTOR)
    client.call("dte.situacao", contribuinte=AUTOR, autenticar_procurador_token="tok")

    consult = [c for c in gateway.calls if c["url"].endswith("/Consultar")]
    assert "autenticar_procurador_token" not in consult[0]["headers"]
    assert consult[1]["headers"]["autenticar_procurador_token"] == "tok"
