# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.intelligence.sync import record_schema_snapshot
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Descobre metadados ODBC Domínio com limite; não imprime tabelas, colunas ou dados."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--dsn", required=True, help="Nome do DSN de sistema ODBC, sem senha")
        parser.add_argument("--prefix", default="", help="Prefixo opcional de objeto Domínio")
        parser.add_argument(
            "--limit", type=int, default=50, help="Máximo de objetos (1 a 500; padrão 50)"
        )
        parser.add_argument(
            "--include-views", action="store_true", help="Inclui views ODBC no inventário"
        )
        parser.add_argument(
            "--apply", action="store_true", help="Persiste somente metadados para revisão"
        )

    def handle(self, *args, **options) -> None:
        limit = int(options["limit"])
        if not 1 <= limit <= 500:
            raise CommandError("--limit deve estar entre 1 e 500.")
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        adapter = ReadOnlyDominoOdbc(options["dsn"])
        try:
            tables = adapter.list_catalog_tables(
                prefix=options["prefix"], include_views=bool(options["include_views"])
            )[:limit]
            objects = [
                (table, adapter.list_catalog_columns(table_name=table.object_name))
                for table in tables
            ]
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        column_count = sum(len(columns) for _, columns in objects)
        self.stdout.write(
            self.style.SUCCESS(
                "Descoberta limitada concluída: "
                f"{len(objects)} objeto(s), {column_count} coluna(s)."
            )
        )
        if not options["apply"]:
            self.stdout.write(
                "Nada foi persistido. Revise o limite e execute novamente com --apply."
            )
            return
        result = record_schema_snapshot(organization=organization, objects=objects)
        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo salvo para revisão: "
                f"{result.created} novo(s), {result.updated} alterado(s), "
                f"{result.unchanged} sem alteração."
            )
        )
