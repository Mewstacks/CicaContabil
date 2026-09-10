# mypy: disable-error-code="no-untyped-def"
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.training import record_evaluation
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Registra relatório de avaliação e aplica o gate de publicação da IA."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument(
            "--report", required=True, help="JSON com métricas sem prompts ou respostas brutas"
        )

    def handle(self, *args, **options) -> None:
        selector = options["organization"]
        organization = resolve_organization(selector)
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            report = json.loads(Path(options["report"]).read_text(encoding="utf-8"))
            if not isinstance(report, dict):
                raise ValueError("O JSON deve ser um objeto.")
            _, gate = record_evaluation(organization=organization, report=report)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        output = (
            f"acurácia={gate.accuracy_percent:.1f}% "
            f"fontes={gate.source_coverage_percent:.1f}% — {gate.reason}"
        )
        if not gate.passed:
            raise CommandError(output)
        self.stdout.write(self.style.SUCCESS(output))
