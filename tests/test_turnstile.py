"""Cloudflare Turnstile no cadastro (E2): desligado = cadastro como era; ligado = falha fechada."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.error import URLError

import pytest
from django.core import mail
from django.test import Client
from django.test.utils import override_settings

from apps.common import turnstile
from apps.platform.models import SignupIntent

SECRET = "1x0000000000000000000000000000000AA"  # chave de teste publicada pela Cloudflare
SITE = "1x00000000000000000000AA"
VALID_CNPJ = "68340160000113"
FORM = {
    "full_name": "Responsável",
    "email": "novo@example.com",
    "cnpj": VALID_CNPJ,
    "accept_terms": "on",
}
ON = {"TURNSTILE_SITE_KEY": SITE, "TURNSTILE_SECRET_KEY": SECRET}


def answer(**payload: Any) -> Any:
    calls: list[tuple[str, dict[str, str], float]] = []

    def post(url: str, data: dict[str, str], timeout: float) -> dict[str, Any]:
        calls.append((url, data, timeout))
        return payload

    post.calls = calls  # type: ignore[attr-defined]
    return post


# ---------------------------------------------------------------- verify()


@override_settings(**ON)
def test_a_valid_token_is_confirmed_with_the_documented_request() -> None:
    post = answer(success=True, hostname="testserver")

    result = turnstile.verify("token-ok", hostname="testserver", post=post)

    assert result == turnstile.OK
    [(url, data, timeout)] = post.calls
    assert url == "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    assert data == {"secret": SECRET, "response": "token-ok"}  # sem IP do visitante
    assert timeout == 5


@override_settings(**ON)
@pytest.mark.parametrize("token", ["", "x" * 2049])
def test_a_missing_or_oversized_token_is_refused_without_calling_cloudflare(token: str) -> None:
    post = answer(success=True)

    assert turnstile.verify(token, post=post) == turnstile.FAILED
    assert post.calls == []


@override_settings(**ON)
@pytest.mark.parametrize(
    "codes", [["invalid-input-response"], ["timeout-or-duplicate"], ["missing-input-secret"], []]
)
def test_a_rejected_token_fails(codes: list[str]) -> None:
    assert turnstile.verify("t", post=answer(success=False, **{"error-codes": codes})) == (
        turnstile.FAILED
    )


@override_settings(**ON)
def test_a_cloudflare_internal_error_is_unavailable_not_a_wrong_answer() -> None:
    post = answer(success=False, **{"error-codes": ["internal-error"]})

    assert turnstile.verify("t", post=post) == turnstile.UNAVAILABLE


@override_settings(**ON)
@pytest.mark.parametrize("error", [URLError("down"), TimeoutError(), OSError("net"), ValueError()])
def test_a_network_failure_is_unavailable(error: Exception) -> None:
    def post(url: str, data: dict[str, str], timeout: float) -> dict[str, Any]:
        raise error

    assert turnstile.verify("t", post=post) == turnstile.UNAVAILABLE


@override_settings(**ON)
def test_a_token_solved_on_another_site_is_refused() -> None:
    post = answer(success=True, hostname="outro-site.example")

    assert turnstile.verify("t", hostname="cica.example", post=post) == turnstile.FAILED


@override_settings(**ON, TURNSTILE_CHECK_HOSTNAME=False)
def test_the_hostname_check_can_be_switched_off_for_test_keys() -> None:
    post = answer(success=True, hostname="example.com")  # o que a chave de teste devolve

    assert turnstile.verify("t", hostname="cica.example", post=post) == turnstile.OK


@pytest.mark.parametrize(
    "settings_",
    [
        {},
        {"TURNSTILE_SITE_KEY": SITE},
        {"TURNSTILE_SECRET_KEY": SECRET},
    ],
)
def test_it_is_off_unless_both_keys_exist(settings_: dict[str, str]) -> None:
    with override_settings(**{"TURNSTILE_SITE_KEY": "", "TURNSTILE_SECRET_KEY": "", **settings_}):
        assert turnstile.enabled() is False
        assert turnstile.site_key() == ""


def test_it_is_off_by_default_in_the_shipped_settings() -> None:
    from django.conf import settings

    assert settings.TURNSTILE_SITE_KEY == "" and settings.TURNSTILE_SECRET_KEY == ""
    assert settings.TURNSTILE_CHECK_HOSTNAME is True


# ---------------------------------------------------------------- cadastro


@pytest.mark.django_db
def test_the_signup_page_without_keys_has_no_widget_and_keeps_the_csp() -> None:
    response = Client().get("/comecar/")

    html = response.content.decode()
    assert "cf-turnstile" not in html and "challenges.cloudflare.com" not in html
    assert "challenges.cloudflare.com" not in response.headers.get("Content-Security-Policy", "")


@pytest.mark.django_db
@override_settings(**ON)
def test_the_signup_page_with_keys_shows_the_widget_and_opens_the_csp_only_there() -> None:
    client = Client()

    signup = client.get("/comecar/")
    login = client.get("/entrar/")

    html = signup.content.decode()
    assert f'data-sitekey="{SITE}"' in html
    assert 'src="https://challenges.cloudflare.com/turnstile/v0/api.js"' in html
    policy = signup.headers["Content-Security-Policy"]
    assert "script-src 'self' https://challenges.cloudflare.com" in policy
    assert "frame-src https://challenges.cloudflare.com" in policy
    assert "challenges.cloudflare.com" not in login.headers.get("Content-Security-Policy", "")


@pytest.mark.django_db
@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "Escritório Teste"})
def test_signup_without_keys_works_exactly_as_before(_lookup: Any) -> None:
    response = Client().post("/comecar/", FORM)

    assert response.status_code == 202
    assert SignupIntent.objects.count() == 1 and len(mail.outbox) == 1


@pytest.mark.django_db
@override_settings(**ON)
@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "Escritório Teste"})
def test_signup_with_keys_and_no_token_is_refused_and_creates_nothing(_lookup: Any) -> None:
    with patch.object(turnstile, "_post") as network:
        response = Client().post("/comecar/", FORM)

    assert response.status_code == 200
    assert "Confirme que você não é um robô" in response.content.decode()
    assert SignupIntent.objects.count() == 0 and mail.outbox == []
    network.assert_not_called()
    assert "challenges.cloudflare.com" in response.headers["Content-Security-Policy"]


@pytest.mark.django_db
@override_settings(**ON)
@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "Escritório Teste"})
def test_signup_with_keys_and_a_good_token_goes_through(_lookup: Any) -> None:
    with patch.object(turnstile, "_post", return_value={"success": True, "hostname": "testserver"}):
        response = Client().post("/comecar/", {**FORM, turnstile.FIELD: "token-bom"})

    assert response.status_code == 202
    assert SignupIntent.objects.count() == 1


@pytest.mark.django_db
@override_settings(**ON)
@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "Escritório Teste"})
def test_signup_with_keys_and_a_bad_token_is_refused(_lookup: Any) -> None:
    bad = {"success": False, "error-codes": ["invalid-input-response"]}
    with patch.object(turnstile, "_post", return_value=bad):
        response = Client().post("/comecar/", {**FORM, turnstile.FIELD: "token-ruim"})

    assert response.status_code == 200 and SignupIntent.objects.count() == 0
    assert "Confirme que você não é um robô" in response.content.decode()


@pytest.mark.django_db
@override_settings(**ON)
@patch("apps.platform.signup.lookup_company", return_value={"razao_social": "Escritório Teste"})
def test_signup_fails_closed_when_cloudflare_is_down(_lookup: Any) -> None:
    with patch.object(turnstile, "_post", side_effect=URLError("down")):
        response = Client().post("/comecar/", {**FORM, turnstile.FIELD: "token"})

    assert response.status_code == 200 and SignupIntent.objects.count() == 0
    assert "Não foi possível validar agora" in response.content.decode()
