"""FGTS Digital: conferir antes de emitir, três travas, incerto nunca repete sozinho."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.fgts import services
from apps.fgts.models import FgtsItem, FgtsSource
from apps.hub.models import ProductModule
from apps.organizations.models import Membership, Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob

pytestmark = pytest.mark.django_db
PDF = b"%PDF-1.4 " + b"x" * 600


def _office(slug: str = "fed", *, on: bool = True) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="fgts", enabled=on)
    return org


def _user(org: Organization, role: str = "owner") -> User:
    user = User.objects.create_user(
        email=f"{role}-{uuid4().hex[:8]}@{org.slug}.test", password="uma-senha-longa"
    )
    Membership.objects.create(organization=org, user=user, role=role)
    return user


def _source(org: Organization, *, cents: int = 12345) -> None:
    FgtsSource.objects.create(
        organization=org,
        year=2026,
        month=9,
        groups=[
            {
                "root": "11222333",
                "name": "ACME",
                "cnpj": "11222333000181",
                "codes": ["10"],
                "amount_cents": cents,
            },
            {
                "root": "44555666",
                "name": "BETA",
                "cnpj": "44555666000100",
                "codes": ["20"],
                "amount_cents": 500,
            },
        ],
    )


def _claim(org: Organization, kind: str) -> tuple[RpaJob, str]:
    claimed = rpa.claim_next(organization=org, agent_id="ag", kinds=[kind])
    assert claimed is not None
    return claimed


def _complete(job: RpaJob, token: str, org: Organization, result: dict[str, Any]) -> RpaJob:
    return rpa.complete(job_id=job.pk, organization=org, agent_id="ag", token=token, result=result)


def _prepared_item(org: Organization, user: User, *, portal: int = 12345) -> FgtsItem:
    _source(org)
    batch = services.create_batch(
        organization=org,
        user=user,
        year=2026,
        month=9,
        deadline=date(2026, 10, 7),
        roots=["11222333"],
    )
    job, token = _claim(org, services.KIND_CHECK)
    _complete(job, token, org, {"portal_cents": portal, "portal_due": "2026-10-07"})
    return batch.items.get()


def _allow(org: Organization) -> None:
    cfg = services.settings_for(org)
    cfg.source_validated = cfg.emission_enabled = True
    cfg.save()


def test_source_result_validation_and_storage() -> None:
    org = _office()
    job = services.request_source(org, 2026, 9)
    assert job.state == RpaJob.State.LEASED or job.state == RpaJob.State.QUEUED
    claimed, token = _claim(org, services.KIND_SOURCE)
    with pytest.raises(Exception, match="inválido"):
        _complete(
            claimed, token, org, {"groups": [{"root": "123", "cnpj": "x", "amount_cents": 1}]}
        )
    ok = [
        {
            "root": "11222333",
            "name": "A",
            "cnpj": "11222333000181",
            "codes": ["10"],
            "amount_cents": 100,
        }
    ]
    _complete(claimed, token, org, {"groups": ok, "pendencies": ["CNPJ duplicado"]})
    src = services.latest_source(org, 2026, 9)
    assert src is not None and src.groups == ok and src.pendencies == ["CNPJ duplicado"]


def test_source_rejects_float_money_and_duplicate_roots() -> None:
    from apps.rpa.registry import RpaError

    base = {"root": "11222333", "cnpj": "11222333000181", "amount_cents": 1}
    for groups in (
        [{**base, "amount_cents": 1.5}],
        [{**base, "amount_cents": True}],
        [{**base, "amount_cents": -1}],
        [base, base],
    ):
        with pytest.raises(RpaError):
            services.validate_source_result({"groups": groups})


def test_batch_needs_source_and_blocks_duplicate_live_item() -> None:
    org = _office()
    user = _user(org)
    with pytest.raises(services.FgtsError):
        services.create_batch(
            organization=org,
            user=user,
            year=2026,
            month=9,
            deadline=date(2026, 10, 7),
            roots=["11222333"],
        )
    _source(org)
    services.create_batch(
        organization=org,
        user=user,
        year=2026,
        month=9,
        deadline=date(2026, 10, 7),
        roots=["11222333"],
    )
    with pytest.raises(services.FgtsError, match="Já existe"):
        services.create_batch(
            organization=org,
            user=user,
            year=2026,
            month=9,
            deadline=date(2026, 10, 7),
            roots=["11222333"],
        )
    with pytest.raises(services.FgtsError):
        services.create_batch(
            organization=org,
            user=user,
            year=2026,
            month=9,
            deadline=date(2026, 10, 7),
            roots=["99999999"],
        )


def test_server_decides_the_comparison_not_the_agent() -> None:
    org, user = _office(), None
    user = _user(org)
    item = _prepared_item(org, user)
    assert item.state == FgtsItem.State.PREPARED  # confere, mas nada foi emitido
    assert not RpaJob.objects.filter(kind=services.KIND_EMIT).exists()


def test_value_or_due_divergence_never_prepares() -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user, portal=12346)  # um centavo a mais
    assert item.state == FgtsItem.State.DIVERGENCE and "diverge" in item.message
    org2 = _office("late")
    user2 = _user(org2)
    _source(org2)
    batch = services.create_batch(
        organization=org2,
        user=user2,
        year=2026,
        month=9,
        deadline=date(2026, 10, 7),
        roots=["11222333"],
    )
    job, token = _claim(org2, services.KIND_CHECK)
    _complete(job, token, org2, {"portal_cents": 12345, "portal_due": "2026-10-08"})
    assert batch.items.get().state == FgtsItem.State.DIVERGENCE


@pytest.mark.parametrize(
    "flag,source,emission", [(False, True, True), (True, False, True), (True, True, False)]
)
def test_emission_needs_all_three_locks(flag: bool, source: bool, emission: bool) -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    cfg = services.settings_for(org)
    cfg.source_validated, cfg.emission_enabled = source, emission
    cfg.save()
    with override_settings(FGTS_EMISSAO_HABILITADA=flag), pytest.raises(services.FgtsError):
        services.request_emission(item, user=user)
    assert not RpaJob.objects.filter(kind=services.KIND_EMIT).exists()


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_emission_flow_success_goes_to_review_with_pdf(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    job, token = _claim(org, services.KIND_EMIT)
    assert job.payload["emit_allowed"] is True and job.max_attempts == 1
    rpa.heartbeat(job_id=job.pk, organization=org, agent_id="ag", token=token, phase="emissao")
    sha = hashlib.sha256(PDF).hexdigest()
    rpa.attach_artifact(
        job_id=job.pk,
        organization=org,
        agent_id="ag",
        token=token,
        name="g.pdf",
        content=PDF,
        claimed_sha256=sha,
    )
    _complete(job, token, org, {"portal_cents": 12345, "portal_due": "2026-10-07", "sha256": sha})
    item.refresh_from_db()
    assert item.state == FgtsItem.State.REVIEW and item.sha256 == sha and item.pdf is not None
    services.mark_reviewed(item, user=user)


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_flag_flipped_off_after_request_blocks_at_delivery() -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    cfg = services.settings_for(org)
    cfg.emission_enabled = False  # alguém desligou entre o pedido e a entrega ao agente
    cfg.save()
    assert rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND_EMIT]) is None
    item.refresh_from_db()
    job = RpaJob.objects.get(kind=services.KIND_EMIT)
    assert job.state == RpaJob.State.FAILED and job.error_code == "bloqueado_por_trava"
    assert item.state == FgtsItem.State.PREPARED


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_portal_changed_after_check_blocks_emission() -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    FgtsItem.objects.filter(pk=item.pk).update(portal_cents=1)  # estado inconsistente
    assert rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND_EMIT]) is None


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_agent_dying_after_click_is_uncertain_never_repeated() -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    job, token = _claim(org, services.KIND_EMIT)
    rpa.heartbeat(job_id=job.pk, organization=org, agent_id="ag", token=token, phase="emissao")
    rpa.release_expired(org, now=timezone.now() + timedelta(hours=2))
    item.refresh_from_db()
    assert item.state == FgtsItem.State.UNCERTAIN
    assert rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND_EMIT]) is None
    with pytest.raises(services.FgtsError):
        services.request_emission(item, user=user)  # não está conferido: incerto bloqueia
    other = _user(org, "operator")
    with pytest.raises(services.FgtsError):
        services.resolve_uncertain(item, user=other, issued=False, note=" ")
    services.resolve_uncertain(item, user=other, issued=False, note="portal sem guia")
    item.refresh_from_db()
    assert item.state == FgtsItem.State.FAILED
    # a raiz volta a poder entrar em novo lote só depois dessa decisão
    services.create_batch(
        organization=org,
        user=user,
        year=2026,
        month=9,
        deadline=date(2026, 10, 7),
        roots=["11222333"],
    )


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_uncertain_with_guide_requires_real_pdf(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    job, token = _claim(org, services.KIND_EMIT)
    rpa.heartbeat(job_id=job.pk, organization=org, agent_id="ag", token=token, phase="emissao")
    rpa.release_expired(org, now=timezone.now() + timedelta(hours=2))
    item.refresh_from_db()
    with pytest.raises(services.FgtsError):
        services.resolve_uncertain(item, user=user, issued=True, note="há guia", pdf=b"nao e pdf")
    services.resolve_uncertain(item, user=user, issued=True, note="há guia", pdf=PDF)
    item.refresh_from_db()
    assert item.state == FgtsItem.State.REVIEW and item.sha256 == hashlib.sha256(PDF).hexdigest()


@override_settings(FGTS_EMISSAO_HABILITADA=True)
def test_emit_result_with_wrong_value_is_flagged_not_trusted(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    _allow(org)
    services.request_emission(item, user=user)
    job, token = _claim(org, services.KIND_EMIT)
    sha = hashlib.sha256(PDF).hexdigest()
    rpa.attach_artifact(
        job_id=job.pk,
        organization=org,
        agent_id="ag",
        token=token,
        name="g.pdf",
        content=PDF,
        claimed_sha256=sha,
    )
    _complete(job, token, org, {"portal_cents": 99999, "portal_due": "2026-10-07", "sha256": sha})
    item.refresh_from_db()
    assert "diverg" in item.message
    with pytest.raises(services.FgtsError):
        services.mark_reviewed(item, user=user)


def test_office_with_module_off_cannot_queue() -> None:
    org = _office(on=False)
    with pytest.raises(Exception, match="módulo"):
        services.request_source(org, 2026, 9)


def test_cents_filter() -> None:
    from apps.rpa.templatetags.rpa_format import cents

    assert cents(123456) == "1.234,56" and cents(5) == "0,05" and cents(None) == "—"
    assert cents(-250) == "-2,50" and cents(True) == "—"


def _client(org: Organization, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client


def test_pages_closed_when_off_and_render_when_on() -> None:
    off = _office("off", on=False)
    assert _client(off, _user(off)).get("/app/fgts/").status_code == 403
    org = _office()
    _source(org)
    client = _client(org, _user(org))
    page = client.get("/app/fgts/?mes=2026-09")
    html = page.content.decode()
    assert page.status_code == 200 and "ACME" in html and "123,45" in html
    assert "Emissão bloqueada" in html


def test_emit_button_is_disabled_and_post_is_refused_without_locks() -> None:
    org = _office()
    user = _user(org)
    item = _prepared_item(org, user)
    client = _client(org, user)
    html = client.get("/app/fgts/?mes=2026-09").content.decode()
    assert "disabled" in html
    client.post(f"/app/fgts/itens/{item.pk}/", {"acao": "emitir"})
    assert not RpaJob.objects.filter(kind=services.KIND_EMIT).exists()


def test_other_office_item_is_404_and_member_cannot_write() -> None:
    a, b = _office("a"), _office("b")
    item = _prepared_item(a, _user(a))
    assert (
        _client(b, _user(b)).post(f"/app/fgts/itens/{item.pk}/", {"acao": "emitir"}).status_code
        == 404
    )
    reader = _client(a, _user(a, "auditor"))
    reader.post(f"/app/fgts/itens/{item.pk}/", {"acao": "emitir"})
    assert not RpaJob.objects.filter(kind=services.KIND_EMIT).exists()
