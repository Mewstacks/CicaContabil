"""Frescor do pack (D-318, T2.8): detectar que o banco mudou e bloquear L1 e L2 ate `build-pack`.

Tres camadas, da mais barata para a mais completa:

1. **Politica e overlay**: o pack foi gerado com outro `policy.yaml` ou outro overlay do que o
   codigo em execucao tem? Desatualizado na hora, sem tocar no banco (mudar a politica precisa
   valer).
2. **Sonda barata** (a cada 60 s, ~30 ms): contagens de `SYS.SYSTAB`, `SYSTABCOL`, `SYSFKEY`,
   `SYSIDX`, `SYSREMARK`, `SYSVIEW` e soma do tamanho das definicoes de view, comparadas com a base
   tirada no ultimo re-hash completo. `MAX(last_modified_at)` ficou de fora: anda sem DDL (E13).
3. **Re-hash completo** (ao iniciar, a cada 1 h e a cada pack novo): le o catalogo inteiro e compara
   os tres hashes (estrutura, views, comentarios) com os do pack. E o que pega comentario editado
   e coluna que mudou de tipo sem mudar contagem.

Desatualizado e "pegajoso": so sai quando um pack novo e publicado. Falha de leitura do banco
(`DbError`) NAO marca desatualizado: propaga e a proxima chamada tenta de novo.

Os packs ficam em arquivos por versao e o ponteiro `current.json` e trocado por `os.replace`:
quem ja abriu o pack antigo continua nele ate a proxima chamada, que reabre o novo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from dominio_mcp.catalog import build_catalog, extract_raw
from dominio_mcp.odbc import RawResult
from dominio_mcp.pack import Pack, PackStore
from dominio_mcp.values import Cell

PROBE_SQL = (
    "SELECT (SELECT COUNT(*) FROM SYS.SYSTAB), (SELECT COUNT(*) FROM SYS.SYSTABCOL), "
    "(SELECT COUNT(*) FROM SYS.SYSFKEY), (SELECT COUNT(*) FROM SYS.SYSIDX), "
    "(SELECT COUNT(*) FROM SYS.SYSREMARK), (SELECT COUNT(*) FROM SYS.SYSVIEW), "
    "(SELECT COALESCE(SUM(LENGTH(view_def)), 0) FROM SYS.SYSVIEW)"
)
PROBE_KEYS = ("tables", "columns", "fkeys", "indexes", "remarks", "views", "view_def_chars")
PROBE_EVERY_SECONDS = 60.0
REHASH_EVERY_SECONDS = 3600.0


class PackMissing(Exception):
    """Nao ha pack publicado: rode `dominio-mcp build-pack`."""


class PackStale(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"pack desatualizado ({reason}): rode `dominio-mcp build-pack` antes de consultar"
        )
        self.reason = reason


class Executor(Protocol):
    def __call__(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult: ...


@dataclass(frozen=True, slots=True)
class Hashes:
    structure: str
    views: str
    comments: str


def read_probe(execute: Executor) -> dict[str, int]:
    result = execute(PROBE_SQL, (), max_rows=2)
    if len(result.rows) != 1 or len(result.rows[0]) != len(PROBE_KEYS):
        raise PackStale("sonda de frescor com resposta inesperada")
    return {k: _to_int(v) for k, v in zip(PROBE_KEYS, result.rows[0], strict=True)}


def _to_int(value: Cell) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        raise PackStale("sonda de frescor com valor inesperado") from None


def make_rehasher(owner: str) -> Callable[[Executor], Hashes]:
    def rehash(execute: Executor) -> Hashes:
        catalog = build_catalog(extract_raw(execute), owner=owner)
        return Hashes(catalog.structure_hash(), catalog.views_hash(), catalog.comments_hash())

    return rehash


class FreshnessGuard:
    def __init__(
        self,
        store: PackStore,
        *,
        policy_sha: str,
        overlay_sha: str,
        rehash: Callable[[Executor], Hashes],
        clock: Callable[[], float] = time.monotonic,
        probe_every: float = PROBE_EVERY_SECONDS,
        rehash_every: float = REHASH_EVERY_SECONDS,
    ) -> None:
        self._store = store
        self._policy_sha = policy_sha
        self._overlay_sha = overlay_sha
        self._rehash = rehash
        self._clock = clock
        self._probe_every = probe_every
        self._rehash_every = rehash_every
        self._pack: Pack | None = None
        self._stale: str | None = None
        self._baseline: dict[str, int] | None = None
        self._last_probe = 0.0
        self._last_full: float | None = None

    @property
    def stale_reason(self) -> str | None:
        return self._stale

    def pack(self) -> Pack:
        """O pack corrente (reabre se o ponteiro mudou), sem consultar o banco."""
        path = self._store.current_path()
        if path is None:
            raise PackMissing("nenhum pack publicado: rode `dominio-mcp build-pack`")
        if self._pack is None or self._pack.path != path:
            self._pack = Pack(path)
            self._stale = None
            self._baseline = None
            self._last_full = None
        meta = self._pack.meta
        if self._stale is None and meta.policy_sha != self._policy_sha:
            self._stale = "a politica de dados mudou desde a geracao do pack"
        if self._stale is None and meta.overlay_sha != self._overlay_sha:
            self._stale = "o overlay mudou desde a geracao do pack"
        return self._pack

    def precheck(self) -> Pack:
        """O pack corrente, sem tocar no banco; levanta `PackStale` se ja se sabe desatualizado."""
        pack = self.pack()
        if self._stale is not None:
            raise PackStale(self._stale)
        return pack

    def check(self, execute: Executor) -> Pack:
        pack = self.precheck()
        now = self._clock()
        if self._last_full is None or now - self._last_full >= self._rehash_every:
            hashes = self._rehash(execute)
            reason = _hash_mismatch(pack, hashes)
            if reason is not None:
                self._stale = reason
                raise PackStale(reason)
            self._baseline = read_probe(execute)
            self._last_full = self._last_probe = now
        elif now - self._last_probe >= self._probe_every:
            current = read_probe(execute)
            self._last_probe = now
            if current != self._baseline:
                self._stale = "as contagens do catalogo mudaram"
                raise PackStale(self._stale)
        return pack


def _hash_mismatch(pack: Pack, hashes: Hashes) -> str | None:
    meta = pack.meta
    if hashes.structure != meta.structure_hash:
        return "a estrutura do banco mudou (objetos, colunas, tipos, chaves ou indices)"
    if hashes.views != meta.views_hash:
        return "a definicao de alguma view mudou"
    if hashes.comments != meta.comments_hash:
        return "os comentarios do banco mudaram"
    return None
