"""Regras da Folha: ciclos, tarefas, resultado do agente, envio ao cliente e agenda.

Travas que valem aqui (todas já testadas no HubFedrizzi e mantidas):

* só empresa da lista autorizada do escritório entra num ciclo (lista vazia = nada);
* o cálculo ALTERA o Domínio: exige confirmação explícita, e o ciclo da agenda nasce rascunho;
* no máximo uma tarefa ativa por empresa/item/competência; repetir um resultado exige pedir
  reprocesso no mesmo ciclo;
* e-mail só sai de um rascunho aprovado, com anexos de hash conferido; falha depois de iniciar o
  envio NUNCA reenvia sozinha — só reconciliação humana com justificativa;
* o cálculo (impressão interna) nunca é anexado.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaArtifact, RpaJob
from apps.rpa.registry import RpaError

from . import catalog as field_catalog
from .models import (
    ITEM_LABELS,
    ITEMS,
    NEVER_ATTACH,
    FolhaCatalog,
    FolhaCycle,
    FolhaEmail,
    FolhaReport,
    FolhaSettings,
    FolhaSheetMark,
    FolhaTask,
    FolhaTitle,
)

KIND_REPORT = "folha.relatorio"
KIND_CONTACTS = "folha.contatos"
VALIDATIONS = frozenset({"captura", "pdf_validado", "pdf_nao_validado", "sem_dados", "falha"})
_SHA = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER = re.compile(r"\{[^}]*\}")
_HTML = re.compile(r"<[a-zA-Z/][^>]*>")
MAX_ATTACHMENT_BYTES = 18_000_000

Transport = Callable[[FolhaEmail, list[tuple[str, bytes]]], str]


class FolhaError(Exception):
    """Regra de negócio da Folha recusou a operação; a mensagem é segura para a tela."""


def settings_for(organization: Organization) -> FolhaSettings:
    obj, _ = FolhaSettings.objects.get_or_create(organization=organization)
    return obj


def competence_start(value: date) -> date:
    return value.replace(day=1)


def is_authorized(organization: Organization, company: ClientCompany) -> bool:
    codes = {str(c).strip() for c in settings_for(organization).authorized_codes}
    return bool(
        company.organization_id == organization.pk
        and company.active
        and company.dominio_code
        and company.dominio_code in codes
    )


def title_for(organization: Organization, item: str) -> str:
    row = FolhaTitle.objects.filter(organization=organization, key=item).first()
    return row.name if row else ITEM_LABELS.get(item, item)


def _audit(action: str, organization: Organization, target: Any, **meta: Any) -> None:
    record_event(action=action, organization=organization, target=target, metadata=meta)


# --- ciclo ---------------------------------------------------------------------------------


def create_cycle(
    *,
    organization: Organization,
    user: User | None,
    competence: date,
    companies: list[ClientCompany],
    items: list[str],
    confirm_calc: bool = False,
    draft: bool = False,
    from_schedule: bool = False,
    note: str = "",
) -> FolhaCycle:
    competence = competence_start(competence)
    wanted = [i for i in ITEMS if i in set(items)]
    if not wanted or len(wanted) != len(set(items)):
        raise FolhaError("Escolha ao menos um item válido.")
    if not companies:
        raise FolhaError("Escolha ao menos uma empresa.")
    blocked = [c.name for c in companies if not is_authorized(organization, c)]
    if blocked:
        raise FolhaError("Empresa fora da lista autorizada da Folha: " + ", ".join(blocked[:3]))
    if "calculo" in wanted and not draft and not confirm_calc:
        raise FolhaError("O cálculo altera dados no Domínio: confirme para continuar.")
    with transaction.atomic():
        cycle = FolhaCycle.objects.create(
            organization=organization,
            competence=competence,
            status=FolhaCycle.Status.DRAFT,
            note=note[:200],
            from_schedule=from_schedule,
            created_by=user,
            confirmed_calc=confirm_calc and not draft,
        )
        _make_tasks(cycle, companies, wanted)
        _audit("folha.cycle.created", organization, cycle, draft=draft, items=wanted)
        if not draft:
            enqueue_cycle(cycle)
    return cycle


def _make_tasks(cycle: FolhaCycle, companies: list[ClientCompany], items: list[str]) -> None:
    ordered = sorted(companies, key=lambda c: (c.dominio_code.zfill(12), c.pk))
    for company in ordered:
        for item in items:
            done = FolhaTask.objects.filter(
                organization=cycle.organization,
                company=company,
                item=item,
                competence=cycle.competence,
                status__in=[*FolhaTask.ACTIVE, FolhaTask.Status.OK, FolhaTask.Status.EMPTY],
            ).exists()
            if done:
                raise FolhaError(
                    f"{company.name}: {ITEM_LABELS[item]} já existe nesta competência. "
                    "Reprocesse no ciclo existente."
                )
            try:
                with transaction.atomic():
                    FolhaTask.objects.create(
                        organization=cycle.organization,
                        cycle=cycle,
                        company=company,
                        item=item,
                        competence=cycle.competence,
                    )
            except IntegrityError as exc:
                raise FolhaError(f"{company.name}: já há tarefa ativa para este item.") from exc


def enqueue_cycle(cycle: FolhaCycle) -> int:
    count = 0
    for task in cycle.tasks.filter(
        status=FolhaTask.Status.PENDING, job__isnull=True
    ).select_related("company"):
        _enqueue_task(task)
        count += 1
    cycle.status = FolhaCycle.Status.QUEUED
    cycle.save(update_fields=["status", "updated_at"])
    return count


def _enqueue_task(task: FolhaTask) -> RpaJob:
    job, _ = rpa.enqueue(
        organization=task.organization,
        kind=KIND_REPORT,
        idempotency_key=f"task:{task.pk}:{task.attempts}",
        payload={
            "task_id": str(task.pk),
            "company_code": task.company.dominio_code,
            "item": task.item,
            "competence": task.competence.strftime("%m/%Y"),
            "title": title_for(task.organization, task.item),
        },
    )
    task.job = job
    task.save(update_fields=["job", "updated_at"])
    return job


def confirm_draft(cycle: FolhaCycle, *, user: User, confirm_calc: bool) -> FolhaCycle:
    """Rascunho (da agenda ou manual) vira fila: revalida a lista autorizada e a confirmação."""

    if cycle.status != FolhaCycle.Status.DRAFT:
        raise FolhaError("Só um rascunho pode ser confirmado.")
    companies = [t.company for t in cycle.tasks.select_related("company")]
    if any(not is_authorized(cycle.organization, c) for c in companies):
        raise FolhaError("Há empresa fora da lista autorizada da Folha.")
    if cycle.tasks.filter(item="calculo").exists() and not confirm_calc:
        raise FolhaError("O cálculo altera dados no Domínio: confirme para continuar.")
    with transaction.atomic():
        cycle.confirmed_calc = confirm_calc
        cycle.save(update_fields=["confirmed_calc", "updated_at"])
        enqueue_cycle(cycle)
        _audit("folha.cycle.draft_confirmed", cycle.organization, cycle, user=str(user.pk))
    return cycle


def reprocess(task: FolhaTask, *, user: User, confirm_calc: bool = False) -> FolhaTask:
    if task.status not in FolhaTask.FINISHED:
        raise FolhaError("A tarefa ainda está ativa.")
    if task.item == "calculo" and not confirm_calc:
        raise FolhaError("O cálculo altera dados no Domínio: confirme para continuar.")
    if not is_authorized(task.organization, task.company):
        raise FolhaError("Empresa fora da lista autorizada da Folha.")
    with transaction.atomic():
        task.status = FolhaTask.Status.PENDING
        task.attempts += 1
        task.error = ""
        task.validation = ""
        task.finished_at = None
        task.job = None
        task.save()
        _enqueue_task(task)
        recompute(task.cycle)
        _audit("folha.task.reprocessed", task.organization, task, user=str(user.pk))
    return task


def cancel_cycle(cycle: FolhaCycle, *, user: User) -> None:
    with transaction.atomic():
        for task in cycle.tasks.filter(status=FolhaTask.Status.PENDING).select_related("job"):
            if task.job is not None and task.job.state == RpaJob.State.QUEUED:
                rpa.cancel(task.job.pk, organization=cycle.organization)
            task.status = FolhaTask.Status.CANCELLED
            task.save(update_fields=["status", "updated_at"])
        recompute(cycle)
        _audit("folha.cycle.cancelled", cycle.organization, cycle, user=str(user.pk))


def recompute(cycle: FolhaCycle) -> str:
    """Estado do ciclo a partir das tarefas. Rascunho nunca é recalculado."""

    if cycle.status == FolhaCycle.Status.DRAFT:
        return cycle.status
    statuses = list(cycle.tasks.values_list("status", flat=True))
    S = FolhaTask.Status
    if not statuses:
        new = cycle.status
    elif S.RUNNING in statuses:
        new = FolhaCycle.Status.RUNNING
    elif S.PENDING in statuses:
        new = FolhaCycle.Status.QUEUED
    elif all(s == S.CANCELLED for s in statuses):
        new = FolhaCycle.Status.CANCELLED
    elif S.FAILED in statuses or S.CANCELLED in statuses:
        new = FolhaCycle.Status.PARTIAL
    else:
        reports = FolhaReport.objects.filter(task__cycle=cycle)
        pending = reports.exclude(state=FolhaReport.State.APPROVED).exists()
        new = FolhaCycle.Status.REVIEW if pending else FolhaCycle.Status.APPROVAL
        if _all_emails_sent(cycle):
            new = FolhaCycle.Status.DONE
    if new != cycle.status:
        cycle.status = new
        cycle.save(update_fields=["status", "updated_at"])
    return new


def _all_emails_sent(cycle: FolhaCycle) -> bool:
    emails = cycle.emails.exclude(state=FolhaEmail.State.VOID)
    return emails.exists() and not emails.exclude(state=FolhaEmail.State.SENT).exists()


# --- resultado do agente -------------------------------------------------------------------


def validate_report_result(result: dict[str, Any]) -> None:
    status = result.get("status")
    if status not in {"ok", "falha", "sem_dados"}:
        raise RpaError("validacao", "Estado do relatório inválido.")
    validation = result.get("validation", "")
    if validation and validation not in VALIDATIONS:
        raise RpaError("validacao", "Validação fora do vocabulário.")
    if status == "ok":
        if not _SHA.match(str(result.get("sha256", ""))):
            raise RpaError("validacao", "Hash do arquivo ausente.")
        if not result.get("output_name") or int(result.get("size") or 0) <= 0 or not validation:
            raise RpaError("validacao", "Resultado 'ok' incompleto.")


def _task_of(job: RpaJob) -> FolhaTask:
    try:
        return (
            FolhaTask.objects.select_for_update()
            .select_related("company", "cycle")
            .get(pk=job.payload.get("task_id"), organization=job.organization)
        )
    except (FolhaTask.DoesNotExist, ValueError, TypeError) as exc:
        raise RpaError("validacao", "Tarefa da Folha não encontrada.") from exc


def on_report_success(job: RpaJob) -> None:
    task = _task_of(job)
    result = job.result
    now = timezone.now()
    if result["status"] == "ok":
        needs_file = task.item not in NEVER_ATTACH
        artifact = job.artifacts.filter(sha256=result["sha256"]).first()
        if needs_file and artifact is None:
            raise RpaError("validacao", "O arquivo do relatório não foi entregue.")
        task.status = FolhaTask.Status.OK
        task.sha256 = result["sha256"]
        task.output_name = str(result["output_name"])[:200]
        task.byte_size = int(result["size"])
        if needs_file and artifact is not None:
            _read_report(task, artifact)
    elif result["status"] == "sem_dados":
        task.status = FolhaTask.Status.EMPTY
    else:
        task.status = FolhaTask.Status.FAILED
        task.error = str(result.get("error", ""))[:500]
    task.validation = str(result.get("validation", ""))
    task.finished_at = now
    task.save()
    if task.item == "calculo" and task.status == FolhaTask.Status.OK:
        queue_mark(task.cycle, task.company, FolhaSheetMark.Stage.CALC)
    _maybe_mark_reports(task)
    recompute(task.cycle)


def on_report_failure(job: RpaJob) -> None:
    task = _task_of(job)
    task.status = FolhaTask.Status.FAILED
    task.error = job.error_detail or job.error_code
    task.finished_at = timezone.now()
    task.save()
    recompute(task.cycle)


def _read_report(task: FolhaTask, artifact: RpaArtifact) -> None:
    """Lê o PDF com o catálogo ativo. Falha do parser vira relatório reprovado, nunca erro."""

    active = FolhaCatalog.objects.filter(organization=task.organization, active=True).first()
    report, _ = FolhaReport.objects.get_or_create(
        task=task, defaults={"organization": task.organization}
    )
    if active is None:
        report.state = FolhaReport.State.REJECTED
        report.problems = ["Catálogo de campos ainda não cadastrado."]
        report.save()
        return
    try:
        rules = active.rules["reports"][task.item]
        text = _pdf_text(artifact)
        found, missing = field_catalog.extract(text, rules)
    except Exception as exc:
        report.state = FolhaReport.State.REJECTED
        report.problems = [f"Leitura falhou ({type(exc).__name__})."]
        report.save()
        return
    report.parser_version = f"{field_catalog.PARSER_VERSION}/{active.version}"
    report.fields = [
        {"key": f.key, "value": f.value, "original": f.value, "corrected": "", "why": ""}
        for f in found
    ]
    report.problems = [f"Campo obrigatório ausente: {m}" for m in missing]
    report.state = FolhaReport.State.REJECTED if missing else FolhaReport.State.PENDING
    report.save()


def _pdf_text(artifact: RpaArtifact) -> str:
    from pypdf import PdfReader

    with artifact.file.open("rb") as handle:
        reader = PdfReader(handle, strict=True)
        return "\n".join((page.extract_text() or "") for page in reader.pages[:30])


def approve_report(report: FolhaReport, *, user: User) -> None:
    if report.state == FolhaReport.State.REJECTED and report.problems:
        raise FolhaError("O relatório tem pendências de leitura; corrija ou reprocesse.")
    report.state = FolhaReport.State.APPROVED
    report.save(update_fields=["state", "updated_at"])
    recompute(report.task.cycle)
    _audit("folha.report.approved", report.organization, report, user=str(user.pk))


def correct_field(report: FolhaReport, *, key: str, value: str, why: str, user: User) -> None:
    if not why.strip():
        raise FolhaError("A correção exige justificativa.")
    for entry in report.fields:
        if entry["key"] == key:
            entry["corrected"] = value
            entry["why"] = why[:300]
            break
    else:
        raise FolhaError("Campo desconhecido.")
    report.problems = [p for p in report.problems if key not in p]
    report.state = FolhaReport.State.PENDING
    report.save()
    _audit("folha.report.field_corrected", report.organization, report, key=key, user=str(user.pk))


# --- planilha ------------------------------------------------------------------------------


def queue_mark(cycle: FolhaCycle, company: ClientCompany, stage: str) -> None:
    cfg = settings_for(cycle.organization)
    if not cfg.sheets_enabled or company.dominio_code in {str(c) for c in cfg.sheets_ignore_codes}:
        return
    FolhaSheetMark.objects.get_or_create(
        organization=cycle.organization,
        competence=cycle.competence,
        company_code=company.dominio_code,
        stage=stage,
        defaults={"company": company},
    )


def _maybe_mark_reports(task: FolhaTask) -> None:
    items = task.cycle.tasks.filter(company=task.company).exclude(item="calculo")
    states = list(items.values_list("status", flat=True))
    if not states or any(s in FolhaTask.ACTIVE for s in states):
        return
    if FolhaTask.Status.OK in states and FolhaTask.Status.FAILED not in states:
        queue_mark(task.cycle, task.company, FolhaSheetMark.Stage.REPORTS)


# --- e-mail --------------------------------------------------------------------------------

DEFAULT_BODY = (
    "Prezados,\n\nSegue a folha de pagamento de {competencia}.\n\n"
    "Pagamento: {pagamento}\nVencimento do INSS: {vencimento_inss}\n\nAtenciosamente."
)


def _date_text(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def build_email(
    *,
    cycle: FolhaCycle,
    company: ClientCompany,
    recipients: list[str],
    sender: str,
    payment_date: date | None,
    inss_due_date: date | None,
) -> FolhaEmail:
    """Um rascunho por ciclo por empresa (idempotente). Anexos: só relatório salvo e validado."""

    if not recipients:
        raise FolhaError("Sem destinatário definido.")
    attachments: list[dict[str, str]] = []
    total = 0
    for task in cycle.tasks.filter(company=company, status=FolhaTask.Status.OK).exclude(
        item__in=NEVER_ATTACH
    ):
        if task.validation != "pdf_validado":
            raise FolhaError(f"{ITEM_LABELS[task.item]}: o PDF ainda não foi validado; reprocesse.")
        artifact = RpaArtifact.objects.filter(job=task.job, sha256=task.sha256).first()
        if artifact is None:
            raise FolhaError(f"{ITEM_LABELS[task.item]}: arquivo não encontrado.")
        total += artifact.byte_size
        attachments.append(
            {
                "artifact": str(artifact.pk),
                "name": f"{title_for(cycle.organization, task.item)}.pdf",
                "sha256": artifact.sha256,
            }
        )
    if not attachments:
        raise FolhaError("Nenhum relatório validado para anexar.")
    if total > MAX_ATTACHMENT_BYTES:
        raise FolhaError("Os anexos passam do limite de tamanho do e-mail.")
    key = f"cycle:{cycle.pk}:company:{company.pk}"
    email, _ = FolhaEmail.objects.get_or_create(
        organization=cycle.organization,
        idempotency_key=key,
        defaults={
            "cycle": cycle,
            "company": company,
            "sender": sender,
            "recipients": recipients,
            "subject": f"Folha de pagamento {cycle.competence:%m/%Y} — {company.name}"[:200],
            "body": DEFAULT_BODY.format(
                competencia=f"{cycle.competence:%m/%Y}",
                pagamento=_date_text(payment_date),
                vencimento_inss=_date_text(inss_due_date),
            ),
            "attachments": attachments,
            "payment_date": payment_date,
            "inss_due_date": inss_due_date,
        },
    )
    return email


def approve_email(email: FolhaEmail, *, user: User) -> FolhaEmail:
    if email.state != FolhaEmail.State.DRAFT:
        raise FolhaError("Só um rascunho pode ser aprovado.")
    if _PLACEHOLDER.search(email.body) or _HTML.search(email.body):
        raise FolhaError("O texto tem marcador pendente ou HTML.")
    if not email.payment_date or not email.inss_due_date:
        raise FolhaError("Informe as datas de pagamento e de vencimento do INSS.")
    if not is_authorized(email.organization, email.company):
        raise FolhaError("Empresa fora da lista autorizada da Folha.")
    if email.cycle.tasks.filter(company=email.company, status=FolhaTask.Status.FAILED).exists():
        raise FolhaError("Há relatório com falha para esta empresa.")
    pending = FolhaReport.objects.filter(
        task__cycle=email.cycle, task__company=email.company
    ).exclude(state=FolhaReport.State.APPROVED)
    if pending.exists():
        raise FolhaError("Há relatório ainda sem conferência aprovada.")
    for entry in email.attachments:
        artifact = RpaArtifact.objects.filter(pk=entry["artifact"]).first()
        if artifact is None or artifact.sha256 != entry["sha256"]:
            raise FolhaError("Anexo diferente do conferido; refaça o rascunho.")
    email.state = FolhaEmail.State.APPROVED
    email.approved_by = user
    email.approved_at = timezone.now()
    email.save()
    _audit("folha.email.approved", email.organization, email, user=str(user.pk))
    return email


def django_transport(email: FolhaEmail, files: list[tuple[str, bytes]]) -> str:
    message = EmailMessage(
        subject=email.subject,
        body=email.body,
        from_email=email.sender,
        to=list(email.recipients),
    )
    for name, content in files:
        message.attach(name, content, "application/pdf")
    message.send(fail_silently=False)
    return (
        str(message.extra_headers.get("Message-ID", ""))
        or hashlib.sha256(f"{email.pk}".encode()).hexdigest()[:32]
    )


def send_email(email: FolhaEmail, *, transport: Transport | None = None) -> FolhaEmail:
    """Envia um aprovado. Falha após iniciar NÃO reenvia: fica ``failed`` para reconciliação."""

    with transaction.atomic():
        locked = FolhaEmail.objects.select_for_update().get(pk=email.pk)
        if locked.state != FolhaEmail.State.APPROVED:
            raise FolhaError("Só um e-mail aprovado pode ser enviado.")
        if not is_authorized(locked.organization, locked.company):
            raise FolhaError("Empresa fora da lista autorizada da Folha.")
        files: list[tuple[str, bytes]] = []
        for entry in locked.attachments:
            artifact = RpaArtifact.objects.get(pk=entry["artifact"])
            with artifact.file.open("rb") as handle:
                content = handle.read()
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise FolhaError("Anexo alterado depois da aprovação; refaça o rascunho.")
            files.append((entry["name"], content))
        locked.state = FolhaEmail.State.SENDING
        locked.save(update_fields=["state", "updated_at"])
    try:
        message_id = (transport or django_transport)(locked, files)
    except Exception as exc:
        locked.state = FolhaEmail.State.FAILED
        locked.error = f"Falha no envio ({type(exc).__name__}). Confira a caixa antes de repetir."
        locked.save(update_fields=["state", "error", "updated_at"])
        _audit("folha.email.failed", locked.organization, locked)
        return locked
    locked.state = FolhaEmail.State.SENT
    locked.sent_at = timezone.now()
    locked.message_id = message_id[:200]
    locked.error = ""
    locked.save()
    queue_mark(locked.cycle, locked.company, FolhaSheetMark.Stage.EMAIL)
    recompute(locked.cycle)
    _audit("folha.email.sent", locked.organization, locked)
    return locked


def reconcile_email(
    email: FolhaEmail, *, user: User, sent: bool, message_id: str, note: str
) -> FolhaEmail:
    """Admin decide um envio que falhou: confirma que saiu (com id) ou libera nova tentativa."""

    if email.state != FolhaEmail.State.FAILED:
        raise FolhaError("Só um envio que falhou pode ser reconciliado.")
    if not note.strip():
        raise FolhaError("A reconciliação exige justificativa.")
    if sent:
        if not message_id.strip():
            raise FolhaError("Informe o identificador da mensagem enviada.")
        email.state = FolhaEmail.State.SENT
        email.sent_at = timezone.now()
        email.message_id = message_id.strip()[:200]
        queue_mark(email.cycle, email.company, FolhaSheetMark.Stage.EMAIL)
    else:
        email.state = FolhaEmail.State.APPROVED
    email.reconciled_note = note[:300]
    email.error = ""
    email.save()
    recompute(email.cycle)
    _audit("folha.email.reconciled", email.organization, email, sent=sent, user=str(user.pk))
    return email


# --- planilha: gravação --------------------------------------------------------------------

STAGE_COLUMN = {"calc": "I", "reports": "M", "email": "N"}
STAGE_VALUE = {"calc": "CALCULANDO", "reports": "OK", "email": "OK"}
MAX_MARK_ATTEMPTS = 20


def flush_marks(
    organization: Organization, client: Any, *, now: datetime | None = None, force: bool = False
) -> dict[str, int]:
    """Grava as marcações pendentes. Nunca levanta: falha vira ``error`` com recuo até 6 h."""

    from . import sheets

    now = now or timezone.now()
    cfg = settings_for(organization)
    out = {"done": 0, "error": 0, "skipped": 0}
    if not cfg.sheets_enabled or not cfg.sheets_spreadsheet_id:
        return out
    states = [FolhaSheetMark.State.PENDING, FolhaSheetMark.State.ERROR]
    if force:
        states.append(FolhaSheetMark.State.FINAL_ERROR)
    for mark in FolhaSheetMark.objects.filter(organization=organization, state__in=states):
        if mark.next_try_at and mark.next_try_at > now and not force:
            out["skipped"] += 1
            continue
        try:
            tab = sheets.find_tab(
                client.titles(cfg.sheets_spreadsheet_id),
                mark.competence,
                template=cfg.sheets_tab_template,
            )
            rows = client.read(cfg.sheets_spreadsheet_id, f"'{tab}'!A:H")
            digits = re.sub(r"\D", "", mark.company.cnpj_masked)
            row = sheets.find_row(
                rows, code=mark.company_code, cnpj_digits=digits, name=mark.company.name
            )
            column = STAGE_COLUMN[mark.stage]
            cell = sheets.a1(tab, column, row)
            current = client.read(cfg.sheets_spreadsheet_id, cell)
            if current and current[0] and current[0][0].strip():
                # Célula já preenchida (talvez à mão): o sistema nunca passa por cima.
                mark.state = FolhaSheetMark.State.DONE
                mark.error = "Célula já preenchida; mantida."
            else:
                client.write(cfg.sheets_spreadsheet_id, cell, STAGE_VALUE[mark.stage])
                mark.state = FolhaSheetMark.State.DONE
                mark.error = ""
            mark.tab, mark.cell, mark.written_at = tab[:60], cell[-20:], now
            out["done"] += 1
        except Exception as exc:
            mark.attempts += 1
            mark.error = (
                str(exc)[:300] if isinstance(exc, sheets.SheetError) else type(exc).__name__
            )
            if mark.attempts >= MAX_MARK_ATTEMPTS:
                mark.state = FolhaSheetMark.State.FINAL_ERROR
            else:
                mark.state = FolhaSheetMark.State.ERROR
                delay = min(5 * 2 ** (mark.attempts - 1), 360)
                mark.next_try_at = now + timedelta(minutes=delay)
            out["error"] += 1
        mark.save()
    return out


# --- agenda --------------------------------------------------------------------------------


def due_competence(today: date, day: int, last: date | None) -> date | None:
    """Competência devida hoje: mês anterior ao do último vencimento do dia ``day``.

    Se ``today`` ainda não chegou ao dia, o vencimento mais recente foi o do mês passado (assim
    uma indisponibilidade da VM recupera os dias perdidos). Nunca repete a ``last``.
    """

    due = (
        today.replace(day=day)
        if today.day >= day
        else (today.replace(day=1) - timedelta(days=1)).replace(day=day)
    )
    competence = (due.replace(day=1) - timedelta(days=1)).replace(day=1)
    if last is not None and competence <= last:
        return None
    return competence


def run_schedule(organization: Organization, *, today: date | None = None) -> FolhaCycle | None:
    """Cria o RASCUNHO da competência devida. Não toca no Domínio e não confirma cálculo."""

    today = today or timezone.localdate()
    cfg = settings_for(organization)
    if not cfg.schedule_enabled or not cfg.schedule_codes or not cfg.schedule_items:
        return None
    competence = due_competence(today, cfg.schedule_day, cfg.last_scheduled_competence)
    if competence is None:
        return None
    authorized = {str(c) for c in cfg.authorized_codes}
    companies = list(
        ClientCompany.objects.filter(
            organization=organization,
            active=True,
            dominio_code__in=[c for c in cfg.schedule_codes if str(c) in authorized],
        )
    )
    if not companies:
        return None
    with transaction.atomic():
        try:
            cycle = create_cycle(
                organization=organization,
                user=None,
                competence=competence,
                companies=companies,
                items=list(cfg.schedule_items),
                draft=True,
                from_schedule=True,
                note="Agenda",
            )
        except FolhaError:
            # Já existe resultado dessa competência: a agenda segue em frente sem repetir.
            cycle = None
        cfg.last_scheduled_competence = competence
        cfg.save(update_fields=["last_scheduled_competence", "updated_at"])
    return cycle
