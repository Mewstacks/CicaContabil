from __future__ import annotations

from celery import shared_task


@shared_task(name="delivery.send")  # type: ignore[untyped-decorator]
def send_delivery_task(delivery_id: str) -> str:
    from apps.delivery.services import process_delivery

    return process_delivery(delivery_id)


@shared_task(name="delivery.dispatch_due")  # type: ignore[untyped-decorator]
def dispatch_due_task() -> int:
    from apps.delivery.services import dispatch_due

    return dispatch_due()
