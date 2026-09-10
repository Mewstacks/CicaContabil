from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from apps.intelligence.connectors import ReadOnlyDominoOdbc


class FakeCursor:
    description = [("codigo",), ("nome",)]

    def __init__(self) -> None:
        self.timeout = 0
        self.executed: list[str] = []

    def execute(self, operation: str) -> None:
        self.executed.append(operation)

    def fetchmany(self, size: int):
        assert size == 500
        return [("001", "Empresa Acme")]

    def tables(self, **kwargs):
        return [
            SimpleNamespace(table_schem="dbo", table_name="geempre", table_type="TABLE"),
            SimpleNamespace(table_schem="dbo", table_name="geview", table_type="VIEW"),
        ]

    def columns(self, **kwargs):
        assert kwargs == {"table": "geempre"}
        return [
            SimpleNamespace(
                column_name="codigo", type_name="varchar", ordinal_position=1, nullable=0
            ),
            SimpleNamespace(
                column_name="nome", type_name="varchar", ordinal_position=2, nullable=1
            ),
        ]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self):
        return self._cursor


class OdbcConnectorTests(TestCase):
    def setUp(self) -> None:
        self.cursor = FakeCursor()
        self.calls: list[tuple[str, bool, int]] = []

        def factory(dsn: str, *, autocommit: bool, timeout: int):
            self.calls.append((dsn, autocommit, timeout))
            return FakeConnection(self.cursor)

        self.adapter = ReadOnlyDominoOdbc("Dominio64", connection_factory=factory)

    def test_only_registry_queries_reach_odbc(self) -> None:
        rows = self.adapter.execute("companies")

        self.assertEqual(rows, [{"codigo": "001", "nome": "Empresa Acme"}])
        self.assertEqual(self.calls, [("DSN=Dominio64", True, 10)])
        self.assertIn("SELECT TOP 500", self.cursor.executed[0])
        with self.assertRaisesRegex(ValueError, "não permitida"):
            self.adapter.execute("SELECT * FROM geempre")
        self.assertEqual(len(self.calls), 1)

    def test_catalog_uses_odbc_metadata_with_bounded_validated_identifiers(self) -> None:
        tables = self.adapter.list_catalog_tables(prefix="gee")
        columns = self.adapter.list_catalog_columns(table_name="geempre")

        self.assertEqual(
            [(table.schema_name, table.object_name) for table in tables], [("dbo", "geempre")]
        )
        self.assertEqual(
            [(column.name, column.nullable) for column in columns],
            [("codigo", False), ("nome", True)],
        )
        with self.assertRaisesRegex(ValueError, "Tabela inválido"):
            self.adapter.list_catalog_columns(table_name="geempre; DROP TABLE geempre")
        with self.assertRaisesRegex(ValueError, "DSN inválido"):
            ReadOnlyDominoOdbc("Dominio64;UID=DBA")
