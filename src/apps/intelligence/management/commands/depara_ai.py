"""Prepare, generate once and review DE-PARA suggestions without ERP writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.common.private_artifacts import write_private_json
from apps.hub.models import FinancialAccount
from apps.intelligence.depara_ai import (
    depara_review_packet,
    generate_depara_ai,
    prepare_depara_ai,
    review_depara_ai,
)
from apps.intelligence.models import DeparaAiBatch
from apps.intelligence.native_title_contract import strict_json


class Command(BaseCommand):
    help = "DE-PARA: prévia local, chamada com teto/dados aprovados e revisão em rascunho."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "account", "actor"):
            parser.add_argument(f"--{name}", required=True)
        actions = parser.add_subparsers(dest="action", required=True)
        prepare = actions.add_parser("prepare")
        prepare.add_argument("--input", required=True)
        generate = actions.add_parser("generate")
        generate.add_argument("--batch", required=True)
        generate.add_argument("--max-request-cents", required=True, type=int)
        generate.add_argument("--allow-data-egress", action="store_true")
        review = actions.add_parser("review")
        review.add_argument("--batch", required=True)
        review.add_argument("--input", required=True)
        packet = actions.add_parser("review-packet")
        packet.add_argument("--batch", required=True)
        packet.add_argument("--output", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=options["account"], organization_id=options["organization"]
            )
            actor = User.objects.get(pk=options["actor"], is_active=True)
            payload = None
            if options.get("input"):
                with Path(options["input"]).open("rb") as stream:
                    payload = strict_json(stream.read(32_769), maximum=32_768)
            if options["action"] == "prepare":
                if not isinstance(payload, dict) or set(payload) != {"items", "candidate_codes"}:
                    raise ValueError
                batch, created = prepare_depara_ai(account=account, actor=actor, **payload)
                result = {
                    "batch_id": str(batch.pk),
                    "state": batch.state,
                    "created": created,
                    "provider_called": False,
                    "fingerprint": batch.fingerprint,
                }
            else:
                batch = DeparaAiBatch.objects.get(
                    pk=options["batch"],
                    financial_account=account,
                    organization_id=account.organization_id,
                )
                if options["action"] == "review-packet":
                    write_private_json(
                        options["output"], depara_review_packet(batch=batch, actor=actor)
                    )
                    result = {"batch_id": str(batch.pk), "review_file_created": True}
                elif options["action"] == "generate":
                    batch = generate_depara_ai(
                        batch=batch,
                        actor=actor,
                        max_request_cents=options["max_request_cents"],
                        allow_data_egress=options["allow_data_egress"],
                    )
                    result = {
                        "batch_id": str(batch.pk),
                        "state": batch.state,
                        "suggestions": len(batch.suggestions),
                        "requires_review": True,
                    }
                else:
                    if (
                        not isinstance(payload, dict)
                        or "choices" not in payload
                        or set(payload)
                        - {"choices", "context", "batch_id", "egress_id", "requires_human_review"}
                    ):
                        raise ValueError
                    reviewed = review_depara_ai(
                        batch=batch, actor=actor, choices=payload["choices"]
                    )
                    result = {
                        "batch_id": str(batch.pk),
                        "results": [vars(r) for r in reviewed],
                        "requires_activation": True,
                    }
        except (ValueError, TypeError, KeyError, OSError, ObjectDoesNotExist, PermissionDenied):
            raise CommandError(
                "Confira acesso, política de IA, teto, lote e arquivo de revisão."
            ) from None
        self.stdout.write(json.dumps(result, ensure_ascii=False))
