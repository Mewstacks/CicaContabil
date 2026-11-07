"""Read bounded sync coverage without reading company identities or credentials."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone

from apps.intelligence.agent_scope import PORTFOLIO_VERSION, VERSION
from apps.intelligence.models import AgentCompanyScan, EdgeAgent
from apps.organizations.selectors import resolve_organization


class Command(BaseCommand):
    help = "Mostra heartbeat e cobertura da carteira sem dados cadastrais, segredos ou escrita."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--organization", required=True, help="UUID ou slug do escritório")
        parser.add_argument("--agent", help="UUID do agente; sempre limitado ao escritório")
        parser.add_argument("--limit", type=int, default=20, help="Scans por agente, de 1 a 100")

    def handle(self, *args: Any, **options: Any) -> None:
        limit = options["limit"]
        if not 1 <= limit <= 100:
            raise CommandError("--limit deve estar entre 1 e 100.")
        agent_id = None
        if options.get("agent"):
            try:
                agent_id = UUID(options["agent"])
            except (ValueError, TypeError) as exc:
                raise CommandError("Identificador de agente inválido.") from exc
        if connection.in_atomic_block or not connection.get_autocommit():
            raise CommandError("Execute o diagnóstico fora de uma transação existente.")
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            organization = resolve_organization(options["organization"])
            if organization is None:
                raise CommandError("Escritório não encontrado.")
            agents = EdgeAgent.objects.filter(organization=organization).order_by("pk")
            if agent_id is not None:
                agents = agents.filter(pk=agent_id)
                if not agents.exists():
                    raise CommandError("Agente não encontrado neste escritório.")
            if agents.count() > 100:
                raise CommandError("Mais de cem agentes; selecione um com --agent.")
            observed = timezone.now()
            result = []
            for agent in agents.values("id", "status", "last_seen_at", "sync_scope"):
                scope = agent["sync_scope"]
                version = scope.get("version") if isinstance(scope, dict) else None
                if version not in (VERSION, PORTFOLIO_VERSION):
                    version = "unscoped" if scope == {} else "invalid"
                scans = AgentCompanyScan.objects.filter(
                    organization=organization, agent_id=agent["id"]
                ).order_by("-created_at", "-pk")
                total = scans.count()
                rows: list[dict[str, Any]] = [
                    dict(row)
                    for row in scans.values(
                        "id",
                        "created_at",
                        "completed_at",
                        "aborted_at",
                        "last_error_code",
                        "last_error_at",
                        "expected_count",
                        "received_count",
                        "page_count",
                    )[:limit]
                ]
                for row in rows:
                    row["state"] = (
                        "completed"
                        if row["completed_at"] is not None
                        else "aborted"
                        if row["aborted_at"] is not None
                        else "in_progress"
                    )
                seen = agent["last_seen_at"]
                result.append(
                    {
                        "agent_id": agent["id"],
                        "agent_status": agent["status"],
                        "scope_version": version,
                        "last_seen_at": seen,
                        "heartbeat_age_seconds": (
                            max(0, int((observed - seen).total_seconds()))
                            if seen is not None
                            else None
                        ),
                        "scans": rows,
                        "total_scans": total,
                        "older_scans_omitted": max(0, total - limit),
                    }
                )
        self.stdout.write(
            json.dumps(
                {
                    "organization_id": str(organization.pk),
                    "observed_at": observed,
                    "read_only": True,
                    "coverage_kind": "keyset_scan_not_erp_snapshot",
                    "agents": result,
                },
                cls=DjangoJSONEncoder,
                sort_keys=True,
            )
        )
