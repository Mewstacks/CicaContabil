"""D-378: reproducible, read-only choice of additional D-73 bank facts (synthetic only)."""

from __future__ import annotations

import json
import os
from datetime import date
from io import StringIO

import pytest
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.audit.models import AuditEvent
from apps.hub.models import NormalizedMovement
from apps.hub.reconciliation_acceptance import (
    prepare_acceptance_sample,
    select_acceptance_movements,
)
from apps.organizations.models import Membership
from test_reconciliation_acceptance import acceptance as acceptance_fixture

acceptance = acceptance_fixture
pytestmark = pytest.mark.django_db


def select(acceptance, *, seed="seed-a", size=50, months=None):
    account, actor, _, _ = acceptance
    return select_acceptance_movements(
        account=account, actor=actor, seed=seed, size=size, months=months or []
    )


def test_same_seed_and_population_give_the_same_distinct_selection(acceptance):
    before = AuditEvent.objects.count()
    first, manifest = select(acceptance)
    second, again = select(acceptance)
    assert first == second and manifest == again
    assert len(first) == len(set(first)) == 50
    assert manifest["population_distinct_facts"] == 200
    assert manifest["counts_as_d73_sample"] is False
    other, _ = select(acceptance, seed="seed-b")
    assert set(other) != set(first)
    assert AuditEvent.objects.count() == before


def test_already_frozen_facts_are_excluded_from_new_selection(acceptance):
    account, actor, _, ids = acceptance
    prepare_acceptance_sample(account=account, actor=actor, movement_ids=ids[:163], release="r1")
    chosen, manifest = select(acceptance, size=200)
    assert manifest["excluded_already_frozen"] == 163
    assert manifest["selected"] == 37
    assert set(chosen).isdisjoint(ids[:163])
    sample = prepare_acceptance_sample(
        account=account, actor=actor, movement_ids=chosen, release="r1"
    )
    assert len(sample.metadata["facts"]) == 37


def test_month_filter_limits_population(acceptance):
    _, _, _, ids = acceptance
    NormalizedMovement.objects.filter(pk__in=ids[:120]).update(occurred_on=date(2026, 9, 10))
    NormalizedMovement.objects.filter(pk__in=ids[120:]).update(occurred_on=date(2026, 10, 3))
    chosen, manifest = select(acceptance, size=200, months=["2026-10"])
    assert manifest["population_distinct_facts"] == 80
    assert set(chosen) <= set(ids[120:])


@pytest.mark.parametrize(
    "kwargs",
    [{"size": 0}, {"size": 1001}, {"months": ["2026-13"]}, {"months": ["2026-09", "2026-09"]}],
)
def test_invalid_selection_is_refused(acceptance, kwargs):
    with pytest.raises(ValueError):
        select(acceptance, **kwargs)


def test_selection_requires_current_access(acceptance):
    account, actor, _, _ = acceptance
    Membership.objects.filter(user=actor, organization_id=account.organization_id).update(
        is_active=False
    )
    with pytest.raises(PermissionDenied):
        select(acceptance)


def test_command_writes_private_input_consumable_by_prepare(acceptance, tmp_path):
    account, actor, _, _ = acceptance
    target = tmp_path / "selection.json"
    out = StringIO()
    base = [
        "reconciliation_acceptance",
        f"--organization={account.organization_id}",
        f"--account={account.pk}",
        f"--actor={actor.pk}",
    ]
    call_command(
        *base,
        "select",
        "--seed=public-seed",
        "--size=20",
        f"--output={target}",
        stdout=out,
    )
    manifest = json.loads(out.getvalue())
    payload = json.loads(target.read_text())
    assert set(payload) == {"movement_ids"} and len(payload["movement_ids"]) == 20
    assert manifest["seed"] == "public-seed" and manifest["selected"] == 20
    assert oct(os.stat(target).st_mode & 0o777) == "0o600"
    worksheet = tmp_path / "worksheet.json"
    call_command(
        *base,
        "prepare",
        "--release=synthetic",
        f"--input={target}",
        f"--output={worksheet}",
        stdout=StringIO(),
    )
    assert len(json.loads(worksheet.read_text())["facts"]) == 20
    with pytest.raises(CommandError):
        call_command(*base, "select", "--seed=x", f"--output={target}", stdout=StringIO())
