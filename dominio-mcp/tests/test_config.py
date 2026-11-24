from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from dominio_mcp.config import (
    HARD_MAX_COLUMNS,
    HARD_MAX_RESPONSE_BYTES,
    HARD_MAX_ROWS,
    HARD_MAX_ROWS_AGGREGATE,
    PII_CATEGORIES,
    ConfigError,
    Profile,
    Settings,
    load_settings,
)

WIN_ENV = {"LOCALAPPDATA": "C:/Users/x/AppData/Local"}


def write_toml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_defaults_are_the_safe_ones(tmp_path: Path) -> None:
    s = load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=tmp_path / "nao.toml")
    assert s.dsn == "contabil"
    assert s.profile is Profile.REMOTE
    assert s.raw_sql is False
    assert s.allow_pii == frozenset()
    assert s.home == tmp_path
    assert s.config_file is None
    assert s.limits.default_rows == 50
    assert s.limits.max_rows == HARD_MAX_ROWS == 500
    assert s.limits.max_rows_aggregate == HARD_MAX_ROWS_AGGREGATE == 2000
    assert s.limits.max_columns == HARD_MAX_COLUMNS == 40
    assert s.limits.max_response_bytes == HARD_MAX_RESPONSE_BYTES == 12 * 1024
    assert s.limits.query_timeout_seconds == 30
    assert s.limits.cancel_confirm_seconds == 10
    assert s.limits.executions_per_minute == 20
    assert (s.limits.plan_cost_budget, s.limits.plan_rows_budget) == (10, 1_000_000)


def test_home_defaults_to_localappdata_on_windows_layout() -> None:
    s = load_settings(env=WIN_ENV, config_path=Path("nao-existe.toml"))
    assert s.home == Path("C:/Users/x/AppData/Local") / "dominio-mcp"


def test_home_falls_back_to_xdg_then_home_dir() -> None:
    s = load_settings(env={"XDG_DATA_HOME": "/data"}, config_path=Path("nao-existe.toml"))
    assert s.home == Path("/data") / "dominio-mcp"
    s2 = load_settings(env={"HOME": "/home/u"}, config_path=Path("nao-existe.toml"))
    assert s2.home == Path("/home/u") / ".local" / "share" / "dominio-mcp"


def test_toml_overrides_defaults(tmp_path: Path) -> None:
    cfg = write_toml(
        tmp_path,
        """
dsn = "outro"
allow_pii = ["cpf", "contato"]

[limits]
default_rows = 20
max_rows = 100
query_timeout_seconds = 15
""",
    )
    s = load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=cfg)
    assert s.dsn == "outro"
    assert s.allow_pii == frozenset({"cpf", "contato"})
    assert s.limits.default_rows == 20
    assert s.limits.max_rows == 100
    assert s.limits.query_timeout_seconds == 15
    assert s.limits.max_columns == 40
    assert s.config_file == cfg


def test_env_overrides_toml(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, 'dsn = "do_arquivo"\nallow_pii = ["cpf"]\nraw_sql = false\n')
    env = {
        "DOMINIO_MCP_HOME": str(tmp_path),
        "DOMINIO_MCP_DSN": "do_ambiente",
        "DOMINIO_MCP_ALLOW_PII": " contato , bancario,contato ",
        "DOMINIO_MCP_RAW_SQL": "TRUE",
    }
    s = load_settings(env=env, config_path=cfg)
    assert s.dsn == "do_ambiente"
    assert s.allow_pii == frozenset({"contato", "bancario"})
    assert s.raw_sql is True


def test_env_can_point_to_the_config_file(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, 'dsn = "via_env"\n')
    s = load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_CONFIG": str(cfg)})
    assert s.dsn == "via_env"


def test_config_path_from_env_must_exist(tmp_path: Path) -> None:
    env = {"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_CONFIG": str(tmp_path / "typo.toml")}
    with pytest.raises(ConfigError, match="DOMINIO_MCP_CONFIG"):
        load_settings(env=env)


def test_config_file_in_home_is_found_by_default(tmp_path: Path) -> None:
    write_toml(tmp_path, 'dsn = "da_casa"\n')
    s = load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)})
    assert s.dsn == "da_casa"
    assert s.config_file == tmp_path / "config.toml"


def test_empty_allow_pii_env_clears_toml(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, 'allow_pii = ["cpf"]\n')
    s = load_settings(
        env={"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_ALLOW_PII": ""}, config_path=cfg
    )
    assert s.allow_pii == frozenset()


@pytest.mark.parametrize(
    ("profile", "raw_sql", "enabled"),
    [
        (Profile.REMOTE, False, False),
        (Profile.REMOTE, True, False),
        (Profile.LOCAL, False, False),
        (Profile.LOCAL, True, True),
    ],
)
def test_raw_sql_needs_local_profile_and_flag(
    tmp_path: Path, profile: Profile, raw_sql: bool, enabled: bool
) -> None:
    env = {"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_RAW_SQL": "1" if raw_sql else "0"}
    s = load_settings(env=env, config_path=tmp_path / "nao.toml", profile=profile)
    assert s.raw_sql is raw_sql
    assert s.raw_sql_enabled is enabled


def test_profile_cannot_come_from_file_or_env(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, 'profile = "local"\n')
    with pytest.raises(ConfigError, match="profile"):
        load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=cfg)
    s = load_settings(
        env={"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_PROFILE": "local"},
        config_path=tmp_path / "nao.toml",
    )
    assert s.profile is Profile.REMOTE


def test_unknown_keys_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="raw_sqll"):
        load_settings(
            env={"DOMINIO_MCP_HOME": str(tmp_path)},
            config_path=write_toml(tmp_path, "raw_sqll = true\n"),
        )
    with pytest.raises(ConfigError, match="max_row"):
        load_settings(
            env={"DOMINIO_MCP_HOME": str(tmp_path)},
            config_path=write_toml(tmp_path, "[limits]\nmax_row = 5\n"),
        )


@pytest.mark.parametrize(
    "dsn", ["DSN=contabil;UID=a;PWD=segredo123", "contabil;PWD=x", "a=b", "", "  ", "x" * 200]
)
def test_dsn_must_be_a_plain_name_and_is_never_echoed(tmp_path: Path, dsn: str) -> None:
    env = {"DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_DSN": dsn}
    with pytest.raises(ConfigError) as exc:
        load_settings(env=env, config_path=tmp_path / "nao.toml")
    assert "segredo123" not in str(exc.value)
    assert "PWD" not in str(exc.value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("max_rows", HARD_MAX_ROWS + 1),
        ("max_rows_aggregate", HARD_MAX_ROWS_AGGREGATE + 1),
        ("max_columns", HARD_MAX_COLUMNS + 1),
        ("max_response_bytes", HARD_MAX_RESPONSE_BYTES + 1),
        ("query_timeout_seconds", 31),
        ("default_rows", 0),
        ("max_rows", -1),
        ("cancel_confirm_seconds", 0),
        ("executions_per_minute", 121),
        ("executions_per_minute", 0),
        ("plan_cost_budget", 101),
        ("plan_rows_budget", 10_000_001),
    ],
)
def test_limits_respect_hard_caps_and_positive(tmp_path: Path, key: str, value: int) -> None:
    cfg = write_toml(tmp_path, f"[limits]\n{key} = {value}\n")
    with pytest.raises(ConfigError, match=key):
        load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=cfg)


def test_default_rows_cannot_exceed_max_rows(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, "[limits]\ndefault_rows = 60\nmax_rows = 50\n")
    with pytest.raises(ConfigError, match="default_rows"):
        load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=cfg)


@pytest.mark.parametrize(
    "body",
    [
        'raw_sql = "false"\n',
        "raw_sql = 1\n",
        'allow_pii = "cpf"\n',
        "allow_pii = [1]\n",
        "dsn = 5\n",
        '[limits]\nmax_rows = "10"\n',
        "[limits]\nmax_rows = true\n",
    ],
)
def test_toml_types_are_strict(tmp_path: Path, body: str) -> None:
    with pytest.raises(ConfigError):
        load_settings(
            env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=write_toml(tmp_path, body)
        )


def test_bad_env_values_are_rejected(tmp_path: Path) -> None:
    for var, value in [
        ("DOMINIO_MCP_RAW_SQL", "talvez"),
        ("DOMINIO_MCP_ALLOW_PII", "cpf,senha"),
    ]:
        with pytest.raises(ConfigError):
            load_settings(
                env={"DOMINIO_MCP_HOME": str(tmp_path), var: value},
                config_path=tmp_path / "nao.toml",
            )


def test_unknown_pii_category_is_rejected_in_toml(tmp_path: Path) -> None:
    cfg = write_toml(tmp_path, 'allow_pii = ["cpf", "tudo"]\n')
    with pytest.raises(ConfigError, match="tudo"):
        load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=cfg)


def test_pii_categories_are_the_documented_closed_set() -> None:
    assert (
        frozenset(
            {"cpf", "folha", "endereco", "contato", "bancario", "nascimento", "nome", "documento"}
        )
        == PII_CATEGORIES
    )


def test_malformed_toml_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="TOML"):
        load_settings(
            env={"DOMINIO_MCP_HOME": str(tmp_path)},
            config_path=write_toml(tmp_path, "dsn = = 1\n"),
        )


def test_settings_are_immutable(tmp_path: Path) -> None:
    s = load_settings(env={"DOMINIO_MCP_HOME": str(tmp_path)}, config_path=tmp_path / "nao.toml")
    assert isinstance(s, Settings)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.raw_sql = True  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.limits.max_rows = 1  # type: ignore[misc]
