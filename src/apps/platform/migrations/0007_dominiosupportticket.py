import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("intelligence", "0020_intelligenceconnector_sync_errors"),
        ("platform", "0006_central_contract_pricing"),
    ]

    operations = [
        migrations.CreateModel(
            name="DominioSupportTicket",
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
                        choices=[
                            ("open", "Aberto"),
                            ("in_progress", "Em atendimento"),
                            ("resolved", "Resolvido"),
                        ],
                        default="open",
                        max_length=16,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=80)),
                ("error_message", apps.common.encryption.EncryptedTextField(blank=True)),
                (
                    "connector",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="support_tickets",
                        to="intelligence.intelligenceconnector",
                    ),
                ),
                (
                    "opened_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dominio_tickets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dominio_tickets",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"], name="platform_do_status_451d9e_idx"
                    )
                ],
            },
        ),
    ]
