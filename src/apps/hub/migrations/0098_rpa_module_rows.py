from django.db import migrations

CODES = ("folha", "fgts", "det", "fap", "admissions")


def add_disabled_rows(apps, schema_editor):
    """Cada escritório que já tem linhas de módulo recebe a linha DESLIGADA dos blocos RPA.

    Mesma razão de ``0094_closing_module_rows``: sem a linha explícita, um escritório com todas
    as outras linhas e só NFS-e ligada passaria de "só NFS-e" a algo mais amplo.
    """

    ProductModule = apps.get_model("hub", "ProductModule")
    configured = set(ProductModule.objects.values_list("organization_id", flat=True))
    for code in CODES:
        already = set(
            ProductModule.objects.filter(code=code).values_list("organization_id", flat=True)
        )
        ProductModule.objects.bulk_create(
            [
                ProductModule(organization_id=organization_id, code=code, enabled=False)
                for organization_id in sorted(configured - already, key=str)
            ],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0097_alter_productmodule_code"),
    ]

    operations = [
        migrations.RunPython(add_disabled_rows, migrations.RunPython.noop),
    ]
