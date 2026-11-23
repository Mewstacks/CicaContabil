"""Opaque internal keys remain stable while the human sees verified source references."""

from datetime import date
from unittest.mock import patch

import pytest

from apps.audit.models import AuditEvent
from apps.hub.models import CompanyAccessGrant
from apps.hub.title_labels import enrich_title_labels
from apps.hub.title_read_model import build_title_workspace
from apps.intelligence.native_title_review import confirm_native_review
from test_native_title_review import captured as captured_fixture
from test_native_title_review import prepare
from test_native_titles import fiscal as fiscal_fixture

captured = captured_fixture
fiscal_source = fiscal_fixture
pytestmark = pytest.mark.django_db


def workspace(captured):
    account, actor, _, _ = captured
    return build_title_workspace(
        account=account,
        actor=actor,
        start=date(2026, 9, 1),
        end=date(2026, 9, 30),
    )


def test_readable_labels_use_reviewed_source_without_changing_keys_or_finance(captured):
    account, actor, _, _ = captured
    arguments, _ = prepare(captured)
    confirm_native_review(**arguments)
    data = workspace(captured)
    keys = [
        (r["title_key"], r["installment_key"], r["settlement_key"], r["cash_cents"])
        for r in data["settlement_rows"]
    ]
    audits = AuditEvent.objects.count()
    enrich_title_labels(data=data, account=account, actor=actor)
    assert data["installment_rows"][0]["title_label"] == "Entradas · título 0001/A"
    assert data["installment_rows"][0]["installment_label"] == "1"
    assert {r["settlement_label"] for r in data["settlement_rows"]} == {"Baixa 1", "Baixa 2"}
    assert keys == [
        (r["title_key"], r["installment_key"], r["settlement_key"], r["cash_cents"])
        for r in data["settlement_rows"]
    ]
    assert AuditEvent.objects.count() == audits


def test_auditor_does_not_read_raw_source_for_labels(captured, membership):
    account, actor, _, _ = captured
    arguments, _ = prepare(captured)
    confirm_native_review(**arguments)
    membership.role = "auditor"
    membership.save(update_fields=["role"])
    CompanyAccessGrant.objects.create(
        organization=account.organization,
        membership=membership,
        company=account.company,
        modules=["reconciliation"],
        capabilities=["bank_statements", "accounting_entries"],
    )
    data = workspace(captured)
    with patch("apps.hub.title_labels.load_native_source") as loader:
        enrich_title_labels(data=data, account=account, actor=actor)
    loader.assert_not_called()
    row = data["installment_rows"][0]
    assert row["title_label"] == "Título " + row["title_key"][:8]
    assert row["title_key"] not in row["label"]


def test_damaged_original_cannot_supply_display_identifiers(captured):
    account, actor, source, _ = captured
    arguments, _ = prepare(captured)
    confirm_native_review(**arguments)
    data = workspace(captured)
    source.capture.source_file.content.storage.delete(source.capture.source_file.content.name)
    enrich_title_labels(data=data, account=account, actor=actor)
    row = data["installment_rows"][0]
    assert row["title_label"].startswith("Título ")
    assert "0001/A" not in row["label"]
    assert {row["cash_cents"] for row in data["settlement_rows"]} == {3000, 4000}
