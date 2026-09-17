"""Validate the bounded Domínio ODBC contract without printing source data."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import record_event
from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.organizations.selectors import resolve_organization

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "geempre": {"codi_emp", "nome_emp", "cgce_emp", "stat_emp"},
    "GENOTIFICACOES_USUARIO_ATENDIMENTO": {
        "sequencial",
        "empresa",
        "assunto",
        "tipo",
        "situacao",
        "visualizado",
    },
    "CTEXTRATO_BANCARIO_LANCAMENTO_ITEM": {
        "codi_emp",
        "i_lancamento",
        "i_item",
        "data_item",
        "historico",
        "valor",
        "tipo",
    },
    "CTEXTRATO_BANCARIO_LANCAMENTO_ITEM_LANCTO": {
        "codi_emp",
        "i_lancamento",
        "i_item",
    },
    "FOVGUIAINSS": {
        "i_guiainss",
        "codi_emp",
        "competencia",
        "vencimento",
        "total_guia",
        "tipo_guia",
        "tipo_process",
        "situacao",
    },
}


class Command(BaseCommand):
    help = (
        "Valida consultas allowlisted e schema Domínio sem exibir nem persistir dados de origem."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--dsn", required=True, help="Nome do DSN de sistema, sem senha")

    def handle(self, *args: object, **options: object) -> None:
        organization = resolve_organization(str(options["organization"]))
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        adapter = ReadOnlyDominoOdbc(str(options["dsn"]))
        try:
            query_counts = {
                query_name: len(adapter.execute(query_name))
                for query_name in ("companies", "communications", "bank_entries", "guide_calculations")
            }
            missing_by_table: dict[str, int] = {}
            for table_name, required_columns in REQUIRED_COLUMNS.items():
                columns = {
                    column.name.casefold()
                    for column in adapter.list_catalog_columns(table_name=table_name)
                }
                missing_by_table[table_name] = len(required_columns - columns)
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        missing_total = sum(missing_by_table.values())
        record_event(
            action="intelligence.dominio.odbc_contract_validated",
            organization=organization,
            metadata={
                "queries": len(query_counts),
                "objects": len(REQUIRED_COLUMNS),
                "rows_read": sum(query_counts.values()),
                "missing_columns": missing_total,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Contrato ODBC validado: "
                f"{len(query_counts)} consulta(s), {len(REQUIRED_COLUMNS)} objeto(s), "
                f"{sum(query_counts.values())} linha(s) lida(s), {missing_total} coluna(s) ausente(s)."
            )
        )
        if missing_total:
            raise CommandError("O schema Domínio não atende ao contrato aprovado.")
