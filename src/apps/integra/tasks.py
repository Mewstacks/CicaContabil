"""Celery task of the fiscal radar (T10.5). Does nothing unless `INTEGRA_RADAR_ENABLED` is on.

Not scheduled: the beat entry belongs to the deploy that turns the flag on. The task only
looks at offices that chose an identity mode (a row of `OfficeSerproIdentity`), so an office that
never touched the Serpro settings is never called.
"""

from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.integra.errors import IntegraError
from apps.integra.identity import office_access
from apps.integra.models import OfficeSerproIdentity
from apps.integra.radar import collect_events, radar_enabled, request_events


@shared_task(name="integra.radar_tick")  # type: ignore[untyped-decorator]
def radar_tick() -> dict[str, int]:
    """Collect what is ready and ask for what is missing, one office at a time."""

    if not radar_enabled():
        return {"offices": 0, "requested": 0, "collected": 0}
    totals = {"offices": 0, "requested": 0, "collected": 0}
    identities = OfficeSerproIdentity.objects.select_related("organization")
    for identity in identities:
        organization = identity.organization
        now = timezone.now()
        try:
            access = office_access(organization)
            totals["collected"] += collect_events(access, organization, now=now)
            totals["requested"] += len(request_events(access, organization, now=now))
        except IntegraError:
            continue
        totals["offices"] += 1
    return totals
