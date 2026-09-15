import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

from apps.common.encryption import EncryptedTextField


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0023_dte_run_item_more_available"),
        ("organizations", "0003_membership_can_acknowledge_dte"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DteMessageAccess",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=[
                            ("reading", "Abertura em andamento"),
                            ("opened", "Teor consultado"),
                            ("failed", "Consulta recusada"),
                            ("unknown", "Resultado a confirmar"),
                        ],
                    ),
                ),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("requested_at", models.DateTimeField(default=timezone.now)),
                ("opened_at", models.DateTimeField(null=True, blank=True)),
                ("provider_read_at", models.DateTimeField(null=True, blank=True)),
                ("provider_science_at", models.DateTimeField(null=True, blank=True)),
                ("provider_request_id", models.CharField(max_length=160, blank=True)),
                ("provider_payload", EncryptedTextField(blank=True)),
                ("error_message", models.CharField(max_length=240, blank=True)),
                (
                    "message",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="access_receipt",
                        to="hub.dtemessage",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="organizations.organization"
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dte_detail_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["organization", "status", "requested_at"],
                        name="hub_dtemess_organiz_8a5b1c_idx",
                    )
                ]
            },
        )
    ]
