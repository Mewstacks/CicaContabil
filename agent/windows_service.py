"""Native Windows Service host for the outbound-only Domínio edge agent.

The module remains importable on non-Windows development hosts. It only loads
pywin32 when the Windows Service Control Manager starts it.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from agent.local_queue import EncryptedQueue
from agent.runner import AgentRuntimeConfig, synchronize_once

try:  # Imported only on Windows hosts that install the dominio-agent extra.
    import servicemanager  # type: ignore[import-not-found]
    import win32event  # type: ignore[import-not-found]
    import win32service  # type: ignore[import-not-found]
    import win32serviceutil  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - expected on the non-Windows CI host
    servicemanager = win32event = win32service = win32serviceutil = None

SERVICE_NAME = "HubContadorDominioAgent"
_DEFAULT_CONFIG_PATH = Path("C:/ProgramData/HubContador/agent-config.dpapi")
_ENVIRONMENT_KEYS = frozenset(
    {
        "HUB_AGENT_DSN",
        "HUB_AGENT_HUB_URL",
        "HUB_AGENT_ID",
        "HUB_AGENT_SHARED_SECRET",
        "HUB_AGENT_CA_FILE",
        "HUB_AGENT_CERTIFICATE_FILE",
        "HUB_AGENT_PRIVATE_KEY_FILE",
        "HUB_AGENT_QUEUE_PATH",
        "HUB_AGENT_INTERVAL_SECONDS",
    }
)


def decode_service_environment(
    protected_payload: bytes, *, unprotect: Callable[[bytes], bytes]
) -> dict[str, str]:
    """Decrypt and validate the small, private service configuration document."""
    try:
        decoded = base64.b64decode(protected_payload, validate=True)
        document: Any = json.loads(unprotect(decoded))
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Configuração protegida do agente inválida.") from exc
    if not isinstance(document, Mapping) or set(document) - _ENVIRONMENT_KEYS:
        raise ValueError("Configuração protegida do agente inválida.")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in document.items()):
        raise ValueError("Configuração protegida do agente inválida.")
    environment = dict(document)
    AgentRuntimeConfig.from_environment(environment)
    return environment


def load_service_environment(config_path: Path = _DEFAULT_CONFIG_PATH) -> dict[str, str]:
    """Read a DPAPI LocalMachine blob; ACLs are applied by the elevated installer."""
    try:
        import win32crypt  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - Windows runtime dependency
        raise RuntimeError(
            "Instale o extra Windows do agente antes de registrar o serviço."
        ) from exc
    try:
        protected_payload = config_path.read_bytes()
    except OSError as exc:
        raise RuntimeError("Configuração protegida do agente não encontrada.") from exc

    def unprotect(value: bytes) -> bytes:
        return bytes(win32crypt.CryptUnprotectData(value, None, None, None, 0)[1])

    return decode_service_environment(protected_payload, unprotect=unprotect)


def _run_service_loop(stop_requested: Callable[[int], bool]) -> None:
    environment = load_service_environment()
    runtime = AgentRuntimeConfig.from_environment(environment)
    runtime.queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue = EncryptedQueue(runtime.queue_path, runtime.sync.shared_secret)
    while not stop_requested(0):
        with suppress(OSError, RuntimeError, ValueError):
            synchronize_once(runtime=runtime, queue=queue)
        stop_requested(runtime.interval_seconds * 1000)


if win32serviceutil is not None:  # pragma: no cover - exercised by the Windows SCM

    class HubContadorDominioAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        # Keep SERVICE_NAME stable for existing Windows installations, but never
        # show the retired product name in the Services console.
        _svc_display_name_ = "CICA — Agente Domínio"
        _svc_description_ = "Sincroniza dados Domínio autorizados, somente por HTTPS de saída."

        def __init__(self, args: list[str]) -> None:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self) -> None:
            try:
                _run_service_loop(
                    lambda timeout: (
                        win32event.WaitForSingleObject(self.stop_event, timeout)
                        == win32event.WAIT_OBJECT_0
                    )
                )
            except Exception as exc:
                servicemanager.LogErrorMsg(f"{SERVICE_NAME} interrompido: {type(exc).__name__}")
                raise


def main() -> None:  # pragma: no cover - exercised by the Windows SCM
    if win32serviceutil is None:
        raise SystemExit(
            "Instale o extra Windows do agente (pywin32) antes de registrar o serviço."
        )
    win32serviceutil.HandleCommandLine(HubContadorDominioAgentService)


if __name__ == "__main__":
    main()
