"""Contrato do legado (L3/L4 de docs/specs/produto-vendavel.md).

Estes testes descrevem o que os clientes atuais recebem hoje na coleta NFS-e por A1 de
empresa. Eles passam antes e depois de qualquer mudança do produto novo: se um deles
quebrar, a mudança alterou o legado e deve ser refeita, não o teste.
"""

from __future__ import annotations

import base64
import ssl
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone

from apps.hub.models import Certificate, ClientCompany, NfseSync
from apps.hub.nfse_adn import AdnClient
from apps.hub.nfse_sync import certificate_ssl_context
from apps.hub.tasks import _eligible_nfse_syncs
from apps.organizations.models import Organization
from config.settings.base import aligned_periodic_minutes
from pki_support import make_pfx

OFFICE_CNPJ = "19131243000197"
COMPANY_CNPJ = "12345678000195"

# Entradas de agenda que existem hoje (nome da entrada -> tarefa). O produto novo pode
# acrescentar entradas, nunca remover nem renomear estas.
LEGACY_BEAT = {
    "generate-recurring-activities": "hub.generate_recurring_activities",
    "refresh-demo-operations": "hub.refresh_demo_operations",
    "notify-due-activities": "hub.notify_due_activities",
    "notify-expiring-certificates": "hub.notify_expiring_certificates",
    "purge-read-notifications": "hub.purge_read_notifications",
    "reap-stale-profitability-runs": "profitability.reap_stale_runs",
    "advance-tenant-lifecycles": "platform.advance_tenant_lifecycles",
    "close-previous-billing-competence": "platform.close_previous_competence",
    "refresh-approved-knowledge-chunks": "intelligence.refresh_knowledge_chunks",
    "refresh-shared-knowledge-chunks": "intelligence.refresh_shared_knowledge_chunks",
    "purge-expired-intelligence-conversations": "intelligence.purge_expired_conversations",
    "retry-pending-intelligence-attachments": "intelligence.retry_pending_attachments",
    "dispatch-active-nfse-syncs": "hub.dispatch_active_nfse_syncs",
    "refresh-nfse-facts": "hub.refresh_nfse_facts",
    "refresh-reform-radar": "hub.refresh_reform_sources",
    "recover-reconciliation-runs": "hub.recover_reconciliation_runs",
    "dispatch-waiting-reconciliation-runs": "hub.dispatch_waiting_reconciliation_runs",
    "recover-financial-report-exports": "hub.recover_financial_report_exports",
    "recover-triage-pipeline": "triage.recover_pipeline",
    "dispatch-waiting-financial-report-exports": "hub.dispatch_waiting_financial_report_exports",
    "recover-crosscheck-runs": "crosscheck.recover_runs",
    "purge-expired-crosscheck": "crosscheck.purge_expired",
}


def test_legacy_beat_schedule_entries_are_unchanged() -> None:
    schedule = settings.CELERY_BEAT_SCHEDULE
    for name, task in LEGACY_BEAT.items():
        assert name in schedule, f"entrada de agenda removida: {name}"
        assert schedule[name]["task"] == task
    assert schedule["dispatch-active-nfse-syncs"]["schedule"] == aligned_periodic_minutes(
        settings.NFSE_ADN_POLL_INTERVAL_MINUTES
    )


def test_adn_request_shape_for_a_company_certificate_is_pinned() -> None:
    seen: dict[str, object] = {}

    def transport(
        url: str, *, headers: dict[str, str], context: ssl.SSLContext
    ) -> tuple[int, bytes]:
        seen.update(url=url, headers=headers, context=context)
        return 200, b'{"LoteDFe": [], "UltimoNSU": 5, "MaxNSU": 5}'

    context = ssl.create_default_context()
    client = AdnClient(environment="production", ssl_context=context, transport=transport)

    page = client.fetch_page(last_nsu=5, cnpj="12.345.678/0001-95")

    assert page.last_nsu == 5
    assert seen["url"] == (
        "https://adn.nfse.gov.br/contribuintes/DFe/5?lote=true&cnpjConsulta=12345678000195"
    )
    assert seen["headers"] == {"Accept": "application/json", "User-Agent": "CICA-NFSe/1.0"}
    assert seen["context"] is context


@pytest.mark.parametrize(
    ("status", "transient"),
    [(401, False), (403, False), (404, True), (429, True), (503, True), (400, False)],
)
def test_adn_status_mapping_for_the_legacy_client_is_pinned(status: int, transient: bool) -> None:
    from apps.hub.nfse_adn import AdnError

    client = AdnClient(
        environment="production",
        ssl_context=ssl.create_default_context(),
        transport=lambda *_a, **_k: (status, b""),
    )

    with pytest.raises(AdnError) as error:
        client.fetch_page(last_nsu=0, cnpj=COMPANY_CNPJ)

    assert error.value.transient is transient


def _company(office: Organization, name: str = "Empresa") -> ClientCompany:
    return ClientCompany.objects.create(
        organization=office, name=name, cnpj_masked="12.345.678/0001-95"
    )


def _certificate(office: Organization, company: ClientCompany, **extra: object) -> Certificate:
    values: dict[str, object] = {
        "label": "A1",
        "pfx_blob": "dummy",
        "password": "dummy",
        "fingerprint_sha256": uuid.uuid4().hex * 2,
        "valid_until": timezone.now() + timedelta(days=30),
    }
    values.update(extra)
    return Certificate.objects.create(organization=office, company=company, **values)


@pytest.mark.django_db
@override_settings(NFSE_ADN_SYNC_ENABLED=True)
def test_legacy_dispatcher_only_sees_syncs_that_have_a_company_certificate() -> None:
    """Invariante de isolamento das filas: linha sem `certificate` nunca é do legado."""

    office = Organization.objects.create(name="Legacy", slug="legacy-contract")
    with_certificate = _company(office, "Com A1")
    without_certificate = _company(office, "Sem A1")
    due = NfseSync.objects.create(
        organization=office,
        company=with_certificate,
        certificate=_certificate(office, with_certificate),
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    orphan = NfseSync.objects.create(
        organization=office,
        company=without_certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    from apps.hub.tasks import dispatch_active_nfse_syncs

    assert list(_eligible_nfse_syncs().values_list("pk", flat=True)) == [due.pk]
    with patch("apps.hub.tasks.poll_nfse_sync.delay") as queued:
        assert dispatch_active_nfse_syncs() == 1
        queued.assert_called_once_with(str(due.pk))
    orphan.refresh_from_db()
    assert orphan.status == NfseSync.Status.IDLE


@pytest.mark.django_db
@override_settings(NFSE_ADN_SYNC_ENABLED=True, NFSE_ADN_ENVIRONMENT="production")
def test_legacy_poll_builds_the_tls_context_from_the_company_certificate() -> None:
    office = Organization.objects.create(name="Poll", slug="legacy-poll")
    company = _company(office)
    certificate = _certificate(office, company)
    sync = NfseSync.objects.create(
        organization=office,
        company=company,
        certificate=certificate,
        enabled=True,
        status=NfseSync.Status.IDLE,
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    from apps.hub.tasks import poll_nfse_sync

    with (
        patch("apps.hub.tasks.certificate_ssl_context", return_value=object()) as context,
        patch("apps.hub.tasks.AdnClient", return_value=object()) as client,
        patch(
            "apps.hub.tasks.process_sync_pages",
            return_value={"state": "completed", "pages": 1, "documents_created": 0},
        ),
        patch("apps.hub.tasks.dispatch_active_nfse_syncs.apply_async"),
    ):
        assert poll_nfse_sync(str(sync.pk))["state"] == "completed"

    context.assert_called_once()
    assert context.call_args.args[0].pk == certificate.pk
    assert client.call_args.kwargs["environment"] == "production"


@pytest.mark.django_db
def test_legacy_certificate_context_requires_the_company_cnpj_root() -> None:
    office = Organization.objects.create(name="Root", slug="legacy-root")
    company = _company(office)
    same_root = base64.b64encode(make_pfx(password="s3nha", cnpj="12345678000276")).decode()
    other_root = base64.b64encode(make_pfx(password="s3nha", cnpj=OFFICE_CNPJ)).decode()

    accepted = _certificate(office, company, pfx_blob=same_root, password="s3nha")
    rejected = _certificate(office, company, pfx_blob=other_root, password="s3nha")

    assert isinstance(certificate_ssl_context(accepted), ssl.SSLContext)
    with pytest.raises(ValidationError, match="raiz"):
        certificate_ssl_context(rejected)


@pytest.mark.django_db
def test_legacy_certificate_context_refuses_revoked_and_expired_certificates() -> None:
    office = Organization.objects.create(name="Status", slug="legacy-status")
    company = _company(office)
    revoked = _certificate(office, company, revoked_at=timezone.now())
    expired = _certificate(office, company, valid_until=timezone.now() - timedelta(days=1))

    with pytest.raises(ValidationError, match="revogado"):
        certificate_ssl_context(revoked)
    with pytest.raises(ValidationError, match="vencido"):
        certificate_ssl_context(expired)


NEW_NOT_NULL_COLUMNS = [
    ("hub_officeprofile", "nfse_collection_mode", "certificate"),
    ("hub_nfsesync", "credential_mode", "certificate"),
    ("hub_nfsesync", "procuracao_status", "unknown"),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("table", "column", "expected"), NEW_NOT_NULL_COLUMNS)
def test_new_not_null_columns_carry_a_database_default(
    table: str, column: str, expected: str
) -> None:
    """Código de antes da coluna (canário, worker antigo) continua inserindo linhas válidas."""

    from django.db import connection

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({table})")
            defaults = {row[1]: row[4] for row in cursor.fetchall()}
        else:
            cursor.execute(
                "SELECT column_name, column_default FROM information_schema.columns "
                "WHERE table_name = %s",
                [table],
            )
            defaults = dict(cursor.fetchall())
    assert expected in str(defaults[column])


@pytest.mark.django_db
def test_every_existing_row_and_every_default_is_legacy() -> None:
    from apps.hub.models import OfficeProfile

    office = Organization.objects.create(name="Defaults", slug="legacy-defaults")
    profile = OfficeProfile.objects.create(organization=office)
    company = _company(office)
    sync = NfseSync.objects.create(organization=office, company=company)

    assert profile.nfse_collection_mode == OfficeProfile.NfseCollectionMode.CERTIFICATE
    assert sync.credential_mode == NfseSync.CredentialMode.CERTIFICATE
    assert sync.procuracao_status == NfseSync.ProcuracaoStatus.UNKNOWN
    assert sync.office_certificate_id is None


def test_the_procuracao_lane_adds_nothing_to_the_schedule_while_its_flag_is_off() -> None:
    assert settings.NFSE_PROCURACAO_SYNC_ENABLED is False
    assert "dispatch-procuracao-syncs" not in settings.CELERY_BEAT_SCHEDULE
    # `tasks_radar` (E14) only registers a task that returns 0 while its own flag is off.
    assert settings.CELERY_IMPORTS == ("apps.hub.tasks_procuracao", "apps.hub.tasks_radar")


def test_the_procuracao_beat_entry_exists_only_when_the_flag_is_on() -> None:
    import importlib

    from config.settings import base

    with patch.dict("os.environ", {"NFSE_PROCURACAO_SYNC_ENABLED": "true"}):
        reloaded = importlib.reload(base)
        try:
            assert reloaded.CELERY_BEAT_SCHEDULE["dispatch-procuracao-syncs"]["task"] == (
                "hub.dispatch_procuracao_syncs"
            )
            assert {
                name: entry["task"]
                for name, entry in reloaded.CELERY_BEAT_SCHEDULE.items()
                if name in LEGACY_BEAT
            } == LEGACY_BEAT
        finally:
            with patch.dict("os.environ", {"NFSE_PROCURACAO_SYNC_ENABLED": "false"}):
                importlib.reload(base)
