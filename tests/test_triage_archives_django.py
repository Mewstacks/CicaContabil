"""AC-11.2: ZIP seguro. Limites de arquivos, tamanho, razão e profundidade; zip bomba recusado."""

from __future__ import annotations

import io
import zipfile
from typing import Any
from unittest.mock import patch

from django.utils import timezone

from apps.triage import archives
from apps.triage.archives import ArchiveRejected, read_zip_members
from apps.triage.extraction import extract_item
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import TriageItem, TriagePolicy
from apps.triage.security import scan_quarantined_item
from apps.triage.tasks import process_triage_item
from apps.triage.transitions import TriageStatus
from triage_v2_support import PDF, CleanScanner, TriageV2Case


def make_zip(entries: dict[str, bytes], *, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as package:
        for name, data in entries.items():
            package.writestr(name, data)
    return buffer.getvalue()


ALLOWED = frozenset({".pdf", ".xml", ".csv", ".ofx", ".xlsx"})


class ReadZipTests(TriageV2Case):
    def read(self, entries: dict[str, bytes], **kw: Any) -> Any:
        return read_zip_members(make_zip(entries), allowed_suffixes=ALLOWED, **kw)

    def test_accepts_supported_members_and_keeps_only_the_base_name(self) -> None:
        reading = self.read({"a.pdf": PDF, "pasta/sub/b.xml": b"<a/>"})
        self.assertEqual(sorted(m.name for m in reading.members), ["a.pdf", "b.xml"])
        folder = {m.name: m.folder for m in reading.members}
        self.assertEqual(folder["b.xml"], "pasta / sub")

    def test_junk_and_directories_are_dropped_silently(self) -> None:
        reading = self.read(
            {"__MACOSX/._a.pdf": b"x", ".DS_Store": b"x", "Thumbs.db": b"x", "a.pdf": PDF}
        )
        self.assertEqual([m.name for m in reading.members], ["a.pdf"])
        self.assertEqual(sum(reading.ignored.values()), 0)

    def test_unsafe_paths_are_ignored_not_trusted(self) -> None:
        reading = self.read(
            {"../../evil.pdf": PDF, "/abs/x.pdf": PDF, "C:\\win\\y.pdf": PDF, "ok.pdf": PDF}
        )
        self.assertEqual([m.name for m in reading.members], ["ok.pdf"])
        self.assertEqual(reading.ignored["caminho inseguro"], 3)

    def test_unsupported_and_nested_archives_are_counted_as_ignored(self) -> None:
        inner = make_zip({"i.pdf": PDF})
        reading = self.read({"a.pdf": PDF, "x.exe": b"MZ", "pacote.zip": inner})
        self.assertEqual([m.name for m in reading.members], ["a.pdf"])
        self.assertIn(".exe", reading.ignored)
        self.assertIn("pacote dentro de pacote", reading.ignored)

    def test_nothing_accepted_is_a_refusal_with_the_ignored_summary(self) -> None:
        with self.assertRaises(ArchiveRejected) as caught:
            self.read({"x.exe": b"MZ"})
        self.assertIn(".exe", str(caught.exception))

    def test_too_many_entries_is_refused(self) -> None:
        with (
            patch.object(archives, "MAX_ARCHIVE_ENTRIES", 3),
            self.assertRaises(ArchiveRejected),
        ):
            self.read({f"{i}.pdf": PDF + bytes([i]) for i in range(4)})

    def test_declared_total_above_the_cap_is_refused_before_reading(self) -> None:
        with (
            patch.object(archives, "MAX_ARCHIVE_UNCOMPRESSED", 1000),
            self.assertRaises(ArchiveRejected),
        ):
            self.read({"a.pdf": b"%PDF" + b"a" * 600, "b.pdf": b"%PDF" + b"b" * 600})

    def test_zip_bomb_by_ratio_is_refused_without_inflating(self) -> None:
        bomb = make_zip({"zeros.xml": b"0" * (8 * 1024 * 1024)})
        self.assertLess(len(bomb), 100 * 1024)
        with (
            patch.object(zipfile.ZipFile, "open", side_effect=AssertionError("inflated")),
            self.assertRaises(ArchiveRejected) as caught,
        ):
            read_zip_members(bomb, allowed_suffixes=ALLOWED)
        self.assertIn("compress", str(caught.exception).casefold())

    def test_member_above_the_member_cap_is_ignored_not_read(self) -> None:
        with patch.object(archives, "MAX_MEMBER_BYTES", 200):
            reading = self.read({"big.pdf": b"%PDF" + b"x" * 500, "ok.pdf": PDF})
        self.assertEqual([m.name for m in reading.members], ["ok.pdf"])
        self.assertIn("maior que 25 MB", reading.ignored)

    def test_declared_size_never_decides_the_real_read(self) -> None:
        class Liar:
            def __init__(self) -> None:
                self.left = 10_000

            def read(self, n: int = -1) -> bytes:
                chunk = min(self.left, n if n > 0 else self.left)
                self.left -= chunk
                return b"x" * chunk

        with self.assertRaises(ArchiveRejected):
            archives.read_bounded(Liar(), limit=100)  # type: ignore[arg-type]

    def test_corrupt_or_empty_file_is_refused(self) -> None:
        for data in (b"not a zip at all", b""):
            with self.assertRaises(ArchiveRejected):
                read_zip_members(data, allowed_suffixes=ALLOWED)

    def test_extension_follows_the_allowed_set(self) -> None:
        reading = read_zip_members(
            make_zip({"a.pdf": PDF, "f.png": b"\x89PNG"}), allowed_suffixes=ALLOWED
        )
        self.assertEqual([m.name for m in reading.members], ["a.pdf"])
        wider = read_zip_members(
            make_zip({"a.pdf": PDF, "f.png": b"\x89PNG"}),
            allowed_suffixes=ALLOWED | {".png"},
        )
        self.assertEqual(sorted(m.name for m in wider.members), ["a.pdf", "f.png"])


class ArchivePipelineTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        TriagePolicy.objects.create(organization=self.office, open_archives=True)

    def receive_zip(self, entries: dict[str, bytes], message_id: str = "zip-1") -> TriageItem:
        return receive_email_attachment(
            mailbox=self.mailbox,
            message_id=message_id,
            part_id="1",
            filename="pacote.zip",
            payload=make_zip(entries),
            sender="ana@e11-office.test",
            subject="Docs de setembro",
            body_excerpt="corpo",
            original_sender="cliente@padaria.example",
            received_at=timezone.now(),
        ).item

    def run_pipeline(self, item: TriageItem) -> None:
        with (
            patch("apps.triage.security.ClamdScanner.from_settings", return_value=CleanScanner()),
            self.captureOnCommitCallbacks(execute=True),
        ):
            process_triage_item(str(item.pk))

    def test_zip_becomes_one_item_per_file_and_the_package_closes(self) -> None:
        item = self.receive_zip({"extrato.pdf": PDF, "dados.xml": b"<a/>"})
        self.run_pipeline(item)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertEqual(item.rejection_reason, "Pacote aberto: 2 arquivos.")
        members = TriageItem.objects.filter(archive_parent=item)
        self.assertEqual(sorted(members.values_list("original_name", flat=True)),
                         ["dados.xml", "extrato.pdf"])
        for member in members:
            self.assertEqual(member.organization_id, self.office.id)
            self.assertEqual(member.mailbox_id, self.mailbox.id)
            self.assertEqual(member.origin, TriageItem.Origin.ARCHIVE)
            self.assertEqual(member.original_sender, "cliente@padaria.example")
            self.assertEqual(member.body_excerpt, "corpo")
            self.assertEqual(member.subject, "Docs de setembro")
            self.assertEqual(member.status, TriageStatus.AWAITING_REVIEW)

    def test_running_the_package_twice_never_duplicates_members(self) -> None:
        item = self.receive_zip({"extrato.pdf": PDF})
        self.run_pipeline(item)
        self.run_pipeline(item)
        self.assertEqual(TriageItem.objects.filter(archive_parent=item).count(), 1)

    def test_member_equal_to_an_earlier_file_closes_as_duplicate(self) -> None:
        first = self.released(filename="antigo.pdf", payload=PDF)
        item = self.receive_zip({"novo.pdf": PDF})
        self.run_pipeline(item)
        member = TriageItem.objects.get(archive_parent=item)
        self.assertEqual(member.status, TriageStatus.REJECTED)
        self.assertEqual(member.duplicate_of_id, first.pk)

    def test_zip_bomb_is_rejected_with_a_reason_and_creates_nothing(self) -> None:
        item = self.receive_zip({"zeros.xml": b"0" * (8 * 1024 * 1024)})
        self.run_pipeline(item)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertIn("compress", item.rejection_reason.casefold())
        self.assertFalse(TriageItem.objects.filter(archive_parent=item).exists())

    def test_package_without_accepted_files_is_rejected(self) -> None:
        item = self.receive_zip({"x.exe": b"MZ"})
        self.run_pipeline(item)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertIn(".exe", item.rejection_reason)

    def test_office_without_the_switch_rejects_the_zip_at_the_door(self) -> None:
        other = self.make_office("e11-zip-off")
        mailbox = self.make_mailbox(other)
        from apps.triage.intake_policy import decide_attachment

        decision = decide_attachment(organization=other, filename="p.zip", size=100)
        self.assertEqual(decision.action, "reject")
        self.assertEqual(mailbox.organization_id, other.id)

    def test_members_stay_in_their_own_office_and_dedupe_is_per_office(self) -> None:
        other = self.make_office("e11-zip-other")
        other_box = self.make_mailbox(other)
        self.released(filename="mesmo.pdf", payload=PDF, mailbox=other_box, message_id="o1")
        item = self.receive_zip({"mesmo.pdf": PDF})
        self.run_pipeline(item)
        member = TriageItem.objects.get(archive_parent=item)
        self.assertEqual(member.status, TriageStatus.AWAITING_REVIEW)  # not a duplicate
        self.assertEqual(member.organization_id, self.office.id)

    def test_archive_is_never_expanded_before_the_scan_releases_it(self) -> None:
        item = self.receive_zip({"extrato.pdf": PDF})
        self.assertEqual(extract_item(item_id=item.pk).status, TriageStatus.QUARANTINED)
        self.assertFalse(TriageItem.objects.filter(archive_parent=item).exists())
        scan_quarantined_item(item=item, scanner=CleanScanner())
        self.assertEqual(TriageItem.objects.get(pk=item.pk).status,
                         TriageStatus.AWAITING_EXTRACTION)
