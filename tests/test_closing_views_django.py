"""Closing screens, module gate, company scope and the entitlement."""

from __future__ import annotations

from datetime import date

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.closing import services
from apps.closing.models import ClosingConference, ClosingDocument, ClosingLayout
from apps.hub.models import (
    CompanyAccessGrant,
    FiscalGuide,
    OperationalActivity,
    ProductModule,
)
from apps.hub.module_catalog import MODULES, self_service_module_codes
from apps.organizations.models import Membership
from apps.platform.models import Entitlement
from closing_support import (
    das_text,
    make_activity,
    make_company,
    make_guide,
    make_layout,
    make_office,
    make_user,
    txt_upload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = tmp_path


def login(user_email: str) -> Client:
    from apps.accounts.models import User

    user = User.objects.get(email=user_email)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(Membership.objects.get(user=user).organization_id)
    session.save()
    return client


@pytest.fixture
def world():  # type: ignore[no-untyped-def]
    office = make_office()
    owner = make_user(office, "owner@closing.test")
    company = make_company(office)
    layout = make_layout(
        office,
        activity_code="pgdas",
        compare=ClosingLayout.Compare.FISCAL_GUIDE,
        guide_kind=FiscalGuide.Kind.DAS,
    )
    activity = make_activity(office, company)
    return office, owner, company, layout, activity


def upload(client: Client, text: str, name: str = "das.txt"):  # type: ignore[no-untyped-def]
    return client.post(reverse("closing:upload"), {"documents": txt_upload(text, name)})


# --- module and entitlement ----------------------------------------------------------


def test_the_module_is_catalogued_but_never_self_service() -> None:
    assert ProductModule.Code.CLOSING in MODULES
    assert MODULES[ProductModule.Code.CLOSING].route_name == "closing:index"
    assert ProductModule.Code.CLOSING not in self_service_module_codes()


def test_a_new_office_does_not_get_the_module_and_gets_a_403(world) -> None:  # type: ignore[no-untyped-def]
    office, _owner, *_ = world
    ProductModule.objects.filter(organization=office, code="closing").update(enabled=False)
    client = login("owner@closing.test")
    assert client.get(reverse("closing:index")).status_code == 403
    assert client.get(reverse("closing:layouts")).status_code == 403


def test_provision_office_turns_the_module_on_for_fedrizzi_and_only_there() -> None:
    other = make_office("other-office")
    call_command("provision_office", name="Fedrizzi Contabilidade", slug="fedrizzi-contabilidade")
    from apps.organizations.models import Organization

    fed = Organization.objects.get(slug="fedrizzi-contabilidade")
    assert ProductModule.objects.get(organization=fed, code="closing").enabled
    assert Entitlement.objects.get(organization=fed, code="closing").enabled
    assert ProductModule.objects.get(organization=other, code="closing").enabled  # fixture row
    assert not Entitlement.objects.filter(organization=other, code="closing").exists()


# --- screens -------------------------------------------------------------------------


def test_upload_reads_the_document_and_opens_it(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    client = login("owner@closing.test")
    response = upload(client, das_text())
    document = ClosingDocument.objects.get(organization=office)
    assert response.status_code == 302
    assert response["Location"] == reverse("closing:document", args=[document.pk])
    page = client.get(response["Location"])
    assert page.status_code == 200
    body = page.content.decode()
    assert "1234.56" in body or "1.234,56" in body
    assert "Sem referência" in body


def test_the_list_filters_by_state_and_search(world) -> None:  # type: ignore[no-untyped-def]
    client = login("owner@closing.test")
    upload(client, das_text())
    upload(client, "Texto sem layout", "outro.txt")
    page = client.get(reverse("closing:index"))
    assert page.status_code == 200
    body = page.content.decode()
    assert "das.txt" in body and "outro.txt" in body
    quarantine = client.get(reverse("closing:index") + "?situacao=quarentena").content.decode()
    assert "outro.txt" in quarantine and "das.txt" not in quarantine
    decide = client.get(reverse("closing:index") + "?situacao=decidir").content.decode()
    assert "das.txt" in decide and "outro.txt" not in decide
    found = client.get(reverse("closing:index") + "?q=Padaria").content.decode()
    assert "das.txt" in found and "outro.txt" not in found


def test_the_filtered_empty_state_offers_the_way_out(world) -> None:  # type: ignore[no-untyped-def]
    client = login("owner@closing.test")
    upload(client, das_text())
    body = client.get(reverse("closing:index") + "?q=inexistente").content.decode()
    assert "Nenhum documento encontrado" in body
    assert "Ver tudo" in body


def test_deciding_a_divergence_through_the_screen(world) -> None:  # type: ignore[no-untyped-def]
    office, _, company, _, activity = world
    make_guide(office, company, cents=150000)
    client = login("owner@closing.test")
    upload(client, das_text())
    document = ClosingDocument.objects.get()
    conference = document.conferences.get()
    url = reverse("closing:conference-decide", args=[document.pk, conference.pk])
    empty = client.post(url, {"decision": "accept", "reason": ""})
    assert empty.status_code == 302
    conference.refresh_from_db()
    assert conference.resolution == ""
    client.post(url, {"decision": "accept", "reason": "Juros conferidos"})
    conference.refresh_from_db()
    activity.refresh_from_db()
    assert conference.resolution == ClosingConference.Resolution.ACCEPTED
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED


def test_a_viewer_reads_but_cannot_upload_or_decide(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    make_user(office, "viewer@closing.test", Membership.Role.AUDITOR)
    client = login("viewer@closing.test")
    assert client.get(reverse("closing:index")).status_code == 200
    before = ClosingDocument.objects.count()
    response = upload(client, das_text())
    assert response.status_code in {302, 403}
    assert ClosingDocument.objects.count() == before


def test_another_office_cannot_open_or_download_the_document(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    login("owner@closing.test")
    services.ingest_upload(
        organization=office,
        actor=Membership.objects.get(organization=office).user,
        upload=txt_upload(das_text()),
    )
    document = ClosingDocument.objects.get()
    other = make_office("intruder-office")
    make_user(other, "intruder@closing.test")
    client = login("intruder@closing.test")
    for name in ("closing:document", "closing:document-file"):
        assert client.get(reverse(name, args=[document.pk])).status_code in {403, 404}
    for name in ("closing:document-reread", "closing:document-discard"):
        assert client.post(reverse(name, args=[document.pk])).status_code in {403, 404}
    document.refresh_from_db()
    assert document.state == ClosingDocument.State.ACCEPTED
    assert "Padaria" not in client.get(reverse("closing:index")).content.decode()


def test_a_collaborator_without_the_company_does_not_see_its_documents(world) -> None:  # type: ignore[no-untyped-def]
    office, owner, *_ = world
    services.ingest_upload(organization=office, actor=owner, upload=txt_upload(das_text()))
    document = ClosingDocument.objects.get()
    other_company = make_company(office, "Outra Ltda", "11.222.333/0001-81")
    operator = make_user(office, "op@closing.test", Membership.Role.OPERATOR)
    membership = Membership.objects.get(organization=office, user=operator)
    CompanyAccessGrant.objects.create(
        organization=office,
        membership=membership,
        company=other_company,
        modules=[ProductModule.Code.CLOSING],
    )
    client = login("op@closing.test")
    page = client.get(reverse("closing:index"))
    if page.status_code == 200:
        assert "das.txt" not in page.content.decode()
    assert client.get(reverse("closing:document", args=[document.pk])).status_code in {403, 404}


def test_the_original_file_downloads_as_an_attachment(world) -> None:  # type: ignore[no-untyped-def]
    office, owner, *_ = world
    services.ingest_upload(organization=office, actor=owner, upload=txt_upload(das_text()))
    document = ClosingDocument.objects.get()
    response = login("owner@closing.test").get(reverse("closing:document-file", args=[document.pk]))
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"


def test_layout_screens_create_edit_and_activate(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    client = login("owner@closing.test")
    created = client.post(
        reverse("closing:layout-new"),
        {
            "label": "Guia ISS",
            "code": "iss",
            "kind": "guide",
            "compare": "none",
            "value_source": "amount",
            "tolerance": "0.99",
            "zero_clears": "on",
        },
    )
    assert created.status_code == 302
    layout = ClosingLayout.objects.get(organization=office, code="iss")
    assert not layout.active
    blocked = client.post(
        reverse("closing:layout-activate", args=[layout.pk]), {"action": "activate"}
    )
    layout.refresh_from_db()
    assert blocked.status_code == 302 and not layout.active
    for variable, anchor in (
        ("marker", "Guia ISS"),
        ("cnpj", "CNPJ:"),
        ("competence", "Período de Apuração"),
        ("amount", "Valor Total do Documento"),
    ):
        client.post(
            reverse("closing:layout-field-add", args=[layout.pk]),
            {"variable": variable, "anchor": anchor, "occurrence": 0, "sum_count": 0},
        )
    assert layout.fields.count() == 4
    client.post(
        reverse("closing:layout-sample", args=[layout.pk]),
        {"sample_text": "Guia ISS\n" + das_text()},
    )
    page = client.get(reverse("closing:layout", args=[layout.pk]))
    assert page.status_code == 200 and "Lido" in page.content.decode()
    client.post(reverse("closing:layout-activate", args=[layout.pk]), {"action": "activate"})
    layout.refresh_from_db()
    assert layout.active
    client.post(
        reverse(
            "closing:layout-field-remove", args=[layout.pk, layout.fields.get(variable="cnpj").pk]
        )
    )
    layout.refresh_from_db()
    assert not layout.active  # lost a required field


def test_a_layout_of_another_office_is_not_reachable(world) -> None:  # type: ignore[no-untyped-def]
    other = make_office("other-layouts")
    foreign = make_layout(other)
    client = login("owner@closing.test")
    assert client.get(reverse("closing:layout", args=[foreign.pk])).status_code == 404
    assert (
        client.post(
            reverse("closing:layout-activate", args=[foreign.pk]), {"action": "deactivate"}
        ).status_code
        == 404
    )
    foreign.refresh_from_db()
    assert foreign.active


def test_a_quarantined_file_becomes_a_layout_draft_with_its_text(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    client = login("owner@closing.test")
    upload(client, "Guia Municipal XYZ\nCNPJ: 12.345.678/0001-95", "xyz.txt")
    document = ClosingDocument.objects.get(original_name="xyz.txt")
    response = client.post(reverse("closing:document-layout", args=[document.pk]))
    assert response.status_code == 302
    draft = ClosingLayout.objects.get(organization=office, code="novo-layout")
    assert "Guia Municipal XYZ" in draft.sample_text
    assert not draft.active


def test_pages_render_with_the_module_navigation(world) -> None:  # type: ignore[no-untyped-def]
    client = login("owner@closing.test")
    body = client.get(reverse("closing:index")).content.decode()
    assert reverse("closing:layouts") in body
    nav = client.get(reverse("hub:dashboard")).content.decode()
    assert reverse("closing:index") in nav
    assert date.today().year > 2000


def _restricted_operator(office, other_company):  # type: ignore[no-untyped-def]
    operator = make_user(office, "scoped@closing.test", Membership.Role.OPERATOR)
    CompanyAccessGrant.objects.create(
        organization=office,
        membership=Membership.objects.get(organization=office, user=operator),
        company=other_company,
        modules=[ProductModule.Code.CLOSING],
    )
    return operator


def test_a_scoped_operator_cannot_read_or_clear_another_companys_document(world) -> None:  # type: ignore[no-untyped-def]
    office, _, company, _, activity = world
    make_guide(office, company)
    _restricted_operator(office, make_company(office, "Outra Ltda", "11.222.333/0001-81"))
    client = login("scoped@closing.test")
    upload(client, das_text())  # CNPJ of the padaria, outside this operator's portfolio
    document = ClosingDocument.objects.get()
    assert document.state == ClosingDocument.State.QUARANTINE
    assert document.company is None
    assert not document.conferences.exists()
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING


def test_a_duplicate_of_a_document_outside_the_portfolio_is_refused_neutrally(world) -> None:  # type: ignore[no-untyped-def]
    office, owner, *_ = world
    services.ingest_upload(organization=office, actor=owner, upload=txt_upload(das_text()))
    _restricted_operator(office, make_company(office, "Outra Ltda", "11.222.333/0001-81"))
    client = login("scoped@closing.test")
    before = ClosingDocument.objects.count()
    response = upload(client, das_text())
    assert response.status_code == 302
    assert ClosingDocument.objects.count() == before
    assert response["Location"] == reverse("closing:index")


def test_a_scoped_operator_neither_sees_samples_nor_builds_layouts_from_files(world) -> None:  # type: ignore[no-untyped-def]
    office, owner, _, layout, _ = world
    layout.sample_text = das_text()
    layout.save()
    services.ingest_upload(
        organization=office, actor=owner, upload=txt_upload("Guia XYZ sem layout", "xyz.txt")
    )
    quarantined = ClosingDocument.objects.get(original_name="xyz.txt")
    _restricted_operator(office, make_company(office, "Outra Ltda", "11.222.333/0001-81"))
    client = login("scoped@closing.test")
    page = client.get(reverse("closing:layout", args=[layout.pk]))
    assert page.status_code == 200
    assert "12.345.678/0001-95" not in page.content.decode()
    assert "Amostra" not in page.content.decode()
    blocked = client.post(reverse("closing:document-layout", args=[quarantined.pk]))
    assert blocked.status_code in {403, 404}
    assert not ClosingLayout.objects.filter(code="novo-layout").exists()
    sample = client.post(reverse("closing:layout-sample", args=[layout.pk]), {"sample_text": "x"})
    assert sample.status_code in {302, 403}
    layout.refresh_from_db()
    assert layout.sample_text == das_text()
