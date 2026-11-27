"""Admissões: revisão obrigatória, travas, dado pessoal fora de log/carga, incerto nunca repete."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.admissions import services
from apps.admissions.models import Admission
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob

pytestmark = pytest.mark.django_db
CPF = "52998224725"
CPF_DEP = "11144477735"


def _office(slug: str = "fed", *, on: bool = True, enabled: bool = True) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="admissions", enabled=on)
    cfg = services.settings_for(org)
    cfg.execution_enabled, cfg.allowed_codes, cfg.example_code = enabled, ["10", "9996"], "9996"
    cfg.save()
    return org


def _user(org: Organization, role: str = "owner") -> User:
    user = User.objects.create_user(
        email=f"{role}-{uuid4().hex[:8]}@{org.slug}.test", password="uma-senha-longa"
    )
    Membership.objects.create(organization=org, user=user, role=role)
    return user


def _company(org: Organization, code: str = "10") -> ClientCompany:
    return ClientCompany.objects.create(organization=org, name=f"Empresa {code}", dominio_code=code)


def _data(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "Fulano de Tal",
        "cpf": CPF,
        "birth_date": "01/02/1990",
        "admission_date": "01/10/2026",
        "role_code": "12",
        "salary_cents": 250000,
        "salary_type": "Mensal",
        "category": "Empregado",
        "bond": "CLT",
        "admission_type": "Primeiro emprego",
        "sex": "M",
        "nationality": "Brasileira",
        "service_code": "1",
        "union_code": "2",
        "agreement_code": "3",
        "schedule_code": "4",
        "department_code": "5",
        "cost_center_code": "6",
        "has_children": "NAO",
        "transport_voucher": "NAO",
        "dependents": [],
        "transports": [],
    }
    return {**base, **over}


def _ready(org: Organization, code: str = "10", **over: Any) -> tuple[Admission, User]:
    user = _user(org)
    admission = services.create(organization=org, user=user, company=_company(org, code))
    assert services.save_review(admission, user=user, data=_data(**over)) == []
    return admission, user


def _claim(org: Organization) -> tuple[RpaJob, str] | None:
    return rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND])


def test_cpf_validation() -> None:
    assert services.valid_cpf(CPF) and services.valid_cpf("529.982.247-25")
    assert not services.valid_cpf("52998224724") and not services.valid_cpf("11111111111")


def test_validation_reports_field_names_never_values() -> None:
    problems = services.validate_data({"cpf": "123", "name": "Segredo Silva"}, example=True)
    assert "CPF" in problems and "Cargo" in problems
    assert all("Segredo" not in p and "123" not in p for p in problems)
    real = services.validate_data(_data(department_code="", cost_center_code=""), example=False)
    assert real == ["Centro de custo", "Departamento"]
    assert (
        services.validate_data(_data(department_code="", cost_center_code=""), example=True) == []
    )


def test_group_rules() -> None:
    kid = {"cpf": CPF_DEP, "birth_date": "05/05/2015", "name": "Filho"}
    assert services.validate_data(_data(has_children="SIM", dependents=[kid]), example=False) == []
    assert services.validate_data(_data(has_children="SIM", dependents=[]), example=False) == [
        "Dependentes"
    ]
    assert services.validate_data(_data(dependents=[kid]), example=False) == ["Dependentes"]
    for bad in ({**kid, "cpf": CPF}, {**kid, "cpf": "1"}, {**kid, "birth_date": "01/01/2030"}):
        assert services.validate_data(
            _data(has_children="SIM", dependents=[bad]), example=False
        ) == ["Dependentes"]
    twin = [kid, kid]
    assert services.validate_data(_data(has_children="SIM", dependents=twin), example=False) == [
        "Dependentes"
    ]


def test_data_is_encrypted_at_rest_and_unknown_keys_dropped() -> None:
    org = _office()
    admission, _ = _ready(org, extra_key="x")
    admission.refresh_from_db()
    raw = Admission.objects.filter(pk=admission.pk).values_list("data_json", flat=True).get()
    assert "Fulano" in admission.data["name"] and "extra_key" not in admission.data
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("select data_json from admissions_admission")
        stored = cursor.fetchone()[0]
    assert "Fulano" not in stored and CPF not in stored and raw


def test_execute_needs_every_lock() -> None:
    org = _office(enabled=False)
    admission, user = _ready(org)
    with pytest.raises(services.AdmissionError, match="desligada"):
        services.execute(admission, user=user, example_confirmed=False)
    cfg = services.settings_for(org)
    cfg.execution_enabled, cfg.allowed_codes = True, []
    cfg.save()
    with pytest.raises(services.AdmissionError, match="lista autorizada"):
        services.execute(admission, user=user, example_confirmed=False)
    cfg.allowed_codes = ["10"]
    cfg.save()
    admission.reviewed_by = None
    admission.save()
    with pytest.raises(services.AdmissionError, match="revisão humana"):
        services.execute(admission, user=user, example_confirmed=False)
    assert not RpaJob.objects.exists()


def test_incomplete_sheet_cannot_execute() -> None:
    org = _office()
    user = _user(org)
    admission = services.create(organization=org, user=user, company=_company(org))
    services.save_review(admission, user=user, data=_data(role_code=""))
    with pytest.raises(services.AdmissionError, match="Cargo"):
        services.execute(admission, user=user, example_confirmed=False)


def test_example_company_needs_test_confirmation() -> None:
    org = _office()
    admission, user = _ready(org, code="9996", department_code="", cost_center_code="")
    with pytest.raises(services.AdmissionError, match="confirmação de teste"):
        services.execute(admission, user=user, example_confirmed=False)
    services.execute(admission, user=user, example_confirmed=True)
    assert Admission.objects.get().state == Admission.State.QUEUED


def test_pii_travels_only_in_claim_response_never_stored_in_job() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    job = RpaJob.objects.get()
    assert CPF not in str(job.payload) and "Fulano" not in str(job.payload)
    claimed = _claim(org)
    assert claimed is not None
    delivered, _ = claimed
    assert delivered.payload["data"]["cpf"] == CPF  # o agente recebe a ficha...
    job.refresh_from_db()
    assert "data" not in job.payload and CPF not in str(job.payload)  # ...e o banco não guarda
    assert Admission.objects.get().state == Admission.State.RUNNING


def test_duplicate_cpf_in_same_company_is_blocked_even_across_sheets() -> None:
    org = _office()
    first, user = _ready(org)
    services.execute(first, user=user, example_confirmed=False)
    second = services.create(organization=org, user=user, company=first.company)
    services.save_review(second, user=user, data=_data())
    with pytest.raises(services.AdmissionError, match="Já existe"):
        services.execute(second, user=user, example_confirmed=False)
    other_company = _company(org, "9996")
    third = services.create(organization=org, user=user, company=other_company)
    services.save_review(third, user=user, data=_data())
    assert third.cpf_hash == first.cpf_hash


def test_lock_dropped_before_delivery_blocks_and_returns_sheet_to_review() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    cfg = services.settings_for(org)
    cfg.execution_enabled = False
    cfg.save()
    assert _claim(org) is None
    admission.refresh_from_db()
    assert admission.state == Admission.State.REVIEW


def test_success_failure_and_divergence_paths() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    job, token = _claim(org)  # type: ignore[misc]
    kwargs: dict[str, Any] = {
        "job_id": job.pk,
        "organization": org,
        "agent_id": "ag",
        "token": token,
    }
    with pytest.raises(Exception, match="código"):
        rpa.complete(**kwargs, result={"divergences": []})
    rpa.complete(**kwargs, result={"domain_code": "1234", "checks_ok": 78, "divergences": []})
    admission.refresh_from_db()
    assert admission.state == Admission.State.DONE and admission.domain_code == "1234"

    org2 = _office("dois")
    a2, u2 = _ready(org2)
    services.execute(a2, user=u2, example_confirmed=False)
    j2, t2 = _claim(org2)  # type: ignore[misc]
    rpa.complete(
        job_id=j2.pk,
        organization=org2,
        agent_id="ag",
        token=t2,
        result={"domain_code": "55", "divergences": ["Salário"]},
    )
    a2.refresh_from_db()
    assert a2.state == Admission.State.UNCERTAIN and "Salário" in a2.error

    org3 = _office("tres")
    a3, u3 = _ready(org3)
    services.execute(a3, user=u3, example_confirmed=False)
    j3, t3 = _claim(org3)  # type: ignore[misc]
    rpa.fail(
        job_id=j3.pk,
        organization=org3,
        agent_id="ag",
        token=t3,
        code="portal_indisponivel",
        detail=f"Domínio fechou ao abrir o cadastro de {CPF}",
    )
    a3.refresh_from_db()
    assert a3.state == Admission.State.FAILED and CPF not in a3.error


def test_failure_after_write_phase_is_uncertain_and_never_requeued() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    job, token = _claim(org)  # type: ignore[misc]
    kwargs: dict[str, Any] = {
        "job_id": job.pk,
        "organization": org,
        "agent_id": "ag",
        "token": token,
    }
    rpa.heartbeat(**kwargs, phase="gravando")
    rpa.fail(**kwargs, code="agent_error", detail="janela fechou")
    admission.refresh_from_db()
    assert admission.state == Admission.State.UNCERTAIN
    assert _claim(org) is None
    with pytest.raises(services.AdmissionError):
        services.resolve_uncertain(
            admission, user=user, registered=True, domain_code="x", note="ok"
        )
    services.resolve_uncertain(
        admission, user=user, registered=True, domain_code="777", note="achei no cadastro"
    )
    admission.refresh_from_db()
    assert admission.state == Admission.State.DONE and admission.domain_code == "777"


def test_agent_dying_after_write_phase_is_uncertain() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    job, token = _claim(org)  # type: ignore[misc]
    rpa.heartbeat(job_id=job.pk, organization=org, agent_id="ag", token=token, phase="gravando")
    rpa.release_expired(org, now=timezone.now() + timedelta(hours=3))
    admission.refresh_from_db()
    assert admission.state == Admission.State.UNCERTAIN and _claim(org) is None


def test_retention_wipes_personal_data_after_90_days(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    user = _user(org)
    admission = services.create(
        organization=org,
        user=user,
        company=_company(org),
        upload=b"%PDF-1.4 ficha",
        original_name="ficha.pdf",
    )
    services.save_review(admission, user=user, data=_data())
    assert admission.file and services.expire(now=timezone.now()) == 0
    assert services.expire(now=timezone.now() + timedelta(days=91)) == 1
    admission.refresh_from_db()
    assert admission.state == Admission.State.EXPIRED and admission.data == {}
    assert not admission.file and admission.cpf_hash == "" and admission.original_name == ""
    assert services.expire(now=timezone.now() + timedelta(days=200)) == 0


def test_cancel_only_before_execution() -> None:
    org = _office()
    admission, user = _ready(org)
    services.execute(admission, user=user, example_confirmed=False)
    services.cancel(admission, user=user)
    assert RpaJob.objects.get().state == RpaJob.State.CANCELLED
    with pytest.raises(services.AdmissionError):
        services.cancel(admission, user=user)


def test_upload_limit_and_foreign_company() -> None:
    org = _office()
    user = _user(org)
    with pytest.raises(services.AdmissionError, match="15 MB"):
        services.create(
            organization=org,
            user=user,
            company=_company(org),
            upload=b"x" * (services.MAX_UPLOAD + 1),
        )
    with pytest.raises(services.AdmissionError, match="outro escritório"):
        services.create(organization=org, user=user, company=_company(_office("b")))


def _client(org: Organization, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client


def test_pages_gate_form_flow_and_isolation() -> None:
    off = _office("off", on=False)
    assert _client(off, _user(off)).get("/app/admissoes/").status_code == 403
    org = _office()
    owner = _client(org, _user(org))
    company = _company(org)
    assert owner.get("/app/admissoes/").status_code == 200
    created = owner.post("/app/admissoes/nova/", {"empresa": company.pk})
    assert created.status_code == 302
    admission = Admission.objects.get()
    assert owner.get(created["Location"]).status_code == 200
    saved = owner.post(
        f"/app/admissoes/{admission.pk}/acao/",
        {"acao": "salvar", "name": "Fulano", "cpf": CPF, "salary": "2.500,00"},
        follow=True,
    )
    assert "Falta" in saved.content.decode()
    admission.refresh_from_db()
    assert admission.data["salary_cents"] == 250000 and admission.cpf_hash
    stranger_org = _office("b")
    stranger = _client(stranger_org, _user(stranger_org))
    assert stranger.get(f"/app/admissoes/{admission.pk}/").status_code == 404
    assert (
        stranger.post(f"/app/admissoes/{admission.pk}/acao/", {"acao": "cancelar"}).status_code
        == 404
    )
    reader = _client(org, _user(org, "auditor"))
    reader.post(f"/app/admissoes/{admission.pk}/acao/", {"acao": "cancelar"})
    admission.refresh_from_db()
    assert admission.state == Admission.State.REVIEW
