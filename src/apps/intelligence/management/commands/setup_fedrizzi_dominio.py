"""Provision the repeatable local Domínio test office without storing ODBC credentials."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.hub.models import OfficeProfile
from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.intelligence.models import IntelligenceConnector
from apps.intelligence.sync import sync_bank_entries, sync_communications, sync_companies
from apps.organizations.models import Organization

OFFICE_NAME = "Fedrizzi Contabilidade"
OFFICE_SLUG = "fedrizzi-contabilidade"


class Command(BaseCommand):
    help = (
        "Cria o escritório local de teste Fedrizzi Contabilidade e, opcionalmente, "
        "espelha cadastros pelo DSN ODBC somente leitura."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--dsn",
            help="Nome do DSN de sistema ODBC. Não aceita connection string nem senha.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Executa a consulta de cadastros allowlisted e atualiza o espelho local.",
        )

    def handle(self, *args: object, **options: object) -> None:
        dsn = str(options.get("dsn") or "").strip()
        sync = bool(options["sync"])
        if sync and not dsn:
            raise CommandError("Informe --dsn para usar --sync.")

        office, created = Organization.objects.get_or_create(
            slug=OFFICE_SLUG,
            defaults={"name": OFFICE_NAME, "is_active": True},
        )
        OfficeProfile.objects.get_or_create(
            organization=office,
            defaults={"legal_name": OFFICE_NAME},
        )
        connector, connector_created = IntelligenceConnector.objects.get_or_create(
            organization=office,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
        )
        if dsn and connector.odbc_dsn != dsn:
            connector.odbc_dsn = dsn
            connector.save(update_fields=["odbc_dsn", "updated_at"])
        state = "criado" if created else "já existente"
        connector_state = "criado" if connector_created else "já existente"
        self.stdout.write(
            self.style.SUCCESS(
                f"Escritório {OFFICE_NAME} {state}; conector ODBC direto {connector_state}."
            )
        )
        if not sync:
            self.stdout.write(
                "Nenhuma leitura ODBC foi executada. Use --dsn <nome> --sync para testar."
            )
            return

        try:
            adapter = ReadOnlyDominoOdbc(dsn)
            company_rows = adapter.execute("companies")
            communication_rows = adapter.execute("communications")
            bank_entry_rows = adapter.execute("bank_entries")
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        result = sync_companies(organization=office, connector=connector, rows=company_rows)
        communications = sync_communications(
            organization=office,
            connector=connector,
            rows=communication_rows,
        )
        bank_entries = sync_bank_entries(
            organization=office,
            connector=connector,
            rows=bank_entry_rows,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Cadastros sincronizados sem identificadores brutos: "
                f"{result.created} criado(s), {result.updated} atualizado(s), "
                f"{result.ignored} ignorado(s)."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Itens bancários sincronizados: "
                f"{bank_entries.created} criado(s), {bank_entries.updated} atualizado(s), "
                f"{bank_entries.ignored} ignorado(s)."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Comunicados sincronizados sem CPF, usuário ou responsável: "
                f"{communications.created} criado(s), {communications.updated} atualizado(s), "
                f"{communications.ignored} ignorado(s)."
            )
        )
