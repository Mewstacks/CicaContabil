from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.hub.management.commands.legacy_snapshot import compare_snapshots, take_snapshot
from apps.hub.models import ClientCompany, NfseSync, OfficeProfile, ProductModule
from apps.organizations.models import Organization


@pytest.fixture
def legacy_office(db: object) -> Organization:
    office = Organization.objects.create(name="Escritório Sigiloso", slug="legado-um")
    OfficeProfile.objects.create(organization=office, legal_name="Razão Sigilosa Ltda")
    ProductModule.objects.create(organization=office, code=ProductModule.Code.NFSE, enabled=True)
    company = ClientCompany.objects.create(
        organization=office, name="Cliente Sigiloso", cnpj_masked="12.345.678/0001-95"
    )
    NfseSync.objects.create(organization=office, company=company, enabled=True)
    return office


def test_snapshot_describes_the_office_without_names_or_cnpj(legacy_office: Organization) -> None:
    snapshot = take_snapshot()

    entry = snapshot["organizations"]["legado-um"]
    assert entry["config"]["modules"] == ["nfse"]
    assert entry["config"]["nfse_collection_mode"] == "certificate"
    assert entry["counts"]["companies"] == 1
    assert entry["counts"]["nfse_syncs"] == 1
    text = json.dumps(snapshot, ensure_ascii=False)
    for secret in ("Sigiloso", "12.345.678", "12345678000195"):
        assert secret not in text
    assert "hub_nfsesync" in snapshot["schema"]
    assert snapshot["table_rows"]["hub_nfsesync"] == 1


def test_identical_snapshots_have_no_violations(legacy_office: Organization) -> None:
    snapshot = take_snapshot()

    assert compare_snapshots(snapshot, copy.deepcopy(snapshot)) == []


def test_growth_is_allowed_but_loss_and_config_changes_are_not(
    legacy_office: Organization,
) -> None:
    before = take_snapshot()
    after: dict[str, Any] = copy.deepcopy(before)
    after["organizations"]["legado-um"]["counts"]["nfse_documents"] += 50
    after["table_rows"]["hub_nfsesync"] += 3
    assert compare_snapshots(before, after) == []

    broken: dict[str, Any] = copy.deepcopy(before)
    broken["organizations"]["legado-um"]["counts"]["companies"] = 0
    broken["organizations"]["legado-um"]["config"]["modules"] = []
    broken["organizations"]["legado-um"]["config"]["nfse_collection_mode"] = "procuracao"
    del broken["schema"]["hub_nfsesync"][0]
    problems = "\n".join(compare_snapshots(before, broken))
    assert "contagem companies caiu" in problems
    assert "configuração modules mudou" in problems
    assert "configuração nfse_collection_mode mudou" in problems
    assert "coluna alterada ou removida" in problems


def test_a_vanished_organization_is_a_violation(legacy_office: Organization) -> None:
    before = take_snapshot()
    after = copy.deepcopy(before)
    del after["organizations"]["legado-um"]

    assert compare_snapshots(before, after) == ["organização legado-um: desapareceu"]


def test_command_writes_a_file_and_compare_fails_only_on_violations(
    legacy_office: Organization, tmp_path: Path
) -> None:
    first = tmp_path / "antes.json"
    second = tmp_path / "depois.json"
    call_command("legacy_snapshot", output=str(first))
    call_command("legacy_snapshot", output=str(second))

    call_command("legacy_snapshot", compare=[str(first), str(second)])

    payload = json.loads(second.read_text(encoding="utf-8"))
    payload["organizations"]["legado-um"]["config"]["is_active"] = False
    second.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CommandError, match="violação"):
        call_command("legacy_snapshot", compare=[str(first), str(second)])


def test_a_table_the_database_does_not_have_yet_is_left_out_of_the_counts(
    legacy_office: Organization,
) -> None:
    from unittest.mock import patch

    from django.db import OperationalError

    from apps.hub.management.commands import legacy_snapshot as module

    class Missing:
        class _meta:
            db_table = "hub_ainda_nao_migrada"

        class _default_manager:
            @staticmethod
            def count() -> int:
                raise OperationalError("no such table: hub_ainda_nao_migrada")

    with patch.object(module, "_project_models", return_value=[*module._project_models(), Missing]):
        counts = module._row_counts()

    assert "hub_ainda_nao_migrada" not in counts
    assert counts["hub_nfsesync"] == 1
