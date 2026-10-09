from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import tempfile
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, NameOID, ObjectIdentifier
from defusedxml import ElementTree  # type: ignore[import-untyped]
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.models import (
    AccumulatorCatalogEntry,
    AccumulatorObservation,
    AccumulatorRule,
    Certificate,
    ClientCompany,
    Connector,
    ConsumptionConfirmation,
    DctfWebDocument,
    DteRun,
    DteRunItem,
    FiscalGuide,
    IntegrationArtifact,
    NfseDocument,
    NfseExport,
    NfseSync,
    ParcelamentoOperation,
    ProductModule,
    ReviewCase,
)
from apps.hub.module_activities import sync_nfse_review_activity
from apps.platform.billing import BillingError, UsageQuote, quote_usage, reserve_usage
from apps.platform.token_billing import TokenQuote, quote_tokens, reserve_tokens


@dataclass(frozen=True)
class ClassificationResult:
    accumulator_code: str
    confidence: int
    rule_name: str
    evidence: dict[str, object]
    needs_review: bool


@dataclass(frozen=True)
class FiscalGuideSyncResult:
    created: int
    updated: int
    ignored: int


@dataclass(frozen=True)
class CertificateImportResult:
    status: str
    title: str
    detail: str
    company_name: str = ""
    reason: str = ""


def _matches(rule: AccumulatorRule, data: dict[str, Any]) -> bool:
    # An empty rule is a catalog entry for human review, never a catch-all classifier.
    return bool(rule.match) and all(
        str(data.get(key, "")) == str(expected) for key, expected in rule.match.items()
    )


_LC116_ITEM = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.\d+)?$")
NFSE_DIRECTIONS = frozenset(
    {AccumulatorObservation.Direction.TAKEN, AccumulatorObservation.Direction.PROVIDED}
)


@lru_cache(maxsize=65536)
def _normalized_service_code(text: str) -> str:
    item = _LC116_ITEM.fullmatch(text)
    if item:
        return f"{int(item.group(1)):02d}{int(item.group(2)):02d}"
    if len(text) == 6 and text.isdigit():
        return text[:4]
    return text


def normalize_service_code(value: object) -> str:
    """Reduce both sides of the match to the LC 116 item + subitem (``1701``).

    The national NFS-e carries ``cTribNac`` with six digits (item, subitem, desdobramento:
    ``170101``) while Domínio configures accumulators by the LC 116 list item (``17.01``).
    Comparing the raw strings made those two never meet, so only the counterparty was left
    to decide and most notes fell into review.
    """

    return _normalized_service_code(str(value or "").strip())


def active_catalog_codes(companies: Sequence[ClientCompany]) -> dict[Any, frozenset[str]]:
    """Active accumulators of each company's latest Domínio snapshot, plus manual ones.

    Companies without any backup catalog are absent from the result: there is no evidence
    to validate against, so callers keep their previous behaviour for them.
    """

    latest: dict[Any, Any] = {}
    codes: dict[Any, set[str]] = {}
    for company_id, snapshot_at, code, active in (
        AccumulatorCatalogEntry.objects.filter(company__in=companies)
        .order_by("company_id", "-source_snapshot_at")
        .values_list("company_id", "source_snapshot_at", "accumulator_code", "active")
        .iterator(chunk_size=2000)
    ):
        if latest.setdefault(company_id, snapshot_at) != snapshot_at:
            continue
        bucket = codes.setdefault(company_id, set())
        if active:
            bucket.add(code)
    # An accumulator the office registered by hand (created in Domínio after the backup) is as
    # valid as the backup catalog; only companies that have a catalog are validated at all.
    for company_id, code in AccumulatorRule.objects.filter(
        company_id__in=list(codes), active=True
    ).values_list("company_id", "accumulator_code"):
        codes[company_id].add(code)
    return {company_id: frozenset(values) for company_id, values in codes.items()}


def classify_nfse(document: NfseDocument, *, on_date: date | None = None) -> ClassificationResult:
    """Deterministic, explainable classification. It never decides a tax treatment by AI."""

    from apps.hub.nfse_sync import nfse_match_data

    return classify_nfse_from_candidates(
        document,
        rules=list(document.company.accumulator_rules.filter(active=True).order_by("priority")),
        observations=list(
            AccumulatorObservation.objects.filter(
                organization=document.organization,
                company=document.company,
            )
        ),
        catalog_codes=active_catalog_codes([document.company]).get(document.company_id),
        match_data=nfse_match_data(document),
        on_date=on_date,
    )


def classify_nfse_from_candidates(
    document: NfseDocument,
    *,
    rules: Sequence[AccumulatorRule],
    observations: Sequence[AccumulatorObservation],
    catalog_codes: frozenset[str] | None = None,
    match_data: dict[str, Any] | None = None,
    on_date: date | None = None,
) -> ClassificationResult:
    """Classify with already-scoped candidates so portfolio replays do not issue N+1 queries.

    ``catalog_codes`` is the company's active Domínio catalog; when present, no accumulator
    outside it can be chosen, because Domínio rejects it as "Acumulador não definido".
    ``match_data`` replaces the stored normalization when the caller derived missing keys.
    """

    def allowed(code: str) -> bool:
        return catalog_codes is None or code in catalog_codes

    data = match_data if match_data is not None else document.normalized_data
    current_day = on_date or timezone.localdate()
    for rule in rules:
        if not rule.active or not allowed(rule.accumulator_code):
            continue
        if rule.valid_from and rule.valid_from > current_day:
            continue
        if rule.valid_until and rule.valid_until < current_day:
            continue
        if _matches(rule, data):
            return ClassificationResult(
                accumulator_code=rule.accumulator_code,
                confidence=95 if not rule.is_transitory else 70,
                rule_name=rule.name,
                evidence={"source": "configured_rule", "transitory": rule.is_transitory},
                needs_review=rule.is_transitory,
            )

    # Entrada and serviço prestado use different accumulators in Domínio: history recorded for
    # the other side never competes, and a note whose side could not be read from the XML is
    # not decided by history that has a side. Rows without a side are legacy evidence.
    direction = str(data.get("direction", ""))
    known_direction = direction in NFSE_DIRECTIONS
    service_code = normalize_service_code(data.get("service_code", ""))
    counterparty_ref = str(data.get("counterparty_ref", ""))
    scored: list[tuple[int, AccumulatorObservation]] = []
    for candidate in observations:
        if not allowed(candidate.accumulator_code):
            continue
        if candidate.direction and known_direction and candidate.direction != direction:
            continue
        service_hit = bool(service_code) and (
            normalize_service_code(candidate.service_code) == service_code
        )
        counterparty_hit = bool(counterparty_ref) and candidate.counterparty_ref == counterparty_ref
        if not service_hit and not counterparty_hit:
            continue
        score = min(candidate.frequency, 20)
        if service_hit:
            score += 45
        if counterparty_hit:
            score += 45
        age_days = (timezone.now() - candidate.last_used_at).days
        score += max(0, 20 - min(max(age_days, 0) // 30, 20))
        scored.append((score, candidate))
    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        score, winner = scored[0]
        runner_up = next(
            (
                candidate_score
                for candidate_score, candidate in scored[1:]
                if candidate.accumulator_code != winner.accumulator_code
            ),
            None,
        )
        ambiguous = runner_up is not None and runner_up >= score - 5
        # The counterparty is the strongest signal the office has: when every past note of this
        # supplier/client went to one accumulator, a low frequency or an old date does not make
        # it uncertain. When it points somewhere else than the winner, the evidence conflicts.
        counterparty_codes = {
            candidate.accumulator_code
            for _score, candidate in scored
            if counterparty_ref and candidate.counterparty_ref == counterparty_ref
        }
        conflict = bool(counterparty_codes) and winner.accumulator_code not in counterparty_codes
        unanimous = counterparty_codes == {winner.accumulator_code}
        sideless_note = not known_direction and any(c.direction for _s, c in scored)
        return ClassificationResult(
            accumulator_code=winner.accumulator_code,
            confidence=min(max(score, 80 if unanimous else 0), 90),
            rule_name="histórico Domínio",
            evidence={
                "source": "dominio_history",
                "frequency": winner.frequency,
                "score": score,
                "ambiguous": ambiguous,
                "conflict": conflict,
                "unanimous_counterparty": unanimous,
                "direction": winner.direction,
                "unknown_note_direction": sideless_note,
            },
            needs_review=ambiguous
            or conflict
            or sideless_note
            or (score < 70 and not unanimous),
        )
    return ClassificationResult("", 0, "sem correspondência", {"source": "none"}, True)


def record_human_observation(
    *, document: NfseDocument, accumulator_code: str, observed_at: datetime
) -> AccumulatorObservation:
    """Teach the classifier one human decision under the note's own match key.

    The key must carry service, counterparty and direction: keyed by accumulator alone, the
    first decision fixed the evidence forever and a backup with several rows for the same
    accumulator made ``get_or_create`` fail.
    """

    from apps.hub.nfse_sync import nfse_match_data

    data = nfse_match_data(document)
    direction = str(data.get("direction", ""))
    lookup = {
        "organization": document.organization,
        "company": document.company,
        "accumulator_code": accumulator_code,
        "service_code": str(data.get("service_code", ""))[:60],
        "counterparty_ref": str(data.get("counterparty_ref", ""))[:80],
        "direction": direction if direction in NFSE_DIRECTIONS else "",
    }
    observation = AccumulatorObservation.objects.filter(**lookup).order_by("pk").first()
    if observation is None:
        return AccumulatorObservation.objects.create(**lookup, last_used_at=observed_at)
    observation.frequency = F("frequency") + 1
    observation.last_used_at = observed_at
    observation.save(update_fields=["frequency", "last_used_at", "updated_at"])
    return observation


@transaction.atomic
def create_document_and_artifact(
    *,
    company: ClientCompany,
    original_xml: str,
    normalized_data: dict[str, Any],
    source_nsu: str = "",
    actor: Any = None,
    request: Any = None,
) -> tuple[NfseDocument, IntegrationArtifact | None, ReviewCase | None]:
    digest = hashlib.sha256(original_xml.encode()).hexdigest()
    issued_at = _issued_at_from_normalized_data(normalized_data)
    document, created = NfseDocument.objects.get_or_create(
        organization=company.organization,
        company=company,
        document_hash=digest,
        defaults={
            "source_nsu": source_nsu,
            "original_xml": original_xml,
            "normalized_data": normalized_data,
            "issued_at": issued_at,
        },
    )
    if created:
        from apps.hub.nfse_sync import sync_nfse_side

        sync_nfse_side(document)
    if not created:
        existing_review = ReviewCase.objects.filter(document=document).first()
        if existing_review is not None:
            sync_nfse_review_activity(existing_review.pk)
        return document, None, None
    result = classify_nfse(document)
    review_case = None
    artifact = None
    if result.needs_review:
        review_case = ReviewCase.objects.create(
            organization=company.organization,
            document=document,
            reason="Baixa confiança ou regra transitória",
            suggested_accumulator=result.accumulator_code,
            confidence=result.confidence,
        )
        sync_nfse_review_activity(review_case.pk)
    elif result.accumulator_code:
        artifact = IntegrationArtifact.objects.create(
            organization=company.organization,
            document=document,
            accumulator_code=result.accumulator_code,
            applied_rule=result.rule_name,
            confidence=result.confidence,
            evidence=result.evidence,
            payload={
                "contract": "hub-nfse-v1",
                "original_hash": digest,
                "accumulator": result.accumulator_code,
            },
        )
    record_event(
        action="hub.nfse.document_captured",
        actor=actor,
        organization=company.organization,
        target=document,
        request=request,
        metadata={"source": "adn", "has_review": bool(review_case)},
    )
    return document, artifact, review_case


def _issued_at_from_normalized_data(normalized_data: dict[str, Any]) -> datetime | None:
    """Keep the fiscal issuance date parsed from the NFS-e payload, never capture time."""

    raw_issued_at = normalized_data.get("issued_at")
    if not isinstance(raw_issued_at, str) or not raw_issued_at.strip():
        return None
    parsed_datetime = parse_datetime(raw_issued_at)
    if parsed_datetime is not None:
        if timezone.is_aware(parsed_datetime):
            return parsed_datetime
        return timezone.make_aware(parsed_datetime)
    parsed_date = parse_date(raw_issued_at)
    if parsed_date is None:
        return None
    return timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))


ICP_BRASIL_CNPJ_OID = ObjectIdentifier("2.16.76.1.3.3")


def _decode_der_text(value: bytes) -> str:
    """Decode the simple string encodings permitted for ICP-Brasil otherName fields."""

    if len(value) < 2:
        return ""
    tag = value[0]
    first_length = value[1]
    offset = 2
    if first_length & 0x80:
        length_octets = first_length & 0x7F
        if not 1 <= length_octets <= 4 or len(value) < offset + length_octets:
            return ""
        length = int.from_bytes(value[offset : offset + length_octets], "big")
        offset += length_octets
    else:
        length = first_length
    if length != len(value) - offset:
        return ""
    payload = value[offset:]
    encoding = "ascii" if tag in {0x04, 0x13, 0x16} else "utf-8" if tag == 0x0C else ""
    if not encoding:
        return ""
    try:
        return payload.decode(encoding)
    except UnicodeDecodeError:
        return ""


def certificate_cnpjs(parsed_certificate: x509.Certificate) -> set[str]:
    """Return valid CNPJs, preferring the official ICP-Brasil SAN otherName."""

    candidates: set[str] = set()
    try:
        alternative_names = parsed_certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
    except x509.ExtensionNotFound:
        alternative_names = None
    if isinstance(alternative_names, x509.SubjectAlternativeName):
        for other_name in alternative_names.get_values_for_type(x509.OtherName):
            if other_name.type_id == ICP_BRASIL_CNPJ_OID:
                value = _decode_der_text(other_name.value)
                digits = re.sub(r"\D", "", value)
                if len(digits) == 14:
                    candidates.add(digits)

    if not candidates:
        for attribute in parsed_certificate.subject:
            raw_value = str(attribute.value)
            digits = re.sub(r"\D", "", raw_value)
            if len(digits) == 14:
                candidates.add(digits)
            else:
                candidates.update(re.findall(r"(?<!\d)\d{14}(?!\d)", raw_value))

    valid: set[str] = set()
    for candidate in candidates:
        try:
            valid.add(normalize_cnpj(candidate))
        except ValidationError:
            continue
    return valid


def infer_certificate_passwords(filename: str, common_password: str = "") -> tuple[str | None, ...]:
    """Build a small local candidate set without logging or returning the filename."""

    stem = filename.rsplit(".", 1)[0]
    inferred: list[str | None] = []
    if common_password:
        inferred.append(common_password)
    marker = re.search(r"(?:^|[\s_-])(?:senha|password|pwd)\s*[=-]\s*(.{1,256})$", stem, re.I)
    if marker:
        inferred.append(marker.group(1).strip())
    if "__" in stem:
        inferred.append(stem.rsplit("__", 1)[1].strip())
    bracketed = re.search(r"\[([^\[\]]{1,256})\]\s*$", stem)
    if bracketed:
        inferred.append(bracketed.group(1).strip())
    # Common accounting-office convention: ``Empresa - SENHA.pfx``.  The
    # separator is deliberately strict so words in a normal company name are
    # not treated as credentials.
    dashed = re.search(r"\s+-\s+(.{1,256})$", stem)
    if dashed:
        inferred.append(dashed.group(1).strip())
    elif not marker and "__" not in stem and not bracketed and (
        trailing := re.search(r"\s+(\S*\d\S*)$", stem)
    ):
        # Covers established names such as ``Bianchi 1234.pfx`` while only
        # attempting a final token that contains a digit.
        inferred.append(trailing.group(1).strip())
    inferred.append(None)
    return tuple(
        dict.fromkeys(candidate for candidate in inferred if candidate is None or candidate)
    )


def _certificate_label(parsed_certificate: x509.Certificate) -> str:
    common_names = parsed_certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if common_names:
        return str(common_names[0].value)[:120]
    return "Certificado A1"


def import_certificate_upload(
    *,
    filename: str,
    pfx_bytes: bytes,
    common_password: str,
    companies: list[ClientCompany],
    actor: Any = None,
    request: Any = None,
) -> CertificateImportResult:
    """Recognize, correlate and store one A1 without retaining failed material."""

    if len(pfx_bytes) > 2_000_000:
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "O arquivo ultrapassa o limite de 2 MB.",
            reason="too_large",
        )
    if not filename.lower().endswith((".pfx", ".p12")):
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "Use um arquivo .pfx ou .p12.",
            reason="wrong_type",
        )

    parsed_key: object | None = None
    parsed_certificate: x509.Certificate | None = None
    selected_password = ""
    for candidate in infer_certificate_passwords(filename, common_password):
        try:
            parsed_key, parsed_certificate, _ = pkcs12.load_key_and_certificates(
                pfx_bytes, candidate.encode() if candidate is not None else None
            )
        except (TypeError, ValueError, UnsupportedAlgorithm):
            continue
        if parsed_key is not None and parsed_certificate is not None:
            selected_password = candidate or ""
            break
    if parsed_key is None or parsed_certificate is None:
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "Não foi possível abrir o A1. Confira a senha e tente selecionar o arquivo novamente.",
            reason="open_failed",
        )

    cnpjs = certificate_cnpjs(parsed_certificate)
    if len(cnpjs) != 1:
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "O certificado não informa um único CNPJ válido da ICP-Brasil.",
            reason="invalid_cnpj",
        )
    certificate_cnpj = next(iter(cnpjs))
    matches: list[ClientCompany] = []
    for company in companies:
        try:
            if normalize_cnpj(company.cnpj_masked) == certificate_cnpj:
                matches.append(company)
        except ValidationError:
            continue
    if len(matches) != 1:
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "O CNPJ do certificado não corresponde a uma empresa acessível deste escritório.",
            reason="unmatched_cnpj",
        )

    fingerprint = hashlib.sha256(pfx_bytes).hexdigest()
    company = matches[0]
    if Certificate.objects.filter(
        organization=company.organization, fingerprint_sha256=fingerprint
    ).exists():
        return CertificateImportResult(
            "unrecognized",
            "Não reconhecido",
            "Este certificado já está cadastrado no escritório.",
            company.name,
            "duplicate",
        )
    store_certificate(
        company=company,
        pfx_bytes=pfx_bytes,
        password=selected_password,
        label=_certificate_label(parsed_certificate),
        actor=actor,
        request=request,
    )
    return CertificateImportResult(
        "recognized",
        "Vinculado automaticamente",
        "CNPJ identificado nos metadados do certificado.",
        company.name,
        "imported",
    )


@transaction.atomic
def store_certificate(
    *,
    company: ClientCompany,
    pfx_bytes: bytes,
    password: str,
    label: str,
    actor: Any = None,
    request: Any = None,
) -> Certificate:
    """Stores PFX once, encrypted; no view/form exposes its source bytes after upload."""
    try:
        parsed_key, parsed_certificate, _ = pkcs12.load_key_and_certificates(
            pfx_bytes, password.encode() or None
        )
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError("Não foi possível abrir o A1/PFX com esta senha.") from exc
    if parsed_key is None or parsed_certificate is None:
        raise ValueError("O arquivo não contém um certificado A1 com chave privada.")
    fingerprint = hashlib.sha256(pfx_bytes).hexdigest()
    valid_from = parsed_certificate.not_valid_before_utc
    valid_until = parsed_certificate.not_valid_after_utc
    certificate = Certificate.objects.create(
        organization=company.organization,
        company=company,
        label=label,
        pfx_blob=base64.b64encode(pfx_bytes).decode("ascii"),
        password=password,
        fingerprint_sha256=fingerprint,
        subject_name=parsed_certificate.subject.rfc4514_string()[:240],
        valid_from=valid_from,
        valid_until=valid_until,
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    record_event(
        action="hub.certificate.uploaded",
        actor=actor,
        organization=company.organization,
        target=certificate,
        request=request,
        metadata={"fingerprint_prefix": fingerprint[:12]},
    )
    certificate_is_current = valid_until > timezone.now()
    sync, _created = NfseSync.objects.update_or_create(
        organization=company.organization,
        company=company,
        defaults={
            "certificate": certificate,
            "enabled": certificate_is_current,
            "status": NfseSync.Status.IDLE if certificate_is_current else NfseSync.Status.PAUSED,
            "last_error_code": "",
            "last_error_message": "",
            "last_error_at": None,
            "failure_count": 0,
            "next_run_at": timezone.now() if certificate_is_current else None,
        },
    )
    record_event(
        action="hub.nfse.sync_prepared_from_certificate",
        actor=actor,
        organization=company.organization,
        target=sync,
        request=request,
        metadata={
            "company_id": str(company.id),
            "certificate_current": certificate_is_current,
            "runtime_enabled": settings.NFSE_ADN_SYNC_ENABLED,
        },
    )
    if certificate_is_current and settings.NFSE_ADN_SYNC_ENABLED:
        from apps.hub.tasks import dispatch_active_nfse_syncs

        transaction.on_commit(dispatch_active_nfse_syncs.delay)
    return certificate


def integration_artifact_export(artifact: IntegrationArtifact) -> str:
    """Contract v1: a derived artifact only. The immutable original XML is never altered."""
    return json.dumps(artifact.payload, ensure_ascii=False, sort_keys=True)


_XML_MARKUP = re.compile(
    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!DOCTYPE[^>]*>"
    r"|<(?P<closing>/?)(?P<name>(?:[\w.-]+:)?[\w.-]+)"
    r"(?:\s+[^\s=/>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*\s*(?P<empty>/?)>",
    re.DOTALL,
)


def _local(name: str) -> str:
    return name.rsplit(":", 1)[-1]


def _xml_with_dominio_accumulator(original_xml: str, accumulator_code: str) -> str:
    """Write the confirmed accumulator at ``infNFSe/valores/acum`` in a derived XML.

    Only that tag is touched: the rest of the document keeps the original bytes, prefixes
    and declaration. Re-serializing through ElementTree used to rename the namespace to
    ``ns0:`` and drop ``<?xml ...?>``, which is not what the Domínio importer was fed when
    the layout was validated.
    """

    try:
        ElementTree.fromstring(original_xml)
    except (ElementTree.ParseError, ValueError) as exc:
        raise ValueError("O XML original da nota é inválido.") from exc

    # A versão anterior do adaptador gerava ACU fora do contrato. Ela nunca deve vazar para o
    # XML derivado novo, mesmo se um arquivo de entrada já vier contaminado por esse formato.
    xml = re.sub(
        r"<((?:[\w.-]+:)?)ACU\b[^>]*/>|<((?:[\w.-]+:)?)ACU\b[^>]*>.*?</\2ACU\s*>",
        "",
        original_xml,
        flags=re.DOTALL,
    )

    stack: list[str] = []
    info_count = 0
    values: list[tuple[str, int, int, int]] = []  # name, open start, open end, close start
    accumulators: list[tuple[int, int]] = []  # whole element span inside infNFSe/valores
    acum_open: int | None = None
    net_value_end: int | None = None  # right after infNFSe/valores/vLiq, where Domínio reads it
    for token in _XML_MARKUP.finditer(xml):
        name = token.group("name")
        if name is None:
            continue
        parent_path = [_local(item) for item in stack[-2:]]
        if token.group("closing"):
            closed = stack.pop() if stack else ""
            if _local(closed) == "acum" and acum_open is not None and len(stack) >= 2:
                if [_local(item) for item in stack[-2:]] == ["infNFSe", "valores"]:
                    accumulators.append((acum_open, token.end()))
                acum_open = None
            if _local(closed) == "vLiq" and [_local(item) for item in stack[-2:]] == [
                "infNFSe",
                "valores",
            ]:
                net_value_end = token.end()
            if _local(closed) == "valores" and stack and _local(stack[-1]) == "infNFSe":
                values[-1] = (*values[-1][:3], token.start())
            continue
        local = _local(name)
        if local == "infNFSe":
            info_count += 1
        if local == "valores" and stack and _local(stack[-1]) == "infNFSe":
            values.append((name, token.start(), token.end(), -1))
        if local == "acum" and parent_path == ["infNFSe", "valores"]:
            if token.group("empty"):
                accumulators.append((token.start(), token.end()))
            else:
                acum_open = token.start()
        if not token.group("empty"):
            stack.append(name)

    if info_count != 1:
        raise ValueError("O XML da NFS-e precisa conter um único grupo infNFSe.")
    if len(values) > 1:
        raise ValueError("O XML da NFS-e contém mais de um grupo infNFSe/valores.")
    if len(accumulators) > 1:
        raise ValueError("O XML da NFS-e contém mais de uma tag infNFSe/valores/acum.")

    escaped = accumulator_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if values:
        values_name, _open_start, open_end, close_start = values[0]
        prefix = values_name[: -len("valores")]
        element = f"<{prefix}acum>{escaped}</{prefix}acum>"
        if accumulators:
            acum_start, acum_end = accumulators[0]
            rendered = xml[:acum_start] + element + xml[acum_end:]
        elif close_start == -1:
            # Self-closing <valores/>: open it to hold the accumulator.
            empty = xml[_open_start:open_end]
            rendered = (
                xml[:_open_start]
                + empty[:-2].rstrip()
                + ">"
                + element
                + f"</{values_name}>"
                + xml[open_end:]
            )
        else:
            insert_at = net_value_end if net_value_end is not None else close_start
            rendered = xml[:insert_at] + element + xml[insert_at:]
    else:
        info_close = None
        depth_names: list[tuple[str, int]] = []
        for token in _XML_MARKUP.finditer(xml):
            name = token.group("name")
            if name is None:
                continue
            if token.group("closing"):
                closed, _ = depth_names.pop() if depth_names else ("", 0)
                if _local(closed) == "infNFSe":
                    info_close = (closed, token.start())
                continue
            if not token.group("empty"):
                depth_names.append((name, token.start()))
        if info_close is None:
            raise ValueError("O XML da NFS-e precisa conter um único grupo infNFSe.")
        info_name, close_at = info_close
        prefix = info_name[: -len("infNFSe")]
        rendered = (
            xml[:close_at]
            + f"<{prefix}valores><{prefix}acum>{escaped}</{prefix}acum></{prefix}valores>"
            + xml[close_at:]
        )

    rendered_root = ElementTree.fromstring(rendered)
    detected_paths: list[str] = []
    for rendered_info in rendered_root.iter():
        if not isinstance(rendered_info.tag, str):
            continue
        if rendered_info.tag.rsplit("}", 1)[-1] != "infNFSe":
            continue
        for rendered_values in rendered_info:
            if rendered_values.tag.rsplit("}", 1)[-1] != "valores":
                continue
            detected_paths.extend(
                (child.text or "").strip()
                for child in rendered_values
                if child.tag.rsplit("}", 1)[-1] == "acum"
            )
    if detected_paths != [accumulator_code]:
        raise ValueError("A tag infNFSe/valores/acum não pôde ser validada no XML exportado.")
    return rendered


_NFSE_EXPORT_SIDES = {
    "provided": ("Saída · serviço prestado", "Serviços", "Emitidas"),
    "taken": ("Entrada · serviço tomado", "Entradas", "Tomadas"),
}


def _document_label(document: NfseDocument) -> str:
    data = document.normalized_data if isinstance(document.normalized_data, dict) else {}
    return str(data.get("number") or document.source_nsu or document.id)[:40]


def nfse_company_archive_folder(*, root: str, dominio_code: str | None) -> str:
    """Build the Domínio ``code-`` ZIP folder without allowing nested paths."""

    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", dominio_code or "").strip("_-.")
    if not safe_code:
        safe_code = "SEM-CODIGO"
    return f"{root}/{safe_code[:40]}-"


_NFSE_EXPORT_PAGE = 200


def _documents_with_xml_in_pages(documents: list[NfseDocument]) -> Iterator[NfseDocument]:
    """Yield the notes in order, decrypting the XML of one page at a time.

    Callers load the selection without ``original_xml``; production runs behind PgBouncer
    with server-side cursors disabled, so a single query would pull every XML at once.
    """

    for start in range(0, len(documents), _NFSE_EXPORT_PAGE):
        page = documents[start : start + _NFSE_EXPORT_PAGE]
        loaded = NfseDocument.objects.select_related("company").in_bulk(
            [document.pk for document in page]
        )
        for document in page:
            if document.pk not in loaded:
                raise ValueError("Seleção desatualizada. Selecione as notas novamente.")
            yield loaded[document.pk]


@transaction.atomic
def create_nfse_export(
    *, organization: Any, documents: list[NfseDocument], actor: User
) -> NfseExport:
    """Freeze classified XML and evidence in a private conference package.

    This is deliberately not an import layout until Domínio supplies and validates one.
    """

    from apps.hub.nfse_sync import nfse_match_data

    ordered_documents = sorted(documents, key=lambda document: str(document.id))
    if not ordered_documents or any(
        document.organization_id != organization.id for document in ordered_documents
    ):
        raise ValueError("Selecione notas do mesmo escritório para gerar o pacote.")
    if len({document.id for document in ordered_documents}) != len(ordered_documents):
        raise ValueError("A seleção contém notas repetidas.")
    artifact_rows = list(
        IntegrationArtifact.objects.filter(
        organization=organization, document__in=ordered_documents
        ).order_by("document_id", "-created_at")
    )
    superseded_ids = {
        str(artifact.payload.get("previous_artifact_id"))
        for artifact in artifact_rows
        if isinstance(artifact.payload, dict) and artifact.payload.get("previous_artifact_id")
    }
    artifacts: dict[str, IntegrationArtifact] = {}
    for artifact in artifact_rows:
        if str(artifact.id) not in superseded_ids:
            artifacts.setdefault(str(artifact.document_id), artifact)
    missing = [document for document in ordered_documents if str(document.id) not in artifacts]
    if missing:
        raise ValueError("Toda NFS-e do pacote precisa ter acumulador confirmado.")
    catalogs = active_catalog_codes(
        list(
            ClientCompany.objects.filter(
                pk__in={document.company_id for document in ordered_documents}
            )
        )
    )
    outside_catalog = [
        document
        for document in ordered_documents
        if document.company_id in catalogs
        and artifacts[str(document.id)].accumulator_code not in catalogs[document.company_id]
    ]
    if outside_catalog:
        sample = outside_catalog[0]
        raise ValueError(
            f"{len(outside_catalog)} NFS-e do pacote usam acumulador que não está ativo "
            f"no Domínio da empresa (ex.: nº {_document_label(sample)}, acumulador "
            f"{artifacts[str(sample.id)].accumulator_code})."
        )

    snapshot_documents: list[dict[str, str]] = []
    # The web machine has little memory to spare: a whole-portfolio package used to hold every
    # decrypted XML plus the ZIP twice in RAM and the request died. The ZIP now goes to a disk
    # temp file and only one page of XMLs is decrypted at a time.
    with tempfile.TemporaryFile() as archive:
        with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
            manifest = io.StringIO(newline="")
            writer = csv.writer(manifest, delimiter=";")
            writer.writerow(
                [
                    "Documento",
                    "Empresa",
                    "Codigo Dominio",
                    "Movimento",
                    "Importador Dominio",
                    "Competencia",
                    "Acumulador",
                    "Hash",
                ]
            )
            for document in _documents_with_xml_in_pages(ordered_documents):
                artifact = artifacts[str(document.id)]
                source = re.sub(r"[^A-Za-z0-9._-]", "_", document.source_nsu or str(document.id))
                issued_at = document.issued_at or _issued_at_from_normalized_data(
                    document.normalized_data
                )
                if issued_at and timezone.is_aware(issued_at):
                    issued_at = timezone.localtime(issued_at)
                competence = issued_at.strftime("%Y%m") if issued_at else "SEM-COMPETENCIA"
                # The accumulator belongs to one side of the note: an issued note must go through
                # Domínio's Serviços importer of the issuing company, a taken one through Entradas.
                direction = str(nfse_match_data(document).get("direction", ""))
                movement, importer, side_folder = _NFSE_EXPORT_SIDES.get(
                    direction, ("A confirmar", "Conferir", "Tipo-a-confirmar")
                )
                company_folder = nfse_company_archive_folder(
                    root=f"NFS-e/{side_folder}",
                    dominio_code=document.company.dominio_code,
                )
                path = f"{company_folder}/{competence}/NFS-e-{source}.xml"
                dominio_xml = _xml_with_dominio_accumulator(
                    document.original_xml,
                    artifact.accumulator_code,
                )
                bundle.writestr(path, dominio_xml)
                writer.writerow(
                    [
                        document.source_nsu or str(document.id),
                        document.company.name,
                        document.company.dominio_code or "",
                        movement,
                        importer,
                        competence,
                        artifact.accumulator_code,
                        document.document_hash,
                    ]
                )
                snapshot_documents.append(
                    {
                        "document_id": str(document.id),
                        "document_hash": document.document_hash,
                        "artifact_id": str(artifact.id),
                        "accumulator_code": artifact.accumulator_code,
                        "path": path,
                    }
                )
            bundle.writestr("manifesto-classificacao.csv", manifest.getvalue().encode("utf-8-sig"))
        archive.seek(0)
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
        export = NfseExport.objects.create(
            organization=organization,
            target="conference_only_pending_dominio_layout",
            adapter_version="nfse-conference-acum-v3",
            content_hash=digest,
            document_count=len(ordered_documents),
            snapshot={"documents": snapshot_documents, "layout": "nfse-conference-acum-v3"},
            created_by=actor,
        )
        export.content.save(f"nfse-dominio-{export.id}.zip", File(archive), save=True)
    export.documents.add(*ordered_documents)
    return export


@transaction.atomic
def prepare_dte_run(
    *,
    organization: Any,
    connector: Connector | None,
    companies: list[ClientCompany],
    actor: Any = None,
    request: Any = None,
) -> DteRun:
    """Persist the operator's scope before a separately-authorized Serpro dispatch.

    This deliberately creates no network request. The later dispatcher must require a
    confirmed ConsumptionConfirmation and configured mTLS credentials.
    """

    if not companies:
        raise ValueError("Selecione pelo menos uma empresa.")
    if any(company.organization_id != organization.id for company in companies):
        raise ValueError("Todas as empresas precisam pertencer ao mesmo escritório.")
    for company in companies:
        try:
            normalize_cnpj(company.cnpj_masked)
        except ValidationError as exc:
            raise ValueError(
                "Uma empresa selecionada está sem CNPJ válido. Revise o cadastro antes de preparar."
            ) from exc
    run = DteRun.objects.create(
        organization=organization,
        connector=connector,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        total_companies=len(companies),
    )
    DteRunItem.objects.bulk_create(
        [DteRunItem(organization=organization, run=run, company=company) for company in companies]
    )
    record_event(
        action="hub.dte.run_prepared",
        actor=actor,
        organization=organization,
        target=run,
        request=request,
        metadata={"companies": len(companies), "network_dispatched": False},
    )
    return run


@transaction.atomic
def prepare_dte_next_page(
    *, source_item: DteRunItem, actor: Any = None, request: Any = None
) -> DteRun:
    """Prepare exactly one additional Serpro page; approval and billing stay separate."""

    source = (
        DteRunItem.objects.select_for_update()
        .select_related("run", "company")
        .get(id=source_item.id)
    )
    if source.status != DteRunItem.Status.COMPLETED or not source.more_available:
        raise ValueError("Esta consulta não tem outra página disponível.")
    if not re.fullmatch(r"\d{1,24}", source.next_page_pointer):
        raise ValueError("Falta o ponteiro da próxima página. Atualize a primeira consulta.")
    if DteRunItem.objects.filter(continued_from=source).exists():
        raise ValueError("A próxima página desta consulta já foi preparada.")
    run = DteRun.objects.create(
        organization=source.organization,
        connector=source.run.connector,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        total_companies=1,
    )
    DteRunItem.objects.create(
        organization=source.organization,
        run=run,
        company=source.company,
        requested_page_pointer=source.next_page_pointer,
        continued_from=source,
    )
    record_event(
        action="hub.dte.next_page_prepared",
        actor=actor,
        organization=source.organization,
        target=run,
        request=request,
        metadata={"source_item_id": str(source.id), "network_dispatched": False},
    )
    return run


class DteRunTransitionError(RuntimeError):
    """A run was asked for a transition its current status does not allow."""


# The catalogue key that a Caixa Postal consultation bills against. Kept here rather than
# imported so a change to the Integra catalogue cannot silently change what was approved.
DTE_ACTION_CODE = "caixapostal.mensagens"
DTE_DETAIL_ACTION_CODE = "caixapostal.detalhe"


class FiscalGuideTransitionError(RuntimeError):
    """An obligation cannot be sent from its current operational state."""


class DctfWebDocumentTransitionError(RuntimeError):
    """A DCTFWeb document cannot be consulted from its current state."""


@transaction.atomic
def prepare_dctfweb_guide_from_documents(
    *,
    organization: Any,
    company: ClientCompany,
    competence: str,
    due_on: date,
    amount_cents: int,
    source_reference: str,
    actor: Any = None,
    request: Any = None,
) -> FiscalGuide:
    """Promote one governed Domínio calculation after both official PDFs exist."""

    if FiscalGuide.objects.filter(
        organization=organization,
        company=company,
        competence=competence,
        kind=FiscalGuide.Kind.DCTFWEB,
        status=FiscalGuide.Status.UNKNOWN,
    ).exists():
        raise DctfWebDocumentTransitionError(
            "Confirme o resultado da emissão anterior antes de preparar outra guia."
        )

    if company.organization_id != organization.id or not company.active:
        raise DctfWebDocumentTransitionError("A empresa não pertence à carteira ativa.")
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None:
        raise DctfWebDocumentTransitionError("Informe uma competência no formato MM/AAAA.")
    if amount_cents < 1 or not source_reference:
        raise DctfWebDocumentTransitionError(
            "A apuração do Domínio não possui valor e referência válidos."
        )
    available_kinds = set(
        DctfWebDocument.objects.filter(
            organization=organization,
            company=company,
            competence=competence,
            status=DctfWebDocument.Status.AVAILABLE,
        ).values_list("kind", flat=True)
    )
    required = {
        DctfWebDocument.Kind.DECLARATION,
        DctfWebDocument.Kind.RECEIPT,
    }
    if not required.issubset(available_kinds):
        raise DctfWebDocumentTransitionError(
            "Baixe e confira a declaração completa e o recibo antes de preparar a emissão."
        )

    reference = f"dominio-dctfweb-{company.dominio_code}-{competence[3:]}{competence[:2]}"
    guide, created = FiscalGuide.objects.select_for_update().get_or_create(
        organization=organization,
        company=company,
        reference=reference,
        defaults={
            "kind": FiscalGuide.Kind.DCTFWEB,
            "status": FiscalGuide.Status.READY,
            "competence": competence,
            "due_on": due_on,
            "amount_cents": amount_cents,
            "integra_service_key": "dctfweb.guia",
            "external_key": source_reference[:160],
            "source_updated_at": timezone.now(),
        },
    )
    if not created:
        if guide.status in {
            FiscalGuide.Status.QUEUED,
            FiscalGuide.Status.ISSUING,
            FiscalGuide.Status.ISSUED,
            FiscalGuide.Status.UNKNOWN,
        }:
            return guide
        guide.kind = FiscalGuide.Kind.DCTFWEB
        guide.status = FiscalGuide.Status.READY
        guide.competence = competence
        guide.due_on = due_on
        guide.amount_cents = amount_cents
        guide.integra_service_key = "dctfweb.guia"
        guide.external_key = source_reference[:160]
        guide.source_updated_at = timezone.now()
        guide.error_code = ""
        guide.error_message = ""
        guide.save()
    record_event(
        action="hub.dctfweb.guide_prepared",
        actor=actor,
        organization=organization,
        target=guide,
        request=request,
        metadata={
            "competence": competence,
            "source_reference": source_reference[:160],
            "documents": sorted(required),
            "created": created,
        },
    )
    return guide


class ParcelamentoTransitionError(RuntimeError):
    """A PARCSN operation cannot be queued in its current state."""


DCTFWEB_DOCUMENT_SERVICE: dict[str, str] = {
    DctfWebDocument.Kind.DECLARATION: "dctfweb.declaracao_completa",
    DctfWebDocument.Kind.RECEIPT: "dctfweb.recibo",
}

PARCELAMENTO_SERVICE: dict[str, str] = {
    ParcelamentoOperation.Kind.ORDERS: "parcelamento.parcsn.pedidos",
    ParcelamentoOperation.Kind.DETAIL: "parcelamento.parcsn.detalhe",
    ParcelamentoOperation.Kind.INSTALLMENTS: "parcelamento.parcsn.parcelas",
    ParcelamentoOperation.Kind.DAS: "parcelamento.parcsn.das",
}


@transaction.atomic
def release_uncertain_parcelamento_operation(
    *,
    organization: Any,
    company: ClientCompany,
    operation_id: Any,
    actor: Any = None,
    request: Any = None,
) -> ParcelamentoOperation:
    """Record a human check of an uncertain PARCSN result and allow one new attempt.

    The token reservation stays untouched: whether Serpro billed the uncertain
    call is settled by the usage reconciliation, never by this button.
    """

    operation = (
        ParcelamentoOperation.objects.select_for_update()
        .filter(organization=organization, company=company, id=operation_id)
        .first()
    )
    if operation is None:
        raise ParcelamentoTransitionError("Operação não encontrada nesta empresa.")
    if operation.status != ParcelamentoOperation.Status.UNKNOWN:
        raise ParcelamentoTransitionError("Somente resultado a confirmar pode ser liberado.")
    actor_label = getattr(actor, "email", "") or "usuário"
    operation.status = ParcelamentoOperation.Status.FAILED
    operation.error_code = "manual_review"
    operation.error_message = (
        f"Conferido por {actor_label} em {timezone.localtime():%d/%m/%Y %H:%M}."
    )[:240]
    operation.completed_at = timezone.now()
    operation.save(
        update_fields=["status", "error_code", "error_message", "completed_at", "updated_at"]
    )
    record_event(
        action="hub.parcelamento.uncertain_released",
        actor=actor,
        organization=organization,
        target=operation,
        request=request,
        metadata={"kind": operation.kind, "service": operation.service_key},
    )
    return operation


@transaction.atomic
def request_parcelamento_operation(
    *,
    organization: Any,
    company: ClientCompany,
    kind: str,
    agreement_number: int | None = None,
    competence: str = "",
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
) -> ParcelamentoOperation:
    """Reserve the quoted PARCSN action before dispatching it once."""

    from apps.hub.integra_access import can_execute_company_operation

    if not can_execute_company_operation(
        organization_id=organization.pk,
        company_id=company.pk,
        actor_id=getattr(actor, "pk", None),
        module_code=ProductModule.Code.INTEGRA,
    ):
        raise ParcelamentoTransitionError(
            "O solicitante precisa de acesso operacional vigente à empresa e ao módulo Integra."
        )

    if company.organization_id != organization.id or not company.active:
        raise ParcelamentoTransitionError("A empresa não pertence à carteira ativa.")
    try:
        service_key = PARCELAMENTO_SERVICE[kind]
    except KeyError as exc:
        raise ParcelamentoTransitionError("Escolha uma operação de parcelamento válida.") from exc
    if kind == ParcelamentoOperation.Kind.DETAIL:
        if agreement_number is None or agreement_number < 1:
            raise ParcelamentoTransitionError("Informe um acordo válido para consultar o detalhe.")
    elif agreement_number is not None:
        raise ParcelamentoTransitionError("Esta operação não aceita número de acordo.")
    if kind == ParcelamentoOperation.Kind.DAS:
        if re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", competence) is None:
            raise ParcelamentoTransitionError("Informe a parcela no formato AAAAMM.")
    elif competence:
        raise ParcelamentoTransitionError("Esta operação não aceita competência.")
    try:
        normalize_cnpj(company.cnpj_masked)
    except ValidationError as exc:
        raise ParcelamentoTransitionError(
            "Confira o CNPJ da empresa antes de consultar o parcelamento."
        ) from exc

    previous = (
        ParcelamentoOperation.objects.select_for_update()
        .filter(
            organization=organization,
            company=company,
            kind=kind,
            agreement_number=agreement_number,
            competence=competence,
        )
        .first()
    )
    if previous and previous.status in {
        ParcelamentoOperation.Status.QUEUED,
        ParcelamentoOperation.Status.FETCHING,
        ParcelamentoOperation.Status.UNKNOWN,
    }:
        raise ParcelamentoTransitionError(
            "Essa operação já está na fila ou aguardando confirmação."
        )
    if (
        previous
        and kind == ParcelamentoOperation.Kind.DAS
        and previous.status == ParcelamentoOperation.Status.AVAILABLE
    ):
        raise ParcelamentoTransitionError("O DAS desta competência já foi emitido.")
    operation = ParcelamentoOperation(
        organization=organization,
        company=company,
        kind=kind,
        agreement_number=agreement_number,
        competence=competence,
        attempt=(previous.attempt + 1 if previous else 1),
    )
    if not organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise ParcelamentoTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            operation.token_usage_event = reserve_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
                idempotency_key=f"parcelamento:{operation.id}:{operation.attempt}",
            )
        except BillingError as exc:
            raise ParcelamentoTransitionError(str(exc)) from exc
    operation.service_key = service_key
    operation.status = ParcelamentoOperation.Status.QUEUED
    operation.requested_by = actor if getattr(actor, "is_authenticated", False) else None
    operation.requested_at = timezone.now()
    operation.completed_at = None
    operation.provider_request_id = ""
    operation.provider_payload = ""
    operation.error_code = ""
    operation.error_message = ""
    operation.save()

    from apps.hub.module_activities import sync_parcelamento_operation_activity

    sync_parcelamento_operation_activity(operation.pk)

    from apps.hub.tasks import dispatch_parcelamento_operation

    if organization.is_demo:
        transaction.on_commit(lambda: dispatch_parcelamento_operation.run(str(operation.id)))
    else:
        transaction.on_commit(lambda: dispatch_parcelamento_operation.delay(str(operation.id)))
    record_event(
        action="hub.parcelamento.requested",
        actor=actor,
        organization=organization,
        target=operation,
        request=request,
        metadata={
            "kind": kind,
            "agreement_number": agreement_number,
            "competence": competence,
            "service": service_key,
        },
    )
    return operation


@transaction.atomic
def request_dctfweb_document(
    *,
    organization: Any,
    company: ClientCompany,
    competence: str,
    kind: str,
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
) -> DctfWebDocument:
    """Reserve exactly the quoted consultation before it reaches the worker."""

    from apps.hub.integra_access import can_consult_dctfweb

    if not can_consult_dctfweb(
        organization_id=organization.pk,
        company_id=company.pk,
        actor_id=getattr(actor, "pk", None),
    ):
        raise DctfWebDocumentTransitionError(
            "O solicitante precisa de acesso operacional vigente à empresa e ao módulo Guias."
        )

    if company.organization_id != organization.id or not company.active:
        raise DctfWebDocumentTransitionError("A empresa não pertence à carteira ativa.")
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None:
        raise DctfWebDocumentTransitionError("Informe uma competência no formato MM/AAAA.")
    try:
        service_key = DCTFWEB_DOCUMENT_SERVICE[kind]
    except KeyError as exc:
        raise DctfWebDocumentTransitionError("Escolha declaração completa ou recibo.") from exc
    try:
        normalize_cnpj(company.cnpj_masked)
    except ValidationError as exc:
        raise DctfWebDocumentTransitionError(
            "Confira o CNPJ da empresa antes de consultar a DCTFWeb."
        ) from exc

    document, _created = DctfWebDocument.objects.select_for_update().get_or_create(
        organization=organization,
        company=company,
        competence=competence,
        kind=kind,
        defaults={"service_key": service_key},
    )
    if (
        document.status
        in {
            DctfWebDocument.Status.QUEUED,
            DctfWebDocument.Status.FETCHING,
            DctfWebDocument.Status.AVAILABLE,
            DctfWebDocument.Status.UNKNOWN,
        }
        and document.attempt
    ):
        raise DctfWebDocumentTransitionError(
            "Essa consulta já está na fila, concluída ou aguardando confirmação."
        )
    document.attempt += 1
    idempotency_key = f"dctfweb-document:{document.id}:{document.attempt}"
    if not organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise DctfWebDocumentTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            usage = reserve_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
                idempotency_key=idempotency_key,
            )
        except BillingError as exc:
            raise DctfWebDocumentTransitionError(str(exc)) from exc
        document.token_usage_event = usage
    document.service_key = service_key
    document.status = DctfWebDocument.Status.QUEUED
    document.requested_by = actor if getattr(actor, "is_authenticated", False) else None
    document.requested_at = timezone.now()
    document.completed_at = None
    document.error_code = ""
    document.error_message = ""
    document.save()

    from apps.hub.module_activities import sync_dctfweb_document_activity

    sync_dctfweb_document_activity(document.pk)

    from apps.hub.tasks import dispatch_dctfweb_document

    if organization.is_demo:
        transaction.on_commit(lambda: dispatch_dctfweb_document.run(str(document.id)))
    else:
        transaction.on_commit(lambda: dispatch_dctfweb_document.delay(str(document.id)))
    record_event(
        action="hub.dctfweb.document_requested",
        actor=actor,
        organization=organization,
        target=document,
        request=request,
        metadata={"kind": kind, "competence": competence, "service": service_key},
    )
    return document


@transaction.atomic
def issue_fiscal_guide(
    *,
    guide: FiscalGuide,
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
) -> FiscalGuide:
    """Reserve one central issuance before queueing a Domínio obligation."""

    from apps.hub.guide_history import record_guide_attempt, save_guide_attempt
    from apps.hub.integra_access import can_execute_company_operation

    guide = FiscalGuide.objects.select_for_update().get(id=guide.id)
    if not can_execute_company_operation(
        organization_id=guide.organization_id,
        company_id=guide.company_id,
        actor_id=getattr(actor, "pk", None),
        module_code=ProductModule.Code.GUIDES,
    ):
        raise FiscalGuideTransitionError(
            "O solicitante precisa de acesso operacional vigente à empresa e ao módulo Guias."
        )
    if guide.status not in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
        raise FiscalGuideTransitionError("Essa obrigação já está em emissão ou foi concluída.")
    if FiscalGuide.objects.filter(
        organization_id=guide.organization_id,
        company_id=guide.company_id,
        kind=guide.kind,
        competence=guide.competence,
        status=FiscalGuide.Status.UNKNOWN,
    ).exists():
        raise FiscalGuideTransitionError("Confirme a emissão anterior desta competência.")
    try:
        normalize_cnpj(guide.company.cnpj_masked)
    except ValidationError as exc:
        raise FiscalGuideTransitionError(
            "Confira o CNPJ da empresa antes de autorizar a emissão."
        ) from exc
    record_guide_attempt(guide)
    guide.issue_attempt += 1
    idempotency_key = f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
    if not guide.organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=guide.organization,
                module_code="integra",
                action_code=guide.integra_service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise FiscalGuideTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            reserve_tokens(
                organization=guide.organization,
                module_code="integra",
                action_code=guide.integra_service_key,
                idempotency_key=idempotency_key,
            )
        except BillingError as exc:
            raise FiscalGuideTransitionError(str(exc)) from exc
    guide.status = FiscalGuide.Status.QUEUED
    guide.issue_requested_by = actor if getattr(actor, "is_authenticated", False) else None
    guide.issue_requested_at = timezone.now()
    guide.provider_request_id = ""
    guide.provider_payload = ""
    guide.issued_at = None
    guide.error_code = ""
    guide.error_message = ""
    save_guide_attempt(
        guide,
        update_fields=[
            "status",
            "issue_attempt",
            "issue_requested_by",
            "issue_requested_at",
            "provider_request_id",
            "provider_payload",
            "issued_at",
            "error_code",
            "error_message",
            "updated_at",
        ],
    )
    from apps.hub.module_activities import sync_fiscal_guide_activity

    sync_fiscal_guide_activity(guide.pk)
    from apps.hub.tasks import dispatch_fiscal_guide

    if guide.organization.is_demo:
        transaction.on_commit(lambda: dispatch_fiscal_guide.run(str(guide.id)))
    else:
        transaction.on_commit(lambda: dispatch_fiscal_guide.delay(str(guide.id)))
    record_event(
        action="hub.fiscal_guide.issuance_requested",
        actor=actor,
        organization=guide.organization,
        target=guide,
        request=request,
        metadata={
            "kind": guide.kind,
            "competence": guide.competence,
            "service": guide.integra_service_key,
        },
    )
    return guide


_GUIDE_SERVICE_BY_KIND: dict[str, str] = {
    FiscalGuide.Kind.DCTFWEB: "dctfweb.guia",
    FiscalGuide.Kind.DAS: "pgdasd.das",
    FiscalGuide.Kind.MEI: "pgmei.das",
}


@transaction.atomic
def sync_fiscal_guides(
    *, organization: Any, rows: list[dict[str, object]]
) -> FiscalGuideSyncResult:
    """Accept the bounded obligation snapshot emitted by the local Domínio agent."""

    companies = {
        company.dominio_code: company
        for company in ClientCompany.objects.filter(organization=organization, active=True)
        if company.dominio_code
    }
    created = updated = ignored = 0
    for row in rows:
        company = companies.get(str(row.get("company_code", "")).strip())
        reference = str(row.get("reference", "")).strip()
        kind = str(row.get("kind", "")).strip()
        competence = str(row.get("competence", "")).strip()
        try:
            due_on = datetime.strptime(str(row.get("due_on", "")), "%Y-%m-%d").date()
            amount_cents = int(str(row.get("amount_cents", 0)))
        except (TypeError, ValueError):
            ignored += 1
            continue
        if (
            company is None
            or not reference
            or kind not in FiscalGuide.Kind.values
            or re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None
            or amount_cents < 0
        ):
            ignored += 1
            continue
        guide, was_created = FiscalGuide.objects.get_or_create(
            organization=organization,
            company=company,
            reference=reference[:120],
            defaults={
                "kind": kind,
                "status": FiscalGuide.Status.DISCOVERED,
                "competence": competence,
                "due_on": due_on,
                "amount_cents": amount_cents,
                "integra_service_key": _GUIDE_SERVICE_BY_KIND[kind],
            },
        )
        if was_created:
            created += 1
            from apps.hub.module_activities import sync_fiscal_guide_activity

            sync_fiscal_guide_activity(guide.pk)
            continue
        if guide.status not in {FiscalGuide.Status.DISCOVERED, FiscalGuide.Status.FAILED}:
            ignored += 1
            continue
        guide.kind = kind
        guide.competence = competence
        guide.due_on = due_on
        guide.amount_cents = amount_cents
        guide.integra_service_key = _GUIDE_SERVICE_BY_KIND[kind]
        guide.save(
            update_fields=[
                "kind",
                "competence",
                "due_on",
                "amount_cents",
                "integra_service_key",
                "updated_at",
            ]
        )
        updated += 1
        from apps.hub.module_activities import sync_fiscal_guide_activity

        sync_fiscal_guide_activity(guide.pk)
    return FiscalGuideSyncResult(created=created, updated=updated, ignored=ignored)


@transaction.atomic
def approve_dte_run(
    *,
    run: DteRun,
    actor: Any = None,
    request: Any = None,
    approved_overage: bool = False,
    approved_overage_total_cents: int | None = None,
) -> ConsumptionConfirmation:
    """Record the consumption the operator is authorizing, and release the run.

    CICA owns the Serpro credentials; the office only approves its operational
    scope.  The queued worker later performs the centrally metered dispatch.
    """

    if run.status != DteRun.Status.AWAITING_APPROVAL:
        raise DteRunTransitionError("Esta consulta já saiu da fila de autorização.")
    for item in run.items.select_related("company"):
        try:
            normalize_cnpj(item.company.cnpj_masked)
        except ValidationError as exc:
            raise DteRunTransitionError(
                "Uma empresa desta consulta está sem CNPJ válido. Retire a preparação, "
                "revise o cadastro e prepare novamente antes de autorizar consumo."
            ) from exc
    if run.organization.is_demo:
        quote: TokenQuote | UsageQuote | None = None
    else:
        try:
            quote = quote_tokens(
                organization=run.organization,
                module_code="integra",
                action_code=DTE_ACTION_CODE,
                operations=run.total_companies,
            )
        except BillingError as exc:
            try:
                quote = quote_usage(
                    organization=run.organization,
                    action_code=DTE_ACTION_CODE,
                    units=run.total_companies,
                )
            except BillingError:
                raise DteRunTransitionError(str(exc)) from exc
    additional_overage_cents = quote.additional_overage_cents if quote is not None else 0
    if additional_overage_cents:
        assert quote is not None
        if not approved_overage or approved_overage_total_cents != quote.additional_overage_cents:
            raise DteRunTransitionError(
                "O excedente desta consulta mudou ou não foi autorizado com o valor exato. "
                "Revise a fila antes de enviar."
            )
    # Reserve each outbound Caixa Postal call before it is queued. A failed reservation
    # means no provider request can escape the product and no unexpected overage occurs.
    for item in run.items.select_for_update().filter(status=DteRunItem.Status.PENDING):
        if run.organization.is_demo:
            continue
        try:
            assert quote is not None
            key = f"dte-run-item:{item.id}:caixapostal"
            if isinstance(quote, TokenQuote):
                token_usage = reserve_tokens(
                    organization=run.organization,
                    module_code="integra",
                    action_code=DTE_ACTION_CODE,
                    idempotency_key=key,
                )
                item.token_usage_event = token_usage
                item.save(update_fields=["token_usage_event", "updated_at"])
            else:
                legacy_usage = reserve_usage(
                    organization=run.organization,
                    action_code=DTE_ACTION_CODE,
                    idempotency_key=key,
                    approved_overage=approved_overage,
                    approved_overage_cents=(
                        quote.overage_unit_price_cents if approved_overage else None
                    ),
                    require_explicit_overage=True,
                )
                item.usage_event = legacy_usage
                item.save(update_fields=["usage_event", "updated_at"])
        except BillingError as exc:
            raise DteRunTransitionError(str(exc)) from exc

    confirmation = ConsumptionConfirmation.objects.create(
        organization=run.organization,
        connector=run.connector,
        action_code=DTE_ACTION_CODE,
        scope_summary=f"Caixa Postal de {run.total_companies} empresa(s).",
        estimated_units=run.total_companies,
        status="confirmed",
        confirmed_by=actor if getattr(actor, "is_authenticated", False) else None,
        confirmed_at=timezone.now(),
    )
    run.status = DteRun.Status.QUEUED
    run.save(update_fields=["status", "updated_at"])
    from apps.hub.tasks import dispatch_dte_run

    if run.organization.is_demo:
        transaction.on_commit(lambda: dispatch_dte_run.run(str(run.id)))
    else:
        transaction.on_commit(lambda: dispatch_dte_run.delay(str(run.id)))
    record_event(
        action="hub.dte.run_approved",
        actor=actor,
        organization=run.organization,
        target=run,
        request=request,
        metadata={
            "companies": run.total_companies,
            "action_code": DTE_ACTION_CODE,
            "queued_for_central_dispatch": True,
        },
    )
    return confirmation


@transaction.atomic
def cancel_dte_run(
    *,
    run: DteRun,
    actor: Any = None,
    request: Any = None,
) -> DteRun:
    """Withdraw a run the operator decided not to authorize.

    Without this the only way out of the approval queue is approving, so a scope chosen
    by mistake stays on the screen forever.
    """

    if run.status != DteRun.Status.AWAITING_APPROVAL:
        raise DteRunTransitionError("Esta consulta já saiu da fila de autorização.")

    run.status = DteRun.Status.CANCELLED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at", "updated_at"])
    run.items.filter(status=DteRunItem.Status.PENDING).update(status=DteRunItem.Status.SKIPPED)
    record_event(
        action="hub.dte.run_cancelled",
        actor=actor,
        organization=run.organization,
        target=run,
        request=request,
        metadata={"companies": run.total_companies},
    )
    return run
