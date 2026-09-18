from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0037_journalentry_source_movement_revision"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountingexport",
            name="target",
            field=models.CharField(
                choices=[("dominio", "Domínio"), ("siescon", "Siescon")],
                default="dominio",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="datasource",
            name="kind",
            field=models.CharField(
                choices=[
                    ("dominio_local_agent", "Domínio Local (agente)"),
                    ("dominio_web_backup", "Domínio Web (backup manual)"),
                    ("siescon", "Siescon"),
                    ("other_manual", "Outro sistema (importação manual)"),
                    ("dominio_official_api", "Domínio API oficial"),
                ],
                max_length=32,
            ),
        ),
    ]
