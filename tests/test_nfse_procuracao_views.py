"""Tela de procurações (D-304/D-305): acesso, escopo, ações e desvio do modo legado."""

from __future__ import annotations

import io
from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    NfseProcuracaoRequest,
    NfseSync,
    OfficeCertificate,
    OfficeProfile,
    ProductModule,
)
from apps.organizations.models import Membership, Organization
from pki_support import make_pfx
from test_nfse_procuracao import (
    CLIENT_CNPJ,
    OFFICE_CNPJ,
    OTHER_CLIENT_CNPJ,
    cnpj_from,
)

PASSWORD = "senha-do-escritorio"
URL = "hub:procuracoes"


def login(user: User, office: Organization) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(office.id)
    session.save()
    return client


class World:
    """Escritório em modo procuração com NFS-e ligada, dono, operador e três empresas."""

    def __init__(self, *, mode: str = OfficeProfile.NfseCollectionMode.PROCURACAO) -> None:
        self.office = Organization.objects.create(name="Escritório Tela", slug="tela")
        OfficeProfile.objects.create(
            organization=self.office, cnpj=OFFICE_CNPJ, nfse_collection_mode=mode
        )
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.NFSE, enabled=True
        )
        self.owner = self.member(Membership.Role.OWNER, "dono@example.test")
        self.operator = self.member(Membership.Role.OPERATOR, "operador@example.test")
        self.auditor = self.member(Membership.Role.AUDITOR, "auditor@example.test")
        self.padaria = self.company("Padaria Central", CLIENT_CNPJ, "dono@padaria.example")
        self.oficina = self.company("Oficina Norte", OTHER_CLIENT_CNPJ, "")
        self.mercado = self.company(
            "Mercado Sul", cnpj_from("AB12CD34EF56"), "mercado@example.test"
        )

    def member(self, role: str, email: str) -> User:
        user = User.objects.create_user(email=email, password="uma-senha-longa")
        Membership.objects.create(organization=self.office, user=user, role=role)
        return user

    def company(self, name: str, cnpj: str, email: str) -> ClientCompany:
        return ClientCompany.objects.create(
            organization=self.office, name=name, cnpj_masked=cnpj, contact_email=email
        )

    def upload(self, client: Client, **extra: Any) -> Any:
        pfx = extra.pop("pfx", make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ))
        return client.post(
            reverse(URL),
            {
                "action": "upload-certificate",
                "pfx": SimpleUploadedFile(extra.pop("name", "escritorio.pfx"), pfx),
                "password": extra.pop("password", PASSWORD),
            },
            follow=True,
        )


@pytest.fixture
def world(db: object) -> World:
    return World()


def texts(response: Any) -> list[str]:
    return [str(message) for message in response.context["messages"]]


@pytest.mark.django_db
def test_a_legacy_office_is_sent_back_to_the_certificates_page(world: World) -> None:
    OfficeProfile.objects.filter(organization=world.office).update(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.CERTIFICATE
    )

    response = login(world.owner, world.office).get(reverse(URL))

    assert response.status_code == 302 and response["Location"] == reverse("hub:certificates")


@pytest.mark.django_db
def test_a_procuracao_office_is_sent_from_the_a1_pages_to_procuracoes(world: World) -> None:
    client = login(world.owner, world.office)

    assert client.get(reverse("hub:certificates"))["Location"] == reverse(URL)
    collection = client.get(reverse("hub:nfse-center") + "?view=collection")
    assert collection["Location"] == reverse(URL)
    assert client.get(reverse("hub:nfse-center")).status_code == 200


@pytest.mark.django_db
def test_a_legacy_office_keeps_every_a1_page(world: World) -> None:
    OfficeProfile.objects.filter(organization=world.office).update(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.CERTIFICATE
    )
    client = login(world.owner, world.office)

    assert client.get(reverse("hub:certificates")).status_code == 200
    assert client.get(reverse("hub:nfse-center") + "?view=collection").status_code == 200


@pytest.mark.django_db
def test_the_menu_swaps_certificates_for_procuracoes_only_in_procuracao_mode(
    world: World,
) -> None:
    client = login(world.owner, world.office)

    menu = client.get(reverse("hub:companies")).content.decode().split("<main")[0]
    assert reverse(URL) in menu and reverse("hub:certificates") not in menu

    OfficeProfile.objects.filter(organization=world.office).update(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.CERTIFICATE
    )
    legacy = login(world.owner, world.office).get(reverse("hub:companies")).content.decode()
    legacy_menu = legacy.split("<main")[0]
    assert reverse("hub:certificates") in legacy_menu and reverse(URL) not in legacy_menu


@pytest.mark.django_db
def test_the_company_list_speaks_procuracao_not_a1_for_a_new_office(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING
    )

    html = client.get(reverse("hub:companies")).content.decode()

    assert "Sem A1 válido" not in html and "Enviar certificado A1" not in html
    assert "filtro-certificado" not in html
    assert "Procuração: sem procuração" in html and "Pedir procuração" in html
    assert "Ver procuração" in html
    detail = client.get(reverse("hub:company-detail", args=[world.padaria.pk])).content.decode()
    assert "Sem certificado A1" not in detail and "Abrir procurações" in detail


@pytest.mark.django_db
def test_the_company_list_of_a_legacy_office_is_untouched(world: World) -> None:
    OfficeProfile.objects.filter(organization=world.office).update(
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.CERTIFICATE
    )
    client = login(world.owner, world.office)

    html = client.get(reverse("hub:companies")).content.decode()

    assert "Sem A1 válido" in html and "filtro-certificado" in html
    assert "Procuração:" not in html
    detail = client.get(reverse("hub:company-detail", args=[world.padaria.pk])).content.decode()
    assert "Sem certificado A1" in detail and "Abrir procurações" not in detail


@pytest.mark.django_db
def test_the_page_lists_every_company_with_its_state_and_seeds_missing_rows(world: World) -> None:
    response = login(world.owner, world.office).get(reverse(URL))

    assert response.status_code == 200
    html = response.content.decode()
    for name in ("Padaria Central", "Oficina Norte", "Mercado Sul"):
        assert name in html
    assert NfseSync.objects.filter(organization=world.office).count() == 3
    assert "e-CNPJ ausente" in html and "Enviar e-CNPJ" in html
    assert "Coleta desligada" in html
    assert [tab["count"] for tab in response.context["tabs"]] == [3, 0, 3, 0, 0]


@pytest.mark.django_db
def test_filters_and_search_are_in_the_url_and_scoped(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING
    )

    missing = client.get(reverse(URL) + "?status=missing")
    assert [row.company.name for row in missing.context["page"].object_list] == ["Padaria Central"]
    searched = client.get(reverse(URL) + "?q=Mercado")
    assert [row.company.name for row in searched.context["page"].object_list] == ["Mercado Sul"]
    by_cnpj = client.get(reverse(URL) + f"?q={OTHER_CLIENT_CNPJ[:6]}")
    assert [row.company.name for row in by_cnpj.context["page"].object_list] == ["Oficina Norte"]
    empty = client.get(reverse(URL) + "?status=ok&q=zzz")
    assert "Nenhuma empresa corresponde" in empty.content.decode()
    assert "Ver tudo" in empty.content.decode()
    junk = client.get(reverse(URL) + "?status=invalido&page=abc")
    assert junk.status_code == 200 and junk.context["tab"] == "all"


@pytest.mark.django_db
def test_pending_companies_come_first(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK
    )
    NfseSync.objects.filter(company=world.mercado).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING
    )

    order = [row.company.name for row in client.get(reverse(URL)).context["page"].object_list]

    assert order == ["Mercado Sul", "Oficina Norte", "Padaria Central"]


@pytest.mark.django_db
def test_the_owner_uploads_the_e_cnpj_and_the_page_reflects_it(world: World) -> None:
    client = login(world.owner, world.office)

    response = world.upload(client)

    assert any("e-CNPJ enviado" in text for text in texts(response))
    certificate = OfficeCertificate.objects.get(organization=world.office)
    html = response.content.decode()
    assert "e-CNPJ válido" in html and "19.131.243/0001-97" in html
    assert "Trocar e-CNPJ" in html
    assert PASSWORD not in html and certificate.pfx_blob not in html
    assert set(NfseSync.objects.values_list("office_certificate_id", flat=True)) == {certificate.pk}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"password": "errada"}, "abrir o arquivo"),
        ({"name": "certificado.txt"}, "Selecione o arquivo"),
        ({"pfx": make_pfx(password=PASSWORD, cnpj=OTHER_CLIENT_CNPJ)}, "não é o do escritório"),
    ],
)
def test_a_bad_upload_says_why_and_stores_nothing(
    world: World, options: dict[str, Any], message: str
) -> None:
    response = world.upload(login(world.owner, world.office), **options)

    assert any(message in text for text in texts(response))
    assert not OfficeCertificate.objects.exists()


@pytest.mark.django_db
def test_only_owners_and_admins_touch_the_e_cnpj(world: World) -> None:
    for user in (world.operator, world.auditor):
        client = login(user, world.office)
        response = client.post(
            reverse(URL),
            {
                "action": "upload-certificate",
                "pfx": SimpleUploadedFile("a.pfx", make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ)),
                "password": PASSWORD,
            },
        )
        assert response.status_code == 403
        assert "Enviar e-CNPJ" not in client.get(reverse(URL)).content.decode()
    assert not OfficeCertificate.objects.exists()


@pytest.mark.django_db
def test_the_owner_revokes_and_the_state_says_so(world: World) -> None:
    client = login(world.owner, world.office)
    world.upload(client)

    response = client.post(reverse(URL), {"action": "revoke-certificate"}, follow=True)

    assert any("revogado" in text for text in texts(response))
    assert "e-CNPJ revogado" in response.content.decode()
    assert OfficeCertificate.objects.get().revoked_at is not None


@pytest.mark.django_db
def test_requesting_for_selected_companies_mails_only_those(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))

    response = client.post(
        reverse(URL),
        {"action": "request", "company": [str(world.padaria.pk), str(world.oficina.pk)]},
        follow=True,
    )

    assert [message.to for message in mail.outbox] == [["dono@padaria.example"]]
    summary = " ".join(texts(response))
    assert "1 pedido enviado" in summary and "1 sem e-mail" in summary
    assert NfseProcuracaoRequest.objects.count() == 1
    assert "Pedido" in response.content.decode()


@pytest.mark.django_db
def test_an_operator_outside_the_portfolio_reaches_no_company(world: World) -> None:
    client = login(world.operator, world.office)

    page = client.get(reverse(URL))
    client.post(reverse(URL), {"action": "request", "company": [str(world.padaria.pk)]})

    assert page.status_code == 200
    assert "Padaria Central" not in page.content.decode()
    assert mail.outbox == []
    assert not NfseProcuracaoRequest.objects.exists()


@pytest.mark.django_db
def test_requesting_for_everyone_without_procuracao_skips_the_ones_that_are_fine(
    world: World,
) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK
    )

    client.post(reverse(URL), {"action": "request-pending"})

    assert [message.to for message in mail.outbox] == [["mercado@example.test"]]


@pytest.mark.django_db
def test_an_auditor_cannot_send_requests_or_verify(world: World) -> None:
    client = login(world.auditor, world.office)
    client.get(reverse(URL))

    for action in ("request", "request-pending", "verify", "verify-all"):
        response = client.post(reverse(URL), {"action": action, "company": [str(world.padaria.pk)]})
        assert response.status_code == 403
    assert mail.outbox == []
    page = client.get(reverse(URL)).content.decode()
    assert "Pedir aos selecionados" not in page and "Verificar selecionados" not in page


@pytest.mark.django_db
def test_ids_from_another_office_are_ignored(world: World) -> None:
    other = Organization.objects.create(name="Outro", slug="outro-escritorio")
    stranger = ClientCompany.objects.create(
        organization=other, name="De outro", cnpj_masked=CLIENT_CNPJ, contact_email="x@example.test"
    )
    client = login(world.owner, world.office)

    client.post(reverse(URL), {"action": "request", "company": [str(stranger.pk)]})

    assert mail.outbox == []
    assert not NfseProcuracaoRequest.objects.exists()


@pytest.mark.django_db
def test_verify_schedules_the_company_for_the_next_probe(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        next_run_at=timezone.now() + timedelta(hours=5),
        status=NfseSync.Status.ERROR,
        failure_count=4,
    )

    response = client.post(
        reverse(URL), {"action": "verify", "company": [str(world.padaria.pk)]}, follow=True
    )

    sync = NfseSync.objects.get(company=world.padaria)
    assert sync.status == NfseSync.Status.IDLE and sync.failure_count == 0
    assert sync.next_run_at <= timezone.now()
    assert any("Verificação agendada: 1 empresa" in text for text in texts(response))


@pytest.mark.django_db
def test_the_return_url_keeps_only_known_filters(world: World) -> None:
    client = login(world.owner, world.office)

    response = client.post(
        reverse(URL),
        {"action": "verify-all", "status": "missing", "q": "Padaria", "evil": "//example.test"},
    )

    assert response["Location"] == reverse(URL) + "?status=missing&q=Padaria"


@pytest.mark.django_db
def test_a_company_page_of_another_office_never_leaks_into_the_list(world: World) -> None:
    other = Organization.objects.create(name="Outro", slug="outro-lista")
    OfficeProfile.objects.create(
        organization=other,
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
        cnpj=OTHER_CLIENT_CNPJ,
    )
    ClientCompany.objects.create(organization=other, name="Cliente Alheio", cnpj_masked=CLIENT_CNPJ)

    html = login(world.owner, world.office).get(reverse(URL)).content.decode()

    assert "Cliente Alheio" not in html


@pytest.mark.django_db
def test_pending_companies_download_as_a_spreadsheet_without_formulas(world: World) -> None:
    from openpyxl import load_workbook

    ClientCompany.objects.filter(pk=world.oficina.pk).update(name='=HYPERLINK("http://x","y")')
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    NfseSync.objects.filter(company=world.padaria).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK
    )

    response = client.get(reverse(URL) + "?export=pendentes")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.openxmlformats")
    assert "attachment" in response["Content-Disposition"]
    assert response["Cache-Control"] == "no-store"
    rows = list(load_workbook(io.BytesIO(response.content)).active.iter_rows(values_only=True))
    assert rows[0] == ("Empresa", "CNPJ", "Código Domínio", "E-mail", "Situação", "Último pedido")
    names = [row[0] for row in rows[1:]]
    assert len(names) == 2 and "Padaria Central" not in names
    assert any(name.startswith("'=HYPERLINK") for name in names)
    assert AuditEvent.objects.get(action="hub.nfse.procuracao_exported").metadata == {"rows": 2}


@pytest.mark.django_db
def test_the_pending_spreadsheet_is_not_for_every_profile(world: World) -> None:
    client = login(world.auditor, world.office)

    assert client.get(reverse(URL) + "?export=pendentes").status_code == 403


@pytest.mark.django_db
def test_the_return_url_encodes_what_the_user_typed(world: World) -> None:
    client = login(world.owner, world.office)

    response = client.post(reverse(URL), {"action": "verify-all", "q": "Silva & Filhos #1 X: y"})

    assert response["Location"] == reverse(URL) + "?q=Silva+%26+Filhos+%231+X%3A+y"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("flag", "environment", "paused", "expected"),
    [
        (False, "production", False, "Coleta desligada"),
        (True, "trial", False, "Coleta só em produção"),
        (True, "production", True, "Coleta em pausa"),
        (True, "production", False, "Coleta ligada"),
    ],
)
def test_the_page_says_what_state_the_collection_lane_is_in(
    world: World, flag: bool, environment: str, paused: bool, expected: str
) -> None:
    from django.core.cache import cache
    from django.test import override_settings

    from apps.hub.tasks_procuracao import PAUSE_CACHE_KEY

    cache.delete(PAUSE_CACHE_KEY)
    if paused:
        cache.set(PAUSE_CACHE_KEY, True, 60)
    with override_settings(NFSE_PROCURACAO_SYNC_ENABLED=flag, NFSE_ADN_ENVIRONMENT=environment):
        html = login(world.owner, world.office).get(reverse(URL)).content.decode()
    cache.delete(PAUSE_CACHE_KEY)

    assert expected in html


@pytest.mark.django_db
def test_the_certificate_state_names_an_expired_or_revoked_e_cnpj(world: World) -> None:
    client = login(world.owner, world.office)
    world.upload(client)
    certificate = OfficeCertificate.objects.get()

    OfficeCertificate.objects.filter(pk=certificate.pk).update(
        valid_until=timezone.now() - timedelta(days=1)
    )
    assert "e-CNPJ vencido" in client.get(reverse(URL)).content.decode()

    OfficeCertificate.objects.filter(pk=certificate.pk).update(revoked_at=timezone.now())
    assert "e-CNPJ revogado" in client.get(reverse(URL)).content.decode()


@pytest.mark.django_db
def test_an_oversized_or_missing_file_is_refused_with_a_clear_message(world: World) -> None:
    client = login(world.owner, world.office)

    too_big = client.post(
        reverse(URL),
        {
            "action": "upload-certificate",
            "pfx": SimpleUploadedFile("grande.pfx", b"0" * 600_000),
            "password": PASSWORD,
        },
        follow=True,
    )
    missing = client.post(reverse(URL), {"action": "upload-certificate"}, follow=True)

    assert any("maior que o esperado" in text for text in texts(too_big))
    assert any("Selecione o arquivo" in text for text in texts(missing))
    assert not OfficeCertificate.objects.exists()


@pytest.mark.django_db
def test_revoking_without_an_e_cnpj_and_unknown_actions_change_nothing(world: World) -> None:
    client = login(world.owner, world.office)

    first = client.post(reverse(URL), {"action": "revoke-certificate"})
    second = client.post(reverse(URL), {"action": "inventada"})

    assert first.status_code == second.status_code == 302
    assert not AuditEvent.objects.filter(action="hub.office_certificate.revoked").exists()


@pytest.mark.django_db
def test_verifying_with_nothing_selected_says_so(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))

    response = client.post(reverse(URL), {"action": "verify"}, follow=True)

    assert any("Nenhuma empresa para verificar" in text for text in texts(response))


@pytest.mark.django_db
def test_verifying_wakes_the_lane_when_it_is_on(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    from unittest.mock import patch

    from django.test import override_settings

    client = login(world.owner, world.office)
    client.get(reverse(URL))

    with (
        override_settings(NFSE_PROCURACAO_SYNC_ENABLED=True, NFSE_ADN_ENVIRONMENT="production"),
        patch("apps.hub.tasks_procuracao.dispatch_procuracao_syncs.delay") as wake,
        django_capture_on_commit_callbacks(execute=True),
    ):
        client.post(reverse(URL), {"action": "verify-all"})

    wake.assert_called_once()


@pytest.mark.django_db
def test_the_request_summary_reports_each_kind_of_skip(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.hub import procuracao_requests

    monkeypatch.setattr(procuracao_requests, "BATCH_LIMIT", 1)
    client = login(world.owner, world.office)
    client.get(reverse(URL))
    client.post(reverse(URL), {"action": "request", "company": [str(world.padaria.pk)]})

    response = client.post(
        reverse(URL),
        {
            "action": "request",
            "company": [str(world.padaria.pk), str(world.mercado.pk), str(world.oficina.pk)],
        },
        follow=True,
    )

    summary = " ".join(texts(response))
    assert "1 pedido enviado" in summary
    assert "1 já pedido(s) há menos de 3 dias" in summary
    assert "1 sem e-mail" in summary


@pytest.mark.django_db
def test_a_failed_delivery_is_reported_as_a_warning_not_a_success(world: World) -> None:
    from unittest.mock import patch

    from apps.platform.notifications import TransactionalEmailError

    client = login(world.owner, world.office)
    client.get(reverse(URL))

    with patch(
        "apps.hub.procuracao_requests.send_transactional_email",
        side_effect=TransactionalEmailError("falhou"),
    ):
        response = client.post(
            reverse(URL),
            {"action": "request", "company": [str(world.padaria.pk), str(world.mercado.pk)]},
            follow=True,
        )

    assert any("e-mail não saiu" in text for text in texts(response))


@pytest.mark.django_db
def test_a_malformed_company_id_is_ignored_not_a_server_error(world: World) -> None:
    client = login(world.owner, world.office)
    client.get(reverse(URL))

    response = client.post(
        reverse(URL), {"action": "request", "company": ["não-é-uuid", str(world.padaria.pk)]}
    )

    assert response.status_code == 302
    assert [message.to for message in mail.outbox] == [["dono@padaria.example"]]
