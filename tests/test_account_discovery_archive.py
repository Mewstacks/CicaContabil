"""The large-source path is bounded, reversible, atomic and fail-closed."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import zipfile
import zlib
from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from account_discovery_fixtures import write_discovery_archive
from apps.hub.account_discovery import (
    AccountDiscoveryError,
    _consistent_discovery,
    import_account_discovery,
    latest_consistent_discovery,
    prepared_account_facts,
)
from apps.hub.account_discovery_archive import (
    BLOCK_LIMIT,
    DiscoveryStage,
    decompress_block,
)
from apps.hub.account_discovery_contract import Invalid
from apps.hub.models import (
    ReconciliationAccountDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationDiscoverySourceBlock,
)
from apps.organizations.models import Organization
from test_account_discovery import discovered_profile as discovered_profile_fixture
from test_account_discovery import scoped
from test_account_discovery import sources as sources_fixture
from test_account_source_details import protected
from test_portfolio_readiness import encode

sources = sources_fixture
discovered_profile = discovered_profile_fixture
pytestmark = pytest.mark.django_db


def run_archive(organization, sources, package, **kwargs):
    return import_account_discovery(
        organization=organization,
        portfolio_raw=encode(sources[0]),
        accounts_raw=encode(sources[1]),
        request_reference="Synthetic archive validation",
        **package,
        **kwargs,
    )


def with_sources(profile):
    result = deepcopy(profile)
    sample = result["snapshot"]["chart_accounts"][0]
    result["snapshot"]["plan_template_accounts"] = [
        dict(sample, plan_id_raw=7, account_code=n, account_name_raw="Literal\t\ue000 ")
        for n in range(1, 1500)
    ]
    result["snapshot"]["nature_rules"] = [
        dict(
            chart_company_code=212,
            rule_order=0,
            classification_raw="001 ",
            nature_raw="D",
            group_raw=" ",
        )
    ]
    return result


def test_zip_path_preview_apply_replay_retains_literal_blocks_without_human_mutations(
    organization,
    sources,
    discovered_profile,
    tmp_path,
):
    profile = with_sources(discovered_profile)
    package = write_discovery_archive(profile, tmp_path / "source.zip")
    before = protected()
    preview = run_archive(organization, sources, package)
    assert protected() == before
    applied = run_archive(
        organization, sources, package, apply=True, expected_manifest=preview["manifest_sha256"]
    )
    assert applied["created"] == 1 and applied["source_blocks_created"] >= 3
    batch = latest_consistent_discovery(organization)
    assert _consistent_discovery(batch, deep=True)
    assert prepared_account_facts(*scoped(batch), month="2026-09")["valid"]
    for table in ("plan_template_accounts", "nature_rules"):
        raw = b"".join(
            decompress_block(bytes(block.compressed_data), block.raw_size_bytes)
            for block in batch.source_blocks.filter(table_name=table)
        )
        assert [json.loads(line) for line in raw.splitlines()] == profile["snapshot"][table]
        assert len(raw) == batch.source_data[table]["bytes"]
    assert run_archive(organization, sources, package, apply=True)["created"] == 0
    assert protected() == before


def rewrite_zip(path, mutation):
    with zipfile.ZipFile(path) as archive:
        entries = [(info, archive.read(info)) for info in archive.infolist()]
    entries = mutation(entries)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, data)
    raw = path.read_bytes()
    return dict(
        discovery_path=path,
        expected_size_bytes=len(raw),
        expected_sha256=hashlib.sha256(raw).hexdigest(),
    )


@pytest.mark.parametrize(
    "problem",
    [
        "extra",
        "missing",
        "duplicate",
        "symlink",
        "descriptor_hash",
        "descriptor_rows",
        "descriptor_bytes",
        "truncated_line",
        "crlf",
        "bom",
        "duplicate_key",
        "wrong_owner",
        "duplicate_account",
        "bad_contract",
        "nul",
    ],
)
def test_malformed_archives_never_write(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    problem,
):
    path = tmp_path / "bad.zip"
    write_discovery_archive(discovered_profile, path)

    def mutate(entries):
        if problem == "extra":
            return [*entries, ("../unexpected", b"private")]
        if problem == "missing":
            return entries[1:]
        if problem == "duplicate":
            return [*entries, entries[0]]
        if problem == "symlink":
            entries[0][0].external_attr = (stat.S_IFLNK | 0o777) << 16
            return entries
        source = {info.filename: data for info, data in entries}
        manifest = json.loads(source["manifest.json"])
        descriptor = manifest["snapshot"]["chart_accounts"]
        if problem.startswith("descriptor_"):
            field = problem.removeprefix("descriptor_")
            field = "sha256" if field == "hash" else field
            descriptor[field] = "a" * 64 if field == "sha256" else descriptor[field] + 1
        elif problem == "bad_contract":
            manifest["human_reviewed"] = True
        else:
            raw = source["chart-accounts.jsonl"]
            if problem == "truncated_line":
                raw = raw[:-1]
            elif problem == "crlf":
                raw = raw.replace(b"\n", b"\r\n")
            elif problem == "bom":
                raw = b"\xef\xbb\xbf" + raw
            elif problem == "duplicate_key":
                raw = raw.replace(b"{", b'{"account_code": 8,', 1)
            elif problem == "duplicate_account":
                raw += raw.splitlines(keepends=True)[0]
            else:
                rows = [json.loads(line) for line in raw.splitlines()]
                if problem == "wrong_owner":
                    rows[-1]["chart_company_code"] = 99999
                else:
                    rows[-1]["account_name_raw"] = "nul\0literal"
                raw = b"".join(encode(row) + b"\n" for row in rows)
            source["chart-accounts.jsonl"] = raw
            descriptor.update(
                bytes=len(raw), rows=raw.count(b"\n"), sha256=hashlib.sha256(raw).hexdigest()
            )
        source["manifest.json"] = encode(manifest)
        return [(name, raw) for name, raw in source.items()]

    package = rewrite_zip(path, mutate)
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()
    assert not ReconciliationDiscoveredChartAccount.objects.exists()
    assert not ReconciliationDiscoverySourceBlock.objects.exists()


def test_source_blocks_are_immutable_scoped_and_deep_integrity_checked(
    organization,
    sources,
    discovered_profile,
    tmp_path,
):
    other_organization = Organization.objects.create(name="Synthetic other", slug="synthetic-other")
    package = write_discovery_archive(with_sources(discovered_profile), tmp_path / "source.zip")
    run_archive(organization, sources, package, apply=True)
    batch = latest_consistent_discovery(organization)
    block = batch.source_blocks.first()
    for action in (
        lambda: block.save(),
        lambda: block.delete(),
        lambda: batch.source_blocks.update(row_count=1),
        lambda: batch.source_blocks.all().delete(),
    ):
        with pytest.raises(ValidationError):
            action()
    block.organization = other_organization
    with pytest.raises(ValidationError):
        block.clean()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE hub_reconciliationdiscoverysourceblock SET row_count=row_count+1 WHERE id=%s",
            [block.pk.hex if connection.vendor == "sqlite" else block.pk],
        )
    assert not _consistent_discovery(batch, deep=True)
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)


def test_stage_permissions_cleanup_and_decompression_bomb_are_bounded(
    sources,
    discovered_profile,
    tmp_path,
):
    package = write_discovery_archive(discovered_profile, tmp_path / "source.zip")
    with DiscoveryStage() as stage:
        directory = stage.directory
        stage.load(
            package["discovery_path"],
            expected_sha256=package["expected_sha256"],
            expected_size_bytes=package["expected_size_bytes"],
            companies={212, 213, 214},
            portfolio_sha256=hashlib.sha256(encode(sources[0])).hexdigest(),
        )
        assert stat.S_IMODE(os.stat(directory).st_mode) == 0o700
        assert all(stat.S_IMODE(os.stat(path).st_mode) == 0o600 for path in directory.iterdir())
        assert stage.database.execute("PRAGMA mmap_size").fetchone()[0] == 0
    assert not directory.exists()
    with pytest.raises(Invalid):
        decompress_block(zlib.compress(b"a" * (BLOCK_LIMIT * 2)), 10)
    with pytest.raises(Invalid):
        decompress_block(zlib.compress(b"a") + b"trailing", 1)


def test_archive_apply_failure_rolls_back_blocks_and_catalogue(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    monkeypatch,
):
    package = write_discovery_archive(with_sources(discovered_profile), tmp_path / "source.zip")

    def fail(**kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_discovery.record_event", fail)
    with pytest.raises(RuntimeError):
        run_archive(organization, sources, package, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()
    assert not ReconciliationDiscoveredChartAccount.objects.exists()
    assert not ReconciliationDiscoverySourceBlock.objects.exists()


def test_large_archive_stages_over_old_limit_with_fixed_io_and_cleanup(
    sources,
    discovered_profile,
    tmp_path,
):
    from itertools import chain

    profile = discovered_profile
    sample = profile["snapshot"]["chart_accounts"][-1]
    rows = chain(
        profile["snapshot"]["chart_accounts"],
        (dict(sample, account_code=1000 + n) for n in range(100_001)),
    )
    package = write_discovery_archive(profile, tmp_path / "large.zip", chart_rows=rows)

    class BoundedReader:
        def __init__(self, stream):
            self.stream = stream

        def read(self, size):
            assert 0 < size <= 1024 * 1024
            return self.stream.read(size)

    with package["discovery_path"].open("rb") as stream, DiscoveryStage() as stage:
        stage.load(
            BoundedReader(stream),
            expected_sha256=package["expected_sha256"],
            expected_size_bytes=package["expected_size_bytes"],
            companies={212, 213, 214},
            portfolio_sha256=hashlib.sha256(encode(sources[0])).hexdigest(),
        )
        assert stage.descriptors["chart_accounts"]["rows"] == 100_005
        assert sum(stage.chart_counts().values()) == 100_005
        assert sum(1 for _ in stage.chart_rows()) == 100_005
        assert isinstance(stage.data["snapshot"]["chart_accounts"], dict)
        assert stage.database.execute("PRAGMA cache_size").fetchone()[0] == -2048
    assert not stage.directory.exists()


def test_scope_is_revalidated_after_staging_and_before_any_write(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    monkeypatch,
):
    from apps.hub.models import ClientCompany

    package = write_discovery_archive(discovered_profile, tmp_path / "source.zip")
    load = DiscoveryStage.load

    def stage_then_change(self, *args, **kwargs):
        load(self, *args, **kwargs)
        ClientCompany.objects.filter(organization=organization, dominio_code="214").update(
            dominio_code="215"
        )

    monkeypatch.setattr(DiscoveryStage, "load", stage_then_change)
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()


def test_underreported_zip_member_cannot_silently_discard_trailing_source_rows(
    organization,
    sources,
    discovered_profile,
    tmp_path,
):
    path = tmp_path / "source.zip"
    package = write_discovery_archive(discovered_profile, path)
    # A ZIP can claim an empty member with the empty CRC while its DEFLATE stream
    # actually contains records. Python ZipExtFile otherwise clips that output.
    raw = bytearray(path.read_bytes())
    with zipfile.ZipFile(path) as archive:
        entry = archive.getinfo("chart-accounts.jsonl")
        central = archive.start_dir
    struct.pack_into("<L", raw, entry.header_offset + 14, 0)
    struct.pack_into("<L", raw, entry.header_offset + 22, 0)
    assert raw[central : central + 4] == b"PK\x01\x02"
    struct.pack_into("<L", raw, central + 16, 0)
    struct.pack_into("<L", raw, central + 24, 0)
    path.write_bytes(raw)
    package.update(expected_size_bytes=len(raw), expected_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()


def test_zip_command_path_never_reads_whole_source_and_insert_batch_is_bounded(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    monkeypatch,
):
    from itertools import chain
    from pathlib import Path

    from apps.hub.models import DiscoveryChartQuerySet

    sample = discovered_profile["snapshot"]["chart_accounts"][-1]
    rows = chain(
        discovered_profile["snapshot"]["chart_accounts"],
        (dict(sample, account_code=1000 + n) for n in range(1001)),
    )
    package = write_discovery_archive(discovered_profile, tmp_path / "source.zip", chart_rows=rows)
    original_insert = DiscoveryChartQuerySet.insert_validated
    batches = []

    def insert(self, objs, batch_size=500):
        assert len(objs) <= 250
        batches.append(len(objs))
        return original_insert(self, objs, batch_size=batch_size)

    def forbid_full_read(self):
        raise AssertionError("The source path must be streamed")

    monkeypatch.setattr(Path, "read_bytes", forbid_full_read)
    monkeypatch.setattr(DiscoveryChartQuerySet, "insert_validated", insert)
    run_archive(organization, sources, package, apply=True)
    assert batches == [250, 250, 250, 250, 5]


@pytest.mark.django_db(transaction=True)
def test_concurrent_archive_replay_has_one_atomic_set_of_all_four_models(
    organization,
    sources,
    discovered_profile,
    tmp_path,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    from apps.audit.models import AuditEvent

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks.")
    package = write_discovery_archive(with_sources(discovered_profile), tmp_path / "source.zip")
    barrier = Barrier(2)

    def apply():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return run_archive(organization, sources, package, apply=True)["created"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: apply(), range(2))) == [0, 1]
    batch = latest_consistent_discovery(organization)
    assert ReconciliationAccountDiscovery.objects.count() == 1
    assert batch.company_coverage.count() == 3
    assert batch.chart_accounts.count() == 4
    assert batch.source_blocks.count() >= 3
    assert _consistent_discovery(batch, deep=True)
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_discovery.imported").count()
        == 1
    )
