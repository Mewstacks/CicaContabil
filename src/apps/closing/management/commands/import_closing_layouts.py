"""Importa layouts de leitura exportados do HubFedrizzi (``MapeamentoRecibo`` + ``CampoMapeado``).

É configuração, não dado de cliente: cada layout entra como RASCUNHO (``active=False``) com a
amostra do legado, para o escritório rever e ativar na tela. Idempotente: rodar de novo
substitui os campos do layout de mesmo código. Só toca o escritório informado.

Formato do JSON (gerado no HubFedrizzi, ver ``docs/fechamento-por-recibo.md``)::

    {"layouts": [{"sigla": "PGDAS", "nome": "PGDAS-D", "amostra_texto": "...",
                  "campos": [{"variavel": "MARCADOR", "localizador": "...",
                              "ocorrencia": 0, "somar": 0, "anulado": false}]}]}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.closing.models import ClosingField, ClosingLayout, Variable
from apps.hub.models import FiscalGuide
from apps.organizations.models import Organization

VARIABLES = {
    "MARCADOR": Variable.MARKER,
    "CNPJ": Variable.CNPJ,
    "CNPJ_RAIZ": Variable.CNPJ_ROOT,
    "INSCRICAO_ESTADUAL": Variable.STATE_REGISTRATION,
    "INSCRICAO_MUNICIPAL": Variable.MUNICIPAL_REGISTRATION,
    "COMPETENCIA": Variable.COMPETENCE,
    "VALOR_PRINCIPAL": Variable.AMOUNT,
    "ICMS": Variable.ICMS,
    "IPI": Variable.IPI,
    "ISSQN": Variable.ISS,
    "ISSQN_RETIDO": Variable.ISS_WITHHELD,
    "NUM_RECIBO": Variable.NUMBER,
    "RAZAO_SOCIAL": Variable.LEGAL_NAME,
}

#: Conferência que o legado fazia por sigla: Serpro (guia da Central) ou cruzamento de documentos.
HINTS: dict[str, dict[str, Any]] = {
    "PGDAS": {"compare": "fiscal_guide", "guide_kind": FiscalGuide.Kind.DAS},
    "DAS": {"compare": "fiscal_guide", "guide_kind": FiscalGuide.Kind.DAS},
    "DCTFWEB": {"compare": "fiscal_guide", "guide_kind": FiscalGuide.Kind.DCTFWEB},
    "EFD-ICMS-IPI": {"compare": "paired", "paired": "icms", "value_source": "icms"},
    "ISSQN-PROPRIO": {"compare": "paired", "paired": "dms", "value_source": "iss"},
}
GUIDE_SIGLAS = {"ICMS", "DMS"}


def legacy_variable(name: str) -> str | None:
    if name.startswith("MARCADOR_"):
        suffix = name.removeprefix("MARCADOR_")
        return f"marker_{suffix}" if suffix.isdigit() else None
    mapped = VARIABLES.get(name)
    return str(mapped) if mapped else None


class Command(BaseCommand):
    help = "Importa layouts do HubFedrizzi como rascunho num escritório."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--office", required=True, help="Slug do escritório.")
        parser.add_argument("--file", required=True, help="JSON exportado do legado.")
        parser.add_argument("--no-hints", action="store_true", help="Não sugerir a conferência.")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args: object, **options: Any) -> None:
        office = Organization.objects.filter(slug=options["office"]).first()
        if office is None:
            raise CommandError("Escritório não encontrado.")
        path = Path(str(options["file"]))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Não consegui ler {path}: {exc}") from exc
        items = payload.get("layouts") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise CommandError('O arquivo precisa ter a chave "layouts" com uma lista.')
        made: dict[str, ClosingLayout] = {}
        skipped: list[str] = []
        for item in items:
            sigla = str(item.get("sigla", "")).strip()
            code = slugify(sigla)[:64]
            if not code:
                skipped.append("(sem sigla)")
                continue
            hint = {} if options["no_hints"] else dict(HINTS.get(sigla.upper(), {}))
            hint.pop("paired", None)
            layout, _ = ClosingLayout.objects.update_or_create(
                organization=office,
                code=code,
                defaults={
                    "label": str(item.get("nome") or sigla)[:160],
                    "kind": (
                        ClosingLayout.Kind.GUIDE
                        if sigla.upper() in GUIDE_SIGLAS
                        else ClosingLayout.Kind.RECEIPT
                    ),
                    "sample_text": str(item.get("amostra_texto", ""))[:60000],
                    "active": False,
                    **hint,
                },
            )
            layout.fields.all().delete()
            for position, campo in enumerate(item.get("campos", [])):
                variable = legacy_variable(str(campo.get("variavel", "")))
                if variable is None or campo.get("custom"):
                    continue
                ClosingField.objects.create(
                    organization=office,
                    layout=layout,
                    variable=variable,
                    anchor=str(campo.get("localizador", ""))[:255],
                    occurrence=int(campo.get("ocorrencia") or 0),
                    sum_count=int(campo.get("somar") or 0),
                    nullified=bool(campo.get("anulado")),
                    position=position,
                )
            made[sigla.upper()] = layout
        if not options["no_hints"]:
            for sigla, hint in HINTS.items():
                hinted = made.get(sigla)
                wanted = hint.get("paired")
                if hinted is None or not wanted:
                    continue
                partner = ClosingLayout.objects.filter(organization=office, code=wanted).first()
                if partner is not None:
                    hinted.paired_layout = partner
                    hinted.save(update_fields=["paired_layout", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(made)} layouts em rascunho em {office.name}"
                + (f"; ignorados: {', '.join(skipped)}" if skipped else "")
            )
        )
        if options["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write("dry-run: nada gravado.")
