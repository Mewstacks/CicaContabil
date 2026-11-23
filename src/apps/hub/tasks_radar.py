"""Tarefa diária do radar Simples/MEI (E14): sem a flag ligada não faz nada."""

from __future__ import annotations

from celery import shared_task
from django.conf import settings

from apps.hub import simples_radar_alerts


@shared_task(name="hub.notify_simples_radar")  # type: ignore[untyped-decorator]
def notify_simples_radar_task() -> int:
    if not getattr(settings, "SIMPLES_RADAR_ENABLED", False):
        return 0
    return simples_radar_alerts.notify_simples_radar()
