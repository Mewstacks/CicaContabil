"""Regras das Admissões: revisão humana, travas de execução e conferência do resultado.

Nada é escrito por SQL no Domínio: o agente grava pela interface nativa e depois confere por
leitura. O servidor decide se um resultado vale: sem código do Domínio ou com divergência de
conferência o cadastro fica ``uncertain`` e NÃO se repete sozinho.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.encryption import blind_index
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

from .models import Admission, AdmissionsSettings

KIND = "admissions.cadastrar"
MAX_UPLOAD = 15 * 1024 * 1024
MAX_GROUP = 20
REQUIRED = (
    "name",
    "cpf",
    "birth_date",
    "admission_date",
    "role_code",
    "salary_cents",
    "salary_type",
    "category",
    "bond",
    "admission_type",
    "sex",
    "nationality",
    "service_code",
    "union_code",
    "agreement_code",
    "schedule_code",
)
REQUIRED_REAL_COMPANY = ("department_code", "cost_center_code")
LABELS = {
    "name": "Nome",
    "cpf": "CPF",
    "birth_date": "Nascimento",
    "admission_date": "Admissão",
    "role_code": "Cargo",
    "salary_cents": "Salário",
    "salary_type": "Tipo de salário",
    "category": "Categoria",
    "bond": "Vínculo",
    "admission_type": "Tipo de admissão",
    "sex": "Sexo",
    "nationality": "Nacionalidade",
    "service_code": "Serviço",
    "union_code": "Sindicato",
    "agreement_code": "Convenção",
    "schedule_code": "Jornada",
    "department_code": "Departamento",
    "cost_center_code": "Centro de custo",
}
ALLOWED_KEYS = (
    set(REQUIRED)
    | set(REQUIRED_REAL_COMPANY)
    | {
        "dependents",
        "transports",
        "has_children",
        "transport_voucher",
        "rg",
        "pis",
        "email",
        "phone",
    }
)


class AdmissionError(Exception):
    """Regra das Admissões recusou a operação; a mensagem é segura para a tela."""


def settings_for(organization: Organization) -> AdmissionsSettings:
    obj, _ = AdmissionsSettings.objects.get_or_create(organization=organization)
    return obj


def valid_cpf(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(d) * w for d, w in zip(digits[:size], range(size + 1, 1, -1), strict=True))
        check = (total * 10) % 11 % 10
        if int(digits[size]) != check:
            return False
    return True


def cpf_hash(value: str) -> str:
    return blind_index(re.sub(r"\D", "", value or ""), namespace="admission-cpf")


def _date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%d/%m/%Y").date()
    except ValueError:
        return None


def is_example(admission: Admission) -> bool:
    code = settings_for(admission.organization).example_code
    return bool(code) and admission.company.dominio_code == code


def validate_data(data: dict[str, Any], *, example: bool) -> list[str]:
    """Nomes dos campos com problema (nunca os valores: eles são dado pessoal)."""

    problems: list[str] = []
    required = REQUIRED if example else (*REQUIRED, *REQUIRED_REAL_COMPANY)
    for key in required:
        if data.get(key) in (None, "", []):
            problems.append(LABELS[key])
    if data.get("cpf") and not valid_cpf(str(data["cpf"])):
        problems.append("CPF")
    birth, admitted = _date(data.get("birth_date")), _date(data.get("admission_date"))
    for key, parsed in (("birth_date", birth), ("admission_date", admitted)):
        if data.get(key) and parsed is None:
            problems.append(LABELS[key])
    salary = data.get("salary_cents")
    if salary not in (None, "") and (
        not isinstance(salary, int) or isinstance(salary, bool) or salary <= 0
    ):
        problems.append("Salário")
    problems += _validate_group(data, "dependents", "has_children", admitted)
    problems += _validate_group(data, "transports", "transport_voucher", admitted)
    return sorted(set(problems))


def _validate_group(data: dict[str, Any], key: str, flag: str, admitted: date | None) -> list[str]:
    rows = data.get(key) or []
    label = "Dependentes" if key == "dependents" else "Vale-transporte"
    if not isinstance(rows, list) or len(rows) > MAX_GROUP:
        return [label]
    if (data.get(flag) == "SIM") != bool(rows):
        return [label]  # "SIM" exige linhas e linhas exigem "SIM"
    if key == "transports":
        return []
    seen: set[str] = set()
    own = re.sub(r"\D", "", str(data.get("cpf", "")))
    for row in rows:
        cpf = re.sub(r"\D", "", str(row.get("cpf", ""))) if isinstance(row, dict) else ""
        born = _date(row.get("birth_date")) if isinstance(row, dict) else None
        if not valid_cpf(cpf) or cpf in seen or cpf == own or born is None:
            return [label]
        if admitted and born > admitted:
            return [label]
        seen.add(cpf)
    return []


# --- ciclo da ficha ------------------------------------------------------------------------


def create(
    *,
    organization: Organization,
    user: User,
    company: ClientCompany,
    upload: bytes | None = None,
    original_name: str = "",
) -> Admission:
    if company.organization_id != organization.pk:
        raise AdmissionError("Empresa de outro escritório.")
    if upload is not None and len(upload) > MAX_UPLOAD:
        raise AdmissionError("O arquivo passa do limite de 15 MB.")
    admission = Admission(organization=organization, company=company, created_by=user)
    if upload:
        admission.sha256 = hashlib.sha256(upload).hexdigest()
        admission.original_name = original_name.replace("\\", "/").rsplit("/", 1)[-1][:200]
        admission.file.save("ficha.bin", ContentFile(upload), save=False)
    admission.save()
    return admission


def save_review(admission: Admission, *, user: User, data: dict[str, Any]) -> list[str]:
    if admission.state != Admission.State.REVIEW:
        raise AdmissionError("Só uma ficha em revisão pode ser editada.")
    clean = {k: v for k, v in data.items() if k in ALLOWED_KEYS}
    admission.data = clean
    admission.pending = validate_data(clean, example=is_example(admission))
    admission.cpf_hash = (
        cpf_hash(str(clean["cpf"])) if clean.get("cpf") and valid_cpf(str(clean["cpf"])) else ""
    )
    admission.reviewed_by, admission.reviewed_at = user, timezone.now()
    try:
        admission.save()
    except IntegrityError as exc:  # pragma: no cover - a restrição só vale fora de review
        raise AdmissionError("Este CPF já tem pedido vivo nesta empresa.") from exc
    return list(admission.pending)


def execution_allowed(admission: Admission) -> tuple[bool, str]:
    cfg = settings_for(admission.organization)
    if not cfg.execution_enabled:
        return False, "A execução está desligada neste escritório."
    if admission.company.dominio_code not in {str(c) for c in cfg.allowed_codes}:
        return False, "A empresa não está na lista autorizada."
    return True, ""


def execute(admission: Admission, *, user: User, example_confirmed: bool) -> Admission:
    ok, why = execution_allowed(admission)
    if not ok:
        raise AdmissionError(why)
    if admission.state != Admission.State.REVIEW:
        raise AdmissionError("Só uma ficha revisada pode ir à execução.")
    example = is_example(admission)
    if example and not example_confirmed:
        raise AdmissionError("A empresa de exemplo só executa com confirmação de teste.")
    pending = validate_data(admission.data, example=example)
    if pending:
        raise AdmissionError("Faltam campos: " + ", ".join(pending))
    if not admission.reviewed_by_id:
        raise AdmissionError("A ficha precisa de revisão humana.")
    duplicate = Admission.objects.filter(
        company=admission.company, cpf_hash=admission.cpf_hash, state__in=Admission.LIVE
    ).exclude(pk=admission.pk)
    if duplicate.exists():
        raise AdmissionError("Já existe pedido para este CPF nesta empresa.")
    with transaction.atomic():
        admission.state = Admission.State.QUEUED
        admission.example_confirmed = example and example_confirmed
        admission.pending = []
        try:
            admission.save()
        except IntegrityError as exc:
            raise AdmissionError("Já existe pedido para este CPF nesta empresa.") from exc
        job, _ = rpa.enqueue(
            organization=admission.organization,
            kind=KIND,
            idempotency_key=f"admission:{admission.pk}",
            payload={
                "admission_id": str(admission.pk),
                "company_code": admission.company.dominio_code,
            },
        )
        admission.job = job
        admission.save(update_fields=["job", "updated_at"])
        record_event(
            action="admissions.queued",
            organization=admission.organization,
            target=admission,
            metadata={"user": str(user.pk)},
        )
    return admission


def prepare_claim(job: RpaJob) -> dict[str, Any]:
    """Reconfere tudo no instante da entrega; a ficha viaja só na resposta (``transient_claim``)."""

    admission = (
        Admission.objects.select_related("company", "organization")
        .filter(pk=job.payload.get("admission_id"), organization=job.organization)
        .first()
    )
    if admission is None or admission.state != Admission.State.QUEUED:
        raise RpaError("trava", "A ficha não está mais na fila.")
    ok, why = execution_allowed(admission)
    if not ok:
        raise RpaError("trava", why)
    example = is_example(admission)
    if example and not admission.example_confirmed:
        raise RpaError("trava", "Falta a confirmação de teste da empresa de exemplo.")
    if validate_data(admission.data, example=example):
        raise RpaError("trava", "A ficha ficou incompleta.")
    admission.state = Admission.State.RUNNING
    admission.save(update_fields=["state", "updated_at"])
    return {"data": admission.data, "example_test": example}


def validate_payload(payload: dict[str, Any]) -> None:
    if not payload.get("admission_id") or not payload.get("company_code"):
        raise RpaError("validacao", "Carga sem ficha ou empresa.")


def validate_result(result: dict[str, Any]) -> None:
    if not str(result.get("domain_code", "")).isdigit() or int(result["domain_code"]) <= 0:
        raise RpaError("validacao", "Sem o código do empregado no Domínio.")
    checks = result.get("divergences", [])
    if not isinstance(checks, list) or any(not isinstance(c, str) or len(c) > 80 for c in checks):
        raise RpaError("validacao", "Divergências inválidas.")


def _admission(job: RpaJob) -> Admission:
    try:
        return Admission.objects.select_for_update().get(
            pk=job.payload.get("admission_id"), organization=job.organization
        )
    except (Admission.DoesNotExist, ValueError, TypeError) as exc:
        raise RpaError("validacao", "Ficha não encontrada.") from exc


def on_success(job: RpaJob) -> None:
    admission = _admission(job)
    admission.domain_code = str(job.result["domain_code"])[:30]
    divergences = job.result.get("divergences", [])
    if divergences:
        admission.state = Admission.State.UNCERTAIN
        admission.error = ("Conferência divergente: " + ", ".join(divergences))[:500]
    else:
        admission.state = Admission.State.DONE
        admission.error = f"Conferido em {int(job.result.get('checks_ok', 0))} verificações."
    admission.save()


def on_failure(job: RpaJob) -> None:
    admission = _admission(job)
    blocked = job.error_code == "bloqueado_por_trava"
    admission.state = Admission.State.REVIEW if blocked else Admission.State.FAILED
    admission.error = (job.error_detail or "Falhou sem gravar.")[:500]
    admission.save()


def on_uncertain(job: RpaJob) -> None:
    admission = _admission(job)
    admission.state = Admission.State.UNCERTAIN
    admission.error = "Parou depois de gravar; confira no Domínio antes de qualquer repetição."
    admission.save()


def resolve_uncertain(
    admission: Admission, *, user: User, registered: bool, domain_code: str, note: str
) -> Admission:
    if admission.state != Admission.State.UNCERTAIN:
        raise AdmissionError("A ficha não está incerta.")
    if not note.strip():
        raise AdmissionError("Informe o que foi conferido no Domínio.")
    with transaction.atomic():
        if registered:
            if not domain_code.isdigit():
                raise AdmissionError("Informe o código do empregado no Domínio.")
            admission.state, admission.domain_code = Admission.State.DONE, domain_code
        else:
            admission.state = Admission.State.FAILED
        admission.error = ""
        admission.save()
        if admission.job is not None and admission.job.state == RpaJob.State.UNCERTAIN:
            rpa.resolve_uncertain(
                admission.job.pk, organization=admission.organization, requeue=False, note=note
            )
        record_event(
            action="admissions.resolved",
            organization=admission.organization,
            target=admission,
            metadata={"registered": registered, "user": str(user.pk)},
        )
    return admission


def cancel(admission: Admission, *, user: User) -> Admission:
    if admission.state not in (Admission.State.REVIEW, Admission.State.QUEUED):
        raise AdmissionError("Só ficha em revisão ou na fila pode ser cancelada.")
    with transaction.atomic():
        if admission.job is not None and admission.job.state == RpaJob.State.QUEUED:
            rpa.cancel(admission.job.pk, organization=admission.organization)
        admission.state = Admission.State.CANCELLED
        admission.save()
        record_event(
            action="admissions.cancelled",
            organization=admission.organization,
            target=admission,
            metadata={"user": str(user.pk)},
        )
    return admission


def expire(*, now: datetime | None = None) -> int:
    """Retenção de 90 dias: apaga ficha, arquivo e CPF; mantém só o rastro mínimo."""

    now = now or timezone.now()
    count = 0
    stale = Admission.objects.filter(expires_at__lt=now).exclude(data_json="", cpf_hash="", file="")
    for admission in stale:
        with transaction.atomic():
            if admission.file:
                admission.file.delete(save=False)
            if admission.state == Admission.State.RUNNING:
                admission.state = Admission.State.UNCERTAIN
                admission.error = "Expirou com a ficha em execução; confira no Domínio."
            elif admission.state in (Admission.State.REVIEW, Admission.State.QUEUED):
                if admission.job is not None and admission.job.state == RpaJob.State.QUEUED:
                    rpa.cancel(admission.job.pk, organization=admission.organization)
                admission.state = Admission.State.EXPIRED
            admission.data_json = ""
            admission.cpf_hash = ""
            admission.pending = []
            admission.original_name = admission.sha256 = ""
            admission.save()
        count += 1
    return count
