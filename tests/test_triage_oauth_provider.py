"""Chamadas ao provedor OAuth da caixa: erros temporários, troca de código e sonda da caixa."""

from __future__ import annotations

import io
import json
from email.message import Message
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import SimpleTestCase, override_settings

from apps.triage import oauth
from apps.triage.models import Mailbox
from apps.triage.oauth import (
    MailboxOAuthError,
    MailboxOAuthTemporaryError,
    exchange_code,
    new_authorization,
    probe_mailbox,
    provider_configuration,
    redirect_uri,
    refresh_access_token,
)

GMAIL = Mailbox.Provider.GMAIL_API
MS = Mailbox.Provider.MS365_GRAPH

CONFIG = {
    "TRIAGE_OAUTH_BASE_URL": "https://cica.example.test",
    "TRIAGE_MS_OAUTH_ENABLED": True,
    "TRIAGE_MS_CLIENT_ID": "ms-app",
    "TRIAGE_MS_CLIENT_SECRET": "ms-fake",
    "TRIAGE_GOOGLE_OAUTH_ENABLED": True,
    "TRIAGE_GOOGLE_CLIENT_ID": "google-app",
    "TRIAGE_GOOGLE_CLIENT_SECRET": "google-fake",
}


class Resposta:
    def __init__(self, corpo: bytes) -> None:
        self.corpo = corpo

    def __enter__(self) -> Resposta:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, limite: int = -1) -> bytes:
        return self.corpo


def http_error(codigo: int, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://provider.test", codigo, "x", headers, io.BytesIO(b""))


@override_settings(**CONFIG)
class ProviderJsonTests(SimpleTestCase):
    def chamar(self, efeito: Any) -> dict[str, object]:
        with patch.object(oauth, "urlopen", side_effect=efeito):
            return oauth._provider_json(oauth.Request("https://provider.test"))

    def test_resposta_valida(self) -> None:
        with patch.object(oauth, "urlopen", return_value=Resposta(b'{"ok": true}')):
            assert oauth._provider_json(oauth.Request("https://provider.test")) == {"ok": True}

    def test_429_e_5xx_sao_temporarios_com_dica_de_espera(self) -> None:
        for codigo in (429, 500, 503):
            with self.assertRaises(MailboxOAuthTemporaryError) as ctx:
                self.chamar(http_error(codigo, "30"))
            assert ctx.exception.retry_seconds >= 0

    def test_4xx_pede_reconexao(self) -> None:
        with self.assertRaisesMessage(MailboxOAuthError, "Reconecte a caixa"):
            self.chamar(http_error(400))

    def test_rede_fora_e_temporaria(self) -> None:
        for erro in (URLError("sem rede"), TimeoutError(), OSError("reset")):
            with self.assertRaises(MailboxOAuthTemporaryError):
                self.chamar(erro)

    def test_corpo_que_nao_e_json(self) -> None:
        with (
            patch.object(oauth, "urlopen", return_value=Resposta(b"<html>")),
            self.assertRaisesMessage(MailboxOAuthError, "nao confirmou"),
        ):
            oauth._provider_json(oauth.Request("https://provider.test"))

    def test_json_que_nao_e_objeto(self) -> None:
        with (
            patch.object(oauth, "urlopen", return_value=Resposta(b"[1, 2]")),
            self.assertRaisesMessage(MailboxOAuthError, "resposta invalida"),
        ):
            oauth._provider_json(oauth.Request("https://provider.test"))


@override_settings(**CONFIG)
class ExchangeCodeTests(SimpleTestCase):
    def test_troca_devolve_os_dois_tokens(self) -> None:
        with patch.object(
            oauth, "_provider_json", return_value={"access_token": "a", "refresh_token": "r"}
        ) as chamado:
            assert exchange_code(GMAIL, code="codigo", verifier="v") == ("a", "r")

        corpo = parse_qs(chamado.call_args.args[0].data.decode())
        assert corpo["grant_type"] == ["authorization_code"]
        assert corpo["code_verifier"] == ["v"]

    def test_codigo_ou_verificador_ausente_ou_gigante(self) -> None:
        for codigo, verificador in (("", "v"), ("c", ""), ("x" * 2_049, "v")):
            with self.assertRaisesMessage(MailboxOAuthError, "Autorizacao incompleta"):
                exchange_code(GMAIL, code=codigo, verifier=verificador)

    def test_resposta_sem_refresh_token(self) -> None:
        for resposta in (
            {"access_token": "a"},
            {"access_token": "", "refresh_token": "r"},
            {"access_token": "a", "refresh_token": ""},
            {"access_token": 1, "refresh_token": "r"},
        ):
            with (
                patch.object(oauth, "_provider_json", return_value=resposta),
                self.assertRaisesMessage(MailboxOAuthError, "acesso permanente"),
            ):
                exchange_code(MS, code="c", verifier="v")


@override_settings(**CONFIG)
class ProbeMailboxTests(SimpleTestCase):
    def test_gmail_usa_email_address_em_minusculas(self) -> None:
        with patch.object(
            oauth, "_provider_json", side_effect=[{"emailAddress": " Caixa@Exemplo.com "}, {}]
        ) as chamado:
            assert probe_mailbox(GMAIL, access_token="t") == "caixa@exemplo.com"

        assert chamado.call_count == 2
        assert chamado.call_args_list[0].args[0].headers["Authorization"] == "Bearer t"

    def test_microsoft_cai_para_user_principal_name(self) -> None:
        with patch.object(
            oauth, "_provider_json", side_effect=[{"userPrincipalName": "u@exemplo.com"}, {}]
        ):
            assert probe_mailbox(MS, access_token="t") == "u@exemplo.com"

    def test_endereco_ausente_ou_invalido(self) -> None:
        with (
            patch.object(oauth, "_provider_json", return_value={}),
            self.assertRaisesMessage(MailboxOAuthError, "nao identificou o endereco"),
        ):
            probe_mailbox(GMAIL, access_token="t")
        with (
            patch.object(oauth, "_provider_json", return_value={"emailAddress": "sem-arroba"}),
            self.assertRaisesMessage(MailboxOAuthError, "endereco de caixa valido"),
        ):
            probe_mailbox(GMAIL, access_token="t")


@override_settings(**CONFIG)
class RefreshTests(SimpleTestCase):
    def credencial(self, **mudar: object) -> str:
        dados = {"version": 1, "provider": GMAIL, "refresh_token": "velho"} | mudar
        return json.dumps(dados)

    def test_renova_e_guarda_o_token_rotacionado(self) -> None:
        with patch.object(
            oauth, "_provider_json", return_value={"access_token": "novo", "refresh_token": "r2"}
        ):
            acesso, guardado = refresh_access_token(GMAIL, self.credencial())

        assert acesso == "novo"
        assert json.loads(guardado)["refresh_token"] == "r2"

    def test_sem_rotacao_mantem_o_refresh_antigo(self) -> None:
        with patch.object(oauth, "_provider_json", return_value={"access_token": "novo"}):
            _, guardado = refresh_access_token(GMAIL, self.credencial())

        assert json.loads(guardado)["refresh_token"] == "velho"

    def test_credencial_corrompida_ou_de_outro_provedor(self) -> None:
        for credencial in (
            "não é json",
            json.dumps([1]),
            self.credencial(version=2),
            self.credencial(provider=MS),
            self.credencial(refresh_token=""),
        ):
            with self.assertRaisesMessage(MailboxOAuthError, "autorização válida"):
                refresh_access_token(GMAIL, credencial)

    def test_provedor_nao_devolve_acesso(self) -> None:
        for resposta in ({}, {"access_token": ""}, {"access_token": "a", "refresh_token": ""}):
            with (
                patch.object(oauth, "_provider_json", return_value=resposta),
                self.assertRaisesMessage(MailboxOAuthError, "não renovou"),
            ):
                refresh_access_token(GMAIL, self.credencial())


@override_settings(**CONFIG)
class ConfiguracaoTests(SimpleTestCase):
    def test_autorizacao_gmail_pede_acesso_offline(self) -> None:
        url, state, verifier = new_authorization(GMAIL)

        consulta = parse_qs(urlsplit(url).query)
        assert consulta["access_type"] == ["offline"]
        assert consulta["code_challenge_method"] == ["S256"]
        assert consulta["state"] == [state]
        assert verifier

    def test_autorizacao_microsoft_nao_pede_offline_na_url(self) -> None:
        url, _, _ = new_authorization(MS)

        assert "access_type" not in parse_qs(urlsplit(url).query)

    def test_provedor_desconhecido(self) -> None:
        with pytest.raises(MailboxOAuthError, match="Provedor de caixa invalido"):
            provider_configuration("outro")

    @override_settings(TRIAGE_GOOGLE_CLIENT_SECRET="")
    def test_sem_segredo_pede_configurar(self) -> None:
        with pytest.raises(MailboxOAuthError, match="Configure o aplicativo OAuth"):
            provider_configuration(GMAIL)

    @override_settings(TRIAGE_OAUTH_BASE_URL="http://cica.example.test", DEBUG=False)
    def test_retorno_sem_https_e_recusado(self) -> None:
        with pytest.raises(MailboxOAuthError, match="HTTPS"):
            redirect_uri(GMAIL)

    @override_settings(TRIAGE_OAUTH_BASE_URL="http://localhost:8000", DEBUG=True)
    def test_retorno_http_local_so_com_debug(self) -> None:
        assert redirect_uri(GMAIL).startswith("http://localhost:8000/")

    @override_settings(TRIAGE_OAUTH_BASE_URL="https://cica.example.test/caminho")
    def test_retorno_com_caminho_e_recusado(self) -> None:
        with pytest.raises(MailboxOAuthError, match="HTTPS"):
            redirect_uri(GMAIL)
