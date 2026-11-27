from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def cents(value: object) -> str:
    """Centavos inteiros em reais, formato brasileiro (123456 -> 1.234,56)."""

    if not isinstance(value, int) or isinstance(value, bool):
        return "—"
    sign = "-" if value < 0 else ""
    reais, rest = divmod(abs(value), 100)
    return f"{sign}{reais:,}".replace(",", ".") + f",{rest:02d}"
