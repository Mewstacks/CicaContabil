"""Business days and legal deadlines from approved reference data only (D-277)."""

from __future__ import annotations

import calendar as month_calendar
from datetime import date, timedelta

from apps.fiscal_calendar.models import (
    BusinessCalendarYear,
    NonBusinessDay,
    ReferenceStatus,
    TaxDeadlineRule,
)


class CalendarIncomplete(Exception):
    """The year has no approved calendar, so a business day cannot be asserted."""


def add_months(value: date, months: int) -> date:
    """First day of the month ``months`` away from ``value``'s month."""

    index = value.year * 12 + value.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def day_in_month(month: date, day: int) -> date:
    """``day`` of ``month``, clamped to the month's last day (31 → 30/28)."""

    if not 1 <= day <= 31:
        raise ValueError(f"Dia fora do intervalo de 1 a 31: {day}")
    last = month_calendar.monthrange(month.year, month.month)[1]
    return date(month.year, month.month, min(day, last))


class BusinessCalendar:
    """Lazily loads approved non-business days per year; one instance per batch/request."""

    def __init__(self, scope: str = "BR") -> None:
        self.scope = scope
        self._years: dict[int, frozenset[date] | None] = {}

    def _holidays(self, year: int) -> frozenset[date]:
        if year not in self._years:
            calendar = BusinessCalendarYear.objects.filter(
                scope=self.scope, year=year, status=ReferenceStatus.APPROVED
            ).first()
            self._years[year] = (
                frozenset(
                    NonBusinessDay.objects.filter(calendar=calendar).values_list("day", flat=True)
                )
                if calendar
                else None
            )
        holidays = self._years[year]
        if holidays is None:
            raise CalendarIncomplete(year)
        return holidays

    def is_business_day(self, value: date) -> bool:
        return value.weekday() < 5 and value not in self._holidays(value.year)

    def shift(self, value: date, direction: str) -> date:
        if direction == TaxDeadlineRule.Shift.NONE:
            return value
        step = timedelta(days=-1 if direction == TaxDeadlineRule.Shift.PREVIOUS else 1)
        while not self.is_business_day(value):
            value += step
        return value

    def last_business_day(self, month: date) -> date:
        return self.shift(day_in_month(month, 31), TaxDeadlineRule.Shift.PREVIOUS)

    def subtract_business_days(self, value: date, count: int) -> date:
        remaining = count
        while remaining > 0:
            value -= timedelta(days=1)
            if self.is_business_day(value):
                remaining -= 1
        return value


def approved_rule(code: str, competence: date) -> TaxDeadlineRule | None:
    """The approved version that covers ``competence``; the newest wins on overlap."""

    if not code:
        return None
    month = competence.replace(day=1)
    return (
        TaxDeadlineRule.objects.filter(
            code=code, status=ReferenceStatus.APPROVED, valid_from__lte=month
        )
        .exclude(valid_until__lt=month)
        .order_by("-version")
        .first()
    )


def rule_due_date(rule: TaxDeadlineRule, competence: date, calendar: BusinessCalendar) -> date:
    """Legal deadline of ``competence`` under ``rule``; raises CalendarIncomplete."""

    month = add_months(competence.replace(day=1), rule.month_offset)
    if rule.anchor == TaxDeadlineRule.Anchor.LAST_BUSINESS_DAY:
        return calendar.last_business_day(month)
    if rule.anchor == TaxDeadlineRule.Anchor.LAST_DAY:
        due = day_in_month(month, 31)
    else:
        due = day_in_month(month, rule.day or 1)
    return calendar.shift(due, rule.non_business_shift)


def internal_before(legal: date, lead_days: int, calendar: BusinessCalendar) -> date:
    """``lead_days`` business days before ``legal``; weekdays only when a year is missing."""

    try:
        return calendar.subtract_business_days(legal, lead_days)
    except CalendarIncomplete:
        value, remaining = legal, lead_days
        while remaining > 0:
            value -= timedelta(days=1)
            if value.weekday() < 5:
                remaining -= 1
        return value
