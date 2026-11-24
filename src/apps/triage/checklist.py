"""The delivery checklist: company x document type x period, with due date and completeness.

What a company is expected to deliver comes from the type (everyone, or some tax regimes)
and from the company's own exception (``ChecklistExpectation`` wins). A cell is *delivered*
when an archived document filled the ``ChecklistEntry`` of that period. The draft of a
request to the client is only text: a person reads it and sends it.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.db.models import QuerySet

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import ChecklistEntry, ChecklistExpectation, DocumentType

DEFAULT_DUE_DAY = 10
_PERIOD = re.compile(r"20\d{2}-(0[1-9]|1[0-2])")
_NOT_EXPECTED = {
    ChecklistExpectation.Requirement.OPTIONAL,
    ChecklistExpectation.Requirement.WAIVED,
    ChecklistExpectation.Requirement.NOT_APPLICABLE,
}


def parse_period(value: str | None) -> str | None:
    value = (value or "").strip()
    return value if _PERIOD.fullmatch(value) else None


def period_label(period: str) -> str:
    return f"{period[5:7]}/{period[:4]}"


def shift_period(period: str, months: int) -> str:
    index = int(period[:4]) * 12 + int(period[5:7]) - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def due_date(document_type: DocumentType, period: str) -> date:
    """The day of the month after ``period`` by which the document should have arrived."""

    year, month = int(period[:4]), int(period[5:7])
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    day = min(document_type.due_day or DEFAULT_DUE_DAY, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass
class Cell:
    document_type: DocumentType
    status: str  # delivered | late | pending
    days_late: int = 0
    due: date | None = None
    received_at: Any = None


@dataclass
class Row:
    company: ClientCompany
    cells: list[Cell] = field(default_factory=list)

    @property
    def expected(self) -> int:
        return len(self.cells)

    @property
    def delivered(self) -> int:
        return sum(cell.status == "delivered" for cell in self.cells)

    @property
    def percent(self) -> int:
        return round(100 * self.delivered / self.expected) if self.expected else 100

    @property
    def missing(self) -> list[Cell]:
        return [cell for cell in self.cells if cell.status != "delivered"]


@dataclass
class Checklist:
    period: str
    rows: list[Row] = field(default_factory=list)

    @property
    def expected(self) -> int:
        return sum(row.expected for row in self.rows)

    @property
    def delivered(self) -> int:
        return sum(row.delivered for row in self.rows)

    @property
    def percent(self) -> int:
        return round(100 * self.delivered / self.expected) if self.expected else 100


def _is_expected(
    company: ClientCompany, document_type: DocumentType, requirement: str | None
) -> bool:
    if requirement is not None:
        return requirement not in _NOT_EXPECTED
    return bool(
        document_type.expected_default
        or (company.tax_regime and company.tax_regime in (document_type.expected_regimes or []))
    )


def build_checklist(
    office: Organization, companies: QuerySet[ClientCompany], period: str, today: date
) -> Checklist:
    """The checklist of ``period`` for ``companies`` (scoped by the caller) of ``office``."""

    scoped = list(companies.filter(organization=office, active=True).order_by("name"))
    types = list(DocumentType.objects.filter(organization=office, active=True).order_by("label"))
    ids = [company.pk for company in scoped]
    exceptions = {
        (row.company_id, row.document_type_id): row.requirement
        for row in ChecklistExpectation.objects.filter(organization=office, company_id__in=ids)
    }
    delivered = {
        (row.company_id, row.document_type_id): row
        for row in ChecklistEntry.objects.filter(
            organization=office,
            company_id__in=ids,
            period_label=period,
            triage_item__isnull=False,
        )
    }
    result = Checklist(period=period)
    for company in scoped:
        row = Row(company=company)
        for document_type in types:
            key = (company.pk, document_type.pk)
            if not _is_expected(company, document_type, exceptions.get(key)):
                continue
            due = due_date(document_type, period)
            entry = delivered.get(key)
            if entry is not None:
                cell = Cell(document_type, "delivered", due=due, received_at=entry.received_at)
            elif today > due:
                cell = Cell(document_type, "late", (today - due).days, due)
            else:
                cell = Cell(document_type, "pending", 0, due)
            row.cells.append(cell)
        result.rows.append(row)
    return result


@dataclass(frozen=True)
class Draft:
    subject: str
    body: str
    to: str


def request_draft(row: Row, period: str) -> Draft:
    """Text asking the client for what is still missing; nothing here sends anything."""

    label = period_label(period)
    company = row.company
    greeting = f"Olá, {company.contact_name}," if company.contact_name else "Olá,"
    lines = []
    for cell in row.missing:
        suffix = f" (há {cell.days_late} dias)" if cell.days_late else ""
        lines.append(f"- {cell.document_type.label}{suffix}")
    body = (
        f"{greeting}\n\nPara fechar {label} de {company.name} ainda precisamos de:\n"
        + "\n".join(lines)
        + "\n\nPode nos enviar por e-mail? Obrigado."
        if lines
        else ""
    )
    return Draft(
        subject=f"Documentos de {label} - {company.name}", body=body, to=company.contact_email
    )
