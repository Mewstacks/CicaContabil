from __future__ import annotations

from typing import cast
from urllib.parse import urlencode
from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.models import ClientCompany
from apps.hub.views import office_required, refuse, workspace_context
from apps.intelligence.forms import AssistantQuestionForm, FeedbackForm
from apps.intelligence.models import (
    ClassificationDraft,
    Conversation,
    LearningCandidate,
    Message,
)
from apps.intelligence.services import accessible_company, answer_question, record_feedback
from apps.organizations.models import Membership, Organization


def _can_curate(context: dict[str, object]) -> bool:
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }


def _active_conversation(
    *, raw_id: str | None, organization: Organization, company_ids: set[UUID]
) -> Conversation | None:
    if not raw_id:
        return None
    return (
        Conversation.objects.filter(
            id=raw_id,
            organization=organization,
            company_id__in=company_ids,
            closed_at__isnull=True,
        )
        .select_related("company")
        .first()
    )


def _assistant_url(conversation: Conversation | None = None) -> str:
    if conversation is None:
        return "intelligence:assistant"
    return f"{reverse('intelligence:assistant')}?{urlencode({'conversation': conversation.id})}"


@office_required
@require_http_methods(["GET", "POST"])
def assistant(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    allowed_companies = cast(list[ClientCompany], context["companies"])
    allowed_company_ids = {company.id for company in allowed_companies}
    allowed_company_id_strings = {str(company_id) for company_id in allowed_company_ids}
    requested_conversation_id = request.POST.get("conversation_id") or request.GET.get(
        "conversation"
    )
    active_conversation = _active_conversation(
        raw_id=requested_conversation_id,
        organization=office,
        company_ids=allowed_company_ids,
    )
    form = AssistantQuestionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        active_company = context.get("active_company")
        selected_id = form.cleaned_data["company_id"] or (
            active_company.id if isinstance(active_company, ClientCompany) else ""
        )
        membership = context.get("membership")
        company = accessible_company(
            organization=office,
            company_id=str(selected_id),
            membership=membership if isinstance(membership, Membership) else None,
            allowed_company_ids=allowed_company_id_strings,
        )
        if company is None:
            form.add_error("question", "Escolha uma empresa permitida antes de analisar.")
        elif requested_conversation_id and active_conversation is None:
            form.add_error("question", "Esta conversa não está disponível para a empresa atual.")
        elif active_conversation is not None and active_conversation.company_id != company.id:
            form.add_error("question", "Troque de conversa ao mudar de empresa.")
        else:
            try:
                conversation, _, _ = answer_question(
                    organization=office,
                    actor=cast(User, request.user),
                    question=form.cleaned_data["question"].strip(),
                    company=company,
                    request=request,
                    uploads=form.cleaned_data["attachments"],
                    conversation=active_conversation,
                )
            except ValueError as exc:
                form.add_error("attachments", str(exc))
            else:
                return redirect(_assistant_url(conversation))

    conversation_messages = []
    draft = None
    if active_conversation is not None:
        conversation_messages = list(
            active_conversation.messages.prefetch_related("attachments").order_by("created_at")
        )
        draft = (
            ClassificationDraft.objects.filter(
                organization=office,
                conversation=active_conversation,
                status=ClassificationDraft.Status.PENDING,
            )
            .order_by("-created_at")
            .first()
        )
    conversations = list(
        Conversation.objects.filter(
            organization=office, company_id__in=allowed_company_ids, closed_at__isnull=True
        )
        .select_related("company")
        .order_by("-updated_at")[:12]
    )
    context.update(
        {
            "page_title": "Assistente IA",
            "form": form,
            "active_conversation": active_conversation,
            "conversation_messages": conversation_messages,
            "conversation_history": conversations,
            "draft": draft,
        }
    )
    return render(request, "intelligence/assistant.html", context)


@office_required
@require_http_methods(["POST"])
def submit_feedback(request: HttpRequest, message_id: str) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    message = get_object_or_404(
        Message, id=message_id, organization=office, role=Message.Role.ASSISTANT
    )
    allowed_companies = cast(list[ClientCompany], context["companies"])
    allowed_company_ids = {str(company.id) for company in allowed_companies}
    if (
        message.conversation.company_id
        and str(message.conversation.company_id) not in allowed_company_ids
    ):
        return refuse(request, "Esta resposta não está disponível para a empresa atual.")
    form = FeedbackForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Não foi possível registrar o feedback.")
    else:
        record_feedback(
            message=message,
            organization=office,
            actor=cast(User, request.user),
            verdict=form.cleaned_data["verdict"],
            comment=form.cleaned_data["comment"].strip(),
            request=request,
        )
        messages.success(request, "Feedback registrado.")
    return redirect(_assistant_url(message.conversation))


@office_required
def learning_center(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    if not _can_curate(context):
        return refuse(request, "A central de aprendizado é restrita a owners e administradores.")
    context.update(
        {
            "page_title": "Central de aprendizado",
            "candidates": LearningCandidate.objects.filter(organization=office).select_related(
                "feedback__message"
            ),
            "can_publish": True,
        }
    )
    return render(request, "intelligence/learning.html", context)


@office_required
@require_http_methods(["POST"])
def review_candidate(request: HttpRequest, candidate_id: str, decision: str) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    if not _can_curate(context):
        return refuse(request, "Seu perfil não pode publicar aprendizado.")
    candidate = get_object_or_404(LearningCandidate, id=candidate_id, organization=office)
    if decision == "approve":
        candidate.status = LearningCandidate.Status.APPROVED
        candidate.reviewed_by = cast(User, request.user)
        candidate.save(update_fields=["status", "reviewed_by", "updated_at"])
        messages.success(request, "Candidato aprovado para o lote de avaliação.")
    elif decision == "reject":
        candidate.status = LearningCandidate.Status.REJECTED
        candidate.reviewed_by = cast(User, request.user)
        candidate.save(update_fields=["status", "reviewed_by", "updated_at"])
        messages.success(request, "Candidato rejeitado; a resposta original permanece auditável.")
    else:
        messages.error(request, "Decisão de aprendizado inválida.")
    return redirect("intelligence:learning")
