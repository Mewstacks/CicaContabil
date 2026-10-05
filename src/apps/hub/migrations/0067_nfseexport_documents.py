import uuid

from django.db import migrations, models


def link_existing_documents(apps, schema_editor):
    alias = schema_editor.connection.alias
    if alias != "default":
        return
    Export = apps.get_model("hub", "NfseExport")
    Document = apps.get_model("hub", "NfseDocument")
    Link = Export.documents.through
    for export in (
        Export.objects.using(alias)
        .only("id", "organization_id", "document_count", "snapshot")
        .iterator(chunk_size=50)
    ):
        snapshot = export.snapshot
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("documents"), list):
            continue
        try:
            ids = [uuid.UUID(item["document_id"]) for item in snapshot["documents"]]
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not ids or len(ids) != export.document_count or len(set(ids)) != len(ids):
            continue
        found = []
        for offset in range(0, len(ids), 500):
            found.extend(
                Document.objects.using(alias)
                .filter(organization_id=export.organization_id, id__in=ids[offset : offset + 500])
                .values_list("id", flat=True)
            )
        if len(found) != len(ids):
            continue
        Link.objects.using(alias).bulk_create(
            [Link(nfseexport_id=export.pk, nfsedocument_id=document_id) for document_id in found],
            batch_size=500,
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):
    dependencies = [("hub", "0066_alter_nfsesync_status")]
    operations = [
        migrations.AddField(
            model_name="nfseexport",
            name="documents",
            field=models.ManyToManyField(
                editable=False, related_name="exports", to="hub.nfsedocument"
            ),
        ),
        migrations.RunPython(link_existing_documents, migrations.RunPython.noop),
    ]
