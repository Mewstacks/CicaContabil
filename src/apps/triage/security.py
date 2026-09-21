"""Fail-closed antimalware gate for quarantined email attachments.

ClamAV is a candidate local engine, not an activated product dependency. A configured
local socket or loopback TCP daemon is required before the adapter can scan bytes.
Clean antimalware alone does not release a file: signature/format policy is separate.
"""

from __future__ import annotations

import hashlib
import socket
import struct
from dataclasses import dataclass
from typing import BinaryIO, Protocol, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.triage.file_policy import UnsupportedAttachment, validate_supported_attachment
from apps.triage.models import TriageEvent, TriageItem, TriageSafetyScan
from apps.triage.transitions import TriageStatus


class ScannerUnavailable(ValueError):
    """A clean result cannot be established; keep the file quarantined."""


@dataclass(frozen=True)
class ScanVerdict:
    verdict: str
    engine: str
    note: str = ""


class Scanner(Protocol):
    def scan(self, stream: BinaryIO) -> ScanVerdict: ...


class ClamdScanner:
    """Stream a private file to a local ClamAV daemon with zINSTREAM framing."""

    def __init__(self, *, local_socket: str = "", loopback_port: int = 0) -> None:
        if bool(local_socket) == bool(loopback_port):
            raise ScannerUnavailable("Configure um único socket local para o antimalware.")
        if loopback_port and not 1 <= loopback_port <= 65535:
            raise ScannerUnavailable("A porta local do antimalware está inválida.")
        self.local_socket = local_socket
        self.loopback_port = loopback_port

    @classmethod
    def from_settings(cls) -> ClamdScanner:
        return cls(
            local_socket=getattr(settings, "TRIAGE_CLAMD_SOCKET", ""),
            loopback_port=getattr(settings, "TRIAGE_CLAMD_PORT", 0),
        )

    def _connect(self) -> socket.socket:
        try:
            if self.local_socket:
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.settimeout(10)
                connection.connect(self.local_socket)
                return connection
            return socket.create_connection(("127.0.0.1", self.loopback_port), timeout=10)
        except (OSError, TimeoutError) as exc:
            raise ScannerUnavailable(
                "O antimalware local está indisponível. O anexo continua em quarentena."
            ) from exc

    def scan(self, stream: BinaryIO) -> ScanVerdict:
        try:
            with self._connect() as connection:
                connection.sendall(b"zINSTREAM\0")
                while chunk := stream.read(64 * 1024):
                    connection.sendall(struct.pack(">I", len(chunk)))
                    connection.sendall(chunk)
                connection.sendall(struct.pack(">I", 0))
                reply = bytearray()
                while len(reply) < 2048:
                    fragment = connection.recv(min(2048 - len(reply), 512))
                    if not fragment:
                        break
                    reply.extend(fragment)
                    if b"\0" in reply:
                        break
        except (OSError, TimeoutError) as exc:
            raise ScannerUnavailable(
                "A varredura antimalware falhou. O anexo continua em quarentena."
            ) from exc
        if b"\0" not in reply:
            raise ScannerUnavailable("O antimalware não confirmou a varredura completa.")
        record = bytes(reply).split(b"\0", 1)[0]
        if record == b"stream: OK":
            return ScanVerdict(TriageSafetyScan.Verdict.CLEAN, "clamav")
        if record.startswith(b"stream: ") and record.endswith(b" FOUND"):
            return ScanVerdict(TriageSafetyScan.Verdict.INFECTED, "clamav")
        raise ScannerUnavailable("O antimalware retornou erro. O anexo continua em quarentena.")


def scan_quarantined_item(*, item: TriageItem, scanner: Scanner | None = None) -> TriageSafetyScan:
    """Save a durable verdict for the exact bytes, rejecting confirmed malware."""
    with transaction.atomic():
        item = TriageItem.objects.select_for_update().select_related("blob").get(
            id=item.id, organization=item.organization
        )
        if item.status != TriageStatus.QUARANTINED:
            raise ValidationError("Somente anexos em quarentena podem ser varridos.")
        if not item.content_hash or not hasattr(item, "blob"):
            raise ValidationError("O anexo não tem arquivo e hash íntegros para varredura.")
        digest = hashlib.sha256()
        with item.blob.content.open("rb") as stream:
            while chunk := stream.read(64 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != item.content_hash:
            raise ValidationError("O hash do anexo mudou. Mantenha a quarentena e investigue.")
        try:
            scanner = scanner or ClamdScanner.from_settings()
            with item.blob.content.open("rb") as stream:
                result = scanner.scan(cast(BinaryIO, stream))
        except ScannerUnavailable as exc:
            result = ScanVerdict(TriageSafetyScan.Verdict.ERROR, "", str(exc)[:200])
        if result.verdict not in TriageSafetyScan.Verdict.values:
            raise ValidationError("O scanner retornou um resultado inválido.")
        format_verdict = TriageSafetyScan.FormatVerdict.PENDING
        format_note = ""
        detected_type = ""
        if result.verdict == TriageSafetyScan.Verdict.CLEAN:
            try:
                with item.blob.content.open("rb") as stream:
                    detected_type = validate_supported_attachment(
                        cast(BinaryIO, stream), filename=item.original_name
                    )
                format_verdict = TriageSafetyScan.FormatVerdict.VALID
            except UnsupportedAttachment as exc:
                format_verdict = TriageSafetyScan.FormatVerdict.INVALID
                format_note = str(exc)[:200]
        verdict, _ = TriageSafetyScan.objects.update_or_create(
            organization=item.organization,
            triage_item=item,
            defaults={
                "engine": result.engine[:40],
                "verdict": result.verdict,
                "content_hash": item.content_hash,
                "scanned_at": timezone.now(),
                "note": result.note[:200],
                "format_verdict": format_verdict,
                "format_note": format_note,
            },
        )
        if result.verdict == TriageSafetyScan.Verdict.INFECTED:
            previous = item.status
            item.transition_to(TriageStatus.REJECTED)
            item.rejection_reason = "Ameaça detectada na varredura antimalware."
            item.save(update_fields=["status", "rejection_reason", "updated_at"])
            TriageEvent.objects.create(
                organization=item.organization,
                triage_item=item,
                actor=None,
                from_status=previous,
                to_status=item.status,
                note="Antimalware detectou ameaça; anexo rejeitado",
            )
        elif format_verdict == TriageSafetyScan.FormatVerdict.VALID:
            previous = item.status
            item.transition_to(TriageStatus.AWAITING_EXTRACTION)
            item.detected_type = detected_type
            item.save(update_fields=["status", "detected_type", "updated_at"])
            TriageEvent.objects.create(
                organization=item.organization,
                triage_item=item,
                actor=None,
                from_status=previous,
                to_status=item.status,
                note="Antimalware sem detecção e formato validado; aguardando extração",
            )
        else:
            TriageEvent.objects.create(
                organization=item.organization,
                triage_item=item,
                actor=None,
                from_status=item.status,
                to_status=item.status,
                note=(
                    "Formato recusado; anexo permanece em quarentena"
                    if format_verdict == TriageSafetyScan.FormatVerdict.INVALID
                    else "Varredura falhou; anexo permanece em quarentena"
                ),
            )
    record_event(
        action="triage.item.antimalware_scan",
        actor=None,
        organization=item.organization,
        target=item,
        metadata={"verdict": verdict.verdict, "engine": verdict.engine},
    )
    return verdict
