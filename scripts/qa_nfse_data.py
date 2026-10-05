"""Add synthetic, cross-page NFS-e to the isolated central QA database."""

import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = ROOT / ".tmp" / "central-review"
sys.path.insert(0, str(ROOT / "src"))
os.environ.update(
    DJANGO_SETTINGS_MODULE="config.settings.test",
    TEST_SQLITE_PATH=str(QA_ROOT / "db.sqlite3"),
)
import django  # noqa: E402

django.setup()
from django.utils import timezone  # noqa: E402

from apps.hub.models import (  # noqa: E402
    ClientCompany,
    IntegrationArtifact,
    NfseDocument,
    ProductModule,
)
from apps.organizations.models import Organization  # noqa: E402

office = Organization.objects.get(slug="qa-central")
ProductModule.objects.update_or_create(
    organization=office, code="nfse", defaults={"enabled": True}
)
companies = list(ClientCompany.objects.filter(organization=office).order_by("dominio_code"))
for index in range(165):
    xml = f"<nfse><numero>QA-{index}</numero></nfse>"
    document, _ = NfseDocument.objects.get_or_create(
        organization=office,
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        defaults={
            "company": companies[index % len(companies)],
            "original_xml": xml,
            "source_nsu": f"QA-{index}",
            "issued_at": timezone.now(),
            "normalized_data": {"number": f"QA-{index}"},
        },
    )
    IntegrationArtifact.objects.get_or_create(
        organization=office,
        document=document,
        defaults={"accumulator_code": "QA-1", "applied_rule": "Synthetic QA", "confidence": 100},
    )
print("165 synthetic classified documents available in central-review only.")
