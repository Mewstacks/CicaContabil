# Generated manually from the payment webhook domain change.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0025_platform_cloud_fallback"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="paymentattempt",
            constraint=models.UniqueConstraint(
                condition=~models.Q(("external_id", "")),
                fields=("provider", "external_id"),
                name="platform_unique_provider_payment_external_id",
            ),
        ),
        migrations.AddField(
            model_name="paymentwebhookdelivery",
            name="error_code",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="paymentwebhookdelivery",
            name="payment_attempt",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="webhook_deliveries",
                to="platform.paymentattempt",
            ),
        ),
        migrations.AddField(
            model_name="paymentwebhookdelivery",
            name="processing_status",
            field=models.CharField(
                choices=[
                    ("processed", "Processado"),
                    ("ignored", "Ignorado"),
                    ("failed", "Falhou"),
                ],
                default="processed",
                max_length=12,
            ),
        ),
    ]
