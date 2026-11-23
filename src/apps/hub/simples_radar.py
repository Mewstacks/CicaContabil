"""Radar Simples/MEI (E14, primeira fatia): receita de serviço por NFS-e contra o teto.

Só lê dado que o CICA já guarda (`NfseDocumentSide`, `PayrollPeriodSnapshot`): custo Serpro zero,
nenhuma chamada externa. O número é **receita de serviço por NFS-e**, nunca "RBT12": venda de
mercadoria e receita sem nota não estão aqui, e o resultado carrega essa ressalva
(`covers_only_nfse`). O RBT12 de verdade vem do PGDAS-D (E10) e entra depois.

Os limites ficam numa tabela com fonte e vigência (`LIMITS`), nunca como constante solta; os
valores ainda precisam de confirmação no Portal do Empreendedor (`confirmed=False`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import QuerySet, Sum

from apps.hub.models import ClientCompany, NfseDocumentSide, PayrollPeriodSnapshot
from apps.organizations.models import Organization

ZERO = Decimal("0.00")
ALERT_LEVELS = (100, 90, 80)
FATOR_R_THRESHOLD = Decimal("0.28")


@dataclass(frozen=True)
class Limit:
    regime: str
    annual_cents: int
    source: str
    effective_from: date
    confirmed: bool


LIMITS: dict[str, Limit] = {
    "mei": Limit(
        regime="mei",
        annual_cents=81_000_00,
        source="LC 123/2006 art. 18-A; conferir no Portal do Empreendedor (teto do MEI)",
        effective_from=date(2018, 1, 1),
        confirmed=False,
    ),
    "simples": Limit(
        regime="simples",
        annual_cents=4_800_000_00,
        source="LC 123/2006 art. 3º; Resolução CGSN 140/2018",
        effective_from=date(2018, 1, 1),
        confirmed=False,
    ),
}


@dataclass(frozen=True)
class RadarRow:
    company_id: str
    company_name: str
    regime: str
    year_revenue: Decimal
    trailing_12m: Decimal
    limit: Decimal
    percent: Decimal
    alert: int | None
    fator_r: Decimal | None
    annex: str
    limit_confirmed: bool
    covers_only_nfse: bool = True


def alert_level(percent: Decimal) -> int | None:
    for level in ALERT_LEVELS:
        if percent >= level:
            return level
    return None


def _months_back(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) - months
    return date(index // 12, index % 12 + 1, 1)


def _provided_total(company: ClientCompany, start: date, end_exclusive: date) -> Decimal:
    """Receita de serviço das notas ativas emitidas pela empresa no intervalo [start, end)."""

    total = NfseDocumentSide.objects.filter(
        document__company=company,
        direction="provided",
        kind="note",
        situation="active",
        issued_on__gte=start,
        issued_on__lt=end_exclusive,
    ).aggregate(total=Sum("service_amount"))["total"]
    return Decimal(total or ZERO)


def trailing_12_months(company: ClientCompany, today: date) -> Decimal:
    """Os 12 meses fechados antes do mês de `today` (como o RBT12 do Simples)."""

    month_start = date(today.year, today.month, 1)
    return _provided_total(company, _months_back(month_start, 12), month_start)


def year_to_date(company: ClientCompany, today: date) -> Decimal:
    return _provided_total(company, date(today.year, 1, 1), date(today.year + 1, 1, 1))


def fator_r(company: ClientCompany, today: date, revenue_12m: Decimal) -> Decimal | None:
    """Folha dos 12 meses ÷ receita dos 12 meses; só com os 12 meses de folha importados."""

    month_start = date(today.year, today.month, 1)
    start = _months_back(month_start, 12)
    snapshots = PayrollPeriodSnapshot.objects.filter(
        company=company, competence__gte=start, competence__lt=month_start
    )
    months = {item.competence.replace(day=1) for item in snapshots}
    if revenue_12m <= 0 or len(months) < 12:
        return None
    cents = sum(
        (item.gross_pay_cents or 0) + (item.employer_charges_cents or 0) for item in snapshots
    )
    return (Decimal(cents) / Decimal(100) / revenue_12m).quantize(Decimal("0.0001"))


def radar_row(
    company: ClientCompany, today: date, *, months_active: int | None = None
) -> RadarRow | None:
    """Uma linha do radar; `None` para quem não é MEI nem Simples.

    `months_active` aplica o teto proporcional do MEI no ano de abertura (R$ 6.750 por mês).
    """

    limit = LIMITS.get(company.tax_regime)
    if limit is None:
        return None
    ceiling = Decimal(limit.annual_cents) / Decimal(100)
    if company.tax_regime == "mei" and months_active is not None and 0 < months_active < 12:
        ceiling = (ceiling / Decimal(12) * Decimal(months_active)).quantize(Decimal("0.01"))
    year = year_to_date(company, today)
    # MEI e Simples medem o teto no ano-calendário; o Simples também olha os 12 meses.
    measured = (
        year if company.tax_regime == "mei" else max(year, trailing_12_months(company, today))
    )
    exact = measured / ceiling * 100 if ceiling else ZERO
    percent = exact.quantize(Decimal("0.01"))
    revenue_12m = trailing_12_months(company, today)
    factor = fator_r(company, today, revenue_12m) if company.tax_regime == "simples" else None
    annex = ""
    if factor is not None:
        annex = "III" if factor >= FATOR_R_THRESHOLD else "V"
    return RadarRow(
        company_id=str(company.pk),
        company_name=company.name,
        regime=company.tax_regime,
        year_revenue=year,
        trailing_12m=revenue_12m,
        limit=ceiling,
        percent=percent,
        alert=alert_level(exact),  # nível sobre o valor exato: 79,999% não vira 80%
        fator_r=factor,
        annex=annex,
        limit_confirmed=limit.confirmed,
    )


def portfolio(
    organization: Organization,
    today: date,
    companies: QuerySet[ClientCompany] | None = None,
) -> list[RadarRow]:
    """Carteira do escritório, da mais perto do teto para a mais longe.

    `companies` restringe ao escopo do colaborador; sem ele vale o escritório inteiro.
    """

    scope = companies if companies is not None else ClientCompany.objects.all()
    scope = scope.filter(organization=organization, active=True, tax_regime__in=list(LIMITS))
    rows = [row for company in scope if (row := radar_row(company, today)) is not None]
    return sorted(rows, key=lambda row: row.percent, reverse=True)
