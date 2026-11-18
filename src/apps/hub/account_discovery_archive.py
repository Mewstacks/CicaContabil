"""Bounded ZIP/JSONL ingestion with private, disk-backed catalogue staging."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import struct
import tempfile
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from apps.hub import account_discovery_contract as contract
from apps.hub import account_source_contract as details

ZIP_LIMIT = 128 * 1024 * 1024
MANIFEST_LIMIT = 8 * 1024 * 1024
TOTAL_LIMIT = 1024 * 1024 * 1024
LINE_LIMIT = 1024 * 1024
BLOCK_LIMIT = 256 * 1024
TABLES = {
    "chart_accounts": ("chart-accounts.jsonl", 1_000_000, 512 * 1024 * 1024),
    "plan_template_accounts": ("plan-template-accounts.jsonl", 1_000_000, 512 * 1024 * 1024),
    "nature_rules": ("nature-rules.jsonl", 100_000, 32 * 1024 * 1024),
}
NATURE_FIELDS = {
    "chart_company_code",
    "rule_order",
    "classification_raw",
    "nature_raw",
    "group_raw",
}


def needs_storage_codec(value: Any) -> bool:
    if isinstance(value, str):
        return "\0" in value
    if isinstance(value, dict):
        return any(needs_storage_codec(item) for item in value.values())
    if isinstance(value, list):
        return any(needs_storage_codec(item) for item in value)
    return False


def _json(raw: bytes) -> Any:
    contract.require(not raw.startswith(b"\xef\xbb\xbf"), "UTF8_BOM")
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=details.pairs,
        parse_constant=details.reject_constant,
    )


def validate_table_row(table: str, row: Any, owners: set[int]) -> tuple[int, ...]:
    if table == "nature_rules":
        contract.keys(row, NATURE_FIELDS)
        contract.integer(row["chart_company_code"], positive=True)
        contract.integer(row["rule_order"])
        contract.require(row["rule_order"] <= 255, "NATURE_SCOPE")
        for field, length in (("classification_raw", 20), ("nature_raw", 1), ("group_raw", 1)):
            contract.text(row[field], length)
        key = (row["chart_company_code"], row["rule_order"], 0)
    else:
        contract.validate_chart_row(row, template=table == "plan_template_accounts")
        key = (row["chart_company_code"], row.get("plan_id_raw", 0), row["account_code"])
    contract.require(row["chart_company_code"] in owners, "CATALOGUE_SCOPE")
    return key


def decompress_block(payload: bytes, expected_size: int) -> bytes:
    """A corrupt block cannot inflate beyond the fixed per-block memory budget."""
    contract.require(type(expected_size) is int and 0 < expected_size <= BLOCK_LIMIT, "BLOCK_SIZE")
    contract.require(len(payload) <= BLOCK_LIMIT + 1024, "COMPRESSED_BLOCK_SIZE")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(payload, expected_size + 1)
    contract.require(
        len(raw) == expected_size
        and decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail,
        "BLOCK_ENCODING",
    )
    return raw


def _verify_zip_entry(path: Path, entry: zipfile.ZipInfo, central_offset: int) -> None:
    """Check real DEFLATE output: ZipExtFile alone clips output to the advertised size."""
    with path.open("rb") as source:
        source.seek(entry.header_offset)
        header = source.read(30)
        contract.require(len(header) == 30, "ZIP_LOCAL_HEADER")
        values = struct.unpack("<4s5H3L2H", header)
        contract.require(
            values[0] == b"PK\x03\x04"
            and values[2] == entry.flag_bits
            and values[3] == entry.compress_type,
            "ZIP_LOCAL_HEADER",
        )
        offset = entry.header_offset + 30 + values[-2] + values[-1]
        contract.require(
            offset + entry.compress_size <= central_offset and entry.compress_size <= ZIP_LIMIT,
            "ZIP_COMPRESSED_SIZE",
        )
        source.seek(offset)
        left, size, crc = entry.compress_size, 0, 0
        decoder = zlib.decompressobj(-15) if entry.compress_type == zipfile.ZIP_DEFLATED else None

        def check(raw: bytes) -> None:
            nonlocal size, crc
            size += len(raw)
            contract.require(size <= entry.file_size, "ZIP_ACTUAL_SIZE")
            crc = zlib.crc32(raw, crc)

        while left:
            chunk = source.read(min(left, 64 * 1024))
            contract.require(bool(chunk), "ZIP_TRUNCATED")
            left -= len(chunk)
            if decoder is None:
                check(chunk)
            else:
                while chunk:
                    check(decoder.decompress(chunk, 64 * 1024))
                    contract.require(not decoder.unused_data, "ZIP_COMPRESSED_TRAILING")
                    chunk = decoder.unconsumed_tail
        contract.require(size == entry.file_size and crc == entry.CRC, "ZIP_ACTUAL_SIZE_CRC")
        contract.require(decoder is None or decoder.eof, "ZIP_INCOMPLETE_DEFLATE")


class DiscoveryStage:
    """Owns all temporary private files; no source names/identifiers enter diagnostics."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="cica-discovery-")
        self.directory = Path(self._temporary.name)
        os.chmod(self.directory, 0o700)
        path = self.directory / "staging.sqlite3"
        path.touch(mode=0o600)
        self.database = sqlite3.connect(path)
        self.database.execute("PRAGMA journal_mode=OFF")
        self.database.execute("PRAGMA synchronous=OFF")
        self.database.execute("PRAGMA temp_store=FILE")
        self.database.execute("PRAGMA cache_size=-2048")
        self.database.execute("PRAGMA mmap_size=0")
        self.database.execute(
            "CREATE TABLE records (kind TEXT, owner INTEGER, subkey INTEGER, code INTEGER, "
            "row TEXT NOT NULL, sha TEXT NOT NULL, "
            "PRIMARY KEY(kind,owner,subkey,code)) WITHOUT ROWID"
        )
        self.database.execute(
            "CREATE TABLE blocks (kind TEXT, ordinal INTEGER, rows INTEGER, size INTEGER, "
            "sha TEXT, payload BLOB, PRIMARY KEY(kind,ordinal)) WITHOUT ROWID"
        )
        self.data: dict[str, Any] = {}
        self.descriptors: dict[str, dict[str, Any]] = {}
        self.has_nul = False

    def __enter__(self) -> DiscoveryStage:
        return self

    def __exit__(self, *args: Any) -> None:
        self.database.close()
        self._temporary.cleanup()

    def load(
        self,
        source: bytes | str | Path | BinaryIO,
        *,
        expected_sha256: str,
        expected_size_bytes: int,
        companies: set[int],
        portfolio_sha256: str,
    ) -> None:
        contract.require(
            type(expected_size_bytes) is int and 2 <= expected_size_bytes <= ZIP_LIMIT,
            "FILE_SIZE",
        )
        contract.require(
            isinstance(expected_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
            "FILE_HASH",
        )
        # Hash and copy the same bytes once into a private snapshot; path changes after
        # preview cannot race the bytes read by ZIP or the descriptor validation.
        pinned = self.directory / "source.bin"
        checksum, total = hashlib.sha256(), 0
        with ExitStack() as stack:
            if isinstance(source, bytes):
                stream: BinaryIO = stack.enter_context(io.BytesIO(source))
            elif isinstance(source, (str, Path)):
                stream = stack.enter_context(Path(source).open("rb"))
            else:
                stream = source
            with pinned.open("xb") as target:
                os.chmod(pinned, 0o600)
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    contract.require(total <= expected_size_bytes, "FILE_SIZE")
                    checksum.update(chunk)
                    target.write(chunk)
        contract.require(total == expected_size_bytes, "FILE_SIZE")
        contract.require(checksum.hexdigest() == expected_sha256, "FILE_HASH")
        try:
            if zipfile.is_zipfile(pinned):
                self._load_zip(pinned, companies, portfolio_sha256)
            else:
                # Compatibility for existing small v1 fixtures/receipts only. The new
                # production CLI does not read a full large JSON into memory.
                contract.require(total <= MANIFEST_LIMIT, "LEGACY_FILE_SIZE")
                self.data = contract.decode_discovery(
                    pinned.read_bytes(),
                    expected_sha256=expected_sha256,
                    expected_size_bytes=expected_size_bytes,
                    companies=companies,
                    portfolio_sha256=portfolio_sha256,
                )
                owners = {
                    row["chart_company_code"] for row in self.data["snapshot"]["chart_owners"]
                }
                for name in TABLES:
                    self._table(
                        name,
                        (
                            details.canonical(row).encode() + b"\n"
                            for row in self.data["snapshot"][name]
                        ),
                        owners,
                    )
                    self.data["snapshot"][name] = self.descriptors[name]
            self.has_nul |= needs_storage_codec(self.data)
            self._configured_consistency()
            self.database.commit()
        except (
            UnicodeError,
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
            OverflowError,
            zipfile.BadZipFile,
            RuntimeError,
            sqlite3.IntegrityError,
            zlib.error,
        ):
            raise contract.Invalid("INVALID_DISCOVERY_ARCHIVE") from None

    def _load_zip(self, path: Path, companies: set[int], portfolio_sha256: str) -> None:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            expected = {"manifest.json", *(value[0] for value in TABLES.values())}
            contract.require(
                len(entries) == 4 and {entry.filename for entry in entries} == expected,
                "ZIP_ENTRIES",
            )
            contract.require(sum(entry.file_size for entry in entries) <= TOTAL_LIMIT, "ZIP_TOTAL")
            limits = {"manifest.json": MANIFEST_LIMIT, **{v[0]: v[2] for v in TABLES.values()}}
            for entry in entries:
                contract.require(
                    0 <= entry.file_size <= limits[entry.filename]
                    and not entry.is_dir()
                    and not entry.flag_bits & 1
                    and not stat.S_ISLNK(entry.external_attr >> 16)
                    and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    "ZIP_ENTRY_CONTRACT",
                )
                _verify_zip_entry(path, entry, archive.start_dir)
            with archive.open("manifest.json") as stream:
                raw = stream.read(MANIFEST_LIMIT + 1)
            contract.require(len(raw) <= MANIFEST_LIMIT, "MANIFEST_SIZE")
            self.data = contract.validate(_json(raw), companies, portfolio_sha256, streaming=True)
            contract.require(
                datetime.fromisoformat(self.data["observed_at_utc"].replace("Z", "+00:00"))
                <= datetime.now(UTC),
                "OBSERVED_IN_FUTURE",
            )
            owners = {row["chart_company_code"] for row in self.data["snapshot"]["chart_owners"]}
            for name, (filename, row_limit, byte_limit) in TABLES.items():
                descriptor = self.data["snapshot"][name]
                contract.keys(descriptor, {"file", "rows", "bytes", "sha256"})
                contract.require(
                    descriptor["file"] == filename
                    and type(descriptor["rows"]) is int
                    and 0 <= descriptor["rows"] <= row_limit
                    and type(descriptor["bytes"]) is int
                    and 0 <= descriptor["bytes"] <= byte_limit
                    and descriptor["bytes"] == archive.getinfo(filename).file_size
                    and isinstance(descriptor["sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]),
                    "TABLE_DESCRIPTOR",
                )
                with archive.open(filename) as stream:
                    self._table(name, iter(lambda: stream.readline(LINE_LIMIT + 1), b""), owners)
                contract.require(descriptor == self.descriptors[name], "TABLE_CONTENT")

    def _table(self, name: str, lines: Iterator[bytes], owners: set[int]) -> None:
        filename, row_limit, byte_limit = TABLES[name]
        checksum, count, size = hashlib.sha256(), 0, 0
        block, block_rows, ordinal = bytearray(), 0, 0

        def save_block() -> None:
            nonlocal block, block_rows, ordinal
            if not block:
                return
            self.database.execute(
                "INSERT INTO blocks VALUES (?,?,?,?,?,?)",
                (
                    name,
                    ordinal,
                    block_rows,
                    len(block),
                    hashlib.sha256(block).hexdigest(),
                    zlib.compress(block),
                ),
            )
            block, block_rows, ordinal = bytearray(), 0, ordinal + 1

        for line in lines:
            count, size = count + 1, size + len(line)
            contract.require(count <= row_limit and size <= byte_limit, "TABLE_LIMIT")
            contract.require(
                len(line) <= LINE_LIMIT
                and line.endswith(b"\n")
                and not line.endswith(b"\r\n")
                and line != b"\n",
                "JSONL_LINE",
            )
            row = _json(line)
            owner, subkey, code = validate_table_row(name, row, owners)
            self.has_nul |= needs_storage_codec(row)
            canonical = details.canonical(row)
            self.database.execute(
                "INSERT INTO records VALUES (?,?,?,?,?,?)",
                (
                    name,
                    owner,
                    subkey,
                    code,
                    canonical,
                    hashlib.sha256(canonical.encode()).hexdigest(),
                ),
            )
            checksum.update(line)
            if name != "chart_accounts":
                contract.require(len(line) <= BLOCK_LIMIT, "SOURCE_ROW_SIZE")
                if block and len(block) + len(line) > BLOCK_LIMIT:
                    save_block()
                block.extend(line)
                block_rows += 1
        save_block()
        self.descriptors[name] = dict(
            file=filename, rows=count, bytes=size, sha256=checksum.hexdigest()
        )

    def _configured_consistency(self) -> None:
        for configured in self.data["snapshot"]["configured_accounts"]:
            found = self.database.execute(
                "SELECT row FROM records WHERE kind='chart_accounts' "
                "AND owner=? AND subkey=0 AND code=?",
                (configured["chart_company_code"], configured["account_code"]),
            ).fetchone()
            contract.require(
                bool(found) == (configured["catalogue_matches"] == 1), "CONFIGURED_CATALOGUE_DRIFT"
            )
            if found:
                chart = json.loads(found[0])
                contract.require(
                    all(chart[field] == configured[field] for field in contract.CHART_FIELDS),
                    "CONFIGURED_CATALOGUE_DRIFT",
                )

    def chart_rows(self) -> Iterator[tuple[dict[str, Any], str]]:
        cursor = self.database.execute(
            "SELECT row,sha FROM records WHERE kind='chart_accounts' ORDER BY owner,subkey,code"
        )
        for raw, sha in cursor:
            yield json.loads(raw), sha

    def chart_counts(self) -> dict[int, int]:
        return dict(
            self.database.execute(
                "SELECT owner,COUNT(*) FROM records WHERE kind='chart_accounts' GROUP BY owner"
            )
        )

    def chart_digest(self) -> str:
        checksum = hashlib.sha256(b"[")
        for index, (raw,) in enumerate(
            self.database.execute(
                "SELECT row FROM records WHERE kind='chart_accounts' ORDER BY owner,subkey,code"
            )
        ):
            if index:
                checksum.update(b",")
            checksum.update(raw.encode())
        checksum.update(b"]")
        return checksum.hexdigest()

    def source_blocks(self) -> Iterator[dict[str, Any]]:
        for kind, ordinal, rows, size, sha, payload in self.database.execute(
            "SELECT kind,ordinal,rows,size,sha,payload FROM blocks ORDER BY kind,ordinal"
        ):
            yield dict(
                table_name=kind,
                ordinal=ordinal,
                row_count=rows,
                raw_size_bytes=size,
                raw_sha256=sha,
                compressed_data=payload,
            )

    def block_manifest(self) -> dict[str, Any]:
        result = {}
        for name in ("plan_template_accounts", "nature_rules"):
            count = self.database.execute(
                "SELECT COUNT(*) FROM blocks WHERE kind=?", (name,)
            ).fetchone()[0]
            result[name] = {**self.descriptors[name], "blocks": count}
        return result
