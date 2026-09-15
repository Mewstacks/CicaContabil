from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_has_capability, company_is_allowed
from apps.hub.models import AccumulatorObservation, AccumulatorRule, ClientCompany, ReviewCase
from apps.intelligence.gateway import (
    can_use_claude_fallback,
    claude_fallback_payload,
    generate_claude_fallback_completion,
    generate_local_completion,
)
from apps.intelligence.mirror import get_mirror_cards
from apps.intelligence.models import (
    AnswerFeedback,
    AssistantSettings,
    ChatAttachment,
    ClassificationDraft,
    ClaudeFallbackApproval,
    Conversation,
    DataCatalogEntry,
    EgressAudit,
    KnowledgeSource,
    LearningCandidate,
    Message,
)
from apps.intelligence.retrieval import query_words, retrieve_chunks, retrieve_shared_chunks
from apps.organizations.models import Membership, Organization
from apps.platform.availability import copilot_is_available
from apps.platform.billing import reserve_usage, settle_usage
from apps.platform.models import PlatformConfiguration
from apps.platform.operation_access import require_operation_access

AI_ANSWER_ACTION = "ai.answer"


@dataclass(frozen=True)
class EvidenceCard:
    label: str
    reference: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"label": self.label, "reference": self.reference, "detail": self.detail}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compact_conversation_context(*, conversation: Conversation) -> str:
    """Bounded continuity: a local summary plus recent turns, never a chat dump."""
    recent = list(
        Message.objects.filter(conversation=conversation)
        .order_by("-created_at")
        .values_list("role", "content")[:4]
    )
    recent.reverse()
    lines = []
    summary = conversation.summary.replace("\n", " ").strip()
    if summary:
        lines.append(f"Resumo anterior: {summary[:520]}")
    for role, content in recent:
        value = content.replace("\n", " ").strip()[:180]
        if value:
            actor = "Usuário" if role == Message.Role.USER else "Assistente"
            lines.append(f"{actor}: {value}")
    return "\n".join(lines)[:1_100]


def next_conversation_summary(*, previous: str, question: str, answer: str) -> str:
    """Keep useful continuity locally without repeatedly sending the full transcript."""
    prior = previous.replace("\n", " ").strip()[-440:]
    question_line = question.replace("\n", " ").strip()[:190]
    answer_line = answer.replace("\n", " ").strip()[:280]
    parts = [
        part for part in (prior, f"Pergunta: {question_line}", f"Resposta: {answer_line}") if part
    ]
    return " | ".join(parts)[-980:]


MAX_MODEL_EVIDENCE_CARDS = 6
MAX_MODEL_EVIDENCE_CHARACTERS = 1_800


def compact_model_evidence(*groups: Iterable[EvidenceCard]) -> list[dict[str, str]]:
    """Return a predictable evidence packet for a model, not the UI's full trace.

    Groups are ordered by business relevance. In particular, an approved
    classification rule must not be displaced by a long attachment or catalogue
    result simply because it was collected later in the request.
    """
    result: list[dict[str, str]] = []
    used: set[tuple[str, str, str]] = set()
    remaining = MAX_MODEL_EVIDENCE_CHARACTERS
    for group in groups:
        for card in group:
            if len(result) >= MAX_MODEL_EVIDENCE_CARDS or remaining <= 0:
                return result
            label = card.label.replace("\n", " ").strip()[:110]
            reference = card.reference.replace("\n", " ").strip()[:180]
            detail = card.detail.replace("\n", " ").strip()[:300]
            identity = (label, reference, detail)
            if not label or identity in used:
                continue
            fixed_size = len(label) + len(reference)
            if fixed_size >= remaining:
                continue
            detail = detail[: max(0, remaining - fixed_size)]
            if not detail:
                continue
            result.append({"label": label, "reference": reference, "detail": detail})
            used.add(identity)
            remaining -= fixed_size + len(detail)
    return result


ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "text/csv",
}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 5


def local_multimodal_endpoint() -> str:
    """Return only the developer-configured private adapter origin."""

    return str(
        PlatformConfiguration.objects.filter(key="default")
        .values_list("local_multimodal_endpoint", flat=True)
        .first()
        or ""
    ).rstrip("/")


def _attachment_type(name: str, declared_type: str) -> str:
    normalized = declared_type.casefold().split(";", 1)[0].strip()
    if normalized in ALLOWED_ATTACHMENT_TYPES:
        return normalized
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"


def _analyze_with_private_model(*, content: bytes, content_type: str, name: str) -> str | None:
    """Use only a deployment-owned local multimodal service; never Claude fallback."""
    endpoint = local_multimodal_endpoint()
    if not endpoint:
        return None
    payload = json.dumps(
        {
            "name": name,
            "content_type": content_type,
            "content_b64": base64.b64encode(content).decode(),
            "instruction": (
                "Extraia somente fatos fiscais ou operacionais verificáveis "
                "em até 1.200 caracteres."
            ),
        },
        separators=(",", ":"),
    ).encode()
    request = Request(  # noqa: S310 - deployment-owned private endpoint
        f"{endpoint}/v1/analyze-document",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:  # noqa: S310 - deployment-owned private endpoint
            result = json.loads(response.read(32_000))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    analysis = result.get("analysis") if isinstance(result, dict) else None
    return analysis.strip()[:1_200] if isinstance(analysis, str) and analysis.strip() else None


def store_chat_attachments(
    *,
    organization: Organization,
    conversation: Conversation,
    message: Message,
    uploads: Iterable[UploadedFile],
) -> list[EvidenceCard]:
    uploads = list(uploads)
    if len(uploads) > MAX_ATTACHMENTS_PER_MESSAGE:
        raise ValueError(f"Envie no máximo {MAX_ATTACHMENTS_PER_MESSAGE} anexos por vez.")
    cards: list[EvidenceCard] = []
    for upload in uploads:
        name = str(getattr(upload, "name", "anexo"))[:180]
        content = upload.read()
        if not isinstance(content, bytes) or not content:
            raise ValueError("Não foi possível ler um dos anexos.")
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise ValueError("Cada anexo pode ter no máximo 10 MB.")
        content_type = _attachment_type(name, str(getattr(upload, "content_type", "")))
        if content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise ValueError("Envie PDF, imagem, TXT ou CSV.")
        analysis = (
            content.decode("utf-8", errors="replace")[:1_200].strip()
            if content_type in {"text/plain", "text/csv"}
            else _analyze_with_private_model(content=content, content_type=content_type, name=name)
        )
        status = (
            ChatAttachment.Status.ANALYZED if analysis else ChatAttachment.Status.AWAITING_MODEL
        )
        attachment = ChatAttachment.objects.create(
            organization=organization,
            conversation=conversation,
            message=message,
            original_name=name,
            content_type=content_type,
            byte_size=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
            encrypted_content_b64=base64.b64encode(content).decode(),
            analysis=analysis or "",
            status=status,
        )
        if analysis:
            cards.append(EvidenceCard("Anexo analisado", attachment.original_name, analysis))
        elif local_multimodal_endpoint():
            from apps.intelligence.tasks import analyze_attachment_task

            attachment_id = str(attachment.id)

            def schedule_attachment_analysis(
                scheduled_attachment_id: str = attachment_id,
            ) -> None:
                analyze_attachment_task.delay(scheduled_attachment_id)

            transaction.on_commit(schedule_attachment_analysis)
    return cards


def prior_attachment_cards(
    *, conversation: Conversation, current_message: Message
) -> list[EvidenceCard]:
    """Reuse prior local analyses in a thread without re-sending the raw attachment."""
    attachments = (
        ChatAttachment.objects.filter(
            conversation=conversation,
            status=ChatAttachment.Status.ANALYZED,
        )
        .exclude(message=current_message)
        .order_by("-updated_at")[:3]
    )
    return [
        EvidenceCard("Anexo analisado", attachment.original_name, attachment.analysis[:1_200])
        for attachment in attachments
        if attachment.analysis
    ]


def accessible_company(
    *,
    organization: Organization,
    company_id: str | None,
    membership: Membership | None = None,
    allowed_company_ids: set[str] | None = None,
) -> ClientCompany | None:
    if not company_id:
        return None
    try:
        UUID(str(company_id))
    except (TypeError, ValueError):
        return None
    company = ClientCompany.objects.filter(
        organization=organization, id=company_id, active=True
    ).first()
    if company is None or (
        membership is not None
        and (
            not company_is_allowed(membership=membership, company=company)
            or not company_has_capability(membership=membership, company=company, capability="read")
        )
    ):
        return None
    if allowed_company_ids is not None and str(company.id) not in allowed_company_ids:
        return None
    return company


class DominioMcp:
    """Business tools only: scoped data cards, not database/schema/SQL access."""

    def __init__(self, organization: Organization, company: ClientCompany | None) -> None:
        self.organization = organization
        self.company = company

    def search_data_catalog(self, term: str) -> list[EvidenceCard]:
        words = [word for word in term.split() if len(word) > 2][:5]
        entries = DataCatalogEntry.objects.filter(organization=self.organization, enabled=True)
        if words:
            from django.db.models import Q

            query = Q()
            for word in words:
                query |= Q(business_name__icontains=word) | Q(description__icontains=word)
            entries = entries.filter(query)
        return [
            EvidenceCard(entry.business_name, entry.source_reference, entry.description[:180])
            for entry in entries[:4]
        ]

    def get_risk_snapshot(self) -> list[EvidenceCard]:
        if not self.company:
            return []
        pending = ReviewCase.objects.filter(
            organization=self.organization,
            document__company=self.company,
            status=ReviewCase.Status.OPEN,
        ).count()
        return [
            EvidenceCard(
                "Fila de revisão",
                "CICA · Revisões",
                f"{pending} ocorrência(s) aguardando decisão humana para esta empresa.",
            )
        ]

    def list_obligations(self, *, period_days: int) -> tuple[str, list[EvidenceCard]]:
        """Read the tenant mirror only; a stale mirror never triggers live ODBC from chat."""
        if not self.company:
            return "not_configured", []
        freshness, cards = get_mirror_cards(
            organization=self.organization,
            company=self.company,
            tool_name="list_obligations",
            period_days=period_days,
        )
        return freshness, [EvidenceCard(card.label, card.reference, card.detail) for card in cards]

    def retrieve_knowledge(self, term: str) -> list[EvidenceCard]:
        """Bounded tenant RAG over approved sources without exposing the full document."""
        tenant_chunks = retrieve_chunks(organization=self.organization, query=term, limit=3)
        global_chunks = retrieve_shared_chunks(query=term, limit=max(0, 4 - len(tenant_chunks)))
        if tenant_chunks or global_chunks:
            tenant_cards = [
                EvidenceCard(
                    chunk.source.title,
                    chunk.source.source_reference,
                    chunk.content[:280] + ("…" if len(chunk.content) > 280 else ""),
                )
                for chunk in tenant_chunks
            ]
            shared_cards = [
                EvidenceCard(
                    chunk.source.title,
                    chunk.source.source_reference,
                    chunk.content[:280] + ("…" if len(chunk.content) > 280 else ""),
                )
                for chunk in global_chunks
            ]
            return [*tenant_cards, *shared_cards]
        words = query_words(term)
        if not words:
            return []
        sources = KnowledgeSource.objects.filter(
            organization=self.organization, status=KnowledgeSource.Status.APPROVED
        ).order_by("-approved_at", "-updated_at")[:50]
        cards: list[EvidenceCard] = []
        for source in sources:
            searchable = f"{source.title}\n{source.source_reference}\n{source.content}".casefold()
            if not any(word in searchable for word in words):
                continue
            detail = source.content.replace("\n", " ").strip()
            cards.append(
                EvidenceCard(
                    source.title,
                    source.source_reference,
                    detail[:280] + ("…" if len(detail) > 280 else ""),
                )
            )
            if len(cards) == 4:
                break
        return cards

    def explain_classification(self) -> tuple[str, list[EvidenceCard]]:
        if not self.company:
            return "Escolha uma empresa para sugerir uma classificação.", []
        rule = (
            AccumulatorRule.objects.filter(
                organization=self.organization, company=self.company, active=True
            )
            .order_by("priority")
            .first()
        )
        observation = (
            AccumulatorObservation.objects.filter(
                organization=self.organization, company=self.company
            )
            .order_by("-frequency", "-last_used_at")
            .first()
        )
        if rule:
            return rule.accumulator_code, [
                EvidenceCard(
                    "Regra aprovada",
                    rule.name,
                    f"Prioridade {rule.priority}; regra ativa para a empresa.",
                )
            ]
        if observation:
            return observation.accumulator_code, [
                EvidenceCard(
                    "Uso histórico",
                    "Espelho Domínio autorizado",
                    f"Usado {observation.frequency} vez(es) no histórico disponível.",
                )
            ]
        return "", []


def answer_question(
    *,
    organization: Organization,
    actor: User,
    question: str,
    company: ClientCompany | None,
    request: object,
    uploads: Iterable[UploadedFile] = (),
    conversation: Conversation | None = None,
) -> tuple[Conversation, Message, ClassificationDraft | None]:
    """Create a grounded response only after rechecking the caller's data scope."""
    if not copilot_is_available():
        raise ValueError("O Copiloto ainda não está disponível para escritórios.")
    with transaction.atomic():
        # The membership is also used to decide whether a managed installation may
        # create a reviewable draft.  Resolve it independently from the optional
        # Claude fallback path so a local-only answer follows the same policy.
        membership = Membership.objects.filter(
            organization=organization,
            organization__is_active=True,
            user=actor,
            user__is_active=True,
            is_active=True,
        ).first()
        if membership is None:
            raise ValueError("Acesso ao escritório não autorizado.")
        require_operation_access(organization, "ai")
        usage = reserve_usage(
            organization=organization,
            action_code=AI_ANSWER_ACTION,
            idempotency_key=f"ai-answer:{uuid4()}",
        )
        if (
            company is not None
            and accessible_company(
                organization=organization, company_id=str(company.pk), membership=membership
            )
            is None
        ):
            raise ValueError("Empresa fora do escopo autorizado.")
        if conversation is not None and conversation.closed_at is not None:
            raise ValueError("Esta conversa está encerrada.")
        if conversation is None:
            conversation = Conversation.objects.create(
                organization=organization,
                company=company,
                title=question[:160],
                summary="",
            )
        elif conversation.organization_id != organization.id or conversation.company_id != getattr(
            company, "id", None
        ):
            raise ValueError("Conversa fora da empresa selecionada.")
        conversation_context = compact_conversation_context(conversation=conversation)
        user_message = Message.objects.create(
            organization=organization,
            conversation=conversation,
            role=Message.Role.USER,
            content=question,
            context_hash=_digest(question),
        )
        attachment_cards = store_chat_attachments(
            organization=organization,
            conversation=conversation,
            message=user_message,
            uploads=uploads,
        )
        previous_attachment_cards = prior_attachment_cards(
            conversation=conversation,
            current_message=user_message,
        )
        mcp = DominioMcp(organization, company)
        _mirror_freshness, mirror_cards = mcp.list_obligations(period_days=31)
        knowledge_cards = mcp.retrieve_knowledge(question)
        catalog_cards = mcp.search_data_catalog(question)
        risk_cards = mcp.get_risk_snapshot()
        cards = [
            *attachment_cards,
            *previous_attachment_cards,
            *mirror_cards,
            *knowledge_cards,
            *catalog_cards,
            *risk_cards,
        ]
        suggested_code, classification_cards = mcp.explain_classification()
        cards.extend(classification_cards)
        model_evidence = compact_model_evidence(
            classification_cards,
            attachment_cards,
            previous_attachment_cards,
            mirror_cards,
            knowledge_cards,
            catalog_cards,
            risk_cards,
        )
        if suggested_code:
            conclusion = f"Sugestão: acumulador {suggested_code}."
        elif cards:
            conclusion = f"Encontrei {len(cards)} ponto(s) relevante(s) para revisão."
        else:
            conclusion = "Não encontrei fonte suficiente. Escolha uma empresa ou refine a pergunta."
        local_completion = generate_local_completion(
            question=question,
            company_name=company.name if company else "Não selecionada",
            evidence=model_evidence,
            conversation_context=conversation_context,
        )
        model_version = "grounded-rules-v1"
        if local_completion:
            conclusion = local_completion.content
            model_version = local_completion.model
        elif PlatformConfiguration.objects.filter(
            key="default", local_llm_endpoint__gt=""
        ).exists():
            # Cloud is considered only after an actual local runtime attempt failed.
            assistant_settings = (
                AssistantSettings.objects.select_for_update()
                .filter(organization=organization)
                .first()
            )
            approval = (
                ClaudeFallbackApproval.objects.select_for_update()
                .filter(organization=organization)
                .first()
            )
            role = membership.role if membership is not None else ""
            if assistant_settings is not None:
                decision = can_use_claude_fallback(
                    assistant_settings=assistant_settings,
                    approval=approval,
                    role=role,
                    estimated_cost_cents=assistant_settings.claude_max_request_cents,
                )
                fallback_payload = claude_fallback_payload(
                    question=question,
                    company_name=company.name if company else "Não selecionada",
                    conversation_context=conversation_context,
                    evidence=model_evidence,
                    allow_full_data=assistant_settings.claude_full_data_allowed,
                    model=assistant_settings.claude_model,
                )
                audit_claude_egress(
                    organization=organization,
                    actor=actor,
                    role=role,
                    payload=json.dumps(fallback_payload, ensure_ascii=False, sort_keys=True),
                    allowed=decision.provider == "claude",
                    estimated_cost_cents=assistant_settings.claude_max_request_cents,
                    model=assistant_settings.claude_model,
                )
                if decision.provider == "claude":
                    cloud_completion = generate_claude_fallback_completion(
                        api_key=assistant_settings.claude_api_key,
                        model=assistant_settings.claude_model,
                        question=question,
                        company_name=company.name if company else "Não selecionada",
                        conversation_context=conversation_context,
                        evidence=model_evidence,
                        allow_full_data=assistant_settings.claude_full_data_allowed,
                    )
                    if cloud_completion is not None:
                        conclusion = cloud_completion.content
                        model_version = cloud_completion.model
        draft = None
        if (
            suggested_code
            and company
            and (
                membership is None
                or company_has_capability(
                    membership=membership, company=company, capability="draft"
                )
            )
        ):
            draft = ClassificationDraft.objects.create(
                organization=organization,
                conversation=conversation,
                company=company,
                suggested_code=suggested_code,
                rationale=(
                    "Sugestão baseada exclusivamente em regra aprovada "
                    "ou uso histórico exibido nas evidências."
                ),
                evidence=[card.as_dict() for card in classification_cards],
            )
        response = Message.objects.create(
            organization=organization,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=conclusion,
            evidence=[card.as_dict() for card in cards],
            model_version=model_version,
            context_hash=_digest(
                question
                + "|"
                + conversation_context
                + "|"
                + "|".join(card.reference for card in cards)
            ),
        )
        settle_usage(event=usage, provider_http_status=200, billable=True)
        conversation.summary = next_conversation_summary(
            previous=conversation.summary,
            question=question,
            answer=conclusion,
        )
        conversation.save(update_fields=["summary", "updated_at"])
        record_event(
            action="intelligence.answer.generated",
            actor=actor,
            organization=organization,
            target=response,
            request=request,
            metadata={
                "evidence_count": len(cards),
                "model_evidence_count": len(model_evidence),
                "model_evidence_characters": sum(
                    len("".join(card.values())) for card in model_evidence
                ),
                "draft_created": draft is not None,
                "model": model_version,
            },
        )
    return conversation, response, draft


def record_feedback(
    *,
    message: Message,
    organization: Organization,
    actor: User,
    verdict: str,
    comment: str,
    request: object,
) -> AnswerFeedback:
    feedback, _ = AnswerFeedback.objects.update_or_create(
        message=message,
        submitted_by=actor,
        defaults={"organization": organization, "verdict": verdict, "comment": comment},
    )
    if verdict == AnswerFeedback.Verdict.NOT_HELPFUL:
        LearningCandidate.objects.get_or_create(
            feedback=feedback,
            defaults={
                "organization": organization,
                "source_summary": (
                    "Candidato criado a partir de feedback negativo; "
                    "exige fontes e avaliação antes da publicação."
                ),
                "prior_answer": message.content,
                "candidate_answer": "Pendente de curadoria com evidência verificável.",
                "evaluation": {"status": "pending_evidence"},
            },
        )
    record_event(
        action="intelligence.answer.feedback",
        actor=actor,
        organization=organization,
        target=feedback,
        request=request,
        metadata={"verdict": verdict, "has_comment": bool(comment)},
    )
    return feedback


def audit_claude_egress(
    *,
    organization: Organization,
    actor: User,
    role: str,
    payload: str,
    allowed: bool,
    estimated_cost_cents: int = 0,
    model: str = "",
) -> EgressAudit:
    """Call this before any provider client. It stores a hash only, never payload content."""
    return EgressAudit.objects.create(
        organization=organization,
        provider="anthropic",
        purpose="technical_fallback",
        payload_hash=_digest(payload),
        actor=actor,
        role=role,
        allowed=allowed,
        estimated_cost_cents=max(0, estimated_cost_cents),
        model=model[:80],
    )
