"""Readable references from the exact retained source of a human title review."""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import FinancialAccount, ReconciliationTitleSnapshot
from apps.hub.title_persistence import authorize_title_account
from apps.intelligence.native_title_comparison import _key
from apps.intelligence.native_title_contract import canonical_hash, manifest
from apps.intelligence.native_title_review import load_native_source, source_installments

ACTIONS = (
    "hub.reconciliation.native_title_ui_reviewed",
    "hub.reconciliation.native_titles_translated",
    "hub.reconciliation.native_titles_auto_interpreted",  # D-394/D-396
)


def _short(value: str, label: str) -> str:
    return f"{label} {value[:8]}" if re.fullmatch(r"[0-9a-f]{64}", value) else value


def enrich_title_labels(*, data: dict[str, Any], account: FinancialAccount, actor: User) -> None:
    """Keep opaque request keys intact; never interpret a component or select a match.

    Only the sources recorded in the snapshot lineage can supply display labels.
    Auditors keep the normalized references: this does not broaden raw-source access.
    A missing display source never changes normalized financial facts or capacities.
    """
    rows = [*data["installment_rows"], *data["settlement_rows"]]
    for row in rows:
        row["title_label"] = _short(row["title_key"], "Título")
        # The templates already say "Parcela"; the fallback is only the short code (D-396).
        row["installment_label"] = (
            row["installment_key"][:8]
            if re.fullmatch(r"[0-9a-f]{64}", row["installment_key"])
            else row["installment_key"]
        )
        if "settlement_key" in row:
            row["settlement_label"] = _short(row["settlement_key"], "Baixa")
        row["label"] = f"{row['title_label']} · parcela {row['installment_label']}"
        if "settlement_key" in row:
            row["label"] += (
                f" · {row['settlement_label']} · {row['posted_on']:%d/%m/%Y}"
                f" · {row['direction_label']} · total {row['cash_display']}"
            )
    snapshot = data.get("snapshot")
    if not snapshot or not rows:
        return
    try:
        authorize_title_account(account, actor)
    except (PermissionDenied, ValueError):
        return
    snapshots = ReconciliationTitleSnapshot.objects.filter(
        organization_id=account.organization_id,
        financial_account=account,
        company_id=account.company_id,
    )
    events = AuditEvent.objects.filter(
        organization_id=account.organization_id,
        target_type="hub.reconciliationtitlesnapshot",
        success=True,
        action__in=ACTIONS,
        target_id__in=[str(pk) for pk in snapshots.values_list("pk", flat=True)],
    ).order_by("-occurred_at", "-id")
    by_snapshot: dict[str, Any] = {}
    by_event: dict[str, Any] = {}
    for event in events:
        by_snapshot.setdefault(event.target_id, event)
        by_event[str(event.pk)] = event
    seen: set[str] = set()
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    sources: dict[str, Any] = {}
    event = by_snapshot.get(str(snapshot.pk))
    wanted = {(row["title_key"], row["installment_key"]) for row in rows}
    while event is not None and str(event.pk) not in seen and wanted - labels.keys():
        seen.add(str(event.pk))
        metadata = event.metadata
        previous_event = metadata.get("previous_review_event_id")
        event = (
            by_event.get(str(previous_event))
            if previous_event
            else by_snapshot.get(str(metadata.get("previous_snapshot_id") or ""))
        )
        provenance = metadata.get("provenance", [])
        if not isinstance(provenance, list):
            continue
        selected = [
            item
            for item in provenance
            if isinstance(item, dict)
            and (item.get("title_key"), item.get("installment_key")) in wanted - labels.keys()
        ]
        if not selected:
            continue
        capture = metadata.get("capture_id")
        try:
            if capture not in sources:
                sources[capture] = load_native_source(
                    account=account,
                    capture_id=capture,
                    actor=actor,
                )
            source = sources[capture]
            if source.evidence.expected_sha256 != metadata.get("source_sha256"):
                continue
            parts = {part["reference"]: part for part in source_installments(source)}
            for item in selected:
                part = parts.get(item["installment_key"])
                if part is None:
                    continue
                spec = manifest()["families"][part["family"]]
                raw = part["raw"]
                if item["title_key"] != canonical_hash(
                    [
                        part["family"],
                        (raw["codi_emp"], raw[spec["note_field"]]),
                    ]
                ):
                    continue
                original = next(
                    (
                        str(value).strip()
                        for key, value in raw.items()
                        if key.startswith("numero_titulo_") and value is not None
                    ),
                    "",
                )
                title_label = f"{part['family_label']} · " + (
                    f"título {original}" if original else f"nota {part['note']}"
                )
                family = next(f for f in source.raw["families"] if f["name"] == part["family"])
                payments = {
                    canonical_hash([part["family"], "payments", _key(p, spec, "payments")]): p
                    for p in family["payments"]
                }
                payment_labels = {}
                for payment in item.get("settlements", []):
                    references = payment.get("payment_references", [])
                    if not references or canonical_hash(sorted(references)) != payment.get(
                        "settlement_key"
                    ):
                        continue
                    numbers = {
                        payments[ref][spec["payment_number_field"]]
                        for ref in references
                        if ref in payments
                    }
                    if len(numbers) == 1 and all(ref in payments for ref in references):
                        payment_labels[payment["settlement_key"]] = f"Baixa {next(iter(numbers))}"
                labels[(item["title_key"], item["installment_key"])] = {
                    "title_label": title_label,
                    "installment_label": str(part["number"]),
                    "payments": payment_labels,
                }
        except (PermissionDenied, ValueError, KeyError, TypeError):
            continue
    for row in rows:
        found = labels.get((row["title_key"], row["installment_key"]))
        if found:
            row.update(
                title_label=found["title_label"], installment_label=found["installment_label"]
            )
            if "settlement_key" in row:
                row["settlement_label"] = found["payments"].get(
                    row["settlement_key"], row["settlement_label"]
                )
        row["label"] = f"{row['title_label']} · parcela {row['installment_label']}"
        if "settlement_key" in row:
            row["label"] += (
                f" · {row['settlement_label']} · {row['posted_on']:%d/%m/%Y}"
                f" · {row['direction_label']} · total {row['cash_display']}"
            )
