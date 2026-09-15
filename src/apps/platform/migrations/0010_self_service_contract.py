import uuid

import django.db.models.deletion
from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_alter_membership_role"),
        ("platform", "0009_lead_cnpj_registry_data"),
    ]

    operations = [
        migrations.AddField(model_name="tenantcontract", name="asaas_customer_id", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="tenantcontract", name="asaas_subscription_id", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="tenantcontract", name="cancel_at_period_end", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="tenantcontract", name="pending_modules", field=models.JSONField(default=list)),
        migrations.AddField(model_name="tenantcontract", name="renews_on", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="tenantcontract", name="selected_modules", field=models.JSONField(default=list)),
        migrations.AddField(model_name="tenantcontract", name="trial_ends_on", field=models.DateField(blank=True, null=True)),
        migrations.AlterField(
            model_name="tenantcontract",
            name="status",
            field=models.CharField(
                choices=[("draft", "Rascunho"), ("trial", "Teste gratuito"), ("active", "Ativo"), ("grace", "Carência"), ("suspended", "Suspenso"), ("archived", "Arquivado")],
                default="draft",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="SignupIntent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("full_name", models.CharField(max_length=150)),
                ("password_hash", models.CharField(max_length=256)),
                ("office_name", models.CharField(max_length=180)),
                ("cnpj", apps.common.encryption.EncryptedTextField()),
                ("cnpj_hash", models.CharField(db_index=True, max_length=64)),
                ("company_count", models.PositiveIntegerField()),
                ("selected_modules", models.JSONField(default=list)),
                ("quoted_monthly_cents", models.PositiveIntegerField()),
                ("terms_version", models.CharField(max_length=32)),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("organization", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="organizations.organization")),
            ],
        ),
    ]
