"""Lista o que falta para vender, com a ação do responsável. Só leitura; sem segredo na saída.

manage.py product_readiness            # tabela
manage.py product_readiness --strict   # sai com 1 se algum item que bloqueia a venda falhar
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.platform.readiness import run_checks


class Command(BaseCommand):
    help = "Confere o ambiente contra o que a venda exige (só leitura)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--strict", action="store_true", help="falha se algo bloqueante faltar")

    def handle(self, *args: Any, **options: Any) -> None:
        checks = run_checks()
        for check in checks:
            state = "OK   " if check.ok else ("FALTA" if check.blocker else "AVISO")
            self.stdout.write(f"{state}  {check.label}: {check.detail}")
            if not check.ok:
                self.stdout.write(f"       ação: {check.action}")
        blockers = [check for check in checks if check.blocker and not check.ok]
        self.stdout.write(
            f"{len(checks) - len(blockers)} de {len(checks)} prontos; "
            f"{len(blockers)} bloqueiam a venda."
        )
        if options["strict"] and blockers:
            raise CommandError(f"{len(blockers)} item(ns) bloqueiam a venda.")
