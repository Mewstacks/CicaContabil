"""Backtest of the triage engine over a labelled dataset (JSON list of rows)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.organizations.models import Organization
from apps.triage.backtest import FIELDS, run_backtest

LABELS = {"company": "Empresa", "type": "Tipo", "period": "Período"}


def pct(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


class Command(BaseCommand):
    help = "Prints accuracy and coverage of the engine for one office over a labelled set."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="slug of the office")
        parser.add_argument("--dataset", required=True, help="JSON file: list of labelled rows")

    def handle(self, *args: Any, **options: Any) -> None:
        office = Organization.objects.filter(slug=options["organization"]).first()
        if office is None:
            raise CommandError("Escritório não encontrado.")
        try:
            rows = json.loads(Path(options["dataset"]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError("Conjunto ilegível: use um arquivo JSON com uma lista.") from exc
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise CommandError("Conjunto inválido: esperada uma lista de linhas.")
        report = run_backtest(office, rows)
        self.stdout.write(f"Linhas: {report.rows}")
        for key in FIELDS:
            stats = report.fields[key]
            self.stdout.write(
                f"{LABELS[key]}: Acurácia {pct(stats.accuracy)} "
                f"({stats.correct}/{stats.answered}) · Cobertura {pct(stats.coverage)} "
                f"({stats.answered}/{stats.total})"
            )
        self.stdout.write(f"Empresa errada: {report.wrong_company}")
