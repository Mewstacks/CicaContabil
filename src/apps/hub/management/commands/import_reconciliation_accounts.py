"""Register retained source candidates; never create bank accounts or financial jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.hub.account_candidates import AccountCandidateImportError, import_account_candidates
from apps.hub.portfolio_evidence import MAX_TRANSFER_BYTES
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Confere perfis retidos; --apply cadastra apenas candidatas com vínculo pendente."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True, help="UUID do escritório.")
        parser.add_argument("--portfolio-file", required=True)
        parser.add_argument("--accounts-file", required=True)
        parser.add_argument(
            "--request-reference", required=True, help="Referência técnica, ex. D-365."
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            organization = Organization.objects.get(pk=UUID(options["organization"]))
            inputs = {}
            for key in ("portfolio", "accounts"):
                with Path(options[f"{key}_file"]).open("rb") as stream:
                    inputs[f"{key}_raw"] = stream.read(MAX_TRANSFER_BYTES + 1)
            report = import_account_candidates(
                organization=organization,
                **inputs,
                request_reference=options["request_reference"],
                apply=options["apply"],
            )
        except AccountCandidateImportError as error:
            raise CommandError(str(error)) from None
        except (OSError, ValueError, TypeError, Organization.DoesNotExist, IntegrityError):
            raise CommandError(
                "Confira escritório, arquivos privados e referência; nenhuma candidata foi criada."
            ) from None
        # Keep identifiers, source flags, candidate snapshots and any human review out of logs.
        safe_keys = (
            "version",
            "valid",
            "company_count",
            "candidate_count",
            "companies_with_candidates",
            "to_create",
            "existing",
            "created",
            "applied",
            "manifest_sha256",
            "financial_accounts_created",
            "ledger_accounts_created",
            "financial_collection_enabled",
            "human_review_performed",
        )
        self.stdout.write(json.dumps({key: report[key] for key in safe_keys}))
