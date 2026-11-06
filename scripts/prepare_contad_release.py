"""Package the local source snapshot for review; never contact or change a host."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT_FILES = {"Dockerfile", "fly.toml", "manage.py", "pyproject.toml", "uv.lock", "README.md"}
SOURCE_ROOTS = {"src", "runtime", "reporting", "deploy", "tests"}
RELEASE_SCRIPTS = {
    "scripts/prepare_contad_release.py",
    "scripts/preview_title_allocations.py",
    "scripts/compare_bank_ledger.py",
}
PROTECTED_SUFFIXES = {".pfx", ".pem", ".key", ".db", ".sqlite3", ".log"}


def prepare(root: Path, destination: Path) -> dict[str, object]:
    destination.mkdir(parents=True, exist_ok=True)
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required for the source inventory.")
    paths = (
        subprocess.check_output(  # noqa: S603 -- resolved Git, fixed read-only arguments.
            [git, "ls-files", "-c", "-o", "--exclude-standard", "-z"], cwd=root
        )
        .decode()
        .split("\0")
    )
    files = {}
    for name in sorted(set(paths) - {""}):
        path = Path(name)
        allowed = name in ROOT_FILES or path.parts[0] in SOURCE_ROOTS or name in RELEASE_SCRIPTS
        if not allowed:
            continue
        if "node_modules" in path.parts:
            # Dependencies are restored from lockfiles, not vendored in the archive.
            continue
        source = root / path
        if (
            source.is_symlink()
            or path.suffix.lower() in PROTECTED_SUFFIXES
            or any(part.startswith(".") or part == "__pycache__" for part in path.parts)
        ):
            raise ValueError(f"Unexpected protected file in source inventory: {name}")
        if source.is_file():
            files[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    archive = destination / "cica-contad-source.zip"
    if archive.exists():
        raise FileExistsError("Use a fresh output folder to preserve earlier release evidence.")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = ((root / name).stat().st_mode & 0o777) << 16
            bundle.writestr(info, (root / name).read_bytes())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None or any(
            hashlib.sha256(bundle.read(name)).hexdigest() != digest
            for name, digest in files.items()
        ):
            raise ValueError("Source changed during packaging; do not use this archive.")
    manifest: dict[str, object] = {
        "contract": "contad-source-review-v1",
        "base_commit": subprocess.check_output(  # noqa: S603 -- same fixed read-only invocation.
            [git, "rev-parse", "HEAD"], cwd=root
        )
        .decode()
        .strip(),
        "working_tree_snapshot": True,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": files,
        "migrations_to_preserve": [
            "hub.0076_accountingentry_account_reference_and_more",
            "hub.0077_independent_ledger_record",
            "hub.0078_accountingexportpreview",
            "intelligence.0031_agent_sync_scope",
        ],
        "agent_version": "1.0.3",
        "agent_msi_sha256": "5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253",
        "transport": "HTTPS + HMAC; explicit legacy mTLS remains supported",
        "published": False,
        "homologated": False,
        "released": False,
    }
    (destination / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(Path(__file__).resolve().parents[1], args.output.resolve())
    print(
        json.dumps(
            {
                "archive": result["archive"],
                "sha256": result["archive_sha256"],
                "published": False,
                "homologated": False,
            }
        )
    )
