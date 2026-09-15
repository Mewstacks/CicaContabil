from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("intelligence", "0018_connector_sync_requests")]

    operations = [
        migrations.AddField(
            model_name="intelligenceconnector",
            name="odbc_dsn",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
