"""Closing management commands: layout import from HubFedrizzi and waiting re-check."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.closing import services
from apps.closing.models import ClosingConference, ClosingDocument, ClosingLayout
from apps.hub.models import FiscalGuide, OperationalActivity
from closing_support import (
    das_text,
    make_activity,
    make_company,
    make_guide,
    make_layout,
    make_office,
    make_user,
    txt_upload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = tmp_path


EXPORT = {
    "layouts": [
        {
            "sigla": "PGDAS",
            "nome": "PGDAS-D",
            "amostra_texto": "Documento de Arrecadação do Simples Nacional\nCNPJ: 12.345.678/0001-95",  # noqa: E501
            "campos": [
                {
                    "variavel": "MARCADOR",
                    "localizador": "Documento de Arrecadação do Simples Nacional",
                },
                {"variavel": "MARCADOR_2", "localizador": "PGDAS-D"},
                {"variavel": "CNPJ", "localizador": "CNPJ:"},
                {"variavel": "COMPETENCIA", "localizador": "Período de Apuração"},
                {"variavel": "VALOR_PRINCIPAL", "localizador": "Total", "ocorrencia": 2},
                {"variavel": "campo_livre", "localizador": "X", "custom": True},
                {"variavel": "ICMS", "localizador": "ICMS", "anulado": True},
            ],
        },
        {"sigla": "ICMS", "nome": "Guia ICMS", "campos": []},
        {"sigla": "EFD-ICMS-IPI", "nome": "EFD", "campos": []},
    ]
}


def export_file(tmp_path: Path) -> Path:
    path = tmp_path / "layouts.json"
    path.write_text(json.dumps(EXPORT), encoding="utf-8")
    return path


def test_import_creates_draft_layouts_with_the_legacy_fields(tmp_path: Path) -> None:
    office = make_office()
    call_command("import_closing_layouts", office=office.slug, file=str(export_file(tmp_path)))
    pgdas = ClosingLayout.objects.get(organization=office, code="pgdas")
    assert not pgdas.active
    assert pgdas.compare == ClosingLayout.Compare.FISCAL_GUIDE
    assert pgdas.guide_kind == FiscalGuide.Kind.DAS
    fields = {f.variable: f for f in pgdas.fields.all()}
    assert set(fields) == {"marker", "marker_2", "cnpj", "competence", "amount", "icms"}
    assert fields["amount"].occurrence == 2
    assert fields["icms"].nullified
    assert "Simples Nacional" in pgdas.sample_text
    efd = ClosingLayout.objects.get(organization=office, code="efd-icms-ipi")
    assert efd.compare == ClosingLayout.Compare.PAIRED
    assert efd.paired_layout == ClosingLayout.objects.get(organization=office, code="icms")
    assert efd.value_source == "icms"


def test_import_is_idempotent_and_never_touches_another_office(tmp_path: Path) -> None:
    office = make_office()
    other = make_office("untouched")
    path = export_file(tmp_path)
    call_command("import_closing_layouts", office=office.slug, file=str(path))
    ClosingLayout.objects.filter(organization=office, code="pgdas").update(active=True)
    call_command("import_closing_layouts", office=office.slug, file=str(path))
    assert ClosingLayout.objects.filter(organization=office).count() == 3
    assert not ClosingLayout.objects.get(organization=office, code="pgdas").active
    assert not ClosingLayout.objects.filter(organization=other).exists()


def test_import_dry_run_writes_nothing_and_bad_input_fails(tmp_path: Path) -> None:
    office = make_office()
    call_command(
        "import_closing_layouts", office=office.slug, file=str(export_file(tmp_path)), dry_run=True
    )
    assert not ClosingLayout.objects.filter(organization=office).exists()
    with pytest.raises(CommandError):
        call_command("import_closing_layouts", office="nao-existe", file=str(export_file(tmp_path)))
    broken = tmp_path / "x.json"
    broken.write_text("[]", encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("import_closing_layouts", office=office.slug, file=str(broken))


def test_reevaluate_command_closes_documents_that_waited_for_the_guide() -> None:
    office = make_office()
    owner = make_user(office, "owner@cmd.test")
    company = make_company(office)
    make_layout(
        office,
        activity_code="pgdas",
        compare=ClosingLayout.Compare.FISCAL_GUIDE,
        guide_kind=FiscalGuide.Kind.DAS,
    )
    activity = make_activity(office, company, code="pgdas", competence=date(2026, 8, 1))
    services.ingest_upload(organization=office, actor=owner, upload=txt_upload(das_text()))
    document = ClosingDocument.objects.get()
    assert document.conferences.get().outcome == ClosingConference.Outcome.WAITING
    make_guide(office, company)
    call_command("closing_reevaluate", office=office.slug)
    assert document.conferences.first().outcome == ClosingConference.Outcome.MATCHED  # type: ignore[union-attr]
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED
    call_command("closing_reevaluate", office=office.slug)
    assert document.conferences.count() == 2
