from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0024_dtemessageaccess")]

    operations = [
        migrations.AddField(
            model_name="dtemessage",
            name="source_science_at",
            field=models.DateTimeField(blank=True, null=True),
        )
    ]
