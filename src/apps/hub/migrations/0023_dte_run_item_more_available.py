from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0022_reclassify_reform_alerts")]

    operations = [
        migrations.AddField(
            model_name="dterunitem",
            name="more_available",
            field=models.BooleanField(default=False),
        )
    ]
