"""Auditoria em JSONL local, sem valor de linha (D-319, T6.1).

Um evento por linha em `<home>/audit/audit.jsonl`: ferramenta, hash dos argumentos, tabelas,
quantidade de linhas, truncado, latencia, custo estimado e versao do pack. **Nunca** valor de
linha: so campos de uma lista fechada entram (`ALLOWED`); qualquer outro nome e descartado e o
evento registra so o nome descartado. Texto e cortado em 200 caracteres e lista em 20 itens.
Rotaciona por tamanho (5 MB, 5 arquivos). Falha ao gravar nunca derruba a consulta: avisa uma
vez no stderr.
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED = frozenset(
    {
        "tool",
        "args",
        "tabelas",
        "resultado",
        "linhas",
        "truncado",
        "latencia_ms",
        "custo",
        "pack",
        "conexao",
        "limite_s",
        "sql_hash",
        "tipo",
        "sqlstate",
        "ferramenta",
        "perfil",
        "versao",
        "codigo",
    }
)
MAX_TEXT = 200
MAX_ITEMS = 20


def _clean(value: Any) -> Any:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"
    if isinstance(value, list | tuple):
        items = [_clean(v) for v in list(value)[:MAX_ITEMS] if isinstance(v, str | int | float)]
        return items
    return "<removido>"


class JsonlAuditor:
    def __init__(
        self,
        directory: Path,
        *,
        max_bytes: int = 5_000_000,
        keep: int = 5,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._dir = directory
        self._max = max_bytes
        self._keep = keep
        self._clock = clock
        self._lock = threading.Lock()
        self._warned = False

    @property
    def path(self) -> Path:
        return self._dir / "audit.jsonl"

    def event(self, name: str, **fields: Any) -> None:
        kept = {k: _clean(v) for k, v in fields.items() if k in ALLOWED}
        dropped = sorted(k for k in fields if k not in ALLOWED)
        record: dict[str, Any] = {
            "ts": datetime.fromtimestamp(self._clock(), UTC).isoformat(timespec="milliseconds"),
            "evento": name,
            **kept,
        }
        if dropped:
            record["descartados"] = dropped
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        try:
            with self._lock:
                self._dir.mkdir(parents=True, exist_ok=True)
                self._rotate_if_needed(len(line.encode("utf-8")))
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(line)
        except OSError as exc:
            if not self._warned:
                self._warned = True
                print(
                    f"dominio-mcp: nao consegui gravar a auditoria ({exc.strerror})",
                    file=sys.stderr,
                )

    def _rotate_if_needed(self, incoming: int) -> None:
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            return
        if size + incoming <= self._max:
            return
        oldest = self._dir / f"audit.{self._keep}.jsonl"
        oldest.unlink(missing_ok=True)
        for i in range(self._keep - 1, 0, -1):
            source = self._dir / f"audit.{i}.jsonl"
            if source.exists():
                source.replace(self._dir / f"audit.{i + 1}.jsonl")
        self.path.replace(self._dir / "audit.1.jsonl")
