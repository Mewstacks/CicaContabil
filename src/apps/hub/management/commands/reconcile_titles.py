"""Private operator workflow for normalized titles; no ERP SQL, posting or matching."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.hub.models import (
    FinancialAccount,
    ReconciliationTitleAllocation,
    ReconciliationTitleBatch,
    ReconciliationTitleSnapshot,
)
from apps.hub.reconciliation_service import MAX_BYTES
from apps.hub.title_contract import TitleContractError
from apps.hub.title_persistence import (
    confirm_title_allocations,
    import_title_snapshot,
    prepare_title_allocations,
    title_plan_review,
    undo_title_allocation,
)


def _read(path: str) -> bytes:
    with Path(path).open("rb") as stream:
        content = stream.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise TitleContractError("Arquivo de entrada vazio ou maior que 25 MiB.")
    return content


def _json(path: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("JSON com membro duplicado.")
            result[key] = value
        return result

    return json.loads(_read(path).decode("utf-8"), object_pairs_hook=unique)


def _private_output(path: str, payload: dict[str, Any]) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode()
    if len(content) > MAX_BYTES:
        raise TitleContractError("Arquivo de revisão excede o limite; reduza o lote.")
    # Refuse overwrite/symlinks, including existing review files from an earlier run.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)


class Command(BaseCommand):
    help = "Importa títulos normalizados e revisa/confirma/desfaz vínculos; sem acesso ao ERP."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--account", required=True)
        parser.add_argument("--actor", required=True, help="UUID do usuário revisor do escritório.")
        actions = parser.add_subparsers(dest="action", required=True)
        importer = actions.add_parser("import")
        importer.add_argument("--input", required=True)
        importer.add_argument("--evidence", required=True)
        preview = actions.add_parser("preview")
        preview.add_argument("--snapshot", required=True)
        preview.add_argument("--requests", required=True)
        preview.add_argument("--start", required=True)
        preview.add_argument("--end", required=True)
        preview.add_argument("--output", required=True)
        confirmer = actions.add_parser("confirm")
        confirmer.add_argument("--plan", required=True)
        confirmer.add_argument("--request-id", required=True)
        confirmer.add_argument("--evidence", required=True)
        confirmer.add_argument("--accept-date-differences", action="store_true")
        undo = actions.add_parser("undo")
        undo.add_argument("--allocation", required=True)
        undo.add_argument("--reason", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=UUID(options["account"]), organization_id=UUID(options["organization"])
            )
            actor = User.objects.get(pk=UUID(options["actor"]), is_active=True)
            result = self._execute(options, account, actor)
        except (
            ValueError,
            TypeError,
            KeyError,
            OSError,
            PermissionDenied,
            ObjectDoesNotExist,
            RecursionError,
        ) as error:
            if isinstance(error, TitleContractError):
                raise CommandError(str(error)) from None
            raise CommandError(
                "Operação não concluída; confira acesso, escopo e arquivos privados."
            ) from None
        self.stdout.write(json.dumps(result, ensure_ascii=False))

    def _execute(
        self, options: dict[str, Any], account: FinancialAccount, actor: User
    ) -> dict[str, Any]:
        action = options["action"]
        if action == "import":
            snapshot, created = import_title_snapshot(
                financial_account=account,
                content=_read(options["input"]),
                actor=actor,
                evidence_reference=options["evidence"],
            )
            return {
                "snapshot_id": str(snapshot.pk),
                "created": created,
                "fingerprint": snapshot.fingerprint,
                "settlements_complete": snapshot.settlements_complete,
            }
        if action == "undo":
            allocation = ReconciliationTitleAllocation.objects.get(
                pk=UUID(options["allocation"]),
                financial_account=account,
                organization_id=account.organization_id,
            )
            changed = undo_title_allocation(
                allocation=allocation, actor=actor, reason=options["reason"]
            )
            return {"allocation_id": str(allocation.pk), "state": "undone", "changed": changed}
        if action == "preview":
            snapshot = ReconciliationTitleSnapshot.objects.get(
                pk=UUID(options["snapshot"]),
                financial_account=account,
                organization_id=account.organization_id,
            )
            requests = _json(options["requests"])
            start, end = date.fromisoformat(options["start"]), date.fromisoformat(options["end"])
            plan = prepare_title_allocations(
                snapshot=snapshot,
                requests=requests,
                actor=actor,
                period_start=start,
                period_end=end,
            )
            _private_output(
                options["output"],
                {
                    "version": "title-reviewed-plan-v1",
                    "snapshot_id": str(snapshot.pk),
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "requests": requests,
                    "fingerprint": plan.fingerprint,
                    "review": title_plan_review(plan),
                },
            )
            return {
                "fingerprint": plan.fingerprint,
                "allocations": len(plan.preview.allocations),
                "date_differences": sum(a.date_difference for a in plan.preview.allocations),
                "requires_human_review": True,
            }
        payload = _json(options["plan"])
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "version",
                "snapshot_id",
                "period_start",
                "period_end",
                "requests",
                "fingerprint",
                "review",
            }
            or payload["version"] != "title-reviewed-plan-v1"
        ):
            raise TitleContractError("Arquivo de revisão fora do contrato.")
        snapshot = ReconciliationTitleSnapshot.objects.get(
            pk=UUID(payload["snapshot_id"]),
            financial_account=account,
            organization_id=account.organization_id,
        )
        start, end = (
            date.fromisoformat(payload["period_start"]),
            date.fromisoformat(payload["period_end"]),
        )
        receipt = ReconciliationTitleBatch.objects.filter(
            organization_id=account.organization_id,
            financial_account=account,
            request_id=UUID(options["request_id"]),
        ).first()
        if receipt:
            expected_review = receipt.review_snapshot
        else:
            expected_review = title_plan_review(
                prepare_title_allocations(
                    snapshot=snapshot,
                    requests=payload["requests"],
                    actor=actor,
                    period_start=start,
                    period_end=end,
                )
            )
        if payload["review"] != expected_review:
            raise TitleContractError("A conferência do arquivo mudou; gere e revise outra prévia.")
        batch, created = confirm_title_allocations(
            snapshot=snapshot,
            requests=payload["requests"],
            actor=actor,
            period_start=start,
            period_end=end,
            request_id=UUID(options["request_id"]),
            preview_fingerprint=payload["fingerprint"],
            evidence_reference=options["evidence"],
            accept_date_differences=options["accept_date_differences"],
        )
        return {
            "batch_id": str(batch.pk),
            "created": created,
            "allocations": batch.allocations.count(),
            "erp_written": False,
        }
