"""Synthetic v2 packages; large callers supply generators rather than resident lists."""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from apps.hub import account_discovery_contract as contract
from apps.hub.account_discovery_archive import TABLES


def write_discovery_archive(
    profile: dict[str, Any],
    path: Path,
    *,
    chart_rows: Iterable[dict[str, Any]] | None = None,
    template_rows: Iterable[dict[str, Any]] | None = None,
    nature_rows: Iterable[dict[str, Any]] | None = None,
    script_sha256: str | None = None,
) -> dict[str, Any]:
    manifest = {
        **profile,
        "version": contract.ARCHIVE_VERSION,
        "script_sha256": script_sha256 or contract.ARCHIVE_SCRIPT_SHA,
        "snapshot": {key: value for key, value in profile["snapshot"].items() if key not in TABLES},
    }
    overrides = dict(
        chart_accounts=chart_rows, plan_template_accounts=template_rows, nature_rules=nature_rows
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for table, (filename, _, _) in TABLES.items():
            rows = overrides[table]
            if rows is None:
                rows = profile["snapshot"][table]
            checksum, count, size = hashlib.sha256(), 0, 0
            with archive.open(filename, "w") as output:
                for row in rows:
                    raw = (
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                    ).encode()
                    output.write(raw)
                    checksum.update(raw)
                    count, size = count + 1, size + len(raw)
            manifest["snapshot"][table] = dict(
                file=filename, rows=count, bytes=size, sha256=checksum.hexdigest()
            )
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False).encode())
    checksum, size = hashlib.sha256(), 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return {
        "discovery_path": path,
        "expected_sha256": checksum.hexdigest(),
        "expected_size_bytes": size,
    }
