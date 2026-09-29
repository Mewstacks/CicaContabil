"""Build-only settings for producing production-compatible static assets."""

from config.settings.test import *

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
