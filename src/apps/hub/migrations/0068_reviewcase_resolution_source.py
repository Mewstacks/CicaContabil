from django.db import migrations, models


def mark_existing_human_resolutions(apps, schema_editor) -> None:
    ReviewCase = apps.get_model("hub", "ReviewCase")
    ReviewCase.objects.filter(status="resolved", resolved_by__isnull=False).update(
        resolution_source="human"
    )


class Migration(migrations.Migration):
    dependencies = [("hub", "0067_nfseexport_documents")]

    operations = [
        migrations.AddField(
            model_name="reviewcase",
            name="resolution_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("human", "Decisão humana"),
                    ("backup", "Reclassificação pelo backup"),
                ],
                max_length=16,
            ),
        ),
        migrations.RunPython(mark_existing_human_resolutions, migrations.RunPython.noop),
    ]
