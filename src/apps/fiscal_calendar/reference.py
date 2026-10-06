"""Reference drafts shipped with the code (D-277). They produce no date until approved.

Holidays follow the national financial calendar (ANBIMA) and Resolução CMN 4.880/2020, art. 6º:
saturdays, sundays, national holidays, Carnaval Monday/Tuesday and Corpus Christi are not
business days. Checked against ANBIMA 2026 on 06/10/2026 (13 dates).
"""

from __future__ import annotations

from datetime import date, timedelta

CALENDAR_LEGAL_BASIS = (
    "Lei 662/1949 (red. Lei 10.607/2002), Lei 6.802/1980, Lei 14.759/2023; "
    "Resolução CMN 4.880/2020, art. 6º (Carnaval e Corpus Christi)"
)
CALENDAR_SOURCE_URL = "https://www.anbima.com.br/feriados/feriados.asp"
CALENDAR_YEARS = (2025, 2026, 2027, 2028)


def easter_sunday(year: int) -> date:
    """Gregorian Easter (anonymous algorithm)."""

    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    weekday_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_offset) // 451
    month, day = divmod(h + weekday_offset - 7 * m + 114, 31)
    return date(year, month, day + 1)


def national_non_business_days(year: int) -> list[tuple[date, str]]:
    easter = easter_sunday(year)
    days = [
        (date(year, 1, 1), "Confraternização Universal"),
        (easter - timedelta(days=48), "Carnaval"),
        (easter - timedelta(days=47), "Carnaval"),
        (easter - timedelta(days=2), "Paixão de Cristo"),
        (date(year, 4, 21), "Tiradentes"),
        (date(year, 5, 1), "Dia do Trabalho"),
        (easter + timedelta(days=60), "Corpus Christi"),
        (date(year, 9, 7), "Independência do Brasil"),
        (date(year, 10, 12), "Nossa Senhora Aparecida"),
        (date(year, 11, 2), "Finados"),
        (date(year, 11, 15), "Proclamação da República"),
        (date(year, 12, 25), "Natal"),
    ]
    if year >= 2024:
        days.append((date(year, 11, 20), "Dia Nacional de Zumbi e da Consciência Negra"))
    return sorted(days)


RULE_DRAFTS: tuple[dict[str, object], ...] = (
    {
        "code": "dctfweb",
        "version": 1,
        "title": "DCTFWeb — transmissão",
        "month_offset": 1,
        "anchor": "last_business_day",
        "day": None,
        "non_business_shift": "none",
        "valid_from": date(2025, 2, 1),
        "legal_basis": (
            "IN RFB 2.237/2024, alterada pela IN RFB 2.248/2025: último dia útil do mês "
            "seguinte ao dos fatos geradores (competência 01/2025 teve prazo especial em 03/2025)"
        ),
        "source_url": (
            "https://www.normaslegais.com.br/legislacao/instrucao-normativa-rfb-2248-2025.htm"
        ),
        "source_checked_on": date(2026, 10, 6),
    },
    {
        "code": "contribuicao-previdenciaria",
        "version": 1,
        "title": "Contribuições previdenciárias — pagamento",
        "month_offset": 1,
        "anchor": "day_of_month",
        "day": 20,
        "non_business_shift": "previous",
        "valid_from": date(2025, 1, 1),
        "legal_basis": (
            "Lei 8.212/1991, art. 30, I, b, e §2º (red. Lei 11.933/2009): dia 20 do mês "
            "seguinte, antecipado quando não houver expediente bancário"
        ),
        "source_url": "https://www.planalto.gov.br/ccivil_03/leis/l8212cons.htm",
        "source_checked_on": date(2026, 10, 6),
    },
    {
        "code": "das-simples-nacional",
        "version": 1,
        "title": "DAS — Simples Nacional",
        "month_offset": 1,
        "anchor": "day_of_month",
        "day": 20,
        "non_business_shift": "next",
        "valid_from": date(2025, 1, 1),
        "legal_basis": (
            "LC 123/2006, art. 21, III: dia 20 do mês seguinte; prorrogação ao dia útil "
            "seguinte sem expediente bancário — confirmar no texto vigente da Resolução "
            "CGSN 140/2018 antes de aprovar"
        ),
        "source_url": "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm",
        "source_checked_on": date(2026, 10, 6),
    },
)


def load_reference_drafts(calendar_year_model, day_model, rule_model) -> None:  # type: ignore[no-untyped-def]
    """Idempotent: creates missing drafts, never touches approved or retired rows."""

    for year in CALENDAR_YEARS:
        calendar, _created = calendar_year_model.objects.get_or_create(
            scope="BR",
            year=year,
            defaults={
                "legal_basis": CALENDAR_LEGAL_BASIS,
                "source_url": CALENDAR_SOURCE_URL,
                "status": "draft",
            },
        )
        if calendar.status != "draft":
            continue
        for day, name in national_non_business_days(year):
            day_model.objects.get_or_create(calendar=calendar, day=day, defaults={"name": name})
    for draft in RULE_DRAFTS:
        rule_model.objects.get_or_create(
            code=draft["code"],
            version=draft["version"],
            defaults={key: value for key, value in draft.items() if key not in {"code", "version"}},
        )
