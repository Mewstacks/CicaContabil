from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import Certificate, ClientCompany, NfseSync
from apps.hub.services import (
    certificate_cnpjs,
    import_certificate_upload,
    infer_certificate_passwords,
)
from apps.organizations.models import Membership, Organization

VALID_CNPJ = "19131243000197"


def _pfx(*, password: str, cnpj: str = VALID_CNPJ) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ACME CERTIFICADO A1")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.OtherName(
                        ObjectIdentifier("2.16.76.1.3.3"),
                        b"\x13\x0e" + cnpj.encode("ascii"),
                    )
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"acme", key, certificate, None, BestAvailableEncryption(password.encode())
    )


class CertificateImportTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa Acme",
            cnpj_masked="19.131.243/0001-97",
            dominio_code="001",
        )

    def test_extracts_official_icp_brasil_cnpj_and_infers_only_explicit_passwords(self) -> None:
        blob = _pfx(password="segredo-123")
        _, parsed, _ = pkcs12.load_key_and_certificates(blob, b"segredo-123")

        assert parsed is not None
        self.assertEqual(certificate_cnpjs(parsed), {VALID_CNPJ})
        self.assertEqual(
            infer_certificate_passwords("acme senha=segredo-123.pfx"),
            ("segredo-123", None),
        )
        self.assertEqual(
            infer_certificate_passwords("acme__segredo-123.p12", "senha-comum"),
            ("senha-comum", "segredo-123", None),
        )
        self.assertEqual(infer_certificate_passwords("Adriano - 1234.pfx"), ("1234", None))
        self.assertEqual(
            infer_certificate_passwords("Apville - Apville@2026.pfx"),
            ("Apville@2026", None),
        )
        self.assertEqual(infer_certificate_passwords("Bianchi 1234.pfx"), ("1234", None))

    def test_import_correlates_exact_company_without_retaining_filename(self) -> None:
        secret = "segredo-123"
        filename = f"cliente senha={secret}.pfx"

        result = import_certificate_upload(
            filename=filename,
            pfx_bytes=_pfx(password=secret),
            common_password="",
            companies=[self.company],
            actor=self.user,
        )

        self.assertEqual(result.status, "recognized")
        stored = Certificate.objects.get()
        self.assertEqual(stored.company, self.company)
        self.assertEqual(stored.label, "ACME CERTIFICADO A1")
        self.assertEqual(stored.password, secret)
        self.assertNotIn(secret, stored.label)
        event = AuditEvent.objects.get(action="hub.certificate.uploaded")
        self.assertNotIn(secret, str(event.metadata))
        self.assertNotIn(filename, str(event.metadata))
        sync = NfseSync.objects.get(company=self.company)
        self.assertTrue(sync.enabled)
        self.assertEqual(sync.status, NfseSync.Status.IDLE)
        self.assertEqual(sync.certificate, stored)

    def test_unmatched_or_duplicate_file_is_not_stored_again(self) -> None:
        blob = _pfx(password="segredo-123")
        first = import_certificate_upload(
            filename="acme__segredo-123.pfx",
            pfx_bytes=blob,
            common_password="",
            companies=[self.company],
            actor=self.user,
        )
        duplicate = import_certificate_upload(
            filename="outra-copia__segredo-123.pfx",
            pfx_bytes=blob,
            common_password="",
            companies=[self.company],
            actor=self.user,
        )

        self.assertEqual(first.status, "recognized")
        self.assertEqual(duplicate.status, "unrecognized")
        self.assertEqual(duplicate.reason, "duplicate")
        self.assertIn("já está cadastrado", duplicate.detail)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_batch_view_reports_recognized_and_unrecognized_without_echoing_names(self) -> None:
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()
        exposed_name = "cliente senha=segredo-123.pfx"
        invalid_name = "arquivo senha=senha-exposta.pfx"

        response = self.client.post(
            reverse("hub:certificates"),
            {
                "pfx_files": [
                    SimpleUploadedFile(
                        exposed_name,
                        _pfx(password="segredo-123"),
                        content_type="application/x-pkcs12",
                    ),
                    SimpleUploadedFile(
                        invalid_name, b"nao-e-pfx", content_type="application/x-pkcs12"
                    ),
                ],
                "common_password": "",
            },
            follow=True,
        )

        self.assertContains(response, "1 certificado vinculado automaticamente")
        self.assertContains(response, "1 arquivo ficou como não reconhecido")
        self.assertContains(response, "Empresa Acme")
        self.assertContains(response, "Arquivo 2")
        self.assertContains(response, "1 arquivo precisa de atenção")
        self.assertContains(response, "Selecionar novamente")
        self.assertEqual(response.context["certificate_import_summary"]["open_failed"], 1)
        self.assertNotContains(response, exposed_name)
        self.assertNotContains(response, invalid_name)
        self.assertNotContains(response, "senha-exposta")
        self.assertEqual(Certificate.objects.count(), 1)

    def test_certificate_page_renders_the_native_multi_file_control(self) -> None:
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

        response = self.client.get(reverse("hub:certificates"))

        self.assertEqual(set(response.context["form"].fields), {"pfx_files", "common_password"})
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'name="pfx_files"')
        self.assertContains(response, "multiple")
        self.assertContains(response, "Senha para abrir os certificados")
        self.assertContains(response, "Cada arquivo usa uma senha diferente?")
        self.assertContains(response, "Mostrar")
        self.assertContains(response, "Tentar novamente")
        self.assertContains(response, "Pular")
        self.assertContains(response, "Cancelar fila")
        self.assertContains(response, "Empresas sem A1 válido")
        self.assertNotContains(response, "data-modal-invalid")
        self.assertTrue(response.context["nfse_sync_runtime_enabled"] is False)
        self.assertNotContains(response, "A fila continua assim que ele abrir")

    def test_queue_upload_returns_a_retryable_password_failure_without_echoing_name(self) -> None:
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()
        exposed_name = "Cliente - senha-supersecreta.pfx"

        response = self.client.post(
            reverse("hub:certificates"),
            {
                "pfx_files": SimpleUploadedFile(
                    exposed_name, b"nao-e-pfx", content_type="application/x-pkcs12"
                ),
                "common_password": "",
                "queue_upload": "1",
                "queue_position": "1",
            },
            HTTP_X_CICA_CERTIFICATE_QUEUE="1",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["result"]
        self.assertEqual(payload["reason"], "open_failed")
        self.assertNotIn(exposed_name, str(payload))
        self.assertNotIn("senha-supersecreta", str(payload))
        self.assertEqual(
            self.client.session["certificate_import_queue"]["1"]["reason"],
            "open_failed",
        )
