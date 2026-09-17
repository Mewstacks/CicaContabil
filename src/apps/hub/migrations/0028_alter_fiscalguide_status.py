from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0027_dterunitem_continued_from_and_more")]

    operations = [
        migrations.AlterField(
            model_name="fiscalguide",
            name="status",
            field=models.CharField(
                choices=[
                    ("discovered", "Apuração a conferir"),
                    ("ready", "Pronta para emitir"),
                    ("queued", "Na fila"),
                    ("issuing", "Emitindo"),
                    ("issued", "Emitida"),
                    ("failed", "Não emitida"),
                    ("skipped", "Dispensada"),
                ],
                default="ready",
                max_length=16,
            ),
        )
    ]
