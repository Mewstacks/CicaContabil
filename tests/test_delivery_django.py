"""Envio ao cliente: conta cifrada, fila, histórico, reenvio, liberação e portões da tela."""

from __future__ import annotations

import base64
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.delivery import services, transports
from apps.delivery.models import Delivery, DeliveryAccount
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    ObligationDelivery,
    ProductModule,
)
from apps.organizations.models import Membership, Organization


class FakeTransport:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> str:
        if self.error:
            raise self.error
        self.sent.append(message)
        return str(message["Message-ID"])


class DeliveryCase(TestCase):
    def setUp(self) -> None:
        self.enterContext(
            mock.patch("apps.delivery.transports.resolve_host", return_value=["93.184.216.34"])
        )
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Escritório A", slug="escritorio-a")
        self.other = Organization.objects.create(name="Escritório B", slug="escritorio-b")
        self.user = User.objects.create_user(email="dono@example.com", password="uma-senha-longa")
        Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.office, name="Padaria Central", contact_email="padaria@example.com"
        )
        self.stranger = ClientCompany.objects.create(organization=self.other, name="Outra")
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.DELIVERY, enabled=True
        )
        self.account = DeliveryAccount.objects.create(
            organization=self.office,
            from_address="contador@escritorio.com.br",
            smtp_host="smtp.example.com",
            smtp_username="contador@escritorio.com.br",
            smtp_password="segredo-smtp",
        )
        self.client = self.login(self.user)

    def login(self, user: User) -> Client:
        client = Client()
        client.force_login(user)
        session = client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()
        return client

    def make(self, **kwargs: Any) -> Delivery:
        values: dict[str, Any] = {
            "organization": self.office,
            "company": self.company,
            "recipients": "padaria@example.com",
            "subject": "Guias 10/2026",
            "body": "Seguem as guias.",
            "attachments": [("guia.pdf", b"%PDF-1.4 guia")],
            "requested_by": self.user,
        }
        values.update(kwargs)
        with self.captureOnCommitCallbacks(execute=False):
            return services.create_delivery(**values)


class AccountSecretTests(DeliveryCase):
    def test_secret_is_encrypted_at_rest_and_sender_is_the_login(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "select smtp_password from delivery_deliveryaccount where id = %s",
                [self.account.pk.hex],
            )
            raw = cursor.fetchone()[0]
        assert raw.startswith("enc:v1") and "segredo-smtp" not in raw
        assert self.account.sender_address == "contador@escritorio.com.br"

    def test_sender_must_match_authenticated_login(self) -> None:
        self.account.from_address = "outro@escritorio.com.br"
        with self.assertRaises(ValidationError):
            self.account.clean()

    def test_graph_account_requires_tenant_and_app(self) -> None:
        graph = DeliveryAccount(
            organization=self.other,
            provider=DeliveryAccount.Provider.GRAPH,
            from_address="a@b.com",
        )
        with self.assertRaises(ValidationError):
            graph.clean()


class CreateAndSendTests(DeliveryCase):
    def test_sends_with_attachment_and_records_history(self) -> None:
        delivery = self.make()
        fake = FakeTransport()
        assert services.process_delivery(str(delivery.pk), transport=fake) == "sent"
        delivery.refresh_from_db()
        assert delivery.status == Delivery.Status.SENT
        assert delivery.sender == "contador@escritorio.com.br"
        assert delivery.attempts == 1 and delivery.sent_at is not None
        message = fake.sent[0]
        assert message["To"] == "padaria@example.com"
        assert str(message["From"]) == "contador@escritorio.com.br"
        assert [part.get_filename() for part in message.iter_attachments()] == ["guia.pdf"]

    def test_attachments_over_30mb_are_refused(self) -> None:
        big = [("a.bin", b"0" * (16 * 1024 * 1024)), ("b.bin", b"0" * (15 * 1024 * 1024))]
        with self.assertRaises(ValidationError):
            self.make(attachments=big)
        assert not Delivery.objects.exists()

    def test_company_of_another_office_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            self.make(company=self.stranger)

    def test_invalid_recipient_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            self.make(recipients="isto-nao-e-email")

    def test_recipients_are_deduplicated(self) -> None:
        assert services.parse_recipients("A@x.com; a@x.com, b@x.com") == ["A@x.com", "b@x.com"]

    def test_temporary_failure_retries_then_fails_with_error_kept(self) -> None:
        delivery = self.make()
        down = FakeTransport(transports.TemporaryDeliveryError("O servidor não respondeu."))
        assert services.process_delivery(str(delivery.pk), transport=down) == "retry"
        delivery.refresh_from_db()
        assert delivery.status == Delivery.Status.QUEUED and delivery.next_attempt_at
        # antes do recuo, uma reentrega do Celery não envia nada
        assert services.process_delivery(str(delivery.pk), transport=down) == "skipped"
        for _ in range(2):
            Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
            outcome = services.process_delivery(str(delivery.pk), transport=down)
        assert outcome == "failed"
        delivery.refresh_from_db()
        assert delivery.status == Delivery.Status.FAILED
        assert delivery.attempts == 3 and "não respondeu" in delivery.last_error

    def test_permanent_failure_fails_at_once(self) -> None:
        delivery = self.make()
        refused = FakeTransport(transports.PermanentDeliveryError("recusou"))
        assert services.process_delivery(str(delivery.pk), transport=refused) == "failed"

    def test_missing_account_fails_without_leaking(self) -> None:
        DeliveryAccount.objects.all().delete()
        delivery = self.make()
        assert services.process_delivery(str(delivery.pk), transport=FakeTransport()) == "failed"
        delivery.refresh_from_db()
        assert "conta de envio" in delivery.last_error

    def test_sent_delivery_is_not_sent_twice(self) -> None:
        delivery = self.make()
        fake = FakeTransport()
        services.process_delivery(str(delivery.pk), transport=fake)
        assert services.process_delivery(str(delivery.pk), transport=fake) == "skipped"
        assert len(fake.sent) == 1

    def test_tampered_attachment_is_refused(self) -> None:
        delivery = self.make()
        item = delivery.attachments.get()
        Delivery.objects.filter(pk=delivery.pk)  # no-op: keep query style simple
        type(item).objects.filter(pk=item.pk).update(sha256="0" * 64)
        assert services.process_delivery(str(delivery.pk), transport=FakeTransport()) == "failed"

    def test_obligation_delivery_mirrors_result(self) -> None:
        template = ActivityTemplate.objects.create(
            organization=self.office, code="DAS", title="DAS", area=ActivityTemplate.Area.FISCAL
        )
        assignment = ActivityTemplateAssignment.objects.create(
            organization=self.office, company=self.company, template=template
        )
        linked = ObligationDelivery.objects.create(
            organization=self.office, assignment=assignment, competence=date(2026, 10, 1)
        )
        delivery = self.make(obligation_delivery=linked)
        services.process_delivery(str(delivery.pk), transport=FakeTransport())
        linked.refresh_from_db()
        assert linked.email_status == ObligationDelivery.EmailStatus.SENT
        assert linked.email_recipient == "padaria@example.com"
        assert linked.sent_to_client_at is not None


class ReleaseDayTests(DeliveryCase):
    def test_release_date_is_next_month_clamped(self) -> None:
        self.company.email_release_day = 31
        assert services.release_date(self.company, date(2026, 1, 1)) == date(2026, 2, 28)
        assert services.release_date(self.company, date(2026, 12, 1)) == date(2027, 1, 31)
        self.company.email_release_day = None
        assert services.release_date(self.company, date(2026, 1, 1)) is None

    def test_delivery_waits_for_release_day_then_dispatches(self) -> None:
        today = timezone.localdate()
        competence = date(today.year, today.month, 1)
        self.company.email_release_day = min(28, today.day)
        # competência do mês corrente: o dia vale para o mês seguinte, então fica retida
        self.company.save()
        held = self.make(competence=competence)
        assert held.status == Delivery.Status.SCHEDULED and held.release_on
        assert services.process_delivery(str(held.pk), transport=FakeTransport()) == "skipped"
        with mock.patch("apps.delivery.tasks.send_delivery_task.delay") as delay:
            later = timezone.now() + timedelta(days=62)
            assert services.dispatch_due(later) == 1
        delay.assert_called_once_with(str(held.pk))
        held.refresh_from_db()
        assert held.status == Delivery.Status.QUEUED


class ResendCancelTests(DeliveryCase):
    def test_resend_copies_attachments_and_keeps_original(self) -> None:
        delivery = self.make()
        services.process_delivery(str(delivery.pk), transport=FakeTransport())
        delivery.refresh_from_db()
        again = services.resend(delivery, requested_by=self.user)
        assert again.pk != delivery.pk and again.resend_of_id == delivery.pk
        assert again.attachments.get().sha256 == delivery.attachments.get().sha256
        delivery.refresh_from_db()
        assert delivery.status == Delivery.Status.SENT

    def test_cannot_resend_something_still_queued(self) -> None:
        with self.assertRaises(ValidationError):
            services.resend(self.make(), requested_by=self.user)

    def test_cancel_only_before_sending(self) -> None:
        delivery = self.make()
        services.cancel(delivery, actor=self.user)
        delivery.refresh_from_db()
        assert delivery.status == Delivery.Status.CANCELLED
        with self.assertRaises(ValidationError):
            services.cancel(delivery, actor=self.user)


class TransportTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(
            mock.patch("apps.delivery.transports.resolve_host", return_value=["93.184.216.34"])
        )

    def account(self, **kwargs: Any) -> DeliveryAccount:
        return DeliveryAccount(
            from_address="c@escritorio.com.br",
            smtp_host="smtp.example.com",
            smtp_username="c@escritorio.com.br",
            smtp_password="x",
            **kwargs,
        )

    def message(self, account: DeliveryAccount) -> EmailMessage:
        return transports.build_message(
            account=account,
            recipients=["a@b.com"],
            subject="s",
            body="b",
            attachments=[("g.pdf", b"x")],
        )

    def test_smtp_auth_error_is_permanent_and_hides_server_text(self) -> None:
        account = self.account()
        with mock.patch("apps.delivery.transports._PinnedSMTPSSL") as ssl_client:
            ssl_client.return_value.__enter__.return_value.login.side_effect = (
                smtplib.SMTPAuthenticationError(535, b"senha errada de fulano")
            )
            with self.assertRaises(transports.PermanentDeliveryError) as raised:
                transports.SmtpTransport(account).send(self.message(account))
        assert "fulano" not in str(raised.exception)

    def test_smtp_4xx_is_temporary(self) -> None:
        account = self.account()
        with mock.patch("apps.delivery.transports._PinnedSMTPSSL") as ssl_client:
            ssl_client.return_value.__enter__.return_value.send_message.side_effect = (
                smtplib.SMTPResponseException(451, b"later")
            )
            with self.assertRaises(transports.TemporaryDeliveryError):
                transports.SmtpTransport(account).send(self.message(account))

    def test_graph_sends_base64_mime_with_bearer_token(self) -> None:
        account = DeliveryAccount(
            provider=DeliveryAccount.Provider.GRAPH,
            from_address="c@escritorio.com.br",
            graph_tenant_id="tenant",
            graph_client_id="app",
            graph_client_secret="segredo",
        )
        calls: list[tuple[str, dict[str, str], bytes]] = []

        def post(url: str, headers: dict[str, str], data: bytes) -> tuple[int, bytes]:
            calls.append((url, headers, data))
            if "oauth2" in url:
                return 200, b'{"access_token": "tok"}'
            return 202, b""

        message = self.message(account)
        transports.GraphTransport(account, post=post).send(message)
        url, headers, data = calls[1]
        assert url.endswith("/users/c%40escritorio.com.br/sendMail")
        assert headers["Authorization"] == "Bearer tok" and headers["Content-Type"] == "text/plain"
        assert b"g.pdf" in base64.b64decode(data)

    def test_graph_bad_credentials_are_permanent(self) -> None:
        account = DeliveryAccount(
            provider=DeliveryAccount.Provider.GRAPH,
            from_address="c@x.com",
            graph_tenant_id="t",
            graph_client_id="a",
            graph_client_secret="s",
        )
        with self.assertRaises(transports.PermanentDeliveryError):
            transports.GraphTransport(account, post=lambda *_: (401, b"{}")).check()


class ScreenTests(DeliveryCase):
    def test_list_detail_and_tenant_isolation(self) -> None:
        delivery = self.make()
        assert self.client.get(reverse("delivery:index")).status_code == 200
        response = self.client.get(reverse("delivery:detail", args=[delivery.pk]))
        assert response.status_code == 200 and "guia.pdf" in response.content.decode()
        outsider = User.objects.create_user(email="x@example.com", password="uma-senha-longa")
        Membership.objects.create(
            organization=self.other, user=outsider, role=Membership.Role.OWNER
        )
        client = Client()
        client.force_login(outsider)
        session = client.session
        session["hub_organization_id"] = str(self.other.id)
        session.save()
        assert client.get(reverse("delivery:detail", args=[delivery.pk])).status_code in {403, 404}

    def test_module_off_blocks_screen(self) -> None:
        ProductModule.objects.filter(organization=self.office).update(enabled=False)
        assert self.client.get(reverse("delivery:index")).status_code == 403

    def test_compose_creates_delivery_with_upload(self) -> None:
        response = self.client.post(
            reverse("delivery:compose"),
            {
                "company": str(self.company.pk),
                "recipients": "padaria@example.com",
                "subject": "Guias",
                "body": "Seguem.",
                "files": SimpleUploadedFile("guia.pdf", b"%PDF-1.4 x"),
            },
        )
        assert response.status_code == 302
        delivery = Delivery.objects.get()
        assert delivery.attachments.get().filename == "guia.pdf"

    def test_read_only_role_cannot_compose_or_configure(self) -> None:
        viewer = User.objects.create_user(email="v@example.com", password="uma-senha-longa")
        Membership.objects.create(
            organization=self.office, user=viewer, role=Membership.Role.AUDITOR
        )
        client = self.login(viewer)
        assert client.get(reverse("delivery:index")).status_code == 200
        assert client.get(reverse("delivery:compose")).status_code == 403
        assert client.get(reverse("delivery:account")).status_code == 403

    def test_account_secret_never_rendered_and_blank_keeps_it(self) -> None:
        page = self.client.get(reverse("delivery:account")).content.decode()
        assert "segredo-smtp" not in page
        response = self.client.post(
            reverse("delivery:account"),
            {
                "provider": "smtp",
                "from_name": "Escritório",
                "from_address": "contador@escritorio.com.br",
                "smtp_host": "smtp.example.com",
                "smtp_port": "465",
                "smtp_security": "ssl",
                "smtp_username": "contador@escritorio.com.br",
                "smtp_password": "",
                "active": "on",
            },
        )
        assert response.status_code == 302
        self.account.refresh_from_db()
        assert self.account.smtp_password == "segredo-smtp"

    def test_release_day_is_saved_per_company_and_validated(self) -> None:
        url = reverse("delivery:release-days")
        self.client.post(url, {"company": str(self.company.pk), "day": "12"})
        self.company.refresh_from_db()
        assert self.company.email_release_day == 12
        self.client.post(url, {"company": str(self.company.pk), "day": "40"})
        self.company.refresh_from_db()
        assert self.company.email_release_day == 12
        # empresa de outro escritório: 404
        assert (
            self.client.post(url, {"company": str(self.stranger.pk), "day": "5"}).status_code == 404
        )


class SecretAndEndpointTests(DeliveryCase):
    def post_account(self, **overrides: str) -> Any:
        data = {
            "provider": "smtp",
            "from_name": "Escritório",
            "from_address": "contador@escritorio.com.br",
            "smtp_host": "smtp.example.com",
            "smtp_port": "465",
            "smtp_security": "ssl",
            "smtp_username": "contador@escritorio.com.br",
            "smtp_password": "",
            "active": "on",
        }
        data.update(overrides)
        return self.client.post(reverse("delivery:account"), data)

    def test_changing_host_without_retyping_password_is_refused(self) -> None:
        response = self.post_account(smtp_host="smtp.outro.com")
        assert response.status_code == 200
        self.account.refresh_from_db()
        assert self.account.smtp_host == "smtp.example.com"

    def test_internal_host_and_odd_port_are_refused(self) -> None:
        with mock.patch("apps.delivery.transports.resolve_host", return_value=["10.0.0.5"]):
            assert self.post_account(smtp_password="x").status_code == 200
        assert self.post_account(smtp_port="6379", smtp_password="x").status_code == 200
        self.account.refresh_from_db()
        assert self.account.smtp_port == 465

    def test_transport_refuses_internal_address_at_send_time(self) -> None:
        with (
            mock.patch("apps.delivery.transports.resolve_host", return_value=["127.0.0.1"]),
            self.assertRaises(transports.PermanentDeliveryError),
        ):
            transports.SmtpTransport(self.account).check()

    def test_connection_goes_to_the_validated_ip_not_a_second_lookup(self) -> None:
        account = self.account
        seen: list[tuple[str, int]] = []

        def fake_connection(address: tuple[str, int], timeout: float) -> Any:
            seen.append(address)
            raise OSError("sem rede no teste")

        with (
            mock.patch("socket.create_connection", side_effect=fake_connection),
            self.assertRaises(transports.TemporaryDeliveryError),
        ):
            transports.SmtpTransport(account).check()
        assert seen == [("93.184.216.34", 465)]
