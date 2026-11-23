"""CLI do dominio-mcp: `serve`, `build-pack`, `doctor`, `reset` e `version` (T6.4).

- `serve --http [--port N]`: o mesmo servidor em HTTP no loopback, com token (`http_app.py`);
  sempre perfil `remote`;
- `http-token`: mostra o token do HTTP (cria na primeira vez);
- `serve [--profile remote|local]`: servidor MCP por stdio. O perfil so vem daqui (D-326): o padrao
  `remote` vale para tunel, gateway e qualquer processo iniciado por terceiro;
- `build-pack [--aceitar]`: gera o pack do catalogo vivo (`buildpack.py`);
- `doctor [--completo]`: confere DSN, driver, versao do servidor, legibilidade, pack e quarentena.
  Nunca imprime credencial nem valor de linha;
- `reset`: libera a quarentena de execucao incerta, depois de o dono conferir no servidor.

Saida do console so em ASCII: o terminal do Windows nem sempre desenha acento.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from dominio_mcp import __version__
from dominio_mcp import buildpack as buildpack_cli
from dominio_mcp.budget import quarantine_for
from dominio_mcp.catalog import CatalogError
from dominio_mcp.config import ConfigError, Profile, Settings, load_settings
from dominio_mcp.freshness import PackStale
from dominio_mcp.http_app import (
    DEFAULT_PORT,
    MCP_PATH,
    HttpConfigError,
    check_bind,
    check_port,
    load_or_create_token,
    serve_http,
    token_path,
)
from dominio_mcp.odbc import DbError, OdbcUnavailable, build_session
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import PackError, pack_store_for
from dominio_mcp.policy import load_policy
from dominio_mcp.readable import CONTROL_SQL

USER_SQL = "SELECT CONNECTION_PROPERTY('Userid')"
SAMPLE_SQL = 'SELECT * FROM "bethadba"."geempre" WHERE 1=0'


@dataclass(slots=True)
class DoctorReport:
    lines: list[str]
    problems: int

    @property
    def ok(self) -> bool:
        return self.problems == 0

    def render(self) -> str:
        return "\n".join(self.lines)


def _driver_line() -> str:
    try:
        return f"pyodbc {importlib.metadata.version('pyodbc')} (instalado)"
    except importlib.metadata.PackageNotFoundError:
        return "pyodbc NAO instalado"


def run_doctor(
    settings: Settings, *, session: Any | None = None, full: bool = False
) -> DoctorReport:
    policy, overlay = load_policy(), load_overlay()
    problems = 0
    lines = [
        f"dominio-mcp {__version__} | Python {platform.python_version()} | perfil padrao: "
        f"{Profile.REMOTE.value}",
        f"configuracao: {settings.config_file or '(nenhum arquivo; valores padrao)'}",
        f"DSN: {settings.dsn} | raw_sql: {'ligado' if settings.raw_sql else 'desligado'} | "
        f"allow_pii: {', '.join(sorted(settings.allow_pii)) or '(nenhum)'}",
        f"pasta de dados: {settings.home}",
        f"politica {policy.sha[:12]} | overlay {overlay.sha[:12]}",
        f"driver: {_driver_line()}",
    ]
    sess = session
    try:
        if sess is None:
            sess = build_session(settings)
        with sess.slot() as slot:
            info = slot.execute(
                "SELECT PROPERTY('ProductVersion'), DB_PROPERTY('Name')", (), max_rows=2, timeout=10
            )
            user = slot.execute(USER_SQL, (), max_rows=2, timeout=10)
        version = f"{info.rows[0][0]} / {info.rows[0][1]}" if info.rows else "?"
        who = user.rows[0][0] if user.rows else "?"
        lines.append(f"conexao: OK (servidor {version}, usuario do banco {who})")
        outcomes = sess.execute_batch([CONTROL_SQL, SAMPLE_SQL])
        control_denied = isinstance(outcomes[0], DbError)
        sample_ok = not isinstance(outcomes[1], DbError | Exception)
        if control_denied and sample_ok:
            lines.append("legibilidade: controle negado como esperado e geempre legivel")
        else:
            problems += 1
            lines.append(
                "legibilidade: PROBLEMA (controle "
                f"{'negado' if control_denied else 'NAO negado'}; geempre "
                f"{'legivel' if sample_ok else 'ILEGIVEL'})"
            )
    except (DbError, OdbcUnavailable) as exc:
        problems += 1
        lines.append(f"conexao: FALHOU ({type(exc).__name__}: {exc})")
    except Exception as exc:
        problems += 1
        lines.append(f"conexao: FALHOU ({type(exc).__name__})")

    pack_line, pack_problem = _pack_line(settings, policy.sha, overlay.sha)
    lines.append(pack_line)
    problems += int(pack_problem)
    quarantine = quarantine_for(settings.home / "state", settings.dsn)
    state = quarantine.state()
    if state is None:
        lines.append("quarentena: nenhuma")
    else:
        problems += 1
        lines.append(
            f"quarentena: ATIVA desde {state.since} ({state.reason}); depois de conferir no "
            "servidor rode `dominio-mcp reset`"
        )
    if full:
        lines.append("--completo: a legibilidade de todos os objetos e conferida em `build-pack`")
    lines.append(f"auditoria: {settings.home / 'audit' / 'audit.jsonl'}")
    if sess is not None and session is None:
        sess.close()
    return DoctorReport(lines, problems)


def _pack_line(settings: Settings, policy_sha: str, overlay_sha: str) -> tuple[str, bool]:
    try:
        pack = pack_store_for(settings).open_current()
    except PackError as exc:
        return f"pack: ILEGIVEL ({exc}); rode `dominio-mcp build-pack`", True
    if pack is None:
        return "pack: AUSENTE; rode `dominio-mcp build-pack`", True
    meta = pack.meta
    stale = meta.policy_sha != policy_sha or meta.overlay_sha != overlay_sha
    note = (
        " | DESATUALIZADO (politica ou overlay mudaram): rode `dominio-mcp build-pack`"
        if stale
        else ""
    )
    accepted = len(pack.accepted())
    return (
        f"pack: {meta.short} gerado em {meta.built_at} | {meta.counts.get('tables')} tabelas, "
        f"{meta.counts.get('columns')} colunas, {accepted} colunas aceitas{note}",
        stale,
    )


def cmd_doctor(args: argparse.Namespace) -> int:
    report = run_doctor(load_settings(), full=args.completo)
    print(report.render())
    return 0 if report.ok else 1


def cmd_reset(_args: argparse.Namespace) -> int:
    settings = load_settings()
    quarantine = quarantine_for(settings.home / "state", settings.dsn)
    state = quarantine.state()
    if state is None:
        print("nao havia quarentena")
        return 0
    quarantine.reset()
    print(
        f"quarentena liberada (estava desde {state.since}: {state.reason}). Confira no servidor "
        "do Dominio que nenhuma consulta antiga segue rodando."
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from dominio_mcp.server import build_deps, build_server

    profile = Profile(args.profile)
    if args.http and profile is not Profile.REMOTE:
        raise ConfigError("o HTTP so existe no perfil remote (L3 nunca passa por HTTP)")
    settings = load_settings(profile=profile)
    deps = build_deps(settings)
    try:
        pack = deps.guard.pack()
        age = datetime.now(UTC) - datetime.fromisoformat(pack.meta.built_at)
        print(
            f"dominio-mcp: pack {pack.meta.short} ({age.days} dia(s)); perfil {profile.value}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"dominio-mcp: {exc}", file=sys.stderr)
    server = build_server(deps, profile)
    if args.http:
        host = check_bind(args.host)
        port = check_port(args.port)
        token = load_or_create_token(token_path(settings.home))
        print(
            f"dominio-mcp: HTTP em http://{host}:{port}{MCP_PATH} (token: dominio-mcp http-token)",
            file=sys.stderr,
        )
        serve_http(server, host=host, port=port, token=token)
        return 0
    server.run(transport="stdio")
    return 0


def cmd_http_token(_args: argparse.Namespace) -> int:
    settings = load_settings()
    path = token_path(settings.home)
    print(load_or_create_token(path))
    print(f"arquivo: {path}", file=sys.stderr)
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dominio-mcp", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="inicia o servidor MCP por stdio")
    serve.add_argument(
        "--profile",
        choices=[p.value for p in Profile],
        default=Profile.REMOTE.value,
        help="remote (padrao) para tunel e gateway; local so em stdio do proprio computador",
    )
    serve.add_argument(
        "--http", action="store_true", help="HTTP em 127.0.0.1 com token, em vez de stdio"
    )
    serve.add_argument("--host", default="127.0.0.1", help="so 127.0.0.1 ou ::1")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT, help="porta do HTTP")
    serve.set_defaults(func=cmd_serve)
    token = sub.add_parser("http-token", help="mostra o token do HTTP (cria na primeira vez)")
    token.set_defaults(func=cmd_http_token)
    build = sub.add_parser("build-pack", help="gera o pack do catalogo do banco")
    build.add_argument("--aceitar", action="store_true", help="aprova o catalogo atual como base")
    build.set_defaults(func=lambda a: buildpack_cli.main(["--aceitar"] if a.aceitar else []))
    doctor = sub.add_parser("doctor", help="confere DSN, driver, legibilidade, pack e quarentena")
    doctor.add_argument(
        "--completo", action="store_true", help="mostra o que a checagem completa faz"
    )
    doctor.set_defaults(func=cmd_doctor)
    reset = sub.add_parser("reset", help="libera a quarentena depois de conferir no servidor")
    reset.set_defaults(func=cmd_reset)
    version = sub.add_parser("version", help="mostra a versao")
    version.set_defaults(func=cmd_version)
    return parser


_EXPECTED = (
    ConfigError,
    HttpConfigError,
    DbError,
    OdbcUnavailable,
    CatalogError,
    PackError,
    PackStale,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except _EXPECTED as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
