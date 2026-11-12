"""Analyze the received fiscal title-family metadata offline, without Django/ERP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.ledger_evidence import write_evidence_report
from apps.hub.title_catalog import MAX_BYTES, analyze_title_catalog, decode_title_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        report = analyze_title_catalog(decode_title_catalog(raw))
        write_evidence_report(args.output, report)
    except (CatalogEvidenceError, OSError):
        print(
            "Complemento não validado; confira contrato, hash e destino privado novo.",
            file=sys.stderr,
        )
        return 1
    print("Metadados fiscais conferidos; sem habilitar fonte de títulos ou executar baixas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
