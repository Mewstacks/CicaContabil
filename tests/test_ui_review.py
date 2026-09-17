import pytest
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts.models import User
from apps.common.redirects import detail_redirect
from apps.hub.forms import CompanyForm
from apps.hub.models import ClientCompany, CompanyAccessGrant
from apps.hub.templatetags.ui_navigation import back_url
from apps.organizations.models import Membership, Organization


def test_public_theme_persists_and_rejects_external_redirects():
    client = Client()
    for theme in ("light", "dark", "system"):
        response = client.post(
            reverse("hub:set-theme"), {"theme": theme, "next": "https://example.org/"}
        )
        assert response.status_code == 302
        assert response.url == "/"
        assert response.cookies["hub_theme"].value == theme
        assert response.cookies["hub_theme"]["httponly"]
    assert client.post(reverse("hub:set-theme"), {"theme": "invalid"}).status_code == 400
    assert client.get(reverse("hub:set-theme")).status_code == 405


def test_public_theme_requires_csrf():
    client = Client(enforce_csrf_checks=True)
    assert client.post(reverse("hub:set-theme"), {"theme": "dark"}).status_code == 403


@pytest.mark.django_db
def test_company_form_rejects_invalid_cnpj_and_keeps_the_entered_name():
    form = CompanyForm(data={"name": "Empresa de teste", "cnpj_masked": "123"})
    assert not form.is_valid()
    assert "cnpj_masked" in form.errors
    assert form["name"].value() == "Empresa de teste"


def test_back_url_preserves_only_the_expected_list():
    factory = RequestFactory()
    good = "/app/empresas/?q=Padaria&situacao=ativa"
    context = {"request": factory.get("/", {"return_to": good})}
    assert back_url(context, "hub:companies") == good
    for bad in (
        "https://example.org/app/empresas/",
        "//example.org/app/empresas/",
        "/app/equipe/",
        "/\\example.org/app/empresas/",
        "/app/empresas/\n",
    ):
        context = {"request": factory.get("/", {"return_to": bad})}
        assert back_url(context, "hub:companies") == "/app/empresas/"


def test_detail_action_keeps_the_list_query_without_redirecting_to_it():
    request = RequestFactory().post("/", {"return_to": "/app/revisoes/?q=Padaria"})
    response = detail_redirect(request, "hub:reviews")
    assert response.url == "/app/revisoes/?return_to=%2Fapp%2Frevisoes%2F%3Fq%3DPadaria"


@pytest.mark.django_db(databases=["default", "knowledge"])
def test_scoped_registry_does_not_reveal_other_companies_or_counts():
    office = Organization.objects.create(name="Escopo", slug="ui-scope")
    user = User.objects.create_user("scope@example.test", "test-password")
    membership = Membership.objects.create(organization=office, user=user, role="operator")
    allowed = ClientCompany.objects.create(organization=office, name="Permitida")
    denied = ClientCompany.objects.create(organization=office, name="Restrita")
    CompanyAccessGrant.objects.create(organization=office, membership=membership, company=allowed)
    client = Client()
    client.force_login(user)
    response = client.get(reverse("hub:companies"))
    assert response.status_code == 200
    assert response.context["office_company_total"] == 1
    assert list(response.context["companies"]) == [allowed]
    assert not response.context["can_manage_companies"]
    assert client.get(reverse("hub:company-detail", args=[denied.pk])).status_code == 404
    assert client.post(reverse("hub:companies"), {"name": "Intrusa"}).status_code == 403


@pytest.mark.django_db(databases=["default", "knowledge"])
def test_auditor_has_no_registry_write_action_and_post_is_denied():
    office = Organization.objects.create(name="Auditoria", slug="ui-audit")
    user = User.objects.create_user("audit@example.test", "test-password")
    Membership.objects.create(organization=office, user=user, role="auditor")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("hub:companies"))
    assert not response.context["can_manage_companies"]
    assert b'data-modal-open="company-dialog"' not in response.content
    assert client.post(reverse("hub:companies"), {"name": "Intrusa"}).status_code == 403
    assert client.post(reverse("hub:certificates"), {}).status_code == 403


@pytest.mark.django_db(databases=["default", "knowledge"])
def test_scoped_owner_can_see_the_company_they_just_created():
    office = Organization.objects.create(name="Cadastro", slug="ui-create")
    user = User.objects.create_user("create@example.test", "test-password")
    membership = Membership.objects.create(organization=office, user=user, role="owner")
    first = ClientCompany.objects.create(organization=office, name="Inicial")
    CompanyAccessGrant.objects.create(organization=office, membership=membership, company=first)
    client = Client()
    client.force_login(user)
    response = client.post(reverse("hub:companies"), {"name": "Nova empresa"})
    assert response.status_code == 302
    company = ClientCompany.objects.get(organization=office, name="Nova empresa")
    assert client.get(reverse("hub:company-detail", args=[company.pk])).status_code == 200
