"""Fila RPA: idempotência, escopo por escritório, reserva com token, fase irreversível."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.hub.models import ProductModule
from apps.organizations.models import Organization
from apps.rpa import registry, services
from apps.rpa.models import RpaJob
from apps.rpa.redaction import SecretInPayload, assert_no_secrets, redact_text
from apps.rpa.registry import RpaError, RpaKind

pytestmark = pytest.mark.django_db

KIND = "teste.rpa"
DESKTOP = "teste.desktop"
OTHER_DESKTOP = "teste.desktop2"
CALLS: list[str] = []


@pytest.fixture(autouse=True)
def kinds() -> None:
    CALLS.clear()
    registry._KINDS.pop(KIND, None)
    registry.register(
        RpaKind(
            code=KIND,
            module_code="folha",
            label="t",
            result_keys=frozenset({"ok", "n"}),
            on_success=lambda job: CALLS.append("success"),
            on_failure=lambda job: CALLS.append("failure"),
            on_uncertain=lambda job: CALLS.append("uncertain"),
            irreversible_phases=frozenset({"emitindo"}),
            lease_seconds=60,
            max_attempts=2,
        )
    )
    registry.register(RpaKind(code=DESKTOP, module_code="folha", label="d", exclusive_group="vm"))
    registry.register(
        RpaKind(code=OTHER_DESKTOP, module_code="folha", label="d2", exclusive_group="vm")
    )


def _office(slug: str, *, on: bool = True) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="folha", enabled=on)
    return org


def _claim(org: Organization, agent: str = "ag", kinds: list[str] | None = None) -> Any:
    claimed = services.claim_next(organization=org, agent_id=agent, kinds=kinds or [KIND])
    assert claimed is not None
    return claimed


def test_enqueue_is_idempotent_and_scoped() -> None:
    a, b = _office("a"), _office("b")
    one, created = services.enqueue(
        organization=a, kind=KIND, idempotency_key="k", payload={"x": 1}
    )
    again, created_again = services.enqueue(
        organization=a, kind=KIND, idempotency_key="k", payload={"x": 2}
    )
    other, _ = services.enqueue(organization=b, kind=KIND, idempotency_key="k")
    assert created and not created_again
    assert one.pk == again.pk and again.payload == {"x": 1}
    assert other.pk != one.pk


def test_module_off_refuses_enqueue_and_claim() -> None:
    off = _office("off", on=False)
    with pytest.raises(RpaError) as err:
        services.enqueue(organization=off, kind=KIND, idempotency_key="k")
    assert err.value.code == "modulo_desligado"
    job = RpaJob.objects.create(organization=off, kind=KIND, idempotency_key="k")
    assert services.claim_next(organization=off, agent_id="ag", kinds=[KIND]) is None
    job.refresh_from_db()
    assert job.state == RpaJob.State.QUEUED


def test_secrets_never_enter_payload_or_logs() -> None:
    org = _office("s")
    with pytest.raises(RpaError) as err:
        services.enqueue(organization=org, kind=KIND, idempotency_key="k", payload={"senha": "x"})
    assert err.value.code == "segredo_na_carga"
    with pytest.raises(SecretInPayload):
        assert_no_secrets({"a": [{"api_key": "x"}]})
    text = redact_text("falha senha=abc123 Bearer abcdefghijklmnop e " + "A" * 60)
    assert "abc123" not in text and "abcdefghijklmnop" not in text and "A" * 40 not in text


def test_claim_is_per_office_and_kind_filtered() -> None:
    a, b = _office("a"), _office("b")
    services.enqueue(organization=a, kind=KIND, idempotency_key="1")
    assert services.claim_next(organization=b, agent_id="ag", kinds=[KIND]) is None
    assert services.claim_next(organization=a, agent_id="ag", kinds=["nao.existe"]) is None
    job, token = _claim(a)
    assert job.state == RpaJob.State.LEASED and job.attempts == 1
    assert job.lease_token_hash != token and len(token) > 30


def test_exclusive_group_runs_one_at_a_time_per_office() -> None:
    org = _office("x")
    both = [DESKTOP, OTHER_DESKTOP]
    services.enqueue(organization=org, kind=DESKTOP, idempotency_key="1")
    services.enqueue(organization=org, kind=OTHER_DESKTOP, idempotency_key="2")
    first, token = _claim(org, kinds=both)
    assert services.claim_next(organization=org, agent_id="ag", kinds=both) is None
    services.complete(job_id=first.pk, organization=org, agent_id="ag", token=token, result={})
    assert services.claim_next(organization=org, agent_id="ag", kinds=both) is not None


def test_lost_lease_cannot_heartbeat_or_complete() -> None:
    org = _office("l")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, old = _claim(org, "ag1")
    later = timezone.now() + timedelta(seconds=120)
    assert services.release_expired(org, now=later) == 1
    again = services.claim_next(organization=org, agent_id="ag2", kinds=[KIND], now=later)
    assert again is not None
    with pytest.raises(RpaError) as err:
        services.heartbeat(job_id=job.pk, organization=org, agent_id="ag1", token=old)
    assert err.value.code == "nao_encontrado"
    with pytest.raises(RpaError) as err2:
        services.complete(job_id=job.pk, organization=org, agent_id="ag2", token=old, result={})
    assert err2.value.code == "reserva_perdida"


def test_complete_is_idempotent_and_drops_unknown_result_keys() -> None:
    org = _office("c")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, token = _claim(org)
    kwargs: dict[str, Any] = {
        "job_id": job.pk,
        "organization": org,
        "agent_id": "ag",
        "token": token,
    }
    done = services.complete(**kwargs, result={"ok": True, "n": 2, "extra": "x"})
    assert done.result == {"ok": True, "n": 2}
    services.complete(**kwargs, result={"ok": True, "n": 2})
    assert CALLS == ["success"]
    with pytest.raises(RpaError) as err:
        services.complete(**kwargs, result={"ok": False})
    assert err.value.code == "resultado_diferente"


def test_failure_retries_then_fails() -> None:
    org = _office("f")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, token = _claim(org)
    services.fail(
        job_id=job.pk,
        organization=org,
        agent_id="ag",
        token=token,
        code="portal_indisponivel",
        detail="senha=abc",
    )
    job.refresh_from_db()
    assert job.state == RpaJob.State.QUEUED and "abc" not in job.error_detail
    assert job.not_before and job.not_before > timezone.now()
    job.not_before = None
    job.save()
    job2, token2 = _claim(org)
    services.fail(
        job_id=job2.pk, organization=org, agent_id="ag", token=token2, code="portal_indisponivel"
    )
    job.refresh_from_db()
    assert job.state == RpaJob.State.FAILED and CALLS == ["failure"]
    retried = services.retry(job.pk, organization=org)
    assert retried.state == RpaJob.State.QUEUED and retried.attempts == 0


def test_permanent_failure_never_retries() -> None:
    org = _office("p")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, token = _claim(org)
    services.fail(
        job_id=job.pk, organization=org, agent_id="ag", token=token, code="conferencia_divergente"
    )
    job.refresh_from_db()
    assert job.state == RpaJob.State.FAILED


def test_irreversible_phase_expiry_goes_uncertain_never_requeued() -> None:
    org = _office("u")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, token = _claim(org)
    services.heartbeat(
        job_id=job.pk, organization=org, agent_id="ag", token=token, phase="emitindo"
    )
    services.release_expired(org, now=timezone.now() + timedelta(hours=1))
    job.refresh_from_db()
    assert job.state == RpaJob.State.UNCERTAIN and CALLS == ["uncertain"]
    assert services.claim_next(organization=org, agent_id="ag", kinds=[KIND]) is None
    with pytest.raises(RpaError):
        services.retry(job.pk, organization=org)
    reopened = services.resolve_uncertain(
        job.pk, organization=org, requeue=True, note="portal sem guia"
    )
    assert reopened.state == RpaJob.State.QUEUED


def test_artifact_hash_checked_and_deduplicated(tmp_path: Any, settings: Any) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office("art")
    services.enqueue(organization=org, kind=KIND, idempotency_key="1")
    job, token = _claim(org)
    kwargs: dict[str, Any] = {
        "job_id": job.pk,
        "organization": org,
        "agent_id": "ag",
        "token": token,
    }
    data = b"%PDF-1.4 teste"
    digest = hashlib.sha256(data).hexdigest()
    with pytest.raises(RpaError) as err:
        services.attach_artifact(**kwargs, name="a.pdf", content=data, claimed_sha256="0" * 64)
    assert err.value.code == "hash_diverge"
    one = services.attach_artifact(
        **kwargs, name="C:\\x\\a.pdf", content=data, claimed_sha256=digest
    )
    two = services.attach_artifact(**kwargs, name="a.pdf", content=data, claimed_sha256=digest)
    assert one.pk == two.pk and one.name == "a.pdf"


def test_api_is_404_when_flag_off(client: Any) -> None:
    response = client.post("/api/agent/v2/rpa/next", data={}, content_type="application/json")
    assert response.status_code == 404


@override_settings(RPA_AGENT_ENABLED=True)
def test_api_refuses_unauthenticated_agent(client: Any) -> None:
    response = client.post("/api/agent/v2/rpa/next", data={}, content_type="application/json")
    assert response.status_code == 401


# --- API assinada --------------------------------------------------------------------------


@override_settings(RPA_AGENT_ENABLED=True)
def test_signed_agent_full_cycle_and_isolation(tmp_path: Any, settings: Any) -> None:
    import base64

    from rpa_support import SignedAgent

    settings.MEDIA_ROOT = str(tmp_path)
    org, rival = _office("api"), _office("rival")
    services.enqueue(organization=rival, kind=KIND, idempotency_key="alheio")
    mine, _ = services.enqueue(organization=org, kind=KIND, idempotency_key="meu", payload={"n": 1})
    agent = SignedAgent(org)

    empty = agent.post("agent-v2-rpa-next", {"kinds": []})
    assert empty.status_code == 200 and empty.json()["job"] is None
    assert agent.post("agent-v2-rpa-next", {"kinds": "x"}).status_code == 400

    response = agent.post("agent-v2-rpa-next", {"kinds": [KIND]})
    job = response.json()["job"]
    assert response["Cache-Control"] == "no-store"
    assert job["id"] == str(mine.pk) and job["payload"] == {"n": 1}
    assert agent.post("agent-v2-rpa-next", {"kinds": [KIND]}).json()["job"] is None

    token = job["lease_token"]
    beat = agent.post("agent-v2-rpa-heartbeat", {"lease_token": token, "phase": "lendo"}, job["id"])
    assert beat.status_code == 200
    stale = agent.post("agent-v2-rpa-heartbeat", {"lease_token": "errado"}, job["id"])
    assert stale.status_code == 409 and stale.json()["code"] == "reserva_perdida"

    data = b"conteudo"
    sent = agent.post(
        "agent-v2-rpa-artifact",
        {
            "lease_token": token,
            "name": "r.pdf",
            "sha256": hashlib.sha256(data).hexdigest(),
            "content_base64": base64.b64encode(data).decode(),
        },
        job["id"],
    )
    assert sent.status_code == 200
    done = agent.post(
        "agent-v2-rpa-complete", {"lease_token": token, "result": {"ok": True}}, job["id"]
    )
    assert done.status_code == 200
    mine.refresh_from_db()
    assert mine.state == RpaJob.State.SUCCEEDED and mine.artifacts.count() == 1
    other = RpaJob.objects.get(organization=rival)
    assert other.state == RpaJob.State.QUEUED
    foreign = agent.post("agent-v2-rpa-heartbeat", {"lease_token": token}, str(other.pk))
    assert foreign.status_code == 404


def test_prepare_claim_refreshes_volatile_flags_or_blocks() -> None:
    state = {"allowed": True}

    def prepare(job: Any) -> dict[str, Any]:
        if not state["allowed"]:
            raise RpaError("trava", "emissão desligada")
        return {"emit_allowed": True}

    registry.register(
        RpaKind(code="teste.trava", module_code="folha", label="x", prepare_claim=prepare)
    )
    org = _office("trava")
    services.enqueue(organization=org, kind="teste.trava", idempotency_key="1")
    services.enqueue(organization=org, kind="teste.trava", idempotency_key="2")
    state["allowed"] = False
    assert services.claim_next(organization=org, agent_id="ag", kinds=["teste.trava"]) is None
    assert (
        RpaJob.objects.filter(state=RpaJob.State.FAILED, error_code="bloqueado_por_trava").count()
        == 2
    )
    state["allowed"] = True
    services.enqueue(organization=org, kind="teste.trava", idempotency_key="3")
    job, _ = _claim(org, kinds=["teste.trava"])
    assert job.payload["emit_allowed"] is True
