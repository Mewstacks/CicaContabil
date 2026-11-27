"""FAP: travas do escritório, cadastro, PDF validado pelo servidor, pausa e reprocesso."""

from __future__ import annotations

import hashlib
import io
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client
from reportlab.pdfgen import canvas

from apps.accounts.models import User
from apps.fap import services
from apps.fap.models import FapBatch, FapItem
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob

pytestmark = pytest.mark.django_db
CNPJ_A = "11222333000181"
CNPJ_B = "11444777000161"


def _pdf(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    for index, line in enumerate(lines):
        page.drawString(40, 800 - 18 * index, line)
    page.save()
    return buffer.getvalue()


def _official(cnpj: str = CNPJ_A, year: int = 2027) -> bytes:
    masked = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return _pdf(
        [
            "Resultado da Consulta FAP",
            "DADOS DO ESTABELECIMENTO",
            f"CNPJ: {masked}",
            "DADOS DO FAP",
            f"Vigencia: {year}",
        ]
    )


def _office(
    slug: str = "fed", *, on: bool = True, enabled: bool = True, portal: bool = True
) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="fap", enabled=on)
    cfg = services.settings_for(org)
    cfg.enabled, cfg.portal_validated, cfg.batch_limit = enabled, portal, 3
    cfg.save()
    return org


def _user(org: Organization, role: str = "owner") -> User:
    user = User.objects.create_user(
        email=f"{role}-{uuid4().hex[:8]}@{org.slug}.test", password="uma-senha-longa"
    )
    Membership.objects.create(organization=org, user=user, role=role)
    return user


def _company(org: Organization, code: str, cnpj: str = CNPJ_A) -> ClientCompany:
    masked = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return ClientCompany.objects.create(
        organization=org, name=f"Empresa {code}", dominio_code=code, cnpj_masked=masked
    )


def _claim(org: Organization) -> tuple[RpaJob, str] | None:
    return rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND])


def _answer(
    org: Organization, status: str = "ok", pdf: bytes | None = None, tmp: Any = None
) -> RpaJob:
    claimed = _claim(org)
    assert claimed is not None
    job, token = claimed
    common: dict[str, Any] = {
        "job_id": job.pk,
        "organization": org,
        "agent_id": "ag",
        "token": token,
    }
    result: dict[str, Any] = {"status": status}
    if pdf is not None:
        sha = hashlib.sha256(pdf).hexdigest()
        rpa.attach_artifact(**common, name="fap.pdf", content=pdf, claimed_sha256=sha)
        result["sha256"] = sha
    rpa.complete(**common, result=result)
    return job


def test_cnpj_check_digit() -> None:
    assert services.valid_cnpj(CNPJ_A) and services.valid_cnpj(CNPJ_B)
    assert not services.valid_cnpj("11222333000180") and not services.valid_cnpj("1" * 14)
    assert not services.valid_cnpj("12ABC345000195")  # alfanumérico ainda não suportado


def test_batch_needs_enabled_and_respects_limit_and_foreign_company() -> None:
    off = _office("off", enabled=False)
    with pytest.raises(services.FapError, match="liberado"):
        services.create_batch(
            organization=off, user=_user(off), year=2027, companies=[_company(off, "1")]
        )
    org = _office()
    companies = [_company(org, str(i), CNPJ_A) for i in range(4)]
    with pytest.raises(services.FapError, match="no máximo 3"):
        services.create_batch(organization=org, user=_user(org), year=2027, companies=companies)
    other = _office("b")
    with pytest.raises(services.FapError, match="outro escritório"):
        services.create_batch(
            organization=org, user=_user(org), year=2027, companies=[_company(other, "9")]
        )


def test_registry_problems_are_not_executable() -> None:
    org = _office()
    bad = _company(org, "1", "11222333000180")
    dup1, dup2 = _company(org, "2", CNPJ_B), _company(org, "3", CNPJ_B)
    ok = _company(org, "4", CNPJ_A)
    batch = services.create_batch(
        organization=org, user=_user(org), year=2027, companies=[bad, dup1, dup2][:3]
    )
    assert set(batch.items.values_list("state", flat=True)) == {"registry"}
    assert not RpaJob.objects.exists()
    batch2 = services.create_batch(organization=org, user=_user(org), year=2027, companies=[ok])
    assert batch2.items.get().state == "pending" and RpaJob.objects.count() == 1


def test_happy_path_validates_pdf_on_the_server(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    batch = services.create_batch(
        organization=org, user=_user(org), year=2027, companies=[_company(org, "1")]
    )
    _answer(org, pdf=_official())
    item = batch.items.get()
    batch.refresh_from_db()
    assert (
        item.state == FapItem.State.DONE
        and item.validated_at
        and batch.state == FapBatch.State.DONE
    )


@pytest.mark.parametrize(
    "pdf",
    [
        _official(CNPJ_B),  # PDF de outra empresa
        _official(CNPJ_A, 2026),  # outra vigência
        _pdf(["Documento qualquer", "CNPJ: 11.222.333/0001-81", "Vigencia: 2027"]),
        b"%PDF-1.4 quebrado",
    ],
)
def test_wrong_pdf_goes_to_review_never_done(pdf: bytes, tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    batch = services.create_batch(
        organization=org, user=_user(org), year=2027, companies=[_company(org, "1")]
    )
    _answer(org, pdf=pdf)
    item = batch.items.get()
    assert item.state == FapItem.State.REVIEW and item.message
    batch.refresh_from_db()
    assert batch.state == FapBatch.State.ATTENTION


def test_missing_pdf_is_refused_and_portal_outcomes_map_to_states() -> None:
    org = _office()
    batch = services.create_batch(
        organization=org, user=_user(org), year=2027, companies=[_company(org, "1")]
    )
    claimed = _claim(org)
    assert claimed is not None
    with pytest.raises(Exception, match=r"sha256|Hash"):
        rpa.complete(
            job_id=claimed[0].pk,
            organization=org,
            agent_id="ag",
            token=claimed[1],
            result={"status": "ok"},
        )
    rpa.complete(
        job_id=claimed[0].pk,
        organization=org,
        agent_id="ag",
        token=claimed[1],
        result={"status": "root_missing", "message": "raiz não listada"},
    )
    assert batch.items.get().state == FapItem.State.ROOT_MISSING


@pytest.mark.parametrize("which", ["enabled", "portal"])
def test_locks_are_rechecked_when_agent_claims(which: str) -> None:
    org = _office()
    batch = services.create_batch(
        organization=org, user=_user(org), year=2027, companies=[_company(org, "1")]
    )
    cfg = services.settings_for(org)
    if which == "enabled":
        cfg.enabled = False
    else:
        cfg.portal_validated = False
    cfg.save()
    assert _claim(org) is None
    item = batch.items.get()
    assert item.state == FapItem.State.PENDING  # nada foi consultado
    assert RpaJob.objects.get().error_code == "bloqueado_por_trava"


def test_pause_cancels_queue_and_resume_requeues() -> None:
    org = _office()
    user = _user(org)
    batch = services.create_batch(
        organization=org,
        user=user,
        year=2027,
        companies=[_company(org, "1"), _company(org, "2", CNPJ_B)],
    )
    services.pause(batch, user=user)
    assert _claim(org) is None
    assert RpaJob.objects.filter(state=RpaJob.State.CANCELLED).count() == 2
    assert services.resume(batch, user=user) == 2
    assert _claim(org) is not None
    with pytest.raises(services.FapError):
        services.resume(batch, user=user)


def test_reprocess_needs_reason_and_keeps_previous_pdf(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    user = _user(org)
    batch = services.create_batch(
        organization=org, user=user, year=2027, companies=[_company(org, "1")]
    )
    _answer(org, pdf=_official(CNPJ_B))
    item = batch.items.get()
    first_pdf = item.pdf_id
    with pytest.raises(services.FapError):
        services.reprocess(item, user=user, reason=" ")
    services.reprocess(item, user=user, reason="PDF era de outra empresa")
    item.refresh_from_db()
    assert item.state == FapItem.State.PENDING and item.generation == 2 and item.pdf_id == first_pdf
    _answer(org, pdf=_official())
    item.refresh_from_db()
    assert item.state == FapItem.State.DONE


def test_one_live_query_per_cnpj_and_year() -> None:
    org = _office()
    user = _user(org)
    services.create_batch(organization=org, user=user, year=2027, companies=[_company(org, "1")])
    with pytest.raises(services.FapError, match="em andamento"):
        services.create_batch(
            organization=org, user=user, year=2027, companies=[_company(org, "2")]
        )
    services.create_batch(organization=org, user=user, year=2028, companies=[_company(org, "3")])


def _client(org: Organization, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client


def test_pages_pdf_download_and_isolation(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    off = _office("off", on=False)
    assert _client(off, _user(off)).get("/app/fap/").status_code == 403
    org = _office()
    owner = _client(org, _user(org))
    company = _company(org, "1")
    response = owner.post("/app/fap/lotes/novo/", {"vigencia": "2027", "empresas": [company.pk]})
    assert response.status_code == 302 and owner.get(response["Location"]).status_code == 200
    _answer(org, pdf=_official())
    item = FapItem.objects.get()
    download = owner.get(f"/app/fap/itens/{item.pk}/arquivo/")
    assert download.status_code == 200 and download["Cache-Control"] == "private, no-store"
    assert download["X-CICA-Content-SHA256"] == item.sha256
    other = _office("b")
    stranger = _client(other, _user(other))
    assert stranger.get(f"/app/fap/itens/{item.pk}/arquivo/").status_code == 404
    assert stranger.get(f"/app/fap/lotes/{item.batch_id}/").status_code == 404


def test_only_admin_changes_locks() -> None:
    org = _office(enabled=False, portal=False)
    operator = _client(org, _user(org, "operator"))
    operator.post("/app/fap/configuracao/", {"liberado": "sim", "portal_validado": "sim"})
    cfg = services.settings_for(org)
    assert not cfg.enabled and not cfg.portal_validated
    owner = _client(org, _user(org))
    owner.post(
        "/app/fap/configuracao/", {"liberado": "sim", "portal_validado": "sim", "teto": "10"}
    )
    cfg.refresh_from_db()
    assert cfg.enabled and cfg.portal_validated and cfg.batch_limit == 10
