"""Servico do Windows `DominioMcpAgent` (pywin32): o laco do agente como servico automatico.

Instalacao: `python -m dominio_mcp.service --startup auto install` (o instalador faz isso).
A pasta de dados e fixa em `C:\ProgramData\HubContador\dominio-mcp`, a mesma do pareamento, e o
DSN tem de ser de SISTEMA (o servico roda como SYSTEM e nao enxerga DSN de usuario).
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

DATA_HOME = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "HubContador" / "dominio-mcp"
os.environ.setdefault("DOMINIO_MCP_HOME", str(DATA_HOME))

import servicemanager  # noqa: E402  (pywin32; so existe no Windows com o extra `servico`)
import win32event  # noqa: E402
import win32service  # noqa: E402
import win32serviceutil  # noqa: E402

from dominio_mcp.agent import Agent, load_config, relay_runner  # noqa: E402


class DominioMcpAgentService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
    _svc_name_ = "DominioMcpAgent"
    _svc_display_name_ = "CICA - Conector MCP do Dominio"
    _svc_description_ = "Responde consultas somente leitura ao Dominio, a pedido do CICA."

    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self._stopped = threading.Event()
        self._wait = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self) -> None:
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stopped.set()
        win32event.SetEvent(self._wait)

    def SvcDoRun(self) -> None:
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        agent = Agent(
            load_config(DATA_HOME),
            relay_runner(),
            log=lambda message: servicemanager.LogInfoMsg(f"{self._svc_name_}: {message}"),
        )
        worker = threading.Thread(target=agent.run, args=(self._stopped,), daemon=True)
        worker.start()
        win32event.WaitForSingleObject(self._wait, win32event.INFINITE)
        worker.join(timeout=30)


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(DominioMcpAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(DominioMcpAgentService)
