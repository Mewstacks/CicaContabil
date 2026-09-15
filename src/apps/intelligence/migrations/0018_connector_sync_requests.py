from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("intelligence", "0017_dominiocommunication")]

    operations = [
        migrations.AddField(
            model_name="intelligenceconnector",
            name="sync_request_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="intelligenceconnector",
            name="sync_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
