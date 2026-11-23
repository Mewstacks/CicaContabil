"""Safe reading of ZIP packages: nothing touches the disk, nothing is trusted.

Limits (all checked before and while reading): entries, declared and real uncompressed
bytes, bytes per member, compression ratio (zip bomb) and folder depth. A name is only ever
used as its last path component, so there is no extraction path to escape (zip-slip). A
package inside a package is not opened: depth is one level.

Pure module (no models): the database side lives in ``archive_expand``. Structure only
taken from HubFedrizzi ``triagem/pacotes.py``; limits are this product's own.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import IO

MAX_ARCHIVE_ENTRIES = 100
MAX_RAW_ENTRIES = 1000  # directories and junk included: bounds the central directory parse
MAX_ARCHIVE_UNCOMPRESSED = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
RATIO_FLOOR_BYTES = 1024 * 1024  # small members may legitimately compress very well
MAX_PATH_DEPTH = 8
_CHUNK = 64 * 1024
_JUNK_NAMES = frozenset({".ds_store", "thumbs.db", "desktop.ini"})
_DRIVE = re.compile(r"^[A-Za-z]:")


class ArchiveRejected(ValueError):
    """The package as a whole cannot be used; the message is shown to the office."""


@dataclass(frozen=True)
class Member:
    path: str
    name: str
    folder: str
    data: bytes


@dataclass
class ZipReading:
    members: list[Member] = field(default_factory=list)
    ignored: Counter[str] = field(default_factory=Counter)

    def summary(self) -> str:
        return ", ".join(f"{count}x {label}" for label, count in self.ignored.most_common(6))


def _is_junk(parts: list[str]) -> bool:
    last = parts[-1].casefold()
    return (
        any(part.casefold() == "__macosx" for part in parts)
        or last in _JUNK_NAMES
        or last.startswith("._")
    )


def _clean(value: str) -> str:
    return re.sub(r"[\x00-\x1f]", "", value).strip()


def read_bounded(stream: IO[bytes], *, limit: int) -> bytes:
    """Read what the stream really holds; more than ``limit`` means the header lied."""

    buffer = bytearray()
    while chunk := stream.read(_CHUNK):
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise ArchiveRejected("Conteúdo do pacote maior que o declarado.")
    return bytes(buffer)


def _open(data: bytes) -> zipfile.ZipFile:
    if not data:
        raise ArchiveRejected("Pacote ZIP vazio.")
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ArchiveRejected("Pacote ZIP corrompido.") from exc


def _plan(
    package: zipfile.ZipFile, *, archive_size: int, allowed_suffixes: frozenset[str]
) -> tuple[list[tuple[zipfile.ZipInfo, str, str, str]], Counter[str]]:
    """Declared-size checks and the members worth reading: (info, path, name, folder)."""

    infos = package.infolist()
    if len(infos) > MAX_RAW_ENTRIES:
        raise ArchiveRejected(f"Pacote com mais de {MAX_RAW_ENTRIES} entradas.")
    considered: list[tuple[zipfile.ZipInfo, list[str]]] = []
    for info in infos:
        if info.is_dir():
            continue
        parts = [part for part in re.split(r"[\\/]+", info.filename) if part]
        if parts and not _is_junk(parts):
            considered.append((info, parts))
    if len(considered) > MAX_ARCHIVE_ENTRIES:
        raise ArchiveRejected(f"Pacote com mais de {MAX_ARCHIVE_ENTRIES} arquivos.")
    declared = sum(info.file_size for info, _ in considered)
    if declared > MAX_ARCHIVE_UNCOMPRESSED:
        raise ArchiveRejected("Pacote descompactado passa de 100 MB.")
    if declared > RATIO_FLOOR_BYTES and declared > MAX_COMPRESSION_RATIO * max(archive_size, 1):
        raise ArchiveRejected("Pacote com taxa de compressão suspeita.")
    if considered and all(info.flag_bits & 0x1 for info, _ in considered):
        raise ArchiveRejected("Pacote protegido por senha.")
    planned: list[tuple[zipfile.ZipInfo, str, str, str]] = []
    ignored: Counter[str] = Counter()
    for info, parts in considered:
        if info.file_size > RATIO_FLOOR_BYTES and (
            info.compress_size <= 0
            or info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise ArchiveRejected("Pacote com taxa de compressão suspeita.")
        raw = info.filename.replace("\\", "/")
        if (
            raw.startswith("/")
            or _DRIVE.match(raw)
            or any(part in {".", ".."} for part in raw.split("/") if part)
        ):
            ignored["caminho inseguro"] += 1
            continue
        if len(parts) > MAX_PATH_DEPTH:
            ignored["pasta funda demais"] += 1
            continue
        name = _clean(parts[-1])[:255]
        suffix = PurePosixPath(name).suffix.casefold()
        if not name:
            ignored["sem nome"] += 1
        elif info.flag_bits & 0x1:
            ignored["protegido por senha"] += 1
        elif suffix == ".zip":
            ignored["pacote dentro de pacote"] += 1
        elif suffix not in allowed_suffixes:
            ignored[suffix or "sem extensão"] += 1
        elif info.file_size > MAX_MEMBER_BYTES:
            ignored["maior que 25 MB"] += 1
        elif info.file_size <= 0:
            continue
        else:
            folder = " / ".join(_clean(part) for part in parts[:-1])[:200]
            planned.append((info, "/".join(parts), name, folder))
    return planned, ignored


def _refuse_if_empty(planned: list[object], ignored: Counter[str]) -> None:
    if not planned:
        detail = ", ".join(f"{count}x {label}" for label, count in ignored.most_common(6))
        raise ArchiveRejected(
            "Nenhum arquivo aceito no pacote" + (f" (ignorados: {detail})." if detail else ".")
        )


def inspect_zip(data: bytes, *, allowed_suffixes: frozenset[str]) -> int:
    """Structure and declared limits only (cheap): the count of members worth opening."""

    with _open(data) as package:
        planned, ignored = _plan(
            package, archive_size=len(data), allowed_suffixes=allowed_suffixes
        )
    _refuse_if_empty(list(planned), ignored)
    return len(planned)


def iter_zip_members(
    data: bytes, *, allowed_suffixes: frozenset[str], ignored: Counter[str]
) -> Iterator[Member]:
    """Yield accepted members one at a time so the caller never holds them all in memory.

    ``ignored`` is filled by the planning step (before the first member) and by members that
    turn out corrupted. ``ArchiveRejected`` can still surface mid-way (a header that lied):
    the caller must be able to undo what it already stored.
    """

    total = 0
    yielded = 0
    with _open(data) as package:
        planned, plan_ignored = _plan(
            package, archive_size=len(data), allowed_suffixes=allowed_suffixes
        )
        ignored.update(plan_ignored)
        _refuse_if_empty(list(planned), ignored)
        for info, path, name, folder in planned:
            try:
                with package.open(info) as source:
                    content = read_bounded(source, limit=info.file_size)
            except ArchiveRejected:
                raise
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError):
                ignored["corrompido"] += 1
                continue
            total += len(content)
            if total > MAX_ARCHIVE_UNCOMPRESSED:
                raise ArchiveRejected("Pacote descompactado passa de 100 MB.")
            if content:
                yielded += 1
                yield Member(path=path, name=name, folder=folder, data=content)
    if not yielded:
        _refuse_if_empty([], ignored)


def read_zip_members(data: bytes, *, allowed_suffixes: frozenset[str]) -> ZipReading:
    """All accepted members at once (small packages and tests)."""

    reading = ZipReading()
    reading.members = list(
        iter_zip_members(data, allowed_suffixes=allowed_suffixes, ignored=reading.ignored)
    )
    return reading
