from django.db import migrations


def replace_module_list(value):
    if not isinstance(value, list) or "journey" not in value:
        return value
    return list(dict.fromkeys("triage" if code == "journey" else code for code in value))


def replace_journey_offer(apps, schema_editor):
    ProductModule = apps.get_model("hub", "ProductModule")
    for old in ProductModule.objects.filter(code="journey").iterator():
        if old.enabled:
            triage, _ = ProductModule.objects.get_or_create(
                organization_id=old.organization_id,
                code="triage",
                defaults={"enabled": True, "enabled_at": old.enabled_at},
            )
            if not triage.enabled:
                triage.enabled = True
                triage.enabled_at = old.enabled_at
                triage.save(update_fields=["enabled", "enabled_at", "updated_at"])
            old.enabled = False
            old.enabled_at = None
            old.save(update_fields=["enabled", "enabled_at", "updated_at"])

    for app_label, model_name, fields in (
        ("platform", "Plan", ("modules",)),
        ("platform", "TenantContract", ("selected_modules", "pending_modules")),
        ("platform", "SignupIntent", ("selected_modules",)),
        ("platform", "Invitation", ("modules",)),
        ("hub", "CompanyAccessGrant", ("modules",)),
    ):
        Model = apps.get_model(app_label, model_name)
        for row in Model.objects.all().iterator():
            changed = []
            for field in fields:
                old = getattr(row, field)
                new = replace_module_list(old)
                if new != old:
                    setattr(row, field, new)
                    changed.append(field)
            if changed:
                row.save(update_fields=[*changed, "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0026_payment_webhook_processing_and_external_id_unique"),
        ("hub", "0026_dtemessageobservation_dtemessagestate_and_more"),
    ]

    operations = [migrations.RunPython(replace_journey_offer, migrations.RunPython.noop)]
