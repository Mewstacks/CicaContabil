from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.demo_session import cleanup_stale_demo_visitors
from apps.hub.models import (
    ClientCompany,
    DteMessage,
    DteMessageAccess,
    DteRun,
    FiscalGuide,
    NfseDocument,
    NfseSync,
    ReconciliationMatch,
    ReformAlert,
    ReviewCase,
)
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
    assert NfseDocument.objects.filter(organization=organization).exists()
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
    assert "Baixar PDF fictício" in first.get(detail).content.decode()
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
def test_demo_dte_message_opening_is_private_to_browser_session() -> None:
    _seed()
    message = DteMessage.objects.filter(read_at=None).first()
    assert message is not None
    first, second = Client(REMOTE_ADDR="198.51.100.15"), Client(REMOTE_ADDR="198.51.100.16")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    detail = reverse("hub:dte-message-detail", args=[message.id])

    assert "Teor ainda não consultado" in first.get(detail).content.decode()
    assert "Teor ainda não consultado" in second.get(detail).content.decode()
    assert first.post(detail, {"confirm_legal_notice": "on"}).status_code == 302
    assert "Mensagem fictícia para" in first.get(detail).content.decode()
    assert "Teor ainda não consultado" in second.get(detail).content.decode()
    assert not DteMessageAccess.objects.filter(message=message).exists()


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_dte_preparation_and_result_are_private_to_browser_session() -> None:
    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    shared_run_count = DteRun.objects.count()
    first, second = Client(REMOTE_ADDR="198.51.100.17"), Client(REMOTE_ADDR="198.51.100.18")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    center = reverse("hub:dte-center")
    assert first.get(center).status_code == 200
    assert second.get(center).status_code == 200

    assert first.post(center, {"companies": [str(company.id)]}).status_code == 302
    first_page = first.get(center).content.decode()
    second_page = second.get(center).content.decode()
    assert "1 na fila" in first_page
    assert "1 na fila" not in second_page
    run_id = next(iter(first.session["demo_progress"]["dte_runs"]))
    approved = first.post(reverse("hub:decide-dte-run", args=[run_id]), {"decision": "approve"})
    assert approved.status_code == 302
    assert "Consulta fictícia concluída" in first.get(center).content.decode()
    assert "Consulta fictícia concluída" not in second.get(center).content.decode()
    assert DteRun.objects.count() == shared_run_count


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_parcelamento_consultation_and_issue_are_private_to_session() -> None:
    _seed()
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
    assert company is not None
    first, second = Client(REMOTE_ADDR="198.51.100.21"), Client(REMOTE_ADDR="198.51.100.22")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    center = reverse("hub:parcelamentos")
    company_url = f"{center}?company={company.id}"

    initial = first.get(company_url).content.decode()
    assert "Nenhuma consulta executada" in initial
    assert "Acordos encontrados" not in initial
    consulted = first.post(center, {"company": company.id, "action": "consult"})
    assert consulted.status_code == 302
    first_page = first.get(company_url).content.decode()
    second_page = second.get(company_url).content.decode()
    assert "Acordos encontrados" in first_page
    assert "Acordos encontrados" not in second_page

    agreement = next(iter(first.session["demo_progress"]["parcelamento_consultations"]))
    assert agreement == str(company.id)
    from apps.hub.views import _demo_parcelamentos

    synthetic = _demo_parcelamentos(company)[0]
    available = next(item for item in synthetic.installments if not item.paid)
    issued = first.post(
        center,
        {
            "company": company.id,
            "action": "issue",
            "agreement": synthetic.number,
            "competence": available.competence_key,
        },
    )
    assert issued.status_code == 302
    assert "DAS fictício emitido" in first.get(company_url).content.decode()
    assert "DAS fictício emitido" not in second.get(company_url).content.decode()


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
    assert review.id not in {item.id for item in first.get(reverse("hub:reviews")).context["cases"]}
    assert review.id in {item.id for item in second.get(reverse("hub:reviews")).context["cases"]}
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
    company = ClientCompany.objects.filter(organization__is_demo=True, active=True).first()
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
    assert "Não configurada" in second.get(center, {"view": "collection"}).content.decode()
    assert NfseSync.objects.count() == initial_sync_count


@override_settings(
    DEBUG=True,
    DEMO_ENTRY_ENABLED=True,
    DEMO_SESSION_ISOLATION_READY=True,
    DEMO_ORGANIZATION_SLUG="escritorio-demo",
)
def test_demo_reconciliation_confirmation_is_private_to_session() -> None:
    _seed()
    first, second = Client(REMOTE_ADDR="198.51.100.25"), Client(REMOTE_ADDR="198.51.100.26")
    entry = reverse("hub:demo-entry")
    assert first.post(entry).status_code == 302
    assert second.post(entry).status_code == 302
    center = reverse("hub:reconciliation")
    first_page = first.get(center)
    assert first_page.status_code == 200
    assert "Demonstração sem dados bancários reais" in first_page.content.decode()
    match = first_page.context["matches"][0]
    candidate = match.candidates[0]

    confirmed = first.post(
        reverse("hub:confirm-reconciliation", args=[match.id]),
        {"dominio_entry_id": candidate.id},
    )
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
    assert "Conteúdo fictício para demonstração" in page.content.decode()
    assert "Exemplo fictício" in page.content.decode()
    assert not ReformAlert.objects.exists()
    filtered = browser.get(reverse("hub:reform"), {"q": "IBS"})
    assert filtered.context["alert_total"] == 1


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
