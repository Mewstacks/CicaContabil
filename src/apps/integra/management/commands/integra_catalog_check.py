from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.integra.catalog_check import (
    CATALOG_URL,
    CatalogDiff,
    compare_catalog,
    fetch_catalog_html,
    parse_catalog_html,
    parse_service_pages,
    render_report,
)


class Command(BaseCommand):
    help = (
        "Compara o registro do Integra Contador com a página oficial do catálogo de serviços "
        "e acusa serviço novo. Sem --file, baixa a página (única chamada de rede deste módulo)."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--file",
            help="HTML salvo da página do catálogo; compara offline, sem rede.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Termina com erro quando o registro diverge do catálogo.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["file"]:
            html = Path(options["file"]).read_text(encoding="utf-8")
        else:
            self.stdout.write(f"Lendo {CATALOG_URL}")
            html = fetch_catalog_html(CATALOG_URL)
        try:
            official = parse_catalog_html(html)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        diff = compare_catalog(official, service_pages=parse_service_pages(html))

        self.stdout.write(render_report(diff))
        if options["strict"] and not diff.clean:
            raise CommandError(f"Registro diverge do catálogo oficial: {_summary(diff)}.")


def _summary(diff: CatalogDiff) -> str:
    parts = [f"novo {row.label}" for row in diff.new_in_production]
    parts += [f"saiu {spec.id_sistema}/{spec.id_servico}" for spec, _ in diff.left_production]
    parts += [f"tipo {row.label}" for _, row in diff.verb_changed]
    return "; ".join(parts)
