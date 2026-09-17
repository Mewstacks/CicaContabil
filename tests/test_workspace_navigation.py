from types import SimpleNamespace

import pytest
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.hub.navigation import workspace_navigation
from apps.hub.templatetags.ui_navigation import back_url


@pytest.mark.parametrize("route", ["hub:nfse-center", "hub:reviews"])
def test_nfse_routes_share_one_task_menu(route):
    request = RequestFactory().get(reverse(route))
    request.resolver_match = resolve(request.path)
    groups = workspace_navigation(
        {
            "request": request,
            "enabled_modules": [SimpleNamespace(code="nfse")],
            "membership": SimpleNamespace(role="member"),
        }
    )
    fiscal = next(group for group in groups if group["key"] == "fiscal")
    assert fiscal["active"]
    assert [item["url"] for item in fiscal["links"]] == [reverse("hub:nfse-center")]
    urls = [item["url"] for group in groups for item in group["links"]]
    assert reverse("hub:team") not in urls
    assert reverse("hub:triage") not in urls
    assert reverse("hub:reconciliation") not in urls


def test_navigation_omits_unavailable_module_groups():
    request = RequestFactory().get(reverse("hub:dashboard"))
    request.resolver_match = resolve(request.path)
    groups = workspace_navigation({"request": request, "enabled_modules": []})
    assert {group["key"] for group in groups} == {"registry", "settings"}


def test_integra_menu_distinguishes_the_direct_dte_queue_from_the_service_hub():
    request = RequestFactory().get(reverse("hub:dte-center"))
    request.resolver_match = resolve(request.path)
    groups = workspace_navigation(
        {
            "request": request,
            "enabled_modules": [SimpleNamespace(code="integra")],
            "membership": SimpleNamespace(role="member"),
        }
    )

    fiscal = next(group for group in groups if group["key"] == "fiscal")
    links = {item["label"]: item for item in fiscal["links"]}
    assert links["Caixa DTE"]["active"] is True
    assert "Abrir mensagens" in links["Caixa DTE"]["description"]
    assert "Central Integra Contador" in links
    assert "Escolher outra rotina" in links["Central Integra Contador"]["description"]


@pytest.mark.parametrize(
    ("candidate", "accepted"),
    [
        ("/app/nfse/?q=Padaria&status=review", True),
        ("/app/revisoes/?q=Padaria", True),
        ("https://example.org/app/nfse/", False),
        ("//example.org/app/nfse/", False),
        ("/app/equipe/", False),
        ("/app/nfse/\n", False),
        ("/\\example.org/app/nfse/", False),
    ],
)
def test_review_return_accepts_only_its_two_lists(candidate, accepted):
    request = RequestFactory().get("/", {"return_to": candidate})
    result = back_url({"request": request}, "hub:reviews", "hub:nfse-center")
    assert result == (candidate if accepted else reverse("hub:reviews"))
