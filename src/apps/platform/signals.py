"""Keep commercial contract snapshots independent from mutable plan catalogue rows."""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.platform.models import TenantContract


@receiver(post_save, sender=TenantContract)
def snapshot_new_contract_pricing(
    sender: type[TenantContract], instance: TenantContract, created: bool, **kwargs: object
) -> None:
    if created and instance.plan_id:
        from apps.platform.billing import snapshot_contract_pricing

        # A contract is an agreement, not a live view of the catalogue.  Freeze
        # the enabled modules before any later plan edit can alter an office's
        # authorization boundary.
        if not instance.selected_modules:
            instance.selected_modules = list(instance.plan.modules)
            instance.save(update_fields=["selected_modules", "updated_at"])
        snapshot_contract_pricing(instance, initialize_price=True)
