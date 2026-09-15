from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("platform", "0020_platformconfiguration_local_llm_runtime")]

    operations = [
        migrations.AddField(
            model_name="platformconfiguration",
            name="local_multimodal_endpoint",
            field=models.URLField(blank=True),
        )
    ]
