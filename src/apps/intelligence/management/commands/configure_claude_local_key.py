"""Legacy command: verify Mewstack's central Claude secret without printing it."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Verifica CICA_CLAUDE_API_KEY no ambiente; n?o grava chaves por escrit?rio."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=False, help="Par?metro legado; ignorado")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.CICA_CLAUDE_API_KEY:
            raise CommandError("Defina CICA_CLAUDE_API_KEY no .env da Mewstack.")
        self.stdout.write(self.style.SUCCESS("Chave Claude central configurada no ambiente."))
