"""Office-owned mailbox consent through Mewstack's provider OAuth applications."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.urls import reverse

from apps.triage.models import Mailbox


class MailboxOAuthError(ValueError):
    """Safe, user-facing failure without token or provider payload."""


@dataclass(frozen=True)
class ProviderConfiguration:
    provider: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    profile_url: str
    mailbox_test_url: str
    scopes: tuple[str, ...]


def provider_configuration(provider: str) -> ProviderConfiguration:
    if provider == Mailbox.Provider.MS365_GRAPH:
        enabled = settings.TRIAGE_MS_OAUTH_ENABLED
        configuration = ProviderConfiguration(
            provider=provider,
            client_id=settings.TRIAGE_MS_CLIENT_ID,
            client_secret=settings.TRIAGE_MS_CLIENT_SECRET,
            authorize_url="https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/organizations/oauth2/v2.0/token",  # noqa: S106 - endpoint, not secret
            profile_url="https://graph.microsoft.com/v1.0/me?$select=mail,userPrincipalName",
            mailbox_test_url=(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1&$select=id"
            ),
            scopes=(
                "openid",
                "offline_access",
                "https://graph.microsoft.com/User.Read",
                "https://graph.microsoft.com/Mail.Read",
            ),
        )
    elif provider == Mailbox.Provider.GMAIL_API:
        enabled = settings.TRIAGE_GOOGLE_OAUTH_ENABLED
        configuration = ProviderConfiguration(
            provider=provider,
            client_id=settings.TRIAGE_GOOGLE_CLIENT_ID,
            client_secret=settings.TRIAGE_GOOGLE_CLIENT_SECRET,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",  # noqa: S106 - endpoint, not secret
            profile_url="https://gmail.googleapis.com/gmail/v1/users/me/profile",
            mailbox_test_url=(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages"
                "?maxResults=1&labelIds=INBOX"
            ),
            scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        )
    else:
        raise MailboxOAuthError("Provedor de caixa invalido.")
    if not enabled or not configuration.client_id or not configuration.client_secret:
        raise MailboxOAuthError("Esta conexao ainda nao foi ativada pela Mewstack.")
    return configuration


def redirect_uri(provider: str) -> str:
    base_url = settings.TRIAGE_OAUTH_BASE_URL.rstrip("/")
    parts = urlsplit(base_url)
    is_local_http = (
        settings.DEBUG and parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1"}
    )
    if (
        not parts.netloc
        or (parts.scheme != "https" and not is_local_http)
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise MailboxOAuthError("Configure o dominio HTTPS de retorno OAuth da CICA.")
    return base_url + reverse("hub:triage-oauth-callback", args=[provider])


def new_authorization(provider: str) -> tuple[str, str, str]:
    configuration = provider_configuration(provider)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    parameters = {
        "client_id": configuration.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri(provider),
        "scope": " ".join(configuration.scopes),
        "state": state,
        "code_challenge": challenge.decode("ascii"),
        "code_challenge_method": "S256",
    }
    if provider == Mailbox.Provider.GMAIL_API:
        parameters.update({"access_type": "offline", "prompt": "consent"})
    return f"{configuration.authorize_url}?{urlencode(parameters)}", state, verifier


def _provider_json(request: Request) -> dict[str, object]:
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed provider origins
            result = json.loads(response.read(64_000))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise MailboxOAuthError("O provedor nao confirmou a conexao. Tente novamente.") from exc
    if not isinstance(result, dict):
        raise MailboxOAuthError("O provedor retornou uma resposta invalida.")
    return result


def exchange_code(provider: str, *, code: str, verifier: str) -> tuple[str, str]:
    configuration = provider_configuration(provider)
    if not code or len(code) > 2_048 or not verifier:
        raise MailboxOAuthError("Autorizacao incompleta. Conecte a caixa novamente.")
    body = urlencode(
        {
            "client_id": configuration.client_id,
            "client_secret": configuration.client_secret,
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri(provider),
        }
    ).encode("utf-8")
    result = _provider_json(
        Request(  # noqa: S310 - provider endpoint is a fixed origin selected above
            configuration.token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    )
    access_token = result.get("access_token")
    refresh_token = result.get("refresh_token")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise MailboxOAuthError("O provedor nao liberou acesso permanente. Reconecte a caixa.")
    if not access_token or not refresh_token:
        raise MailboxOAuthError("O provedor nao liberou acesso permanente. Reconecte a caixa.")
    return access_token, refresh_token


def probe_mailbox(provider: str, *, access_token: str) -> str:
    configuration = provider_configuration(provider)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    profile = _provider_json(
        Request(configuration.profile_url, headers=headers)  # noqa: S310 - fixed API origin
    )
    address = (
        profile.get("emailAddress")
        if provider == Mailbox.Provider.GMAIL_API
        else profile.get("mail") or profile.get("userPrincipalName")
    )
    if not isinstance(address, str):
        raise MailboxOAuthError("O provedor nao identificou o endereco da caixa.")
    address = address.strip().lower()
    try:
        validate_email(address)
    except ValidationError as exc:
        raise MailboxOAuthError("O provedor nao identificou um endereco de caixa valido.") from exc
    _provider_json(
        Request(configuration.mailbox_test_url, headers=headers)  # noqa: S310 - fixed API origin
    )
    return address


def encrypted_refresh_credential(provider: str, refresh_token: str) -> str:
    """Mailbox.credential encrypts this serialized value at rest."""
    return json.dumps({"version": 1, "provider": provider, "refresh_token": refresh_token})


def refresh_access_token(provider: str, credential: str) -> tuple[str, str]:
    """Get a fresh access token; return the token that must stay encrypted for next use."""
    configuration = provider_configuration(provider)
    try:
        data = json.loads(credential)
    except (TypeError, ValueError) as exc:
        raise MailboxOAuthError("Caixa sem autorização válida. Reconecte-a.") from exc
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("provider") != provider:
        raise MailboxOAuthError("Caixa sem autorização válida. Reconecte-a.")
    old_refresh = data.get("refresh_token")
    if not isinstance(old_refresh, str) or not old_refresh:
        raise MailboxOAuthError("Caixa sem autorização válida. Reconecte-a.")
    body = urlencode(
        {
            "client_id": configuration.client_id,
            "client_secret": configuration.client_secret,
            "refresh_token": old_refresh,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    result = _provider_json(
        Request(  # noqa: S310 - fixed provider endpoint
            configuration.token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    )
    access_token = result.get("access_token")
    rotated = result.get("refresh_token", old_refresh)
    if not isinstance(access_token, str) or not access_token:
        raise MailboxOAuthError("O provedor não renovou o acesso. Reconecte a caixa.")
    if not isinstance(rotated, str) or not rotated:
        raise MailboxOAuthError("O provedor não renovou o acesso. Reconecte a caixa.")
    return access_token, encrypted_refresh_credential(provider, rotated)
