from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("platform", "0012_platformconfiguration")]
    operations = [
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_cnpj",
            field=models.CharField(default="68340160000113", max_length=14),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_legal_name",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_trade_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_registration_status",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_opened_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_primary_activity",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_registry_source",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="platformconfiguration",
            name="provider_registry_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
