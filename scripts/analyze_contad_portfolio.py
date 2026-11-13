"""Validate private active-company coverage without Django, ERP access or writes to production."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.ledger_evidence import write_evidence_report
from apps.hub.portfolio_evidence import (
    MAX_TRANSFER_BYTES,
    analyze_portfolio_profile,
    decode_portfolio_profile,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_TRANSFER_BYTES + 1)
        report = analyze_portfolio_profile(decode_portfolio_profile(raw))
        write_evidence_report(
            args.output, {**report, "input_file_sha256": hashlib.sha256(raw).hexdigest()}
        )
    except (CatalogEvidenceError, OSError):
        print(
            "Cobertura não validada; confira contrato, hash e destino privado novo.",
            file=sys.stderr,
        )
        return 1
    print("Cobertura técnica conferida; nenhuma conta, coleta financeira ou revisão humana criada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
