import os
from pathlib import Path

from config.settings.base import *
from config.settings.env import env_bool

SECRET_KEY = "test-only-secret-key-not-used-outside-the-test-suite"
DEBUG = env_bool("TEST_VISUAL_DEBUG", False)
DEMO_SESSION_ISOLATION_READY = env_bool("TEST_DEMO_SESSION_ISOLATION_READY", False)
test_database_path = os.environ.get("TEST_SQLITE_PATH", "")
if not env_bool("TEST_USE_EXTERNAL_SERVICES", False):
    default_database_name: str | Path = ":memory:"
    knowledge_database_name: str | Path = ":memory:"
    if test_database_path:
        default_database_name = Path(test_database_path)
        knowledge_database_name = Path(test_database_path).with_name("knowledge.sqlite3")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": default_database_name,
        },
        "knowledge": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": knowledge_database_name,
        },
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
    AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
FIELD_ENCRYPTION_ACTIVE_KEY_ID = "test-v1"
FIELD_ENCRYPTION_KEYS = {
    "test-v1": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
}
PRIVACY_HMAC_KEY = "test-independent-hmac-key"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
PLATFORM_DEVELOPER_FULL_ACCESS = True
HEALTH_READINESS_CACHE_SECONDS = 0
