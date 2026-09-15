from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("intelligence", "0019_intelligenceconnector_odbc_dsn")]

    operations = [
        migrations.AddField(
            model_name="intelligenceconnector",
            name="last_error_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="intelligenceconnector",
            name="last_error_code",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="intelligenceconnector",
            name="last_error_message",
            field=models.CharField(blank=True, max_length=240),
        ),
    ]
