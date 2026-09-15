# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.intelligence.models import IntelligenceConnector
from apps.intelligence.sync import sync_companies
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Testa a consulta Domínio allowlisted; use --apply somente após validar o resultado."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--dsn", required=True, help="Nome do DSN de sistema ODBC, sem senha")
        parser.add_argument("--apply", action="store_true", help="Espelha empresas após o probe")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            rows = ReadOnlyDominoOdbc(options["dsn"]).execute("companies")
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(f"Consulta allowlisted concluída: {len(rows)} empresa(s).")
        )
        if not options["apply"]:
            self.stdout.write(
                "Nada foi espelhado. Revise a contagem e execute novamente com --apply."
            )
            return
        connector, _ = IntelligenceConnector.objects.get_or_create(
            organization=organization, mode=IntelligenceConnector.Mode.DIRECT_ODBC
        )
        connector.odbc_dsn = options["dsn"]
        connector.save(update_fields=["odbc_dsn", "updated_at"])
        result = sync_companies(organization=organization, connector=connector, rows=rows)
        self.stdout.write(
            self.style.SUCCESS(
                "Espelho atualizado: "
                f"{result.created} criado(s), {result.updated} atualizado(s), "
                f"{result.ignored} ignorado(s)."
            )
        )
