"""Shared builders for the closing (fechamento por recibo) tests."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.closing.models import ClosingField, ClosingLayout
from apps.hub.models import (
    ActivityTemplate,
    ClientCompany,
    FiscalGuide,
    OperationalActivity,
    ProductModule,
)
from apps.organizations.models import Membership, Organization

CNPJ = "12.345.678/0001-95"
CNPJ_DIGITS = "12345678000195"
PASSWORD = "senha-longa-de-teste-2026"

DAS_TEXT = (
    "Documento de Arrecadação do Simples Nacional\n"
    "CNPJ: {cnpj}\n"
    "Período de Apuração: 08/2026\n"
    "Valor Total do Documento    {amount}\n"
)


def das_text(amount: str = "1.234,56", cnpj: str = CNPJ) -> str:
    return DAS_TEXT.format(amount=amount, cnpj=cnpj)


def txt_upload(text: str, name: str = "das.txt") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/plain")


def make_office(slug: str = "closing-office") -> Organization:
    office = Organization.objects.create(name=f"Office {slug}", slug=slug)
    ProductModule.objects.create(organization=office, code=ProductModule.Code.CLOSING, enabled=True)
    return office


def make_user(office: Organization, email: str, role: str = Membership.Role.OWNER) -> User:
    user = User.objects.create_user(email, PASSWORD)
    Membership.objects.create(organization=office, user=user, role=role)
    return user


def make_company(
    office: Organization, name: str = "Padaria Sol", cnpj: str = CNPJ
) -> ClientCompany:
    return ClientCompany.objects.create(
        organization=office, name=name, cnpj_masked=cnpj, dominio_code=cnpj[-7:-3] + cnpj[-2:]
    )


def make_layout(
    office: Organization,
    *,
    code: str = "das",
    label: str = "DAS",
    marker: str = "Documento de Arrecadação do Simples Nacional",
    active: bool = True,
    fields: dict[str, str] | None = None,
    **extra: Any,
) -> ClosingLayout:
    layout = ClosingLayout.objects.create(
        organization=office, code=code, label=label, active=active, **extra
    )
    wanted = {
        "marker": marker,
        "cnpj": "CNPJ:",
        "competence": "Período de Apuração",
        "amount": "Valor Total do Documento",
        **(fields or {}),
    }
    for position, (variable, anchor) in enumerate(wanted.items()):
        ClosingField.objects.create(
            organization=office, layout=layout, variable=variable, anchor=anchor, position=position
        )
    return layout


def make_activity(
    office: Organization,
    company: ClientCompany,
    *,
    code: str = "pgdas",
    competence: date = date(2026, 8, 1),
    requirement: str = ActivityTemplate.EvidenceRequirement.SOURCE_OR_HUMAN,
) -> OperationalActivity:
    return OperationalActivity.objects.create(
        organization=office,
        company=company,
        code=code,
        title="Transmitir PGDAS",
        area="fiscal",
        competence=competence,
        evidence_requirement=requirement,
    )


def make_guide(
    office: Organization,
    company: ClientCompany,
    *,
    cents: int = 123456,
    reference: str = "DAS-082026",
    competence: str = "08/2026",
    kind: str = FiscalGuide.Kind.DAS,
) -> FiscalGuide:
    return FiscalGuide.objects.create(
        organization=office,
        company=company,
        kind=kind,
        reference=reference,
        competence=competence,
        due_on=date(2026, 9, 20),
        amount_cents=cents,
        integra_service_key="pgdasd.das",
    )
