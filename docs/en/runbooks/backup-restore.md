# Backup and restore

[Versão em português](../../pt-BR/runbooks/backup-restauracao.md)

The current architecture uses **Neon PostgreSQL** for both `default` and
`knowledge`, and **Tigris** for private objects. Fly runs the application and
worker. The stopped legacy PostgreSQL is not production. Recheck the current
configuration and endpoints at execution time without printing credentials.

D-73 requires lossless recovery within 15 minutes and verified database and
file restoration within four hours. The **business RPO has not been approved**.
Provider defaults do not establish that requirement. V-322 proved a one-time
backup and restore; its snapshot expired on 2026-11-13 at 14:29:44 UTC. It does
not establish current protection or a recurring backup routine.

## Operational record and routine

Before enabling the routine, record in the existing PC-09/stage 12:

- approved maximum RPO, measurement window, frequency and retention;
- operator, substitute, restricted destination and recovery permissions;
- backup IDs for both databases, recoverable timestamp and expiration;
- an object manifest containing keys, sizes and SHA-256 hashes, tied to the databases;
- application version, migrations and required historical encryption key IDs;
- an already authorized alert destination, late/failure condition and response evidence.

Check the latest **recoverable set**, its age and expiration, and the presence and
integrity of every referenced file. Record failed runs too. Missing objects or
keys make a database backup incomplete. A failed run must not supersede the last
valid set. This runbook does not enable schedules, paid retention or messaging.

Keep keys out of manifests. Preserve active and required historical keys in the
existing protected mechanism, separately from backup data, and verify substitute
access. Current keys alone do not prove older ciphertext can be restored. Keep
tenant information out of the shared `knowledge` database.

## Restore exercise

1. Record operator, substitute, UTC start, simulated incident, version and selected
   set. Confirm validity and approved capacity before provisioning resources.
   Never overwrite the only production database as a restore test.
2. Isolate the destination: distinct databases/branch and object prefix; no outbound
   queues, scheduler, email, AI, official agents or ERP writes. Do not switch live
   application endpoints merely to test a restoration.
3. Restore **both** aliases to the defined point. Check schemas, migrations, counts
   and content hashes for the covered scope. Counts or schema hashes alone do not
   establish row equality.
4. Restore manifest objects privately, checking hashes, sizes, source links and
   receipts. Missing/corrupt objects or missing keys prevent recovery acceptance.
5. Supply required historical keys through the protected mechanism. Read encrypted
   application fields in both aliases without revealing plaintext. Do not generate
   a replacement key to read old data.
6. Start a compatible application version in a fresh process. Verify queries,
   reports, receipts and idempotent replay in the isolated copy. Healthy HTTP
   responses alone do not establish pending-work recovery.
7. Record UTC finish, full elapsed time, recovery point age, observed loss,
   counts/hashes, failures and limitations. Compare with approved criteria.
   Observed recovery point age does not approve a business RPO.
8. Propose a production cutover only after verification and cutover authorization,
   preserving the previous image/configuration. Remove only rehearsal resources
   and revoke temporary credentials on completion; record cleanup.

Failure before verification keeps the destination isolated. Preserve redacted
logs and resume from the last proven step; never blindly replay an uncertain
write. Code rollback requires schema compatibility. Additive migrations do not
authorize dropping tables or replacing newer decisions with an older database.
In a real incident, suspend relevant dispatches under the approved procedure
before any cutover.

Never download production dumps to developer workstations. Real copies and
verification belong in an authorized protected environment. Do not change
retention or remove the only recoverable backup during validation.

## Repeatable local rehearsal

The [synthetic script](../../../scripts/rehearse_contad_recovery.py) creates its own
PostgreSQL 18 container from an already cached image (`--pull=never`). It accepts
no production URL, credentials, dump or existing container. It uses both aliases,
real migrations, fictitious native ledger/knowledge records, private files and
test keys. It restores separate databases and verifies them in a fresh process,
then removes only its temporary container/files and retains a private JSON receipt.

```sh
python scripts/rehearse_contad_recovery.py --output /private/path/new-recovery.json
```

Use the existing development Python environment, local Docker and an already
cached `postgres:18-bookworm`. Existing receipts are never overwritten. The command rejects
`python -O`: assertions validate the rehearsal. The receipt separates backup,
restore/verification, replay and synthetic recovery point age; production RPO
and business target remain absent.

This complements the SQLite exercise in V-365. It does not test Neon, Tigris,
recurring backup, real volume, worker/Windows outages, substitute access or
customer acceptance. Actual network/worker/agent recovery and cutover still need
their own authorized exercise with end-to-end timing and the same manifest.
