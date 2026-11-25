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
        from apps.hub.bank_evidence import read_sicredi_pdf
        from apps.hub.multisource.client_cashbook import read_client_cashbook_xlsx
        from apps.hub.multisource.francesinha import read_francesinha_pdf
        from apps.hub.multisource.investment import read_investment_pdf
        from apps.hub.multisource.ledger_comparison import (
            compare_with_ledger,
            movements_from_ledger_csv,
            movements_from_pdf,
        )
        from apps.hub.multisource.matching import BankLine, simulate
        from apps.hub.multisource.report import (
            render_differences_csv,
            render_documents_csv,
            render_ledger_csv,
            render_ledger_summary,
            render_lines_csv,
            render_position_csv,
            render_summary,
        )
        from apps.hub.multisource.scanned_documents import MAX_SCAN_BYTES, read_scanned_pdf
        from apps.hub.multisource.title_position import PAYABLE, RECEIVABLE, read_title_position_xls
        from apps.hub.reconciliation_service import ReconciliationError

        try:
            statement_bytes = _read(options["extrato"])
            assert statement_bytes is not None
            statement = read_sicredi_pdf(statement_bytes)
            if statement is None:
                raise CommandError("Extrato fora do leiaute Sicredi suportado.")
            bank_lines = [
                BankLine(i, line.occurred_on, line.amount_cents, line.description, line.document)
                for i, line in enumerate(statement.lines, 1)
            ]
            collection = None
            if content := _read(options["francesinha"]):
                collection = read_francesinha_pdf(content)
            positions = {}
            for option, kind in (
                ("receber", RECEIVABLE),
                ("pagar", PAYABLE),
                ("receber_referencia", RECEIVABLE),
                ("pagar_referencia", PAYABLE),
            ):
                if content := _read(options[option]):
                    position = read_title_position_xls(content)
                    if position.kind != kind:
                        raise CommandError(
                            f"--{option.replace('_', '-')}: o arquivo é da posição errada."
                        )
                    if options["cnpj"] and position.company_cnpj != options["cnpj"]:
                        raise CommandError(
                            f"--{option.replace('_', '-')}: CNPJ do relatório difere do informado."
                        )
                    positions[option] = position
            cashbook = None
            cash_accounts = []
            if content := _read(options["caixa"]):
                workbook = read_client_cashbook_xlsx(content)
                cashbook = workbook.sheet(options["aba"])
                cash_accounts = [workbook.sheet(name) for name in options["aba_sem_extrato"]]
            elif options["aba_sem_extrato"]:
                raise CommandError("--aba-sem-extrato exige --caixa.")
            if options["razao_pdf"] and options["razao_csv"]:
                raise CommandError("Informe o Razão em PDF ou em CSV, não os dois.")
            documents = []
            for path in options["documentos"]:
                content = _read(path, MAX_SCAN_BYTES)
                assert content is not None
                documents.extend(
                    read_scanned_pdf(content, source=path.name, own_tax_id=options["cnpj"] or "")
                )
            investment = None
            if content := _read(options["aplicacao"]):
                investment = read_investment_pdf(content)
            ledger_movements = None
            if content := _read(options["razao_pdf"]):
                from apps.hub.ledger_evidence import LedgerEvidenceError, read_dominio_ledger_pdf

                try:
                    ledger_movements = movements_from_pdf(read_dominio_ledger_pdf(content))
                except LedgerEvidenceError as exc:
                    raise MultisourceError(str(exc)) from exc
            if content := _read(options["razao_csv"]):
                ledger_movements = movements_from_ledger_csv(content)
        except (MultisourceError, ReconciliationError) as exc:
            raise CommandError(str(exc)) from exc

        result = simulate(
            bank_lines,
            collection=collection,
            receivables=positions.get("receber"),
            payables=positions.get("pagar"),
            cashbook=cashbook,
            reference_receivables=positions.get("receber_referencia"),
            reference_payables=positions.get("pagar_referencia"),
            cash_accounts=cash_accounts,
            investment=investment,
            documents=documents,
        )
        output: Path = options["saida"]
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        period = f"{statement.period_start:%m/%Y}"
        files = {
            "resumo.md": render_summary(result, title=f"Simulação multifontes — {period}"),
            "movimentos.csv": render_lines_csv(result),
            "posicao.csv": render_position_csv(result),
            "diferencas-posicao.csv": render_differences_csv(result),
        }
        if documents:
            files["documentos.csv"] = render_documents_csv(result)
        if ledger_movements is not None:
            comparison = compare_with_ledger(result, ledger_movements)
            files["resumo.md"] += render_ledger_summary(comparison)
            files["comparacao-razao.csv"] = render_ledger_csv(comparison)
        for name, text in files.items():
            target = output / name
            target.write_text(text, encoding="utf-8")
            target.chmod(0o600)
        self.stdout.write(
            f"{len(result.lines)} movimentos: {result.automatic_share:.1%} automático, "
            f"{result.identified_share:.1%} identificados. Relatórios em {output}"
        )
