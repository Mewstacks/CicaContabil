from __future__ import annotations

from unittest.mock import Mock, patch

from django.db import connection
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.organizations.models import Membership, Organization
from apps.triage.forms import IMAPConnectionForm
from apps.triage.imap import (
    MailboxIMAPError,
    _PinnedIMAP4SSL,
    probe_imap_mailbox,
    public_imap_address,
)
from apps.triage.models import Mailbox


class IMAPConnectionTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("imap-owner@example.test", "test-password-123")
        self.office = Organization.objects.create(name="Escritorio IMAP", slug="escritorio-imap")
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

    @staticmethod
    def form_data(**changes: str) -> dict[str, str]:
        values = {
            "address": "box@office.example",
            "host": "imap.provider.example",
            "username": "",
            "password": "fake-app-password",
            "folder": "INBOX",
        }
        values.update(changes)
        return values

    def test_host_and_folder_validation_reject_local_targets_and_commands(self) -> None:
        for host in ("localhost", "127.0.0.1", "imap.local", "imap.example.test"):
            form = IMAPConnectionForm(self.form_data(host=host))
            self.assertFalse(form.is_valid(), host)
            self.assertIn("host", form.errors)
        form = IMAPConnectionForm(self.form_data(folder="INBOX\r\nLOGOUT"))
        self.assertFalse(form.is_valid())
        self.assertIn("folder", form.errors)

    def test_dns_probe_rejects_private_and_mixed_answers(self) -> None:
        private = [(2, 1, 6, "", ("10.0.0.2", 993))]
        mixed = [(2, 1, 6, "", ("8.8.8.8", 993)), *private]
        for answers in (private, mixed):
            with (
                patch("apps.triage.imap.socket.getaddrinfo", return_value=answers),
                self.assertRaises(MailboxIMAPError),
            ):
                public_imap_address("imap.provider.example")

    def test_probe_uses_checked_address_tls_and_readonly_uid_search(self) -> None:
        with (
            patch("apps.triage.imap.public_imap_address", return_value="8.8.8.8"),
            patch("apps.triage.imap._PinnedIMAP4SSL") as factory,
        ):
            server = factory.return_value
            server.login.return_value = ("OK", [b"authenticated"])
            server.select.return_value = ("OK", [b"0"])
            server.uid.return_value = ("OK", [b""])
            probe_imap_mailbox(
                host="imap.provider.example",
                username="box@office.example",
                password="fake-app-password",
                folder="INBOX",
            )
            factory.assert_called_once_with("imap.provider.example", "8.8.8.8")
            server.select.assert_called_once_with("INBOX", readonly=True)
            server.uid.assert_called_once_with("search", None, "ALL")
            server.logout.assert_called_once()

    def test_tls_socket_uses_checked_ip_but_verifies_original_hostname(self) -> None:
        client = object.__new__(_PinnedIMAP4SSL)
        client._checked_address = "8.8.8.8"
        client.port = 993
        client.host = "imap.provider.example"
        client.ssl_context = Mock()
        with patch("apps.triage.imap.socket.create_connection") as connect:
            client._create_socket(10)
        connect.assert_called_once_with(("8.8.8.8", 993), timeout=10)
        client.ssl_context.wrap_socket.assert_called_once_with(
            connect.return_value, server_hostname="imap.provider.example"
        )

    def test_connection_encrypts_secret_and_does_not_start_intake(self) -> None:
        with patch("apps.hub.views.probe_imap_mailbox") as probe:
            response = self.client.post(reverse("hub:triage-imap-connect"), self.form_data())
        self.assertRedirects(response, reverse("hub:triage"))
        probe.assert_called_once_with(
            host="imap.provider.example",
            username="box@office.example",
            password="fake-app-password",
            folder="INBOX",
        )
        mailbox = Mailbox.objects.get(organization=self.office)
        self.assertEqual(mailbox.provider, Mailbox.Provider.IMAP)
        self.assertFalse(mailbox.active)
        self.assertIsNone(mailbox.since)
        self.assertEqual(mailbox.cursor, "")
        self.assertIn("fake-app-password", mailbox.credential)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT credential FROM triage_mailbox WHERE address = %s",
                ["box@office.example"],
            )
            raw = cursor.fetchone()[0]
        self.assertNotIn("fake-app-password", raw)

    def test_failed_probe_shows_recovery_without_echoing_secret(self) -> None:
        with patch(
            "apps.hub.views.probe_imap_mailbox",
            side_effect=MailboxIMAPError("A autenticação falhou. Confira a senha específica."),
        ):
            response = self.client.post(reverse("hub:triage-imap-connect"), self.form_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A autenticação falhou")
        self.assertNotContains(response, "fake-app-password")
        self.assertFalse(Mailbox.objects.exists())

    def test_non_admin_cannot_test_or_save_imap_credentials(self) -> None:
        Membership.objects.filter(organization=self.office, user=self.user).update(
            role=Membership.Role.OPERATOR
        )
        with patch("apps.hub.views.probe_imap_mailbox") as probe:
            response = self.client.post(reverse("hub:triage-imap-connect"), self.form_data())
        self.assertIn(response.status_code, (403, 404))
        probe.assert_not_called()
        self.assertFalse(Mailbox.objects.exists())
