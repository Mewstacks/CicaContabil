from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    dependencies = [("platform", "0019_platformconfiguration_copilot_available_for_offices")]

    operations = [
        migrations.AddField(model_name="platformconfiguration", name="local_llm_endpoint", field=models.URLField(blank=True)),
        migrations.AddField(model_name="platformconfiguration", name="local_llm_model", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="platformconfiguration", name="local_llm_api_key", field=apps.common.encryption.EncryptedTextField(blank=True)),
    ]
