from __future__ import annotations

from itertools import pairwise

from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import (
    AgentFileJob,
    ChecklistEntry,
    ChecklistExpectation,
    CounterpartyAlias,
    DestinationProfile,
    DocumentType,
    Mailbox,
    TriageItem,
)
from apps.triage.services import decide_item, intake_manual
from apps.triage.transitions import InvalidTransition, TriageStatus, ensure_transition_allowed


class TransitionGraphTests(TestCase):
    """The state machine is pure data — no DB, no model instance required."""

    def test_the_happy_path_from_received_to_archived_is_allowed(self) -> None:
        path = [
            TriageStatus.RECEIVED,
            TriageStatus.QUARANTINED,
            TriageStatus.AWAITING_EXTRACTION,
            TriageStatus.EXTRACTING,
            TriageStatus.READY_TO_ARCHIVE,
            TriageStatus.ARCHIVING,
            TriageStatus.ARCHIVED,
        ]
        for current, target in pairwise(path):
            ensure_transition_allowed(current, target)  # must not raise

    def test_the_review_detour_is_allowed_both_ways(self) -> None:
        ensure_transition_allowed(TriageStatus.EXTRACTING, TriageStatus.AWAITING_REVIEW)
        ensure_transition_allowed(TriageStatus.AWAITING_REVIEW, TriageStatus.READY_TO_ARCHIVE)
        ensure_transition_allowed(TriageStatus.AWAITING_REVIEW, TriageStatus.REJECTED)

    def test_failure_retries_are_allowed(self) -> None:
        ensure_transition_allowed(TriageStatus.EXTRACTING, TriageStatus.FAILED)
        ensure_transition_allowed(TriageStatus.FAILED, TriageStatus.AWAITING_EXTRACTION)
        ensure_transition_allowed(TriageStatus.ARCHIVING, TriageStatus.ARCHIVE_FAILED)
        ensure_transition_allowed(TriageStatus.ARCHIVE_FAILED, TriageStatus.ARCHIVING)

    def test_terminal_states_accept_no_further_transition(self) -> None:
        for terminal in (TriageStatus.REJECTED, TriageStatus.ARCHIVED):
            for target in TriageStatus:
                if target == terminal:
                    continue
                with self.assertRaises(InvalidTransition):
                    ensure_transition_allowed(terminal, target)

    def test_skipping_a_state_is_rejected(self) -> None:
        """Received cannot jump straight to archived without quarantine and review."""

        with self.assertRaises(InvalidTransition):
            ensure_transition_allowed(TriageStatus.RECEIVED, TriageStatus.ARCHIVED)

    def test_an_unknown_status_string_is_rejected_not_silently_ignored(self) -> None:
        with self.assertRaises(InvalidTransition):
            ensure_transition_allowed("recebido", "estado_que_nao_existe")

    def test_every_status_has_an_entry_in_the_graph(self) -> None:
        """Guards against silently forgetting a status when the enum grows."""

        from apps.triage.transitions import _ALLOWED_TRANSITIONS

        for status in TriageStatus:
            self.assertIn(status, _ALLOWED_TRANSITIONS)


class TriageItemModelTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme-triage")
        self.other_organization = Organization.objects.create(name="Other", slug="other-triage")
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Acme", dominio_code="001"
        )

    def test_transition_to_updates_status_only_when_allowed(self) -> None:
        item = TriageItem.objects.create(
            organization=self.organization, original_name="extrato.pdf"
        )
        self.assertEqual(item.status, TriageStatus.RECEIVED)

        item.transition_to(TriageStatus.QUARANTINED)
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.status, TriageStatus.QUARANTINED)

    def test_transition_to_leaves_status_untouched_on_an_invalid_edge(self) -> None:
        item = TriageItem.objects.create(
            organization=self.organization, original_name="extrato.pdf"
        )

        with self.assertRaises(InvalidTransition):
            item.transition_to(TriageStatus.ARCHIVED)

        self.assertEqual(item.status, TriageStatus.RECEIVED)

    def test_duplicate_content_hash_keeps_both_receipts_for_review(self) -> None:
        first = TriageItem.objects.create(
            organization=self.organization,
            original_name="extrato.pdf",
            content_hash="a" * 64,
        )
        second = TriageItem.objects.create(
            organization=self.organization,
            original_name="extrato-copia.pdf",
            content_hash="a" * 64,
        )
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_the_same_hash_is_allowed_in_a_different_office(self) -> None:
        """A duplicate is a per-office concept, not a global one."""

        TriageItem.objects.create(
            organization=self.organization,
            original_name="extrato.pdf",
            content_hash="b" * 64,
        )

        # Must not raise.
        TriageItem.objects.create(
            organization=self.other_organization,
            original_name="extrato.pdf",
            content_hash="b" * 64,
        )

    def test_two_blank_hashes_do_not_collide(self) -> None:
        """The empty string is not itself a duplicate to guard against."""

        TriageItem.objects.create(organization=self.organization, original_name="a.pdf")
        # Must not raise: content_hash="" is excluded by the constraint's condition.
        TriageItem.objects.create(organization=self.organization, original_name="b.pdf")

    def test_duplicate_message_part_on_the_same_mailbox_is_rejected(self) -> None:
        mailbox = Mailbox.objects.create(
            organization=self.organization,
            provider=Mailbox.Provider.IMAP,
            address="documentos@escritorio.test",
        )
        TriageItem.objects.create(
            organization=self.organization,
            mailbox=mailbox,
            original_name="a.pdf",
            message_id="msg-1",
            part_id="1",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TriageItem.objects.create(
                organization=self.organization,
                mailbox=mailbox,
                original_name="a-again.pdf",
                message_id="msg-1",
                part_id="1",
            )

    def test_mailbox_supports_gmail_and_encrypts_long_checkpoints(self) -> None:
        token = "gmail-history-" + ("opaque-token-" * 40)
        mailbox = Mailbox.objects.create(
            organization=self.organization,
            provider=Mailbox.Provider.GMAIL_API,
            address="documentos@gmail.test",
            cursor=token,
        )
        with connection.cursor() as database_cursor:
            database_cursor.execute("SELECT cursor FROM triage_mailbox")
            stored = database_cursor.fetchone()[0]
        self.assertTrue(stored.startswith("enc:v1:"))
        self.assertNotIn(token, stored)
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.cursor, token)


class DestinationProfileTests(TestCase):
    def test_an_office_gets_exactly_one_destination_profile(self) -> None:
        organization = Organization.objects.create(name="Acme", slug="acme-destination")
        DestinationProfile.objects.create(
            organization=organization, mode=DestinationProfile.Mode.INTERNAL
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            DestinationProfile.objects.create(
                organization=organization, mode=DestinationProfile.Mode.WINDOWS
            )


class ChecklistTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme-checklist")
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Acme"
        )
        self.document_type = DocumentType.objects.create(
            organization=self.organization,
            code="extrato-banco",
            label="Extrato conta corrente",
            name_template="{codigo}_EXTRATO_BANCO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
            counterparty_kind=DocumentType.CounterpartyKind.BANCO,
        )

    def test_an_expectation_is_unique_per_company_and_document_type(self) -> None:
        ChecklistExpectation.objects.create(
            organization=self.organization, company=self.company, document_type=self.document_type
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ChecklistExpectation.objects.create(
                organization=self.organization,
                company=self.company,
                document_type=self.document_type,
            )

    def test_a_checklist_entry_counts_once_per_period(self) -> None:
        ChecklistEntry.objects.create(
            organization=self.organization,
            company=self.company,
            document_type=self.document_type,
            period_label="062026",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ChecklistEntry.objects.create(
                organization=self.organization,
                company=self.company,
                document_type=self.document_type,
                period_label="062026",
            )


class CounterpartyAliasTests(TestCase):
    def test_alias_is_unique_per_office(self) -> None:
        organization = Organization.objects.create(name="Acme", slug="acme-alias")
        CounterpartyAlias.objects.create(
            organization=organization,
            kind=DocumentType.CounterpartyKind.BANCO,
            token="BANRISUL",
            alias="Banco do Estado do Rio Grande do Sul",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CounterpartyAlias.objects.create(
                organization=organization,
                kind=DocumentType.CounterpartyKind.BANCO,
                token="BANRISUL",
                alias="Banco do Estado do Rio Grande do Sul",
            )


class AgentFileJobTests(TestCase):
    def test_a_job_starts_queued_and_can_be_claimed(self) -> None:
        organization = Organization.objects.create(name="Acme", slug="acme-agent-job")
        item = TriageItem.objects.create(organization=organization, original_name="a.pdf")
        job = AgentFileJob.objects.create(
            organization=organization,
            triage_item=item,
            destination_path=r"\\servidor\clientes\acme\extrato.pdf",
        )

        self.assertEqual(job.status, AgentFileJob.Status.QUEUED)

        job.status = AgentFileJob.Status.CLAIMED
        job.claimed_by = "agent-01"
        job.save()
        job.refresh_from_db()

        self.assertEqual(job.status, AgentFileJob.Status.CLAIMED)


class ManualIntakeTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="manual-intake")
        self.other_organization = Organization.objects.create(name="Other", slug="manual-other")
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Acme Ltda"
        )
        self.other_company = ClientCompany.objects.create(
            organization=self.other_organization, name="Other Ltda"
        )
        self.user = User.objects.create_user(email="operator@acme.test", password="not-a-secret")

    def _upload(self, name: str = "extrato.ofx") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, b"OFXHEADER:100", content_type="application/x-ofx")

    def test_manual_intake_stores_a_private_blob_and_waits_for_review(self) -> None:
        item = intake_manual(
            organization=self.organization,
            actor=self.user,
            company=self.company,
            document_type=None,
            upload=self._upload(),
        )

        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.events.count(), 4)
        self.assertTrue(
            item.blob.content.name.startswith(f"private/triage/{self.organization.id}/")
        )
        with self.assertRaises(SuspiciousFileOperation):
            _ = item.blob.content.url

    def test_manual_intake_refuses_cross_office_company(self) -> None:
        with self.assertRaises(ValidationError):
            intake_manual(
                organization=self.organization,
                actor=self.user,
                company=self.other_company,
                document_type=None,
                upload=self._upload(),
            )

    def test_reviewer_cannot_archive_unverified_manual_prototype(self) -> None:
        item = intake_manual(
            organization=self.organization,
            actor=self.user,
            company=self.company,
            document_type=None,
            upload=self._upload(),
        )

        with self.assertRaises(ValidationError):
            decide_item(item=item, actor=self.user, decision="archive", reason="")
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.destination_path, "")
        self.assertEqual(item.events.count(), 4)

    def test_reviewer_must_supply_a_reason_to_reject(self) -> None:
        item = intake_manual(
            organization=self.organization,
            actor=self.user,
            company=self.company,
            document_type=None,
            upload=self._upload(),
        )

        with self.assertRaises(ValidationError):
            decide_item(item=item, actor=self.user, decision="reject", reason="")
