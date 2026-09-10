from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.intelligence.models import AssistantSettings, Conversation
from apps.organizations.models import Organization


@dataclass(frozen=True)
class RetentionResult:
    eligible: int
    deleted: int


def purge_expired_conversations(*, organization: Organization, apply: bool) -> RetentionResult:
    settings = AssistantSettings.objects.filter(organization=organization).first()
    days = settings.retention_days if settings else 90
    cutoff = timezone.now() - timedelta(days=days)
    expired = (
        Conversation.objects.filter(organization=organization, created_at__lt=cutoff)
        .filter(drafts__isnull=True)
        .exclude(messages__feedbacks__candidate__isnull=False)
        .distinct()
    )
    eligible = expired.count()
    deleted = 0
    if apply and eligible:
        deleted, _ = expired.delete()
    return RetentionResult(eligible, deleted)
