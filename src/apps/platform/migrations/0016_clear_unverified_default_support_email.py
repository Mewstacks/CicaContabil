from django.db import migrations


def clear_unverified_default_email(apps, schema_editor):
    """Remove the contact that an earlier migration guessed instead of verified."""
    configuration = apps.get_model("platform", "PlatformConfiguration")
    configuration.objects.filter(
        key="default",
        support_email="admin@mewstack.com",
        updated_by__isnull=True,
    ).update(support_email="")


class Migration(migrations.Migration):
    dependencies = [("platform", "0015_invitation_modules")]

    operations = [
        migrations.RunPython(clear_unverified_default_email, migrations.RunPython.noop),
    ]
