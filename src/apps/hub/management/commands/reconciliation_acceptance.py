"""Record and measure a D-73 sample without asserting ERP or release acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.common.private_artifacts import write_private_json
from apps.hub.models import FinancialAccount
from apps.hub.reconciliation_acceptance import (
    acceptance_report,
    acceptance_review_packet,
    prepare_acceptance_sample,
    review_acceptance_sample,
)
from apps.intelligence.native_title_contract import strict_json


class Command(BaseCommand):
    help = "Congela previsões, registra revisão do proprietário e mede fatos/precisão/tempo."

    def add_arguments(self, parser: Any) -> None:
        for name in ("organization", "account", "actor"):
            parser.add_argument(f"--{name}", required=True)
        actions = parser.add_subparsers(dest="action", required=True)
        prepare = actions.add_parser("prepare")
        prepare.add_argument("--release", required=True)
        prepare.add_argument("--input", required=True, help="JSON com movement_ids.")
        prepare.add_argument("--output", required=True, help="Arquivo privado para revisão.")
        review = actions.add_parser("review")
        review.add_argument("--sample", required=True)
        review.add_argument(
            "--input", required=True, help="JSON com expected e evidence_reference."
        )
        report = actions.add_parser("report")
        report.add_argument("--release", required=True)
        report.add_argument("--run", action="append", default=[])

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=options["account"], organization_id=options["organization"]
            )
            actor = User.objects.get(pk=options["actor"], is_active=True)
            payload = None
            if options.get("input"):
                with Path(options["input"]).open("rb") as stream:
                    payload = strict_json(stream.read(1_000_001), maximum=1_000_000)
            if options["action"] == "prepare":
                if not isinstance(payload, dict) or set(payload) != {"movement_ids"}:
                    raise ValueError
                sample = prepare_acceptance_sample(
                    account=account,
                    actor=actor,
                    movement_ids=payload["movement_ids"],
                    release=options["release"],
                )
                write_private_json(
                    options["output"],
                    acceptance_review_packet(
                        account=account, actor=actor, sample_id=str(sample.pk)
                    ),
                )
                result = {
                    "sample_id": str(sample.pk),
                    "distinct_facts": len(sample.metadata["facts"]),
                    "requires_owner_review": True,
                }
            elif options["action"] == "review":
                if (
                    not isinstance(payload, dict)
                    or not {"expected", "evidence_reference"}.issubset(payload)
                    or ("sample_id" in payload and payload["sample_id"] != options["sample"])
                    or ("facts" in payload and not isinstance(payload["facts"], list))
                    or (
                        "requires_owner_review" in payload
                        and payload["requires_owner_review"] is not True
                    )
                    or set(payload)
                    - {
                        "expected",
                        "evidence_reference",
                        "facts",
                        "sample_id",
                        "requires_owner_review",
                    }
                ):
                    raise ValueError
                review = review_acceptance_sample(
                    account=account,
                    actor=actor,
                    sample_id=options["sample"],
                    expected=payload["expected"],
                    evidence_reference=payload["evidence_reference"],
                    expected_source_facts=payload.get("facts"),
                )
                result = {"review_id": str(review.pk), "release_accepted": False}
            else:
                result = acceptance_report(
                    account=account, actor=actor, release=options["release"], run_ids=options["run"]
                )
        except (ValueError, TypeError, KeyError, OSError, ObjectDoesNotExist, PermissionDenied):
            raise CommandError(
                "Confira acesso, amostra, revisão do proprietário e processamentos."
            ) from None
        self.stdout.write(json.dumps(result, ensure_ascii=False))
