"""Blocos RPA por escritório: ligados só por decisão, nunca por padrão nem por autosserviço."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.folha import services as folha
from apps.folha.models import FolhaCycle
from apps.folha.tasks import schedule_daily
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import OFFERED_MODULE_CODES, self_service_module_codes
from apps.organizations.models import Membership, Organization
from apps.rpa import registry
from apps.rpa.tasks import release_expired

pytestmark = pytest.mark.django_db
RPA_MODULES = ("folha", "fgts", "det", "fap", "admissions")


def test_rpa_modules_are_offered_but_never_self_service() -> None:
    for code in RPA_MODULES:
        assert code in OFFERED_MODULE_CODES
        assert code not in self_service_module_codes()


def test_provision_office_turns_them_on_only_for_that_office() -> None:
    other = Organization.objects.create(name="Outro", slug="outro")
    call_command(
        "provision_office",
        name="Fedrizzi Contabilidade",
        slug="fedrizzi-contabilidade",
        owner_email="dono@fedrizzi.test",
    )
    fed = Organization.objects.get(slug="fedrizzi-contabilidade")
    enabled = set(
        ProductModule.objects.filter(organization=fed, enabled=True).values_list("code", flat=True)
    )
    assert set(RPA_MODULES) <= enabled
    assert not ProductModule.objects.filter(organization=other).exists()


def test_every_kind_belongs_to_an_rpa_module_and_desktop_kinds_share_one_group() -> None:
    kinds = {k.code: k for k in registry.kinds() if not k.code.startswith("teste.")}
    assert set(kinds) >= {
        "folha.relatorio",
        "folha.contatos",
        "fgts.fonte",
        "fgts.conferir",
        "fgts.emitir",
        "det.consultar",
        "fap.consultar",
        "admissions.cadastrar",
    }
    for kind in kinds.values():
        assert kind.module_code in RPA_MODULES
    desktop = {c for c, k in kinds.items() if k.exclusive_group}
    assert {kinds[c].exclusive_group for c in desktop} == {"dominio_desktop"}
    # nada que emite ou grava admite segunda tentativa automática
    assert (
        kinds["fgts.emitir"].max_attempts == 1 and kinds["admissions.cadastrar"].max_attempts == 1
    )
    assert (
        kinds["fgts.emitir"].irreversible_phases
        and kinds["admissions.cadastrar"].irreversible_phases
    )


def test_daily_schedule_only_for_offices_with_the_module_on_and_only_drafts() -> None:
    on = Organization.objects.create(name="on", slug="on")
    off = Organization.objects.create(name="off", slug="off")
    for org, enabled in ((on, True), (off, False)):
        ProductModule.objects.create(organization=org, code="folha", enabled=enabled)
        company = ClientCompany.objects.create(organization=org, name="E", dominio_code="10")
        cfg = folha.settings_for(org)
        cfg.authorized_codes, cfg.schedule_codes = [company.dominio_code], ["10"]
        cfg.schedule_items, cfg.schedule_enabled, cfg.schedule_day = ["extrato"], True, 1
        cfg.save()
    assert schedule_daily() == 1
    cycle = FolhaCycle.objects.get()
    assert cycle.organization_id == on.pk and cycle.status == FolhaCycle.Status.DRAFT
    assert cycle.competence < date.today().replace(day=1)


def test_release_task_is_a_noop_when_agent_flag_is_off() -> None:
    assert release_expired() == 0
    with override_settings(RPA_AGENT_ENABLED=True):
        assert release_expired() == 0


# --- carteira: quem não é administrador só enxerga as empresas dos seus acessos ------------------


def _restricted(org: Organization) -> tuple[Any, ClientCompany, ClientCompany]:
    from uuid import uuid4

    from django.test import Client

    from apps.accounts.models import User
    from apps.hub.models import CompanyAccessGrant
    from apps.organizations.models import Membership

    mine = ClientCompany.objects.create(organization=org, name="Minha", dominio_code="1")
    theirs = ClientCompany.objects.create(organization=org, name="Alheia", dominio_code="2")
    user = User.objects.create_user(
        email=f"op-{uuid4().hex[:6]}@x.test", password="uma-senha-longa"
    )
    membership = Membership.objects.create(organization=org, user=user, role="operator")
    CompanyAccessGrant.objects.create(
        organization=org,
        membership=membership,
        company=mine,
        is_active=True,
        modules=["folha", "fgts", "det", "fap", "admissions"],
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client, mine, theirs


def test_operator_never_reaches_another_companys_rows() -> None:
    from apps.admissions import services as adm
    from apps.admissions.models import Admission
    from apps.fap.models import FapBatch, FapItem
    from apps.fgts.models import FgtsBatch, FgtsItem

    org = Organization.objects.create(name="fed", slug="fed")
    for code in RPA_MODULES:
        ProductModule.objects.create(organization=org, code=code, enabled=True)
    client, _mine, theirs = _restricted(org)
    owner_like = None
    admission = Admission.objects.create(organization=org, company=theirs, data_json="")
    fap_batch = FapBatch.objects.create(organization=org, year=2027)
    fap_item = FapItem.objects.create(
        organization=org, batch=fap_batch, company=theirs, code="2", name="Alheia", year=2027
    )
    fgts_batch = FgtsBatch.objects.create(
        organization=org, year=2026, month=9, deadline=date(2026, 10, 7)
    )
    fgts_item = FgtsItem.objects.create(
        organization=org,
        batch=fgts_batch,
        root="11222333",
        year=2026,
        month=9,
        company=theirs,
        expected_cents=1,
    )
    cycle = FolhaCycle.objects.create(organization=org, competence=date(2026, 9, 1))
    folha_task = cycle.tasks.create(
        organization=org, company=theirs, item="extrato", competence=date(2026, 9, 1)
    )
    assert owner_like is None and adm.settings_for(org)
    assert client.get(f"/app/admissoes/{admission.pk}/").status_code == 404
    assert client.get(f"/app/fap/lotes/{fap_batch.pk}/").status_code == 404
    assert client.get(f"/app/fap/itens/{fap_item.pk}/arquivo/").status_code == 404
    assert client.post(f"/app/fgts/itens/{fgts_item.pk}/", {"acao": "revisar"}).status_code == 404
    assert client.get(f"/app/folha/ciclos/{cycle.pk}/").status_code == 404
    assert folha_task.pk
    # controle positivo: o mesmo pedido, feito por quem é dono, abre
    Membership.objects.filter(organization=org).update(role="owner")
    assert client.get(f"/app/admissoes/{admission.pk}/").status_code == 200
    assert client.get(f"/app/fap/lotes/{fap_batch.pk}/").status_code == 200
    assert client.get(f"/app/folha/ciclos/{cycle.pk}/").status_code == 200


def test_operator_cannot_batch_foreign_groups_or_pause_mixed_batch() -> None:
    from apps.fap.models import FapBatch, FapItem
    from apps.fgts.models import FgtsItem, FgtsSource

    org = Organization.objects.create(name="fed2", slug="fed2")
    for code in RPA_MODULES:
        ProductModule.objects.create(organization=org, code=code, enabled=True)
    client, _mine, theirs = _restricted(org)
    Membership.objects.filter(organization=org).update(role="admin")
    Membership.objects.filter(organization=org).update(role="operator")
    FgtsSource.objects.create(
        organization=org,
        year=2026,
        month=9,
        groups=[
            {
                "root": "11222333",
                "name": "A",
                "cnpj": "11222333000181",
                "codes": ["2"],
                "amount_cents": 1,
            }
        ],
    )
    client.post(
        "/app/fgts/lotes/novo/",
        {"mes": "2026-09", "limite": "07/10/2026", "raizes": ["11222333"]},
    )
    assert not FgtsItem.objects.exists()
    batch = FapBatch.objects.create(organization=org, year=2027, state="queued")
    FapItem.objects.create(
        organization=org, batch=batch, company=theirs, code="2", name="x", year=2027
    )
    client.post(f"/app/fap/lotes/{batch.pk}/acao/", {"acao": "pausar"})
    batch.refresh_from_db()
    assert batch.state == "queued"


def test_fgts_group_needs_every_company_in_portfolio() -> None:
    from apps.fgts.views import _group_visible

    assert _group_visible({"codes": ["1"]}, {"1", "2"})
    assert not _group_visible({"codes": ["1", "3"]}, {"1", "2"})
    assert not _group_visible({"codes": []}, {"1"})
