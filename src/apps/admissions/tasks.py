"""Retenção das Admissões: dados pessoais apagados em 90 dias."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="admissions.expire")  # type: ignore[untyped-decorator]
def expire() -> int:
    from .services import expire as run

    return run()
