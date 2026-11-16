import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hub", "0084_candidate_review_history")]

    operations = [
        migrations.AddField(
            model_name="financialaccount",
            name="current_title_snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="hub.reconciliationtitlesnapshot",
            ),
        ),
    ]
