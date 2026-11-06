"""Run the same private account-report comparison inside the deployed runtime."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.ledger_evidence import (
    MAX_SOURCE_BYTES,
    LedgerEvidenceError,
    compare_ledger_files,
    write_evidence_report,
)


class Command(BaseCommand):
    help = "Conferir OFX, PDF Sicredi e Razão PDF localmente, sem importar ou conciliar."
    requires_system_checks: list[str] = []
    requires_migrations_checks = False

    def add_arguments(self, parser: CommandParser) -> None:
        for name in ("ofx", "bank-pdf", "ledger-pdf", "output"):
            parser.add_argument(f"--{name}", type=Path, required=True)
        parser.add_argument("--company-name", required=True)
        parser.add_argument("--ledger-code", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            sources = {}
            for name in ("ofx", "bank_pdf", "ledger_pdf"):
                with Path(options[name]).open("rb") as source:
                    sources[name] = source.read(MAX_SOURCE_BYTES + 1)
                if not sources[name] or len(sources[name]) > MAX_SOURCE_BYTES:
                    raise LedgerEvidenceError("Fonte vazia ou maior que 25 MiB.")
            report = compare_ledger_files(
                **sources,
                company_name=options["company_name"],
                ledger_code=options["ledger_code"],
            )
            write_evidence_report(Path(options["output"]), report)
        except (OSError, ValueError) as exc:
            raise CommandError(f"Conferência recusada: {exc}") from exc
        self.stdout.write("Conferência privada gravada; nenhuma conciliação confirmada ou enviada.")
