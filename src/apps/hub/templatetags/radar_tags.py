"""Tag da aba do radar Simples/MEI (E14): a aba só existe com a flag ligada."""

from __future__ import annotations

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def radar_enabled() -> bool:
    return bool(getattr(settings, "SIMPLES_RADAR_ENABLED", False))
