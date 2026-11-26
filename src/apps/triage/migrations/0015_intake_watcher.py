from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("triage", "0014_folder_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="triagepolicy",
            name="inbox_watch_enabled",
            field=models.BooleanField(default=False, db_default=False),
        ),
        migrations.AddField(
            model_name="triagepolicy",
            name="inbox_watch_path",
            field=models.CharField(blank=True, db_default="", default="", max_length=500),
        ),
        migrations.AddField(
            model_name="triagepolicy",
            name="inbox_stable_seconds",
            field=models.PositiveSmallIntegerField(db_default=30, default=30),
        ),
    ]
