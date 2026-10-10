from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.integra.catalog import SERVICES, service
from apps.integra.client import IntegraClient, credentials_from_settings
from apps.integra.errors import IntegraError


class Command(BaseCommand):
    help = "Call one catalogued Integra Contador service and print what came back."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--service", default="dte.situacao", choices=sorted(SERVICES))
        parser.add_argument("--contribuinte", required=True, help="CPF or CNPJ, any punctuation")
        parser.add_argument("--dados", default="", help="JSON object for the service parameters")
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Confirma a chamada externa. Sem esta opção, o comando somente mostra a prévia.",
        )
        parser.add_argument(
            "--approve-billable-production",
            action="store_true",
            help="Confirma custo para serviço faturável no ambiente de produção.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            credentials = credentials_from_settings()
        except IntegraError as exc:
            raise CommandError(str(exc)) from exc
        spec = service(options["service"])
        dados = json.loads(options["dados"]) if options["dados"] else None

        self.stdout.write(f"Ambiente:    {credentials.environment}")
        self.stdout.write(f"Serviço:     {spec.label} ({spec.id_sistema}/{spec.id_servico})")
        self.stdout.write(f"Verbo:       {spec.verb.value}")
        self.stdout.write(f"Faturável:   {'sim' if spec.billable else 'não'}")
        if spec.billable:
            self.stdout.write(
                self.style.WARNING("Esta chamada é faturada pelo Serpro em produção.")
            )
        if not options["execute"]:
            self.stdout.write(
                self.style.WARNING(
                    "Prévia concluída sem chamada externa. Use --execute para confirmar a execução."
                )
            )
            return
        if (
            credentials.environment == "production"
            and spec.billable
            and not options["approve_billable_production"]
        ):
            raise CommandError(
                "Serviço faturável em produção exige --approve-billable-production."
            )

        try:
            payload = IntegraClient(credentials).call(
                spec.key, contribuinte=options["contribuinte"], dados=dados
            )
        except IntegraError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Resposta:"))
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
