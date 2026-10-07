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
