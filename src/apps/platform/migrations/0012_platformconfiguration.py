import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0011_alter_tenantcontract_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="PlatformConfiguration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, editable=False, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "key",
                    models.CharField(max_length=32, unique=True, default="default", editable=False),
                ),
                ("support_email", models.EmailField(max_length=254, blank=True)),
                ("privacy_email", models.EmailField(max_length=254, blank=True)),
                ("support_hours", models.CharField(max_length=180, blank=True)),
                ("legal_address", models.CharField(max_length=300, blank=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
