from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0002_alter_membership_role")]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="can_acknowledge_dte",
            field=models.BooleanField(default=False),
        )
    ]
