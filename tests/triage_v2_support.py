"""Shared fixtures for the Triagem v2 tests (E11): offices, mailboxes, released items."""

from __future__ import annotations

from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import DestinationProfile, Mailbox, TriageItem
from apps.triage.security import ScanVerdict, scan_quarantined_item


class CleanScanner:
    def scan(self, stream: object) -> ScanVerdict:
        return ScanVerdict("clean", "test")


def alnum_cnpj(root12: str) -> str:
    """Complete a 12-char root with the two check digits (module 11, ASCII - 48)."""

    base = root12.upper()
    for weights in (
        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    ):
        remainder = sum((ord(c) - 48) * w for c, w in zip(base, weights, strict=True)) % 11
        base += str(0 if remainder < 2 else 11 - remainder)
    return base


def mask_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


class TriageV2Case(TestCase):
    """An office with a company, an active IMAP mailbox and an owner."""

    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = self.make_office("e11-office")
        self.company = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Sol",
            cnpj_masked="12.345.678/0001-95",
            dominio_code="417",
            tax_regime=ClientCompany.TaxRegime.SIMPLES,
        )
        self.mailbox = self.make_mailbox(self.office)
        self.owner = User.objects.create_user("owner-e11@office.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )

    def make_office(self, slug: str) -> Organization:
        office = Organization.objects.create(name=f"Office {slug}", slug=slug)
        DestinationProfile.objects.create(organization=office)
        ProductModule.objects.create(
            organization=office, code=ProductModule.Code.TRIAGE, enabled=True
        )
        return office

    def make_mailbox(self, office: Organization) -> Mailbox:
        return Mailbox.objects.create(
            organization=office,
            provider=Mailbox.Provider.IMAP,
            address=f"docs@{office.slug}.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
        )

    def released(
        self,
        *,
        filename: str,
        payload: bytes,
        subject: str = "",
        mailbox: Mailbox | None = None,
        message_id: str = "",
    ) -> TriageItem:
        item = receive_email_attachment(
            mailbox=mailbox or self.mailbox,
            message_id=message_id or f"m-{filename}",
            part_id="1",
            filename=filename,
            payload=payload,
            subject=subject,
            received_at=timezone.now(),
        ).item
        scan_quarantined_item(item=item, scanner=CleanScanner())
        return TriageItem.objects.get(pk=item.pk)

    def login(self, user: User | None = None, office: Organization | None = None) -> None:
        self.client.force_login(user or self.owner)
        session = self.client.session
        session["hub_organization_id"] = str((office or self.office).id)
        session.save()


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def make_png() -> bytes:
    """A real 1x1 PNG, built with Pillow so verify() accepts it."""

    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


PNG = make_png()


class FakeIMAP:
    """A read-only IMAP double serving ``raws`` (uid 1..n), all received at ``stamp``."""

    def __init__(self, raws: list[bytes], stamp: object) -> None:
        self.raws = raws
        self.stamp = stamp
        self.calls: list[tuple[object, ...]] = []

    def login(self, username: str, password: str):  # type: ignore[no-untyped-def]
        return "OK", [b"success"]

    def select(self, folder: str, readonly: bool = False):  # type: ignore[no-untyped-def]
        return "OK", [str(len(self.raws)).encode()]

    def response(self, code: str):  # type: ignore[no-untyped-def]
        return code, [b"900"]

    def uid(self, command: str, *args: object):  # type: ignore[no-untyped-def]
        self.calls.append((command, *args))
        if command == "search":
            return "OK", [" ".join(str(i + 1) for i in range(len(self.raws))).encode()]
        uid = int(str(args[0]))
        raw = self.raws[uid - 1]
        if args[1] == "(RFC822.SIZE INTERNALDATE)":
            stamp = self.stamp.strftime("%d-%b-%Y %H:%M:%S %z")  # type: ignore[attr-defined]
            return "OK", [f'1 (UID {uid} RFC822.SIZE {len(raw)} INTERNALDATE "{stamp}")'.encode()]
        return "OK", [(b"1 (BODY[] {n})", raw)]

    def logout(self) -> None:
        pass
