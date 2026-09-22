from pathlib import Path

from dotenv import load_dotenv

# override=True: Django's autoreloader re-executes the server with the environment the
# first boot left behind, so a value already in os.environ would outlive every edit to
# .env and only a full kill would clear it. In development the file is the source.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)

from config.settings.base import *  # noqa: E402
from config.settings.env import env_bool  # noqa: E402

DEBUG = True
ADMIN_ENABLED = True
API_DOCS_ENABLED = True
PLATFORM_DEVELOPER_FULL_ACCESS = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

# Development must not depend on a running Redis. base.py builds a RedisCache whenever
# REDIS_URL is set, with IGNORE_EXCEPTIONS off — so with Redis down every throttled API
# call and the public proposal form (rate limited through the cache) return a 500 that
# has nothing to do with the code under test. Opt back in with LOCAL_USE_REDIS=true when
# you are specifically exercising the Redis path.
if not env_bool("LOCAL_USE_REDIS", False):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "hub-local-cache",
        }
    }

# ManifestStaticFilesStorage resolves {% static %} through staticfiles.json, so any asset
# added since the last collectstatic raises at render time. test.py already overrides this;
# without the same override here development is stricter than production and breaks on new
# files. Production keeps the manifest.
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
