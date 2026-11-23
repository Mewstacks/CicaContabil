"""Manifesto do `.mcpb` (M11): consistente com o pacote, sem L3, sem segredo, sem caminho do dono.

A prova de instalacao em pasta limpa e `scripts/prove_mcpb.py` (precisa do artefato montado);
aqui ficam as conferencias que nao dependem de rede nem de build.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.config import ConfigError, load_settings
from dominio_mcp.server import TOOL_NAMES

ROOT = Path(__file__).resolve().parents[1]
MANIFEST: dict[str, Any] = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))


def test_required_fields_and_version_match_the_package() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    for field in ("manifest_version", "name", "version", "description", "author", "server"):
        assert field in MANIFEST, field
    assert MANIFEST["version"] == project["version"] and MANIFEST["name"] == project["name"]
    assert MANIFEST["author"]["name"]


def test_the_declared_tools_are_exactly_the_servers_remote_tools() -> None:
    declared = tuple(t["name"] for t in MANIFEST["tools"])
    assert declared == TOOL_NAMES and not any("sql" in name for name in declared)
    assert all(t["description"] for t in MANIFEST["tools"])


def test_launch_config_uses_the_bundle_and_never_the_local_profile() -> None:
    server = MANIFEST["server"]
    assert server["type"] == "python" and (ROOT / "mcpb" / server["entry_point"]).is_file()
    config = server["mcp_config"]
    assert config["args"] == ["${__dirname}/" + server["entry_point"]]
    env = config["env"]
    assert env["PYTHONPATH"] == "${__dirname}/server/lib" and env["PYTHONNOUSERSITE"] == "1"
    launch = json.dumps(config).lower()
    for forbidden in ("--profile", "local", "raw_sql", "allow_pii", "http", "token", "c:\\"):
        assert forbidden not in launch, forbidden
    entry = (ROOT / "mcpb" / server["entry_point"]).read_text(encoding="utf-8")
    assert 'main(["serve"])' in entry and "--profile" not in entry and "--http" not in entry


def test_the_only_user_setting_is_a_dsn_name_that_the_config_accepts(tmp_path: Path) -> None:
    config = MANIFEST["user_config"]
    assert list(config) == ["dsn"] and config["dsn"]["type"] == "string"
    assert config["dsn"]["required"] is True and not config["dsn"].get("sensitive")
    assert MANIFEST["server"]["mcp_config"]["env"]["DOMINIO_MCP_DSN"] == "${user_config.dsn}"
    settings = load_settings(
        env={"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_DSN": config["dsn"]["default"]},
        config_path=tmp_path / "nao.toml",
    )
    assert settings.dsn == "contabil"
    with pytest.raises(ConfigError):
        load_settings(
            env={"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_DSN": ""},
            config_path=tmp_path / "nao.toml",
        )


def test_platform_and_runtime_match_the_bundled_binary_wheels() -> None:
    compat = MANIFEST["compatibility"]
    assert compat["platforms"] == ["win32"]
    assert compat["runtimes"]["python"] == ">=3.12,<3.13"
    build = (ROOT / "scripts" / "build_mcpb.py").read_text(encoding="utf-8")
    assert 'TARGET_PLATFORM = "x86_64-pc-windows-msvc"' in build
    assert 'TARGET_PYTHON = "3.12"' in build


def test_the_entry_point_activates_dot_pth_files_for_pywin32() -> None:
    entry = (ROOT / "mcpb" / "server" / "main.py").read_text(encoding="utf-8")
    assert "site.addsitedir" in entry
    assert entry.index("site.addsitedir") < entry.index("from dominio_mcp")
