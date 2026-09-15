from django.db import migrations

from apps.common.encryption import EncryptedTextField


def encrypt_existing_odbc_dsns(apps, schema_editor):
    """Rewrite legacy plaintext DSNs after the field begins decrypting on read."""

    connector_model = apps.get_model("intelligence", "IntelligenceConnector")
    for connector in connector_model.objects.exclude(odbc_dsn="").iterator():
        # The new field accepts legacy plaintext on read and encrypts it again on save.
        connector.save(update_fields=["odbc_dsn"])


class Migration(migrations.Migration):
    dependencies = [("intelligence", "0020_intelligenceconnector_sync_errors")]

    operations = [
        migrations.AlterField(
            model_name="intelligenceconnector",
            name="odbc_dsn",
            field=EncryptedTextField(blank=True),
        ),
        migrations.RunPython(encrypt_existing_odbc_dsns, migrations.RunPython.noop),
    ]
