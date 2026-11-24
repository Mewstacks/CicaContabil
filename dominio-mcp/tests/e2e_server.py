"""Servidor MCP por stdio com backend falso, para o teste e2e (T6.3).

Uso: python e2e_server.py <pasta de dados>. Monta o pack sintetico e um ODBC falso com o roteiro
de duas consultas (a primeira com duas linhas, a segunda com 120 linhas largas, que estoura o teto
de 12 KB) e atende por stdin/stdout de verdade.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from dominio_mcp.audit import JsonlAuditor  # noqa: E402
from dominio_mcp.config import Limits, Profile, Settings  # noqa: E402
from dominio_mcp.executor import QueryEngine  # noqa: E402
from dominio_mcp.odbc import build_session  # noqa: E402
from dominio_mcp.overlay import load_overlay  # noqa: E402
from dominio_mcp.server import Deps, build_server  # noqa: E402
from dominio_mcp.tools_schema import SchemaTools  # noqa: E402
from dominio_mcp.verified import VerifiedRunner, load_shipped_tools  # noqa: E402
from fake_odbc import FakeDriver, Rows  # noqa: E402
from packs import build_demo_pack  # noqa: E402
from qhelp import POLICY  # noqa: E402


class Guard:
    stale_reason = None

    def __init__(self, pack):  # type: ignore[no-untyped-def]
        self._pack = pack

    def pack(self):  # type: ignore[no-untyped-def]
        return self._pack

    precheck = pack

    def check(self, execute):  # type: ignore[no-untyped-def]
        return self._pack


def main() -> None:
    home = Path(sys.argv[1])
    home.mkdir(parents=True, exist_ok=True)
    pack = build_demo_pack(home)
    plan = (HERE / "fixtures" / "plans" / "full_scan.txt").read_text(encoding="utf-8")
    driver = FakeDriver()
    big = [(n, f"EMPRESA-{n:03d}-" + "x" * 150) for n in range(1, 121)]
    driver.server.script += [
        Rows(["plan"], [(plan,)]),
        Rows(["codi_emp", "nome_emp"], [(1, "ACME"), (2, "BETA")]),
        # segunda consulta da sessao: resultado grande, para ver `truncado` do lado do cliente
        Rows(["plan"], [(plan,)]),
        Rows(["codi_emp", "nome_emp"], big),
    ]
    settings = Settings(dsn="contabil", home=home, limits=Limits())
    overlay = load_overlay()
    auditor = JsonlAuditor(home / "audit")
    session = build_session(settings, driver=driver, auditor=auditor, lock_wait_seconds=0.3)
    guard = Guard(pack)
    engine = QueryEngine(
        settings=settings, policy=POLICY, guard=guard, session=session, auditor=auditor
    )  # type: ignore[arg-type]
    deps = Deps(
        settings=settings,
        policy=POLICY,
        overlay=overlay,
        guard=guard,  # type: ignore[arg-type]
        session=session,
        auditor=auditor,
        engine=engine,
        schema=SchemaTools(guard.pack, lambda: None, overlay),
        verified=VerifiedRunner(engine, load_shipped_tools(), overlay),
    )
    build_server(deps, Profile.REMOTE).run(transport="stdio")


if __name__ == "__main__":
    main()
