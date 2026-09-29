"""Disposable loopback PostgreSQL only; keep all other test services local/mocked."""

import os

from config.settings.env import env_bool
from config.settings.test import *

if env_bool("TEST_USE_EXTERNAL_SERVICES", False):
    raise RuntimeError("PostgreSQL validation must not enable other external services.")

test_postgres_port = int(os.environ["CICA_TEST_POSTGRES_PORT"])
if not 1024 <= test_postgres_port <= 65535 or test_postgres_port == 5432:
    raise RuntimeError("Use the disposable container's non-default loopback port.")

DATABASES = {
    alias: {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "127.0.0.1",
        "PORT": test_postgres_port,
        "USER": "cica_test",
        "PASSWORD": "local-test-only",
        "NAME": name,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
        "TEST": {"NAME": f"test_{name}"},
    }
    for alias, name in (("default", "cica_test"), ("knowledge", "cica_test_knowledge"))
}
