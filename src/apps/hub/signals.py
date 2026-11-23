"""D-397 item 6: a bank account created by any path triggers the automatic title reading (D-394)."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.hub.models import FinancialAccount


@receiver(post_save, sender=FinancialAccount, dispatch_uid="hub-d397-title-reading")
def interpret_titles_for_new_account(
    sender: type[FinancialAccount], instance: FinancialAccount, created: bool, **kwargs: Any
) -> None:
    if not created or kwargs.get("raw") or not instance.active:
        return
    from apps.hub.direct_use import direct_use_enabled
    from apps.hub.title_auto import schedule_company

    if direct_use_enabled(instance.organization):
        schedule_company(instance.company_id)  # after commit, in the worker; idempotent
