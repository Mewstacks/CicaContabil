from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.organizations.models import Membership, Organization
from apps.triage.models import Mailbox
from apps.triage.oauth import (
    MailboxOAuthError,
    encrypted_refresh_credential,
    refresh_access_token,
)


@override_settings(
    TRIAGE_OAUTH_BASE_URL="https://cica.example.test",
    TRIAGE_MS_OAUTH_ENABLED=True,
    TRIAGE_MS_CLIENT_ID="mewstack-ms-app",
    TRIAGE_MS_CLIENT_SECRET="fake-ms-secret",
    TRIAGE_GOOGLE_OAUTH_ENABLED=True,
    TRIAGE_GOOGLE_CLIENT_ID="mewstack-google-app",
    TRIAGE_GOOGLE_CLIENT_SECRET="fake-google-secret",
)
class TriageMailboxOAuthTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("mail-owner@example.test", "safe-password-123")
        self.office = Organization.objects.create(name="Escritorio A", slug="escritorio-a")
        Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.TRIAGE, enabled=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def _start(self, provider: str = Mailbox.Provider.MS365_GRAPH) -> dict[str, object]:
        response = self.client.post(reverse("hub:triage-oauth-start", args=[provider]))
        self.assertEqual(response.status_code, 302)
        parameters = parse_qs(urlsplit(response["Location"]).query)
        self.assertEqual(parameters["code_challenge_method"], ["S256"])
        self.assertEqual(
            parameters["redirect_uri"],
            ["https://cica.example.test" + reverse("hub:triage-oauth-callback", args=[provider])],
        )
        flow = self.client.session["triage_oauth_flow"]
        self.assertEqual(parameters["state"], [flow["state"]])
        self.assertNotIn("fake-ms-secret", response["Location"])
        return flow

    def test_oauth_start_uses_per_office_state_pkce_and_no_client_secret_in_browser(self) -> None:
        self._start()
        google = self._start(Mailbox.Provider.GMAIL_API)
        self.assertEqual(google["provider"], Mailbox.Provider.GMAIL_API)
        self.assertEqual(google["office_id"], str(self.office.id))
        self.assertEqual(
            self.client.get(
                reverse("hub:triage-oauth-start", args=[Mailbox.Provider.GMAIL_API])
            ).status_code,
            405,
        )

    def test_callback_rejects_wrong_state_before_exchanging_code(self) -> None:
        self._start()
        with patch("apps.hub.views.exchange_code") as exchange:
            response = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.MS365_GRAPH]),
                {"state": "wrong", "code": "authorization-code"},
            )
        self.assertRedirects(response, reverse("hub:triage"))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        exchange.assert_not_called()
        self.assertFalse(Mailbox.objects.exists())

    def test_callback_uses_tested_provider_identity_and_encrypts_refresh_token(self) -> None:
        flow = self._start()
        with (
            patch("apps.hub.views.exchange_code", return_value=("access", "refresh-secret")),
            patch("apps.hub.views.probe_mailbox", return_value="box@office.test"),
        ):
            response = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.MS365_GRAPH]),
                {"state": flow["state"], "code": "authorization-code"},
            )
        self.assertRedirects(response, reverse("hub:triage"))
        self.assertEqual(response["Cache-Control"], "no-store")
        mailbox = Mailbox.objects.get(organization=self.office)
        self.assertEqual(mailbox.address, "box@office.test")
        self.assertEqual(mailbox.status, Mailbox.Status.ACTIVE)
        self.assertFalse(mailbox.active)
        self.assertIsNone(mailbox.since)
        self.assertIn("refresh-secret", mailbox.credential)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT credential FROM triage_mailbox WHERE address = %s",
                ["box@office.test"],
            )
            raw = cursor.fetchone()[0]
        self.assertNotIn("refresh-secret", raw)
        self.assertNotIn("triage_oauth_flow", self.client.session)

    def test_callback_cannot_complete_after_office_switch(self) -> None:
        flow = self._start()
        other = Organization.objects.create(name="Escritorio B", slug="escritorio-b")
        Membership.objects.create(organization=other, user=self.user, role=Membership.Role.OWNER)
        ProductModule.objects.create(
            organization=other, code=ProductModule.Code.TRIAGE, enabled=True
        )
        session = self.client.session
        session["hub_organization_id"] = str(other.id)
        session.save()
        with patch("apps.hub.views.exchange_code") as exchange:
            response = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.MS365_GRAPH]),
                {"state": flow["state"], "code": "authorization-code"},
            )
        self.assertRedirects(response, reverse("hub:triage"))
        exchange.assert_not_called()
        self.assertFalse(Mailbox.objects.exists())

    def test_disconnect_removes_this_offices_credential_and_cursor(self) -> None:
        mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="box@office.test",
            credential="refresh-secret",
            cursor="opaque-checkpoint",
            status=Mailbox.Status.ACTIVE,
        )
        response = self.client.post(reverse("hub:triage-mailbox-disconnect", args=[mailbox.id]))
        self.assertRedirects(response, reverse("hub:triage"))
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.credential, "")
        self.assertEqual(mailbox.cursor, "")
        self.assertFalse(mailbox.active)
        self.assertEqual(mailbox.status, Mailbox.Status.DISABLED)

    def test_error_mailbox_is_not_presented_as_authorized(self) -> None:
        Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="box@office.test",
            status=Mailbox.Status.ERROR,
            active=False,
        )
        response = self.client.get(reverse("hub:triage"))
        self.assertContains(response, "Caixa com erro; recebimento indisponível")
        self.assertNotContains(response, "Caixa autorizada; recebimento não disponível")
        self.assertContains(response, "peça suporte à Mewstack")

    def test_refresh_handles_provider_rotation_without_exposing_secret_in_url(self) -> None:
        for provider, result, expected in (
            (
                Mailbox.Provider.MS365_GRAPH,
                {"access_token": "fresh-access", "refresh_token": "rotated-refresh"},
                "rotated-refresh",
            ),
            (Mailbox.Provider.GMAIL_API, {"access_token": "fresh-access"}, "old-refresh"),
        ):
            credential = encrypted_refresh_credential(provider, "old-refresh")
            with patch("apps.triage.oauth._provider_json", return_value=result) as transport:
                access, updated = refresh_access_token(provider, credential)
            self.assertEqual(access, "fresh-access")
            self.assertIn(expected, updated)
            request = transport.call_args.args[0]
            self.assertNotIn("old-refresh", request.full_url)
            self.assertIn(b"grant_type=refresh_token", request.data)
            self.assertIn(b"refresh_token=old-refresh", request.data)

    def test_refresh_rejects_disconnected_or_mismatched_credential_without_transport(self) -> None:
        with patch("apps.triage.oauth._provider_json") as transport:
            for credential in (
                "",
                "not-json",
                encrypted_refresh_credential(Mailbox.Provider.GMAIL_API, "other-token"),
            ):
                with self.assertRaises(MailboxOAuthError):
                    refresh_access_token(Mailbox.Provider.MS365_GRAPH, credential)
        transport.assert_not_called()
