import hashlib
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    OperationalActivity,
    OperationalEvidence,
    ProductModule,
    ReformAlert,
)
from apps.hub.operations import complete_activity, completion_requirements
from apps.hub.reform_activities import request_reform_analysis, sync_reform_activities
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def review_data():
    office = Organization.objects.create(name="Radar", slug="radar-analysis")
    user = User.objects.create_user("radar-analysis@example.test", "SafePassword2026!")
    member = Membership.objects.create(organization=office, user=user, role="owner")
    company = ClientCompany.objects.create(organization=office, name="Empresa Radar")
    ProductModule.objects.create(organization=office, code=ProductModule.Code.REFORM, enabled=True)
    alert = ReformAlert.objects.create(
        source="rfb",
        external_key=hashlib.sha256(b"https://www.gov.br/receitafederal/teste").hexdigest(),
        title="Publicação fiscal",
        source_url="https://www.gov.br/receitafederal/teste",
        relevance="fiscal",
        content_hash="a",
    )
    return office, user, member, company, alert


def _request(data):
    _, user, member, company, alert = data
    return request_reform_analysis(
        alert_id=alert.pk,
        company_id=company.pk,
        membership=member,
        actor=user,
        reason="Conferir possível necessidade de adequação.",
    )


def _review(activity, user):
    OperationalEvidence.objects.create(
        organization=activity.organization,
        activity=activity,
        kind="human",
        recorded_by=user,
        summary="Análise documentada",
    )


def test_radar_review_version_reopens_without_duplicate_or_inferred_obligation(review_data):
    office, user, member, _company, alert = review_data
    activity = _request(review_data)
    assert activity.assigned_to == user
    assert activity.legal_due_on is None and activity.competence is None
    assert activity.obligation_status == "not_applicable"
    assert _request(review_data).pk == activity.pk
    assert activity.evidence_items.count() == 1
    assert completion_requirements(activity)
    _review(activity, user)
    complete_activity(activity=activity, membership=member, actor=user, request=None)
    sync_reform_activities(alert.pk)
    activity.refresh_from_db()
    assert activity.work_status == "completed"
    alert.title = "Publicação revisada"
    alert.relevance = "general"
    alert.save()
    with pytest.raises(ValidationError, match="versão atual"):
        complete_activity(activity=activity, membership=member, actor=user, request=None)
    with patch("apps.hub.reform.urlopen") as network:
        call_command("sync_reform_activities", organization=office.pk, stdout=StringIO())
        network.assert_not_called()
    activity.refresh_from_db()
    assert activity.work_status == "pending"
    assert activity.completed_by is None
    assert activity.evidence_items.filter(kind="source").count() == 2
    assert activity.evidence_items.filter(summary="Fiscal: Publicação fiscal").exists()
    assert activity.evidence_items.filter(source_url=alert.source_url).count() == 2
    assert completion_requirements(activity)
    _review(activity, user)
    assert (
        complete_activity(
            activity=activity, membership=member, actor=user, request=None
        ).work_status
        == "completed"
    )
    assert activity.events.filter(event_type="reform_received").count() == 2


def test_radar_refuses_cross_office_and_consultative_requests(review_data):
    _office, user, member, _company, alert = review_data
    other = Organization.objects.create(name="Outro", slug="radar-other")
    foreign = ClientCompany.objects.create(organization=other, name="Empresa fora")
    with pytest.raises(PermissionDenied):
        request_reform_analysis(
            alert_id=alert.pk,
            company_id=foreign.pk,
            membership=member,
            actor=user,
            reason="Teste",
        )
    member.role = "auditor"
    member.save()
    with pytest.raises(PermissionDenied):
        _request(review_data)
    assert not OperationalActivity.objects.exists()


def test_collection_updates_only_explicitly_linked_companies(review_data):
    from apps.hub.reform import CollectedAlert, refresh_reform_source

    office, user, member, _company, alert = review_data
    activity = _request(review_data)
    _review(activity, user)
    complete_activity(activity=activity, membership=member, actor=user, request=None)
    ClientCompany.objects.create(organization=office, name="Empresa sem vínculo")
    with patch(
        "apps.hub.reform._fetch_source",
        return_value=[
            CollectedAlert(title="Novas regras de IBS e CBS", source_url=alert.source_url),
        ],
    ):
        assert refresh_reform_source("rfb") == (0, 1)
        assert refresh_reform_source("rfb") == (0, 0)
    activity.refresh_from_db()
    assert activity.work_status == "pending"
    assert OperationalActivity.objects.count() == 1
    assert activity.events.filter(event_type="reform_received").count() == 2
    _review(activity, user)
    complete_activity(activity=activity, membership=member, actor=user, request=None)
    with patch(
        "apps.hub.reform._fetch_source",
        return_value=[
            CollectedAlert(title="Receita apreende mercadorias", source_url=alert.source_url),
        ],
    ):
        assert refresh_reform_source("rfb") == (0, 1)
    activity.refresh_from_db()
    assert activity.work_status == "pending"
    assert activity.evidence_items.filter(summary="Geral: Receita apreende mercadorias").exists()


def test_radar_web_selection_returns_to_activity_and_does_not_collect(client, review_data):
    from django.utils import timezone

    from apps.hub.models import ReformSourceStatus

    office, user, member, company, alert = review_data
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(office.pk)
    session.save()
    url = reverse("hub:reform-analysis", args=[alert.pk])
    ReformSourceStatus.objects.create(
        source="rfb", last_success_at=timezone.now(), last_error="Fonte indisponível",
    )
    with patch("apps.hub.reform.urlopen") as network:
        radar_html = client.get(reverse("hub:reform")).content.decode()
        assert url in radar_html
        assert "Falha na coleta" in radar_html
        assert "Coleta concluída" not in radar_html
        assert "Última atualização" in radar_html
        detail = client.get(url)
        assert detail.status_code == 200
        assert b"data-company-filter" in detail.content
        assert b"Criar ou retomar atividade de an" in detail.content
        assert b"Nenhuma an" in detail.content
        assert b"n\xc3\xa3o conclua que a norma se aplica" in detail.content
        assert not OperationalActivity.objects.exists()
        invalid = client.post(url, {"company": company.pk, "reason": ""})
        assert invalid.status_code == 400
        assert b"data-form-errors" in invalid.content
        response = client.post(url, {"company": company.pk, "reason": "Conferir adequação"})
        activity = OperationalActivity.objects.get()
        assert response.url == reverse("hub:activity-detail", args=[activity.pk])
        assert url in client.get(response.url).content.decode()
        assert response.url in client.get(url).content.decode()
        client.post(url, {"company": company.pk, "reason": "Repetir"})
        assert OperationalActivity.objects.count() == 1
        network.assert_not_called()
    member.role = "auditor"
    member.save()
    assert client.post(url, {"company": company.pk, "reason": "Teste"}).status_code == 403
