"""Stream the NFS-e of a HubFedrizzi bundle straight into ``NfseDocument``.

Two sources: the Postgres table ``robo_nfse_notanfse`` and the Mongo dump ``mongo_nfse``. Neither
is stored verbatim: the XML lands once, encrypted, in the native evidence row, and the rest of
the legacy fields travel inside ``normalized_data["legacy"]``. Work is committed in small
batches (a failure keeps what is done, a re-run skips it) and nothing but one batch is ever
held in memory. ``measure_only`` reads the same stream and writes nothing, to size the storage
before the owner decides.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.hub.legacy_convert import SYSTEM, mapped_ids
from apps.hub.legacy_import import Bundle
from apps.hub.models import ClientCompany, LegacyImportRecord, NfseDocument
from apps.hub.nfse_adn import AdnDocument, AdnPayloadError
from apps.hub.nfse_sync import normalize_adn_document
from apps.hub.services import _issued_at_from_normalized_data
from apps.organizations.models import Organization

BATCH = 200
# EncryptedTextField stores a Fernet token (base64 of ciphertext + 57 bytes of framing).
ENCRYPTED_FACTOR = 1.4
SOURCES = {
    "robo": ("robo_nfse_notanfse", "tables/robo_nfse_notanfse.jsonl"),
    "mongo": ("mongo_nfse", "mongo_nfse.jsonl"),
}


@dataclass
class NfseDocsReport:
    read: Counter[str] = field(default_factory=Counter)
    created: Counter[str] = field(default_factory=Counter)
    existing: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    xml_bytes: Counter[str] = field(default_factory=Counter)
    measure_only: bool = False

    def lines(self) -> list[str]:
        out = []
        for source in sorted(self.read):
            out.append(
                f"nfse {source}: lidas={self.read[source]} novas={self.created[source]} "
                f"já existiam={self.existing[source]} "
                f"xml_novo={self.xml_bytes[source] / 1_048_576:.1f} MB"
            )
        for reason, count in sorted(self.skipped.items()):
            out.append(f"nfse sem nativo: {count}x {reason}")
        new_bytes = sum(self.xml_bytes.values())
        out.append(
            "armazenamento estimado das notas novas no Neon: "
            f"{new_bytes * ENCRYPTED_FACTOR / 1_048_576:.1f} MB "
            f"(XML {new_bytes / 1_048_576:.1f} MB x {ENCRYPTED_FACTOR} da criptografia, "
            "sem índices)"
        )
        if self.measure_only:
            out.append("medição: nada foi gravado")
        return out


def _xml_text(blob: Any) -> str:
    """The exporter wraps bytes as ``{"__b64__": ...}``; plain strings pass through."""

    if isinstance(blob, dict) and "__b64__" in blob:
        try:
            return base64.b64decode(blob["__b64__"]).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return ""
    return blob if isinstance(blob, str) else ""


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _robo_keys(organization: Organization) -> set[str]:
    return {
        key
        for key in LegacyImportRecord.objects.filter(
            organization=organization, source_system=SYSTEM, source_table="robo_nfse_notanfse"
        ).values_list("payload__chave_acesso", flat=True)
        if key
    }


def _prepare(row: dict[str, Any], source: str, company_of: Any) -> dict[str, Any] | None:
    """One legacy row → keyword arguments of a document, or ``None`` when it cannot be placed."""

    xml = _xml_text(row.get("xml") if source == "robo" else row.get("xml_content"))
    company_pk = company_of(row)
    if not xml:
        return {"skip": "sem XML"}
    if company_pk is None:
        return {"skip": "empresa sem nativa"}
    key = str(row.get("chave_acesso") or "")
    nsu = "" if source == "robo" else str(row.get("nsu") or "")
    return {
        "company_pk": company_pk,
        "xml": xml,
        "key": key,
        "nsu": nsu,
        "legacy": {
            "source": source,
            "tipo": row.get("tipo"),
            "situacao": row.get("situacao"),
            "cancelada": bool(row.get("cancelada")),
            "baixada_em": row.get("baixada_em") or row.get("created_at"),
        },
    }


def _flush(
    organization: Organization,
    batch: list[dict[str, Any]],
    source: str,
    cnpj_of: dict[str, str],
    report: NfseDocsReport,
) -> None:
    hashes = {item["hash"] for item in batch}
    nsus = {item["nsu"] for item in batch if item["nsu"]}
    have = set(
        NfseDocument.objects.filter(
            organization=organization, document_hash__in=hashes
        ).values_list("company_id", "document_hash")
    )
    taken = (
        set(
            NfseDocument.objects.filter(organization=organization, source_nsu__in=nsus).values_list(
                "company_id", "source_nsu"
            )
        )
        if nsus
        else set()
    )
    fresh: list[dict[str, Any]] = []
    for item in batch:
        marker = (item["company_pk"], item["hash"])
        if marker in have:
            report.existing[source] += 1
            continue
        have.add(marker)
        fresh.append(item)
    if report.measure_only:
        for item in fresh:
            report.created[source] += 1
            report.xml_bytes[source] += len(item["xml"].encode("utf-8"))
        return
    with transaction.atomic():
        for item in fresh:
            try:
                data = normalize_adn_document(
                    AdnDocument(
                        nsu=int(item["nsu"] or 0),
                        xml=item["xml"],
                        access_key=item["key"],
                        document_type="NFSe",
                    ),
                    company_cnpj=cnpj_of.get(str(item["company_pk"]), ""),
                )
            except AdnPayloadError:
                report.skipped["XML malformado"] += 1
                continue
            nsu = item["nsu"]
            if nsu and (item["company_pk"], nsu) in taken:
                nsu = ""
            if nsu:
                taken.add((item["company_pk"], nsu))
            data.update({"source": "hubfedrizzi", "nsu": nsu, "legacy": item["legacy"]})
            try:
                issued = _issued_at_from_normalized_data(data)
            except (ValueError, TypeError):
                issued = None
            NfseDocument(
                organization=organization,
                company_id=item["company_pk"],
                source_nsu=nsu,
                document_hash=item["hash"],
                original_xml=item["xml"],
                normalized_data=data,
                issued_at=issued,
            ).save()
            report.created[source] += 1
            report.xml_bytes[source] += len(item["xml"].encode("utf-8"))


def import_nfse_documents(
    *,
    organization: Organization,
    path: Path,
    sources: tuple[str, ...] = ("robo", "mongo"),
    measure_only: bool = False,
    limit: int | None = None,
    offset: int = 0,
    batch_size: int = BATCH,
) -> NfseDocsReport:
    bundle = Bundle(path)
    report = NfseDocsReport(measure_only=measure_only)
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    cnpj_of: dict[str, str] = {}
    by_cnpj: dict[str, UUID] = {}
    for pk, masked in ClientCompany.objects.filter(
        organization=organization, pk__in=list(companies.values())
    ).values_list("pk", "cnpj_masked"):
        cnpj_of[str(pk)] = masked
        digits = "".join(ch for ch in masked if ch.isdigit())
        if digits:
            by_cnpj[digits] = pk
    bundle.verify()  # raises BundleError on a changed or truncated member
    seen: set[str] = set()
    if (
        "robo" not in sources
        and NfseDocument.objects.filter(
            organization=organization, normalized_data__legacy__source="robo"
        ).exists()
    ):
        seen = _robo_keys(organization)

    def company_of_robo(row: dict[str, Any]) -> UUID | None:
        return companies.get(str(row.get("empresa_id")))

    def company_of_mongo(row: dict[str, Any]) -> UUID | None:
        return by_cnpj.get(_digits(row.get("cnpj")))

    for source in sources:
        _table, member = SOURCES[source]
        company_of = company_of_robo if source == "robo" else company_of_mongo
        if source == "mongo":
            info = bundle.manifest.get("mongo_nfse", {})
            if info.get("status") != "ok" or not info.get("rows"):
                report.skipped["mongo_nfse ausente no pacote (use o pacote completo)"] += 1
                continue
        batch: list[dict[str, Any]] = []
        position = 0
        for item in bundle.rows(member):
            row = item["row"]
            position += 1
            if position <= offset:
                continue  # earlier slice: a cheap skip, nothing is decoded
            if limit is not None and report.read[source] >= limit:
                break
            report.read[source] += 1
            prepared = _prepare(row, source, company_of)
            if prepared is None or "skip" in prepared:
                report.skipped[(prepared or {}).get("skip", "linha ilegível")] += 1
                continue
            if source == "mongo" and prepared["key"] and prepared["key"] in seen:
                report.existing[source] += 1  # same note already came from the robot table
                continue
            if source == "robo" and prepared["key"]:
                seen.add(prepared["key"])
            prepared["hash"] = hashlib.sha256(prepared["xml"].encode()).hexdigest()
            batch.append(prepared)
            if len(batch) >= batch_size:
                _flush(organization, batch, source, cnpj_of, report)
                batch = []
        if batch:
            _flush(organization, batch, source, cnpj_of, report)
    return report
