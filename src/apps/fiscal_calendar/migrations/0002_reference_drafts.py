from django.db import migrations


def load_drafts(apps, schema_editor):  # type: ignore[no-untyped-def]
    from apps.fiscal_calendar.reference import load_reference_drafts

    load_reference_drafts(
        apps.get_model("fiscal_calendar", "BusinessCalendarYear"),
        apps.get_model("fiscal_calendar", "NonBusinessDay"),
        apps.get_model("fiscal_calendar", "TaxDeadlineRule"),
    )


class Migration(migrations.Migration):
    """About sixty draft rows; drafts produce no date until a platform reviewer approves them."""

    dependencies = [("fiscal_calendar", "0001_initial")]

    operations = [migrations.RunPython(load_drafts, migrations.RunPython.noop)]
