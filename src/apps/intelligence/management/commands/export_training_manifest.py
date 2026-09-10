# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.training import training_manifest
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Exporta JSONL validado para treino local, sem misturar escritórios."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--output", required=True, help="Arquivo JSONL de saída")

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        manifest = training_manifest(organization=organization)
        if not manifest:
            raise CommandError("Não há exemplos validados com fonte para exportar.")
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as stream:
            for item in manifest:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.stdout.write(self.style.SUCCESS(f"{len(manifest)} exemplo(s) exportado(s)."))
