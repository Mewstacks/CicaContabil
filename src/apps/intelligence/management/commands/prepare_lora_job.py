# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.training import qlora_job_spec
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Prepara o contrato reproduzível de treino QLoRA para um runner GPU privado."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--base-model", required=True, help="Modelo local base aprovado")
        parser.add_argument("--adapter", required=True, help="Nome imutável do adaptador de saída")
        parser.add_argument(
            "--template", required=True, help="Template de chat compatível com o modelo base"
        )
        parser.add_argument("--output", required=True, help="Arquivo JSON de especificação do job")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            spec = qlora_job_spec(
                organization=organization,
                base_model=options["base_model"],
                adapter_name=options["adapter"],
                chat_template=options["template"],
            )
            output = Path(options["output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Job QLoRA preparado: {spec['corpus_version']} ({spec['example_count']} exemplos)."
            )
        )
