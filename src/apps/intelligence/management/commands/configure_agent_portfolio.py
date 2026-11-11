"""Prepare or explicitly apply a reviewed pilot-to-portfolio transition."""

from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.portfolio_configuration import (
    INVENTORY_LIMIT,
    REVIEW_LIMIT,
    configure_portfolio,
)
from apps.organizations.selectors import resolve_organization


def _read(path: str, limit: int) -> bytes:
    with Path(path).open("rb") as stream:
        return stream.read(limit + 1)


class Command(BaseCommand):
    help = "Prévia da carteira companies; --apply exige inventário e revisão explícitos."

    def add_arguments(self, parser: ArgumentParser) -> None:
        for name in (
            "organization",
            "agent",
            "expected-scope-revision",
            "inventory",
            "review",
            "period-end",
        ):
            parser.add_argument("--" + name, required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Filtrar ativas na origem; exige agente 1.0.6+.",
        )
        parser.add_argument(
            "--existing-active-selector",
            action="store_true",
            help="Revisão técnica restrita ao filtro A já existente; sem atribuir revisor humano.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        import json

        organization = resolve_organization(options["organization"])
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        try:
            result = configure_portfolio(
                organization=organization,
                agent_id=UUID(options["agent"]),
                expected_revision=options["expected_scope_revision"],
                inventory_raw=_read(options["inventory"], INVENTORY_LIMIT),
                review_raw=_read(options["review"], REVIEW_LIMIT),
                period_end=date.fromisoformat(options["period_end"]),
                apply=options["apply"],
                active_only=options["active_only"],
                allow_existing_active_selector=options["existing_active_selector"],
            )
        except OSError as exc:
            raise CommandError("Não foi possível ler os arquivos locais de evidência.") from exc
        except (ValueError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, sort_keys=True))
