from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Membership, Organization
from apps.triage.models import (
    AgentFileJob,
    DestinationProfile,
    Mailbox,
    MailboxOAuthApp,
    TriageItem,
)
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
    TRIAGE_GOOGLE_PERSONAL_VERIFIED=True,
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

    def test_office_configures_cutoff_filters_and_activation_after_consent(self) -> None:
        mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            address="documentos@office.test",
            credential=encrypted_refresh_credential(Mailbox.Provider.GMAIL_API, "refresh-token"),
            status=Mailbox.Status.ACTIVE,
            active=False,
        )
        prefix = f"mailbox-{mailbox.id}"

        response = self.client.post(
            reverse("hub:triage-mailbox-configure", args=[mailbox.id]),
            {
                f"{prefix}-folder": "NOTAS",
                f"{prefix}-since": "2026-09-01",
                f"{prefix}-sender_filter": "fiscal@cliente.test",
                f"{prefix}-subject_filter": "documentos",
                f"{prefix}-active": "on",
            },
        )

        self.assertRedirects(response, reverse("hub:triage-connections"))
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.folder, "NOTAS")
        self.assertEqual(mailbox.since.date().isoformat(), "2026-09-01")
        self.assertEqual(mailbox.sender_filter, "fiscal@cliente.test")
        self.assertEqual(mailbox.subject_filter, "documentos")
        self.assertTrue(mailbox.active)

    def test_office_selects_internal_or_windows_destination_with_fixed_pattern(self) -> None:
        internal = self.client.post(
            reverse("hub:triage-destination-configure"),
            {"mode": DestinationProfile.Mode.INTERNAL, "windows_root": ""},
        )
        self.assertRedirects(internal, reverse("hub:triage-connections"))
        profile = DestinationProfile.objects.get(organization=self.office)
        self.assertEqual(profile.mode, DestinationProfile.Mode.INTERNAL)
        self.assertEqual(profile.folder_template, "{company_name} [Domínio {dominio_code}]")

        windows = self.client.post(
            reverse("hub:triage-destination-configure"),
            {"mode": DestinationProfile.Mode.WINDOWS, "windows_root": r"D:\Clientes"},
        )
        self.assertRedirects(windows, reverse("hub:triage-connections"))
        profile.refresh_from_db()
        self.assertEqual(profile.mode, DestinationProfile.Mode.WINDOWS)
        self.assertEqual(profile.windows_root, r"D:\Clientes")

        invalid = self.client.post(
            reverse("hub:triage-destination-configure"),
            {"mode": DestinationProfile.Mode.WINDOWS, "windows_root": r"..\fora"},
        )
        self.assertEqual(invalid.status_code, 400)
        profile.refresh_from_db()
        self.assertEqual(profile.windows_root, r"D:\Clientes")

    def test_windows_destination_shows_agent_health_and_the_last_write(self) -> None:
        self.client.post(
            reverse("hub:triage-destination-configure"),
            {"mode": DestinationProfile.Mode.WINDOWS, "windows_root": r"D:\Clientes"},
        )

        offline = self.client.get(reverse("hub:triage-connections"))
        self.assertContains(offline, "Agente sem sinal")
        self.assertContains(offline, "Nenhum agente pareado")
        self.assertContains(offline, "Nenhuma gravação confirmada")

        EdgeAgent.objects.create(
            organization=self.office,
            label="Servidor do escritório",
            fingerprint="fp",
            shared_secret="secret",
            last_seen_at=timezone.now(),
        )
        item = TriageItem.objects.create(
            organization=self.office,
            original_name="nota.xml",
            content_hash="c" * 64,
            byte_size=10,
            declared_type="text/xml",
        )
        AgentFileJob.objects.create(
            organization=self.office,
            triage_item=item,
            destination_path="D:/Clientes/Empresa/nota.xml",
            status=AgentFileJob.Status.DONE,
            completed_at=timezone.now(),
        )

        online = self.client.get(reverse("hub:triage-connections"))
        self.assertContains(online, "Agente conectado")
        self.assertContains(online, "Servidor do escritório")
        self.assertContains(online, "Última gravação confirmada")

    def test_central_demo_hides_and_blocks_real_mailbox_connections(self) -> None:
        self.office.is_demo = True
        self.office.save(update_fields=["is_demo"])
        page = self.client.get(reverse("hub:triage-connections"))
        self.assertContains(page, "Caixa de exemplo")
        self.assertNotContains(page, "Testar e conectar IMAP")
        with (
            patch("apps.hub.views.probe_imap_mailbox") as imap,
            patch("apps.hub.views.new_authorization") as oauth,
        ):
            imap_response = self.client.post(reverse("hub:triage-imap-connect"), {})
            oauth_response = self.client.post(
                reverse("hub:triage-oauth-start", args=[Mailbox.Provider.MS365_GRAPH])
            )
        self.assertEqual(imap_response.status_code, 403)
        self.assertEqual(oauth_response.status_code, 403)
        imap.assert_not_called()
        oauth.assert_not_called()

    @override_settings(TRIAGE_EMAIL_POLL_ENABLED=True)
    def test_mailbox_workspace_explains_setup_retry_and_corrective_action(self) -> None:
        cutoff = timezone.now() - timedelta(days=1)
        Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="setup@office.test",
            status=Mailbox.Status.ACTIVE,
            active=False,
            since=None,
        )
        Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            address="retry@office.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=cutoff,
            poll_retry_after=timezone.now() + timedelta(minutes=20),
            last_error="Gmail temporariamente indisponível.",
        )
        Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.IMAP,
            address="error@office.test",
            status=Mailbox.Status.ERROR,
            active=True,
            since=cutoff,
            last_error="A pasta IMAP não foi encontrada.",
        )
        response = self.client.get(reverse("hub:triage-connections"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conectada; falta configurar a leitura")
        self.assertContains(response, "Retentativa programada")
        self.assertContains(response, "Próxima tentativa:")
        self.assertContains(response, "Gmail temporariamente indisponível.")
        self.assertContains(response, "Ação necessária")
        self.assertContains(response, "A pasta IMAP não foi encontrada.")
        self.assertContains(response, 'href="#triage-provider-imap"')
        self.assertContains(response, "Anexos já recebidos não serão apagados por esta ação.")
        self.assertNotContains(response, "O recebimento de anexos já está desligado")
        self.assertNotContains(response, "Precisa reconectar")

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
        self.assertRedirects(response, reverse("hub:triage-connections"))
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
        self.assertRedirects(response, reverse("hub:triage-connections"))
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
        self.assertRedirects(response, reverse("hub:triage-connections"))
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
        self.assertRedirects(response, reverse("hub:triage-connections"))
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
        queue = self.client.get(reverse("hub:triage"))
        self.assertContains(queue, "Caixa precisa de atenção")
        self.assertContains(queue, reverse("hub:triage-connections"))
        response = self.client.get(reverse("hub:triage-connections"))
        self.assertNotContains(response, "Leitura habilitada")
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


@override_settings(
    TRIAGE_OAUTH_BASE_URL="https://cica.example.test",
    TRIAGE_MS_OAUTH_ENABLED=False,
    TRIAGE_MS_CLIENT_ID="",
    TRIAGE_MS_CLIENT_SECRET="",
    TRIAGE_GOOGLE_OAUTH_ENABLED=False,
    TRIAGE_GOOGLE_CLIENT_ID="",
    TRIAGE_GOOGLE_CLIENT_SECRET="",
    TRIAGE_GOOGLE_PERSONAL_VERIFIED=False,
)
class OfficeOwnedOAuthAppTests(TestCase):
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

    def _save_ms(self) -> MailboxOAuthApp:
        response = self.client.post(
            reverse("hub:triage-oauth-app-save", args=[Mailbox.Provider.MS365_GRAPH]),
            {
                "ms365_graph-client_id": "office-ms-client",
                "ms365_graph-client_secret": "office-ms-secret",
                "ms365_graph-tenant_id": "0f23e421-3914-48ca-9aa2-11ed3d907240",
            },
        )
        self.assertRedirects(response, reverse("hub:triage-connections"))
        return MailboxOAuthApp.objects.get(organization=self.office)

    def test_owner_saves_encrypted_app_and_signs_in_through_own_tenant(self) -> None:
        app = self._save_ms()
        self.assertEqual(app.client_secret, "office-ms-secret")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT client_secret FROM triage_mailboxoauthapp WHERE id = %s", [app.id.hex]
            )
            raw = cursor.fetchone()[0]
        self.assertNotIn("office-ms-secret", raw)
        response = self.client.post(
            reverse("hub:triage-oauth-start", args=[Mailbox.Provider.MS365_GRAPH])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(app.tenant_id, response["Location"])
        self.assertEqual(
            parse_qs(urlsplit(response["Location"]).query)["client_id"], [app.client_id]
        )
        self.assertNotIn(app.client_secret, response["Location"])
        self.assertEqual(self.client.session["triage_oauth_flow"]["app_id"], str(app.id))

    def test_callback_binds_token_to_unchanged_office_app(self) -> None:
        app = self._save_ms()
        response = self.client.post(
            reverse("hub:triage-oauth-start", args=[Mailbox.Provider.MS365_GRAPH])
        )
        self.assertEqual(response.status_code, 302)
        flow = self.client.session["triage_oauth_flow"]
        with (
            patch("apps.hub.views.exchange_code", return_value=("access", "refresh")) as exchange,
            patch("apps.hub.views.probe_mailbox", return_value="box@office.test"),
        ):
            callback = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.MS365_GRAPH]),
                {"state": flow["state"], "code": "code"},
            )
        self.assertRedirects(callback, reverse("hub:triage-connections"))
        self.assertEqual(exchange.call_args.kwargs["app"], app)
        mailbox = Mailbox.objects.get(organization=self.office)
        self.assertEqual(mailbox.oauth_app_id, app.id)
        with patch(
            "apps.triage.oauth._provider_json", return_value={"access_token": "fresh"}
        ) as io:
            fresh, _ = refresh_access_token(
                mailbox.provider, mailbox.credential, app=mailbox.oauth_app
            )
        self.assertEqual(fresh, "fresh")
        self.assertIn(b"client_id=office-ms-client", io.call_args.args[0].data)

    def test_cannot_replace_app_while_box_is_connected(self) -> None:
        app = self._save_ms()
        Mailbox.objects.create(
            organization=self.office,
            oauth_app=app,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="box@office.test",
            status=Mailbox.Status.ACTIVE,
        )
        response = self.client.post(
            reverse("hub:triage-oauth-app-save", args=[Mailbox.Provider.MS365_GRAPH]),
            {
                "ms365_graph-client_id": "new-client",
                "ms365_graph-client_secret": "new-secret",
                "ms365_graph-tenant_id": app.tenant_id,
            },
        )
        self.assertEqual(response.status_code, 409)
        app.refresh_from_db()
        self.assertEqual(app.client_id, "office-ms-client")

    @override_settings(
        TRIAGE_GOOGLE_OAUTH_ENABLED=True,
        TRIAGE_GOOGLE_CLIENT_ID="mewstack-verified-google",
        TRIAGE_GOOGLE_CLIENT_SECRET="central-secret",
        TRIAGE_GOOGLE_PERSONAL_VERIFIED=True,
    )
    def test_personal_gmail_uses_central_app_even_when_office_has_workspace_app(self) -> None:
        app = MailboxOAuthApp.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            client_id="office-workspace-google",
            client_secret="office-secret",
        )
        start = self.client.post(
            reverse("hub:triage-oauth-start", args=[Mailbox.Provider.GMAIL_API]),
            {"oauth_source": "mewstack"},
        )
        self.assertEqual(start.status_code, 302)
        self.assertEqual(
            parse_qs(urlsplit(start["Location"]).query)["client_id"],
            ["mewstack-verified-google"],
        )
        flow = self.client.session["triage_oauth_flow"]
        self.assertEqual(flow["app_id"], "")
        with (
            patch("apps.hub.views.exchange_code", return_value=("access", "refresh")) as exchange,
            patch("apps.hub.views.probe_mailbox", return_value="office@gmail.com"),
        ):
            callback = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.GMAIL_API]),
                {"state": flow["state"], "code": "code"},
            )
        self.assertRedirects(callback, reverse("hub:triage-connections"))
        self.assertIsNone(exchange.call_args.kwargs["app"])
        mailbox = Mailbox.objects.get(organization=self.office, address="office@gmail.com")
        self.assertIsNone(mailbox.oauth_app)
        self.assertNotEqual(mailbox.oauth_app_id, app.id)

    @override_settings(
        TRIAGE_GOOGLE_OAUTH_ENABLED=True,
        TRIAGE_GOOGLE_CLIENT_ID="mewstack-verified-google",
        TRIAGE_GOOGLE_CLIENT_SECRET="central-secret",
        TRIAGE_GOOGLE_PERSONAL_VERIFIED=True,
    )
    def test_central_gmail_rejects_workspace_address(self) -> None:
        start = self.client.post(
            reverse("hub:triage-oauth-start", args=[Mailbox.Provider.GMAIL_API]),
            {"oauth_source": "mewstack"},
        )
        flow = self.client.session["triage_oauth_flow"]
        self.assertEqual(start.status_code, 302)
        with (
            patch("apps.hub.views.exchange_code", return_value=("access", "refresh")),
            patch("apps.hub.views.probe_mailbox", return_value="box@office.com"),
        ):
            callback = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.GMAIL_API]),
                {"state": flow["state"], "code": "code"},
            )
        self.assertRedirects(callback, reverse("hub:triage-connections"))
        self.assertFalse(Mailbox.objects.exists())

    @override_settings(TRIAGE_GOOGLE_OAUTH_ENABLED=True)
    def test_office_workspace_app_rejects_personal_gmail_address(self) -> None:
        MailboxOAuthApp.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            client_id="office-workspace-google",
            client_secret="office-secret",
        )
        start = self.client.post(
            reverse("hub:triage-oauth-start", args=[Mailbox.Provider.GMAIL_API]),
            {"oauth_source": "office"},
        )
        flow = self.client.session["triage_oauth_flow"]
        self.assertEqual(start.status_code, 302)
        with (
            patch("apps.hub.views.exchange_code", return_value=("access", "refresh")),
            patch("apps.hub.views.probe_mailbox", return_value="box@gmail.com"),
        ):
            callback = self.client.get(
                reverse("hub:triage-oauth-callback", args=[Mailbox.Provider.GMAIL_API]),
                {"state": flow["state"], "code": "code"},
            )
        self.assertRedirects(callback, reverse("hub:triage-connections"))
        self.assertFalse(Mailbox.objects.exists())
