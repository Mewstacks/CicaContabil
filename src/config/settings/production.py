from __future__ import annotations

import base64

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *
from config.settings.env import env_bool, env_int, env_str

DEBUG = False
PLATFORM_DEVELOPER_FULL_ACCESS = False
EDGE_AGENT_MTLS_REQUIRED = env_bool("EDGE_AGENT_MTLS_REQUIRED", True)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

fly_app_name = env_str("FLY_APP_NAME")
if fly_app_name:
    fly_hostname = f"{fly_app_name}.fly.dev"
    if fly_hostname not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(fly_hostname)
    fly_origin = f"https://{fly_hostname}"
    if fly_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(fly_origin)

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("insecure-"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a random value of at least 50 characters."
    )
if "*" in ALLOWED_HOSTS or not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set explicit DJANGO_ALLOWED_HOSTS values; wildcards are forbidden.")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires PostgreSQL.")
if not env_str("KNOWLEDGE_DATABASE_URL"):
    raise ImproperlyConfigured("Production requires an explicit KNOWLEDGE_DATABASE_URL.")
if DATABASES["knowledge"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Shared knowledge requires PostgreSQL.")
if (
    DATABASES["knowledge"]["HOST"],
    DATABASES["knowledge"]["PORT"],
    DATABASES["knowledge"]["NAME"],
) == (DATABASES["default"]["HOST"], DATABASES["default"]["PORT"], DATABASES["default"]["NAME"]):
    raise ImproperlyConfigured(
        "KNOWLEDGE_DATABASE_URL must point to a database separate from tenant data."
    )
# Refusing sslmode=disable is not enough: with DB_SSL_REQUIRE unset and no sslmode in the
# URL, libpq falls back to "prefer" and silently accepts a plaintext connection. Demand an
# explicit, verified mode instead. A deployment whose database traffic never leaves a private
# encrypted network (a Fly .internal mesh, a WireGuard tunnel) opts out on purpose.
SECURE_DB_SSL_MODES = {"require", "verify-ca", "verify-full"}
if not env_bool("DB_TLS_ENFORCED_BY_NETWORK", False):
    for alias in ("default", "knowledge"):
        mode = DATABASES[alias].get("OPTIONS", {}).get("sslmode")
        if mode not in SECURE_DB_SSL_MODES:
            raise ImproperlyConfigured(
                f"The {alias} database needs sslmode in {sorted(SECURE_DB_SSL_MODES)}; "
                f"got {mode!r}. Set DB_SSL_REQUIRE=true, put sslmode in the URL, or set "
                "DB_TLS_ENFORCED_BY_NETWORK=true when the link is already encrypted."
            )
if not redis_url:
    raise ImproperlyConfigured("Production requires REDIS_URL.")
if not FIELD_ENCRYPTION_KEYS or not FIELD_ENCRYPTION_ACTIVE_KEY_ID:
    raise ImproperlyConfigured("Production field encryption keys are required.")
if FIELD_ENCRYPTION_ACTIVE_KEY_ID not in FIELD_ENCRYPTION_KEYS:
    raise ImproperlyConfigured("The active field encryption key ID is missing from the key ring.")
for key_id, encoded_key in FIELD_ENCRYPTION_KEYS.items():
    try:
        decoded_key = base64.urlsafe_b64decode(encoded_key)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"Field encryption key {key_id!r} is invalid.") from exc
    if len(decoded_key) != 32:
        raise ImproperlyConfigured(
            f"Field encryption key {key_id!r} must decode to exactly 32 bytes."
        )
if len(PRIVACY_HMAC_KEY) < 32:
    raise ImproperlyConfigured("PRIVACY_HMAC_KEY must contain at least 32 random characters.")

ADMIN_ENABLED = env_bool("ADMIN_ENABLED", False)
API_DOCS_ENABLED = env_bool("API_DOCS_ENABLED", False)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env_bool("DB_PGBOUNCER", True)

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
for cookie_name, samesite in (
    ("SESSION_COOKIE_SAMESITE", SESSION_COOKIE_SAMESITE),
    ("CSRF_COOKIE_SAMESITE", CSRF_COOKIE_SAMESITE),
):
    if samesite not in {"Lax", "Strict", "None"}:
        raise ImproperlyConfigured(f"{cookie_name} must be 'Lax', 'Strict', or 'None'.")
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}

media_bucket = env_str("BUCKET_NAME") or env_str("AWS_MEDIA_BUCKET")
if env_bool("OBJECT_STORAGE_REQUIRED", False) and not media_bucket:
    raise ImproperlyConfigured(
        "Production object storage is required but BUCKET_NAME/AWS_MEDIA_BUCKET is missing."
    )
if media_bucket:
    object_parameters = {}
    media_kms_key = env_str("AWS_MEDIA_KMS_KEY_ID")
    if media_kms_key:
        object_parameters = {
            "ServerSideEncryption": "aws:kms",
            "SSEKMSKeyId": media_kms_key,
        }
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": media_bucket,
            "region_name": env_str("AWS_REGION", "auto"),
            "endpoint_url": env_str("AWS_ENDPOINT_URL_S3") or None,
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
            "object_parameters": object_parameters,
        },
    }

# The developer console holds the platform SMTP credentials encrypted at rest.
# A production process never reads delivery credentials from environment variables.
EMAIL_BACKEND = "apps.common.database_email.DatabaseEmailBackend"

sentry_enabled = env_bool("SENTRY_ENABLED", True)
sentry_dsn = env_str("SENTRY_DSN")
if sentry_enabled and not sentry_dsn:
    raise ImproperlyConfigured(
        "SENTRY_DSN is required in production; set SENTRY_ENABLED=false only intentionally."
    )
if sentry_enabled:
    import sentry_sdk

    from apps.common.sentry import before_send, before_send_transaction, traces_sampler

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=env_str("SENTRY_ENVIRONMENT", "production"),
        release=env_str("SENTRY_RELEASE") or env_str("FLY_IMAGE_REF") or None,
        send_default_pii=False,
        before_send=before_send,
        before_send_transaction=before_send_transaction,
        traces_sampler=traces_sampler,
        profiles_sample_rate=0.0,
        max_breadcrumbs=50,
        max_request_body_size="never",
        include_local_variables=False,
        include_source_context=False,
    )
