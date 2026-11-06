"""Offline comparison of supplied OFX, Sicredi PDF and Domínio account-report PDF."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from apps.hub.ledger_evidence import (
    MAX_SOURCE_BYTES,
    LedgerEvidenceError,
    compare_ledger_files,
    write_evidence_report,
)


def _read_source(path: Path) -> bytes:
    with path.open("rb") as source:
        content = source.read(MAX_SOURCE_BYTES + 1)
    if not content or len(content) > MAX_SOURCE_BYTES:
        raise LedgerEvidenceError("Fonte vazia ou maior que 25 MiB.")
    return content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ofx", type=Path, required=True)
    parser.add_argument("--bank-pdf", type=Path, required=True)
    parser.add_argument("--ledger-pdf", type=Path, required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--ledger-code", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare_ledger_files(
            ofx=_read_source(args.ofx),
            bank_pdf=_read_source(args.bank_pdf),
            ledger_pdf=_read_source(args.ledger_pdf),
            company_name=args.company_name,
            ledger_code=args.ledger_code,
        )
        write_evidence_report(args.output, report)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Conferência recusada: {exc}\n")
    print("Conferência local gravada; nenhuma conciliação confirmada ou enviada.")
    return 0


if __name__ == "__main__":
    # Existing bank readers import Django models. Boot with isolated settings;
    # this command never opens a database, contacts a provider or loads .env.
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    os.environ["TEST_USE_EXTERNAL_SERVICES"] = "false"
    import django

    django.setup()
    raise SystemExit(main())
