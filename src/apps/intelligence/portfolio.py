"""Authenticated, bounded company scans for the office portfolio (D-323)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.intelligence.agent_scope import PORTFOLIO_VERSION, validate_sync_scope
from apps.intelligence.agent_v2 import _agent, _error, _payload
from apps.intelligence.models import AgentCompanyScan, EdgeAgent, IntelligenceConnector
from apps.intelligence.sync import sync_companies


def _receipt(scan: AgentCompanyScan) -> dict[str, Any]:
    return {
        "run_id": str(scan.pk),
        "after": scan.cursor,
        "received_count": scan.received_count,
        "expected_count": scan.expected_count,
        "page_count": scan.page_count,
        "complete": scan.completed_at is not None,
    }


def _abandon_scan(scan: AgentCompanyScan, *, code: str, request: HttpRequest) -> None:
    """Caller holds the agent lock. Preserve committed rows and their checkpoint."""
    if scan.completed_at is not None or scan.aborted_at is not None:
        return
    scan.aborted_at = scan.last_error_at = timezone.now()
    scan.last_error_code = code
    scan.save(update_fields=["aborted_at", "last_error_at", "last_error_code", "updated_at"])
    record_event(
        action="intelligence.dominio.company_scan_aborted",
        organization=scan.organization,
        target=scan,
        request=request,
        metadata={"reason": code, "received": scan.received_count},
    )


def _coverage_error(scan: AgentCompanyScan, *, code: str, request: HttpRequest) -> JsonResponse:
    _abandon_scan(scan, code=code, request=request)
    response = JsonResponse(
        {
            "error": "Cobertura alterada na origem; a próxima leitura começará do início.",
            "code": code,
            "scan_aborted": scan.aborted_at is not None,
        },
        status=409,
    )
    response["Cache-Control"] = "no-store"
    return response


def _company_rows(rows: Any, scope: dict[str, Any], after: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) > 500:
        raise ValueError("Página deve conter até 500 empresas.")
    normalized = []
    previous = int(after)
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"codigo", "nome", "cnpj_masked", "status"}:
            raise ValueError("Campos da empresa fora do contrato autorizado.")
        code, name, cnpj, status = (row[key] for key in ("codigo", "nome", "cnpj_masked", "status"))
        if (
            not isinstance(code, str)
            or not re.fullmatch(r"[1-9][0-9]{0,17}", code)
            or int(code) <= previous
            or not isinstance(name, str)
            or not name.strip()
            or len(name) > 180
            or name != name.strip()
            or not isinstance(cnpj, str)
            or len(cnpj) > 18
            or (cnpj and not re.fullmatch(r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}", cnpj))
            or not isinstance(status, str)
            or status not in scope["company_status_map"]
        ):
            raise ValueError("Empresa inválida, ordem inconsistente ou situação não revisada.")
        previous = int(code)
        normalized.append({**row, "active": scope["company_status_map"][status]})
    return normalized


@csrf_exempt
@require_POST
def company_scan(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request, 500_000)
    if payload is None:
        return _error("Solicitação de carteira inválida.", 400)
    try:
        # Serializes open/page/replay and rechecks revocation/scope after waiting.
        with transaction.atomic():
            agent = (
                EdgeAgent.objects.select_for_update()
                .select_related("organization")
                .get(pk=agent.pk)
            )
            if agent.status != EdgeAgent.Status.ACTIVE:
                return _error("Agente revogado.", 401)
            scope = validate_sync_scope(agent.sync_scope, agent.organization)
            if (
                scope["version"] != PORTFOLIO_VERSION
                or payload.get("scope_revision") != scope["revision"]
            ):
                return _error("Revisão de carteira ausente ou desatualizada.", 403)
            action = payload.get("action")
            if action == "open":
                if set(payload) != {"action", "scope_revision", "expected_count"}:
                    raise ValueError("Campos de abertura inválidos.")
                count = payload["expected_count"]
                if type(count) is not int or not 0 <= count <= 1_000_000:
                    raise ValueError("Contagem de origem inválida ou superior ao limite explícito.")
                previous_scan = AgentCompanyScan.objects.filter(
                    agent=agent,
                    scope_revision=scope["revision"],
                    completed_at=None,
                    aborted_at=None,
                ).first()
                if previous_scan is not None and previous_scan.expected_count != count:
                    _abandon_scan(previous_scan, code="source_count_changed", request=request)
                scan, _ = AgentCompanyScan.objects.get_or_create(
                    agent=agent,
                    scope_revision=scope["revision"],
                    completed_at=None,
                    aborted_at=None,
                    defaults={"organization": agent.organization, "expected_count": count},
                )
                response = JsonResponse(_receipt(scan))
            elif action == "page":
                if set(payload) != {
                    "action",
                    "scope_revision",
                    "run_id",
                    "after",
                    "rows",
                    "complete",
                    "source_count",
                }:
                    raise ValueError("Campos de página inválidos.")
                try:
                    run_id = UUID(payload["run_id"])
                except (ValueError, TypeError, AttributeError) as exc:
                    raise ValueError("Identificador de carga inválido.") from exc
                found_scan = AgentCompanyScan.objects.filter(
                    pk=run_id,
                    agent=agent,
                    organization=agent.organization,
                    scope_revision=scope["revision"],
                    aborted_at=None,
                ).first()
                if found_scan is None:
                    return _error("Carga não encontrada neste agente/escritório.", 403)
                scan = found_scan
                after = payload["after"]
                if not isinstance(after, str) or not re.fullmatch(r"0|[1-9][0-9]{0,17}", after):
                    raise ValueError("Cursor inválido.")
                # Stale clients must not invalidate progress made by another request.
                # Completed scans remain immutable, with their original replay receipt.
                if after != scan.cursor and after != scan.last_after:
                    return _error("Página fora de sequência ou carga já encerrada.", 409)
                rows = _company_rows(payload["rows"], scope, after)
                complete, count = payload["complete"], payload["source_count"]
                if (
                    type(complete) is not bool
                    or type(count) is not int
                    or not 0 <= count <= 1_000_000
                ):
                    return _error("Declaração de cobertura inválida.", 409)
                digest = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if scan.last_digest == digest:
                    response = JsonResponse({**scan.last_result, "replayed": True})
                else:
                    if scan.completed_at is not None or after != scan.cursor:
                        return _error("Página fora de sequência ou carga já encerrada.", 409)
                    if count != scan.expected_count:
                        return _coverage_error(scan, code="source_count_changed", request=request)
                    received = scan.received_count + len(rows)
                    if received > count or (complete and received != count):
                        return _coverage_error(scan, code="coverage_mismatch", request=request)
                    if not complete and not rows:
                        return _error("Página sem progresso e sem declaração de fim.", 409)
                    connector, _ = IntelligenceConnector.objects.get_or_create(
                        organization=agent.organization,
                        mode=IntelligenceConnector.Mode.EDGE_AGENT,
                        defaults={"status": "healthy"},
                    )
                    result = sync_companies(
                        organization=agent.organization,
                        connector=connector,
                        rows=rows,
                        request=request,
                        full_snapshot=False,
                        honor_source_active=True,
                    )
                    scan.received_count = received
                    scan.page_count += 1
                    scan.cursor = rows[-1]["codigo"] if rows else after
                    scan.last_after, scan.last_digest = after, digest
                    if complete:
                        scan.completed_at = timezone.now()
                    scan.last_result = {
                        **_receipt(scan),
                        "created": result.created,
                        "updated": result.updated,
                        "ignored": result.ignored,
                        "replayed": False,
                    }
                    scan.save()
                    if complete:
                        record_event(
                            action="intelligence.dominio.company_scan_completed",
                            organization=agent.organization,
                            target=scan,
                            request=request,
                            metadata={
                                "rows": received,
                                "pages": scan.page_count,
                                "scope_revision": scope["revision"],
                            },
                        )
                    response = JsonResponse(scan.last_result)
            else:
                raise ValueError("Ação de carteira desconhecida.")
    except ValueError as exc:
        return _error(str(exc), 400)
    response["Cache-Control"] = "no-store"
    return response
