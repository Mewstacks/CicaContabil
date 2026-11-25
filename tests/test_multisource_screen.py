"""Tela “Fechamento do mês (simulação)” (D-413). Dados sintéticos; nada pode ser gravado."""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from openpyxl import Workbook

from apps.hub.models import (
    ClientCompany,
    NormalizedMovement,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract
from test_multisource_matching import _statement_pdf

pytestmark = pytest.mark.django_db


@pytest.fixture
def screen(organization, user, membership):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(organization=organization, name="Empresa fictícia")
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return {"client": client, "company": company, "membership": membership}


def cashbook() -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "SICREDI"
    sheet.append(["DATA", "HISTÓRICO", "ENTRADA", "SAÍDA", "SALDO"])
    sheet.append([date(2026, 10, 1), "SALARIO PESSOA A", None, 100])
    sheet.append([date(2026, 10, 1), "SALARIO PESSOA B", None, 200])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def payload(company, **extra):
    data = {
        "company": str(company.pk),
        "statement": SimpleUploadedFile("extrato.pdf", _statement_pdf(), "application/pdf"),
        "cashbook": SimpleUploadedFile("caixa.xlsx", cashbook()),
        "cashbook_sheet": "SICREDI",
        "action": "simulate",
    }
    data.update(extra)
    return data


URL = "hub:reconciliation-multisource"


def test_page_opens_from_reconciliation_and_shows_the_form(screen):
    client = screen["client"]
    assert reverse(URL) in client.get(reverse("hub:reconciliation")).content.decode()
    response = client.get(reverse(URL))
    page = response.content.decode()
    assert response.status_code == 200
    assert "Fechamento do mês (simulação)" in page and 'enctype="multipart/form-data"' in page
    assert "Extrato bancário Sicredi (PDF)" in page and "Nada é lançado nem guardado" in page


def test_simulation_shows_result_and_writes_nothing(screen):
    files_before = ReconciliationSourceFile.objects.count()
    movements_before = NormalizedMovement.objects.count()
    response = screen["client"].post(reverse(URL), payload(screen["company"]))
    page = response.content.decode()
    assert response.status_code == 200
    assert "Resultado de 10/2026" in page and "Empresa fictícia · 1 movimentos" in page
    assert "Identificado pelo caixa (sem baixa de título)" in page
    assert "Automático (títulos, aplicação ou transferência)" in page  # D-415
    assert "Transferências entre contas" in page
    assert "Nenhuma sinalização" in page
    assert response["Cache-Control"] == "no-store, private"
    assert ReconciliationSourceFile.objects.count() == files_before
    assert NormalizedMovement.objects.count() == movements_before


def test_zip_action_returns_the_reports(screen):
    response = screen["client"].post(reverse(URL), payload(screen["company"], action="zip"))
    assert response.status_code == 200 and response["Content-Type"] == "application/zip"
    assert "simulacao-multifontes-2026-10.zip" in response["Content-Disposition"]
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert {"resumo.md", "movimentos.csv", "posicao.csv"} <= set(names)


def test_wrong_format_and_layout_errors_are_shown(screen):
    bad_format = payload(screen["company"], statement=SimpleUploadedFile("extrato.txt", b"x"))
    response = screen["client"].post(reverse(URL), bad_format)
    assert response.status_code == 400 and "no formato .pdf" in response.content.decode()
    not_sicredi = payload(
        screen["company"], statement=SimpleUploadedFile("extrato.pdf", _plain_pdf())
    )
    response = screen["client"].post(reverse(URL), not_sicredi)
    assert response.status_code == 400 and "fora do leiaute Sicredi" in response.content.decode()
    sheets_without_cashbook = payload(screen["company"], cash_sheets="CAIXA")
    sheets_without_cashbook.pop("cashbook")
    response = screen["client"].post(reverse(URL), sheets_without_cashbook)
    assert response.status_code == 400


def test_company_from_another_office_is_rejected(screen):
    other = Organization.objects.create(name="Outro", slug="outro")
    foreign = ClientCompany.objects.create(organization=other, name="De outro escritório")
    response = screen["client"].post(reverse(URL), payload(foreign))
    assert response.status_code == 400 and "Resultado de" not in response.content.decode()


def test_read_only_profile_cannot_send_files(screen):
    membership = screen["membership"]
    membership.role = Membership.Role.AUDITOR
    membership.save(update_fields=["role"])
    page = screen["client"].get(reverse(URL)).content.decode()
    assert "Acesso de consulta" in page and '<form method="post"' not in page
    response = screen["client"].post(reverse(URL), payload(screen["company"]))
    assert response.status_code == 403


def _plain_pdf() -> bytes:
    from reportlab.pdfgen.canvas import Canvas

    stream = io.BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(40, 700, "Documento qualquer")
    canvas.showPage()
    canvas.save()
    return stream.getvalue()
