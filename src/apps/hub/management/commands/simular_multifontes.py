"""Simular a conciliação multifontes de um mês (D-409, PC-33), sem gravar nada no banco.

Exemplo:
    manage.py simular_multifontes --extrato extrato.pdf --francesinha francesinha.pdf \\
        --receber CR-09.xls --pagar CP-09.xls --caixa caixa.xlsx --aba SICREDI \\
        --receber-referencia CR-10.xls --pagar-referencia CP-10.xls --saida /pasta/privada
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.hub.multisource.common import MAX_SOURCE_BYTES, MultisourceError


def _read(path: Path | None, limit: int = MAX_SOURCE_BYTES) -> bytes | None:
    if path is None:
        return None
    if not path.is_file():
        raise CommandError(f"Arquivo não encontrado: {path}")
    if path.stat().st_size > limit:
        raise CommandError(f"Arquivo maior que {limit // (1024 * 1024)} MiB: {path.name}")
    return path.read_bytes()


class Command(BaseCommand):
    help = "Simular a conciliação multifontes (extrato, francesinha, posição, caixa) sem gravar."
    requires_system_checks: list[str] = []
    requires_migrations_checks = False

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--extrato", type=Path, required=True, help="Extrato Sicredi em PDF.")
        parser.add_argument("--francesinha", type=Path, help="Francesinha Sicredi em PDF.")
        parser.add_argument(
            "--receber", type=Path, help="Posição a receber do mês anterior (.xls)."
        )
        parser.add_argument("--pagar", type=Path, help="Posição a pagar do mês anterior (.xls).")
        parser.add_argument("--caixa", type=Path, help="Caixa do cliente (.xlsx).")
        parser.add_argument(
            "--aba", default="SICREDI", help="Aba do caixa que corresponde ao extrato."
        )
        parser.add_argument(
            "--documentos",
            type=Path,
            action="append",
            default=[],
            help="PDF escaneado com boletos, recibos, DANFE ou CT-e (OCR local); pode repetir.",
        )
        parser.add_argument("--aplicacao", type=Path, help="Extrato de aplicação Sicredi (PDF).")
        parser.add_argument(
            "--razao-pdf", type=Path, help="Razão da conta bancária (PDF do Domínio)."
        )
        parser.add_argument(
            "--razao-csv", type=Path, help="Razão da conta bancária no contrato ledger-csv-v1."
        )
        parser.add_argument(
            "--aba-sem-extrato",
            action="append",
            default=[],
            help="Aba do caixa sem extrato (ex.: CAIXA em dinheiro); pode repetir.",
        )
        parser.add_argument(
            "--receber-referencia", type=Path, help="Posição a receber do mês (.xls)."
        )
        parser.add_argument("--pagar-referencia", type=Path, help="Posição a pagar do mês (.xls).")
        parser.add_argument(
            "--cnpj", help="CNPJ esperado da empresa (14 dígitos), conferido nas posições."
        )
        parser.add_argument(
            "--saida", type=Path, required=True, help="Pasta privada para os relatórios."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.hub.multisource.scanned_documents import MAX_SCAN_BYTES
        from apps.hub.multisource.service import SimulationSources, run_simulation

        statement = _read(options["extrato"])
        assert statement is not None
        if options["razao_pdf"] and options["razao_csv"]:
            raise CommandError("Informe o Razão em PDF ou em CSV, não os dois.")
        if options["aba_sem_extrato"] and not options["caixa"]:
            raise CommandError("--aba-sem-extrato exige --caixa.")
        documents = []
        for path in options["documentos"]:
            content = _read(path, MAX_SCAN_BYTES)
            assert content is not None
            documents.append((path.name, content))
        sources = SimulationSources(
            statement=statement,
            collection=_read(options["francesinha"]),
            receivables=_read(options["receber"]),
            payables=_read(options["pagar"]),
            cashbook=_read(options["caixa"]),
            cashbook_sheet=options["aba"],
            cash_sheets=options["aba_sem_extrato"],
            reference_receivables=_read(options["receber_referencia"]),
            reference_payables=_read(options["pagar_referencia"]),
            investment=_read(options["aplicacao"]),
            ledger_pdf=_read(options["razao_pdf"]),
            ledger_csv=_read(options["razao_csv"]),
            documents=documents,
            tax_id=options["cnpj"] or "",
        )
        try:
            output = run_simulation(sources)
        except MultisourceError as exc:
            raise CommandError(str(exc)) from exc
        target_dir: Path = options["saida"]
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, text in output.reports.items():
            target = target_dir / name
            target.write_text(text, encoding="utf-8")
            target.chmod(0o600)
        result = output.result
        self.stdout.write(
            f"{len(result.lines)} movimentos: {result.automatic_share:.1%} automático, "
            f"{result.identified_share:.1%} identificados. Relatórios em {target_dir}"
        )
