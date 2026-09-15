from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import AccumulatorRule, ClientCompany, OfficeProfile, ProductModule
from apps.intelligence.models import AnswerFeedback, ClassificationDraft, LearningCandidate, Message
from apps.intelligence.services import DominioMcp
from apps.organizations.models import Organization
from apps.platform.models import Plan, PlanServiceRate, PlatformConfiguration, TenantContract


@pytest.fixture
def ai_trial(organization):
    PlatformConfiguration.objects.update_or_create(
        key="default", defaults={"copilot_available_for_offices": True}
    )
    plan = Plan.objects.create(code="intelligence-test", name="Intelligence test")
    PlanServiceRate.objects.create(plan=plan, action_code="ai.answer", included_units=10)
    OfficeProfile.objects.create(organization=organization, trial_started_at=timezone.now())
    ProductModule.objects.create(organization=organization, code="ai", enabled=True)
    return TenantContract.objects.create(
        organization=organization,
        plan=plan,
        status="trial",
        starts_on=timezone.localdate(),
        trial_ends_on=timezone.localdate() + timedelta(days=14),
        selected_modules=["ai"],
    )


@pytest.mark.django_db(databases={"default", "knowledge"})
def test_assistant_creates_grounded_answer_and_reviewable_draft(
    org_client, organization, ai_trial
) -> None:
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa Acme", dominio_code="001"
    )
    AccumulatorRule.objects.create(
        organization=organization,
        company=company,
        name="Serviços recorrentes",
        accumulator_code="SERV-001",
        priority=10,
    )

    response = org_client.post(
        reverse("intelligence:assistant"),
        {"question": "Qual classificação usar?", "company_id": str(company.id)},
    )

    assert response.status_code == 302
    answer = Message.objects.get(role=Message.Role.ASSISTANT)
    assert answer.evidence
    assert any(item["label"] == "Regra aprovada" for item in answer.evidence)
    assert any(item["reference"] == "Serviços recorrentes" for item in answer.evidence)
    draft = ClassificationDraft.objects.get(organization=organization)
    assert draft.suggested_code == "SERV-001"
    assert draft.status == ClassificationDraft.Status.PENDING


@pytest.mark.django_db(databases={"default", "knowledge"})
def test_negative_feedback_creates_candidate_not_an_automatic_change(
    org_client, organization, ai_trial
) -> None:
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa Acme",
        dominio_code="001",
    )
    response = org_client.post(
        reverse("intelligence:assistant"),
        {"question": "O que devo revisar?", "company_id": str(company.id)},
    )
    assert response.status_code == 302
    answer = Message.objects.get(organization=organization, role=Message.Role.ASSISTANT)

    response = org_client.post(
        reverse("intelligence:feedback", args=[answer.id]),
        {"verdict": AnswerFeedback.Verdict.NOT_HELPFUL, "comment": "Faltou fonte."},
    )

    assert response.status_code == 302
    candidate = LearningCandidate.objects.get(organization=organization)
    assert candidate.status == LearningCandidate.Status.PENDING
    assert candidate.evaluation["status"] == "pending_evidence"


@pytest.mark.django_db
def test_mcp_catalogue_is_scoped_to_the_current_organization(organization) -> None:
    other = Organization.objects.create(name="Outro", slug="outro")
    from apps.intelligence.models import DataCatalogEntry

    DataCatalogEntry.objects.create(
        organization=other,
        module="fiscal",
        business_name="Obrigação secreta",
        description="Nunca pode aparecer para Acme.",
        sensitivity=DataCatalogEntry.Sensitivity.RESTRICTED,
        source_reference="interno",
        enabled=True,
    )

    cards = DominioMcp(organization, None).search_data_catalog("obrigação")

    assert cards == []
