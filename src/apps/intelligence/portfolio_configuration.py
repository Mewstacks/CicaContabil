"""Reviewed pilot-to-company-portfolio transition, without re-pairing (D-331)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.intelligence.agent_scope import VERSION, build_portfolio_scope, validate_sync_scope
from apps.intelligence.models import AgentEnrollment, EdgeAgent
from apps.organizations.models import Membership, Organization

INVENTORY_LIMIT = 12 * 1024 * 1024
REVIEW_LIMIT = 32 * 1024
ACTION = "intelligence.agent.portfolio_configured"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contém campo repetido; revise o arquivo.")
        result[key] = value
    return result


def _document(raw: bytes, limit: int) -> dict[str, Any]:
    if not 0 < len(raw) <= limit:
        raise ValueError("Arquivo vazio ou superior ao limite explícito.")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError("Arquivo JSON inválido ou ambíguo.") from exc
    if not isinstance(value, dict):
        raise ValueError("Arquivo deve conter um objeto JSON.")
    return value


def _integer(value: Any, maximum: int) -> bool:
    return type(value) is int and 0 <= value <= maximum


def validate_inventory(inventory_raw: bytes) -> dict[str, Any]:
    """Check source structure without fabricating a reviewer or approving semantics."""
    inventory = _document(inventory_raw, INVENTORY_LIMIT)
    if (
        inventory.get("version") != "contad-schema-inventory-v1"
        or inventory.get("financial_period_start") != "2026-09-01"
        or inventory.get("status_mapping_approved") is not False
        or inventory.get("keys_relations_and_financial_semantics_verified") is not False
    ):
        raise ValueError("Inventário não corresponde à sonda de metadados autorizada.")
    try:
        observed = parse_datetime(inventory["observed_at_utc"])
        now = timezone.now()
        if (
            observed is None
            or timezone.is_naive(observed)
            or not now - timedelta(days=1) <= observed <= now
        ):
            raise ValueError
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(
            "Inventário deve ser recente (24 horas), com fuso e sem data futura."
        ) from exc
    objects = inventory.get("objects")
    if not isinstance(objects, list) or not 1 <= len(objects) <= 1500:
        raise ValueError("Quantidade de objetos do inventário inválida.")
    identities: set[str] = set()
    column_total = 0
    for obj in objects:
        if (
            not isinstance(obj, dict)
            or obj.get("schema") != "bethadba"
            or not isinstance(obj.get("name"), str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", obj["name"])
            or obj["name"].casefold() in identities
            or not isinstance(obj.get("columns"), list)
            or not obj["columns"]
        ):
            raise ValueError("Objeto/colunas incompletos ou repetidos no inventário.")
        identities.add(obj["name"].casefold())
        columns = obj["columns"]
        column_total += len(columns)
        if column_total > 50_000:
            raise ValueError("Inventário excede 50.000 colunas.")
        names: set[str] = set()
        for column in columns:
            if (
                not isinstance(column, dict)
                or not isinstance(column.get("name"), str)
                or not column["name"]
                or column["name"].casefold() in names
                or not isinstance(column.get("type"), str)
                or not column["type"]
                or not _integer(column.get("ordinal"), 50_000)
                or column["ordinal"] == 0
            ):
                raise ValueError("Metadados de coluna incompletos ou repetidos.")
            names.add(column["name"].casefold())
        if (
            obj["name"].casefold() == "geempre"
            and not {
                "codi_emp",
                "nome_emp",
                "cgce_emp",
                "stat_emp",
            }
            <= names
        ):
            raise ValueError("GEEMPRE sem as colunas exigidas; não habilitar a carteira.")
    if (
        "geempre" not in identities
        or type(inventory.get("object_count")) is not int
        or inventory["object_count"] != len(objects)
        or type(inventory.get("column_count")) is not int
        or inventory["column_count"] != column_total
    ):
        raise ValueError("Cobertura de metadados não confere.")
    statuses = inventory.get("company_status_counts")
    if not isinstance(statuses, list) or not 1 <= len(statuses) <= 20:
        raise ValueError("Situações de origem ou mapa revisado ausentes.")
    counts: dict[str, int] = {}
    for row in statuses:
        if (
            not isinstance(row, dict)
            or set(row) != {"source_status", "count"}
            or not isinstance(row["source_status"], str)
            or not re.fullmatch(r"[A-Z0-9_-]{1,16}", row["source_status"])
            or row["source_status"] in counts
            or not _integer(row["count"], 1_000_000)
        ):
            raise ValueError("Situação de origem inválida ou repetida.")
        counts[row["source_status"]] = row["count"]
    if not _integer(inventory.get("company_count"), 1_000_000) or inventory["company_count"] != sum(
        counts.values()
    ):
        raise ValueError("Contagens ou cobertura integral do mapa de situações não conferem.")
    return {
        **inventory,
        "inventory_sha256": hashlib.sha256(inventory_raw).hexdigest(),
        "inventory_observed_at": observed.isoformat(),
        "status_counts": counts,
    }


def reviewed_inventory(
    inventory_raw: bytes,
    review_raw: bytes,
    *,
    active_only: bool = False,
    allow_existing_active_selector: bool = False,
) -> dict[str, Any]:
    """Validate bounded source evidence and an explicitly separate human review."""
    inventory = validate_inventory(inventory_raw)
    review = _document(review_raw, REVIEW_LIMIT)
    existing_selector = review.get("version") == "contad-active-selection-review-v1"
    if set(review) != {
        "version",
        "organization_id",
        "agent_id",
        "inventory_sha256",
        "reviewer_id",
        "review_reference",
        "agent_version",
        "company_status_map",
    } or review["version"] not in (
        "contad-company-status-review-v1",
        "contad-active-selection-review-v1",
    ):
        raise ValueError("Contrato de revisão de situações inválido.")
    if existing_selector and (
        not active_only
        or not allow_existing_active_selector
        or review["reviewer_id"] is not None
        or review["company_status_map"] != {"A": True}
        or not isinstance(review["review_reference"], str)
        or not review["review_reference"].startswith("D-332:")
    ):
        raise ValueError("Seletor técnico restrito a A exige flags e referência D-332 explícitas.")
    for key in ("organization_id", "agent_id", *(() if existing_selector else ("reviewer_id",))):
        try:
            if str(UUID(review[key])) != review[key]:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Identificador da revisão inválido.") from exc
    if review["inventory_sha256"] != hashlib.sha256(inventory_raw).hexdigest():
        raise ValueError("SHA-256 do inventário difere da revisão.")
    if (
        not isinstance(review["review_reference"], str)
        or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,120}", review["review_reference"])
        or not isinstance(review["agent_version"], str)
        or not re.fullmatch(r"1\.0\.(?:[5-9]|[1-9][0-9]+)", review["agent_version"])
    ):
        raise ValueError("Referência de revisão ou versão compatível ausente.")
    mapping = review["company_status_map"]
    if (
        not isinstance(mapping, dict)
        or (
            not set(mapping) <= set(inventory["status_counts"])
            if existing_selector
            else set(mapping) != set(inventory["status_counts"])
        )
        or any(type(active) is not bool for active in mapping.values())
    ):
        raise ValueError("Cobertura integral do mapa revisado não confere.")
    return {
        **review,
        "review_sha256": hashlib.sha256(review_raw).hexdigest(),
        "company_count": inventory["company_count"],
        "status_counts": inventory["status_counts"],
        "inventory_observed_at": inventory["inventory_observed_at"],
        "review_origin": "existing_active_selector"
        if existing_selector
        else "organization_reviewer",
    }


def configure_portfolio(
    *,
    organization: Organization,
    agent_id: UUID,
    expected_revision: str,
    inventory_raw: bytes,
    review_raw: bytes,
    period_end: date,
    apply: bool = False,
    active_only: bool = False,
    allow_existing_active_selector: bool = False,
) -> dict[str, Any]:
    evidence = reviewed_inventory(
        inventory_raw,
        review_raw,
        active_only=active_only,
        allow_existing_active_selector=allow_existing_active_selector,
    )
    if active_only and tuple(map(int, evidence["agent_version"].split("."))) < (1, 0, 6):
        raise ValueError("Coleta somente de ativas exige agente 1.0.6 ou posterior comprovado.")
    if evidence["organization_id"] != str(organization.pk) or evidence["agent_id"] != str(agent_id):
        raise ValueError("Revisão não pertence a este escritório/agente.")
    with transaction.atomic():
        if apply:
            Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
        agents = EdgeAgent.objects.defer("shared_secret").filter(
            pk=agent_id, organization=organization
        )
        if apply:
            agents = agents.select_for_update(of=("self",))
        agent = agents.first()
        now = timezone.now()
        if (
            agent is None
            or agent.status != EdgeAgent.Status.ACTIVE
            or not agent.is_official
            or agent.last_seen_at is None
            or not now - timedelta(minutes=5) <= agent.last_seen_at <= now
        ):
            raise ValueError("Selecione o oficial ativo com heartbeat dos últimos cinco minutos.")
        reviewer = (
            Membership.objects.select_related("user")
            .filter(
                organization=organization,
                user_id=evidence["reviewer_id"],
                is_active=True,
                user__is_active=True,
                role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
            )
            .first()
        )
        if reviewer is None and evidence["review_origin"] != "existing_active_selector":
            raise ValueError("Revisão exige dono/administrador ativo deste escritório.")
        current = validate_sync_scope(agent.sync_scope, organization)
        proposed = build_portfolio_scope(
            organization=organization,
            start=date(2026, 9, 1),
            end=period_end,
            company_status_map=evidence["company_status_map"],
            active_only=active_only,
        )
        replay = AuditEvent.objects.filter(
            organization=organization,
            action=ACTION,
            target_id=str(agent.pk),
            metadata__previous_revision=expected_revision,
            metadata__revision=proposed["revision"],
            metadata__review_sha256=evidence["review_sha256"],
        ).exists()
        if current == proposed and replay:
            return {"applied": False, "replayed": True, "scope_revision": current["revision"]}
        if current["version"] != VERSION or current["revision"] != expected_revision:
            raise ValueError("Revisão anterior mudou ou não é piloto; refaça a prévia.")
        if current["period_start"] != "2026-09-01":
            raise ValueError("Início financeiro diverge da autorização CONTAD.")
        if (
            EdgeAgent.objects.filter(
                organization=organization, status=EdgeAgent.Status.PENDING_ACTIVATION
            ).exists()
            or AgentEnrollment.objects.filter(
                replaces_agent=agent,
                used_at=None,
                expires_at__gt=now,
            ).exists()
        ):
            raise ValueError("Há substituição pendente; não alterar o manifesto durante o corte.")
        result = {
            "applied": apply,
            "replayed": False,
            "organization_id": str(organization.pk),
            "agent_id": str(agent.pk),
            "previous_revision": current["revision"],
            "scope_revision": proposed["revision"],
            "datasets": ["companies"],
            "financial_collection_enabled": False,
            "existing_financial_data_preserved": True,
            "observed_company_count": evidence["company_count"],
            "company_selection": "active_only" if active_only else "all_reviewed_statuses",
            "review_origin": evidence["review_origin"],
            "selected_company_count": sum(
                count
                for code, count in evidence["status_counts"].items()
                if not active_only or evidence["company_status_map"].get(code, False)
            ),
            "inventory_sha256": evidence["inventory_sha256"],
        }
        if apply:
            agent.sync_scope = proposed
            agent.save(update_fields=["sync_scope", "updated_at"])
            record_event(
                action=ACTION,
                organization=organization,
                target=agent,
                actor=reviewer.user if reviewer is not None else None,
                metadata={
                    **result,
                    "revision": proposed["revision"],
                    "previous_scope": current,
                    "inventory_observed_at": evidence["inventory_observed_at"],
                    "review_sha256": evidence["review_sha256"],
                    "review_reference": evidence["review_reference"],
                    "reviewed_agent_version": evidence["agent_version"],
                },
            )
        return result
