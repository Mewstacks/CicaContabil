"""Read metadata locally without starting Django or contacting the ERP/backend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apps.hub.contad_relations import CatalogEvidenceError, analyze_catalog, read_metadata_json
from apps.hub.ledger_evidence import write_evidence_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--focus-table",
        action="append",
        default=[],
        help="Objeto bethadba a destacar nos metadados recebidos (repetível, até 12).",
    )
    args = parser.parse_args(argv)
    try:
        report = analyze_catalog(
            read_metadata_json(args.catalog, max_bytes=2 * 1024 * 1024),
            read_metadata_json(args.inventory, max_bytes=4 * 1024 * 1024),
            focus_tables=tuple(args.focus_table),
        )
        write_evidence_report(args.output, report)
    except (CatalogEvidenceError, OSError):
        print(
            "Análise não concluída; confira contrato, limites e destino local novo.",
            file=sys.stderr,
        )
        return 1
    print("Catálogo consistente; relatório privado criado. Sem habilitar coleta financeira.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
