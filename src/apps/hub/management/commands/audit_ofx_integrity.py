"""Read-only pre-pilot inspection; never repairs or homologates historical matches."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.hub.models import BankTransaction, DataSource, ReconciliationMatch
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Inspeciona integridade OFX de um escritório, sem alterar decisões ou dados."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True, help="UUID do escritório autorizado.")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            office = Organization.objects.get(pk=options["organization"])
        except (Organization.DoesNotExist, ValidationError, ValueError) as exc:
            raise CommandError("Escritório não encontrado.") from exc
        counts: Counter[str] = Counter()
        matches = ReconciliationMatch.objects.filter(
            organization=office,
            status=ReconciliationMatch.Status.MATCHED,
        ).select_related("transaction__statement", "accounting_entry__data_source", "dominio_entry")
        for match in matches.iterator():
            statement = match.transaction.statement
            entry = match.accounting_entry
            if match.dominio_entry_id or (
                entry
                and entry.data_source.kind
                in {
                    DataSource.Kind.DOMINIO_LOCAL_AGENT,
                    DataSource.Kind.DOMINIO_WEB_BACKUP,
                }
            ):
                counts["bank_mirror_without_ledger_proof"] += 1
            if entry is None:
                counts["missing_independent_accounting_entry"] += 1
                continue
            if (
                entry.organization_id != office.pk
                or entry.data_source.organization_id != office.pk
                or statement.organization_id != office.pk
                or match.transaction.organization_id != office.pk
                or entry.company_id != statement.company_id
            ):
                counts["scope_mismatch"] += 1
            expected = "inflow" if match.transaction.amount_cents > 0 else "outflow"
            if entry.direction != expected:
                counts["unknown_or_incompatible_direction"] += 1
            if (
                not entry.account_reference
                or entry.account_reference != statement.account_reference
            ):
                counts["missing_or_incompatible_account"] += 1
            if entry.occurred_on != match.transaction.occurred_on or entry.amount_cents != abs(
                match.transaction.amount_cents
            ):
                counts["date_or_amount_mismatch"] += 1
        reused = (
            matches.exclude(accounting_entry=None)
            .values("accounting_entry_id")
            .annotate(
                uses=Count("id"),
            )
            .filter(uses__gt=1)
            .count()
        )
        duplicate_groups = (
            BankTransaction.objects.filter(organization=office)
            .values(
                "statement__company_id",
                "statement__account_reference",
                "external_id",
            )
            .annotate(uses=Count("id"))
            .filter(uses__gt=1)
            .count()
        )
        counts["reused_candidate_groups"] = reused
        counts["duplicate_transaction_groups"] = duplicate_groups
        self.stdout.write(
            json.dumps(
                {
                    "organization_id": str(office.pk),
                    "matched_records_examined": matches.count(),
                    "issues": dict(counts),
                    "read_only": True,
                    "homologated": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
