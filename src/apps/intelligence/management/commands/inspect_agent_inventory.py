"""Validate supplied metadata without pretending that a human reviewed its semantics."""

import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.portfolio_configuration import INVENTORY_LIMIT, validate_inventory


class Command(BaseCommand):
    help = "Confere estrutura/hash/contagens do inventário local, sem banco, escrita ou aprovação."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--inventory", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with Path(options["inventory"]).open("rb") as stream:
                result = validate_inventory(stream.read(INVENTORY_LIMIT + 1))
        except OSError as exc:
            raise CommandError("Não foi possível ler o inventário local.") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            json.dumps(
                {
                    "read_only": True,
                    "semantics_approved": False,
                    **{
                        key: result[key]
                        for key in (
                            "inventory_sha256",
                            "inventory_observed_at",
                            "object_count",
                            "column_count",
                            "company_count",
                            "status_counts",
                        )
                    },
                },
                sort_keys=True,
            )
        )
