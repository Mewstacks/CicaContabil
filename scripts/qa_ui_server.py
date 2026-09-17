"""Disposable UI review server. No .env, production data or outbound sockets.

Run with .venv/Scripts/python scripts/qa_ui_server.py, then open port 8011.
The databases/media live under .tmp/ui-review; restart preserves review progress.
"""

from __future__ import annotations

import os
import socket
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = ROOT / ".tmp" / "ui-review"
QA_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
os.environ.update(
    DJANGO_SETTINGS_MODULE="config.settings.test",
    TEST_SQLITE_PATH=str(QA_ROOT / "db.sqlite3"),
    TEST_VISUAL_DEBUG="true",
    TEST_DEMO_SESSION_ISOLATION_READY="true",
    DEMO_ENTRY_ENABLED="true",
)

import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.hub.models import ClientCompany, ProductModule  # noqa: E402
from apps.hub.seeding import DEFAULT_PASSWORD  # noqa: E402
from apps.intelligence.connectors import ReadOnlyDominoOdbc  # noqa: E402
from apps.intelligence.models import IntelligenceConnector  # noqa: E402
from apps.organizations.models import Membership, Organization  # noqa: E402
from apps.platform.models import TenantLifecycle  # noqa: E402

settings.MEDIA_ROOT = QA_ROOT / "media"
settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.SECURE_SSL_REDIRECT = False
settings.TEMPLATES[0]["APP_DIRS"] = False
settings.TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

original_connect = socket.socket.connect


def local_connect(self: socket.socket, address: object) -> None:
    if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise OSError("UI review: outbound connections are disabled")
    original_connect(self, address)


socket.socket.connect = local_connect
for alias in ("default", "knowledge"):
    call_command("migrate", database=alias, verbosity=0)
if not (QA_ROOT / "seeded").exists():
    call_command("seed_demo", password=DEFAULT_PASSWORD, verbosity=0)
    call_command("seed_personas", verbosity=0)
    (QA_ROOT / "seeded").touch()
large_office, _ = Organization.objects.get_or_create(
    slug="ui-large-portfolio",
    defaults={
        "name": "Escritório QA — carteira extensa e nomes longos para validação de interface"
    },
)
TenantLifecycle.objects.get_or_create(organization=large_office, defaults={"state": "active"})
Membership.objects.get_or_create(
    organization=large_office,
    user=User.objects.get(email="demo@hubcontador.local"),
    defaults={"role": "owner"},
)
if not ClientCompany.objects.filter(organization=large_office).exists():
    ClientCompany.objects.bulk_create(
        [
            ClientCompany(
                organization=large_office,
                name=f"Empresa QA {number:03d} — Comércio, Serviços e Consultoria Contábil "
                "de Longo Nome para Verificação Responsiva",
                dominio_code=f"QA{number:03d}",
            )
            for number in range(240)
        ]
    )
ProductModule.objects.get_or_create(
    organization=large_office, code="guides", defaults={"enabled": True}
)
IntelligenceConnector.objects.update_or_create(
    organization=large_office,
    mode="direct_odbc",
    defaults={"status": "healthy", "odbc_dsn": "UI_QA_SYNTHETIC"},
)
qa_companies = list(
    ClientCompany.objects.filter(organization=large_office).order_by("dominio_code")
)


def synthetic_odbc(self: ReadOnlyDominoOdbc, query_name: str) -> list[dict[str, object]]:
    if self.dsn != "UI_QA_SYNTHETIC":
        raise RuntimeError("UI review: external ODBC connections are disabled")
    if query_name != "guide_calculations":
        return []
    rows = []
    for index in range(2945):
        year, month = divmod(2026 * 12 + 8 - index // len(qa_companies), 12)
        due_year, due_month = divmod(year * 12 + month + 1, 12)
        rows.append(
            {
                "source_id": f"UI-QA-{index}",
                "company_code": qa_companies[index % len(qa_companies)].dominio_code,
                "competence": date(year, month + 1, 1),
                "due_on": date(due_year, due_month + 1, 20),
                "amount": "5308.07" if index % 2 else "178.31",
            }
        )
    return rows


ReadOnlyDominoOdbc.execute = synthetic_odbc
print("Isolated UI review: http://127.0.0.1:8011/ (outbound connections blocked)", flush=True)
call_command("runserver", "127.0.0.1:8011", use_reloader=False)
