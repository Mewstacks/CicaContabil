"""Governed read-only adapters for Domínio through SQL Anywhere ODBC.

No API, MCP tool, model, or database row can supply SQL to this module. The
only data queries are named entries in ``QUERY_REGISTRY``; discovery uses the
ODBC metadata API instead of querying arbitrary system tables.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, cast

MAX_CATALOG_TABLES = 500
MAX_CATALOG_COLUMNS = 250
MAX_COMPANY_ROWS = 1_000
MAX_BANK_ENTRY_ROWS = 10_000
_DSN_RE = re.compile(r"^[A-Za-z0-9 _.-]{1,128}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,127}$")


class CursorProtocol(Protocol):
    description: Any

    def execute(self, operation: str) -> Any: ...
    def fetchmany(self, size: int) -> Iterable[tuple[Any, ...]]: ...
    def tables(self, **kwargs: Any) -> Iterable[Any]: ...
    def columns(self, **kwargs: Any) -> Iterable[Any]: ...


class ConnectionProtocol(Protocol):
    def __enter__(self) -> ConnectionProtocol: ...
    def __exit__(self, *args: Any) -> None: ...
    def cursor(self) -> CursorProtocol: ...


ConnectionFactory = Callable[..., ConnectionProtocol]


@dataclass(frozen=True)
class QuerySpec:
    sql: str
    max_rows: int


@dataclass(frozen=True)
class CatalogTable:
    schema_name: str
    object_name: str
    object_kind: str


@dataclass(frozen=True)
class CatalogColumn:
    name: str
    type_name: str
    ordinal: int
    nullable: bool | None


QUERY_REGISTRY: dict[str, QuerySpec] = {
    "companies": QuerySpec(
        sql=(
            "SELECT TOP 1000 codi_emp AS codigo, nome_emp AS nome, cgce_emp AS cnpj "
            "FROM bethadba.geempre WHERE stat_emp = 'A' ORDER BY nome_emp"
        ),
        max_rows=MAX_COMPANY_ROWS,
    ),
    "communications": QuerySpec(
        sql=(
            "SELECT TOP 1000 SEQUENCIAL AS source_id, EMPRESA AS company_code, "
            "ASSUNTO AS subject, TIPO AS type_code, SITUACAO AS status_code, "
            "VISUALIZADO AS is_read "
            "FROM bethadba.GENOTIFICACOES_USUARIO_ATENDIMENTO ORDER BY SEQUENCIAL DESC"
        ),
        max_rows=MAX_COMPANY_ROWS,
    ),
    "bank_entries": QuerySpec(
        sql=(
            "SELECT TOP 10000 "
            "CAST(i.CODI_EMP AS VARCHAR(64)) || '|' || "
            "CAST(i.I_LANCAMENTO AS VARCHAR(64)) || '|' || "
            "CAST(i.I_ITEM AS VARCHAR(64)) AS source_id, i.CODI_EMP AS company_code, "
            "i.DATA_ITEM AS occurred_on, i.HISTORICO AS description, i.VALOR AS amount, "
            "i.TIPO AS direction, "
            "CASE WHEN EXISTS (SELECT 1 FROM bethadba.CTEXTRATO_BANCARIO_LANCAMENTO_ITEM_LANCTO l "
            "WHERE l.CODI_EMP = i.CODI_EMP AND l.I_LANCAMENTO = i.I_LANCAMENTO "
            "AND l.I_ITEM = i.I_ITEM) "
            "THEN 1 ELSE 0 END AS is_linked "
            "FROM bethadba.CTEXTRATO_BANCARIO_LANCAMENTO_ITEM i "
            "ORDER BY i.DATA_ITEM DESC, i.CODI_EMP DESC, i.I_LANCAMENTO DESC, i.I_ITEM DESC"
        ),
        max_rows=MAX_BANK_ENTRY_ROWS,
    ),
}


def _safe_dsn(value: str) -> str:
    dsn = value.strip()
    if not _DSN_RE.fullmatch(dsn):
        raise ValueError("DSN inválido. Informe somente o nome do DSN de sistema.")
    return dsn


def _safe_identifier(value: str, *, field: str) -> str:
    identifier = value.strip()
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"{field} inválido para descoberta de catálogo.")
    return identifier


def _metadata_value(row: object, name: str, position: int, default: object = "") -> object:
    """Read pyodbc metadata rows by stable attribute, with tuple fallback for tests."""
    value = getattr(row, name, None)
    if value is not None:
        return value
    if isinstance(row, tuple) and len(row) > position:
        return row[position]
    return default


def _format_cnpj(value: object) -> str:
    """Normalize a company identifier for authorized operational use."""
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 14:
        return ""
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _company_snapshot(columns: list[str], row: tuple[Any, ...]) -> dict[str, str]:
    """Normalize the one approved company query before raw ODBC values leave this adapter."""
    raw = dict(zip(columns, row, strict=True))
    return {
        "codigo": str(raw.get("codigo") or "").strip(),
        "nome": str(raw.get("nome") or "").strip(),
        "cnpj_masked": _format_cnpj(raw.get("cnpj")),
    }


def _communication_snapshot(columns: list[str], row: tuple[Any, ...]) -> dict[str, object]:
    """Project only the approved non-personal notification fields from Domínio."""
    raw = dict(zip(columns, row, strict=True))
    return {
        "source_id": str(raw.get("source_id") or "").strip(),
        "company_code": str(raw.get("company_code") or "").strip(),
        "subject": str(raw.get("subject") or "").strip(),
        "type_code": str(raw.get("type_code") or "").strip(),
        "status_code": str(raw.get("status_code") or "").strip(),
        "is_read": raw.get("is_read"),
    }


def _bank_entry_snapshot(columns: list[str], row: tuple[Any, ...]) -> dict[str, object]:
    """Project the verified Domínio bank-statement schema only."""
    raw = dict(zip(columns, row, strict=True))
    return {
        "source_id": str(raw.get("source_id") or "").strip(),
        "company_code": str(raw.get("company_code") or "").strip(),
        "occurred_on": raw.get("occurred_on"),
        "description": str(raw.get("description") or "").strip(),
        "amount": raw.get("amount"),
        "direction": str(raw.get("direction") or "").strip(),
        "is_linked": raw.get("is_linked"),
    }


class ReadOnlyDominoOdbc:
    """Private-network ODBC bridge with a fixed query and metadata contract."""

    def __init__(self, dsn: str, *, connection_factory: ConnectionFactory | None = None) -> None:
        self.dsn = _safe_dsn(dsn)
        self._connection_factory = connection_factory

    def _connect(self) -> ConnectionProtocol:
        if self._connection_factory is not None:
            return self._connection_factory(f"DSN={self.dsn}", autocommit=True, timeout=10)
        try:
            import pyodbc  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - deployment-only dependency
            raise RuntimeError("O driver ODBC do agente não está instalado.") from exc
        return cast(
            ConnectionProtocol,
            pyodbc.connect(f"DSN={self.dsn}", autocommit=True, timeout=10),
        )

    def execute(self, query_name: str) -> list[dict[str, Any]]:
        """Run one source-controlled query; caller-supplied SQL is impossible."""
        spec = QUERY_REGISTRY.get(query_name)
        if spec is None:
            raise ValueError("Consulta Domínio não permitida.")
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(spec.sql)
            columns = [str(column[0]) for column in (cursor.description or ())]
            rows = list(cursor.fetchmany(spec.max_rows))
        if query_name == "companies":
            return [_company_snapshot(columns, row) for row in rows]
        if query_name == "communications":
            return [_communication_snapshot(columns, row) for row in rows]
        if query_name == "bank_entries":
            return [_bank_entry_snapshot(columns, row) for row in rows]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def list_catalog_tables(
        self, *, prefix: str = "", include_views: bool = False
    ) -> list[CatalogTable]:
        """Read bounded ODBC metadata without exposing it to a model or MCP client."""
        normalized_prefix = prefix.strip().casefold()
        if normalized_prefix and not _IDENTIFIER_RE.fullmatch(prefix.strip()):
            raise ValueError("Prefixo de catálogo inválido.")
        allowed_types = {"TABLE"}
        if include_views:
            allowed_types.add("VIEW")
        tables: list[CatalogTable] = []
        with self._connect() as connection:
            cursor = connection.cursor()
            for row in cursor.tables():
                object_kind = str(_metadata_value(row, "table_type", 3)).upper()
                object_name = str(_metadata_value(row, "table_name", 2)).strip()
                schema_name = str(_metadata_value(row, "table_schem", 1)).strip()
                if object_kind not in allowed_types or not object_name:
                    continue
                if normalized_prefix and not object_name.casefold().startswith(normalized_prefix):
                    continue
                tables.append(CatalogTable(schema_name, object_name, object_kind.lower()))
                if len(tables) >= MAX_CATALOG_TABLES:
                    break
        return tables

    def list_catalog_columns(self, *, table_name: str) -> list[CatalogColumn]:
        """Read a single validated object's columns through ODBC metadata."""
        table_name = _safe_identifier(table_name, field="Tabela")
        columns: list[CatalogColumn] = []
        with self._connect() as connection:
            cursor = connection.cursor()
            for row in cursor.columns(table=table_name):
                name = str(_metadata_value(row, "column_name", 3)).strip()
                if not name:
                    continue
                nullable_value = _metadata_value(row, "nullable", 10, None)
                nullable = bool(nullable_value) if nullable_value is not None else None
                raw_ordinal = _metadata_value(row, "ordinal_position", 16, 0)
                try:
                    ordinal = int(str(raw_ordinal))
                except (TypeError, ValueError):
                    ordinal = 0
                columns.append(
                    CatalogColumn(
                        name=name,
                        type_name=str(_metadata_value(row, "type_name", 5)).strip()[:96],
                        ordinal=max(0, ordinal),
                        nullable=nullable,
                    )
                )
                if len(columns) >= MAX_CATALOG_COLUMNS:
                    break
        return columns
