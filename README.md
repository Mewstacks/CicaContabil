# Security-first Django SaaS backend

A clone-per-product Django 6 backend with organization tenancy, a versioned REST API,
privacy workflows, append-only audit events, application-level AES-256-GCM fields,
PostgreSQL, Redis/Celery, Sentry, Docker, and a first-class Fly.io deployment.

Para instalação e uso em português, consulte o
[guia rápido em português](docs/guia-rapido-pt-br.md).

This repository supplies technical controls and operational evidence for an LGPD program. It
does not make a product legally compliant by itself; each product still needs a data inventory,
lawful-basis assessment, privacy notice, contracts, retention decisions, incident ownership,
and qualified Brazilian legal/privacy review.

## What is included

- Email-based UUID users with Argon2 password hashing, CSRF-protected session authentication,
  login throttling, and account lockouts.
- Optional organization tenancy with explicit `X-Organization-ID` resolution through active
  membership—there is no unsafe implicit tenant fallback.
- Processing-purpose and privacy-notice records, append-only consent evidence, data-subject
  request tracking, and five-year personal-data incident records.
- Independent AES-256-GCM field keys and HMAC keys, safe rotation support, TLS/secure-cookie
  production defaults, native Django CSP, and strict host/origin validation.
- JSON logs with request/organization correlation and redaction; privacy-safe Sentry event and
  trace capture with health-check exclusion.
- PostgreSQL readiness, Redis-backed cache/sessions/throttles, Celery worker processes,
  Docker Compose, Fly.io release migrations, and CI dependency/image checks.

Read [the architecture](docs/architecture.md), [security model](docs/security.md), and
[LGPD implementation guide](docs/lgpd.md) before adding product features.

## Local quick start

Python 3.12 is required. Docker is optional.

```powershell
python -m pip install uv==0.12.0
uv sync --locked --all-extras
.\.venv\Scripts\Activate.ps1
python scripts/init_local.py --sqlite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For PostgreSQL and Redis, omit `--sqlite`, install Docker Desktop, then run:

```powershell
docker compose up -d postgres redis
python manage.py migrate
python manage.py runserver
```

API documentation is at `http://127.0.0.1:8000/api/docs/`. A browser client first calls
`GET /api/v1/auth/csrf/`, sends the returned token as `X-CSRFToken`, and then posts credentials
to `/api/v1/auth/login/`.

Run the validation suite with:

```powershell
ruff check .
ruff format --check .
mypy src
pytest --cov
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Fly.io deployment

The production path keeps the app and managed data services in São Paulo (`gru`). Install and
authenticate `flyctl`, choose a globally unique lowercase app name, then:

```powershell
python scripts/configure_fly.py your-unique-app-name
fly apps create your-unique-app-name
python scripts/generate_production_secrets.py | fly secrets import -a your-unique-app-name
fly mpg create
fly mpg attach YOUR_MPG_CLUSTER_ID -a your-unique-app-name
fly redis create
fly storage create -a your-unique-app-name
fly secrets set SENTRY_DSN="YOUR_SENTRY_DSN" -a your-unique-app-name
fly deploy
fly scale count web=2 worker=1 -a your-unique-app-name
```

Choose `gru` for Managed Postgres and Redis. After `fly redis create`, copy its private URL
into all three runtime values:

```powershell
fly secrets set REDIS_URL="YOUR_PRIVATE_REDIS_URL" CELERY_BROKER_URL="YOUR_PRIVATE_REDIS_URL" CELERY_RESULT_BACKEND="YOUR_PRIVATE_REDIS_URL" -a your-unique-app-name
```

`fly mpg attach` provides the pooled `DATABASE_URL`. `fly storage create` provisions a private
Tigris bucket and injects its S3-compatible credentials. Every deploy runs migrations once in
a temporary release Machine; failure aborts the rollout. The service uses readiness checks and
two independently scalable process groups.

Before accepting traffic:

1. Add the production domain to `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and
   `DJANGO_CORS_ALLOWED_ORIGINS` with `fly secrets set`.
   Because HSTS includes subdomains and the preload directive, confirm every subdomain is
   permanently HTTPS before serving a custom parent domain; otherwise explicitly disable
   those two options until the domain is ready.
2. Keep admin/API docs disabled publicly. For a temporary operations session, set
   `ADMIN_ENABLED=true`, create a superuser through `fly ssh console`, and disable it again;
   add staff MFA/SSO before making it persistent.
3. Verify `python manage.py check --deploy` through `fly ssh console`.
4. Configure a custom domain/TLS, Sentry alerts, Fly billing alerts, database alerts, and
   external uptime monitoring.
5. Test a Managed Postgres restore and a field-key rotation in staging.
6. Complete the product-specific LGPD checklist in [docs/lgpd.md](docs/lgpd.md).

Detailed commands and rollback notes are in [docs/deployment-fly.md](docs/deployment-fly.md).

## Replicating for a new SaaS

Follow [docs/clone-checklist.md](docs/clone-checklist.md). Product tables containing tenant data
must inherit `OrganizationScopedModel`, require explicit organization context at the API
boundary, and filter every query by `request.organization`. Encryption is for confidential
values that do not need normal database lookup; use a keyed blind index for equality lookup
when truly required.
