"""Synthetic company collection journeys: historical scope, sources, access and recovery."""

from datetime import date
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_persistence import import_title_snapshot
from apps.intelligence.agent_scope import build_portfolio_scope
from apps.intelligence.models import CompanyTitleCollection, EdgeAgent
from apps.organizations.models import Organization
from test_native_ledger import post
from test_native_title_review import post_fields
from test_native_titles import complete
from test_native_titles_automatic import CAPABILITY, automatic_sample
from test_title_persistence import context as context_fixture

context = context_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def case(context, settings):
    account, actor, _ = context
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    account.company.dominio_code = "212"
    account.company.save(update_fields=["dominio_code"])
    account.ledger_code = "8"
    account.save(update_fields=["ledger_code"])
    company = ClientCompany.objects.create(
        organization=account.organization, name="Empresa sem conta", dominio_code="37"
    )
    agent = EdgeAgent.objects.create(
        organization=account.organization,
        label="Conexão sintética",
        fingerprint="titles-ui",
        shared_secret="synthetic-only",
        is_official=True,
        status="active",
        last_seen_at=timezone.now(),
        sync_scope=build_portfolio_scope(
            organization=account.organization,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            company_status_map={"A": True},
            active_only=True,
        ),
    )
    client = Client()
    client.force_login(actor)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    return dict(account=account, company=company, agent=agent, actor=actor, client=client)


def endpoint():
    return reverse("hub:reconciliation-title-requests")


def fields(case, **extra):
    return {
        "companies": [str(case["company"].pk)],
        "start_month": "2019-12",
        "end_month": "2019-12",
        "request_key": str(uuid4()),
        "action": "preview",
        **extra,
    }


def request_batch(case, **extra):
    payload = fields(case, **extra)
    preview = case["client"].post(endpoint(), payload)
    assert preview.status_code == 200, preview.content
    payload.update(
        action="request", expected_revision=preview.context["collection_preview"]["revision"]
    )
    response = case["client"].post(endpoint(), payload)
    assert response.status_code == 302, response.content
    return response, payload


def receive(case):
    response, _ = request_batch(case)
    job = CompanyTitleCollection.objects.get()
    pending = post(case["agent"], "agent-v2-titles-next", CAPABILITY)
    assert pending.status_code == 200 and pending.json()["job"]["id"] == str(job.pk)
    _scope, data = automatic_sample(job.pk, company=37, start="2019-12-01")
    accepted = complete(case["agent"], job, data)
    assert accepted.status_code == 200, accepted.content
    job.refresh_from_db()
    return job, response


def test_company_without_account_previews_requests_and_opens_historical_source(case):
    initial = case["client"].get(endpoint())
    assert initial.status_code == 200
    assert case["company"] in initial.context["collection_form"].fields["companies"].queryset
    assert not CompanyTitleCollection.objects.exists()
    job, response = receive(case)
    history = case["client"].get(response.url)
    assert history.status_code == 200
    assert history.context["collection_jobs"][0]["source_available"]
    source = case["client"].get(reverse("hub:reconciliation-title-source", args=[job.pk]))
    assert source.status_code == 200, source.content
    assert "A fonte está disponível sem conta bancária" in source.content.decode()
    assert source.context["collection_source_page"].paginator.count == 2
    assert len(source.context["collection_source_page"][0]["payments"]) == 3
    assert "-2.00" in source.content.decode()
    assert not source.context["collection_account"]
    assert not FinancialAccount.objects.filter(company=case["company"]).exists()
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert "no-store" in source["Cache-Control"]


def test_preview_lists_146_companies_and_twelve_months_without_truncation(case):
    ClientCompany.objects.bulk_create(
        [
            ClientCompany(
                organization=case["company"].organization,
                name=f"Sintética {i}",
                dominio_code=str(1000 + i),
            )
            for i in range(144)
        ]
    )
    companies = list(
        ClientCompany.objects.filter(organization=case["company"].organization).values_list(
            "pk", flat=True
        )
    )
    assert len(companies) == 146
    response = case["client"].post(
        endpoint(),
        fields(
            case,
            companies=[str(pk) for pk in companies],
            start_month="2018-01",
            end_month="2018-12",
        ),
    )
    assert response.status_code == 200, response.content
    assert response.context["collection_preview"]["count"] == 1752
    assert len(response.context["collection_selected"]) == 146
    assert len(response.context["collection_preview"]["rows"]) == 1752
    assert "Solicitar 1.752 buscas" in response.content.decode()
    assert not CompanyTitleCollection.objects.exists()
    too_large = case["client"].post(
        endpoint(),
        fields(
            case,
            companies=[str(pk) for pk in companies],
            start_month="2018-01",
            end_month="2019-02",
        ),
    )
    assert too_large.status_code == 400 and "2.000" in too_large.content.decode()


@pytest.mark.parametrize(
    "changes",
    [
        {"start_month": "2020-13"},
        {"start_month": "0000-01"},
        {"end_month": "9999-01"},
        {"end_month": "2019-11"},
        {"start_month": "2019-1"},
        {"start_month": ["2019-12", "2020-01"]},
        {"companies": []},
        {"companies": [str(uuid4())]},
        {"action": ["preview", "request"]},
    ],
)
def test_invalid_selection_never_creates_jobs(case, changes):
    response = case["client"].post(endpoint(), fields(case, **changes))
    assert response.status_code == 400
    assert not CompanyTitleCollection.objects.exists()


def test_repeated_company_and_forged_preview_are_rejected(case):
    response = case["client"].post(
        endpoint(), fields(case, companies=[str(case["company"].pk)] * 2)
    )
    assert response.status_code == 400
    response = case["client"].post(
        endpoint(), fields(case, action="request", expected_revision="0" * 64)
    )
    assert response.status_code == 409 and not CompanyTitleCollection.objects.exists()


def test_confirmation_is_idempotent_and_stale_company_requires_new_preview(case):
    response, payload = request_batch(case, end_month="2020-01")
    assert CompanyTitleCollection.objects.count() == 2
    repeated = case["client"].post(endpoint(), payload)
    assert repeated.status_code == 302 and repeated.url == response.url
    assert CompanyTitleCollection.objects.count() == 2
    case["company"].dominio_code = "38"
    case["company"].save(update_fields=["dominio_code"])
    stale = case["client"].post(endpoint(), payload)
    assert stale.status_code == 409 and CompanyTitleCollection.objects.count() == 2


def test_pagination_keeps_all_jobs_and_month_filter_does_not_expand(case):
    response, _ = request_batch(case, start_month="2010-01", end_month="2012-02")
    first = case["client"].get(response.url)
    assert first.status_code == 200
    assert len(first.context["collection_jobs"]) == 25
    assert first.context["collection_page"].paginator.count == 26
    second = case["client"].get(endpoint(), {"page": "2"})
    assert second.status_code == 200 and len(second.context["collection_jobs"]) == 1
    filtered = case["client"].get(endpoint(), {"month": "2010-03"})
    assert filtered.status_code == 200 and len(filtered.context["collection_jobs"]) == 1
    invalid = case["client"].get(endpoint(), {"month": "bad"})
    assert invalid.status_code == 400 and not invalid.context.get("collection_jobs")


def test_status_delivery_retry_and_stored_source_are_distinct(case):
    request_batch(case)
    job = CompanyTitleCollection.objects.get()
    url = reverse("hub:reconciliation-title-request-status")
    response = case["client"].get(url, {"job": str(job.pk)})
    assert response.status_code == 200 and response.json()["jobs"][0]["status"] == "queued"
    assert "no-store" in response["Cache-Control"]
    CompanyTitleCollection.objects.filter(pk=job.pk).update(claimed_at=timezone.now())
    response = case["client"].get(url, {"job": str(job.pk)})
    assert response.json()["jobs"][0]["status"] == "delivered"
    assert not response.json()["jobs"][0]["source_url"]
    CompanyTitleCollection.objects.filter(pk=job.pk).update(state="review")
    response = case["client"].get(url, {"job": str(job.pk)})
    row = response.json()["jobs"][0]
    assert row["can_retry"] and not row["source_url"]
    retried = case["client"].post(row["retry_url"], {"request_key": row["retry_key"]})
    assert retried.status_code == 302 and CompanyTitleCollection.objects.count() == 2
    assert case["client"].get(url, {"job": [str(job.pk)] * 2}).status_code == 400
    assert case["client"].get(url, {"job": [str(uuid4()) for _ in range(26)]}).status_code == 400
    assert case["client"].get(url, {"job": str(uuid4())}).status_code == 404


def test_source_selects_only_explicit_account_of_same_company(case):
    job, _ = receive(case)
    account = FinancialAccount.objects.create(
        organization=case["company"].organization,
        company=case["company"],
        name="Conta escolhida",
        account_reference="SYN-37",
        ledger_code="8",
    )
    url = reverse("hub:reconciliation-title-source", args=[job.pk])
    assert case["client"].get(url, {"account": case["account"].pk}).status_code == 404
    response = case["client"].get(url, {"account": account.pk})
    assert response.status_code == 200 and response.context["collection_account"] == account
    row = response.context["collection_source_page"][0]
    review = case["client"].get(row["url"])
    assert review.status_code == 200, review.content
    assert review.context["title_account"] == account
    assert not ReconciliationTitleSnapshot.objects.exists()
    catalog = case["client"].get(
        reverse("hub:reconciliation-native-titles", args=[account.pk]), {"capture": job.pk}
    )
    assert catalog.status_code == 200 and catalog.context["native_capture_id"] == str(job.pk)


def test_historical_source_stays_readable_when_financial_snapshot_is_newer(case, context):
    from test_title_persistence import encoded

    account, actor, payload = context
    response, _ = request_batch(case, companies=[str(account.company_id)])
    job = CompanyTitleCollection.objects.get()
    _scope, data = automatic_sample(job.pk, company=212, start="2019-12-01")
    assert complete(case["agent"], job, data).status_code == 200
    import_title_snapshot(
        financial_account=account,
        actor=actor,
        content=encoded(payload),
        evidence_reference="Fotografia sintética mais recente",
    )
    source = case["client"].get(
        reverse("hub:reconciliation-title-source", args=[job.pk]), {"account": account.pk}
    )
    assert source.status_code == 200
    target = source.context["collection_source_page"][0]["url"]
    review = case["client"].get(target)
    assert review.status_code == 200
    preview = case["client"].post(target, post_fields(review))
    assert preview.status_code == 409
    assert "anterior à fotografia vigente" in preview.content.decode()
    assert "Fonte recebida" in preview.content.decode()
    assert ReconciliationTitleSnapshot.objects.count() == 1
    assert case["client"].get(response.url).status_code == 200


def test_auditor_reads_company_source_but_cannot_request_or_review(case, membership):
    job, _ = receive(case)
    membership.role = "auditor"
    membership.save(update_fields=["role"])
    CompanyAccessGrant.objects.create(
        organization=case["company"].organization,
        company=case["company"],
        membership=membership,
        modules=["reconciliation"],
    )
    response = case["client"].get(endpoint())
    assert response.status_code == 200 and not response.context["collection_can_write"]
    assert case["client"].post(endpoint(), fields(case)).status_code == 403
    source = case["client"].get(reverse("hub:reconciliation-title-source", args=[job.pk]))
    assert source.status_code == 200 and "source-account" not in source.content.decode()


def test_foreign_company_and_jobs_never_leak(case, membership):
    foreign = Organization.objects.create(name="Outro escritório", slug="other-title-office")
    other = ClientCompany.objects.create(
        organization=foreign, name="Segredo externo", dominio_code="999"
    )
    assert case["client"].get(endpoint(), {"company": other.pk}).status_code == 404
    assert (
        case["client"].post(endpoint(), fields(case, companies=[str(other.pk)])).status_code == 400
    )
    job, _ = receive(case)
    membership.role = "operator"
    membership.save(update_fields=["role"])
    assert (
        case["client"].get(reverse("hub:reconciliation-title-source", args=[job.pk])).status_code
        == 404
    )
    assert (
        case["client"]
        .get(reverse("hub:reconciliation-title-request-status"), {"job": job.pk})
        .status_code
        == 404
    )


def test_csrf_demo_and_invalid_filters_never_write(case):
    client = Client(enforce_csrf_checks=True)
    client.force_login(case["actor"])
    session = client.session
    session["hub_organization_id"] = str(case["company"].organization_id)
    session.save()
    assert client.post(endpoint(), fields(case)).status_code == 403
    assert case["client"].get(endpoint(), {"company": [case["company"].pk] * 2}).status_code == 400
    assert case["client"].get(endpoint(), {"page": "0"}).status_code == 400
    case["company"].organization.is_demo = True
    case["company"].organization.save(update_fields=["is_demo"])
    assert case["client"].post(endpoint(), fields(case)).status_code == 403
    assert not CompanyTitleCollection.objects.exists()
