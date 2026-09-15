from django.db import migrations

from apps.common.encryption import EncryptedTextField


class Migration(migrations.Migration):
    dependencies = [('platform', '0008_payment_webhook_delivery')]
    operations = [
        migrations.AddField(model_name='lead', name='cnpj', field=EncryptedTextField(blank=True, default='')),
        migrations.AddField(model_name='lead', name='registry_data', field=EncryptedTextField(blank=True, default='')),
    ]
