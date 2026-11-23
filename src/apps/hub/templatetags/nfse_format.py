from __future__ import annotations

from decimal import Decimal

from django import template

from apps.hub.nfse_list import brl as format_brl

register = template.Library()


@register.filter
def brl(value: Decimal | int | None) -> str:
    """Brazilian money without the currency sign: 1.234,56."""

    if value is None:
        return ""
    return format_brl(Decimal(value))


@register.filter
def source_date(value: object) -> str:
    """A source date as dd/mm/aaaa when it is ISO (AAAA-MM-DD); anything else stays verbatim."""

    import re

    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    return f"{match[3]}/{match[2]}/{match[1]}" if match else text


@register.filter
def source_brl(value: object) -> str:
    """A plain numeric source amount as R$ 1.234,56; anything else stays verbatim."""

    from decimal import InvalidOperation

    text = str(value or "").strip()
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return text
    if not amount.is_finite():
        return text
    return ("-" if amount < 0 else "") + "R$ " + format_brl(abs(amount))
