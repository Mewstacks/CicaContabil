"""Closing services: read, identify, confer receipt x guide, and clear the checklist."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditEvent
from apps.closing import services
from apps.closing.models import ClosingConference, ClosingDocument, ClosingField, ClosingLayout
from apps.hub.models import ClientCompany, FiscalGuide, OperationalActivity
from closing_support import (
    CNPJ,
    CNPJ_DIGITS,
    das_text,
    make_activity,
    make_company,
    make_guide,
    make_layout,
    make_office,
    make_user,
    txt_upload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):  # type: ignore[no-untyped-def]
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def world():  # type: ignore[no-untyped-def]
    office = make_office()
    user = make_user(office, "owner@closing.test")
    company = make_company(office)
    layout = make_layout(
        office,
        activity_code="pgdas",
        compare=ClosingLayout.Compare.FISCAL_GUIDE,
        guide_kind=FiscalGuide.Kind.DAS,
    )
    activity = make_activity(office, company, code="pgdas")
    return office, user, company, layout, activity


def ingest(office, user, text: str, name: str = "das.txt") -> ClosingDocument:  # type: ignore[no-untyped-def]
    return services.ingest_upload(organization=office, actor=user, upload=txt_upload(text, name))


# --- reading -------------------------------------------------------------------------


def test_a_known_document_is_read_and_tied_to_company_and_competence(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, layout, _ = world
    document = ingest(office, user, das_text())
    assert document.state == ClosingDocument.State.ACCEPTED
    assert document.layout == layout
    assert document.company == company
    assert document.competence == date(2026, 8, 1)
    assert document.amount == Decimal("1234.56")
    assert document.reasons == []


def test_an_unrecognised_document_goes_to_quarantine_with_the_reason(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    document = ingest(office, user, "Um texto qualquer sem identificador")
    assert document.state == ClosingDocument.State.QUARANTINE
    assert document.layout is None
    assert any("nenhum layout" in reason.lower() for reason in document.reasons)
    assert not ClosingConference.objects.filter(document=document).exists()


def test_a_layout_that_is_not_active_never_reads_and_the_reason_says_so(world) -> None:  # type: ignore[no-untyped-def]
    office, user, _, layout, _ = world
    layout.active = False
    layout.save()
    document = ingest(office, user, das_text())
    assert document.state == ClosingDocument.State.QUARANTINE
    assert any("ativ" in reason.lower() for reason in document.reasons)


def test_an_unknown_company_is_named_in_the_quarantine_reason(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    document = ingest(office, user, das_text(cnpj="11.222.333/0001-81"))
    assert document.state == ClosingDocument.State.QUARANTINE
    assert document.company is None
    assert any("11.222.333/0001-81" in reason for reason in document.reasons)


def test_the_company_is_never_taken_from_another_office(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    other = make_office("other-office")
    foreign = make_company(other, "Outra", "11.222.333/0001-81")
    document = ingest(office, user, das_text(cnpj="11.222.333/0001-81"))
    assert document.company is None
    assert foreign.organization_id != office.id


def test_two_companies_with_the_same_cnpj_are_ambiguous_not_guessed(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    ClientCompany.objects.create(
        organization=office, name="Filial duplicada", cnpj_masked=CNPJ, dominio_code="418"
    )
    document = ingest(office, user, das_text())
    assert document.state == ClosingDocument.State.QUARANTINE
    assert any("mais de uma empresa" in reason.lower() for reason in document.reasons)


def test_company_is_found_by_root_state_and_municipal_registration(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, layout, _ = world
    company.state_registration = "029/0618657"
    company.save()
    ClosingField.objects.filter(layout=layout, variable="cnpj").delete()
    ClosingField.objects.create(
        organization=office, layout=layout, variable="state_registration", anchor="IE:"
    )
    text = "Documento de Arrecadação do Simples Nacional\nIE: 029/0618657\nPeríodo de Apuração: 08/2026\nValor Total do Documento 10,00"  # noqa: E501
    document = ingest(office, user, text)
    assert document.company == company


def test_a_missing_competence_or_value_is_listed_not_defaulted(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    text = "Documento de Arrecadação do Simples Nacional\nCNPJ: " + CNPJ
    document = ingest(office, user, text)
    assert document.state == ClosingDocument.State.QUARANTINE
    joined = " ".join(document.reasons).lower()
    assert "competência" in joined
    assert "valor" in joined


def test_ambiguous_layouts_are_refused_instead_of_picking_one(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    make_layout(office, code="das-2", label="DAS cópia")
    document = ingest(office, user, das_text())
    assert document.state == ClosingDocument.State.QUARANTINE
    assert any("mais de um layout" in reason.lower() for reason in document.reasons)


def test_the_same_bytes_are_not_stored_twice(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    first = ingest(office, user, das_text())
    again = ingest(office, user, das_text())
    assert again.pk == first.pk
    assert ClosingDocument.objects.filter(organization=office).count() == 1


def test_a_discarded_file_can_be_sent_again(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    first = ingest(office, user, das_text())
    services.discard(first, actor=user)
    again = ingest(office, user, das_text())
    assert again.pk != first.pk
    first.refresh_from_db()
    assert first.state == ClosingDocument.State.DISCARDED


@pytest.mark.parametrize(
    "upload",
    [
        SimpleUploadedFile("vazio.txt", b""),
        SimpleUploadedFile("macro.exe", b"MZ"),
        SimpleUploadedFile("falso.pdf", b"isto nao e pdf"),
    ],
)
def test_bad_uploads_are_refused(world, upload) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    with pytest.raises(ValidationError):
        services.ingest_upload(organization=office, actor=user, upload=upload)
    assert not ClosingDocument.objects.exists()


def test_rereading_after_the_layout_is_fixed_accepts_the_quarantined_file(world) -> None:  # type: ignore[no-untyped-def]
    office, user, _, layout, _ = world
    layout.active = False
    layout.save()
    document = ingest(office, user, das_text())
    assert document.state == ClosingDocument.State.QUARANTINE
    layout.active = True
    layout.save()
    document = services.reread(document, actor=user)
    assert document.state == ClosingDocument.State.ACCEPTED


# --- conferring and clearing the checklist -------------------------------------------


def test_a_value_inside_the_tolerance_matches_and_clears_the_checklist(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    make_guide(office, company, cents=123500)  # R$ 1.235,00 x R$ 1.234,56
    document = ingest(office, user, das_text())
    conference = document.conferences.get()
    assert conference.outcome == ClosingConference.Outcome.MATCHED
    assert conference.reference_source == ClosingConference.Source.FISCAL_GUIDE
    assert conference.reference_amount == Decimal("1235.00")
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED
    assert activity.evidence_items.filter(kind="source").exists()
    assert conference.checklist == ClosingConference.Checklist.DONE
    assert conference.activity == activity


def test_a_divergence_blocks_the_item_and_waits_for_a_person(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    make_guide(office, company, cents=150000)
    document = ingest(office, user, das_text())
    conference = document.conferences.get()
    assert conference.outcome == ClosingConference.Outcome.DIVERGED
    assert conference.difference == Decimal("265.44")
    assert conference.needs_person
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.BLOCKED
    assert "1.234,56" in activity.blocked_reason


def test_accepting_a_divergence_needs_a_reason_and_clears_with_human_evidence(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    make_guide(office, company, cents=150000)
    conference = ingest(office, user, das_text()).conferences.get()
    with pytest.raises(ValidationError):
        services.resolve(conference, actor=user, accept=True, reason="  ")
    services.resolve(conference, actor=user, accept=True, reason="Juros da guia de agosto")
    conference.refresh_from_db()
    activity.refresh_from_db()
    assert conference.resolution == ClosingConference.Resolution.ACCEPTED
    assert conference.resolved_by == user
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED
    assert activity.evidence_items.filter(kind="human", recorded_by=user).exists()
    assert AuditEvent.objects.filter(action="closing.conference.resolved").exists()


def test_rejecting_keeps_the_item_blocked(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    make_guide(office, company, cents=150000)
    conference = ingest(office, user, das_text()).conferences.get()
    services.resolve(conference, actor=user, accept=False, reason="Guia errada")
    activity.refresh_from_db()
    conference.refresh_from_db()
    assert conference.resolution == ClosingConference.Resolution.REJECTED
    assert activity.work_status == OperationalActivity.WorkStatus.BLOCKED


def test_a_resolved_conference_cannot_be_resolved_twice(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, _ = world
    make_guide(office, company, cents=150000)
    conference = ingest(office, user, das_text()).conferences.get()
    services.resolve(conference, actor=user, accept=False, reason="Guia errada")
    with pytest.raises(ValidationError):
        services.resolve(conference, actor=user, accept=True, reason="Mudei de ideia")


def test_a_match_cannot_be_overridden_as_if_it_were_a_divergence(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, *_ = world
    make_guide(office, company)
    conference = ingest(office, user, das_text()).conferences.get()
    with pytest.raises(ValidationError):
        services.resolve(conference, actor=user, accept=True, reason="Sem necessidade")


def test_without_a_guide_the_item_stays_open_until_one_arrives(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    document = ingest(office, user, das_text())
    conference = document.conferences.get()
    assert conference.outcome == ClosingConference.Outcome.WAITING
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING
    make_guide(office, company)
    services.reevaluate_waiting(office, company=company, competence=date(2026, 8, 1))
    document.refresh_from_db()
    latest = document.conferences.first()
    assert latest is not None
    assert latest.outcome == ClosingConference.Outcome.MATCHED
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED


def test_two_candidate_guides_are_not_guessed_between(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    make_guide(office, company, reference="DAS-A")
    make_guide(office, company, reference="DAS-B", cents=999900)
    conference = ingest(office, user, das_text()).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.WAITING
    assert "mais de uma guia" in conference.note.lower()
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING


def test_a_guide_of_another_company_or_kind_is_not_a_reference(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, *_ = world
    other = make_company(office, "Outra", "11.222.333/0001-81")
    make_guide(office, other)
    make_guide(office, company, kind=FiscalGuide.Kind.DCTFWEB, reference="DCTF-1")
    conference = ingest(office, user, das_text()).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.WAITING


def test_a_zero_value_clears_without_a_guide(world) -> None:  # type: ignore[no-untyped-def]
    office, user, _, _, activity = world
    conference = ingest(office, user, das_text(amount="0,00")).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.ZERO
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED


def test_zero_does_not_clear_when_the_layout_turns_that_off(world) -> None:  # type: ignore[no-untyped-def]
    office, user, _, layout, activity = world
    layout.zero_clears = False
    layout.save()
    conference = ingest(office, user, das_text(amount="0,00")).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.WAITING
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING


def test_a_read_only_layout_clears_by_reading_unless_it_asks_for_a_person(world) -> None:  # type: ignore[no-untyped-def]
    office, user, _, layout, activity = world
    layout.compare = ClosingLayout.Compare.NONE
    layout.save()
    conference = ingest(office, user, das_text()).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.READ
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED

    layout.requires_human = True
    layout.save()
    activity.work_status = OperationalActivity.WorkStatus.PENDING
    activity.completed_at = None
    activity.save()
    other = ingest(office, user, das_text(amount="2.000,00"))
    pending = other.conferences.get()
    assert pending.needs_person
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING
    services.resolve(pending, actor=user, accept=True, reason="Conferido no portal")
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.COMPLETED


def test_a_document_without_a_checklist_item_is_conferred_and_says_so(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    activity.delete()
    make_guide(office, company)
    conference = ingest(office, user, das_text()).conferences.get()
    assert conference.outcome == ClosingConference.Outcome.MATCHED
    assert conference.checklist == ClosingConference.Checklist.NO_ITEM


def test_an_item_that_needs_human_evidence_gets_the_evidence_but_stays_open(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    activity.evidence_requirement = "human"
    activity.save()
    make_guide(office, company)
    conference = ingest(office, user, das_text()).conferences.get()
    activity.refresh_from_db()
    assert conference.checklist == ClosingConference.Checklist.OPEN
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING
    assert activity.evidence_items.filter(kind="document").exists()


def test_the_checklist_item_of_another_competence_or_office_is_never_touched(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, _, activity = world
    activity.competence = date(2026, 7, 1)
    activity.save()
    other_office = make_office("other-2")
    other_company = make_company(other_office)
    foreign = make_activity(other_office, other_company)
    make_guide(office, company)
    ingest(office, user, das_text())
    activity.refresh_from_db()
    foreign.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.PENDING
    assert foreign.work_status == OperationalActivity.WorkStatus.PENDING


def test_paired_documents_are_conferred_against_each_other(world) -> None:  # type: ignore[no-untyped-def]
    office, user, company, *_ = world
    guide_layout = make_layout(
        office,
        code="icms-guia",
        label="Guia ICMS",
        marker="Guia Estadual ICMS",
        kind=ClosingLayout.Kind.GUIDE,
        fields={"amount": "Total a Recolher"},
    )
    receipt = make_layout(
        office,
        code="efd",
        label="EFD ICMS",
        marker="Recibo EFD ICMS",
        compare=ClosingLayout.Compare.PAIRED,
        paired_layout=guide_layout,
        value_source=ClosingLayout.ValueSource.ICMS,
        activity_code="efd",
        fields={"icms": "Valor do ICMS", "amount": "Valor do ICMS"},
    )
    make_activity(office, company, code="efd")
    efd_text = (
        "Recibo EFD ICMS\nCNPJ: " + CNPJ + "\nPeríodo de Apuração: 08/2026\n"
        "Valor do ICMS    500,00\n"
    )
    guide_text = (
        "Guia Estadual ICMS\nCNPJ: " + CNPJ + "\nPeríodo de Apuração: 08/2026\n"
        "Total a Recolher    500,00\n"
    )
    first = ingest(office, user, efd_text, "efd.txt").conferences.get()
    assert first.outcome == ClosingConference.Outcome.WAITING
    ingest(office, user, guide_text, "guia.txt")
    efd_doc = ClosingDocument.objects.get(layout=receipt)
    latest = efd_doc.conferences.first()
    assert latest is not None
    assert latest.outcome == ClosingConference.Outcome.MATCHED
    assert latest.reference_source == ClosingConference.Source.DOCUMENT


# --- layouts -------------------------------------------------------------------------


def test_activation_requires_the_fields_that_identify_and_value_the_document(world) -> None:  # type: ignore[no-untyped-def]
    office, *_ = world
    layout = ClosingLayout.objects.create(organization=office, code="vazio", label="Vazio")
    problems = services.activation_problems(layout)
    joined = " ".join(problems).lower()
    assert "identificador" in joined
    assert "competência" in joined
    assert "empresa" in joined


def test_activation_requires_the_sample_to_read_every_field(world) -> None:  # type: ignore[no-untyped-def]
    _, _, _, layout, _ = world
    layout.sample_text = "Documento de Arrecadação do Simples Nacional\nCNPJ: " + CNPJ
    layout.save()
    problems = services.activation_problems(layout)
    assert any("competência" in problem.lower() for problem in problems)
    layout.sample_text = das_text()
    layout.save()
    assert services.activation_problems(layout) == []


def test_the_diagnosis_shows_what_each_field_read(world) -> None:  # type: ignore[no-untyped-def]
    _, _, _, layout, _ = world
    rows = {row.variable: row for row in services.diagnose(layout, das_text())}
    assert rows["cnpj"].value == CNPJ_DIGITS
    assert rows["amount"].value == "1234.56"
    assert rows["competence"].value == "08/2026"
    assert rows["marker"].found


def test_events_are_audited(world) -> None:  # type: ignore[no-untyped-def]
    office, user, *_ = world
    ingest(office, user, das_text())
    assert AuditEvent.objects.filter(action="closing.document.received").exists()
