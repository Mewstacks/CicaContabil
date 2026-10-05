from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0065_operationalactivity_source_dctfweb_document_and_more")]

    operations = [
        migrations.AddField(
            model_name="nfsesync",
            name="max_nsu",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AlterField(
            model_name="nfsesync",
            name="status",
            field=models.CharField(
                choices=[
                    ("paused", "Pausada"),
                    ("idle", "Aguardando"),
                    ("queued", "Na fila"),
                    ("running", "Sincronizando"),
                    ("retry", "Nova tentativa agendada"),
                    ("error", "Requer atenção"),
                ],
                default="paused",
                max_length=24,
            ),
        ),
    ]
