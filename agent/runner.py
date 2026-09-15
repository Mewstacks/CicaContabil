"""Runtime local do agente Domínio, executado somente no Windows do escritório.

O processo não aceita comandos remotos nem SQL. Ele lê uma consulta constante,
persiste snapshots na fila local cifrada e faz somente uma chamada
HTTPS mTLS de saída à CICA.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent.hub_agent import OdbcCursor, serialize_companies
from agent.local_queue import EncryptedQueue
from agent.sync_client import EdgeAgentConfig, post_snapshot

_DSN_PATTERN = re.compile(r"[A-Za-z0-9_. -]{1,128}")
_DEFAULT_QUEUE_PATH = Path("C:/ProgramData/HubContador/agent-queue.bin")


class OdbcConnection(Protocol):
    def cursor(self) -> OdbcCursor: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class AgentRuntimeConfig:
    dsn: str
    sync: EdgeAgentConfig
    queue_path: Path
    interval_seconds: int = 60

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> AgentRuntimeConfig:
        values = os.environ if environment is None else environment

        def required(name: str) -> str:
            value = values.get(name, "").strip()
            if not value:
                raise ValueError(f"Defina {name} no ambiente protegido do agente.")
            return value

        dsn = required("HUB_AGENT_DSN")
        if not _DSN_PATTERN.fullmatch(dsn):
            raise ValueError("HUB_AGENT_DSN deve conter somente o nome do DSN de sistema.")
        try:
            interval_seconds = int(values.get("HUB_AGENT_INTERVAL_SECONDS", "60"))
        except ValueError as exc:
            raise ValueError("HUB_AGENT_INTERVAL_SECONDS deve ser numérico.") from exc
        if not 10 <= interval_seconds <= 86_400:
            raise ValueError("HUB_AGENT_INTERVAL_SECONDS deve ficar entre 10 e 86400.")
        return cls(
            dsn=dsn,
            sync=EdgeAgentConfig(
                hub_url=required("HUB_AGENT_HUB_URL"),
                agent_id=required("HUB_AGENT_ID"),
                shared_secret=required("HUB_AGENT_SHARED_SECRET"),
                client_ca_file=required("HUB_AGENT_CA_FILE"),
                client_certificate_file=required("HUB_AGENT_CERTIFICATE_FILE"),
                client_private_key_file=required("HUB_AGENT_PRIVATE_KEY_FILE"),
            ),
            queue_path=Path(values.get("HUB_AGENT_QUEUE_PATH", str(_DEFAULT_QUEUE_PATH))).resolve(),
            interval_seconds=interval_seconds,
        )


@dataclass(frozen=True)
class SyncOutcome:
    status: str
    company_count: int


def pyodbc_connection_factory(dsn: str) -> OdbcConnection:
    """Load pyodbc only on the authorized Windows host with its installed driver."""
    if not _DSN_PATTERN.fullmatch(dsn):
        raise ValueError("DSN inválido.")
    try:
        import pyodbc  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Instale o driver e pyodbc somente no host Domínio autorizado.") from exc
    return pyodbc.connect(f"DSN={dsn}", autocommit=True, timeout=20)


def synchronize_once(
    *,
    runtime: AgentRuntimeConfig,
    queue: EncryptedQueue,
    connection_factory: Callable[[str], OdbcConnection] = pyodbc_connection_factory,
) -> SyncOutcome:
    """Replay one queued snapshot first; only then query the local read-only DSN."""
    pending = queue.first()
    if pending is not None:
        post_snapshot(runtime.sync, pending["payload"])
        queue.acknowledge(pending["id"])
        companies = pending["payload"].get("companies", [])
        return SyncOutcome("replayed", len(companies) if isinstance(companies, list) else 0)

    connection = connection_factory(runtime.dsn)
    try:
        companies = serialize_companies(connection.cursor())
    finally:
        connection.close()
    # The allowlisted company query is bounded. It is therefore an incremental
    # snapshot and must never deactivate a company absent from this batch.
    item_id = queue.push({"companies": companies, "full_snapshot": False})
    pending = queue.first()
    if pending is None or pending["id"] != item_id:
        raise RuntimeError("Fila local do agente não confirmou o snapshot.")
    post_snapshot(runtime.sync, pending["payload"])
    queue.acknowledge(item_id)
    return SyncOutcome("synchronized", len(companies))


def run_forever(
    *,
    runtime: AgentRuntimeConfig,
    queue: EncryptedQueue,
    connection_factory: Callable[[str], OdbcConnection] = pyodbc_connection_factory,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    while True:
        with suppress(OSError, RuntimeError, ValueError):
            synchronize_once(
                runtime=runtime,
                queue=queue,
                connection_factory=connection_factory,
            )
        sleep(runtime.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente Domínio da CICA, somente leitura")
    parser.add_argument(
        "--once", action="store_true", help="Executa um ciclo sem imprimir dados fiscais"
    )
    options = parser.parse_args()
    runtime = AgentRuntimeConfig.from_environment()
    runtime.queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue = EncryptedQueue(runtime.queue_path, runtime.sync.shared_secret)
    if options.once:
        outcome = synchronize_once(runtime=runtime, queue=queue)
        print(f"status={outcome.status} empresas={outcome.company_count}")
        return
    run_forever(runtime=runtime, queue=queue)


if __name__ == "__main__":
    main()
