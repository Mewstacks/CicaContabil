"""DET: só a lista de não lidas, seleção autorizada, contagem conferida, planilha segura."""

from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client
from openpyxl import load_workbook

from apps.accounts.models import User
from apps.det import services
from apps.det.models import DetQuery, DetResult
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

pytestmark = pytest.mark.django_db


def _office(slug: str = "fed", *, on: bool = True) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="det", enabled=on)
    return org


def _user(org: Organization, role: str = "owner") -> User:
    user = User.objects.create_user(
        email=f"{role}-{uuid4().hex[:8]}@{org.slug}.test", password="uma-senha-longa"
    )
    Membership.objects.create(organization=org, user=user, role=role)
    return user


def _company(org: Organization, code: str, cnpj: str = "11.222.333/0001-81") -> ClientCompany:
    return ClientCompany.objects.create(
        organization=org, name=f"Empresa {code}", dominio_code=code, cnpj_masked=cnpj
    )


def _msg(title: str = "Notificação") -> dict[str, str]:
    return {"type": "Aviso", "sender": "MTE", "sent_at": "01/10/2026", "title": title}


def _run(org: Organization, results: list[dict[str, Any]]) -> RpaJob:
    claimed = rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND])
    assert claimed is not None
    job, token = claimed
    rpa.complete(
        job_id=job.pk, organization=org, agent_id="ag", token=token, result={"results": results}
    )
    return job


def _row(company: dict[str, str], situation: str = "unread", **extra: Any) -> dict[str, Any]:
    return {
        "company_code": company["code"],
        "cnpj": company["cnpj"],
        "situation": situation,
        "messages": [_msg()],
        "portal_counter": 1,
        **extra,
    }


def test_selection_needs_active_company_with_cnpj_and_is_split_in_chunks() -> None:
    org = _office()
    user = _user(org)
    with pytest.raises(services.DetError):
        services.create_query(organization=org, user=user, companies=[])
    with pytest.raises(services.DetError):
        services.create_query(organization=org, user=user, companies=[_company(org, "1", cnpj="")])
    other = _office("other")
    with pytest.raises(services.DetError):
        services.create_query(organization=org, user=user, companies=[_company(other, "9")])
    companies = [_company(org, str(100 + i), f"11.222.333/{i:04d}-81") for i in range(23)]
    query = services.create_query(organization=org, user=user, companies=companies)
    assert query.chunks.count() == 3 and RpaJob.objects.count() == 3
    assert all(j.payload["list_only"] is True for j in RpaJob.objects.all())


def test_payload_must_stay_list_only() -> None:
    with pytest.raises(RpaError):
        services.validate_payload(
            {"companies": [{"code": "1"}], "list_only": False, "query_id": "x"}
        )


def test_unread_result_is_stored_and_query_done() -> None:
    org = _office()
    company = _company(org, "10")
    query = services.create_query(organization=org, user=_user(org), companies=[company])
    snap = query.companies[0]
    _run(org, [_row(snap)])
    query.refresh_from_db()
    result = DetResult.objects.get()
    assert result.situation == "unread" and result.messages[0]["title"] == "Notificação"
    assert query.state == DetQuery.State.DONE and query.total_messages == 1


def test_counter_mismatch_makes_result_inconclusive_and_drops_rows() -> None:
    org = _office()
    query = services.create_query(
        organization=org, user=_user(org), companies=[_company(org, "10")]
    )
    _run(org, [_row(query.companies[0], portal_counter=3)])
    result = DetResult.objects.get()
    assert result.situation == "error" and result.messages == [] and "inconclusiva" in result.detail
    query.refresh_from_db()
    assert query.state == DetQuery.State.FAILED


def test_opened_message_is_never_hidden() -> None:
    org = _office()
    query = services.create_query(
        organization=org, user=_user(org), companies=[_company(org, "10")]
    )
    _run(org, [_row(query.companies[0], opened_any=True)])
    result = DetResult.objects.get()
    assert result.situation == "error" and "ALERTA" in result.detail


def test_result_for_company_not_requested_is_refused() -> None:
    org = _office()
    query = services.create_query(
        organization=org, user=_user(org), companies=[_company(org, "10")]
    )
    foreign = {"code": "99", "cnpj": "99999999000199"}
    claimed = rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND])
    assert claimed is not None
    with pytest.raises(RpaError):
        rpa.complete(
            job_id=claimed[0].pk,
            organization=org,
            agent_id="ag",
            token=claimed[1],
            result={"results": [_row(foreign)]},
        )
    wrong_cnpj = {**query.companies[0], "cnpj": "00000000000000"}
    with pytest.raises(RpaError):
        rpa.complete(
            job_id=claimed[0].pk,
            organization=org,
            agent_id="ag",
            token=claimed[1],
            result={"results": [_row(wrong_cnpj)]},
        )
    assert not DetResult.objects.exists()


def test_bad_situation_and_oversized_fields_are_refused() -> None:
    for row in (
        {"situation": "inventada", "messages": []},
        {
            "situation": "unread",
            "messages": [{"type": "x" * 2001, "sender": "", "sent_at": "", "title": ""}],
        },
        {"situation": "unread", "messages": "nao-lista"},
    ):
        with pytest.raises(RpaError):
            services.validate_result({"results": [row]})


def test_company_omitted_by_agent_becomes_error_and_failed_job_marks_all() -> None:
    org = _office()
    companies = [_company(org, "10"), _company(org, "11", "44.555.666/0001-00")]
    query = services.create_query(organization=org, user=_user(org), companies=companies)
    _run(org, [_row(query.companies[0])])
    omitted = DetResult.objects.get(company_code=query.companies[1]["code"])
    assert omitted.situation == "error" and "não devolveu" in omitted.detail
    org2 = _office("dois")
    q2 = services.create_query(
        organization=org2, user=_user(org2), companies=[_company(org2, "10")]
    )
    claimed = rpa.claim_next(organization=org2, agent_id="ag", kinds=[services.KIND])
    assert claimed is not None
    rpa.fail(
        job_id=claimed[0].pk,
        organization=org2,
        agent_id="ag",
        token=claimed[1],
        code="validacao",
        detail="portal fora",
    )
    q2.refresh_from_db()
    assert q2.state == DetQuery.State.FAILED and DetResult.objects.filter(query=q2).count() == 1


def test_resend_replaces_instead_of_duplicating() -> None:
    org = _office()
    query = services.create_query(
        organization=org, user=_user(org), companies=[_company(org, "10")]
    )
    snap = query.companies[0]
    job = _run(org, [_row(snap)])
    RpaJob.objects.filter(pk=job.pk).update(
        state=RpaJob.State.QUEUED, leased_by="", lease_token_hash=""
    )
    _run(org, [_row(snap, situation="none", messages=[], portal_counter=0)])
    assert DetResult.objects.count() == 1 and DetResult.objects.get().situation == "none"


def test_workbook_neutralizes_formulas() -> None:
    org = _office()
    query = services.create_query(
        organization=org, user=_user(org), companies=[_company(org, "10")]
    )
    row = _row(query.companies[0])
    row["messages"] = [_msg('=HYPERLINK("http://x")')]
    _run(org, [row])
    book = load_workbook(io.BytesIO(services.workbook(query)))
    cell = book["Mensagens"]["G2"].value
    assert cell.startswith("'=") and book.sheetnames == ["Mensagens", "Pendências", "Resumo"]


def _client(org: Organization, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client


def test_pages_gate_isolation_and_download() -> None:
    off = _office("off", on=False)
    assert _client(off, _user(off)).get("/app/det/").status_code == 403
    org = _office()
    company = _company(org, "10")
    owner = _client(org, _user(org))
    assert owner.get("/app/det/").status_code == 200
    created = owner.post("/app/det/consultas/nova/", {"empresas": [company.pk]})
    assert created.status_code == 302
    query = DetQuery.objects.get()
    assert owner.get(created["Location"]).status_code == 200
    sheet = owner.get(f"/app/det/consultas/{query.pk}/planilha/")
    assert sheet.status_code == 200 and sheet["Cache-Control"] == "private, no-store"
    other = _office("b")
    stranger = _client(other, _user(other))
    assert stranger.get(f"/app/det/consultas/{query.pk}/").status_code == 404
    assert stranger.get(f"/app/det/consultas/{query.pk}/planilha/").status_code == 404


def test_reader_cannot_create_query() -> None:
    org = _office()
    company = _company(org, "10")
    _client(org, _user(org, "auditor")).post("/app/det/consultas/nova/", {"empresas": [company.pk]})
    assert not DetQuery.objects.exists()
