"""Notes list of the NFS-e center: filters, counters and company groups computed in SQL.

The list used to build every row in Python, with a DISTINCT over the encrypted XML and
per-row accumulator queries; at 29k notes it took seconds. Now the page is one aggregate per
company (count, pending, service, net and retained amounts from ``NfseDocumentSide``) and
the rows of a company are read only when its group is opened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.db.models import (
    BooleanField,
    Case,
    Count,
    DecimalField,
    Exists,
    F,
    OuterRef,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Length, Replace

from apps.fiscal_calendar.services import add_months
from apps.hub.models import IntegrationArtifact, NfseDocument

CLOSED_SITUATIONS = ("cancelled", "substituted")
SITUATION_LABELS = {"active": "Ativa", "cancelled": "Cancelada", "substituted": "Substituída"}
STATUS_VALUES = ("all", "unclassified", "classified")
DIRECTION_VALUES = ("all", "provided", "taken", "unknown")
GROUP_PAGE_SIZE = 200
MONEY = DecimalField(max_digits=18, decimal_places=2)
ZERO = Decimal("0.00")


@dataclass
class NfseFilters:
    q: str = ""
    status: str = "all"
    direction: str = "all"
    period: str = "competence"
    competence: str = ""
    issued_from: date | None = None
    issued_to: date | None = None
    issued_from_text: str = ""
    issued_to_text: str = ""
    error: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return bool(
            self.q
            or self.competence
            or self.issued_from
            or self.issued_to
            or self.status != "all"
            or self.direction != "all"
        )

    def params(self, **overrides: str) -> dict[str, str]:
        values: dict[str, str] = {"status": self.status, "direction": self.direction}
        if self.q:
            values["q"] = self.q
        if self.period == "issued":
            values["period"] = "issued"
            if self.issued_from_text:
                values["issued_from"] = self.issued_from_text
            if self.issued_to_text:
                values["issued_to"] = self.issued_to_text
        else:
            values["competence"] = self.competence
        values.update(self.extra)
        values.update(overrides)
        return values

    def url(self, base: str, **overrides: str) -> str:
        return f"{base}?{urlencode(self.params(**overrides))}"


def _parse_day(value: str) -> date | None:
    value = value.strip()[:10]
    if not value:
        return None
    try:
        if "/" in value:
            return datetime.strptime(value, "%d/%m/%Y").date()
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(value) from exc


def parse_filters(params: Any, *, today: date) -> NfseFilters:
    """Read the GET filters, accepting the parameter names of the previous screens."""

    filters = NfseFilters(q=str(params.get("q", "")).strip()[:100])
    status = str(params.get("status", "all"))
    filters.status = (
        ("unclassified" if status in {"review", "received"} else status)
        if status in {*STATUS_VALUES, "review", "received"}
        else "all"
    )
    direction = str(params.get("direction", "all"))
    filters.direction = direction if direction in DIRECTION_VALUES else "all"
    period = str(params.get("period") or params.get("date_filter") or "competence")
    filters.period = "issued" if period == "issued" else "competence"

    competence = str(params.get("competence", "")).strip()[:7]
    if "competence_month" in params:
        month = str(params.get("competence_month", ""))
        year = str(params.get("competence_year", ""))
        competence = f"{year}-{month}" if month and year else ""
    if not any(
        key in params
        for key in (
            "competence",
            "competence_month",
            "q",
            "status",
            "direction",
            "period",
            "date_filter",
            "issued_from",
            "issued_to",
            "page",
        )
    ):
        # A bare visit opens the month the office is closing: the previous one.
        competence = add_months(today.replace(day=1), -1).strftime("%Y-%m")
    filters.competence = (
        competence if re.fullmatch(r"[12]\d{3}-(0[1-9]|1[0-2])", competence) else ""
    )

    if filters.period == "issued":
        filters.competence = ""
        raw_from = str(params.get("issued_from", ""))
        raw_to = str(params.get("issued_to", ""))
        try:
            filters.issued_from = _parse_day(raw_from)
            filters.issued_to = _parse_day(raw_to)
        except ValueError:
            filters.error = "Data inválida. Use DD/MM/AAAA."
        if filters.issued_from and filters.issued_to and filters.issued_from > filters.issued_to:
            filters.error = "A data final é anterior à inicial."
        filters.issued_from_text = (
            filters.issued_from.strftime("%d/%m/%Y") if filters.issued_from else raw_from[:10]
        )
        filters.issued_to_text = (
            filters.issued_to.strftime("%d/%m/%Y") if filters.issued_to else raw_to[:10]
        )
    return filters


def base_queryset(
    *, organization: Any, companies: QuerySet[Any], demo_classified_ids: set[Any] | None = None
) -> QuerySet[NfseDocument]:
    """Notes of the portfolio (events excluded) with their classification and situation."""

    classified: Any = Exists(IntegrationArtifact.objects.filter(document=OuterRef("pk")))
    if demo_classified_ids:
        classified = Q(classified) | Q(pk__in=demo_classified_ids)
    return (
        NfseDocument.objects.filter(organization=organization, company__in=companies)
        .exclude(side__kind="event")
        .annotate(
            is_classified=Case(
                When(classified, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            situation=Coalesce(F("side__situation"), Value("active")),
        )
    )


def _period_filter(query: QuerySet[NfseDocument], filters: NfseFilters) -> QuerySet[NfseDocument]:
    if filters.error:
        return query.none()
    if filters.period == "competence" and filters.competence:
        year, month = (int(part) for part in filters.competence.split("-"))
        start = date(year, month, 1)
        end = add_months(start, 1)
        # Notes whose facts were not read yet fall back to the emission month.
        return query.filter(
            Q(side__competence__gte=start, side__competence__lt=end)
            | Q(side__competence__isnull=True, issued_at__year=year, issued_at__month=month)
        )
    if filters.period == "issued":
        if filters.issued_from:
            query = query.filter(
                Q(side__issued_on__gte=filters.issued_from)
                | Q(side__issued_on__isnull=True, issued_at__date__gte=filters.issued_from)
            )
        if filters.issued_to:
            query = query.filter(
                Q(side__issued_on__lte=filters.issued_to)
                | Q(side__issued_on__isnull=True, issued_at__date__lte=filters.issued_to)
            )
    return query


def _digits_of(name: str) -> Replace:
    return Replace(Replace(Replace(F(name), Value(".")), Value("/")), Value("-"))


def _search_filter(query: QuerySet[NfseDocument], text: str) -> QuerySet[NfseDocument]:
    if not text:
        return query
    condition = (
        Q(company__name__icontains=text)
        | Q(company__dominio_code__iexact=text)
        | Q(side__number__icontains=text)
        | Q(normalized_data__number__icontains=text)
        | Q(side__counterparty_name__icontains=text)
    )
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 4 and len(digits) == len(re.sub(r"[\s./-]", "", text)):
        query = query.annotate(
            _counterparty_digits=_digits_of("side__counterparty_document"),
            _company_digits=_digits_of("company__cnpj_masked"),
        )
        condition |= Q(_counterparty_digits__contains=digits) | Q(
            _company_digits__startswith=digits
        )
    return query.filter(condition)


def _direction_filter(query: QuerySet[NfseDocument], direction: str) -> QuerySet[NfseDocument]:
    sides = ["provided", "taken"]
    if direction in sides:
        return query.filter(
            Q(side__direction=direction)
            | Q(side__isnull=True, normalized_data__direction=direction)
        )
    if direction == "unknown":
        return query.exclude(
            Q(side__direction__in=sides)
            | Q(side__isnull=True, normalized_data__direction__in=sides)
        )
    return query


def _status_filter(query: QuerySet[NfseDocument], status: str) -> QuerySet[NfseDocument]:
    if status == "classified":
        return query.filter(Q(is_classified=True))
    if status == "unclassified":
        return query.filter(Q(is_classified=False)).exclude(Q(situation__in=CLOSED_SITUATIONS))
    return query


def apply_filters(
    query: QuerySet[NfseDocument], filters: NfseFilters, *, skip: tuple[str, ...] = ()
) -> QuerySet[NfseDocument]:
    query = _search_filter(_period_filter(query, filters), filters.q)
    if "direction" not in skip:
        query = _direction_filter(query, filters.direction)
    if "status" not in skip:
        query = _status_filter(query, filters.status)
    return query


def tab_counts(
    query: QuerySet[NfseDocument], filters: NfseFilters
) -> tuple[dict[str, int], dict[str, int]]:
    """Each facet counts what selecting its tab would return (it ignores its own filter)."""

    pending = Q(is_classified=False) & ~Q(situation__in=CLOSED_SITUATIONS)
    status_scope = apply_filters(query, filters, skip=("status",)).aggregate(
        all=Count("pk"),
        unclassified=Count("pk", filter=pending),
        classified=Count("pk", filter=Q(is_classified=True)),
    )
    provided = Q(side__direction="provided") | Q(
        side__isnull=True, normalized_data__direction="provided"
    )
    taken = Q(side__direction="taken") | Q(side__isnull=True, normalized_data__direction="taken")
    direction_scope = apply_filters(query, filters, skip=("direction",)).aggregate(
        all=Count("pk"),
        provided=Count("pk", filter=provided),
        taken=Count("pk", filter=taken),
    )
    direction_scope["unknown"] = (
        direction_scope["all"] - direction_scope["provided"] - direction_scope["taken"]
    )
    return status_scope, direction_scope


def _open_sum(name: str) -> Coalesce:
    return Coalesce(
        Sum(name, filter=~Q(situation__in=CLOSED_SITUATIONS)), Value(ZERO), output_field=MONEY
    )


def company_groups(query: QuerySet[NfseDocument]) -> list[dict[str, Any]]:
    """One aggregate per company; cancelled and substituted notes stay out of the totals."""

    rows = (
        query.order_by()
        .values(
            "company_id",
            "company__name",
            "company__cnpj_masked",
            "company__dominio_code",
            "company__active",
        )
        .annotate(
            notes=Count("pk"),
            pending=Count(
                "pk", filter=Q(is_classified=False) & ~Q(situation__in=CLOSED_SITUATIONS)
            ),
            closed=Count("pk", filter=Q(situation__in=CLOSED_SITUATIONS)),
            service=_open_sum("side__service_amount"),
            net=_open_sum("side__net_amount"),
            iss=_open_sum("side__iss_retained"),
            crf=_open_sum("side__crf_retained"),
            irrf=_open_sum("side__irrf_retained"),
            inss=_open_sum("side__inss_retained"),
            retained=_open_sum("side__retained_total"),
        )
        .order_by("company__name", "company_id")
    )
    return [
        {
            "company_id": row["company_id"],
            "name": row["company__name"],
            "cnpj": row["company__cnpj_masked"],
            "dominio_code": row["company__dominio_code"],
            "active": row["company__active"],
            "notes": row["notes"],
            "pending": row["pending"],
            "closed": row["closed"],
            "service": row["service"],
            "net": row["net"],
            "iss": row["iss"],
            "crf": row["crf"],
            "irrf": row["irrf"],
            "inss": row["inss"],
            "retained": row["retained"],
        }
        for row in rows
    ]


TOTAL_KEYS = (
    "notes",
    "pending",
    "closed",
    "service",
    "net",
    "iss",
    "crf",
    "irrf",
    "inss",
    "retained",
)


def portfolio_totals(groups: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {key: 0 for key in TOTAL_KEYS[:3]}
    totals.update({key: ZERO for key in TOTAL_KEYS[3:]})
    for group in groups:
        for key in TOTAL_KEYS:
            totals[key] += group[key]
    return totals


def group_documents(query: QuerySet[NfseDocument], company_id: Any) -> QuerySet[NfseDocument]:
    """Rows of one company in book order: emission day, then note number."""

    return (
        query.filter(company_id=company_id)
        .select_related("side", "review_case")
        .defer("original_xml")
        .order_by(
            F("side__issued_on").asc(nulls_last=True),
            Length("side__number"),
            "side__number",
            "issued_at",
            "captured_at",
        )
    )


def brl(value: Decimal | None) -> str:
    if value is None:
        return ""
    formatted = f"{value.quantize(Decimal('0.01')):,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
