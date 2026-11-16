"""Customer title journeys use synthetic evidence and never infer a financial relation."""

import csv
import io
from copy import deepcopy
from datetime import date
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    JournalEntry,
    NormalizedMovement,
    ReconciliationTitleAllocation,
    ReconciliationTitleBatch,
    ReconciliationTitleDecision,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_forms import BRLCentsField
from apps.intelligence.native_title_review import confirm_native_review
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract
from test_native_title_review import captured as captured_fixture
from test_native_title_review import prepare as prepare_native
from test_native_titles import fiscal as fiscal_fixture
from test_title_persistence import bank, imported
from test_title_persistence import context as context_fixture

context = context_fixture
captured = captured_fixture
fiscal_source = fiscal_fixture
pytestmark = pytest.mark.django_db
PERIOD = {"start": "2026-09-01", "end": "2026-09-30"}


def login(account, actor, *, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(actor)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    return client


@pytest.fixture
def journey(context):
    account, actor, payload = context
    snapshot = imported(context)
    movement = bank(account)
    return {
        "account": account,
        "actor": actor,
        "payload": payload,
        "snapshot": snapshot,
        "movement": movement,
        "client": login(account, actor),
    }


def url(case, name, **kwargs):
    if name == "titles":
        return (
            reverse("hub:reconciliation-titles")
            + "?"
            + urlencode(
                {
                    "account": case["account"].pk,
                    **PERIOD,
                    **kwargs,
                }
            )
        )
    return reverse(
        "hub:reconciliation-title-" + name,
        kwargs={
            "account_id": case["account"].pk,
            **kwargs,
        },
    )


def selection(case, *, amount="61,25", movement=None):
    response = case["client"].get(url(case, "plan"), PERIOD)
    assert response.status_code == 200
    settlement = response.context["titles_settlement_options"][0]["key"]
    return {
        "action": "preview",
        "links-TOTAL_FORMS": "1",
        "links-INITIAL_FORMS": "0",
        "links-0-settlement": settlement,
        "links-0-movement_key": str((movement or case["movement"]).pk),
        "links-0-cash_cents": amount,
    }


def preview(case, *, amount="61,25", data=None):
    response = case["client"].post(
        url(case, "plan") + "?" + urlencode(PERIOD),
        data or selection(case, amount=amount),
    )
    assert response.status_code == 200
    assert response.templates[0].name == "hub/reconciliation_titles_preview.html"
    return response


def confirmation(response, **overrides):
    return {
        "token": response.context["titles_confirm_form"]["token"].value(),
        "evidence_reference": "Conferência sintética de título e extrato",
        "reviewed": "on",
        **overrides,
    }


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (
            AuditEvent,
            ReconciliationTitleSnapshot,
            ReconciliationTitleBatch,
            ReconciliationTitleAllocation,
            ReconciliationTitleDecision,
            JournalEntry,
        )
    }


def test_complete_customer_journey_and_exact_replay_keep_evidence(journey):
    case = journey
    before = counts()
    catalog = case["client"].get(url(case, "titles"))
    assert catalog.status_code == 200
    assert "R$ 100,00" in catalog.content.decode()
    assert "no-store" in catalog["Cache-Control"]
    response = preview(case)
    assert counts() == before
    data = confirmation(response)
    confirmed = case["client"].post(url(case, "confirm"), data)
    assert confirmed.status_code == 302 and "start=2026-09-01" in confirmed.url
    assert ReconciliationTitleAllocation.objects.get().cash_cents == 6125
    saved = counts()
    assert case["client"].post(url(case, "confirm"), data).status_code == 302
    assert counts() == saved
    history = case["client"].get(confirmed.url)
    assert "Desfazer vínculo" in history.content.decode()
    for mode in ("print", "csv"):
        report = case["client"].get(url(case, "report"), {**PERIOD, "format": mode})
        assert report.status_code == 200
        assert "61,25" in report.content.decode()
    assert not JournalEntry.objects.exists()
    allocation = ReconciliationTitleAllocation.objects.get()
    undone = case["client"].post(
        url(case, "undo", allocation_id=allocation.pk),
        {
            f"undo-{allocation.pk}-reason": "Refazer conferência sintética",
            "start": "2026-09-10",
            "end": "2026-09-20",
        },
    )
    assert undone.status_code == 302
    assert "start=2026-09-10" in undone.url and "end=2026-09-20" in undone.url
    allocation.refresh_from_db()
    assert allocation.state == "undone"
    assert list(allocation.decisions.order_by("created_at").values_list("state", flat=True)) == [
        "confirmed",
        "undone",
    ]


def test_partial_grouped_allocations_keep_global_capacity(journey):
    case = journey
    first = confirmation(preview(case, amount="20,00"))
    assert case["client"].post(url(case, "confirm"), first).status_code == 302
    available = case["client"].get(url(case, "plan"), PERIOD)
    choices = available.context["titles_formset"].forms[0].fields["settlement"].choices
    assert "disponível R$ 41,25" in choices[1][1]
    data = selection(case, amount="21,25")
    other = bank(case["account"], cents=-2000)
    data.update(
        {
            "links-TOTAL_FORMS": "2",
            "links-1-settlement": data["links-0-settlement"],
            "links-1-movement_key": str(other.pk),
            "links-1-cash_cents": "20,00",
        }
    )
    response = preview(case, data=data)
    assert "R$ 41,25" in response.content.decode()
    assert case["client"].post(url(case, "confirm"), confirmation(response)).status_code == 302
    assert ReconciliationTitleAllocation.objects.count() == 3
    catalog = case["client"].get(url(case, "titles"))
    assert catalog.context["title_data"]["settlement_rows"][0]["remaining_cents"] == 0


def test_date_difference_requires_explicit_acceptance_and_preserves_form(journey):
    case = journey
    NormalizedMovement.objects.filter(pk=case["movement"].pk).update(occurred_on=date(2026, 9, 13))
    response = preview(case)
    assert response.context["titles_confirm_form"].fields["accept_date_differences"].required
    data = confirmation(response, evidence_reference="Minha evidência digitada")
    refused = case["client"].post(url(case, "confirm"), data)
    assert refused.status_code == 400
    assert "Minha evidência digitada" in refused.content.decode()
    assert refused.context["titles_confirm_form"].errors["accept_date_differences"]
    assert not ReconciliationTitleAllocation.objects.exists()
    data["accept_date_differences"] = "on"
    assert case["client"].post(url(case, "confirm"), data).status_code == 302


def test_missing_review_keeps_signed_selection_and_evidence(journey):
    case = journey
    response = preview(case)
    data = confirmation(response, reviewed="", evidence_reference="Texto mantido")
    result = case["client"].post(url(case, "confirm"), data)
    assert result.status_code == 400
    assert result.context["titles_preview_count"] == 1
    assert result.context["titles_confirm_form"]["evidence_reference"].value() == "Texto mantido"
    assert not ReconciliationTitleBatch.objects.exists()


def test_stale_preview_cannot_spend_capacity_again(journey):
    case = journey
    old = confirmation(preview(case))
    current = confirmation(preview(case, amount="20,00"))
    assert case["client"].post(url(case, "confirm"), current).status_code == 302
    result = case["client"].post(url(case, "confirm"), old)
    assert result.status_code == 409
    assert ReconciliationTitleAllocation.objects.count() == 1


@pytest.mark.parametrize(
    "value,expected",
    [
        ("61,25", 6125),
        ("1.234,56", 123456),
        ("12", 1200),
        ("0,01", 1),
        ("1,5", 150),
    ],
)
def test_brl_is_strict_decimal_in_cents(value, expected):
    assert BRLCentsField().clean(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "12.34",
        "1.23,00",
        "01,00",
        "1e3",
        "-1,00",
        "0",
        "0,00",
        "1,234",
        "nan",
        "R$ 1,00",
        "1" * 31,
        "99999999999999999999999999999999",
    ],
)
def test_brl_rejects_ambiguous_negative_exponent_and_oversized_values(value):
    with pytest.raises(ValidationError):
        BRLCentsField().clean(value)


def test_zero_is_only_opted_in_for_native_components():
    assert BRLCentsField(allow_zero=True).clean("0,00") == 0


@pytest.mark.parametrize(
    "query",
    [
        "start=2026-09-01",
        "start=invalid&end=2026-09-30",
        "start=2026-9-1&end=2026-09-30",
        "start=2026-10-01&end=2026-09-30",
        "start=2026-09-01&start=2026-08-01&end=2026-09-30",
    ],
)
def test_invalid_or_duplicate_dates_never_expand_period(journey, query):
    case = journey
    before = counts()
    response = case["client"].get(
        reverse("hub:reconciliation-titles") + "?account=" + str(case["account"].pk) + "&" + query
    )
    assert response.status_code == 400
    assert "R$ 61,25" not in response.content.decode()
    assert counts() == before


def test_duplicate_post_fields_and_tampered_signature_are_refused(journey):
    case = journey
    data = confirmation(preview(case))
    assert (
        case["client"].post(url(case, "confirm"), {**data, "reviewed": ["on", "on"]}).status_code
        == 400
    )
    assert (
        case["client"]
        .post(url(case, "confirm"), {**data, "token": data["token"] + "x"})
        .status_code
        == 409
    )
    assert not ReconciliationTitleBatch.objects.exists()


def test_foreign_selection_and_excessive_formset_are_refused(journey):
    case = journey
    data = selection(case)
    data["links-0-movement_key"] = str(uuid4())
    response = case["client"].post(url(case, "plan") + "?" + urlencode(PERIOD), data)
    assert response.status_code == 400
    data.update({"links-TOTAL_FORMS": "99999", "links-0-movement_key": str(case["movement"].pk)})
    response = case["client"].post(url(case, "plan") + "?" + urlencode(PERIOD), data)
    assert response.status_code == 400
    assert len(response.context["titles_formset"].forms) == 20
    assert not ReconciliationTitleAllocation.objects.exists()


def test_added_row_keeps_previous_selections(journey):
    case = journey
    data = selection(case, amount="20,00")
    data["action"] = "add"
    response = case["client"].post(url(case, "plan") + "?" + urlencode(PERIOD), data)
    assert response.status_code == 200
    formset = response.context["titles_formset"]
    assert len(formset.forms) == 2
    assert formset.forms[0]["cash_cents"].value() == "20,00"


def test_token_is_bound_to_actor_and_account(journey):
    case = journey
    data = confirmation(preview(case))
    other = FinancialAccount.objects.create(
        organization=case["account"].organization,
        company=case["account"].company,
        name="Outra conta sintética",
        account_reference="SYN-2",
    )
    assert (
        case["client"]
        .post(reverse("hub:reconciliation-title-confirm", args=[other.pk]), data)
        .status_code
        == 409
    )
    actor = User.objects.create_user("second@titles.test", "synthetic-only-password")
    Membership.objects.create(organization=case["account"].organization, user=actor, role="owner")
    assert login(case["account"], actor).post(url(case, "confirm"), data).status_code == 409
    assert not ReconciliationTitleBatch.objects.exists()


def test_live_role_company_and_module_scope_control_reads_and_writes(journey, membership):
    case = journey
    data = confirmation(preview(case))
    membership.role = "auditor"
    membership.save()
    grant = CompanyAccessGrant.objects.create(
        organization=case["account"].organization,
        membership=membership,
        company=case["account"].company,
        modules=["reconciliation"],
    )
    assert case["client"].get(url(case, "titles")).status_code == 200
    assert case["client"].get(url(case, "report"), PERIOD).status_code == 200
    assert case["client"].get(url(case, "plan"), PERIOD).status_code == 403
    assert case["client"].post(url(case, "confirm"), data).status_code == 403
    grant.modules = ["payroll"]
    grant.save()
    assert case["client"].get(url(case, "titles")).status_code == 404
    assert case["client"].get(url(case, "report"), PERIOD).status_code == 404


def test_inactive_account_keeps_read_history_but_blocks_writes(journey):
    case = journey
    data = confirmation(preview(case))
    FinancialAccount.objects.filter(pk=case["account"].pk).update(active=False)
    assert case["client"].get(url(case, "titles")).status_code == 200
    assert case["client"].get(url(case, "report"), PERIOD).status_code == 200
    assert case["client"].post(url(case, "confirm"), data).status_code == 403


def test_suspended_contract_has_no_500_or_write(journey):
    case = journey
    data = confirmation(preview(case))
    TenantContract.objects.filter(organization=case["account"].organization).update(
        status="suspended"
    )
    assert case["client"].get(url(case, "titles")).status_code == 403
    assert case["client"].get(url(case, "report"), PERIOD).status_code == 403
    assert case["client"].post(url(case, "confirm"), data).status_code == 403
    assert not ReconciliationTitleBatch.objects.exists()


def test_other_organization_account_is_never_selected(journey):
    case = journey
    org = Organization.objects.create(name="Outra organização fictícia", slug="titles-other")
    company = ClientCompany.objects.create(organization=org, name="Outra empresa fictícia")
    other = FinancialAccount.objects.create(organization=org, company=company, name="Outra conta")
    assert case["client"].get(url(case, "titles", account=other.pk)).status_code == 404
    assert (
        case["client"]
        .get(reverse("hub:reconciliation-title-report", args=[other.pk]), PERIOD)
        .status_code
        == 404
    )


def test_csrf_is_required_on_every_mutation(journey):
    case = journey
    data = confirmation(preview(case))
    client = login(case["account"], case["actor"], csrf=True)
    assert client.get(url(case, "titles")).status_code == 200
    assert client.post(url(case, "confirm"), data).status_code == 403
    assert client.post(url(case, "plan"), {}).status_code == 403
    assert client.post(url(case, "undo", allocation_id=uuid4()), {}).status_code == 403


def test_report_ignores_catalog_search_and_page_and_escapes_financial_text(context):
    account, actor, payload = context
    payload["titles"][0]["key"] = "<script>alert(1)</script>"
    payload["titles"][0]["installments"][0]["outstanding_cents"] = None
    imported(context)
    movement = bank(account)
    NormalizedMovement.objects.filter(pk=movement.pk).update(original_description="=SUM(1,2)")
    case = {"account": account, "client": login(account, actor)}
    response = case["client"].get(url(case, "report"), {**PERIOD, "q": "absent", "page": "99"})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.content.decode()
    assert "<script>alert(1)</script>" not in response.content.decode()
    assert "Não informado" in response.content.decode()
    csv = case["client"].get(url(case, "report"), {**PERIOD, "format": "csv"})
    assert csv.status_code == 200
    assert "'=SUM(1,2)" in csv.content.decode()
    assert "Não informado" in csv.content.decode()


def test_csv_keeps_components_history_and_source_proof(journey):
    case = journey
    assert case["client"].post(url(case, "confirm"), confirmation(preview(case))).status_code == 302
    response = case["client"].get(url(case, "report"), {**PERIOD, "format": "csv"})
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    header = next(row for row in rows if row[0] == "Tipo")
    financial = [row for row in rows if row[0] in {"Parcela", "Baixa", "Extrato", "Decisão"}]
    assert all(len(row) == len(header) for row in financial)
    settlement = dict(zip(header, next(row for row in financial if row[0] == "Baixa"), strict=True))
    assert [
        settlement[key]
        for key in ("Principal R$", "Juros R$", "Multa R$", "Tarifas R$", "Desconto R$")
    ] == ["60,00", "1,50", "0,50", "0,25", "1,00"]
    assert case["snapshot"].source_file.content_hash in response.content.decode()
    assert "Conferência sintética de título e extrato" in response.content.decode()


def test_default_period_uses_restored_current_snapshot(context):
    account, actor, payload = context
    original = imported(context)
    newer = deepcopy(payload)
    newer["as_of"] = "2026-10-31"
    imported(context, newer)
    FinancialAccount.objects.filter(pk=account.pk).update(current_title_snapshot=original)
    response = login(account, actor).get(
        reverse("hub:reconciliation-titles"), {"account": account.pk}
    )
    assert response.status_code == 200
    assert response.context["titles_end"] == date(2026, 9, 30)
    assert response.context["title_data"]["snapshot"].pk == original.pk


def test_invalid_current_pointer_is_private_error_not_foreign_data(journey):
    case = journey
    other = FinancialAccount.objects.create(
        organization=case["account"].organization,
        company=case["account"].company,
        name="Conta com vínculo incorreto",
        account_reference="OTHER",
    )
    FinancialAccount.objects.filter(pk=other.pk).update(current_title_snapshot=case["snapshot"])
    response = case["client"].get(reverse("hub:reconciliation-titles"), {"account": other.pk})
    assert response.status_code == 400
    assert "no-store" in response["Cache-Control"]
    assert "R$ 61,25" not in response.content.decode()


def test_catalog_paginates_and_keeps_report_unfiltered(context):
    account, actor, payload = context
    title = deepcopy(payload["titles"][0])
    payload["titles"] = [{**deepcopy(title), "key": f"T-{i:03d}"} for i in range(30)]
    imported(context)
    case = {"account": account, "client": login(account, actor)}
    first = case["client"].get(url(case, "titles"))
    second = case["client"].get(url(case, "titles", page="2"))
    assert len(first.context["titles_page"]) == 25 and len(second.context["titles_page"]) == 5
    assert "page=" not in first.context["titles_report_url"]
    assert "q=" not in first.context["titles_report_url"]


def test_corrupt_source_still_allows_scoped_undo_and_requires_valid_return_period(journey):
    case = journey
    assert case["client"].post(url(case, "confirm"), confirmation(preview(case))).status_code == 302
    allocation = ReconciliationTitleAllocation.objects.get()
    with case["snapshot"].source_file.content.open("wb") as stream:
        stream.write(b"altered synthetic source")
    catalog = case["client"].get(url(case, "titles"))
    assert catalog.status_code == 200 and catalog.context["title_data"]["blocking"]
    assert "Desfazer vínculo" in catalog.content.decode()
    reason = {f"undo-{allocation.pk}-reason": "Fonte mudou; revisar novamente"}
    target = url(case, "undo", allocation_id=allocation.pk)
    assert case["client"].post(target, reason).status_code == 400
    allocation.refresh_from_db()
    assert allocation.state == "confirmed"
    assert case["client"].post(target, {**reason, **PERIOD}).status_code == 302


def test_empty_state_offers_received_sources_without_mutation(context):
    account, actor, _ = context
    case = {"account": account, "client": login(account, actor)}
    before = counts()
    response = case["client"].get(url(case, "titles"))
    assert response.status_code == 200
    assert "Ainda não há títulos revisados" in response.content.decode()
    assert (
        reverse("hub:reconciliation-native-titles", args=[account.pk]) in response.content.decode()
    )
    assert counts() == before


def test_restored_report_preserves_original_review_and_names_current_activation(captured):
    account, original_actor, source, initial = captured
    original = deepcopy(initial)
    original["evidence_reference"] = "Evidência original sintética"
    options, _ = prepare_native(captured, original)
    first, _ = confirm_native_review(**options)
    changed = deepcopy(original)
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500,
        cash_cents=3500,
    )
    options, _ = prepare_native(captured, changed)
    second, _ = confirm_native_review(**options)
    assert second.pk != first.pk
    reviewer = User.objects.create_user(
        "restore@titles.test",
        "synthetic-only-password",
        full_name="Revisora da restauração",
    )
    Membership.objects.create(organization=account.organization, user=reviewer, role="owner")
    restored_review = deepcopy(original)
    restored_review["evidence_reference"] = "=Restauração <revisada>"
    options, _ = prepare_native((account, reviewer, source, restored_review))
    restored, _ = confirm_native_review(**options)
    assert restored.pk == first.pk
    activation = (
        AuditEvent.objects.filter(
            action="hub.reconciliation.native_title_ui_reviewed",
            target_id=str(first.pk),
        )
        .order_by("-occurred_at", "-id")
        .first()
    )
    assert activation.metadata["activated_existing"] is True
    case = {"account": account, "client": login(account, reviewer)}
    before = counts()
    report = case["client"].get(url(case, "report"), PERIOD)
    assert report.status_code == 200
    assert report.context["titles_current_review"]["event_id"] == str(activation.pk)
    assert report.context["titles_current_review"]["occurred_at"] == activation.occurred_at
    text = report.content.decode()
    assert "Revisão original da fonte" in text and "Evidência original sintética" in text
    assert original_actor.display_name in text
    assert "Revisão que tornou a fotografia vigente" in text
    assert "=Restauração &lt;revisada&gt;" in text and reviewer.display_name in text
    response = case["client"].get(url(case, "report"), {**PERIOD, "format": "csv"})
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    original_row = next(row for row in rows if row[0] == "Revisão original da fonte")
    current_row = next(row for row in rows if row[0] == "Revisão que tornou a fotografia vigente")
    assert original_row[1:3] == ["Evidência original sintética", original_actor.display_name]
    assert current_row[1:4] == [
        "'=Restauração <revisada>",
        reviewer.display_name,
        activation.occurred_at.isoformat(),
    ]
    assert "histórico completo de vínculos" in response.content.decode()
    first.refresh_from_db()
    assert first.reviewed_by_id == original_actor.pk
    assert first.evidence_reference == "Evidência original sintética"
    assert counts() == before


def test_report_never_takes_activation_from_wrong_scope_or_failed_event(journey):
    case = journey
    foreign = Organization.objects.create(
        name="Organização fictícia separada", slug="activation-other"
    )
    common = {
        "action": "hub.reconciliation.native_title_ui_reviewed",
        "organization": case["account"].organization,
        "target_type": "hub.reconciliationtitlesnapshot",
        "target_id": str(case["snapshot"].pk),
        "metadata": {"activated_existing": True, "evidence_reference": "NÃO EXIBIR"},
    }
    for overrides in (
        {"organization": foreign},
        {"target_id": str(uuid4())},
        {"target_type": "hub.financialaccount"},
        {"success": False},
    ):
        AuditEvent.objects.create(**{**common, **overrides})
    for mode in ("print", "csv"):
        response = case["client"].get(url(case, "report"), {**PERIOD, "format": mode})
        assert response.status_code == 200
        assert "NÃO EXIBIR" not in response.content.decode()
        assert "Revisão que tornou a fotografia vigente" not in response.content.decode()
