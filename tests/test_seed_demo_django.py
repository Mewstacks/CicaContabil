from __future__ import annotations

import io
import re
import zipfile
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.demo_session import cleanup_stale_demo_visitors
from apps.hub.models import (
    Certificate,
    ClientCompany,
    DctfWebDocument,
    DteMessage,
    DteMessageAccess,
    DteRun,
    FiscalGuide,
    NfseDocument,
    NfseSync,
    ParcelamentoOperation,
    ReconciliationMatch,
    ReformAlert,
    ReviewCase,
)
from apps.hub.services import nfse_company_archive_folder
from apps.intelligence.models import Conversation, Message
from apps.organizations.models import Membership, Organization
from apps.triage.models import TriageItem, TriageSafetyScan

pytestmark = pytest.mark.django_db


def _seed() -> None:
    call_command("seed_demo", "--password", "seed-only-password-9f2c", verbosity=0)


@override_settings(DEBUG=True)
def test_seed_populates_every_screen_with_data() -> None:
    _seed()

    organization = Organization.objects.get(slug="escritorio-demo")
    assert organization.is_demo
    assert ClientCompany.objects.filter(organization=organization).count() == 8
    document = NfseDocument.objects.filter(organization=organization).first()
    assert document is not None
    assert str(document.normalized_data["number"]).startswith("DEMO-")
    assert "fictíci" in str(document.normalized_data["service_description"]).casefold()
    assert DteMessage.objects.filter(organization=organization, read_at=None).exists()
    assert (
        FiscalGuide.objects.filter(organization=organization, kind=FiscalGuide.Kind.DCTFWEB).count()
        == 3
    )
    assert TriageItem.objects.filter(organization=organization).count() == 2
    assert (
        TriageSafetyScan.objects.filter(organization=organization, engine="demo-simulado").count()
        == 2
    )


@override_settings(DEBUG=True)
def test_seed_is_idempotent() -> None:
    _seed()
    first = NfseDocument.objects.count()
    _seed()

    assert NfseDocument.objects.count() == first
    assert Organization.objects.filter(slug="escritorio-demo").count() == 1


@override_settings(DEBUG=False, SEED_DEMO_ALLOWED=False)
def test_seed_refuses_to_fabricate_evidence_outside_debug() -> None:
    with pytest.raises(CommandError):
        _seed()


@override_settings(DEBUG=True)
def test_seed_refuses_an_existing_operational_office_slug() -> None:
    office = Organization.objects.create(name="Escritório piloto real", slug="escritorio-demo")
    with pytest.raises(CommandError, match="escritório operacional"):
        _seed()
    office.refresh_from_db()
    assert not office.is_demo
    assert not ClientCompany.objects.filter(organization=office).exists()


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_separate_demo_link_only_enters_flagged_office_with_browser_session(client) -> None:
    entry = reverse("hub:demo-entry")
    unavailable = client.get(entry)
    assert unavailable.status_code == 200
    assert "a demonstração separada está sendo preparada" in unavailable.content.decode().lower()
    _seed()
    available = client.get(entry)
    assert "Iniciar demonstração fictícia" in available.content.decode()
    started = client.post(entry)
    assert started.status_code == 302
    assert started["Location"] == reverse("hub:dashboard")
    assert client.session.get_expire_at_browser_close()
    visitor = Membership.objects.get(user__email__startswith="demo-", organization__is_demo=True)
    assert not visitor.user.has_usable_password()
    assert client.session["hub_organization_id"] == str(visitor.organization_id)


def test_demo_cleanup_removes_only_expired_guests_owned_exclusively_by_demo_office() -> None:
    demo = Organization.objects.create(name="Demo central", slug="demo-central", is_demo=True)
    real = Organization.objects.create(name="EscritÃ³rio real", slug="escritorio-real")
    expired = User.objects.create_user(email="demo-expired@example.test")
    recent = User.objects.create_user(email="demo-recent@example.test")
    password_user = User.objects.create_user(
        email="demo-password@example.test", password="senha-forte-de-teste"
    )
    mixed = User.objects.create_user(email="demo-mixed@example.test")
    old_joined = timezone.now() - timedelta(hours=25)
    User.objects.filter(id__in=[expired.id, password_user.id, mixed.id]).update(
        date_joined=old_joined
    )
    Membership.objects.create(organization=demo, user=expired)
    Membership.objects.create(organization=demo, user=recent)
    Membership.objects.create(organization=demo, user=password_user)
    Membership.objects.create(organization=demo, user=mixed)
    Membership.objects.create(organization=real, user=mixed)

    assert cleanup_stale_demo_visitors(demo) >= 1
    assert not User.objects.filter(id=expired.id).exists()
    assert User.objects.filter(id=recent.id).exists()
    assert User.objects.filter(id=password_user.id).exists()
    assert User.objects.filter(id=mixed.id).exists()


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_guide_issuance_is_private_to_each_browser_session() -> None:
    _seed()
    guide = FiscalGuide.objects.filter(reference__startswith="DEMO-DCTFWEB-").first()
    assert guide is not None
    first, second = Client(REMOTE_ADDR="198.51.100.11"), Client(REMOTE_ADDR="198.51.100.12")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302

    detail = reverse("hub:guide-detail", args=[guide.id])
    pdf = reverse("hub:demo-guide-pdf", args=[guide.id])
    assert "Pronta" in first.get(detail).content.decode()
    assert "Pronta" in second.get(detail).content.decode()
    assert first.post(reverse("hub:issue-guide", args=[guide.id])).status_code == 302
    assert "Baixar DARF fictício" in first.get(detail).content.decode()
    assert first.get(pdf).status_code == 200
    assert "Pronta" in second.get(detail).content.decode()
    assert second.get(pdf).status_code == 404
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.READY


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_triage_review_and_download_do_not_change_other_visitors() -> None:
    _seed()
    item = TriageItem.objects.get(message_id="demo-triage-1", part_id="1")
    first, second = Client(REMOTE_ADDR="198.51.100.13"), Client(REMOTE_ADDR="198.51.100.14")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    detail = reverse("hub:triage-item", args=[item.id])
    download = reverse("hub:triage-download", args=[item.id])

    assert "Aguardando revisão" in first.get(detail).content.decode()
    assert "Aguardando revisão" in second.get(detail).content.decode()
    assert first.post(detail, {"decision": "archive"}).status_code == 302
    assert "Pronto para arquivar" in first.get(detail).content.decode()
    assert "Aguardando revisão" in second.get(detail).content.decode()
    assert first.post(detail, {"decision": "finish_archive"}).status_code == 302
    assert "Baixar arquivo fictício" in first.get(detail).content.decode()
    assert first.get(download).status_code == 200
    assert second.get(download).status_code == 404
    assert "Aguardando revisão" in second.get(detail).content.decode()
    item.refresh_from_db()
    assert item.status == TriageItem.Status.AWAITING_REVIEW
    assert not item.destination_path


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member", "auditor"])
def test_demo_dte_message_opening_is_private_to_browser_session(entry_mode) -> None:
    _seed()
    message = DteMessage.objects.filter(read_at=None).first()
    assert message is not None
    first, second = Client(REMOTE_ADDR="198.51.100.15"), Client(REMOTE_ADDR="198.51.100.16")
    if entry_mode == "public":
        for client in (first, second):
            assert client.post(reverse("hub:demo-entry")).status_code == 302
    else:
        member = Membership.objects.get(organization=message.organization, role="owner")
        if entry_mode == "auditor":
            member.role = "auditor"
            member.save(update_fields=["role"])
        for client in (first, second):
            client.force_login(member.user)
            session = client.session
            session["hub_organization_id"] = str(message.organization_id)
            session.save()
    detail = reverse("hub:dte-message-detail", args=[message.id])

    assert "Teor ainda não consultado" in first.get(detail).content.decode()
    assert "Teor ainda não consultado" in second.get(detail).content.decode()
    if entry_mode == "auditor":
        assert first.post(detail, {"confirm_legal_notice": "on"}).status_code == 403
        assert (
            first.post(
                reverse("hub:dte-center"), {"companies": [str(message.company_id)]}
            ).status_code
            == 403
        )
        assert "Abrir teor fictício" not in first.get(detail).content.decode()
        assert not DteMessageAccess.objects.filter(message=message).exists()
        return
    with patch("apps.hub.views.open_message") as external_open:
        assert first.post(detail, {}).status_code == 302
        assert "Teor ainda não consultado" in first.get(detail).content.decode()
        assert first.post(detail, {"confirm_legal_notice": "on"}).status_code == 302
        external_open.assert_not_called()
    assert "Mensagem fictícia para" in first.get(detail).content.decode()
    assert "Teor ainda não consultado" in second.get(detail).content.decode()
    assert not DteMessageAccess.objects.filter(message=message).exists()


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member"])
def test_demo_dte_preparation_and_result_are_private_to_browser_session(entry_mode) -> None:
    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    shared_run_count = DteRun.objects.count()
    first, second = Client(REMOTE_ADDR="198.51.100.17"), Client(REMOTE_ADDR="198.51.100.18")
    if entry_mode == "public":
        for client in (first, second):
            assert client.post(reverse("hub:demo-entry")).status_code == 302
    else:
        member = Membership.objects.get(organization=company.organization, role="owner")
        for client in (first, second):
            client.force_login(member.user)
            session = client.session
            session["hub_organization_id"] = str(company.organization_id)
            session.save()
    center = reverse("hub:dte-center")
    assert first.get(center).status_code == 200
    assert second.get(center).status_code == 200

    assert first.post(center, {"companies": [str(company.id)]}).status_code == 302
    first_page = first.get(center).content.decode()
    second_page = second.get(center).content.decode()
    assert "1 na fila" in first_page
    assert "1 na fila" not in second_page
    run_id = next(iter(first.session["demo_progress"]["dte_runs"]))
    assert first.get(reverse("hub:integra")).context["integra_pending_count"] == 1
    assert second.get(reverse("hub:integra")).context["integra_pending_count"] == 0
    # A stale/malformed session batch must not turn into a misleading partial batch.
    for selected_ids in (
        [str(company.id), "00000000-0000-0000-0000-000000000001"],
        [str(company.id), str(company.id)],
        {"invalid": str(company.id)},
        [None],
        [],
    ):
        session = first.session
        progress = session["demo_progress"]
        progress["dte_runs"][run_id]["company_ids"] = selected_ids
        session["demo_progress"] = progress
        session.save()
        assert first.get(center).context["dte_stats"]["awaiting"] == 0
        assert first.get(reverse("hub:integra")).context["integra_pending_count"] == 0
    session = first.session
    progress = session["demo_progress"]
    progress["dte_runs"][run_id]["company_ids"] = [str(company.id)]
    session["demo_progress"] = progress
    session.save()
    assert (
        second.post(
            reverse("hub:decide-dte-run", args=[run_id]), {"decision": "approve"}
        ).status_code
        == 404
    )
    approved = first.post(reverse("hub:decide-dte-run", args=[run_id]), {"decision": "approve"})
    assert approved.status_code == 302
    assert "Consulta fictícia concluída" in first.get(center).content.decode()
    assert "Consulta fictícia concluída" not in second.get(center).content.decode()
    assert first.get(reverse("hub:integra")).context["integra_pending_count"] == 0
    assert DteRun.objects.count() == shared_run_count


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member"])
def test_demo_parcelamento_consultation_and_issue_are_private_to_session(entry_mode) -> None:
    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    first, second = Client(REMOTE_ADDR="198.51.100.21"), Client(REMOTE_ADDR="198.51.100.22")
    entry = reverse("hub:demo-entry")
    if entry_mode == "public":
        assert first.post(entry).status_code == 302
        assert second.post(entry).status_code == 302
    else:
        member = Membership.objects.get(organization=company.organization, role="owner")
        for client in (first, second):
            client.force_login(member.user)
            session = client.session
            session["hub_organization_id"] = str(company.organization_id)
            session.save()
    operation_count = ParcelamentoOperation.objects.count()
    center = reverse("hub:parcelamentos")
    company_url = f"{center}?company={company.id}"

    initial = first.get(company_url).content.decode()
    assert "Comece consultando os pedidos" in initial
    assert "Situação dos parcelamentos" not in initial
    with patch("apps.hub.views.request_parcelamento_operation") as real_operation:
        consulted = first.post(center, {"company": company.id, "action": "consult"})
        real_operation.assert_not_called()
    assert consulted.status_code == 302
    first_page = first.get(company_url).content.decode()
    second_page = second.get(company_url).content.decode()
    assert "Situação dos parcelamentos" in first_page
    assert "Situação dos parcelamentos" not in second_page

    agreement = next(iter(first.session["demo_progress"]["parcelamento_consultations"]))
    assert agreement == str(company.id)
    from apps.hub.views import _demo_parcelamentos

    synthetic = _demo_parcelamentos(company)[0]
    available = next(item for item in synthetic.installments if not item.paid)
    rendered_agreements = re.findall(r'name="agreement" value="([^"]+)"', first_page)
    assert str(synthetic.number) in rendered_agreements
    rendered_agreement = rendered_agreements[0]
    issued = first.post(
        center,
        {
            "company": company.id,
            "action": "issue",
            "agreement": rendered_agreement,
            "competence": available.competence_key,
        },
    )
    assert issued.status_code == 302
    issued_page = first.get(company_url).content.decode()
    assert "DAS fictício pronto" in issued_page
    assert "Baixar DAS fictício" in issued_page
    assert "DAS fictício pronto" not in second.get(company_url).content.decode()
    demo_pdf = reverse(
        "hub:demo-parcelamento-das-pdf",
        args=[company.id, synthetic.number, available.competence_key],
    )
    pdf_response = first.get(demo_pdf)
    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert pdf_response["Cache-Control"] == "private, no-store"
    assert second.get(demo_pdf).status_code == 404
    assert ParcelamentoOperation.objects.count() == operation_count


@override_settings(DEBUG=True)
@pytest.mark.parametrize("role", ["owner", "auditor"])
def test_demo_member_bulk_actions_preserve_permissions_and_shared_data(role):
    _seed()
    member = Membership.objects.get(organization__slug="escritorio-demo", role="owner")
    member.role = role
    member.save(update_fields=["role"])
    company = ClientCompany.objects.filter(organization=member.organization, active=True).first()
    assert company is not None
    client = Client()
    client.force_login(member.user)
    session = client.session
    session["hub_organization_id"] = str(member.organization_id)
    session.save()
    before = (ParcelamentoOperation.objects.count(), DctfWebDocument.objects.count())
    with (
        patch("apps.hub.views.request_parcelamento_operation") as parcels,
        patch("apps.hub.views.request_dctfweb_document") as documents,
    ):
        result = client.post(
            reverse("hub:parcelamentos"),
            {"action": "consult_selected", "selected_company": [str(company.pk)]},
        )
        bulk = client.post(
            reverse("hub:dctfweb-bulk-consult"),
            {
                "step": "confirm",
                "kind": DctfWebDocument.Kind.RECEIPT,
                "targets": [f"{company.pk}|09/2026"],
                "approved_overage_cents": "0",
            },
        )
        assert result.status_code == (302 if role == "owner" else 403)
        assert bulk.status_code == (302 if role == "owner" else 403)
        parcels.assert_not_called()
        documents.assert_not_called()
    assert before == (ParcelamentoOperation.objects.count(), DctfWebDocument.objects.count())
    progress = client.session.get("demo_progress", {})
    if role == "owner":
        assert str(company.pk) in progress["parcelamento_consultations"]
        assert f"receipt:{company.pk}:09/2026" in progress["dctfweb_bulk"]
    else:
        assert not progress


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member", "auditor"])
def test_demo_individual_dctfweb_is_session_local(entry_mode):
    _seed()
    member = Membership.objects.get(organization__slug="escritorio-demo", role="owner")
    company = ClientCompany.objects.filter(organization=member.organization, active=True).first()
    assert company is not None
    clients = [Client(REMOTE_ADDR=f"198.51.100.{value}") for value in (41, 42)]
    if entry_mode == "public":
        for client in clients:
            assert client.post(reverse("hub:demo-entry")).status_code == 302
    else:
        if entry_mode == "auditor":
            member.role = "auditor"
            member.save(update_fields=["role"])
        for client in clients:
            client.force_login(member.user)
            session = client.session
            session["hub_organization_id"] = str(member.organization_id)
            session.save()
    first, second = clients
    assert "Demonstração fictícia" in first.get(reverse("hub:guides")).content.decode()
    url = reverse("hub:dctfweb-consult")
    params = {"company": str(company.pk), "competence": "09/2026"}
    before = DctfWebDocument.objects.count()
    assert "Resultado fictício pronto." not in first.get(url, params).content.decode()
    with patch("apps.hub.views.request_dctfweb_document") as service:
        result = first.post(url, {**params, "kind": "receipt", "approved_overage_cents": "0"})
        assert result.status_code == (403 if entry_mode == "auditor" else 302)
        service.assert_not_called()
        for invalid in ("13/2026", "09/0000", "2026-09", ""):
            response = first.post(url, {**params, "competence": invalid, "kind": "receipt"})
            assert response.status_code == 302
        service.assert_not_called()
    assert DctfWebDocument.objects.count() == before
    page = first.get(url, params).content.decode()
    assert ("Resultado fictício pronto." in page) == (entry_mode != "auditor")
    assert "Resultado fictício pronto." not in second.get(url, params).content.decode()
    if entry_mode == "auditor":
        assert "Simular declaração completa" not in page


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_review_decision_is_private_to_session() -> None:
    _seed()
    review = ReviewCase.objects.filter(
        organization__is_demo=True, status=ReviewCase.Status.OPEN
    ).first()
    assert review is not None
    first, second = Client(REMOTE_ADDR="198.51.100.23"), Client(REMOTE_ADDR="198.51.100.24")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    detail = reverse("hub:review-detail", args=[review.id])
    resolve = reverse("hub:resolve-review", args=[review.id])

    assert "Registrar acumulador conferido" in first.get(detail).content.decode()
    decided = first.post(resolve, {"accumulator_code": "DEMO-1042"})
    assert decided.status_code == 302
    assert "DEMO-1042" in first.get(detail).content.decode()
    assert "Registrar acumulador conferido" in second.get(detail).content.decode()
    group_query = {
        "status": "unclassified",
        "competence": "",
        "group": str(review.document.company_id),
    }
    first_rows = first.get(reverse("hub:nfse-center"), group_query).context["group"]["rows"]
    second_rows = second.get(reverse("hub:nfse-center"), group_query).context["group"]["rows"]
    assert review.id not in {row["review"].id for row in first_rows if row["review"] is not None}
    assert review.id in {row["review"].id for row in second_rows if row["review"] is not None}
    first_pending = first.get(reverse("hub:dashboard")).context["stats"]["pending"]
    second_pending = second.get(reverse("hub:dashboard")).context["stats"]["pending"]
    assert first_pending == second_pending - 1
    review.refresh_from_db()
    assert review.status == ReviewCase.Status.OPEN
    assert not review.resolved_accumulator


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_collection_progress_is_private_to_session() -> None:
    _seed()
    certificate = Certificate.objects.filter(
        organization__is_demo=True,
        revoked_at__isnull=True,
        valid_until__gt=timezone.now(),
    ).select_related("company").first()
    assert certificate is not None
    company = certificate.company
    assert company is not None
    initial_sync_count = NfseSync.objects.count()
    first, second = Client(REMOTE_ADDR="198.51.100.41"), Client(REMOTE_ADDR="198.51.100.42")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    center = reverse("hub:nfse-center")

    activated = first.post(
        center,
        {"action": "activate", "companies": [str(company.id)]},
    )

    assert activated.status_code == 302
    assert "Aguardando" in first.get(center, {"view": "collection"}).content.decode()
    assert "SIMULAÇÃO DE COLETA" in second.get(
        center, {"view": "collection"}
    ).content.decode()
    first_page = first.get(center, {"view": "collection"}).content.decode()
    assert "SIMULAÇÃO DE COLETA" in first_page
    assert "COLETA AUTOMÁTICA · PRODUÇÃO" not in first_page

    assert first.post(
        center + "?view=collection",
        {"action": "pause", "companies": [str(company.id)]},
    ).status_code == 302
    first_queue = first.get(reverse("hub:nfse-queue-status")).json()
    second_queue = second.get(reverse("hub:nfse-queue-status")).json()
    first_states = {item["company_id"]: item["state"] for item in first_queue["items"]}
    second_states = {item["company_id"]: item["state"] for item in second_queue["items"]}
    assert first_states[str(company.id)] == "paused"
    assert second_states[str(company.id)] != "paused"
    assert first_queue["simulated"] is True
    assert NfseSync.objects.count() == initial_sync_count


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_collection_does_not_activate_a_company_without_a_valid_a1() -> None:
    _seed()
    company = (
        ClientCompany.objects.filter(organization__is_demo=True, active=True)
        .exclude(
            id__in=Certificate.objects.filter(
                organization__is_demo=True,
                revoked_at__isnull=True,
                valid_until__gt=timezone.now(),
            ).values("company_id")
        )
        .first()
    )
    assert company is not None
    client = Client(REMOTE_ADDR="198.51.100.43")
    assert client.post(reverse("hub:demo-entry")).status_code == 302

    response = client.post(
        reverse("hub:nfse-center") + "?view=collection",
        {"action": "activate", "companies": [str(company.id)]},
        follow=True,
    )

    assert response.status_code == 200
    assert "precisa de A1 válido antes de ativar a coleta" in response.content.decode()
    session_state = client.session.get("demo_progress", {}).get("nfse_syncs", {})
    assert str(company.id) not in session_state


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_retry_is_session_local_and_never_dispatches_the_real_sync() -> None:
    _seed()
    certificate = Certificate.objects.filter(
        organization__is_demo=True,
        revoked_at__isnull=True,
        valid_until__gt=timezone.now(),
    ).select_related("organization", "company").first()
    assert certificate is not None
    sync, _created = NfseSync.objects.update_or_create(
        organization=certificate.organization,
        company=certificate.company,
        defaults={
            "certificate": certificate,
            "enabled": True,
            "status": NfseSync.Status.ERROR,
            "last_error_message": "Falha fictícia",
        },
    )
    first, second = Client(REMOTE_ADDR="198.51.100.44"), Client(REMOTE_ADDR="198.51.100.45")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302

    with patch("apps.hub.tasks.dispatch_active_nfse_syncs.delay") as dispatch:
        retried = first.post(
            reverse("hub:nfse-queue-retry"),
            {"company_id": str(certificate.company_id)},
        )

    assert retried.status_code == 200
    assert retried.json() == {"changed": 1}
    dispatch.assert_not_called()
    sync.refresh_from_db()
    assert sync.status == NfseSync.Status.ERROR
    first_states = {
        item["company_id"]: item["state"]
        for item in first.get(reverse("hub:nfse-queue-status")).json()["items"]
    }
    second_states = {
        item["company_id"]: item["state"]
        for item in second.get(reverse("hub:nfse-queue-status")).json()["items"]
    }
    assert first_states[str(certificate.company_id)] == "queued"
    assert second_states[str(certificate.company_id)] == "failed"


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_bulk_download_builds_the_selected_dominio_folder() -> None:
    _seed()
    document = (
        NfseDocument.objects.filter(organization__is_demo=True).select_related("company").first()
    )
    assert document is not None
    client = Client(REMOTE_ADDR="198.51.100.45")
    assert client.post(reverse("hub:demo-entry")).status_code == 302

    response = client.post(
        reverse("hub:nfse-center"),
        {"action": "demo_download_taken", "documents": [str(document.id)]},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    body = b"".join(response.streaming_content)
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        company_folder = nfse_company_archive_folder(
            root="Tomadas",
            dominio_code=document.company.dominio_code,
        )
        xml_path = f"{company_folder}/NFS-e-{document.source_nsu}.xml"
        assert archive.namelist() == [xml_path, "manifesto-classificacao.csv"]
        assert archive.read(xml_path) == document.original_xml.encode()
        manifest = archive.read("manifesto-classificacao.csv").decode("utf-8-sig")
        assert "Transitória;Transitória sem acumulador" in manifest


@override_settings(DEBUG=True, DEMO_ORGANIZATION_SLUG="escritorio-demo")
def test_demo_office_owner_can_use_the_download_shown_by_the_interface() -> None:
    _seed()
    organization = Organization.objects.get(slug="escritorio-demo")
    owner = User.objects.get(email="demo@hubcontador.local")
    document = NfseDocument.objects.filter(organization=organization).first()
    assert document is not None
    client = Client()
    client.force_login(owner)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    page = client.get(reverse("hub:nfse-center"), {"status": "all"})
    response = client.post(
        reverse("hub:nfse-center"),
        {"action": "demo_download_selected", "all_documents": "1"},
    )

    assert "Pacote com acumuladores" in page.content.decode()
    assert 'form="nfse-download-demo-package"' in page.content.decode()
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_nfse_bulk_download_includes_all_and_marks_manual_accumulator() -> None:
    _seed()
    documents = list(
        NfseDocument.objects.filter(organization__is_demo=True).select_related("company")[:2]
    )
    assert len(documents) == 2
    client = Client(REMOTE_ADDR="198.51.100.47")
    assert client.post(reverse("hub:demo-entry")).status_code == 302

    response = client.post(
        reverse("hub:nfse-center"),
        {
            "action": "demo_download_issued",
            "all_documents": "1",
            f"accumulator_{documents[0].id}": "SERVICOS",
        },
    )

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as archive:
        names = archive.namelist()
        assert "manifesto-classificacao.csv" in names
        assert any(name.startswith("Emitidas/") and name.endswith(".xml") for name in names)
        manifest = archive.read("manifesto-classificacao.csv").decode("utf-8-sig")
        assert "SERVICOS;Definida pelo contador" in manifest
        assert "Transitória;Transitória sem acumulador" in manifest


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member", "auditor"])
def test_demo_reconciliation_confirmation_is_private_to_session(entry_mode) -> None:
    _seed()
    first, second = Client(REMOTE_ADDR="198.51.100.25"), Client(REMOTE_ADDR="198.51.100.26")
    entry = reverse("hub:demo-entry")
    if entry_mode == "public":
        assert first.post(entry).status_code == 302
        assert second.post(entry).status_code == 302
    else:
        member = Membership.objects.get(organization__is_demo=True, role="owner")
        if entry_mode == "auditor":
            member.role = Membership.Role.AUDITOR
            member.save(update_fields=["role"])
        for browser in (first, second):
            browser.force_login(member.user)
            session = browser.session
            session["hub_organization_id"] = str(member.organization_id)
            session.save()
    center = reverse("hub:reconciliation")
    first_page = first.get(center)
    assert first_page.status_code == 200
    assert "Confirmações valem só nesta sessão" in first_page.content.decode()
    assert 'id="visao-geral"' not in first_page.content.decode()
    assert "normalized_movements" not in first_page.context
    empty = first.get(center, {"q": "nenhum-correspondente-qa"})
    assert "Nenhum lançamento corresponde aos filtros" in empty.content.decode()
    assert "Sem extratos OFX" not in empty.content.decode()
    match = first_page.context["matches"][0]
    candidate = match.candidates[0]

    with patch("apps.hub.views.confirm_reconciliation_match") as shared_write:
        confirmed = first.post(
            reverse("hub:confirm-reconciliation", args=[match.id]),
            {"dominio_entry_id": candidate.id},
        )
        shared_write.assert_not_called()
    if entry_mode == "auditor":
        assert confirmed.status_code == 403
        assert "Comparar candidatos" not in first_page.content.decode()
        assert "Apenas consulta" in first_page.content.decode()
        assert not first.session.get("demo_progress", {}).get("reconciliation")
        return
    assert confirmed.status_code == 302
    first_matches = first.get(f"{center}?status=all").context["matches"]
    second_matches = second.get(f"{center}?status=all").context["matches"]
    assert first_matches[0].status == ReconciliationMatch.Status.MATCHED
    assert second_matches[0].status == ReconciliationMatch.Status.AMBIGUOUS
    assert not ReconciliationMatch.objects.filter(organization__is_demo=True).exists()


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_reform_radar_uses_labeled_synthetic_alerts_without_persisting() -> None:
    _seed()
    browser = Client(REMOTE_ADDR="198.51.100.27")
    assert browser.post(reverse("hub:demo-entry")).status_code == 302
    page = browser.get(reverse("hub:reform"))

    assert page.status_code == 200
    assert page.context["radar_demo"] is True
    assert page.context["alert_total"] == 3
    assert "Exemplo fictício" in page.content.decode()
    assert "Exemplo fictício" in page.content.decode()
    assert not ReformAlert.objects.exists()
    filtered = browser.get(reverse("hub:reform"), {"q": "IBS"})
    assert filtered.context["alert_total"] == 1


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="slug-que-nao-existe",
)
@pytest.mark.django_db
def test_a_stale_configured_slug_still_finds_the_single_demonstration_office() -> None:
    _seed()

    home = Client().get(reverse("hub:home"))
    entry = Client().get(reverse("hub:demo-entry"))

    assert "Explorar a demonstração completa" in home.content.decode()
    assert "Iniciar demonstração fictícia" in entry.content.decode()

    visitor = Client(REMOTE_ADDR="198.51.100.41")
    assert visitor.post(reverse("hub:demo-entry")).status_code == 302
    assert (
        Organization.objects.get(slug="escritorio-demo")
        .memberships.filter(user_id=visitor.session["_auth_user_id"])
        .exists()
    )


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="slug-que-nao-existe",
)
@pytest.mark.django_db
def test_two_demonstration_offices_close_the_entry_instead_of_guessing() -> None:
    _seed()
    Organization.objects.create(name="Segunda demo", slug="outra-demo", is_demo=True)

    entry = Client().get(reverse("hub:demo-entry"))
    blocked = Client().post(reverse("hub:demo-entry"))

    assert "está sendo preparada" in entry.content.decode()
    assert blocked.status_code == 400


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.django_db
def test_demo_team_page_hides_the_accounts_of_other_visitors() -> None:
    _seed()
    first = Client(REMOTE_ADDR="198.51.100.31")
    second = Client(REMOTE_ADDR="198.51.100.32")
    assert first.post(reverse("hub:demo-entry")).status_code == 302
    assert second.post(reverse("hub:demo-entry")).status_code == 302
    first_email = User.objects.get(id=first.session["_auth_user_id"]).email

    page = second.get(reverse("hub:team"))

    body = page.content.decode()
    assert page.status_code == 200
    assert first_email not in body
    assert "Visitante da demonstração" in body


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_visitor_cannot_mutate_shared_administration_or_company_data() -> None:
    _seed()
    browser = Client(REMOTE_ADDR="198.51.100.19")
    assert browser.post(reverse("hub:demo-entry")).status_code == 302
    company_count = ClientCompany.objects.filter(organization__is_demo=True).count()
    for route in ("hub:companies", "hub:team", "hub:settings", "hub:reconciliation"):
        blocked = browser.post(reverse(route), {"name": "Alteração indevida"})
        assert blocked.status_code == 403
        assert "não altera a configuração" in blocked.content.decode()
    assert ClientCompany.objects.filter(organization__is_demo=True).count() == company_count


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_copilot_conversation_is_private_to_browser_session() -> None:
    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    conversations_before = Conversation.objects.count()
    messages_before = Message.objects.count()
    first = Client(REMOTE_ADDR="198.51.100.20")
    second = Client(REMOTE_ADDR="198.51.100.21")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    assistant = reverse("intelligence:assistant")

    sent = first.post(
        assistant,
        {
            "company_id": str(company.id),
            "question": "Quais pendências merecem atenção?",
            "request_id": "87000e76-a81a-4d90-b8da-e65d854c64c0",
        },
    )
    assert sent.status_code == 302
    assert "conversation=" in sent["Location"]
    assert "Demonstração fictícia para" in first.get(sent["Location"]).content.decode()
    assert "Demonstração fictícia para" not in second.get(assistant).content.decode()
    assert Conversation.objects.count() == conversations_before
    assert Message.objects.count() == messages_before


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member"])
def test_demo_reconciliation_never_receives_shared_files(entry_mode) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.hub.models import ReconciliationSourceFile

    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    browser = Client(REMOTE_ADDR="198.51.100.28")
    if entry_mode == "public":
        assert browser.post(reverse("hub:demo-entry")).status_code == 302
    else:
        member = Membership.objects.get(organization=company.organization, role="owner")
        browser.force_login(member.user)
        session = browser.session
        session["hub_organization_id"] = str(company.organization_id)
        session.save()
    before = ReconciliationSourceFile.objects.filter(organization__is_demo=True).count()

    page = browser.get(reverse("hub:reconciliation")).content.decode()
    refused = browser.post(
        reverse("hub:reconciliation-upload"),
        {
            "company": str(company.id),
            "origin": ReconciliationSourceFile.Origin.BANK_STATEMENT,
            "files": SimpleUploadedFile("extrato.csv", b"data;valor\n01/09/2026;10,00\n"),
        },
    )

    assert 'id="reconciliation-upload-dialog"' not in page
    assert refused.status_code == 403
    assert ReconciliationSourceFile.objects.filter(organization__is_demo=True).count() == before


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
@pytest.mark.parametrize("entry_mode", ["public", "member", "auditor"])
def test_demo_reconciliation_advanced_routes_are_closed_before_data_access(entry_mode, subtests):
    from apps.hub.urls import urlpatterns

    _seed()
    office = Organization.objects.get(slug="escritorio-demo")
    browser = Client(REMOTE_ADDR="198.51.100.29")
    if entry_mode == "public":
        assert browser.post(reverse("hub:demo-entry")).status_code == 302
    else:
        member = Membership.objects.get(organization=office, role="owner")
        if entry_mode == "auditor":
            member.role = "auditor"
            member.save(update_fields=["role"])
        browser.force_login(member.user)
        session = browser.session
        session["hub_organization_id"] = str(office.id)
        session.save()

    # Discover the entire advanced route family so newly added endpoints cannot
    # silently escape the same boundary. The two session-backed routes are separate.
    routes = [
        route for route in urlpatterns if route.callback.__name__.startswith("reconciliation_")
    ]
    assert len(routes) >= 12
    for route in routes:
        kwargs = {name: "00000000-0000-4000-8000-000000000001" for name in route.pattern.converters}
        url = reverse(f"hub:{route.name}", kwargs=kwargs)
        for method in ("get", "post"):
            with subtests.test(route=route.name, method=method):
                with patch("apps.hub.views._module_page_context") as module_context:
                    response = getattr(browser, method)(url)
                module_context.assert_not_called()
                assert response.status_code == 403
                body = response.content.decode()
                assert "somente a comparação fictícia" in body
                assert "Voltar à conciliação demo" in body
                assert f'href="{reverse("hub:reconciliation")}"' in body
                assert "Abrir integrações" not in body
    assert browser.get(reverse("hub:reconciliation")).status_code == 200
