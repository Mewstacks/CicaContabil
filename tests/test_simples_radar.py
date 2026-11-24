"""Radar Simples/MEI (E14): receita de serviço por NFS-e contra o teto, só com dado já coletado."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from apps.hub import simples_radar
from apps.hub.models import (
    ClientCompany,
    NfseDocument,
    NfseDocumentSide,
    PayrollPeriodSnapshot,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db
TODAY = date(2026, 11, 23)


def company(office: Organization, name: str, regime: str) -> ClientCompany:
    return ClientCompany.objects.create(
        organization=office, name=name, cnpj_masked="11.222.333/0001-81", tax_regime=regime
    )


def note(
    comp: ClientCompany,
    amount: str,
    issued_on: date,
    *,
    direction: str = "provided",
    situation: str = "active",
    kind: str = "note",
) -> None:
    digest = hashlib.sha256(
        f"{comp.pk}{amount}{issued_on}{direction}{situation}".encode()
    ).hexdigest()
    document = NfseDocument.objects.create(
        organization=comp.organization,
        company=comp,
        document_hash=digest,
        original_xml="<x/>",
        source_nsu=digest[:20],
    )
    NfseDocumentSide.objects.create(
        organization=comp.organization,
        document=document,
        direction=direction,
        kind=kind,
        situation=situation,
        issued_on=issued_on,
        service_amount=Decimal(amount),
    )


def test_only_active_provided_notes_count_and_the_row_says_it_is_only_nfse() -> None:
    office = Organization.objects.create(name="Esc", slug="radar")
    mei = company(office, "Padaria MEI", "mei")
    note(mei, "40500.00", date(2026, 3, 10))
    note(mei, "9999.00", date(2026, 4, 10), situation="canceled")
    note(mei, "5000.00", date(2026, 4, 11), direction="taken")
    note(mei, "700.00", date(2026, 5, 2), kind="event")
    note(mei, "8000.00", date(2025, 12, 31))  # ano anterior: fora do teto do MEI

    row = simples_radar.radar_row(mei, TODAY)

    assert row is not None
    assert row.year_revenue == Decimal("40500.00")
    assert row.percent == Decimal("50.00") and row.alert is None
    assert row.covers_only_nfse is True and row.limit_confirmed is False


@pytest.mark.parametrize(
    ("amount", "level"),
    [("64800.00", 80), ("72900.00", 90), ("81000.00", 100), ("90000.00", 100), ("64799.99", None)],
)
def test_alert_levels_are_80_90_and_100_percent_of_the_mei_ceiling(
    amount: str, level: int | None
) -> None:
    office = Organization.objects.create(name="Esc", slug=f"nivel-{amount}")
    mei = company(office, "MEI", "mei")
    note(mei, amount, date(2026, 6, 1))

    row = simples_radar.radar_row(mei, TODAY)

    assert row is not None and row.alert == level


def test_the_mei_ceiling_is_proportional_in_the_opening_year() -> None:
    office = Organization.objects.create(name="Esc", slug="abertura")
    mei = company(office, "MEI novo", "mei")
    note(mei, "27000.00", date(2026, 9, 1))

    row = simples_radar.radar_row(mei, TODAY, months_active=5)

    assert row is not None and row.limit == Decimal("33750.00")
    assert row.percent == Decimal("80.00") and row.alert == 80


def test_the_simples_looks_at_the_larger_of_the_year_and_the_twelve_closed_months() -> None:
    office = Organization.objects.create(name="Esc", slug="simples")
    simples = company(office, "Serviços Ltda", "simples")
    note(simples, "3900000.00", date(2025, 12, 15))  # entra no RBT12 (12 meses fechados)
    note(simples, "100000.00", date(2026, 2, 1))

    row = simples_radar.radar_row(simples, TODAY)

    assert row is not None
    assert row.trailing_12m == Decimal("4000000.00")
    assert row.percent == Decimal("83.33") and row.alert == 80


def test_fator_r_needs_twelve_months_of_payroll_and_picks_the_annex() -> None:
    office = Organization.objects.create(name="Esc", slug="fatorr")
    simples = company(office, "Consultoria", "simples")
    window = [date(2025, 11 + i, 1) if i < 2 else date(2026, i - 1, 1) for i in range(12)]
    assert window[0] == date(2025, 11, 1) and window[-1] == date(2026, 10, 1)
    for month in window:
        note(simples, "10000.00", month.replace(day=5))
    row = simples_radar.radar_row(simples, TODAY)
    assert row is not None and row.trailing_12m == Decimal("120000.00") and row.fator_r is None

    for month in window[:11]:
        PayrollPeriodSnapshot.objects.create(
            organization=office,
            company=simples,
            competence=month,
            source_kind=PayrollPeriodSnapshot.SourceKind.MANUAL,
            source_reference="teste",
            gross_pay_cents=300_000,
        )
    row = simples_radar.radar_row(simples, TODAY)
    assert row is not None and row.fator_r is None  # 11 meses de folha não bastam

    PayrollPeriodSnapshot.objects.create(
        organization=office,
        company=simples,
        competence=window[11],
        source_kind=PayrollPeriodSnapshot.SourceKind.MANUAL,
        source_reference="teste",
        gross_pay_cents=300_000,
        employer_charges_cents=60_000,
    )
    row = simples_radar.radar_row(simples, TODAY)

    # (12 x 3.000 + 600) / 120.000 = 0,3050
    assert row is not None and row.fator_r == Decimal("0.3050") and row.annex == "III"


def test_other_regimes_are_ignored_and_the_portfolio_is_sorted_by_percentage() -> None:
    office = Organization.objects.create(name="Esc", slug="carteira")
    low = company(office, "Baixo", "mei")
    high = company(office, "Alto", "mei")
    company(office, "Presumido", "presumido")
    note(low, "8100.00", date(2026, 2, 1))
    note(high, "70000.00", date(2026, 2, 1))

    rows = simples_radar.portfolio(office, TODAY)

    assert [row.company_name for row in rows] == ["Alto", "Baixo"]
    assert simples_radar.radar_row(ClientCompany(tax_regime="presumido"), TODAY) is None
