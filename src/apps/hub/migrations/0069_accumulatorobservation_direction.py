from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0068_reviewcase_resolution_source")]

    operations = [
        migrations.AddField(
            model_name="accumulatorobservation",
            name="direction",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Sem direção"),
                    ("taken", "Tomada (entrada)"),
                    ("provided", "Prestada (serviço)"),
                ],
                default="",
                max_length=16,
            ),
        ),
    ]
