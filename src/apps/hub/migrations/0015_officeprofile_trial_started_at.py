from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('hub', '0014_clientjourney_journeystep_portalrequest')]
    operations = [migrations.AddField(model_name='officeprofile', name='trial_started_at', field=models.DateTimeField(null=True, blank=True, editable=False))]
