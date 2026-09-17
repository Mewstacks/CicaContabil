"""Session-local progress for the one synthetic demonstration office.

The cookie is browser-session scoped; Django stores the small JSON scenario in
its session backend. Seeded office records remain immutable reference data.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.db.models import Exists, OuterRef
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization

DEMO_VISITOR_MAX_AGE = timedelta(hours=24)
DEMO_VISITOR_CLEANUP_BATCH = 100


def cleanup_stale_demo_visitors(office: Organization) -> int:
    """Remove only expired, passwordless guests belonging solely to this demo office."""

    other_membership = Membership.objects.filter(user_id=OuterRef("pk")).exclude(
        organization=office
    )
    candidate_ids = list(
        User.objects.filter(
            date_joined__lt=timezone.now() - DEMO_VISITOR_MAX_AGE,
            email__startswith="demo-",
            email__endswith="@example.test",
            password__startswith=UNUSABLE_PASSWORD_PREFIX,
            is_staff=False,
            is_superuser=False,
            organization_memberships__organization=office,
        )
        .annotate(has_other_membership=Exists(other_membership))
        .filter(has_other_membership=False)
        .values_list("id", flat=True)[:DEMO_VISITOR_CLEANUP_BATCH]
    )
    if not candidate_ids:
        return 0
    User.objects.filter(id__in=candidate_ids).delete()
    return len(candidate_ids)


def is_demo_visitor(request: HttpRequest, office: Organization) -> bool:
    return office.is_demo and bool(request.session.get("demo_visit_id"))


def get_progress(request: HttpRequest, section: str, item_id: object) -> dict[str, Any]:
    data = request.session.get("demo_progress", {})
    if not isinstance(data, dict):
        return {}
    entries = data.get(section, {})
    if not isinstance(entries, dict):
        return {}
    entry = entries.get(str(item_id), {})
    return entry if isinstance(entry, dict) else {}


def get_section(request: HttpRequest, section: str) -> dict[str, dict[str, Any]]:
    data = request.session.get("demo_progress", {})
    entries = data.get(section, {}) if isinstance(data, dict) else {}
    if not isinstance(entries, dict):
        return {}
    return {
        str(key): value
        for key, value in entries.items()
        if isinstance(value, dict)
    }


def put_progress(
    request: HttpRequest, section: str, item_id: object, entry: dict[str, Any]
) -> None:
    data = request.session.get("demo_progress", {})
    if not isinstance(data, dict):
        data = {}
    data = dict(data)
    entries = data.get(section, {})
    entries = dict(entries) if isinstance(entries, dict) else {}
    entries[str(item_id)] = entry
    data[section] = entries
    request.session["demo_progress"] = data
