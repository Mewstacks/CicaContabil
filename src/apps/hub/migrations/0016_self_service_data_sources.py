import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.common.encryption
import apps.hub.models


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0015_officeprofile_trial_started_at"),
        ("organizations", "0002_alter_membership_role"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("kind", models.CharField(choices=[("companies", "Empresas"), ("obligations", "Obrigações e guias"), ("accounting", "Lançamentos contábeis"), ("fiscal_xml", "Documentos fiscais XML"), ("bank_ofx", "Extratos bancários OFX"), ("dominio_backup", "Backup completo Domínio Web")], max_length=24)),
                ("status", models.CharField(choices=[("preview", "Aguardando confirmação"), ("queued", "Na fila de extração"), ("processing", "Processando"), ("completed", "Concluído"), ("failed", "Falhou")], default="preview", max_length=16)),
                ("original_filename", models.CharField(max_length=255)),
                ("content_hash", models.CharField(max_length=64)),
                ("template_version", models.PositiveSmallIntegerField(default=1)),
                ("mapping", models.JSONField(default=dict)),
                ("encrypted_payload", apps.common.encryption.EncryptedTextField(blank=True)),
                ("source_file", models.FileField(blank=True, upload_to=apps.hub.models.private_import_path)),
                ("backup_key", apps.common.encryption.EncryptedTextField(blank=True)),
                ("source_snapshot_at", models.DateTimeField(blank=True, null=True)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("ignored_count", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(default=list)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddField(model_name="clientcompany", name="external_key", field=models.CharField(blank=True, db_index=True, max_length=160)),
        migrations.AddField(model_name="clientcompany", name="source_updated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="fiscalguide", name="external_key", field=models.CharField(blank=True, db_index=True, max_length=160)),
        migrations.AddField(model_name="fiscalguide", name="source_updated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="officeprofile", name="cnpj", field=apps.common.encryption.EncryptedTextField(blank=True)),
        migrations.AddField(model_name="officeprofile", name="cnpj_hash", field=models.CharField(blank=True, db_index=True, max_length=64)),
        migrations.AlterField(model_name="productmodule", name="code", field=models.CharField(choices=[("nfse", "NFS-e Inteligente"), ("guides", "Guias e DCTFWeb"), ("integra", "Central Integra Contador"), ("reconciliation", "Conciliação OFX x Domínio"), ("reform", "Radar da Reforma Tributária"), ("journey", "Jornada e Portal"), ("ai", "IA CICA")], max_length=32)),
        migrations.CreateModel(
            name="AccountingEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("external_key", models.CharField(max_length=160)),
                ("occurred_on", models.DateField(db_index=True)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("amount_cents", models.BigIntegerField()),
                ("direction", models.CharField(blank=True, max_length=8)),
                ("is_linked", models.BooleanField(default=False)),
                ("source_updated_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="entries", to="hub.clientcompany")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="organizations.organization")),
            ],
            options={"ordering": ("-occurred_on", "-created_at")},
        ),
        migrations.AddField(model_name="reconciliationmatch", name="accounting_entry", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reconciliation_matches", to="hub.accountingentry")),
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("kind", models.CharField(choices=[("dominio_local_agent", "Domínio Local (agente)"), ("dominio_web_backup", "Domínio Web (backup manual)"), ("other_manual", "Outro sistema (importação manual)"), ("dominio_official_api", "Domínio API oficial")], max_length=32)),
                ("label", models.CharField(max_length=120)),
                ("status", models.CharField(choices=[("not_configured", "Não configurada"), ("ready", "Pronta"), ("processing", "Processando"), ("attention", "Requer atenção"), ("disabled", "Desativada")], default="not_configured", max_length=24)),
                ("capabilities", models.JSONField(default=list)),
                ("last_import_at", models.DateTimeField(blank=True, null=True)),
                ("source_snapshot_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_code", models.CharField(blank=True, max_length=80)),
                ("last_error_message", models.CharField(blank=True, max_length=240)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="organizations.organization")),
            ],
        ),
        migrations.AddField(model_name="accountingentry", name="data_source", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="hub.datasource")),
        migrations.AddField(model_name="clientcompany", name="data_source", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="companies", to="hub.datasource")),
        migrations.AddField(model_name="fiscalguide", name="data_source", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fiscal_guides", to="hub.datasource")),
        migrations.AddConstraint(model_name="clientcompany", constraint=models.UniqueConstraint(condition=models.Q(("data_source__isnull", False), ("external_key__gt", "")), fields=("data_source", "external_key"), name="hub_unique_company_source_key")),
        migrations.AddField(model_name="importbatch", name="created_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="imports", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="importbatch", name="data_source", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="imports", to="hub.datasource")),
        migrations.AddField(model_name="importbatch", name="organization", field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="organizations.organization")),
        migrations.AddField(model_name="accountingentry", name="source_batch", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="entries", to="hub.importbatch")),
        migrations.AddField(model_name="fiscalguide", name="source_batch", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fiscal_guides", to="hub.importbatch")),
        migrations.AddConstraint(model_name="datasource", constraint=models.UniqueConstraint(fields=("organization", "kind"), name="hub_unique_data_source_kind")),
        migrations.AddConstraint(model_name="importbatch", constraint=models.UniqueConstraint(fields=("organization", "data_source", "kind", "content_hash"), name="hub_unique_import_batch_content")),
        migrations.AddIndex(model_name="accountingentry", index=models.Index(fields=["organization", "company", "occurred_on"], name="hub_account_organiz_37aec2_idx")),
        migrations.AddConstraint(model_name="accountingentry", constraint=models.UniqueConstraint(fields=("data_source", "external_key"), name="hub_unique_accounting_source_key")),
    ]
