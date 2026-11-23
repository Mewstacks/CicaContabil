"""Limites do plano (E3): empresas, usuários e e-CNPJ. Sem limite configurado, nada muda."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ClientCompany, ImportBatch, OfficeCertificate, ProductModule
from apps.organizations.models import Membership, Organization
from apps.platform import limits
from apps.platform.models import Invitation, Plan, TenantContract
from test_company_roster import CSV_HEADER, NEW_A, NEW_B, NEW_C, csv_file
from test_nfse_procuracao import OFFICE_CNPJ, cnpj_from
from test_nfse_procuracao_views import World, login


def contract(
    organization: Organization,
    *,
    plan_limits: Any = None,
    status: str = TenantContract.Status.ACTIVE,
    code: str = "plano-limites",
) -> TenantContract:
    plan, _ = Plan.objects.get_or_create(
        code=code,
        defaults={"name": "Plano", "limits": plan_limits if plan_limits is not None else {}},
    )
    if plan_limits is not None and plan.limits != plan_limits:
        plan.limits = plan_limits
        plan.save(update_fields=["limits", "updated_at"])
    return TenantContract.objects.create(organization=organization, plan=plan, status=status)


# ---------------------------------------------------------------- leitura do plano


@pytest.mark.django_db
def test_an_office_without_contract_or_limits_has_no_limit_at_all() -> None:
    world = World()

    assert limits.plan_limits(world.office) == {}
    assert limits.room(world.office, limits.COMPANIES) is None
    assert limits.states(world.office) == []
    assert limits.notices(world.office) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"companies": 0},
        {"companies": -3},
        {"companies": "10"},
        {"companies": True},
        {"companies": None},
        {"companies": 2.5},
        [],
        "x",
    ],
)
def test_only_positive_integers_count_as_a_limit(raw: Any) -> None:
    world = World()
    contract(world.office, plan_limits=raw)

    assert limits.plan_limits(world.office) == {}


@pytest.mark.django_db
def test_the_current_contract_decides_and_archived_or_draft_ones_do_not() -> None:
    world = World()
    contract(
        world.office,
        plan_limits={"companies": 9},
        status=TenantContract.Status.ARCHIVED,
        code="velho",
    )
    contract(
        world.office,
        plan_limits={"companies": 8},
        status=TenantContract.Status.DRAFT,
        code="rascunho",
    )
    assert limits.plan_limits(world.office) == {}

    contract(world.office, plan_limits={"companies": 7, "users": 4}, code="vigente")

    assert limits.plan_limits(world.office) == {"companies": 7, "users": 4}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [TenantContract.Status.TRIAL, TenantContract.Status.ACTIVE, TenantContract.Status.GRACE],
)
def test_trial_active_and_grace_contracts_all_carry_the_plan_limits(status: str) -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 5}, status=status)

    assert limits.plan_limits(world.office) == {"companies": 5}


# ---------------------------------------------------------------- níveis e avisos


@pytest.mark.parametrize(
    ("used", "level", "percent"),
    [
        (0, "ok", 0),
        (7, "ok", 70),
        (8, "warn", 80),
        (9, "warn", 90),
        (10, "full", 100),
        (14, "full", 140),
    ],
)
def test_the_warning_starts_at_80_percent_and_full_at_100(
    used: int, level: str, percent: int
) -> None:
    state = limits.LimitState(key=limits.COMPANIES, limit=10, used=used)

    assert (state.level, state.percent) == (level, percent)
    assert (state.message == "") is (level == "ok")


def test_the_messages_name_the_measure_and_the_numbers() -> None:
    assert limits.LimitState(limits.COMPANIES, 10, 8).message == "Empresas: 8 de 10 do plano."
    assert limits.LimitState(limits.USERS, 3, 3).message == (
        "Usuários: limite do plano atingido (3 de 3)."
    )
    assert limits.LimitState(limits.COMPANIES, None, 99).message == ""
    assert limits.LimitState(limits.COMPANIES, None, 99).remaining is None


# ---------------------------------------------------------------- contagem


@pytest.mark.django_db
def test_companies_count_only_the_active_ones() -> None:
    world = World()
    world.oficina.active = False
    world.oficina.save(update_fields=["active"])

    assert limits.usage(world.office, limits.COMPANIES) == 2


@pytest.mark.django_db
def test_users_count_seats_and_pending_invitations_but_not_expired_or_revoked_ones() -> None:
    world = World()
    base = limits.usage(world.office, limits.USERS)
    assert base == 3  # dono, operador e auditor
    Membership.objects.filter(user=world.auditor).update(is_active=False)
    assert limits.usage(world.office, limits.USERS) == 2

    def invite(email: str, *, status: str, days: int) -> None:
        Invitation.objects.create(
            organization=world.office,
            email=email,
            role=Membership.Role.OPERATOR,
            token_digest=email,
            status=status,
            expires_at=timezone.now() + timedelta(days=days),
        )

    invite("pendente@example.test", status=Invitation.Status.PENDING, days=3)
    invite("vencido@example.test", status=Invitation.Status.PENDING, days=-1)
    invite("revogado@example.test", status=Invitation.Status.REVOKED, days=3)

    assert limits.usage(world.office, limits.USERS) == 3


@pytest.mark.django_db
def test_office_certificates_count_only_the_valid_unrevoked_ones() -> None:
    world = World()
    now = timezone.now()

    def cert(fingerprint: str, **extra: Any) -> None:
        fields: dict[str, Any] = {
            "organization": world.office,
            "label": "e-CNPJ",
            "cnpj": OFFICE_CNPJ,
            "valid_from": now - timedelta(days=10),
            "valid_until": now + timedelta(days=10),
            "fingerprint_sha256": fingerprint,
        }
        fields.update(extra)
        OfficeCertificate.objects.create(**fields)

    cert("a" * 64)
    cert("b" * 64, revoked_at=now)
    cert("c" * 64, valid_until=now - timedelta(days=1))

    assert limits.usage(world.office, limits.OFFICE_CERTIFICATES) == 1


@pytest.mark.django_db
def test_another_offices_records_never_count() -> None:
    world = World()
    stranger = Organization.objects.create(name="Vizinho", slug="vizinho-limites")
    ClientCompany.objects.create(organization=stranger, name="De outro", cnpj_masked=NEW_A)

    assert limits.usage(world.office, limits.COMPANIES) == 3


# ---------------------------------------------------------------- empresa cadastrada à mão


def add_company(client: Any, name: str, cnpj: str) -> Any:
    return client.post(reverse("hub:companies"), {"name": name, "cnpj_masked": cnpj}, follow=True)


@pytest.mark.django_db
def test_a_manual_company_is_refused_at_the_limit_and_allowed_below_it() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 4})
    client = login(world.owner, world.office)

    allowed = add_company(client, "Quarta", NEW_A)
    refused = add_company(client, "Quinta", NEW_B)

    assert ClientCompany.objects.filter(organization=world.office, name="Quarta").exists()
    assert not ClientCompany.objects.filter(organization=world.office, name="Quinta").exists()
    assert "Empresas: limite do plano atingido (4 de 4)." in refused.content.decode()
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_without_a_company_limit_the_manual_add_is_exactly_as_before() -> None:
    world = World()
    contract(world.office, plan_limits={"users": 9})  # só usuários têm limite
    client = login(world.owner, world.office)

    add_company(client, "Quarta", NEW_A)

    assert ClientCompany.objects.filter(organization=world.office, name="Quarta").exists()


@pytest.mark.django_db
def test_the_companies_page_warns_at_80_percent() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 4})  # 3 de 4 = 75%: sem aviso
    client = login(world.owner, world.office)
    assert "do plano" not in client.get(reverse("hub:companies")).content.decode()

    world.company("Quarta", NEW_A, "")  # 4 de 4

    assert (
        "limite do plano atingido (4 de 4)" in client.get(reverse("hub:companies")).content.decode()
    )


# ---------------------------------------------------------------- convite


def invite(client: Any, email: str, world: World) -> Any:
    return client.post(
        reverse("hub:team"),
        {
            "full_name": "Ana Fiscal",
            "email": email,
            "role": Membership.Role.OPERATOR,
            "modules": [ProductModule.Code.NFSE],
            "companies": [str(world.padaria.id)],
        },
    )


@pytest.mark.django_db
@patch("apps.hub.views.send_invitation_email")
def test_an_invitation_is_refused_when_the_users_limit_is_reached(send: Any) -> None:
    world = World()
    contract(world.office, plan_limits={"users": 3})  # dono, operador e auditor já ocupam 3
    client = login(world.owner, world.office)

    response = invite(client, "ana@example.test", world)

    assert response.status_code == 200
    assert "Usuários: limite do plano atingido (3 de 3)." in response.content.decode()
    assert not Invitation.objects.filter(email="ana@example.test").exists()
    send.assert_not_called()


@pytest.mark.django_db
@patch("apps.hub.views.send_invitation_email")
def test_an_invitation_goes_through_below_the_limit_and_takes_a_seat(send: Any) -> None:
    world = World()
    contract(world.office, plan_limits={"users": 4})
    client = login(world.owner, world.office)

    assert invite(client, "ana@example.test", world).status_code == 302
    assert Invitation.objects.filter(email="ana@example.test").exists()
    assert limits.usage(world.office, limits.USERS) == 4  # o convite pendente já ocupa vaga
    assert invite(client, "bia@example.test", world).status_code == 200  # a próxima não cabe


# ---------------------------------------------------------------- carteira por planilha


@pytest.mark.django_db
def test_the_roster_preview_and_confirmation_respect_the_company_limit() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 5})  # sobra 2 vagas
    client = login(world.owner, world.office)
    sent = client.post(
        reverse("hub:roster"),
        {
            "planilha": csv_file(
                CSV_HEADER + f"Um;{NEW_A};;\r\nDois;{NEW_B};;\r\nTrês;{NEW_C};;\r\n"
            )
        },
    )

    html = client.get(sent["Location"]).content.decode()
    assert "Limite de empresas do plano" in html and "Importar 2" in html

    client.post(sent["Location"], {"action": "confirm"})

    names = set(
        ClientCompany.objects.filter(organization=world.office).values_list("name", flat=True)
    )
    assert {"Um", "Dois"} <= names and "Três" not in names
    assert limits.usage(world.office, limits.COMPANIES) == 5


@pytest.mark.django_db
def test_the_roster_upload_page_shows_the_plan_notice_near_the_limit() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 3})
    client = login(world.owner, world.office)

    html = client.get(reverse("hub:roster")).content.decode()

    assert "Empresas: limite do plano atingido (3 de 3)." in html


@pytest.mark.django_db
def test_the_roster_without_limit_is_unchanged() -> None:
    world = World()
    client = login(world.owner, world.office)
    sent = client.post(
        reverse("hub:roster"),
        {
            "planilha": csv_file(
                CSV_HEADER + f"Um;{NEW_A};;\r\nDois;{cnpj_from('889990000001')};;\r\n"
            )
        },
    )

    client.post(sent["Location"], {"action": "confirm"})

    assert ImportBatch.objects.get(organization=world.office).created_count == 2


# ---------------------------------------------------------------- raiz de CNPJ (D-109)


def branch_of(cnpj: str) -> str:
    """CNPJ de uma filial: mesma raiz de 8 dígitos, outra ordem (0002), dígitos recalculados."""

    return cnpj_from(cnpj[:8] + "0002")


@pytest.mark.django_db
def test_a_branch_does_not_count_against_the_company_limit() -> None:
    world = World()
    assert limits.usage(world.office, limits.COMPANIES) == 3

    world.company("Filial da padaria", branch_of(world.padaria.cnpj_masked), "")

    assert ClientCompany.objects.filter(organization=world.office, active=True).count() == 4
    assert limits.usage(world.office, limits.COMPANIES) == 3


@pytest.mark.django_db
def test_a_company_without_a_valid_cnpj_counts_one_by_one() -> None:
    world = World()
    world.company("Sem CNPJ A", "", "")
    world.company("Sem CNPJ B", "", "")

    assert limits.usage(world.office, limits.COMPANIES) == 5


@pytest.mark.django_db
def test_an_inactive_root_is_not_in_use() -> None:
    world = World()
    world.oficina.active = False
    world.oficina.save(update_fields=["active"])

    assert limits.usage(world.office, limits.COMPANIES) == 2
    assert limits.adds_company_root(world.office, world.oficina.cnpj_masked) is True


@pytest.mark.django_db
def test_the_manual_add_of_a_branch_is_allowed_at_the_limit_but_a_new_root_is_not() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 3})  # as 3 raízes já estão em uso
    client = login(world.owner, world.office)

    branch = add_company(client, "Filial", branch_of(world.padaria.cnpj_masked))
    refused = add_company(client, "Raiz nova", NEW_A)

    assert ClientCompany.objects.filter(organization=world.office, name="Filial").exists()
    assert not ClientCompany.objects.filter(organization=world.office, name="Raiz nova").exists()
    assert "limite do plano atingido (3 de 3)" in refused.content.decode()
    assert branch.status_code == 200


@pytest.mark.django_db
def test_the_roster_lets_branches_in_and_only_new_roots_take_room() -> None:
    world = World()
    contract(world.office, plan_limits={"companies": 4})  # sobra 1 raiz nova
    padaria_branch = branch_of(world.padaria.cnpj_masked)
    client = login(world.owner, world.office)
    lines = [
        f"Filial da padaria;{padaria_branch};;",
        f"Raiz nova;{NEW_A};;",
        f"Filial da raiz nova;{branch_of(NEW_A)};;",
        f"Outra raiz;{NEW_B};;",
    ]
    text = CSV_HEADER + "\r\n".join(lines) + "\r\n"
    sent = client.post(reverse("hub:roster"), {"planilha": csv_file(text)})

    html = client.get(sent["Location"]).content.decode()
    assert "Importar 3" in html and html.count("Limite de empresas do plano") == 1

    client.post(sent["Location"], {"action": "confirm"})

    names = set(
        ClientCompany.objects.filter(organization=world.office).values_list("name", flat=True)
    )
    assert {"Filial da padaria", "Raiz nova", "Filial da raiz nova"} <= names
    assert "Outra raiz" not in names
    assert limits.usage(world.office, limits.COMPANIES) == 4
