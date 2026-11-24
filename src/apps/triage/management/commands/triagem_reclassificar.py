"""Reclassify an office's pending items with the current engine (optionally bumping the version)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.organizations.models import Organization
from apps.triage.reclassify import bump_engine_version, reclassify_pending


class Command(BaseCommand):
    help = "Reclassify pending items of one office; --bump raises its engine version first."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True, help="slug of the office")
        parser.add_argument("--bump", action="store_true", help="raise the engine version")

    def handle(self, *args: Any, **options: Any) -> None:
        office = Organization.objects.filter(slug=options["organization"]).first()
        if office is None:
            raise CommandError("Escritório não encontrado.")
        if options["bump"]:
            self.stdout.write(f"Versão do motor: {bump_engine_version(office)}")
        else:
            self.stdout.write(f"Itens alterados: {reclassify_pending(office)}")
