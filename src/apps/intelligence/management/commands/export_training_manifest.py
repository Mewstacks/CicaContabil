# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.models import TrainingExample
from apps.intelligence.training import evaluation_manifest, training_manifest
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Exporta JSONL validado para treino local, sem misturar escritórios."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--output", required=True, help="Arquivo JSONL de saída")
        parser.add_argument(
            "--split",
            choices=TrainingExample.DatasetSplit.values,
            default=TrainingExample.DatasetSplit.TRAINING,
            help="Exporta somente o conjunto de treino ou de avaliação.",
        )

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            manifest = (
                training_manifest(organization=organization)
                if options["split"] == TrainingExample.DatasetSplit.TRAINING
                else evaluation_manifest(organization=organization)
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        if not manifest:
            raise CommandError("Não há exemplos validados com fonte para exportar.")
        output = Path(options["output"])
        if output.exists():
            raise CommandError("O arquivo de saída já existe; use um novo caminho de manifesto.")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            stream = output.open("x", encoding="utf-8")
        except FileExistsError as exc:
            raise CommandError(
                "O arquivo de saída já existe; use um novo caminho de manifesto."
            ) from exc
        with stream:
            for item in manifest:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.stdout.write(self.style.SUCCESS(f"{len(manifest)} exemplo(s) exportado(s)."))
