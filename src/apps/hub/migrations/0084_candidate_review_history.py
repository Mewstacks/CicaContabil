from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0083_reconciliationaccountcandidate")]
    operations = [migrations.AddField(
        model_name="reconciliationaccountcandidate", name="review_history",
        field=models.JSONField(default=list, db_default=[], blank=True),
    ), migrations.AddField(
        model_name="financialaccount", name="review_history",
        field=models.JSONField(default=list, db_default=[], blank=True),
    )]
