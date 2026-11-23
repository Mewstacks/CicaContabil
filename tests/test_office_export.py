"""Exportação do escritório (E4, LGPD): só leitura, sem segredo, sem dado de outro escritório."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub import offboarding
from apps.hub.company_roster import (
    PREVIEW_RETENTION,
    REPORT_RETENTION,
    purge_roster_artifacts,
)
from apps.hub.models import (
    Certificate,
    ClientCompany,
    ImportBatch,
    NfseDocument,
    OfficeCertificate,
)
from apps.hub.offboarding import (
    HUB_EXCLUDED,
    export_office,
    exported_fields,
    exported_models,
    hub_models_with_organization,
)
from apps.organizations.models import Organization
from test_company_roster import CSV_HEADER, NEW_A, csv_file
from test_nfse_procuracao import OFFICE_CNPJ
from test_nfse_procuracao_views import World

SECRET = "SEGREDO-NAO-PODE-SAIR-9f3a"
XML = "<NFSe><infNFSe><nNFSe>77</nNFSe></infNFSe></NFSe>"


def seeded(world: World) -> None:
    now = timezone.now()
    Certificate.objects.create(
        organization=world.office,
        company=world.padaria,
        label="A1 da padaria",
        pfx_blob=SECRET + "-pfx",
        password=SECRET + "-senha",
        fingerprint_sha256="a" * 64,
    )
    OfficeCertificate.objects.create(
        organization=world.office,
        label="e-CNPJ",
        cnpj=OFFICE_CNPJ,
        pfx_blob=SECRET + "-office-pfx",
        password=SECRET + "-office-senha",
        fingerprint_sha256="b" * 64,
        valid_from=now - timedelta(days=5),
        valid_until=now + timedelta(days=300),
    )
    NfseDocument.objects.create(
        organization=world.office,
        company=world.padaria,
        source_nsu="1",
        document_hash=hashlib.sha256(XML.encode()).hexdigest(),
        original_xml=XML,
        issued_at=datetime(2026, 11, 1, tzinfo=UTC),
    )


def read_zip(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


@pytest.fixture
def world(db: object) -> World:
    return World()


# ---------------------------------------------------------------- contrato do registro


@pytest.mark.django_db
def test_every_hub_model_of_an_office_is_exported_or_excluded_with_a_reason() -> None:
    exported = {model.__name__ for model in exported_models()}
    every = {model.__name__ for model in hub_models_with_organization()}

    assert every == exported | set(HUB_EXCLUDED)  # modelo novo sem decisão derruba este teste
    assert set(HUB_EXCLUDED) <= every
    assert all(reason.strip() for reason in HUB_EXCLUDED.values())


@pytest.mark.django_db
def test_secret_looking_fields_are_cut_and_business_fields_are_kept() -> None:
    kept, cut = exported_fields(Certificate)

    assert {"pfx_blob", "password", "fingerprint_sha256"} & set(kept) == set()
    assert {"pfx_blob", "password", "fingerprint_sha256"} <= set(cut)
    assert {"label", "valid_until", "company", "revoked_at"} <= set(kept)
    document_kept, document_cut = exported_fields(NfseDocument)
    assert "original_xml" in document_kept and "document_hash" in document_cut


# ---------------------------------------------------------------- o pacote


@pytest.mark.django_db
def test_the_package_has_the_business_data_and_never_a_secret(world: World, tmp_path: Path) -> None:
    seeded(world)
    destination = tmp_path / "pacote.zip"

    result = export_office(world.office, destination)

    files = read_zip(destination)
    assert "manifest.json" in files and "team.jsonl" in files
    assert SECRET not in "".join(files.values())
    assert "a" * 64 not in files["hub.Certificate.jsonl"]  # nem o fingerprint
    assert "Padaria Central" in files["hub.ClientCompany.jsonl"]
    assert XML in files["hub.NfseDocument.jsonl"]  # o XML fiscal é do cliente: sai em claro
    assert result.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()


@pytest.mark.django_db
def test_the_manifest_counts_match_the_database_and_say_what_was_left_out(
    world: World, tmp_path: Path
) -> None:
    seeded(world)
    destination = tmp_path / "pacote.zip"

    export_office(world.office, destination)

    manifest = json.loads(read_zip(destination)["manifest.json"])
    assert manifest["format"] == "cica-export-1" and manifest["organization"] == "tela"
    assert (
        manifest["models"]["hub.ClientCompany"]["rows"]
        == ClientCompany.objects.filter(organization=world.office).count()
        == 3
    )
    assert "pfx_blob" in manifest["models"]["hub.Certificate"]["excluded_fields"]
    for key in ("hub.ControlPlaneBinding", "platform", "audit", "arquivos"):
        assert manifest["not_included"][key]


@pytest.mark.django_db
def test_the_team_lists_people_and_roles_without_any_credential(
    world: World, tmp_path: Path
) -> None:
    destination = tmp_path / "pacote.zip"

    export_office(world.office, destination)

    rows = [json.loads(line) for line in read_zip(destination)["team.jsonl"].splitlines()]
    assert {row["email"] for row in rows} == {
        "dono@example.test",
        "operador@example.test",
        "auditor@example.test",
    }
    assert {row["role"] for row in rows} == {"owner", "operator", "auditor"}
    text = read_zip(destination)["team.jsonl"]
    assert "password" not in text.lower() and "pbkdf2" not in text


@pytest.mark.django_db
def test_another_offices_data_never_enters_the_package(world: World, tmp_path: Path) -> None:
    stranger = Organization.objects.create(name="Vizinho", slug="vizinho-export")
    ClientCompany.objects.create(
        organization=stranger, name="Empresa Do Vizinho", cnpj_masked=NEW_A
    )
    destination = tmp_path / "pacote.zip"

    export_office(world.office, destination)

    assert "Empresa Do Vizinho" not in "".join(read_zip(destination).values())


@pytest.mark.django_db
def test_a_dry_run_counts_without_writing_and_both_are_audited(world: World) -> None:
    result = export_office(world.office, None)

    assert result.path is None and result.sha256 == ""
    assert result.models["hub.ClientCompany"].rows == 3
    event = AuditEvent.objects.get(action="hub.office.exported")
    assert event.metadata["dry_run"] is True and event.metadata["rows"] == result.total_rows


@pytest.mark.django_db
def test_exporting_changes_nothing_in_the_office(world: World, tmp_path: Path) -> None:
    seeded(world)
    before = {
        "companies": ClientCompany.objects.count(),
        "certificates": Certificate.objects.count(),
        "documents": NfseDocument.objects.count(),
    }

    export_office(world.office, tmp_path / "pacote.zip")

    assert before == {
        "companies": ClientCompany.objects.count(),
        "certificates": Certificate.objects.count(),
        "documents": NfseDocument.objects.count(),
    }


# ---------------------------------------------------------------- comando


@pytest.mark.django_db
def test_the_command_writes_the_zip_and_prints_the_hash(world: World, tmp_path: Path) -> None:
    out = io.StringIO()
    destination = tmp_path / "saida.zip"

    call_command("office_export", "tela", "--output", str(destination), stdout=out)

    text = out.getvalue()
    assert "hub.ClientCompany: 3" in text and "equipe: 3" in text
    assert f"sha256: {hashlib.sha256(destination.read_bytes()).hexdigest()}" in text


@pytest.mark.django_db
def test_the_command_demands_one_mode_a_known_office_and_a_new_file(
    world: World, tmp_path: Path
) -> None:
    existing = tmp_path / "ja-existe.zip"
    existing.write_bytes(b"x")

    with pytest.raises(CommandError, match="--output ou --dry-run"):
        call_command("office_export", "tela")
    with pytest.raises(CommandError, match="--output ou --dry-run"):
        call_command("office_export", "tela", "--dry-run", "--output", str(tmp_path / "a.zip"))
    with pytest.raises(CommandError, match="não encontrado"):
        call_command("office_export", "nao-existe", "--dry-run")
    with pytest.raises(CommandError, match="já existe"):
        call_command("office_export", "tela", "--output", str(existing))
    assert existing.read_bytes() == b"x"


@pytest.mark.django_db
def test_the_dry_run_command_prints_counts_and_no_file_line(world: World) -> None:
    out = io.StringIO()

    call_command("office_export", "tela", "--dry-run", stdout=out)

    assert "total:" in out.getvalue() and "arquivo:" not in out.getvalue()


def test_the_module_documents_that_erasure_is_not_executed_here() -> None:
    assert "Q-49" in (offboarding.__doc__ or "")


# ---------------------------------------------------------------- retenção da carteira


def roster_batch(world: World, name: str, **fields: Any) -> ImportBatch:
    from apps.hub.company_roster import create_roster_batch

    batch, _ = create_roster_batch(
        organization=world.office,
        upload=csv_file(CSV_HEADER + f"{name};{NEW_A};;\r\n", name=f"{name}.csv"),
        actor=world.owner,
    )
    if fields:
        ImportBatch.objects.filter(pk=batch.pk).update(**fields)
        batch.refresh_from_db()
    return batch


@pytest.mark.django_db
def test_a_forgotten_preview_disappears_after_seven_days_and_a_fresh_one_stays(
    world: World,
) -> None:
    old = roster_batch(
        world, "antiga", created_at=timezone.now() - PREVIEW_RETENTION - timedelta(hours=1)
    )
    fresh = roster_batch(world, "recente")

    outcome = purge_roster_artifacts()

    assert outcome["previews_discarded"] == 1
    assert not ImportBatch.objects.filter(pk=old.pk).exists()
    assert ImportBatch.objects.filter(pk=fresh.pk).exists()


@pytest.mark.django_db
def test_the_report_of_a_finished_import_is_cleared_after_thirty_days(world: World) -> None:
    from apps.hub.company_roster import apply_roster, batch_rows

    batch = roster_batch(world, "concluida")
    apply_roster(batch=batch, actor=world.owner)
    batch.refresh_from_db()
    assert batch_rows(batch)  # relatório guardado
    ImportBatch.objects.filter(pk=batch.pk).update(
        completed_at=timezone.now() - REPORT_RETENTION - timedelta(days=1)
    )

    outcome = purge_roster_artifacts()

    assert outcome["reports_cleared"] == 1
    batch.refresh_from_db()
    assert batch.encrypted_payload == "" and batch.created_count == 1  # os números ficam


@pytest.mark.django_db
def test_retention_never_touches_a_legacy_import_batch(world: World) -> None:
    from apps.hub.models import DataSource

    source = DataSource.objects.create(organization=world.office, kind="other_manual", label="M")
    legacy = ImportBatch.objects.create(
        organization=world.office,
        data_source=source,
        kind=ImportBatch.Kind.COMPANIES,
        original_filename="antigo.csv",
        content_hash="c" * 64,
        mapping={"company_id": ""},
        encrypted_payload="[]",
        status=ImportBatch.Status.PREVIEW,
    )
    ImportBatch.objects.filter(pk=legacy.pk).update(created_at=timezone.now() - timedelta(days=90))

    assert purge_roster_artifacts() == {"previews_discarded": 0, "reports_cleared": 0}
    assert ImportBatch.objects.filter(pk=legacy.pk).exists()
