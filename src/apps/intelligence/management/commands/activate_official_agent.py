"""Explicit administrative cutover after the new Windows host is verified."""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.agents import activate_official_replacement
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Ativa candidato oficial e revoga o agente anterior na mesma transação."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--candidate", required=True)
        parser.add_argument("--previous", required=True)
        parser.add_argument("--scope-revision", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        organization = resolve_organization(options["organization"])
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            candidate_id, previous_id = (
                str(UUID(options[key])) for key in ("candidate", "previous")
            )
            candidate = activate_official_replacement(
                organization=organization,
                candidate_id=candidate_id,
                previous_id=previous_id,
                scope_revision=options["scope_revision"],
            )
        except (ValueError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Agente oficial: {candidate.pk}; agente anterior revogado.")
