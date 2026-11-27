"""Blocos RPA por escritório: ligados só por decisão, nunca por padrão nem por autosserviço."""

from __future__ import annotations

from datetime import date

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.folha import services as folha
from apps.folha.models import FolhaCycle
from apps.folha.tasks import schedule_daily
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import OFFERED_MODULE_CODES, self_service_module_codes
from apps.organizations.models import Organization
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
