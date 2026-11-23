"""Explicit reviewed per-account monthly jobs; defaults to read-only preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from apps.intelligence.native_ledger_contract import strict_json
from apps.intelligence.portfolio_ledger import VERSION, prepare_portfolio_ledger_batch


class Command(BaseCommand):
    help = "Prepara coleta mensal com plano/conta/contagens revisados; não descobre vínculos."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "agent", "account", "actor", "scope-file", "evidence"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--allow-financial-capture", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with Path(options["scope_file"]).open("rb") as stream:
                content = stream.read(32_769)
            if len(content) > 32_768:
                raise ValueError
            report = prepare_portfolio_ledger_batch(
                organization_id=options["organization"],
                agent_id=options["agent"],
                actor_id=options["actor"],
                manifest={
                    "version": VERSION,
                    "organization_id": options["organization"],
                    "agent_id": options["agent"],
                    "items": [{
                        "financial_account_id": options["account"],
                        "scope": strict_json(content),
                        "evidence_reference": options["evidence"],
                    }],
                },
                enqueue=options["allow_financial_capture"],
            )
            if not report["valid"]:
                raise ValueError
        except (ValueError, TypeError, OSError, ObjectDoesNotExist, PermissionDenied):
            raise CommandError("Confira acesso atual, conta, escopo e evidência privada.") from None
        item = report["items"][0]
        self.stdout.write(
            json.dumps(
                {
                    "queued": item["job_id"] is not None,
                    "created": item["created"],
                    "job_id": item["job_id"],
                    "scope_revision": item["scope_revision"],
                    "contract_hash": report["contract_hash"],
                    "requires_capability": "portfolio_scope",
                    "requires_source_review": True,
                }
            )
        )
