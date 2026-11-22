from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dominio_mcp import cli
from dominio_mcp.budget import quarantine_for
from dominio_mcp.config import Settings
from dominio_mcp.odbc import build_session
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import build_pack, pack_store_for
from dominio_mcp.policy import load_policy
from fake_odbc import Fail, FakeDriver, Rows
from packs import build_demo_pack

DENIED = Fail("42000", "[42000] Permission denied: SEGREDO (-121)")


def settings(tmp_path: Path) -> Settings:
    return Settings(dsn="contabil", home=tmp_path)


def doctor_session(
    tmp_path: Path, *, control: Any = DENIED, sample: Any = None, alive: int | None = None
) -> Any:
    driver = FakeDriver()
    if alive is not None:
        driver.server.live_numbers.add(alive)
    driver.server.script += [
        Rows(["v", "n"], [("17.0.11.7312", "contabil")]),
        Rows(["u"], [("EXTERNO",)]),
        control,
        sample if sample is not None else Rows([], []),
    ]
    return build_session(settings(tmp_path), driver=driver, lock_wait_seconds=0.3)


def test_version_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["version"]) == 0
    assert capsys.readouterr().out.strip().count(".") == 2


def test_doctor_reports_everything_and_prints_no_secret(tmp_path: Path) -> None:
    session = doctor_session(tmp_path)
    report = cli.run_doctor(settings(tmp_path), session=session)
    text = report.render()
    assert "conexao: OK (servidor 17.0.11.7312 / contabil, usuario do banco EXTERNO)" in text
    assert "legibilidade: controle negado como esperado e geempre legivel" in text
    assert "pack: AUSENTE" in text and "quarentena: nenhuma" in text
    assert "driver: pyodbc" in text and "perfil padrao: remote" in text
    assert "raw_sql: desligado" in text and "allow_pii: (nenhum)" in text
    for secret in ("PWD", "UID=", "SEGREDO", "password"):
        assert secret not in text
    assert report.problems == 1 and report.ok is False  # so o pack ausente


def test_doctor_is_clean_with_a_current_pack(tmp_path: Path) -> None:
    import json

    from dominio_mcp.catalog import build_catalog

    data = json.loads(
        (Path(__file__).parent / "fixtures" / "mini_catalog.json").read_text(encoding="utf-8")
    )
    store = pack_store_for(settings(tmp_path))
    built = store.new_build_path()
    meta = build_pack(
        built,
        catalog=build_catalog(data),
        policy=load_policy(),
        overlay=load_overlay(),
        dsn="contabil",
    )
    store.publish(built, meta)
    report = cli.run_doctor(settings(tmp_path), session=doctor_session(tmp_path))
    assert report.ok, report.render()
    assert f"pack: {meta.short}" in report.render()


def test_doctor_flags_a_stale_pack_and_a_quarantine(tmp_path: Path) -> None:
    import json

    from dominio_mcp.catalog import build_catalog
    from dominio_mcp.overlay import overlay_from_files

    data = json.loads(
        (Path(__file__).parent / "fixtures" / "mini_catalog.json").read_text(encoding="utf-8")
    )
    store = pack_store_for(settings(tmp_path))
    built = store.new_build_path()
    meta = build_pack(
        built,
        catalog=build_catalog(data),
        policy=load_policy(),
        overlay=overlay_from_files({"a.yaml": "x: 1\n"}),
        dsn="contabil",
    )
    store.publish(built, meta)
    quarantine_for(tmp_path / "state", "contabil").enter(77, "cancelamento nao confirmado")
    session = doctor_session(tmp_path, alive=77)  # a conexao antiga segue viva no servidor
    text = cli.run_doctor(settings(tmp_path), session=session).render()
    assert "DESATUALIZADO" in text
    assert "quarentena: ATIVA" in text and "dominio-mcp reset" in text


def test_doctor_reports_connection_failure_without_the_driver_text(tmp_path: Path) -> None:
    driver = FakeDriver()
    driver.server.connect_failures = 1
    session = build_session(settings(tmp_path), driver=driver, lock_wait_seconds=0.3)
    report = cli.run_doctor(settings(tmp_path), session=session)
    assert "conexao: FALHOU" in report.render() and "nao conectou" not in report.render()
    assert not report.ok


def test_doctor_does_not_trust_a_control_that_was_not_denied(tmp_path: Path) -> None:
    report = cli.run_doctor(
        settings(tmp_path), session=doctor_session(tmp_path, control=Rows([], []))
    )
    assert "controle NAO negado" in report.render() and not report.ok


def test_reset_releases_the_quarantine_and_says_when_there_was_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    assert cli.main(["reset"]) == 0
    assert "nao havia quarentena" in capsys.readouterr().out
    quarantine_for(tmp_path / "state", "contabil").enter(5, "teste")
    assert cli.main(["reset"]) == 0
    assert "quarentena liberada" in capsys.readouterr().out
    assert quarantine_for(tmp_path / "state", "contabil").is_active() is False


def test_parser_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["serve"]).profile == "remote"
    assert parser.parse_args(["serve", "--profile", "local"]).profile == "local"
    with pytest.raises(SystemExit):
        parser.parse_args(["serve", "--profile", "qualquer"])
    with pytest.raises(SystemExit):
        parser.parse_args([])
    seen: list[list[str]] = []
    monkeypatch.setattr(cli.buildpack_cli, "main", lambda argv: seen.append(list(argv)) or 0)
    assert cli.main(["build-pack"]) == 0 and cli.main(["build-pack", "--aceitar"]) == 0
    assert seen == [[], ["--aceitar"]]


def test_expected_errors_become_a_clean_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_DSN", "DSN=x;PWD=segredo")
    assert cli.main(["doctor"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("erro:") and "segredo" not in err


def test_demo_pack_helper_still_builds(tmp_path: Path) -> None:
    assert build_demo_pack(tmp_path).meta.counts["tables"] == 7
