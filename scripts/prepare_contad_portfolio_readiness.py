"""Prepare a private coverage worklist offline, without Django or ERP/database access."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.ledger_evidence import write_evidence_report
from apps.hub.portfolio_evidence import MAX_TRANSFER_BYTES
from apps.hub.portfolio_readiness import prepare_portfolio_readiness


def _read(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read(MAX_TRANSFER_BYTES + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-input", type=Path, required=True)
    parser.add_argument("--accounts-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare_portfolio_readiness(
            _read(args.portfolio_input), _read(args.accounts_input)
        )
        write_evidence_report(args.output, report)
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    except (CatalogEvidenceError, OSError):
        print(
            "Matriz não gerada; confira os perfis originais, o recorte e um destino privado novo.",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "summary": report["summary"],
                "report_sha256": digest,
                "financial_collection_enabled": False,
                "human_reviewed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
