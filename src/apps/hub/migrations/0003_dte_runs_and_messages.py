# Generated manually for the DTE Caixa Postal module.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0002_controlplanebinding_companyaccessgrant_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DteRun",
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
                            ("awaiting_approval", "Aguardando autoriza\u00e7\u00e3o"),
                            ("queued", "Na fila"),
                            ("running", "Em consulta"),
                            ("completed", "Conclu\u00edda"),
                            ("partial", "Conclu\u00edda com pend\u00eancias"),
                            ("failed", "N\u00e3o conclu\u00edda"),
                            ("cancelled", "Cancelada"),
                        ],
                        default="awaiting_approval",
                        max_length=24,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("total_companies", models.PositiveIntegerField(default=0)),
                ("completed_companies", models.PositiveIntegerField(default=0)),
                ("messages_found", models.PositiveIntegerField(default=0)),
                ("error_summary", models.CharField(blank=True, max_length=240)),
                (
                    "connector",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dte_runs",
                        to="hub.connector",
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
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dte_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-requested_at",)},
        ),
        migrations.CreateModel(
            name="DteRunItem",
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
                            ("pending", "Aguardando"),
                            ("running", "Em consulta"),
                            ("completed", "Conclu\u00edda"),
                            ("failed", "Falhou"),
                            ("skipped", "Ignorada"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("messages_found", models.PositiveIntegerField(default=0)),
                ("service_response_id", models.CharField(blank=True, max_length=120)),
                ("error_code", models.CharField(blank=True, max_length=80)),
                ("error_message", models.CharField(blank=True, max_length=240)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dte_run_items",
                        to="hub.clientcompany",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="organizations.organization"
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="hub.dterun",
                    ),
                ),
            ],
            options={"ordering": ("company__name",)},
        ),
        migrations.CreateModel(
            name="DteMessage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_isn", models.CharField(max_length=120)),
                ("subject", models.CharField(max_length=500)),
                ("sender", models.CharField(blank=True, max_length=240)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("raw_payload", apps.common.encryption.EncryptedTextField(blank=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dte_messages",
                        to="hub.clientcompany",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="organizations.organization"
                    ),
                ),
            ],
            options={"ordering": ("-sent_at", "-first_seen_at")},
        ),
        migrations.AddIndex(
            model_name="dterun",
            index=models.Index(
                fields=["organization", "status", "requested_at"],
                name="hub_dterun_organiz_8421d3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dterunitem",
            index=models.Index(
                fields=["organization", "company", "status"], name="hub_dteruni_organiz_4b0b65_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dtemessage",
            index=models.Index(
                fields=["organization", "company", "sent_at"], name="hub_dtemess_organiz_a0a7f2_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="dterunitem",
            constraint=models.UniqueConstraint(
                fields=("run", "company"), name="hub_unique_dte_run_company"
            ),
        ),
        migrations.AddConstraint(
            model_name="dtemessage",
            constraint=models.UniqueConstraint(
                fields=("organization", "company", "source_isn"),
                name="hub_unique_dte_message_source",
            ),
        ),
    ]
