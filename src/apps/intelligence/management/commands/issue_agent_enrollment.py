# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

from datetime import date

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.agents import issue_enrollment
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Gera código único de 30 minutos para instalar um agente Domínio."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--minutes", type=int, default=30)
        parser.add_argument("--financial-account", help="UUID da conta do piloto autorizado")
        parser.add_argument("--period-start", help="Início da competência (AAAA-MM-DD)")
        parser.add_argument("--period-end", help="Fim da competência (AAAA-MM-DD)")
        parser.add_argument(
            "--statement-id",
            action="append",
            default=[],
            help="I_LANCAMENTO revisado na origem; repetir para cada extrato",
        )

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            scope = None
            if any(
                options[key]
                for key in ("financial_account", "period_start", "period_end", "statement_id")
            ):
                from apps.hub.models import FinancialAccount
                from apps.intelligence.agent_scope import build_sync_scope

                account = FinancialAccount.objects.select_related("company").get(
                    pk=options["financial_account"], organization=organization
                )
                scope = build_sync_scope(
                    account=account,
                    start=date.fromisoformat(options["period_start"]),
                    end=date.fromisoformat(options["period_end"]),
                    statement_ids=options["statement_id"],
                )
            credentials = issue_enrollment(
                organization=organization, valid_for_minutes=options["minutes"], sync_scope=scope
            )
        except (ValueError, TypeError, ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Código: {credentials.code}")
        self.stdout.write(f"Expira: {credentials.expires_at.isoformat()}")
