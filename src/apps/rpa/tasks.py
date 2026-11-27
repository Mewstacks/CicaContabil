"""Tarefas periódicas da fila RPA: devolver reservas vencidas (ou marcar incerto)."""

from __future__ import annotations

from celery import shared_task

from . import services


@shared_task(name="rpa.release_expired")  # type: ignore[untyped-decorator]
def release_expired() -> int:
    """Reserva sem sinal do agente volta à fila; a que já passou do ponto sem volta vira incerta."""

    if not services.agent_enabled():
        return 0
    return services.release_expired()
