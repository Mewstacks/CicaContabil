"""Preflight reviewed monthly scopes together; explicit apply is atomic and replayable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.native_ledger_contract import MAX_BYTES, strict_json
from apps.intelligence.portfolio_ledger import PortfolioBatchError, prepare_portfolio_ledger_batch


class Command(BaseCommand):
    help = "Confere lote de contas/meses revisados; só enfileira com --allow-financial-capture."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "agent", "actor", "manifest-file"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--allow-financial-capture", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with Path(options["manifest_file"]).open("rb") as stream:
                manifest = strict_json(stream.read(MAX_BYTES + 1))
            report = prepare_portfolio_ledger_batch(
                organization_id=options["organization"],
                agent_id=options["agent"],
                actor_id=options["actor"],
                manifest=manifest,
                enqueue=options["allow_financial_capture"],
            )
        except PortfolioBatchError as error:
            self.stdout.write(json.dumps(error.report))
            raise CommandError(str(error)) from None
        except (ValueError, TypeError, OSError, ObjectDoesNotExist, PermissionDenied):
            raise CommandError("Confira acesso atual e manifesto privado da carteira.") from None
        self.stdout.write(json.dumps(report))
        if not report["valid"]:
            raise CommandError("Prévia com pendências; nenhuma coleta foi criada.")
