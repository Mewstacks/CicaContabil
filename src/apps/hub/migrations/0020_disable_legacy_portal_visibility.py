from django.db import migrations


def disable_legacy_portal_visibility(apps, schema_editor):
    del schema_editor
    apps.get_model("hub", "ClientJourney").objects.update(portal_visible=False)
    apps.get_model("hub", "PortalRequest").objects.update(portal_visible=False)


class Migration(migrations.Migration):
    dependencies = [("hub", "0019_alter_portalrequest_portal_visible_and_more")]

    operations = [migrations.RunPython(disable_legacy_portal_visibility, migrations.RunPython.noop)]
