from datetime import date

from django.db import migrations, models


def populate_mewstack(apps, schema_editor):
    configuration = apps.get_model("platform", "PlatformConfiguration")
    item, _ = configuration.objects.get_or_create(key="default")
    defaults = {
        "provider_cnpj": "68340160000113",
        "provider_legal_name": "MEWSTACK DESENVOLVIMENTO DE SISTEMAS LTDA",
        "provider_trade_name": "MEWSTACK",
        "provider_registration_status": "ATIVA",
        "provider_opened_on": date(2026, 8, 3),
        "provider_primary_activity": "Desenvolvimento de programas de computador sob encomenda",
        "provider_registry_source": "BrasilAPI",
        "legal_address": (
            "RUA PRIMITIVA ZATTI, 297, FUNDOS, SAO CIRO · CAXIAS DO SUL / RS · CEP 95057-560"
        ),
        "support_phone": "(54) 99657-3455",
        "support_hours": (
            "Segunda a sexta, das 09:00 às 19:00; sábado, das 09:00 às 14:00; domingo, fechado."
        ),
    }
    changed = []
    for field, value in defaults.items():
        if not getattr(item, field):
            setattr(item, field, value)
            changed.append(field)
    if changed:
        item.save(update_fields=[*changed, "updated_at"])


class Migration(migrations.Migration):
    dependencies = [("platform", "0013_provider_registry_fields")]
    operations = [
        migrations.AddField(
            model_name="platformconfiguration",
            name="support_phone",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.RunPython(populate_mewstack, migrations.RunPython.noop),
    ]
