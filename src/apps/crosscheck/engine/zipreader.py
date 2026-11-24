"""Leitura de ZIP de XMLs sem extrair em disco e com defesa contra bomba de compressão.

O ZIP vive num arquivo temporário do worker; cada entrada é lida para a memória, uma por
vez, com teto de bytes. O tamanho declarado no cabeçalho do ZIP pode mentir, então a leitura
também para no teto: uma entrada que passa do limite é recusada, não truncada.
"""

from __future__ import annotations

import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class ZipLimits:
    max_entries: int = 12_000
    max_entry_bytes: int = 2 * 1024 * 1024
    max_total_bytes: int = 1024 * 1024 * 1024
    max_ratio: int = 100


class ZipRejected(ValueError):
    """O arquivo inteiro é recusado (não é ZIP, entradas demais, tamanho total absurdo)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ZipItem:
    name: str
    data: bytes | None = None
    #: "" quando a entrada foi lida; senão o motivo de não ter sido.
    problem: str = ""


@dataclass(frozen=True, slots=True)
class ZipSummary:
    entries: int
    xml_entries: int
    uncompressed_bytes: int


def display_name(raw: str) -> str:
    """Só o nome do arquivo, com qualquer separador, para nunca exibir caminho do ZIP."""

    return raw.replace("\\", "/").rsplit("/", 1)[-1]


def _is_noise(raw: str) -> bool:
    name = display_name(raw)
    return raw.startswith("__MACOSX/") or name.startswith("._") or name == ".DS_Store"


def _open(fileobj: BinaryIO, limits: ZipLimits) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(fileobj)
    except (zipfile.BadZipFile, OSError, EOFError, ValueError) as exc:
        raise ZipRejected("nao_zip", "O arquivo não é um ZIP válido.") from exc
    infos = archive.infolist()
    if len(infos) > limits.max_entries:
        archive.close()
        raise ZipRejected(
            "entradas_demais",
            f"O ZIP tem {len(infos)} entradas; o limite é {limits.max_entries}.",
        )
    if sum(info.file_size for info in infos) > limits.max_total_bytes:
        archive.close()
        raise ZipRejected("tamanho_total", "O ZIP descompactado passa do limite de tamanho.")
    return archive


def summarize_zip(fileobj: BinaryIO, limits: ZipLimits | None = None) -> ZipSummary:
    """Só o diretório central do ZIP: seguro para o processo web, não descomprime nada."""

    limits = limits or ZipLimits()
    with _open(fileobj, limits) as archive:
        files = [
            info
            for info in archive.infolist()
            if not info.is_dir() and not _is_noise(info.filename)
        ]
        return ZipSummary(
            entries=len(files),
            xml_entries=sum(1 for info in files if info.filename.lower().endswith(".xml")),
            uncompressed_bytes=sum(info.file_size for info in files),
        )


def iter_zip_items(fileobj: BinaryIO, limits: ZipLimits | None = None) -> Iterator[ZipItem]:
    """Uma entrada por vez: o XML lido ou o motivo de ter sido recusado."""

    limits = limits or ZipLimits()
    with _open(fileobj, limits) as archive:
        for info in archive.infolist():
            if info.is_dir() or _is_noise(info.filename):
                continue
            name = display_name(info.filename)
            if not info.filename.lower().endswith(".xml"):
                yield ZipItem(name, problem="nao_xml")
                continue
            if info.flag_bits & 0x1:
                yield ZipItem(name, problem="criptografado")
                continue
            if info.file_size > limits.max_entry_bytes:
                yield ZipItem(name, problem="grande_demais")
                continue
            if (
                info.file_size > 0
                and info.file_size / max(info.compress_size, 1) > limits.max_ratio
            ):
                yield ZipItem(name, problem="razao_suspeita")
                continue
            try:
                with archive.open(info) as handle:
                    data = handle.read(limits.max_entry_bytes + 1)
            except (zipfile.BadZipFile, OSError, EOFError, RuntimeError, zlib.error):
                yield ZipItem(name, problem="corrompido")
                continue
            if len(data) > limits.max_entry_bytes:
                yield ZipItem(name, problem="grande_demais")
                continue
            yield ZipItem(name, data=data)
