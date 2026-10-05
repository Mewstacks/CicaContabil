import os
import subprocess
import sys
from pathlib import Path

import pytest


def _load_settings(port, external_services="false", assertions=""):
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "TEST_USE_EXTERNAL_SERVICES": external_services,
        "DATABASE_URL": "postgresql://unused:unused@production.invalid/main",
        "KNOWLEDGE_DATABASE_URL": "postgresql://unused:unused@production.invalid/knowledge",
    }
    env.pop("CICA_TEST_POSTGRES_PORT", None)
    if port is not None:
        env["CICA_TEST_POSTGRES_PORT"] = str(port)
    # Python and assertions come only from this test module; no shell or user input.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import config.settings.test_postgresql as s; " + assertions],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize("port", [None, 5432, 0, 65536, "invalid"])
def test_postgresql_test_settings_refuse_missing_or_unsafe_port(port):
    result = _load_settings(port)
    assert result.returncode != 0


def test_postgresql_test_settings_refuse_external_service_mode():
    result = _load_settings(55432, external_services="true")
    assert result.returncode != 0
    assert "must not enable other external services" in result.stderr


def test_postgresql_test_settings_ignore_production_urls_and_keep_other_services_local():
    result = _load_settings(
        55432,
        assertions=(
            "assert set(s.DATABASES) == {'default', 'knowledge'}; "
            "assert all(db['HOST'] == '127.0.0.1' and db['PORT'] == 55432 "
            "and db['USER'] == 'cica_test' and db['NAME'].startswith('cica_test') "
            "for db in s.DATABASES.values()); "
            "assert s.CACHES['default']['BACKEND'].endswith('LocMemCache'); "
            "assert s.EMAIL_BACKEND.endswith('locmem.EmailBackend'); "
            "assert s.CELERY_TASK_ALWAYS_EAGER"
        ),
    )
    assert result.returncode == 0, result.stderr
