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
from defusedxml import ElementTree  # type: ignore[import-untyped]
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import Certificate, NfseDocument, NfseDocumentSide, NfseSync
from apps.hub.nfse_adn import AdnClient, AdnDocument, AdnPayloadError
from apps.hub.nfse_facts import (
    FACT_FIELDS,
    FACTS_VERSION,
    apply_facts,
    nfse_facts,
    refresh_situations,
)
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


_PROVIDER_GROUPS = {
    "emit",
    "emitente",
    "prest",
    "prestador",
    "prestadorservico",
    "infprestador",
}
_RECIPIENT_GROUPS = {"toma", "tomador", "tomadorservico", "inftomador", "dest"}


def _party_identifier(root: Any, group_names: set[str]) -> str:
    for group in root.iter():
        if not isinstance(group.tag, str):
            continue
        if group.tag.rsplit("}", 1)[-1].casefold() not in group_names:
            continue
        for element in group.iter():
            if not isinstance(element.tag, str):
                continue
            if element.tag.rsplit("}", 1)[-1].casefold() not in {"cnpj", "cpf", "nif"}:
                continue
            identifier = re.sub(r"\D", "", element.text or "")
            if len(identifier) in {11, 14}:
                return identifier
    return ""


def _party_name(root: Any, group_names: set[str]) -> str:
    for group in root.iter():
        if not isinstance(group.tag, str):
            continue
        if group.tag.rsplit("}", 1)[-1].casefold() not in group_names:
            continue
        for element in group.iter():
            if not isinstance(element.tag, str):
                continue
            if element.tag.rsplit("}", 1)[-1].casefold() not in {
                "xnome",
                "razaosocial",
                "nome",
            }:
                continue
            name = " ".join((element.text or "").split())
            if name:
                return name[:160]
    return ""


def nfse_service_direction(xml: str, *, company_cnpj: str) -> str:
    """Return a fiscal direction only when the XML roles identify it unambiguously."""

    company_identifier = normalize_cnpj(company_cnpj)
    if len(company_identifier) != 14:
        return "unknown"
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return "unknown"
    provider = _party_identifier(root, _PROVIDER_GROUPS)
    recipient = _party_identifier(root, _RECIPIENT_GROUPS)
    provider_matches = provider == company_identifier
    recipient_matches = recipient == company_identifier
    if provider_matches and not recipient_matches:
        return "provided"
    if recipient_matches and not provider_matches:
        return "taken"
    return "unknown"


def nfse_match_data(document: NfseDocument) -> dict[str, Any]:
    """Classification keys of a stored note, completed from its XML when they are missing.

    Notes captured before the direction existed kept only the first CNPJ of the XML as the
    counterparty, which on a serviço prestado is the company itself. The stored normalization
    is immutable evidence, so the side and the real counterparty are derived here instead.
    """

    data = dict(document.normalized_data) if isinstance(document.normalized_data, dict) else {}
    if data.get("direction") in {"provided", "taken"}:
        return data
    try:
        company_identifier = normalize_cnpj(document.company.cnpj_masked)
        root = ElementTree.fromstring(document.original_xml)
    except (ValidationError, ElementTree.ParseError, ValueError, TypeError):
        return data
    provider = _party_identifier(root, _PROVIDER_GROUPS)
    recipient = _party_identifier(root, _RECIPIENT_GROUPS)
    if not provider and not recipient:
        return data
    root_identifier = company_identifier[:8]
    provider_name = _party_name(root, _PROVIDER_GROUPS)
    recipient_name = _party_name(root, _RECIPIENT_GROUPS)
    if provider == company_identifier and recipient != company_identifier:
        direction, counterparty, name = "provided", recipient, recipient_name
    elif recipient == company_identifier and provider != company_identifier:
        direction, counterparty, name = "taken", provider, provider_name
    # A branch (same CNPJ root) reaches the company through the same A1 certificate.
    elif provider[:8] == root_identifier and recipient[:8] != root_identifier:
        direction, counterparty, name = "provided", recipient, recipient_name
    elif recipient[:8] == root_identifier and provider[:8] != root_identifier:
        direction, counterparty, name = "taken", provider, provider_name
    else:
        direction, counterparty, name = "unknown", "", ""
    data["direction"] = direction
    if name and not data.get("counterparty_name"):
        data["counterparty_name"] = name
    # Without a side, the legacy "first CNPJ" may be the company itself: never match on it.
    data["counterparty_ref"] = (
        hashlib.sha256(counterparty.encode()).hexdigest()[:24] if counterparty else ""
    )
    return data


def _decimal_field(values: dict[str, list[str]], *names: str) -> str:
    raw = _first(values, *names)
    if not raw:
        return ""
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return ""
    exponent = value.as_tuple().exponent
    if value < 0 or not isinstance(exponent, int) or exponent < -2:
        return ""
    return format(value, ".2f")


def _explicit_retentions(values: dict[str, list[str]]) -> dict[str, str]:
    """Keep only retained amounts explicitly present in the source XML."""

    iss_retained = _first(values, "tpRetISSQN") == "2"
    federal_retained = _first(values, "tpRetPisCofins") in {"1", "3"}
    retentions = {
        "iss": _decimal_field(
            values,
            "vISSQNRetido",
            "vISSRet",
            "vRetISS",
            *("vISSQN",) if iss_retained else (),
        ),
        "pis": _decimal_field(
            values, "vRetPIS", "vRetPis", *("vPis",) if federal_retained else ()
        ),
        "cofins": _decimal_field(
            values, "vRetCOFINS", "vRetCofins", *("vCofins",) if federal_retained else ()
        ),
        "csll": _decimal_field(values, "vRetCSLL", "vRetCsll"),
        "irrf": _decimal_field(values, "vRetIRRF"),
        "inss": _decimal_field(values, "vRetCP", "vRetINSS"),
    }
    return {name: value for name, value in retentions.items() if Decimal(value or "0") > 0}


def normalize_adn_document(document: AdnDocument, *, company_cnpj: str = "") -> dict[str, Any]:
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
        exponent = parsed_amount.as_tuple().exponent
        if parsed_amount < 0 or not isinstance(exponent, int) or exponent < -2:
            raise AdnPayloadError(f"O XML do NSU {document.nsu} traz valor inválido.")
        amount = format(parsed_amount, ".2f")

    generated = _first(values, "dhProc") or document.generated_at or _first(
        values, "dhEmi", "dCompet"
    )
    parsed_datetime = parse_datetime(generated) if generated else None
    direction = nfse_service_direction(document.xml, company_cnpj=company_cnpj)
    provider_identifier = _party_identifier(root, _PROVIDER_GROUPS)
    recipient_identifier = _party_identifier(root, _RECIPIENT_GROUPS)
    provider_name = _party_name(root, _PROVIDER_GROUPS)
    recipient_name = _party_name(root, _RECIPIENT_GROUPS)
    counterparty_identifier = (
        recipient_identifier
        if direction == "provided"
        else provider_identifier
        if direction == "taken"
        else ""
    )
    retentions = _explicit_retentions(values)
    retained_total = sum((Decimal(value) for value in retentions.values()), Decimal("0"))
    return {
        "source": "adn",
        "nsu": str(document.nsu),
        "access_key": document.access_key or _first(values, "chNFSe", "Id")[:80],
        "document_type": document.document_type or root.tag.rsplit("}", 1)[-1],
        "number": _first(values, "nNFSe", "nDPS")[:40],
        "service_code": _first(values, "cTribNac", "cTribMun", "cServ")[:40],
        "service_description": _first(values, "xDescServ", "xTribNac")[:500],
        "counterparty_ref": (
            hashlib.sha256(counterparty_identifier.encode()).hexdigest()[:24]
            if counterparty_identifier
            else _counterparty(values)
        ),
        "counterparty_name": (
            recipient_name
            if direction == "provided"
            else provider_name
            if direction == "taken"
            else ""
        ),
        "direction": direction,
        "amount": amount,
        "accumulator_code": _first(values, "acum")[:80],
        "competence": _first(values, "dCompet")[:40],
        "retentions": retentions,
        "retained_total": format(retained_total, ".2f") if retentions else "",
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


def _side_for(document: NfseDocument, side: NfseDocumentSide | None = None) -> NfseDocumentSide:
    """Side and fiscal facts of one stored document, read from its immutable XML."""

    data = nfse_match_data(document)
    direction = str(data.get("direction") or "unknown")
    side = side or NfseDocumentSide(document=document, organization_id=document.organization_id)
    side.direction = direction if direction in {"provided", "taken"} else "unknown"
    side.counterparty_ref = str(data.get("counterparty_ref") or "")[:80]
    side.counterparty_name = str(data.get("counterparty_name") or "")[:160]
    apply_facts(
        side,
        nfse_facts(
            document.original_xml,
            company_cnpj=document.company.cnpj_masked,
            fallback=document.normalized_data if isinstance(document.normalized_data, dict) else {},
        ),
    )
    if side.kind == "event":
        side.direction = "unknown"
    return side


def sync_nfse_side(document: NfseDocument) -> NfseDocumentSide:
    """Persist the side of one note so filters and counters can query it in SQL."""

    existing = NfseDocumentSide.objects.filter(document=document).first()
    side = _side_for(document, existing)
    side.save()
    refresh_situations(document.organization_id, {side.access_key})
    return side


FACTS_PAGE_SIZE = 200


def refresh_nfse_facts(*, limit: int = 5000, organization_id: Any = None) -> dict[str, int]:
    """Read the facts of documents whose side is missing or older than ``FACTS_VERSION``.

    Paged by primary key because production runs behind PgBouncer without server-side
    cursors, and bounded per call so the 512 MB worker never holds the whole archive.
    """

    documents = NfseDocument.objects.filter(
        Q(side__isnull=True) | Q(side__facts_version__lt=FACTS_VERSION)
    )
    if organization_id is not None:
        documents = documents.filter(organization_id=organization_id)
    pending = list(documents.order_by("pk").values_list("pk", flat=True)[:limit])
    updated = 0
    touched: dict[object, set[str]] = {}
    for start in range(0, len(pending), FACTS_PAGE_SIZE):
        batch = list(
            NfseDocument.objects.filter(pk__in=pending[start : start + FACTS_PAGE_SIZE])
            .select_related("company", "side")
        )
        creates: list[NfseDocumentSide] = []
        updates: list[NfseDocumentSide] = []
        for document in batch:
            try:
                existing = document.side
            except NfseDocumentSide.DoesNotExist:
                existing = None
            side = _side_for(document, existing)
            (updates if existing is not None else creates).append(side)
            touched.setdefault(document.organization_id, set()).add(side.access_key)
        with transaction.atomic():
            NfseDocumentSide.objects.bulk_create(creates, ignore_conflicts=True)
            NfseDocumentSide.objects.bulk_update(
                updates,
                ["direction", "counterparty_ref", "counterparty_name", "event_situation",
                 "facts_version", *FACT_FIELDS],
            )
        updated += len(batch)
    for organization, keys in touched.items():
        refresh_situations(organization, keys)
    return {"updated": updated, "remaining": max(documents.count(), 0)}


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
                    normalized_data=normalize_adn_document(
                        document, company_cnpj=locked.company.cnpj_masked
                    ),
                    source_nsu=str(document.nsu),
                )
                if existing is None and same_hash is None and saved.document_hash == digest:
                    created_in_page += 1
            now = timezone.now()
            locked.checkpoint_nsu = str(page.last_nsu)
            locked.max_nsu = str(page.max_nsu)
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
                    "max_nsu",
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
        sync.max_nsu = str(page.max_nsu)
        if caught_up:
            break
    return {"state": "completed", "pages": pages, "documents_created": total_created}
