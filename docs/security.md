# Security model

## Default controls

- HTTPS redirect, secure/HTTP-only/SameSite cookies, HSTS, strict hosts/origins, CSRF, XSS
  escaping, clickjacking protection, MIME sniffing protection, referrer policy, and CSP.
- Argon2 passwords, 12-character minimum, lockout after repeated failures, generic credential
  errors, and shared Redis-backed authentication throttles.
- JSON-only production APIs, authenticated-by-default DRF permissions, bounded pagination and
  uploads, explicit CORS allowlists, and request IDs.
- Non-root immutable container, pinned direct dependencies, CI lint/tests/dependency audit,
  secret scanning, and a production image build.
- PII-safe logging and Sentry: request bodies, query strings, cookies, user context, and secret
  headers are removed before transmission.

## Encryption

Infrastructure encryption and application encryption solve different threats:

- Fly Managed Postgres protects transport and storage media.
- HTTPS protects browser/API transport.
- `EncryptedTextField` uses AES-256-GCM with a new 96-bit nonce per write and authenticates the
  ciphertext. The stored format contains a version and key ID for rotation.
- Field keys and the HMAC key are independent from Django's signing key. Production refuses to
  boot without all of them.

Keep the active field key plus old decrypt-only keys in `FIELD_ENCRYPTION_KEYS`. Rotate by
adding a new ID, making it active, deploying, re-saving affected rows in bounded background
batches, verifying no old key IDs remain, then removing the old key in a later release. Never
remove a key before database backups that contain it have expired or been cryptographically
retired.

Do not encrypt values just to claim that everything is encrypted. Randomized ciphertext cannot
be indexed or searched normally and can break uniqueness. Use infrastructure encryption for
ordinary indexed fields; use application encryption for especially confidential free text,
tokens, identifiers, and incident/request narratives.

## Authentication limitations

The included session authentication is the safest default for a same-site first-party web app.
It does not include customer signup, password reset email, MFA, enterprise SSO, or service API
keys because those flows require product decisions. Before exposing privileged staff access,
add WebAuthn/TOTP or an OIDC identity provider with mandatory MFA. Keep Django admin disabled
or access-controlled until that is complete.

## Required production work

- Put the application behind a rate-limiting edge/WAF for volumetric and bot attacks.
- Restrict Fly organization membership, require MFA/SSO, rotate deploy tokens, and separate
  production from non-production organizations.
- Configure Sentry server-side scrubbers and least-retention settings in addition to SDK
  scrubbing.
- Patch dependencies promptly and subscribe to Django, Fly, PostgreSQL, Redis, and Sentry
  security advisories.
- Perform threat modeling, SAST/DAST, restore tests, and an independent penetration test before
  high-risk or large-scale processing.

See [the incident runbook](runbooks/incident-response.md) and
[backup/restore runbook](runbooks/backup-restore.md).

