"""Tipos de trabalho RPA da Folha (registrados em ``FolhaConfig.ready``)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import ClientCompany, ProductModule
from apps.rpa import registry
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError, RpaKind

from . import recipients
from .models import FolhaContact

KIND_REPORT = "folha.relatorio"
KIND_CONTACTS = "folha.contatos"
#: Uma só sessão do Domínio desktop por escritório: folha, admissões e FGTS não rodam juntos.
DESKTOP_GROUP = "dominio_desktop"


def _validate_report_payload(payload: dict[str, Any]) -> None:
    for key in ("task_id", "company_code", "item", "competence", "title"):
        if not str(payload.get(key) or "").strip():
            raise RpaError("validacao", f"Carga sem {key}.")


def _validate_report_result(result: dict[str, Any]) -> None:
    from .services import validate_report_result

    validate_report_result(result)


def _on_report_success(job: RpaJob) -> None:
    from .services import on_report_success

    on_report_success(job)


def _on_report_failure(job: RpaJob) -> None:
    from .services import on_report_failure

    on_report_failure(job)


def _validate_contacts_result(result: dict[str, Any]) -> None:
    rows = result.get("contacts")
    if not isinstance(rows, list) or len(rows) > 5000:
        raise RpaError("validacao", "Lista de contatos inválida.")
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("company_code") or "").strip():
            raise RpaError("validacao", "Contato sem empresa.")


def _on_contacts_success(job: RpaJob) -> None:
    """Troca os contatos das empresas pedidas pelo que o Domínio devolveu agora."""

    wanted = {str(c) for c in job.payload.get("company_codes", [])}
    rows = [r for r in job.result.get("contacts", []) if str(r["company_code"]) in wanted]
    companies = {
        c.dominio_code: c
        for c in ClientCompany.objects.filter(
            organization=job.organization, dominio_code__in=wanted
        )
    }
    FolhaContact.objects.filter(
        organization=job.organization, company__in=companies.values()
    ).delete()
    FolhaContact.objects.bulk_create(
        [
            FolhaContact(
                organization=job.organization,
                company=companies[str(row["company_code"])],
                emails=recipients.extract_emails(" ".join(map(str, row.get("emails", [])))),
                note=str(row.get("note", ""))[:300],
            )
            for row in rows
            if str(row["company_code"]) in companies
        ]
    )


registry.register(
    RpaKind(
        code=KIND_REPORT,
        module_code=ProductModule.Code.FOLHA,
        label="Relatório da folha no Domínio",
        exclusive_group=DESKTOP_GROUP,
        lease_seconds=600,
        max_attempts=3,
        validate_payload=_validate_report_payload,
        validate_result=_validate_report_result,
        on_success=_on_report_success,
        on_failure=_on_report_failure,
        result_keys=frozenset({"status", "validation", "sha256", "size", "output_name", "error"}),
    )
)
registry.register(
    RpaKind(
        code=KIND_CONTACTS,
        module_code=ProductModule.Code.FOLHA,
        label="Contatos das empresas no Domínio (leitura)",
        lease_seconds=300,
        max_attempts=2,
        validate_result=_validate_contacts_result,
        on_success=_on_contacts_success,
        result_keys=frozenset({"contacts"}),
    )
)
