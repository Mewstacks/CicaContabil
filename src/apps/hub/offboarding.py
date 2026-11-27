"""Exportação dos dados de um escritório (E4, LGPD art. 18, portabilidade e fim de contrato).

O pacote é um ZIP com um arquivo JSON por linha para cada modelo de negócio do app `hub`, a equipe
e um `manifest.json` que diz o que foi contado e o que ficou de fora e por quê. É só leitura: não
altera nada. Segredo nunca sai: todo campo cujo nome indica credencial, chave, hash ou digest é
cortado (`SECRET_FIELD`), e modelos de segurança ou de estado interno ficam fora (`HUB_EXCLUDED`).
Arquivos binários em armazenamento de objeto (PDF, anexos) não vão no pacote; os registros dizem o
caminho e o armazenamento é exportado à parte.

Tudo o que tem FK `organization` e é do `hub` precisa estar em `exported_models()` ou em
`HUB_EXCLUDED`: um modelo novo sem decisão derruba `tests/test_office_export.py`. Outros apps
(`profitability`, `crosscheck`, `triage`, `intelligence`, `platform`, `audit`) entram em
`OTHER_APPS` com o motivo: dado derivado, de terceiro ou trilha que a Mewstack retém.

A EXCLUSÃO do escritório não é executada por código aqui (Q-49): `hub.NfseDocument` e o restante
da evidência fiscal são imutáveis por desenho e a retenção legal precisa de decisão do responsável
e da revisão jurídica antes de qualquer comando que apague.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core import serializers
from django.db.models import Model
from django.utils import timezone

from apps.audit.services import record_event
from apps.organizations.models import Membership, Organization

FORMAT = "cica-export-1"
SECRET_FIELD = re.compile(
    r"(password|secret|private_key|pfx|credential|lease_token|api_key|backup_key"
    r"|encrypted_configuration|odbc_dsn|_hash$|_digest$|_sha256$|^token$)",
    re.IGNORECASE,
)
HUB_EXCLUDED = {
    "ControlPlaneBinding": "credencial do controle central da Mewstack",
    "RemoteSupportGrant": "concessão de suporte remoto (segurança)",
    "Connector": "configuração cifrada de conector externo",
    "NfseSync": "estado interno da fila de coleta (lease, recuo)",
    "ImportBatch": "arquivo e carga de importação (dado bruto descartado após o processamento)",
}
OTHER_APPS = {
    "profitability": "dado derivado de horas e honorários; exportação sob pedido",
    "delivery": "histórico de e-mails ao cliente e anexos; exportação sob pedido",
    "crosscheck": "conferência derivada dos arquivos do cliente; exportação sob pedido",
    "det": "consultas do DET e lista de mensagens lidas pelo agente; exportação sob pedido",
    "admissions": "fichas de admissão (dado pessoal cifrado, apagado em 90 dias); sem exportação",
    "fap": "lotes, consultas e PDFs do FAP; exportação sob pedido",
    "fgts": "apuração, lotes e guias do FGTS Digital; exportação sob pedido",
    "folha": "ciclos, relatórios, envios e marcações da folha; exportação sob pedido",
    "rpa": "fila de trabalhos do agente Windows e arquivos entregues; exportação sob pedido",
    "closing": "recibos, guias lidas e conferências do fechamento; exportação sob pedido",
    "triage": "metadados de caixa de entrada e anexos em armazenamento; exportação sob pedido",
    "intelligence": "espelho, conversas e conhecimento derivados; exportação sob pedido",
    "platform": "contrato, fatura, convite e cobrança: a Mewstack retém (registro contábil)",
    "audit": "trilha de auditoria: a Mewstack retém",
}


@dataclass
class ModelReport:
    rows: int = 0
    excluded_fields: list[str] = field(default_factory=list)


@dataclass
class ExportResult:
    path: Path | None
    sha256: str
    models: dict[str, ModelReport]
    team_rows: int

    @property
    def total_rows(self) -> int:
        return sum(report.rows for report in self.models.values()) + self.team_rows


def _is_exportable(model: type[Model]) -> bool:
    if model._meta.app_label != "hub" or model._meta.abstract or model._meta.proxy:
        return False
    if model.__name__ in HUB_EXCLUDED:
        return False
    return any(
        getattr(f, "name", "") == "organization" and f.is_relation for f in model._meta.get_fields()
    )


def exported_models() -> list[type[Model]]:
    return sorted(
        (model for model in apps.get_models() if _is_exportable(model)),
        key=lambda model: model._meta.label,
    )


def hub_models_with_organization() -> list[type[Model]]:
    """Every `hub` model that belongs to an office; each must be exported or excluded."""

    return [
        model
        for model in apps.get_models()
        if model._meta.app_label == "hub"
        and not model._meta.abstract
        and not model._meta.proxy
        and any(
            getattr(f, "name", "") == "organization" and f.is_relation
            for f in model._meta.get_fields()
        )
    ]


def exported_fields(model: type[Model]) -> tuple[list[str], list[str]]:
    """(campos exportados, campos cortados por parecerem segredo)."""

    kept: list[str] = []
    cut: list[str] = []
    for model_field in model._meta.get_fields():
        if not getattr(model_field, "concrete", False) or model_field.name == "id":
            continue
        (cut if SECRET_FIELD.search(model_field.name) else kept).append(model_field.name)
    return kept, cut


def _write_model(
    archive: zipfile.ZipFile, model: type[Model], organization: Organization
) -> ModelReport:
    kept, cut = exported_fields(model)
    queryset = model._default_manager.filter(organization=organization).order_by("pk")
    report = ModelReport(excluded_fields=cut)
    with archive.open(f"{model._meta.label}.jsonl", "w") as raw:
        stream = io.TextIOWrapper(raw, encoding="utf-8", newline="\n")
        for row in queryset.iterator(chunk_size=500):
            serializers.serialize("jsonl", [row], fields=kept, stream=stream)
            report.rows += 1
        stream.flush()
        stream.detach()
    return report


def _write_team(archive: zipfile.ZipFile, organization: Organization) -> int:
    rows = 0
    members = Membership.objects.filter(organization=organization).select_related("user")
    with archive.open("team.jsonl", "w") as raw:
        for member in members.order_by("created_at"):
            line = {
                "email": member.user.email,
                "name": member.user.full_name,
                "role": member.role,
                "active": member.is_active,
                "since": member.created_at.isoformat(),
            }
            raw.write((json.dumps(line, ensure_ascii=False) + "\n").encode("utf-8"))
            rows += 1
    return rows


def export_office(
    organization: Organization, destination: Path | None, *, now: datetime | None = None
) -> ExportResult:
    """Write the package to `destination`; with `None` only count (dry run)."""

    now = now or timezone.now()
    models = exported_models()
    reports: dict[str, ModelReport] = {}
    buffer: Any = destination.open("wb") if destination is not None else io.BytesIO()
    team_rows = 0
    try:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for model in models:
                reports[model._meta.label] = _write_model(archive, model, organization)
            team_rows = _write_team(archive, organization)
            manifest = {
                "format": FORMAT,
                "organization": organization.slug,
                "generated_at": now.isoformat(),
                "models": {
                    label: {"rows": report.rows, "excluded_fields": report.excluded_fields}
                    for label, report in reports.items()
                },
                "team_rows": team_rows,
                "not_included": {
                    **{f"hub.{name}": reason for name, reason in HUB_EXCLUDED.items()},
                    **OTHER_APPS,
                    "arquivos": "PDF, anexos e demais binários ficam no armazenamento de objeto",
                },
            }
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    finally:
        buffer.close()
    digest = ""
    if destination is not None:
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    result = ExportResult(path=destination, sha256=digest, models=reports, team_rows=team_rows)
    record_event(
        action="hub.office.exported",
        organization=organization,
        target=organization,
        metadata={"rows": result.total_rows, "dry_run": destination is None},
    )
    return result
