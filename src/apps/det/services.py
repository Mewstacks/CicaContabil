"""Regras do DET: seleção autorizada, pedaços, resultado conferido e planilha."""

from __future__ import annotations

import io
import re
from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

from .models import DetChunk, DetQuery, DetResult

KIND = "det.consultar"
MAX_COMPANIES = 2000
CHUNK = 10
MAX_MESSAGES = 10_000
MAX_TEXT = 2000
MESSAGE_KEYS = ("type", "sender", "sent_at", "title")
SITUATIONS = {c for c, _ in DetResult.Situation.choices}
_CNPJ = re.compile(r"^\d{14}$")
_FORMULA = re.compile(r"^[=+\-@\t\r]")


class DetError(Exception):
    """Regra do DET recusou a operação; a mensagem é segura para a tela."""


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def create_query(
    *, organization: Organization, user: User, companies: list[ClientCompany]
) -> DetQuery:
    """Só empresa ativa do escritório com CNPJ de 14 dígitos; a seleção fica congelada."""

    if not companies or len(companies) > MAX_COMPANIES:
        raise DetError(f"Escolha de 1 a {MAX_COMPANIES} empresas.")
    snapshot: list[dict[str, str]] = []
    seen: set[str] = set()
    for company in companies:
        cnpj = _digits(company.cnpj_masked)
        if company.organization_id != organization.pk or not company.active:
            raise DetError("Há empresa fora do escritório ou inativa.")
        if not _CNPJ.match(cnpj) or not company.dominio_code:
            raise DetError(f"{company.name}: falta código do Domínio ou CNPJ de 14 dígitos.")
        if company.dominio_code in seen:
            continue
        seen.add(company.dominio_code)
        snapshot.append({"code": company.dominio_code, "name": company.name[:255], "cnpj": cnpj})
    with transaction.atomic():
        query = DetQuery.objects.create(
            organization=organization, companies=snapshot, created_by=user
        )
        for position, start in enumerate(range(0, len(snapshot), CHUNK)):
            piece = snapshot[start : start + CHUNK]
            job, _ = rpa.enqueue(
                organization=organization,
                kind=KIND,
                idempotency_key=f"q:{query.pk}:{position}",
                payload={"query_id": str(query.pk), "companies": piece, "list_only": True},
            )
            DetChunk.objects.create(
                organization=organization, query=query, position=position, job=job
            )
        record_event(
            action="det.query.created",
            organization=organization,
            target=query,
            metadata={"companies": len(snapshot), "user": str(user.pk)},
        )
    return query


def validate_payload(payload: dict[str, Any]) -> None:
    companies = payload.get("companies")
    if not isinstance(companies, list) or not companies or len(companies) > CHUNK:
        raise RpaError("validacao", "Lista de empresas inválida.")
    if payload.get("list_only") is not True:
        raise RpaError("validacao", "A consulta do DET só pode ler a lista.")
    if not payload.get("query_id"):
        raise RpaError("validacao", "Carga sem query_id.")


def _clean_message(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise RpaError("validacao", "Mensagem inválida.")
    out: dict[str, str] = {}
    for key in MESSAGE_KEYS:
        value = raw.get(key, "")
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise RpaError("validacao", "Campo de mensagem inválido ou longo demais.")
        out[key] = value
    return out


def validate_result(result: dict[str, Any]) -> None:
    rows = result.get("results")
    if not isinstance(rows, list) or len(rows) > CHUNK:
        raise RpaError("validacao", "Lista de resultados inválida.")
    for row in rows:
        if not isinstance(row, dict) or row.get("situation") not in SITUATIONS:
            raise RpaError("validacao", "Situação desconhecida.")
        messages = row.get("messages", [])
        if not isinstance(messages, list) or len(messages) > MAX_MESSAGES:
            raise RpaError("validacao", "Lista de mensagens inválida.")
        for message in messages:
            _clean_message(message)
        if len(str(row.get("detail", ""))) > 1000:
            raise RpaError("validacao", "Detalhe longo demais.")


def on_success(job: RpaJob) -> None:
    """Grava por empresa SOMENTE o que a seleção autorizou; o resto é descartado e avisado."""

    query = DetQuery.objects.select_for_update().get(
        pk=job.payload["query_id"], organization=job.organization
    )
    allowed = {c["code"]: c for c in job.payload["companies"]}
    got: set[str] = set()
    for row in job.result.get("results", []):
        code = str(row.get("company_code", ""))
        company = allowed.get(code)
        if company is None or str(row.get("cnpj", "")) != company["cnpj"]:
            raise RpaError("validacao", "Resultado de empresa que não foi pedida.")
        messages = [_clean_message(m) for m in row.get("messages", [])]
        situation = row["situation"]
        detail = str(row.get("detail", ""))
        counter = row.get("portal_counter")
        # Trava de contagem: o contador do portal precisa bater com as linhas lidas.
        if situation == DetResult.Situation.UNREAD and (
            not isinstance(counter, int) or counter != len(messages)
        ):
            situation, messages = DetResult.Situation.ERROR, []
            detail = "Consulta inconclusiva: a contagem do portal não bate com as linhas lidas."
        if situation == DetResult.Situation.UNREAD and not messages:
            situation = DetResult.Situation.NONE
        if row.get("opened_any") is True:
            # O agente declarou ter aberto algo: ciência possível. Nunca esconder.
            detail = (detail + " ALERTA: houve abertura de mensagem.").strip()
            situation = DetResult.Situation.ERROR
        DetResult.objects.update_or_create(
            query=query,
            company_code=code,
            defaults={
                "organization": job.organization,
                "company_name": company["name"],
                "cnpj": company["cnpj"],
                "situation": situation,
                "messages": messages,
                "detail": detail[:1000],
            },
        )
        got.add(code)
    missing = set(allowed) - got
    for code in missing:
        DetResult.objects.update_or_create(
            query=query,
            company_code=code,
            defaults={
                "organization": job.organization,
                "company_name": allowed[code]["name"],
                "cnpj": allowed[code]["cnpj"],
                "situation": DetResult.Situation.ERROR,
                "messages": [],
                "detail": "O agente não devolveu esta empresa.",
            },
        )
    recompute(query)


def on_failure(job: RpaJob) -> None:
    query = DetQuery.objects.select_for_update().get(
        pk=job.payload["query_id"], organization=job.organization
    )
    for company in job.payload["companies"]:
        DetResult.objects.update_or_create(
            query=query,
            company_code=company["code"],
            defaults={
                "organization": job.organization,
                "company_name": company["name"],
                "cnpj": company["cnpj"],
                "situation": DetResult.Situation.ERROR,
                "messages": [],
                "detail": (job.error_detail or "Falha na consulta.")[:1000],
            },
        )
    recompute(query)


def recompute(query: DetQuery) -> DetQuery:
    results = list(query.results.all())
    total = len(query.companies)
    query.total_messages = sum(len(r.messages) for r in results)
    jobs = [c.job for c in query.chunks.select_related("job") if c.job is not None]
    if len(results) >= total and not any(
        j.state in (RpaJob.State.QUEUED, RpaJob.State.LEASED) for j in jobs
    ):
        failed = any(r.situation == DetResult.Situation.ERROR for r in results)
        query.state = DetQuery.State.FAILED if failed else DetQuery.State.DONE
        query.notice = "Há empresas com erro na consulta." if failed else ""
    elif any(j.state == RpaJob.State.LEASED for j in jobs) or results:
        query.state = DetQuery.State.RUNNING
    query.save()
    return query


def _safe(value: str) -> str:
    return "'" + value if _FORMULA.match(value) else value


def workbook(query: DetQuery) -> bytes:
    """Planilha com mensagens, pendências e resumo. Texto do portal nunca vira fórmula."""

    from openpyxl import Workbook  # type: ignore[import-untyped]

    book = Workbook()
    sheet = book.active
    sheet.title = "Mensagens"
    sheet.append(["Código", "Empresa", "CNPJ", "Tipo", "Remetente", "Data de envio", "Título"])
    pending = book.create_sheet("Pendências")
    pending.append(["Código", "Empresa", "CNPJ", "Situação", "Detalhe"])
    summary = book.create_sheet("Resumo")
    summary.append(["Situação", "Empresas"])
    counts: dict[str, int] = {}
    for result in query.results.order_by("company_code"):
        label = result.get_situation_display()
        counts[label] = counts.get(label, 0) + 1
        base = [_safe(result.company_code), _safe(result.company_name), result.cnpj]
        if result.situation == DetResult.Situation.UNREAD:
            for m in result.messages:
                sheet.append([*base, *(_safe(m[k]) for k in MESSAGE_KEYS)])
        elif result.situation != DetResult.Situation.NONE:
            pending.append([*base, label, _safe(result.detail)])
    for label, count in sorted(counts.items()):
        summary.append([label, count])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
