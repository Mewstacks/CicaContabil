"""Put the files of a HubFedrizzi bundle into the CICA storage and tie each to its native row.

Only files whose native owner already exists are stored: receipts (``ClosingDocument.file``) and
FAP reports (``RpaArtifact`` behind ``FapItem.pdf``). Every file is read from the zip, checked
against the manifest hash AND the hash the legacy row recorded, then saved through the
configured private storage. A second run skips what is already attached.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile

from apps.closing.models import ClosingDocument
from apps.fap.models import FapItem
from apps.hub.legacy_convert import SYSTEM, _records
from apps.hub.legacy_import import Bundle
from apps.hub.models import LegacyImportRecord
from apps.organizations.models import Organization
from apps.rpa.models import RpaArtifact, RpaJob

FAP_JOB_KIND = "legacy.fap.import"
# Files with no native owner today, by folder of the legacy MEDIA_ROOT.
NO_HOME = {
    "triagem/": "binário de item de triagem (os itens não foram importados)",
    "mapeamentos/": "amostra de layout (o texto já está em ClosingLayout.sample_text)",
    "admissoes/": "admissões de teste não migradas",
    "guias/": "guia da conferência (sem campo de arquivo)",
}


@dataclass
class FilesReport:
    in_bundle: int = 0
    stored: Counter[str] = field(default_factory=Counter)
    existing: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    no_home: Counter[str] = field(default_factory=Counter)
    stored_bytes: int = 0
    dry_run: bool = False

    def lines(self) -> list[str]:
        out = [f"arquivos no pacote: {self.in_bundle}"]
        for kind in sorted(set(self.stored) | set(self.existing)):
            out.append(
                f"arquivos {kind}: gravados={self.stored[kind]} já ligados={self.existing[kind]}"
            )
        for reason, count in sorted(self.skipped.items()):
            out.append(f"arquivos pulados: {count}x {reason}")
        for reason, count in sorted(self.no_home.items()):
            out.append(f"arquivos sem destino: {count}x {reason}")
        attached = sum(self.stored.values()) + sum(self.existing.values())
        left = sum(self.skipped.values()) + sum(self.no_home.values())
        out.append(
            f"paridade arquivos: pacote={self.in_bundle} ligados={attached} "
            f"sem destino ou pulados={left} bytes gravados={self.stored_bytes}"
        )
        if self.dry_run:
            out.append("simulação: nada foi gravado")
        return out


def _read_checked(
    bundle: Bundle, items: dict[str, Any], path: str, expected: str, report: FilesReport
) -> bytes | None:
    info = items.get(path)
    if info is None:
        report.skipped["arquivo fora do pacote"] += 1
        return None
    data = bundle.read_bytes(f"files/{path}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != info.get("sha256") or (expected and digest != expected):
        report.skipped["hash diferente do manifesto ou do registro"] += 1
        return None
    return data


def _receipts(
    organization: Organization,
    bundle: Bundle,
    items: dict[str, Any],
    claimed: set[str],
    report: FilesReport,
    dry_run: bool,
) -> None:
    done: set[str] = set()
    for record in _records(organization, "fechamento_recibo"):
        path = str(record.payload.get("arquivo") or "")
        if path:
            claimed.add(path)
        if not record.mapped_to.startswith("closing.ClosingDocument:") or not path:
            continue
        document_pk = record.mapped_to.split(":", 1)[1]
        if document_pk in done:
            continue
        done.add(document_pk)
        document = ClosingDocument.objects.filter(pk=document_pk).first()
        if document is None:
            report.skipped["documento nativo ausente"] += 1
        elif document.file:
            report.existing["recibos"] += 1
        else:
            data = _read_checked(bundle, items, path, document.content_hash, report)
            if data is None:
                continue
            if not dry_run:
                document.file.save(f"{document.pk}.bin", ContentFile(data), save=False)
                document.byte_size = len(data)
                document.save(update_fields=["file", "byte_size", "updated_at"])
            report.stored["recibos"] += 1
            report.stored_bytes += len(data)


def _fap_job(organization: Organization, item: FapItem) -> RpaJob:
    job, _ = RpaJob.objects.get_or_create(
        organization=organization,
        kind=FAP_JOB_KIND,
        idempotency_key=f"hubfedrizzi:fap-batch:{item.batch_id}",
        defaults={
            "state": RpaJob.State.SUCCEEDED,
            "payload": {"source": "hubfedrizzi"},
            "phase": "importado",
        },
    )
    return job


def _fap(
    organization: Organization,
    bundle: Bundle,
    items: dict[str, Any],
    claimed: set[str],
    report: FilesReport,
    dry_run: bool,
) -> None:
    for record in _records(organization, "fap_itemfap"):
        path = str(record.payload.get("pdf") or "")
        if path:
            claimed.add(path)
        if not record.mapped_to.startswith("fap.FapItem:") or not path:
            continue
        item = FapItem.objects.filter(pk=record.mapped_to.split(":", 1)[1]).first()
        if item is None:
            report.skipped["item FAP nativo ausente"] += 1
        elif item.pdf_id is not None:
            report.existing["FAP"] += 1
        else:
            data = _read_checked(
                bundle, items, path, str(record.payload.get("sha256_pdf") or ""), report
            )
            if data is None:
                continue
            if not dry_run:
                job = _fap_job(organization, item)
                digest = hashlib.sha256(data).hexdigest()
                artifact = RpaArtifact.objects.filter(job=job, sha256=digest).first()
                if artifact is None:
                    artifact = RpaArtifact(
                        organization=organization,
                        job=job,
                        name=f"FAP-{item.year}-{item.code}.pdf"[:200],
                        sha256=digest,
                        byte_size=len(data),
                        content_type="application/pdf",
                    )
                    artifact.file.save(f"{digest}.bin", ContentFile(data), save=False)
                    artifact.save()
                item.pdf = artifact
                if not item.sha256:
                    item.sha256 = digest
                item.save(update_fields=["pdf", "sha256", "updated_at"])
            report.stored["FAP"] += 1
            report.stored_bytes += len(data)


def import_files(*, organization: Organization, path: Path, dry_run: bool = False) -> FilesReport:
    bundle = Bundle(path)
    items: dict[str, Any] = bundle.manifest.get("files", {}).get("items", {})
    report = FilesReport(in_bundle=len(items), dry_run=dry_run)
    claimed: set[str] = set()
    if not LegacyImportRecord.objects.filter(
        organization=organization, source_system=SYSTEM
    ).exists():
        report.skipped["importe o pacote antes (sem registros do HubFedrizzi)"] += len(items)
        return report
    _receipts(organization, bundle, items, claimed, report, dry_run)
    _fap(organization, bundle, items, claimed, report, dry_run)
    for name in items:
        if name in claimed:
            continue
        reason = next((why for prefix, why in NO_HOME.items() if name.startswith(prefix)), None)
        report.no_home[reason or "sem dono nativo"] += 1
    return report
