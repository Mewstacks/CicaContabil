"""Durable ADN synchronization with per-company checkpoints and atomic pages."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import ssl
import tempfile
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    pkcs12,
)
from defusedxml import ElementTree
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import Certificate, NfseDocument, NfseSync
from apps.hub.nfse_adn import AdnClient, AdnDocument, AdnPayloadError
from apps.hub.services import create_document_and_artifact


def certificate_ssl_context(certificate: Certificate) -> ssl.SSLContext:
    if certificate.revoked_at is not None:
        raise ValidationError("O certificado selecionado foi revogado.")
    now = timezone.now()
    if certificate.valid_from and certificate.valid_from > now:
        raise ValidationError("O certificado selecionado ainda não é válido.")
    if certificate.valid_until and certificate.valid_until <= now:
        raise ValidationError("O certificado selecionado está vencido.")
    try:
        blob = base64.b64decode(certificate.pfx_blob, validate=True)
        key, parsed, chain = pkcs12.load_key_and_certificates(
            blob, certificate.password.encode() or None
        )
    except (ValueError, TypeError) as exc:
        raise ValidationError("Não foi possível abrir o certificado armazenado.") from exc
    if key is None or parsed is None:
        raise ValidationError("O certificado armazenado não contém chave privada.")
    _validate_certificate_company(parsed, certificate)
    passphrase = base64.urlsafe_b64encode(os.urandom(24))
    pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(passphrase)
    ) + parsed.public_bytes(Encoding.PEM)
    for issuer in chain or []:
        pem += issuer.public_bytes(Encoding.PEM)
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    handle, filename = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(pem)
        context.load_cert_chain(filename, password=passphrase)
    finally:
        os.unlink(filename)
    return context


def _validate_certificate_company(parsed: x509.Certificate, stored: Certificate) -> None:
    company_cnpj = normalize_cnpj(stored.company.cnpj_masked)
    candidates: set[str] = set()
    for attribute in parsed.subject:
        raw_value = str(attribute.value)
        digits = re.sub(r"\D", "", raw_value)
        if len(digits) == 14:
            candidates.add(digits)
        elif len(digits) > 14:
            candidates.update(re.findall(r"(?<!\d)\d{14}(?!\d)", raw_value))
    if not candidates:
        raise ValidationError(
            "O A1 não informa um CNPJ verificável. Use um e-CNPJ ICP-Brasil "
            "da empresa ou da mesma raiz."
        )
    if not any(candidate[:8] == company_cnpj[:8] for candidate in candidates):
        raise ValidationError("O CNPJ raiz do certificado não corresponde ao da empresa.")


def normalize_adn_document(document: AdnDocument) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(document.xml)
    except ElementTree.ParseError as exc:
        raise AdnPayloadError(f"O XML do NSU {document.nsu} está malformado.") from exc
    values: dict[str, list[str]] = {}
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        text = (element.text or "").strip()
        if text:
            values.setdefault(local_name, []).append(text)

    amount = _first(values, "vLiq", "vServPrest", "vServ", "vBC")
    if amount:
        try:
            parsed_amount = Decimal(amount)
        except InvalidOperation as exc:
            raise AdnPayloadError(f"O XML do NSU {document.nsu} traz valor inválido.") from exc
        if parsed_amount < 0 or parsed_amount.as_tuple().exponent < -2:
            raise AdnPayloadError(f"O XML do NSU {document.nsu} traz valor inválido.")
        amount = format(parsed_amount, ".2f")

    generated = document.generated_at or _first(values, "dhEmi", "dhProc", "dCompet")
    parsed_datetime = parse_datetime(generated) if generated else None
    return {
        "source": "adn",
        "nsu": str(document.nsu),
        "access_key": document.access_key or _first(values, "chNFSe", "Id")[:80],
        "document_type": document.document_type or root.tag.rsplit("}", 1)[-1],
        "number": _first(values, "nNFSe", "nDPS")[:40],
        "service_code": _first(values, "cTribNac", "cTribMun", "cServ")[:40],
        "service_description": _first(values, "xDescServ", "xTribNac")[:500],
        "counterparty_ref": _counterparty(values),
        "amount": amount,
        "issued_at": parsed_datetime.isoformat() if parsed_datetime else generated[:40],
    }


def _first(values: dict[str, list[str]], *names: str) -> str:
    for name in names:
        items = values.get(name)
        if items:
            return items[0]
    return ""


def _counterparty(values: dict[str, list[str]]) -> str:
    for name in ("CNPJ", "CPF", "NIF"):
        for value in values.get(name, []):
            digits = re.sub(r"\D", "", value)
            if len(digits) in {11, 14}:
                return hashlib.sha256(digits.encode()).hexdigest()[:24]
    return ""


def process_sync_pages(
    *, sync: NfseSync, client: AdnClient, max_pages: int = 10
) -> dict[str, int | str]:
    if max_pages < 1 or max_pages > 20:
        raise ValueError("max_pages fora do limite operacional.")
    total_created = 0
    pages = 0
    for _ in range(max_pages):
        requested_nsu = int(sync.checkpoint_nsu or "0")
        cnpj = normalize_cnpj(sync.company.cnpj_masked)
        page = client.fetch_page(last_nsu=requested_nsu, cnpj=cnpj)
        with transaction.atomic():
            locked = NfseSync.objects.select_for_update().select_related("company").get(pk=sync.pk)
            if int(locked.checkpoint_nsu or "0") != requested_nsu:
                raise AdnPayloadError("O checkpoint mudou durante a sincronização.")
            created_in_page = 0
            for document in page.documents:
                digest = hashlib.sha256(document.xml.encode()).hexdigest()
                existing = NfseDocument.objects.filter(
                    organization=locked.organization,
                    company=locked.company,
                    source_nsu=str(document.nsu),
                ).first()
                if existing is not None and existing.document_hash != digest:
                    raise AdnPayloadError(
                        f"O NSU {document.nsu} reapareceu com conteúdo diferente."
                    )
                same_hash = NfseDocument.objects.filter(
                    organization=locked.organization,
                    company=locked.company,
                    document_hash=digest,
                ).first()
                if same_hash is not None and same_hash.source_nsu != str(document.nsu):
                    raise AdnPayloadError(
                        "O ADN associou o mesmo documento a dois NSUs diferentes."
                    )
                saved, _artifact, _review = create_document_and_artifact(
                    company=locked.company,
                    original_xml=document.xml,
                    normalized_data=normalize_adn_document(document),
                    source_nsu=str(document.nsu),
                )
                if existing is None and same_hash is None and saved.document_hash == digest:
                    created_in_page += 1
            now = timezone.now()
            locked.checkpoint_nsu = str(page.last_nsu)
            locked.last_batch_count = len(page.documents)
            locked.last_run_at = now
            locked.last_success_at = now
            locked.last_error_code = ""
            locked.last_error_message = ""
            locked.last_error_at = None
            locked.failure_count = 0
            caught_up = page.last_nsu >= page.max_nsu or not page.documents
            locked.next_run_at = now + timedelta(hours=1) if caught_up else now
            locked.status = NfseSync.Status.IDLE
            locked.save(
                update_fields=[
                    "checkpoint_nsu",
                    "last_batch_count",
                    "last_run_at",
                    "last_success_at",
                    "last_error_code",
                    "last_error_message",
                    "last_error_at",
                    "failure_count",
                    "next_run_at",
                    "status",
                    "updated_at",
                ]
            )
        pages += 1
        total_created += created_in_page
        sync.checkpoint_nsu = str(page.last_nsu)
        if caught_up:
            break
    return {"state": "completed", "pages": pages, "documents_created": total_created}
