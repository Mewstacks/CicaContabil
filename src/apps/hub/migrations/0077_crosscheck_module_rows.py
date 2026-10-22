from django.db import migrations

CODE = "crosscheck"


def add_disabled_rows(apps, schema_editor):
    """Give every office that already carries module rows a disabled row for the new code.

    `workspace_context` calls an office "NFS-e only" when it has explicit rows for every
    offered module and only NFS-e is enabled. A new offered code without a row would flip
    that test to false and widen the surface of an office that never asked for it. Offices
    with no module rows at all keep the legacy path (NFS-e implied), so they get nothing.
    """

    ProductModule = apps.get_model("hub", "ProductModule")
    configured = set(ProductModule.objects.values_list("organization_id", flat=True))
    already = set(ProductModule.objects.filter(code=CODE).values_list("organization_id", flat=True))
    ProductModule.objects.bulk_create(
        [
            ProductModule(organization_id=organization_id, code=CODE, enabled=False)
            for organization_id in sorted(configured - already, key=str)
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0076_productmodule_code_crosscheck"),
    ]

    operations = [
        migrations.RunPython(add_disabled_rows, migrations.RunPython.noop),
    ]
