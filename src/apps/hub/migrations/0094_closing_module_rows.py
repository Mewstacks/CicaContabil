from django.db import migrations

CODE = "closing"


def add_disabled_rows(apps, schema_editor):
    """Give every office that already carries module rows a disabled row for the new code.

    Same reason as ``0077_crosscheck_module_rows``: an office with explicit rows for every
    offered module and only NFS-e enabled is "NFS-e only"; a missing row would widen it.
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
        ("hub", "0093_productmodule_code_closing"),
    ]

    operations = [
        migrations.RunPython(add_disabled_rows, migrations.RunPython.noop),
    ]
