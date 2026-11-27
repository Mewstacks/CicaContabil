"""Folha: ciclos autorizados, resultado do agente, envio ao cliente, planilha e agenda."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.folha import catalog, recipients, services, sheets
from apps.folha.models import (
    FolhaContact,
    FolhaCycle,
    FolhaEmail,
    FolhaReport,
    FolhaSheetMark,
    FolhaTask,
)
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob

pytestmark = pytest.mark.django_db
SEP = date(2026, 9, 1)


def _office(slug: str = "fed", *, folha: bool = True) -> Organization:
    org = Organization.objects.create(name=slug, slug=slug)
    ProductModule.objects.create(organization=org, code="folha", enabled=folha)
    return org


def _company(org: Organization, code: str, name: str = "Empresa") -> ClientCompany:
    return ClientCompany.objects.create(
        organization=org, name=f"{name} {code}", dominio_code=code, cnpj_masked="11.222.333/0001-81"
    )


def _authorize(org: Organization, *codes: str) -> None:
    cfg = services.settings_for(org)
    cfg.authorized_codes = list(codes)
    cfg.save()


def _user(org: Organization, role: str = "owner") -> User:
    user = User.objects.create_user(
        email=f"{role}-{uuid4().hex[:8]}@{org.slug}.test", password="uma-senha-longa"
    )
    Membership.objects.create(organization=org, user=user, role=role)
    return user


def _agent_report(
    job: RpaJob,
    *,
    status: str = "ok",
    content: bytes = b"%PDF-1.4 x",
    validation: str = "pdf_validado",
) -> None:
    """O que o agente faz: reserva, entrega o arquivo, fecha."""

    claimed = rpa.claim_next(
        organization=job.organization, agent_id="ag", kinds=[services.KIND_REPORT]
    )
    assert claimed is not None and claimed[0].pk == job.pk
    _, token = claimed
    common: dict[str, Any] = {
        "job_id": job.pk,
        "organization": job.organization,
        "agent_id": "ag",
        "token": token,
    }
    sha = hashlib.sha256(content).hexdigest()
    if status == "ok":
        rpa.attach_artifact(**common, name="r.pdf", content=content, claimed_sha256=sha)
    result: dict[str, Any] = {"status": status, "validation": validation}
    if status == "ok":
        result.update({"sha256": sha, "size": len(content), "output_name": "r.pdf"})
    rpa.complete(**common, result=result)


# --- puros ----------------------------------------------------------------------------------


def test_recipient_rules_fail_closed() -> None:
    one = recipients.decide([recipients.Contact(("a@x.com.br",), "")])
    assert one.situation == "unico" and one.recipients == ["a@x.com.br"]
    marked = recipients.decide(
        [
            recipients.Contact(("a@x.com.br",), "geral"),
            recipients.Contact(("f@x.com.br",), "Fiolha"),
        ]
    )
    assert marked.situation == "marcado" and marked.recipients == ["f@x.com.br"]
    unmarked = recipients.decide(
        [recipients.Contact(("a@x.com.br",), ""), recipients.Contact(("b@x.com.br",), "")]
    )
    assert unmarked.situation == "ambiguo" and unmarked.blocks_sending
    two_marked = recipients.decide(
        [recipients.Contact(("a@x.com.br",), "folha"), recipients.Contact(("b@x.com.br",), "pagto")]
    )
    assert two_marked.situation == "ambiguo"
    refused = recipients.decide([recipients.Contact(("a@x.com.br",), "SEM CONTATO / honorário")])
    assert refused.situation == "sem_email"
    assert recipients.is_refused("mandar no WPP") and not recipients.is_refused(
        "mandar no WPP folha"
    )
    assert recipients.extract_emails("a@x.com.br; B@X.com.br / a@x.com.br x@y") == [
        "a@x.com.br",
        "b@x.com.br",
    ]


def test_recipient_choice_only_among_current_candidates() -> None:
    decision = recipients.decide(
        [recipients.Contact(("a@x.com.br",), ""), recipients.Contact(("b@x.com.br",), "")]
    )
    assert recipients.resolve(decision, chosen=["b@x.com.br"]) == ["b@x.com.br"]
    with pytest.raises(recipients.RecipientError):
        recipients.resolve(decision, chosen=["intruso@x.com.br"])
    with pytest.raises(recipients.RecipientError):
        recipients.resolve(decision, chosen=[], manual="novo@x.com.br")  # há contato válido
    empty = recipients.decide([])
    assert recipients.resolve(empty, chosen=[], manual="novo@x.com.br") == ["novo@x.com.br"]
    with pytest.raises(recipients.RecipientError):
        recipients.resolve(empty, chosen=[], manual="a@x.com.br, b@x.com.br")


def test_catalog_is_fail_closed() -> None:
    items = ("extrato",)
    good = {
        "version": "1",
        "reports": {
            "extrato": [
                {"key": "total", "type": "dinheiro", "required": True, "pattern": r"Total:\s*(\S+)"}
            ]
        },
    }
    catalog.validate_catalog(good, required_items=items)
    for broken in (
        {"version": "", "reports": good["reports"]},
        {"version": "1", "reports": {}},
        {"version": "1", "reports": {"extrato": []}},
        {
            "version": "1",
            "reports": {"extrato": [{**good["reports"]["extrato"][0], "pattern": "("}]},
        },
        {
            "version": "1",
            "reports": {"extrato": [{**good["reports"]["extrato"][0], "pattern": "Total"}]},
        },
        {
            "version": "1",
            "reports": {"extrato": [{**good["reports"]["extrato"][0], "key": "Total"}]},
        },
        {
            "version": "1",
            "reports": {"extrato": [{**good["reports"]["extrato"][0], "required": "sim"}]},
        },
    ):
        with pytest.raises(catalog.CatalogIncomplete):
            catalog.validate_catalog(broken, required_items=items)
    found, missing = catalog.extract("Total: 1.200,00", good["reports"]["extrato"])
    assert found[0].value == "1.200,00" and not missing
    _, missing = catalog.extract("nada", good["reports"]["extrato"])
    assert missing == ["total"]


def test_sheet_tab_and_row_detection() -> None:
    titles = ["Resumo", "09/2026", "Agosto 2026"]
    assert sheets.find_tab(titles, SEP) == "09/2026"
    for title in ("9-2026", "092026", "2026-09", "Set/26", "Setembro 2026", "Setembro de 2026"):
        assert sheets.find_tab([title, "x"], SEP) == title
    assert sheets.find_tab(["Setembro", "x"], SEP) == "Setembro"
    with pytest.raises(sheets.SheetError):
        sheets.find_tab(["09/2026", "9-2026"], SEP)
    with pytest.raises(sheets.SheetError):
        sheets.find_tab(["Agosto"], SEP)
    rows = [
        ["Cód", "Empresa", "CNPJ"],
        ["12", "ACME COMERCIO LTDA", "11.222.333/0001-81"],
        ["7", "Outra", ""],
    ]
    assert sheets.find_row(rows, code="12") == 2
    assert sheets.find_row(rows, code="", cnpj_digits="11222333000181") == 2
    assert sheets.find_row(rows, code="", name="Acme Ltda") == 2
    with pytest.raises(sheets.SheetError):
        sheets.find_row(rows, code="99")
    dup = [*rows, ["12", "ACME", ""]]
    with pytest.raises(sheets.SheetError):
        sheets.find_row(dup, code="12")


# --- ciclo ----------------------------------------------------------------------------------


def test_cycle_refuses_unauthorized_company_and_empty_allowlist() -> None:
    org = _office()
    company = _company(org, "10")
    with pytest.raises(services.FolhaError):  # lista vazia: nada é autorizado
        services.create_cycle(
            organization=org, user=None, competence=SEP, companies=[company], items=["extrato"]
        )
    _authorize(org, "99")
    with pytest.raises(services.FolhaError):
        services.create_cycle(
            organization=org, user=None, competence=SEP, companies=[company], items=["extrato"]
        )
    assert not FolhaCycle.objects.exists() and not RpaJob.objects.exists()


def test_other_office_company_is_never_authorized() -> None:
    a, b = _office("a"), _office("b")
    _authorize(a, "10")
    foreign = _company(b, "10")
    assert not services.is_authorized(a, foreign)


def test_calc_needs_confirmation_and_draft_waits_for_it() -> None:
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    with pytest.raises(services.FolhaError):
        services.create_cycle(
            organization=org, user=None, competence=SEP, companies=[company], items=["calculo"]
        )
    draft = services.create_cycle(
        organization=org,
        user=None,
        competence=SEP,
        companies=[company],
        items=["calculo", "extrato"],
        draft=True,
    )
    assert draft.status == FolhaCycle.Status.DRAFT and not RpaJob.objects.exists()
    user = _user(org)
    with pytest.raises(services.FolhaError):
        services.confirm_draft(draft, user=user, confirm_calc=False)
    services.confirm_draft(draft, user=user, confirm_calc=True)
    assert RpaJob.objects.filter(kind=services.KIND_REPORT).count() == 2
    # a autorização é revalidada na confirmação
    other = services.create_cycle(
        organization=org,
        user=None,
        competence=date(2026, 8, 1),
        companies=[company],
        items=["extrato"],
        draft=True,
    )
    _authorize(org)
    with pytest.raises(services.FolhaError):
        services.confirm_draft(other, user=user, confirm_calc=False)


def test_one_active_task_per_company_item_competence() -> None:
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    services.create_cycle(
        organization=org, user=None, competence=SEP, companies=[company], items=["extrato"]
    )
    with pytest.raises(services.FolhaError):
        services.create_cycle(
            organization=org, user=None, competence=SEP, companies=[company], items=["extrato"]
        )
    assert FolhaTask.objects.count() == 1


def test_agent_result_updates_task_cycle_and_marks_sheet() -> None:
    org = _office()
    cfg = services.settings_for(org)
    cfg.authorized_codes = ["10"]
    cfg.sheets_enabled = True
    cfg.sheets_spreadsheet_id = "plan"
    cfg.save()
    company = _company(org, "10")
    cycle = services.create_cycle(
        organization=org,
        user=None,
        competence=SEP,
        companies=[company],
        items=["calculo", "extrato"],
        confirm_calc=True,
    )
    jobs = list(RpaJob.objects.order_by("created_at"))
    assert [j.payload["item"] for j in jobs] == ["calculo", "extrato"]
    _agent_report(jobs[0], content=b"print do calculo")
    cycle.refresh_from_db()
    assert cycle.status == FolhaCycle.Status.QUEUED
    assert FolhaSheetMark.objects.filter(stage="calc").exists()
    _agent_report(jobs[1])
    cycle.refresh_from_db()
    task = FolhaTask.objects.get(item="extrato")
    assert task.status == FolhaTask.Status.OK and task.validation == "pdf_validado"
    assert FolhaSheetMark.objects.filter(stage="reports").exists()
    # sem catálogo: o relatório fica reprovado, nunca derruba o resultado
    assert FolhaReport.objects.get(task=task).state == FolhaReport.State.REJECTED
    assert cycle.status == FolhaCycle.Status.REVIEW


def test_result_without_delivered_file_is_refused_and_job_stays_leased() -> None:
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    services.create_cycle(
        organization=org, user=None, competence=SEP, companies=[company], items=["extrato"]
    )
    job = RpaJob.objects.get()
    _claimed, token = rpa.claim_next(
        organization=org, agent_id="ag", kinds=[services.KIND_REPORT]
    )  # type: ignore[misc]
    sha = hashlib.sha256(b"x").hexdigest()
    with pytest.raises(Exception, match="arquivo do relatório"):
        rpa.complete(
            job_id=job.pk,
            organization=org,
            agent_id="ag",
            token=token,
            result={
                "status": "ok",
                "validation": "pdf_validado",
                "sha256": sha,
                "size": 1,
                "output_name": "r.pdf",
            },
        )
    job.refresh_from_db()
    assert job.state == RpaJob.State.LEASED
    assert FolhaTask.objects.get().status == FolhaTask.Status.PENDING


def test_empty_and_failed_results() -> None:
    org = _office()
    _authorize(org, "10", "11")
    c1, c2 = _company(org, "10"), _company(org, "11")
    cycle = services.create_cycle(
        organization=org, user=None, competence=SEP, companies=[c1, c2], items=["extrato"]
    )
    first, second = list(RpaJob.objects.order_by("created_at"))
    _agent_report(first, status="sem_dados", validation="sem_dados")
    assert FolhaTask.objects.get(company=c1).status == FolhaTask.Status.EMPTY
    claimed = rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND_REPORT])
    assert claimed is not None
    rpa.fail(
        job_id=second.pk,
        organization=org,
        agent_id="ag",
        token=claimed[1],
        code="conferencia_divergente",
        detail="valor diferente",
    )
    assert FolhaTask.objects.get(company=c2).status == FolhaTask.Status.FAILED
    cycle.refresh_from_db()
    assert cycle.status == FolhaCycle.Status.PARTIAL
    user = _user(org)
    services.reprocess(FolhaTask.objects.get(company=c2), user=user)
    assert RpaJob.objects.filter(state=RpaJob.State.QUEUED).count() == 1


def test_contacts_job_replaces_contacts_and_ignores_other_companies() -> None:
    org = _office()
    company = _company(org, "10")
    _company(org, "11")
    FolhaContact.objects.create(organization=org, company=company, emails=["velho@x.com.br"])
    rpa.enqueue(
        organization=org,
        kind=services.KIND_CONTACTS,
        idempotency_key="c1",
        payload={"company_codes": ["10"]},
    )
    job, token = rpa.claim_next(organization=org, agent_id="ag", kinds=[services.KIND_CONTACTS])  # type: ignore[misc]
    rpa.complete(
        job_id=job.pk,
        organization=org,
        agent_id="ag",
        token=token,
        result={
            "contacts": [
                {"company_code": "10", "emails": ["novo@x.com.br"], "note": "folha"},
                {"company_code": "11", "emails": ["fora@x.com.br"], "note": ""},
            ]
        },
    )
    rows = FolhaContact.objects.filter(organization=org)
    assert [r.emails for r in rows] == [["novo@x.com.br"]]


# --- e-mail ---------------------------------------------------------------------------------


def _finished_cycle(
    tmp_path: Any, settings: Any
) -> tuple[Organization, FolhaCycle, ClientCompany, User]:
    settings.MEDIA_ROOT = str(tmp_path)
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    cycle = services.create_cycle(
        organization=org,
        user=None,
        competence=SEP,
        companies=[company],
        items=["calculo", "extrato"],
        confirm_calc=True,
    )
    for job in list(RpaJob.objects.order_by("created_at")):
        _agent_report(job, content=b"%PDF " + job.payload["item"].encode())
    for report in FolhaReport.objects.all():
        report.state = FolhaReport.State.APPROVED
        report.problems = []
        report.save()
    return org, cycle, company, _user(org)


def test_email_flow_never_attaches_calculo_and_sends_once(tmp_path: Any, settings: Any) -> None:
    _org, cycle, company, user = _finished_cycle(tmp_path, settings)
    email = services.build_email(
        cycle=cycle,
        company=company,
        recipients=["c@cli.com.br"],
        sender="f@esc.com.br",
        payment_date=date(2026, 10, 5),
        inss_due_date=date(2026, 10, 20),
    )
    assert [a["name"] for a in email.attachments] == ["Extrato.pdf"]
    again = services.build_email(
        cycle=cycle,
        company=company,
        recipients=["c@cli.com.br"],
        sender="f@esc.com.br",
        payment_date=date(2026, 10, 5),
        inss_due_date=date(2026, 10, 20),
    )
    assert again.pk == email.pk
    with pytest.raises(services.FolhaError):
        services.send_email(email, transport=lambda e, f: "id")  # rascunho não envia
    services.approve_email(email, user=user)
    sent_files: list[Any] = []

    def transport(e: FolhaEmail, files: list[tuple[str, bytes]]) -> str:
        sent_files.extend(files)
        return "msg-1"

    done = services.send_email(email, transport=transport)
    assert done.state == FolhaEmail.State.SENT and done.message_id == "msg-1"
    assert [name for name, _ in sent_files] == ["Extrato.pdf"]
    with pytest.raises(services.FolhaError):
        services.send_email(email, transport=transport)  # nunca duas vezes
    cycle.refresh_from_db()
    assert cycle.status == FolhaCycle.Status.DONE


def test_email_blocked_without_dates_pending_review_or_placeholder(
    tmp_path: Any, settings: Any
) -> None:
    _org, cycle, company, user = _finished_cycle(tmp_path, settings)
    email = services.build_email(
        cycle=cycle,
        company=company,
        recipients=["c@cli.com.br"],
        sender="f@esc.com.br",
        payment_date=None,
        inss_due_date=None,
    )
    with pytest.raises(services.FolhaError):
        services.approve_email(email, user=user)
    email.payment_date, email.inss_due_date = date(2026, 10, 5), date(2026, 10, 20)
    email.body = "Olá {nome}"
    with pytest.raises(services.FolhaError):
        services.approve_email(email, user=user)
    email.body = "Olá"
    report = FolhaReport.objects.get(task__item="extrato")
    report.state = FolhaReport.State.PENDING
    report.save()
    with pytest.raises(services.FolhaError):
        services.approve_email(email, user=user)


def test_failed_send_is_never_retried_only_reconciled(tmp_path: Any, settings: Any) -> None:
    _org, cycle, company, user = _finished_cycle(tmp_path, settings)
    email = services.build_email(
        cycle=cycle,
        company=company,
        recipients=["c@cli.com.br"],
        sender="f@esc.com.br",
        payment_date=date(2026, 10, 5),
        inss_due_date=date(2026, 10, 20),
    )
    services.approve_email(email, user=user)

    def boom(e: FolhaEmail, files: Any) -> str:
        raise TimeoutError("senha=segredo")

    failed = services.send_email(email, transport=boom)
    assert failed.state == FolhaEmail.State.FAILED and "segredo" not in failed.error
    with pytest.raises(services.FolhaError):
        services.send_email(failed, transport=lambda e, f: "x")
    with pytest.raises(services.FolhaError):
        services.reconcile_email(failed, user=user, sent=True, message_id="", note="conferi")
    with pytest.raises(services.FolhaError):
        services.reconcile_email(failed, user=user, sent=False, message_id="", note=" ")
    services.reconcile_email(
        failed, user=user, sent=True, message_id="abc", note="saiu pelo webmail"
    )
    assert FolhaEmail.objects.get().state == FolhaEmail.State.SENT


def test_altered_attachment_after_approval_blocks_send(tmp_path: Any, settings: Any) -> None:
    _org, cycle, company, user = _finished_cycle(tmp_path, settings)
    email = services.build_email(
        cycle=cycle,
        company=company,
        recipients=["c@cli.com.br"],
        sender="f@esc.com.br",
        payment_date=date(2026, 10, 5),
        inss_due_date=date(2026, 10, 20),
    )
    services.approve_email(email, user=user)
    from apps.rpa.models import RpaArtifact

    artifact = RpaArtifact.objects.get(pk=email.attachments[0]["artifact"])
    with artifact.file.storage.open(artifact.file.name, "wb") as handle:
        handle.write(b"adulterado")
    with pytest.raises(services.FolhaError):
        services.send_email(email, transport=lambda e, f: "x")


# --- planilha -------------------------------------------------------------------------------


class FakeSheet:
    def __init__(self, cell: str = "", fail: bool = False) -> None:
        self.cell, self.fail, self.writes = cell, fail, []  # type: ignore[var-annotated]

    def titles(self, spreadsheet_id: str) -> list[str]:
        if self.fail:
            raise sheets.SheetError("Google indisponível.")
        return ["09/2026"]

    def read(self, spreadsheet_id: str, a1: str) -> list[list[str]]:
        if "!A:H" in a1:
            return [["Cód", "Empresa"], ["10", "Empresa 10"]]
        return [[self.cell]] if self.cell else []

    def write(self, spreadsheet_id: str, a1: str, value: str) -> None:
        self.writes.append((a1, value))


def _marked_office() -> Organization:
    org = _office()
    cfg = services.settings_for(org)
    cfg.sheets_enabled, cfg.sheets_spreadsheet_id = True, "plan"
    cfg.save()
    company = _company(org, "10")
    cycle = FolhaCycle.objects.create(organization=org, competence=SEP, status="queued")
    services.queue_mark(cycle, company, "calc")
    services.queue_mark(cycle, company, "calc")  # idempotente
    return org


def test_sheet_mark_written_once_and_never_over_manual_cell() -> None:
    org = _marked_office()
    assert FolhaSheetMark.objects.count() == 1
    client = FakeSheet()
    assert services.flush_marks(org, client)["done"] == 1
    assert client.writes == [("'09/2026'!I2", "CALCULANDO")]
    assert services.flush_marks(org, client)["done"] == 0
    FolhaSheetMark.objects.update(state="pending")
    typed = FakeSheet(cell="feito à mão")
    services.flush_marks(org, typed)
    assert typed.writes == []


def test_sheet_failure_backs_off_and_never_raises() -> None:
    org = _marked_office()
    broken = FakeSheet(fail=True)
    assert services.flush_marks(org, broken)["error"] == 1
    mark = FolhaSheetMark.objects.get()
    assert mark.state == "error" and mark.attempts == 1 and mark.next_try_at is not None
    assert services.flush_marks(org, broken)["skipped"] == 1
    mark.attempts = services.MAX_MARK_ATTEMPTS - 1
    mark.next_try_at = None
    mark.save()
    services.flush_marks(org, broken)
    assert FolhaSheetMark.objects.get().state == "final_error"


def test_sheet_disabled_or_ignored_company_writes_nothing() -> None:
    org = _office()
    company = _company(org, "10")
    cycle = FolhaCycle.objects.create(organization=org, competence=SEP, status="queued")
    services.queue_mark(cycle, company, "calc")
    assert not FolhaSheetMark.objects.exists()
    cfg = services.settings_for(org)
    cfg.sheets_enabled, cfg.sheets_ignore_codes = True, ["10"]
    cfg.save()
    services.queue_mark(cycle, company, "calc")
    assert not FolhaSheetMark.objects.exists()


# --- agenda ---------------------------------------------------------------------------------


def test_due_competence_recovers_lost_days_and_never_repeats() -> None:
    assert services.due_competence(date(2026, 10, 5), 5, None) == date(2026, 9, 1)
    assert services.due_competence(date(2026, 10, 4), 5, None) == date(2026, 8, 1)
    assert services.due_competence(date(2026, 10, 20), 5, date(2026, 9, 1)) is None
    assert services.due_competence(date(2026, 11, 5), 5, date(2026, 9, 1)) == date(2026, 10, 1)
    assert services.due_competence(date(2027, 1, 7), 5, None) == date(2026, 12, 1)


def test_schedule_only_creates_a_draft_and_is_idempotent() -> None:
    org = _office()
    _authorize(org, "10")
    _company(org, "10")
    _company(org, "11")  # fora da lista autorizada
    cfg = services.settings_for(org)
    cfg.schedule_enabled, cfg.schedule_codes, cfg.schedule_items = (
        True,
        ["10", "11"],
        ["calculo", "extrato"],
    )
    cfg.save()
    cycle = services.run_schedule(org, today=date(2026, 10, 5))
    assert cycle is not None and cycle.status == FolhaCycle.Status.DRAFT and cycle.from_schedule
    assert cycle.tasks.count() == 2 and not RpaJob.objects.exists()
    assert services.run_schedule(org, today=date(2026, 10, 6)) is None
    assert FolhaCycle.objects.count() == 1


def test_schedule_off_does_nothing() -> None:
    org = _office()
    _authorize(org, "10")
    _company(org, "10")
    assert services.run_schedule(org, today=date(2026, 10, 5)) is None


# --- telas ----------------------------------------------------------------------------------


def _client(org: Organization, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(org.id)
    session.save()
    return client


def test_pages_are_closed_when_module_is_off() -> None:
    org = _office(folha=False)
    client = _client(org, _user(org))
    assert client.get("/app/folha/").status_code == 403
    assert client.post("/app/folha/ciclos/novo/", {}).status_code == 403


def test_pages_render_and_create_flow_enforces_guards() -> None:
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    owner = _user(org)
    client = _client(org, owner)
    page = client.get("/app/folha/")
    assert page.status_code == 200 and "Empresa 10" in page.content.decode()
    refused = client.post(
        "/app/folha/ciclos/novo/",
        {"competencia": "2026-09", "empresas": [company.pk], "itens": ["calculo"]},
        follow=True,
    )
    assert "confirme" in refused.content.decode() and not FolhaCycle.objects.exists()
    ok = client.post(
        "/app/folha/ciclos/novo/",
        {"competencia": "2026-09", "empresas": [company.pk], "itens": ["extrato"]},
    )
    cycle = FolhaCycle.objects.get()
    assert ok.status_code == 302 and ok["Location"].endswith(f"/app/folha/ciclos/{cycle.pk}/")
    assert client.get(ok["Location"]).status_code == 200
    assert client.get(f"/app/folha/ciclos/{cycle.pk}/envio/{company.pk}/").status_code == 200
    assert client.get("/app/folha/configuracao/").status_code == 200


def test_office_isolation_on_cycle_page() -> None:
    a, b = _office("a"), _office("b")
    _authorize(a, "10")
    cycle = services.create_cycle(
        organization=a, user=None, competence=SEP, companies=[_company(a, "10")], items=["extrato"]
    )
    client = _client(b, _user(b))
    assert client.get(f"/app/folha/ciclos/{cycle.pk}/").status_code == 404


def test_readonly_role_cannot_write_or_change_config() -> None:
    org = _office()
    _authorize(org, "10")
    company = _company(org, "10")
    viewer = _user(org, "auditor")
    client = _client(org, viewer)
    assert client.get("/app/folha/").status_code == 200
    denied = client.post(
        "/app/folha/ciclos/novo/",
        {"competencia": "2026-09", "empresas": [company.pk], "itens": ["extrato"]},
    )
    assert denied.status_code in (302, 403) and not FolhaCycle.objects.exists()
    operator = _client(org, _user(org, "operator"))
    assert operator.post("/app/folha/configuracao/", {"autorizadas": "10, 11"}).status_code in (
        302,
        403,
    )
    assert services.settings_for(org).authorized_codes == ["10"]
