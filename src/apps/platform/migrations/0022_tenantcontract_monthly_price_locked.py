from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("platform", "0021_platformconfiguration_local_multimodal_endpoint")]

    operations = [
        migrations.AddField(
            model_name="tenantcontract",
            name="monthly_price_locked",
            field=models.BooleanField(default=False),
        )
    ]
