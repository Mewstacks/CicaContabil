"""Private offline preview for reviewed normalized inputs; never import or post to ERP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from apps.hub.title_allocation import preview_title_allocations
from apps.hub.title_contract import TitleContractError, _day

MAX_SOURCE_BYTES = 25 * 1024 * 1024


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise TitleContractError("JSON contém campo repetido; nenhuma prévia foi gravada.")
        result[key] = value
    return result


def _read_json(path: Path) -> tuple[Any, str]:
    with path.open("rb") as source:
        content = source.read(MAX_SOURCE_BYTES + 1)
    if len(content) > MAX_SOURCE_BYTES:
        raise TitleContractError("Fonte JSON excede o limite de 25 MiB.")
    try:
        payload = json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TitleContractError("Fonte JSON inválida; nenhuma prévia foi gravada.") from exc
    return payload, hashlib.sha256(content).hexdigest()


def _json_date(value: Any) -> str:
    if type(value) is date:
        return value.isoformat()
    raise TypeError("Tipo não serializável no relatório de prévia.")


def _write_private_report(path: Path, report: dict[str, Any]) -> None:
    content = (
        json.dumps(report, default=_json_date, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    # Link only a fully written temporary file. Existing files and symlinks are
    # never replaced; a failed write cannot expose a partly written final report.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".cica-preview-", delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.link(temp_path, path, follow_symlinks=False)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--allocations", type=Path, required=True)
    parser.add_argument("--company-key", required=True)
    parser.add_argument("--account-reference", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        titles, titles_hash = _read_json(args.titles)
        bank, bank_hash = _read_json(args.bank)
        allocations, allocations_hash = _read_json(args.allocations)
        preview = preview_title_allocations(
            titles,
            bank,
            allocations,
            company_key=args.company_key,
            account_reference=args.account_reference,
            period_start=_day(args.start),
            period_end=_day(args.end),
        )
        _write_private_report(
            args.output,
            {
                "contract": "title-allocation-preview-report-v1",
                "status": "requires_review",
                "persisted_allocations": False,
                "erp_written": False,
                "source_sha256": {
                    "titles": titles_hash,
                    "bank": bank_hash,
                    "allocations": allocations_hash,
                },
                "preview": asdict(preview),
            },
        )
    except (OSError, TitleContractError) as exc:
        parser.exit(2, f"Prévia recusada: {exc}\n")
    print("Prévia local gravada para revisão; nenhuma alocação persistida ou enviada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
