"""Configuracao: TOML opcional mais variaveis DOMINIO_MCP_*, sempre falhando fechado.

Precedencia: argumento da CLI (so o perfil) > ambiente > arquivo TOML > padroes.

Decisoes de seguranca (D-317, D-326, D-327):

- O perfil (`remote` ou `local`) so vem da CLI (`serve --profile`). Nem o arquivo nem o ambiente o
  alteram, para que um processo iniciado por tunel ou gateway seja `remote` seja qual for a
  configuracao do escritorio.
- `raw_sql` so tem efeito no perfil `local` (`Settings.raw_sql_enabled`).
- O DSN e so o nome do DSN de sistema ODBC; a credencial fica no proprio DSN, nunca aqui.
- Chave desconhecida, tipo errado ou limite acima do teto duro e erro (nada de ignorar em silencio).
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

HARD_MAX_ROWS = 500
HARD_MAX_ROWS_AGGREGATE = 2000
HARD_MAX_COLUMNS = 40
HARD_MAX_RESPONSE_BYTES = 12 * 1024
HARD_QUERY_TIMEOUT_SECONDS = 30
HARD_CANCEL_CONFIRM_SECONDS = 60
HARD_EXECUTIONS_PER_MINUTE = 120
HARD_PLAN_COST_BUDGET = 100
HARD_PLAN_ROWS_BUDGET = 10_000_000

# Categorias que o dono do escritorio pode liberar em `allow_pii` (sempre com mascara).
PII_CATEGORIES = frozenset(
    {"cpf", "folha", "endereco", "contato", "bancario", "nascimento", "nome", "documento"}
)

_DSN_RE = re.compile(r"^[A-Za-z0-9_. -]{1,64}$")
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})
_TOP_KEYS = frozenset({"dsn", "raw_sql", "allow_pii", "limits"})
_LIMIT_KEYS = frozenset(
    {
        "default_rows",
        "max_rows",
        "max_rows_aggregate",
        "max_columns",
        "max_response_bytes",
        "query_timeout_seconds",
        "cancel_confirm_seconds",
        "executions_per_minute",
        "plan_cost_budget",
        "plan_rows_budget",
    }
)


class ConfigError(Exception):
    """Configuracao invalida. A mensagem nunca repete o valor de um DSN."""


class Profile(StrEnum):
    REMOTE = "remote"
    LOCAL = "local"


@dataclass(frozen=True, slots=True)
class Limits:
    default_rows: int = 50
    max_rows: int = HARD_MAX_ROWS
    max_rows_aggregate: int = HARD_MAX_ROWS_AGGREGATE
    max_columns: int = HARD_MAX_COLUMNS
    max_response_bytes: int = HARD_MAX_RESPONSE_BYTES
    query_timeout_seconds: int = HARD_QUERY_TIMEOUT_SECONDS
    cancel_confirm_seconds: int = 10
    executions_per_minute: int = 20
    plan_cost_budget: int = 10
    plan_rows_budget: int = 1_000_000


@dataclass(frozen=True, slots=True)
class Settings:
    dsn: str
    home: Path
    profile: Profile = Profile.REMOTE
    raw_sql: bool = False
    allow_pii: frozenset[str] = frozenset()
    limits: Limits = field(default_factory=Limits)
    config_file: Path | None = None

    @property
    def raw_sql_enabled(self) -> bool:
        """Unico ponto de decisao de L3: perfil local mais `raw_sql` ligado."""
        return self.profile is Profile.LOCAL and self.raw_sql


def default_home(env: Mapping[str, str]) -> Path:
    if env.get("DOMINIO_MCP_HOME"):
        return Path(env["DOMINIO_MCP_HOME"])
    if env.get("LOCALAPPDATA"):
        return Path(env["LOCALAPPDATA"]) / "dominio-mcp"
    if env.get("XDG_DATA_HOME"):
        return Path(env["XDG_DATA_HOME"]) / "dominio-mcp"
    base = Path(env["HOME"]) if env.get("HOME") else Path.home()
    return base / ".local" / "share" / "dominio-mcp"


def _check_dsn(value: object) -> str:
    if not isinstance(value, str) or not _DSN_RE.fullmatch(value.strip()):
        raise ConfigError(
            "dsn deve ser so o nome do DSN de sistema ODBC (letras, numeros, espaco, ponto, "
            "hifen e sublinhado, ate 64 caracteres); o valor nao e exibido"
        )
    return value.strip()


def _parse_bool_env(name: str, value: str) -> bool:
    text = value.strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ConfigError(f"{name} deve ser true ou false")


def _check_pii(items: object, where: str) -> frozenset[str]:
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise ConfigError(f"{where} deve ser uma lista de textos")
    return _normalize_pii([str(i) for i in items], where)


def _normalize_pii(items: list[str], where: str) -> frozenset[str]:
    cleaned = {i.strip().lower() for i in items if i.strip()}
    unknown = sorted(cleaned - PII_CATEGORIES)
    if unknown:
        shown = ", ".join(repr(u[:40]) for u in unknown)
        raise ConfigError(
            f"categoria desconhecida em {where}: {shown}; validas: {sorted(PII_CATEGORIES)}"
        )
    return frozenset(cleaned)


def _int_limit(key: str, value: object, cap: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"limits.{key} deve ser um inteiro")
    if value < 1:
        raise ConfigError(f"limits.{key} deve ser maior que zero")
    if value > cap:
        raise ConfigError(f"limits.{key} passa do teto duro de {cap}")
    return value


def _build_limits(raw: object) -> Limits:
    if raw is None:
        return Limits()
    if not isinstance(raw, dict):
        raise ConfigError("limits deve ser uma tabela TOML")
    unknown = sorted(set(raw) - _LIMIT_KEYS)
    if unknown:
        raise ConfigError(f"chave desconhecida em limits: {unknown[0]!r}")
    caps = {
        "default_rows": HARD_MAX_ROWS,
        "max_rows": HARD_MAX_ROWS,
        "max_rows_aggregate": HARD_MAX_ROWS_AGGREGATE,
        "max_columns": HARD_MAX_COLUMNS,
        "max_response_bytes": HARD_MAX_RESPONSE_BYTES,
        "query_timeout_seconds": HARD_QUERY_TIMEOUT_SECONDS,
        "cancel_confirm_seconds": HARD_CANCEL_CONFIRM_SECONDS,
        "executions_per_minute": HARD_EXECUTIONS_PER_MINUTE,
        "plan_cost_budget": HARD_PLAN_COST_BUDGET,
        "plan_rows_budget": HARD_PLAN_ROWS_BUDGET,
    }
    values = {k: _int_limit(k, v, caps[k]) for k, v in raw.items()}
    limits = Limits(**values)
    if limits.default_rows > limits.max_rows:
        raise ConfigError("limits.default_rows nao pode passar de limits.max_rows")
    if limits.max_rows > limits.max_rows_aggregate:
        raise ConfigError("limits.max_rows nao pode passar de limits.max_rows_aggregate")
    return limits


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"nao consegui ler {path}: {exc.strerror}") from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML invalido em {path}: {exc}") from exc


def load_settings(
    *,
    env: Mapping[str, str] | None = None,
    config_path: Path | None = None,
    profile: Profile = Profile.REMOTE,
) -> Settings:
    environ: Mapping[str, str] = os.environ if env is None else env
    home = default_home(environ)

    explicit_required = False
    if config_path is None:
        from_env = environ.get("DOMINIO_MCP_CONFIG")
        if from_env:
            config_path = Path(from_env)
            explicit_required = True
        else:
            config_path = home / "config.toml"

    data: dict[str, Any] = {}
    loaded: Path | None = None
    if config_path.is_file():
        data = _read_toml(config_path)
        loaded = config_path
    elif explicit_required:
        raise ConfigError("DOMINIO_MCP_CONFIG aponta para um arquivo que nao existe")

    if "profile" in data:
        raise ConfigError("profile so vem de `serve --profile`, nao do arquivo de configuracao")
    unknown = sorted(set(data) - _TOP_KEYS)
    if unknown:
        raise ConfigError(f"chave desconhecida no TOML: {unknown[0]!r}")

    dsn = _check_dsn(data["dsn"]) if "dsn" in data else "contabil"
    if "raw_sql" in data:
        if not isinstance(data["raw_sql"], bool):
            raise ConfigError("raw_sql deve ser true ou false (booleano TOML)")
        raw_sql = data["raw_sql"]
    else:
        raw_sql = False
    allow_pii = _check_pii(data["allow_pii"], "allow_pii") if "allow_pii" in data else frozenset()
    limits = _build_limits(data.get("limits"))

    if "DOMINIO_MCP_DSN" in environ:
        dsn = _check_dsn(environ["DOMINIO_MCP_DSN"])
    if "DOMINIO_MCP_RAW_SQL" in environ:
        raw_sql = _parse_bool_env("DOMINIO_MCP_RAW_SQL", environ["DOMINIO_MCP_RAW_SQL"])
    if "DOMINIO_MCP_ALLOW_PII" in environ:
        allow_pii = _normalize_pii(
            environ["DOMINIO_MCP_ALLOW_PII"].split(","), "DOMINIO_MCP_ALLOW_PII"
        )

    return Settings(
        dsn=dsn,
        home=home,
        profile=profile,
        raw_sql=raw_sql,
        allow_pii=allow_pii,
        limits=limits,
        config_file=loaded,
    )
