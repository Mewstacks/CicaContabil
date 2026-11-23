"""Rehearse PostgreSQL + private-file recovery using synthetic data only.

No production URL, credentials, input dump or existing container is accepted. The
cached PostgreSQL image is never pulled. Every Django process uses isolated test
settings and the container created by this invocation is removed in finally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:18-bookworm"


def docker_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("DOCKER_")}


def run(command: list[str], **kwargs: object) -> bytes:
    if Path(command[0]).name == "docker":
        kwargs.setdefault("env", docker_environment())
    return subprocess.check_output(command, **kwargs)  # noqa: S603 -- fixed commands, no shell.


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprints() -> dict[str, object]:
    """Hash every table, including raw ciphertext and the migration recorder."""
    from django.db import connections

    result = {}
    for alias in ("default", "knowledge"):
        connection = connections[alias]
        tables = {}
        with connection.cursor() as cursor:
            for table in sorted(connection.introspection.table_names(cursor)):
                quoted = connection.ops.quote_name(table)
                cursor.execute(
                    f"SELECT row_to_json(t)::text FROM {quoted} t ORDER BY 1"  # noqa: S608 -- introspected, quoted identifier.
                )
                rows = cursor.fetchall()
                content = "\n".join(row[0] for row in rows).encode()
                tables[table] = {"rows": len(rows), "sha256": hashlib.sha256(content).hexdigest()}
        result[alias] = tables
    return result


def application_phase(phase: str, area: Path) -> None:
    """Executed in a fresh process before and after restoring both databases."""
    import django
    from django.conf import settings

    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test_postgresql"
    settings.DATABASES = {
        alias: {**config, "NAME": config["NAME"] + ("_restored" if phase == "verify" else "")}
        for alias, config in settings.DATABASES.items()
    }
    settings.MEDIA_ROOT = area / ("restored_objects" if phase == "verify" else "source_objects")
    settings.ALLOWED_HOSTS = ["testserver"]
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    # Explicitly local storage even if the invoking shell had cloud configuration.
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    django.setup()
    from django.core.exceptions import SuspiciousOperation
    from django.core.management import call_command
    from django.db import connections
    from django.test import override_settings

    from apps.common.encryption import _key
    from apps.hub.models import (
        AccountingEntry,
        ClientCompany,
        FinancialAccount,
        IndependentLedgerRecord,
        JournalEntry,
        JournalLine,
        ReconciliationSourceFile,
    )
    from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
    from apps.knowledge.models import SharedKnowledgeSource
    from apps.organizations.models import Organization

    sys.path.insert(0, str(ROOT / "tests"))
    from test_native_ledger import complete, post, setup_native, snapshot

    if phase == "seed":
        for alias in ("default", "knowledge"):
            call_command("migrate", database=alias, interactive=False, verbosity=0)
        organization = Organization.objects.create(name="Recovery synthetic", slug="recovery-test")
        agent, _, job, data = setup_native.__wrapped__(organization, settings, settings.MEDIA_ROOT)
        # Exercise the existing failure/retry contract before the recovery point.
        failed = post(
            agent,
            "agent-v2-ledger-failure",
            dict(
                scope_revision=job.scope_revision,
                contract_hash=job.contract_hash,
                code="source_unavailable",
            ),
            job=job,
        )
        assert failed.status_code == 200 and failed.json()["state"] == "queued"
        completed = complete(agent, job, data)
        assert completed.status_code == 200 and completed.json()["state"] == "imported"
        knowledge_text = "Synthetic recovery procedure; no tenant data."
        SharedKnowledgeSource.objects.create(
            kind="procedure",
            title="Recovery synthetic",
            version="test-v1",
            source_reference="synthetic:recovery",
            content=knowledge_text,
            content_hash=hashlib.sha256(knowledge_text.encode()).hexdigest(),
        )
        objects = {
            str(path.relative_to(settings.MEDIA_ROOT)): digest(path)
            for path in settings.MEDIA_ROOT.rglob("*")
            if path.is_file()
        }
        write_json(
            area / "baseline.json",
            {
                "tables": fingerprints(),
                "objects": objects,
                "receipt": completed.json(),
                "frozen_at": datetime.now(UTC).isoformat(),
            },
        )
    else:
        baseline = json.loads((area / "baseline.json").read_text())
        restored = fingerprints()
        assert restored == baseline["tables"], "Restored table content differs from the backup."
        for name, expected in baseline["objects"].items():
            assert digest(settings.MEDIA_ROOT / name) == expected, "Private file differs."
        source = ReconciliationSourceFile.objects.get()
        with source.content.open("rb") as stream:
            raw = stream.read()
        assert hashlib.sha256(raw).hexdigest() == source.content_hash
        agent = EdgeAgent.objects.get()
        job = NativeLedgerCollection.objects.get()
        assert job.source_file_id == source.pk and agent.shared_secret == "synthetic-secret"  # noqa: S105 -- synthetic fixture.
        assert SharedKnowledgeSource.objects.get().content == (
            "Synthetic recovery procedure; no tenant data."
        )
        # Missing historical key must fail closed in both aliases, never look healthy.
        with override_settings(FIELD_ENCRYPTION_KEYS={}):
            _key.cache_clear()
            for model, field in ((EdgeAgent, "shared_secret"), (SharedKnowledgeSource, "content")):
                try:
                    model.objects.values_list(field, flat=True).get()
                except SuspiciousOperation:
                    pass
                else:
                    raise AssertionError(
                        "Restore without historical keys was incorrectly accepted."
                    )
        _key.cache_clear()
        before = {
            model._meta.label: model.objects.count()
            for model in (
                Organization,
                ClientCompany,
                FinancialAccount,
                NativeLedgerCollection,
                ReconciliationSourceFile,
                JournalEntry,
                JournalLine,
                IndependentLedgerRecord,
                AccountingEntry,
            )
        }
        started = time.perf_counter()
        replay = complete(agent, job, snapshot(job.scope))
        replay_seconds = time.perf_counter() - started
        assert replay.status_code == 200 and replay.json() == baseline["receipt"]
        assert before == {
            model._meta.label: model.objects.count()
            for model in (
                Organization,
                ClientCompany,
                FinancialAccount,
                NativeLedgerCollection,
                ReconciliationSourceFile,
                JournalEntry,
                JournalLine,
                IndependentLedgerRecord,
                AccountingEntry,
            )
        }
        assert JournalEntry.objects.count() == 163 and JournalLine.objects.count() == 333
        assert IndependentLedgerRecord.objects.count() == AccountingEntry.objects.count() == 163
        assert not JournalEntry.objects.exclude(state="draft", purpose="source_ledger").exists()
        # Intentionally corrupt only a second copy: the preserved restored object remains intact.
        corrupted = area / "corrupted-synthetic-copy.json"
        corrupted.write_bytes(raw + b"corruption")
        assert digest(corrupted) != source.content_hash
        write_json(
            area / "verification.json",
            {
                "all_tables_equal": True,
                "private_objects_equal": True,
                "historical_keys_required": True,
                "corrupted_copy_detected": True,
                "source_job_link_equal": True,
                "receipt_replay_equal": True,
                "counts_after_replay": before,
                "replay_seconds": replay_seconds,
                "table_counts": {alias: len(tables) for alias, tables in restored.items()},
            },
        )
    connections.close_all()


def local_docker_command() -> list[str]:
    binary = shutil.which("docker")
    if binary is None:
        raise RuntimeError("Docker and a cached postgres:18-bookworm image are required.")
    context = os.environ.get("DOCKER_CONTEXT")
    endpoint = os.environ.get("DOCKER_HOST") if not context else None
    if not endpoint:
        command = [binary, "context", "inspect"]
        if context:
            command.append(context)
        endpoint = run([*command, "--format", "{{.Endpoints.docker.Host}}"])
        endpoint = endpoint.decode().strip()
    if not endpoint.startswith("unix:///"):
        raise RuntimeError("Recovery rehearsal requires a local Docker Unix socket.")
    socket = Path(endpoint.removeprefix("unix://")).resolve(strict=True)
    if not stat.S_ISSOCK(socket.stat().st_mode):
        raise RuntimeError("The configured local Docker endpoint is not a Unix socket.")
    # Pin the verified socket for every call; Docker env cannot redirect the exercise.
    return [binary, "--host", "unix://" + str(socket)]


def rehearse(output: Path) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise FileExistsError("Use a fresh output path to preserve earlier evidence.")
    docker = local_docker_command()
    image_id = run([*docker, "image", "inspect", IMAGE, "--format", "{{.Id}}"]).decode().strip()
    container = "cica-recovery-" + uuid.uuid4().hex[:12]
    started = time.perf_counter()
    created = False
    with tempfile.TemporaryDirectory(prefix="cica-recovery-") as temporary:
        area = Path(temporary)
        # No inherited DB/storage/provider credentials enter application subprocesses.
        app_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(ROOT / "src"),
            "DJANGO_SETTINGS_MODULE": "config.settings.test_postgresql",
        }
        try:
            run(
                [
                    *docker,
                    "run",
                    "--detach",
                    "--pull=never",
                    "--name",
                    container,
                    "--label",
                    "cica.synthetic-recovery=true",
                    "--publish",
                    "127.0.0.1::5432",
                    "--tmpfs",
                    "/var/lib/postgresql:rw",
                    "--env",
                    "POSTGRES_USER=cica_test",
                    "--env",
                    "POSTGRES_PASSWORD=local-test-only",
                    "--env",
                    "POSTGRES_DB=cica_test",
                    image_id,
                ]
            )
            created = True
            port = run([*docker, "port", container, "5432/tcp"]).decode().strip()
            assert port.startswith("127.0.0.1:") and "\n" not in port
            app_env["CICA_TEST_POSTGRES_PORT"] = port.rsplit(":", 1)[1]
            for _attempt in range(100):
                check = subprocess.run(  # noqa: S603 -- fixed local container probe.
                    [*docker, "exec", container, "pg_isready", "-U", "cica_test"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=docker_environment(),
                )
                if check.returncode == 0:
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("Disposable PostgreSQL did not become ready.")
            run([*docker, "exec", container, "createdb", "-U", "cica_test", "cica_test_knowledge"])
            run([sys.executable, __file__, "--phase", "seed", "--area", str(area)], env=app_env)
            baseline = json.loads((area / "baseline.json").read_text())
            backup_started = time.perf_counter()
            for name in ("cica_test", "cica_test_knowledge"):
                run(
                    [
                        *docker,
                        "exec",
                        container,
                        "pg_dump",
                        "-U",
                        "cica_test",
                        "-Fc",
                        "--file",
                        f"/var/lib/postgresql/{name}.dump",
                        name,
                    ]
                )
            shutil.copytree(area / "source_objects", area / "backup_objects")
            backup_seconds = time.perf_counter() - backup_started
            # Remove this container's sources so verification cannot accidentally read them.
            for name in ("cica_test", "cica_test_knowledge"):
                run([*docker, "exec", container, "dropdb", "-U", "cica_test", name])
            shutil.rmtree(area / "source_objects")
            recovery_started_at = datetime.now(UTC)
            recovery_started = time.perf_counter()
            for name in ("cica_test", "cica_test_knowledge"):
                run([*docker, "exec", container, "createdb", "-U", "cica_test", name + "_restored"])
                run(
                    [
                        *docker,
                        "exec",
                        container,
                        "pg_restore",
                        "-U",
                        "cica_test",
                        "--exit-on-error",
                        "--no-owner",
                        "--dbname",
                        name + "_restored",
                        f"/var/lib/postgresql/{name}.dump",
                    ]
                )
            shutil.copytree(area / "backup_objects", area / "restored_objects")
            run([sys.executable, __file__, "--phase", "verify", "--area", str(area)], env=app_env)
            verification = json.loads((area / "verification.json").read_text())
            report = {
                "contract": "cica-synthetic-recovery-v1",
                "synthetic_only": True,
                "production_validated": False,
                "business_rpo_target_seconds": None,
                "production_rpo_seconds": None,
                "recurring_backup_configured": False,
                "postgres_image_id": image_id,
                "source_script_sha256": digest(Path(__file__)),
                "source_databases_removed_before_restore": True,
                "docker_local_socket_pinned": True,
                "source_commit": run(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
                "frozen_at": baseline["frozen_at"],
                "recovery_started_at": recovery_started_at.isoformat(),
                "recovery_completed_at": datetime.now(UTC).isoformat(),
                "backup_seconds": backup_seconds,
                "restore_and_verify_seconds": time.perf_counter() - recovery_started,
                "recovery_point_age_seconds": (
                    recovery_started_at - datetime.fromisoformat(baseline["frozen_at"])
                ).total_seconds(),
                "total_seconds": time.perf_counter() - started,
                "objects_restored": len(baseline["objects"]),
                "verification": verification,
                "limits": [
                    "synthetic corpus",
                    "no Neon restore",
                    "no Tigris restore",
                    "no real worker or Windows agent outage",
                    "no business RPO approved",
                ],
            }
        finally:
            if created:
                # Unique name generated here; never prune or remove another task's containers.
                run([*docker, "rm", "--force", "--volumes", container])
        report["temporary_container_removed"] = True
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(output, report)
        return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Recovery verification requires assertions; do not use python -O.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--phase", choices=("seed", "verify"), help=argparse.SUPPRESS)
    parser.add_argument("--area", type=Path, help=argparse.SUPPRESS)
    options = parser.parse_args()
    os.umask(0o077)
    if options.phase:
        if options.area is None:
            parser.error("An isolated work area is required.")
        application_phase(options.phase, options.area)
    else:
        if options.output is None:
            parser.error("--output is required.")
        print(json.dumps(rehearse(options.output.absolute()), indent=2))
