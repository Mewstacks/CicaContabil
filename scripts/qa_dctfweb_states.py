"""Seed five synthetic DCTFWeb states in the existing isolated UI QA database only."""

import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_DB = ROOT / ".tmp" / "ui-review" / "db.sqlite3"
if not QA_DB.is_file():
    raise RuntimeError("Start qa_ui_server.py once before seeding these local states")
sys.path.insert(0, str(ROOT / "src"))
os.environ.update(DJANGO_SETTINGS_MODULE="config.settings.test", TEST_SQLITE_PATH=str(QA_DB))

import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.utils import timezone  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from apps.hub.models import ClientCompany, DctfWebDocument  # noqa: E402
from apps.organizations.models import Organization  # noqa: E402

assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
assert Path(settings.DATABASES["default"]["NAME"]).resolve() == QA_DB.resolve()
office = Organization.objects.get(slug="ui-large-portfolio", is_demo=False)
companies = list(ClientCompany.objects.filter(organization=office).order_by("dominio_code")[:5])
if len(companies) != 5:
    raise RuntimeError("Synthetic QA portfolio is missing")
buffer = BytesIO()
pdf = canvas.Canvas(buffer)
pdf.drawString(40, 780, "QA SINTETICO - SEM VALIDADE FISCAL OU BANCARIA")
pdf.save()
payload = json.dumps(
    {"dados": json.dumps({"PDFByteArrayBase64": base64.b64encode(buffer.getvalue()).decode()})}
)
for company, status in zip(companies, DctfWebDocument.Status.values, strict=True):
    DctfWebDocument.objects.update_or_create(
        organization=office,
        company=company,
        competence="09/2026",
        kind="receipt",
        defaults={
            "status": status,
            "service_key": "dctfweb.recibo",
            "provider_payload": payload if status == "available" else "",
            "completed_at": timezone.now() if status == "available" else None,
            "error_message": "Cenário sintético: certificado recusado."
            if status == "failed"
            else "",
        },
    )
    print(f"{status}: /app/guias/dctfweb/consultar/?company={company.pk}&competence=09/2026")
