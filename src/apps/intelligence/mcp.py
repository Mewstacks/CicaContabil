"""Internal, HTTP JSON-RPC 2.0 MCP surface.

It is intentionally not a public MCP endpoint: Hub is the only client in v1.  The
authenticated Hub session determines the tenant and role; callers cannot pass either
in arguments.  A future external transport must use MCP OAuth resource indicators and
audience validation rather than reusing this session transport.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from time import perf_counter
from typing import Any

from apps.audit.services import record_event
from apps.hub.controlplane import (
    authorization_is_fresh,
    companies_for_membership,
    company_has_capability,
    membership_has_capability,
)
from apps.intelligence.models import ClassificationDraft, Conversation, Message
from apps.intelligence.services import DominioMcp, EvidenceCard, accessible_company
from apps.organizations.models import Membership, Organization

PROTOCOL_VERSION = "2025-06-18"

TOOLS: list[dict[str, object]] = [
    {
        "name": "search_data_catalog",
        "description": "Busca fontes de negócio autorizadas no catálogo do escritório.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "maxLength": 300}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_company_context",
        "description": "Retorna o contexto compacto de uma empresa permitida.",
        "inputSchema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_risk_snapshot",
        "description": "Resume revisões abertas para uma empresa permitida.",
        "inputSchema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_obligations",
        "description": (
            "Lista obrigações a partir do espelho privado atualizado; nunca consulta SQL livre."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "period_days": {"type": "integer", "minimum": 1, "maximum": 366},
            },
            "required": ["company_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "retrieve_knowledge",
        "description": "Recupera cartões curtos de fonte aprovada; não retorna banco bruto.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "maxLength": 300}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "explain_classification",
        "description": (
            "Explica sugestão por regra aprovada ou uso histórico; nunca grava no Domínio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_classification_draft",
        "description": (
            "Cria somente um rascunho revisável no Hub após confirmação explícita; "
            "não altera o Domínio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "conversation_id": {"type": "string"},
                "confirmed_by_user": {"type": "boolean"},
            },
            "required": ["company_id", "conversation_id", "confirmed_by_user"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_answer_evidence",
        "description": "Recupera evidências de uma resposta pertencente ao escritório atual.",
        "inputSchema": {
            "type": "object",
            "properties": {"message_id": {"type": "string"}},
            "required": ["message_id"],
            "additionalProperties": False,
        },
    },
]


class McpToolError(ValueError):
    pass


def _cards(cards: Iterable[EvidenceCard]) -> list[dict[str, str]]:
    return [card.as_dict() for card in cards]


def _audit_result_metadata(
    *, name: str, result: dict[str, object], elapsed_ms: int
) -> dict[str, object]:
    """Keep an inspectable proof of a tool call without retaining tool content."""
    serialized = json.dumps(
        result, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
    )
    references: set[str] = set()
    evidence = result.get("evidence", [])
    if isinstance(evidence, list):
        for card in evidence:
            if isinstance(card, dict) and isinstance(card.get("reference"), str):
                references.add(card["reference"])
    return {
        "tool": name,
        "purpose": "internal_mcp_business_query",
        "result_keys": sorted(result.keys()),
        "result_hash": hashlib.sha256(serialized.encode()).hexdigest(),
        "source_hashes": sorted(
            hashlib.sha256(reference.encode()).hexdigest() for reference in references
        )[:8],
        "latency_ms": max(0, elapsed_ms),
    }


def call_tool(
    *,
    name: str,
    arguments: dict[str, Any],
    organization: Organization,
    membership: Membership,
    actor: object,
    request: object,
) -> dict[str, object]:
    started_at = perf_counter()
    if not isinstance(arguments, dict):
        raise McpToolError("Os argumentos da ferramenta devem ser um objeto.")
    allowed_arguments = {
        "search_data_catalog": {"query"},
        "retrieve_knowledge": {"query"},
        "get_company_context": {"company_id"},
        "get_risk_snapshot": {"company_id"},
        "list_obligations": {"company_id", "period_days"},
        "explain_classification": {"company_id"},
        "get_answer_evidence": {"message_id"},
        "create_classification_draft": {"company_id", "conversation_id", "confirmed_by_user"},
    }
    if name not in allowed_arguments or set(arguments) - allowed_arguments[name]:
        raise McpToolError("Ferramenta MCP ou argumento não permitido.")
    if not authorization_is_fresh(organization):
        raise McpToolError(
            "Permissão expirada; aguarde a renovação pelo controle central da Mewstack."
        )
    allowed_company_ids = {str(company.id) for company in companies_for_membership(membership)}
    required_capability = "draft" if name == "create_classification_draft" else "read"
    if name in {"search_data_catalog", "retrieve_knowledge"} and not membership_has_capability(
        membership=membership, capability=required_capability
    ):
        raise McpToolError("Seu perfil não possui leitura de dados deste escritório.")
    mcp = DominioMcp(organization, None)
    if name in {"search_data_catalog", "retrieve_knowledge"}:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip() or len(query) > 300:
            raise McpToolError("Informe uma consulta de até 300 caracteres.")
        cards = (
            mcp.retrieve_knowledge(query.strip())
            if name == "retrieve_knowledge"
            else mcp.search_data_catalog(query.strip())
        )
        result: dict[str, object] = {"evidence": _cards(cards)}
    elif name in {
        "get_company_context",
        "get_risk_snapshot",
        "explain_classification",
        "list_obligations",
    }:
        raw_company_id = arguments.get("company_id")
        company = accessible_company(
            organization=organization,
            company_id=raw_company_id,
            membership=membership,
            allowed_company_ids=allowed_company_ids,
        )
        if company is None:
            raise McpToolError("Empresa não encontrada no escopo autorizado.")
        if not company_has_capability(
            membership=membership, company=company, capability=required_capability
        ):
            raise McpToolError("Seu perfil não possui a capacidade necessária nesta empresa.")
        scoped_mcp = DominioMcp(organization, company)
        if name == "get_company_context":
            result = {
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "last_sync_at": company.last_dominio_sync_at.isoformat()
                    if company.last_dominio_sync_at
                    else None,
                }
            }
        elif name == "get_risk_snapshot":
            result = {"evidence": _cards(scoped_mcp.get_risk_snapshot())}
        elif name == "list_obligations":
            period_days = arguments.get("period_days", 31)
            if (
                isinstance(period_days, bool)
                or not isinstance(period_days, int)
                or not 1 <= period_days <= 366
            ):
                raise McpToolError("Período inválido para obrigações.")
            freshness, cards = scoped_mcp.list_obligations(period_days=period_days)
            result = {"freshness": freshness, "evidence": _cards(cards)}
        else:
            suggested_code, cards = scoped_mcp.explain_classification()
            result = {"suggested_code": suggested_code or None, "evidence": _cards(cards)}
    elif name == "get_answer_evidence":
        message_id = arguments.get("message_id")
        if not isinstance(message_id, str):
            raise McpToolError("Identificador da resposta inválido.")
        message = Message.objects.filter(
            id=message_id, organization=organization, role=Message.Role.ASSISTANT
        ).first()
        if message is None:
            raise McpToolError("Resposta não encontrada no escopo autorizado.")
        if (
            message.conversation.company_id
            and str(message.conversation.company_id) not in allowed_company_ids
        ):
            raise McpToolError("Resposta não encontrada no escopo autorizado.")
        result = {"evidence": message.evidence, "message_id": str(message.id)}
    elif name == "create_classification_draft":
        raw_company_id = arguments.get("company_id")
        raw_conversation_id = arguments.get("conversation_id")
        if arguments.get("confirmed_by_user") is not True or not isinstance(
            raw_conversation_id, str
        ):
            raise McpToolError("O usuário precisa confirmar a criação do rascunho.")
        company = accessible_company(
            organization=organization,
            company_id=raw_company_id,
            membership=membership,
            allowed_company_ids=allowed_company_ids,
        )
        conversation = Conversation.objects.filter(
            id=raw_conversation_id, organization=organization
        ).first()
        if (
            company is None
            or conversation is None
            or (conversation.company_id and str(conversation.company_id) not in allowed_company_ids)
        ):
            raise McpToolError("Empresa ou conversa não encontrada no escopo autorizado.")
        if not company_has_capability(membership=membership, company=company, capability="draft"):
            raise McpToolError(
                "Seu perfil não possui capacidade para criar rascunhos nesta empresa."
            )
        suggested_code, cards = DominioMcp(organization, company).explain_classification()
        if not suggested_code:
            raise McpToolError("Não há evidência suficiente para criar um rascunho.")
        draft = ClassificationDraft.objects.create(
            organization=organization,
            conversation=conversation,
            company=company,
            suggested_code=suggested_code,
            rationale="Rascunho confirmado pelo usuário com base nas fontes anexadas.",
            evidence=_cards(cards),
        )
        result = {
            "draft_id": str(draft.id),
            "suggested_code": suggested_code,
            "evidence": _cards(cards),
        }
    else:
        raise McpToolError("Ferramenta MCP não permitida.")
    record_event(
        action="intelligence.mcp.tool_called",
        actor=actor,
        organization=organization,
        request=request,
        metadata=_audit_result_metadata(
            name=name,
            result=result,
            elapsed_ms=round((perf_counter() - started_at) * 1_000),
        ),
    )
    return result
