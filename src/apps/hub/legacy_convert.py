"""Turn the verbatim ``LegacyImportRecord`` rows of HubFedrizzi into native CICA models.

Every converter reads only the records of ONE organization, writes only inside it (the one
exception, regional holidays, is global by the owner's decision and written as inert drafts),
finds its native row by a natural key before creating (so a second run changes nothing) and
stamps ``LegacyImportRecord.mapped_to`` so the parity report can compare source and native.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify

from apps.accounts.models import User
from apps.fiscal_calendar.models import BusinessCalendarYear, NonBusinessDay
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAreaResponsible,
    CompanyPartner,
    LegacyImportRecord,
    NfseSync,
    ObligationDelivery,
)
from apps.organizations.models import Organization
from apps.triage.models import (
    ChecklistEntry,
    ChecklistExpectation,
    DocumentType,
    ExtractionRule,
    LearnedLink,
    SenderRule,
)

SYSTEM = "hubfedrizzi"
PAGE = 500

REGIME_VALUES = {
    "SIMPLES": ClientCompany.TaxRegime.SIMPLES.value,
    "PRESUMIDO": ClientCompany.TaxRegime.PRESUMIDO.value,
    "REAL": ClientCompany.TaxRegime.REAL.value,
    "MEI": ClientCompany.TaxRegime.MEI.value,
}
SPHERE = {
    "FEDERAL": ActivityTemplate.Sphere.FEDERAL,
    "ESTADUAL": ActivityTemplate.Sphere.STATE,
    "MUNICIPAL": ActivityTemplate.Sphere.MUNICIPAL,
}
CATEGORY = {
    "OBRIGACAO": ActivityTemplate.Category.ANCILLARY,
    "IMPOSTO": ActivityTemplate.Category.TAX,
    "IMPOSTO_VARIAVEL": ActivityTemplate.Category.VARIABLE_TAX,
}
PERIODICITY = {
    "MENSAL": ActivityTemplate.Periodicity.MONTHLY,
    "BIMESTRAL": ActivityTemplate.Periodicity.BIMONTHLY,
    "TRIMESTRAL": ActivityTemplate.Periodicity.QUARTERLY,
    "QUADRIMESTRAL": ActivityTemplate.Periodicity.FOUR_MONTHLY,
    "SEMESTRAL": ActivityTemplate.Periodicity.SEMIANNUAL,
    "ANUAL": ActivityTemplate.Periodicity.ANNUAL,
}
WEEKEND = {
    "ANTECIPA": ActivityTemplate.WeekendAdjustment.PREVIOUS,
    "POSTERGA": ActivityTemplate.WeekendAdjustment.NEXT,
    "NENHUM": ActivityTemplate.WeekendAdjustment.NONE,
}
PAYROLL_CODES = {"esocial", "fgts", "inss-e-irpf", "folha-de-pagamento", "holerite"}
PROCURACAO = {
    "ok": NfseSync.ProcuracaoStatus.OK,
    "ausente": NfseSync.ProcuracaoStatus.MISSING,
}
DELIVERY_STATUS = {
    "CONCLUIDO": ObligationDelivery.Status.DONE,
    "DISPENSADO": ObligationDelivery.Status.WAIVED,
}
DELIVERY_CHECKS = ("esocial_ok", "reinf_ok", "mit_ok", "recibo_dctfweb_ok", "guia_manual_ok")
RULE_MODES = {
    "dois_pontos": ExtractionRule.Mode.COLON,
    "linha_seguinte": ExtractionRule.Mode.NEXT_LINE,
    "contem": ExtractionRule.Mode.CONTAINS,
}
REQUIREMENT = {
    "obrigatorio": ChecklistExpectation.Requirement.EXPECTED,
    "opcional": ChecklistExpectation.Requirement.OPTIONAL,
    "dispensado": ChecklistExpectation.Requirement.WAIVED,
    "nao_aplicavel": ChecklistExpectation.Requirement.NOT_APPLICABLE,
}
HOLIDAY_SOURCE_URL = "https://hubfedrizzi.invalid/importacao-legada"


class Stats:
    """What the converters did, kept apart from the importer's report type."""

    def __init__(self) -> None:
        self.created: Counter[str] = Counter()
        self.reused: Counter[str] = Counter()
        self.skipped: dict[str, Counter[str]] = {}
        self.warnings: list[str] = []

    def skip(self, table: str, reason: str) -> None:
        self.skipped.setdefault(table, Counter())[reason] += 1


class _Marks:
    """Batches the ``mapped_to`` stamps so 60k rows do not mean 60k UPDATEs."""

    def __init__(self) -> None:
        self._pending: list[LegacyImportRecord] = []

    def set(self, record: LegacyImportRecord, value: str) -> None:
        if record.mapped_to == value:
            return
        record.mapped_to = value
        record.updated_at = timezone.now()
        self._pending.append(record)
        if len(self._pending) >= PAGE:
            self.flush()

    def flush(self) -> None:
        if self._pending:
            LegacyImportRecord.objects.bulk_update(self._pending, ["mapped_to", "updated_at"])
            self._pending = []


def _records(organization: Organization, table: str) -> Iterator[LegacyImportRecord]:
    """Keyset pages: production runs behind PgBouncer, where ``.iterator()`` loads everything."""

    last = None
    while True:
        queryset = LegacyImportRecord.objects.filter(
            organization=organization, source_system=SYSTEM, source_table=table
        ).order_by("pk")
        if last is not None:
            queryset = queryset.filter(pk__gt=last)
        batch = list(queryset[:PAGE])
        if not batch:
            return
        yield from batch
        last = batch[-1].pk


def mapped_ids(organization: Organization, table: str, prefix: str) -> dict[str, UUID]:
    """legacy pk -> native pk, read from ``mapped_to`` without loading any payload."""

    found: dict[str, UUID] = {}
    rows = LegacyImportRecord.objects.filter(
        organization=organization, source_system=SYSTEM, source_table=table, mapped_to__gt=""
    ).values_list("source_pk", "mapped_to")
    for source_pk, mapped in rows:
        if mapped.startswith(prefix):
            found[source_pk] = UUID(mapped[len(prefix) :])
    return found


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed.date()
    return parse_date(value[:10])


def _datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        day = parse_date(value[:10])
        if day is None:
            return None
        parsed = datetime(day.year, day.month, day.day)
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _slug(value: str, limit: int) -> str:
    return slugify(value)[:limit]


# ---- companies: fields the first importer did not carry -------------------------------------


def assign_responsible(
    organization: Organization, company: ClientCompany, name: str, stats: Stats
) -> None:
    """HubFedrizzi keeps one free-text owner per company; here it is the fiscal-area owner."""

    wanted = name.strip().casefold()
    if not wanted:
        return
    users = User.objects.filter(
        organization_memberships__organization=organization,
        organization_memberships__is_active=True,
    )
    match = None
    for user in users:
        if wanted in {user.email.casefold(), (user.full_name or "").strip().casefold()}:
            match = user
            break
    if match is None:
        stats.warnings.append(f"responsável '{name}' da empresa {company.pk}: sem usuário no CICA")
        stats.skip("core_empresa.responsavel", "sem usuário")
        return
    _, made = CompanyAreaResponsible.objects.get_or_create(
        organization=organization,
        company=company,
        area=ActivityTemplate.Area.FISCAL,
        defaults={"user": match},
    )
    stats.created["responsáveis por área"] += int(made)
    stats.reused["responsáveis por área"] += int(not made)


# ---- obligations ----------------------------------------------------------------------------


def _fill_blank(instance: Any, values: dict[str, Any]) -> bool:
    """Complete only what the office left empty; never overwrite its own corrections."""

    changed = False
    for key, value in values.items():
        current = getattr(instance, key)
        if value in ("", None, [], False):
            continue
        if current in ("", None, [], False):
            setattr(instance, key, value)
            changed = True
    return changed


def convert_obligations(organization: Organization, stats: Stats) -> None:
    regimes: dict[str, set[str]] = {}
    needs_ie: set[str] = set()
    regime_records: list[LegacyImportRecord] = []
    for record in _records(organization, "core_regimeobrigacao"):
        regime_records.append(record)
        data = record.payload
        key = str(data.get("obrigacao_id"))
        value = REGIME_VALUES.get(str(data.get("regime") or "").upper())
        if value:
            regimes.setdefault(key, set()).add(value)
        if data.get("exige_inscricao_estadual"):
            needs_ie.add(key)
    marks = _Marks()
    used_codes: set[str] = set(
        ActivityTemplate.objects.filter(organization=organization).values_list("code", flat=True)
    )
    for record in _records(organization, "core_obrigacao"):
        data = record.payload
        sigla = _text(data.get("sigla") or data.get("nome"), 40)
        code = _slug(sigla, 80)
        if not code:
            stats.skip("core_obrigacao", "sem sigla")
            continue
        weekday = str(data.get("ajuste_vencimento") or "").upper()
        periodicity = PERIODICITY.get(
            str(data.get("periodicidade") or "").upper(), ActivityTemplate.Periodicity.MONTHLY
        )
        day = _int(data.get("dia_vencimento"))
        offset = _int(data.get("meses_apos_competencia")) or 0
        values: dict[str, Any] = {
            "title": _text(data.get("nome") or sigla, 180),
            "area": (
                ActivityTemplate.Area.PAYROLL
                if code in PAYROLL_CODES
                else ActivityTemplate.Area.FISCAL
            ),
            # The activity engine only generates monthly work: a quarterly obligation stays
            # on demand until the engine learns the period, instead of repeating every month.
            "frequency": (
                ActivityTemplate.Frequency.MONTHLY
                if periodicity == ActivityTemplate.Periodicity.MONTHLY
                else ActivityTemplate.Frequency.AD_HOC
            ),
            "legal_due_day": day if day and 1 <= day <= 31 else None,
            "due_month_offset": min(max(offset, 0), 12),
            "abbreviation": sigla,
            "integration_code": _text(data.get("sigla_integracao"), 40),
            "sphere": SPHERE.get(str(data.get("esfera") or "").upper(), ""),
            "category": CATEGORY.get(str(data.get("categoria") or "").upper(), ""),
            "periodicity": periodicity,
            "weekend_adjustment": WEEKEND.get(weekday, ""),
            "state_code": _text(data.get("uf"), 2).upper(),
            "municipality": _text(data.get("municipio"), 120),
            "destination_root": _text(data.get("destino_raiz"), 500),
            "destination_subfolders": _text(data.get("destino_subpastas"), 500),
            "allows_manual_completion": bool(data.get("permite_baixa_manual")),
            "requires_human_review": bool(data.get("exige_conferencia_humana")),
            "applicable_regimes": sorted(regimes.get(record.source_pk, set())),
            "requires_state_registration": record.source_pk in needs_ie,
        }
        template = ActivityTemplate.objects.filter(
            organization=organization, code=code, version=1
        ).first()
        if template is None:
            if code in used_codes:
                code = f"{code}-{record.source_pk}"[:80]
            template = ActivityTemplate.objects.create(
                organization=organization,
                code=code,
                version=1,
                active=bool(data.get("ativa", True)),
                **values,
            )
            used_codes.add(code)
            stats.created["modelos de atividade"] += 1
        else:
            stats.reused["modelos de atividade"] += 1
            if _fill_blank(template, values):
                template.save()
        marks.set(record, f"hub.ActivityTemplate:{template.pk}")
    marks.flush()
    template_map = mapped_ids(organization, "core_obrigacao", "hub.ActivityTemplate:")
    for record in regime_records:
        target = template_map.get(str(record.payload.get("obrigacao_id")))
        if target is None:
            stats.skip("core_regimeobrigacao", "obrigação sem modelo nativo")
            continue
        marks.set(record, f"hub.ActivityTemplate:{target}")
    marks.flush()


def convert_assignments(organization: Organization, stats: Stats, *, hold: bool) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    templates = mapped_ids(organization, "core_obrigacao", "hub.ActivityTemplate:")
    existing = {
        (str(template_id), str(company_id)): pk
        for pk, template_id, company_id in ActivityTemplateAssignment.objects.filter(
            organization=organization
        ).values_list("pk", "template_id", "company_id")
    }
    marks = _Marks()
    pending: list[ActivityTemplateAssignment] = []
    for record in _records(organization, "core_empresaobrigacao"):
        data = record.payload
        company = companies.get(str(data.get("empresa_id")))
        template = templates.get(str(data.get("obrigacao_id")))
        if company is None or template is None:
            stats.skip(
                "core_empresaobrigacao",
                "empresa sem nativa" if company is None else "obrigação sem nativa",
            )
            continue
        key = (str(template), str(company))
        pk = existing.get(key)
        if pk is None:
            # Held assignments are created inactive so the activity engine does not start
            # generating work for them before the office decides to.
            made = ActivityTemplateAssignment(
                organization=organization,
                template_id=template,
                company_id=company,
                active=bool(data.get("ativa", True)) and not hold,
            )
            pending.append(made)
            existing[key] = made.pk
            pk = made.pk
            stats.created["vínculos empresa x obrigação"] += 1
        else:
            stats.reused["vínculos empresa x obrigação"] += 1
        marks.set(record, f"hub.ActivityTemplateAssignment:{pk}")
        if len(pending) >= PAGE:
            ActivityTemplateAssignment.objects.bulk_create(pending)
            pending = []
    if pending:
        ActivityTemplateAssignment.objects.bulk_create(pending)
    marks.flush()


def _informative(data: dict[str, Any]) -> bool:
    """A delivery row that records something somebody did; a bare PENDENTE is a placeholder."""

    return bool(
        str(data.get("status") or "PENDENTE").upper() != "PENDENTE"
        or any(data.get(name) for name in DELIVERY_CHECKS)
        or data.get("data_envio")
        or data.get("enviado_cliente_em")
        or str(data.get("email_cliente_status") or "NAO_ENVIADO").upper() != "NAO_ENVIADO"
        or data.get("observacao")
        or data.get("responsavel")
        or data.get("email_cliente_destinatario")
        or data.get("email_cliente_erro")
    )


def _email_status(raw: Any) -> str:
    value = str(raw or "").upper()
    if value in {"", "NAO_ENVIADO"}:
        return ObligationDelivery.EmailStatus.NOT_SENT
    if "ERRO" in value or "FALH" in value:
        return ObligationDelivery.EmailStatus.FAILED
    return ObligationDelivery.EmailStatus.SENT


def convert_deliveries(organization: Organization, stats: Stats) -> None:
    assignments = mapped_ids(
        organization, "core_empresaobrigacao", "hub.ActivityTemplateAssignment:"
    )
    existing = {
        (str(assignment_id), competence): pk
        for pk, assignment_id, competence in ObligationDelivery.objects.filter(
            organization=organization
        ).values_list("pk", "assignment_id", "competence")
    }
    marks = _Marks()
    pending: list[ObligationDelivery] = []
    for record in _records(organization, "workflow_envio"):
        data = record.payload
        if not _informative(data):
            stats.skip("workflow_envio", "pendente sem registro (o motor gera a atividade)")
            continue
        assignment = assignments.get(str(data.get("empresa_obrigacao_id")))
        year, month = _int(data.get("ano")), _int(data.get("mes"))
        if assignment is None:
            stats.skip("workflow_envio", "vínculo sem nativo")
            continue
        if not year or not month or not 1 <= month <= 12:
            stats.skip("workflow_envio", "competência inválida")
            continue
        competence = date(year, month, 1)
        key = (str(assignment), competence)
        pk = existing.get(key)
        if pk is None:
            made = ObligationDelivery(
                organization=organization,
                assignment_id=assignment,
                competence=competence,
                status=DELIVERY_STATUS.get(
                    str(data.get("status") or "").upper(), ObligationDelivery.Status.PENDING
                ),
                filed_on=_date(data.get("data_envio")),
                responsible_name=_text(data.get("responsavel"), 120),
                note=str(data.get("observacao") or ""),
                email_status=_email_status(data.get("email_cliente_status")),
                email_recipient=_text(data.get("email_cliente_destinatario"), 254),
                email_error=_text(data.get("email_cliente_erro"), 500),
                email_sent_by=_text(data.get("email_cliente_por"), 120),
                sent_to_client_at=_datetime(data.get("enviado_cliente_em")),
                checks={name: bool(data.get(name)) for name in DELIVERY_CHECKS},
            )
            pending.append(made)
            existing[key] = made.pk
            pk = made.pk
            stats.created["entregas"] += 1
        else:
            stats.reused["entregas"] += 1
        marks.set(record, f"hub.ObligationDelivery:{pk}")
        if len(pending) >= PAGE:
            ObligationDelivery.objects.bulk_create(pending)
            pending = []
    if pending:
        ObligationDelivery.objects.bulk_create(pending)
    marks.flush()


# ---- company registrations and partners -----------------------------------------------------


def convert_state_registrations(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    marks = _Marks()
    rows = sorted(
        _records(organization, "core_empresainscricaoestadual"),
        key=lambda r: (not r.payload.get("principal"), int(r.source_pk)),
    )
    for record in rows:
        data = record.payload
        company_pk = companies.get(str(data.get("empresa_id")))
        number = _text(data.get("numero"), 30)
        if company_pk is None or not number:
            stats.skip("core_empresainscricaoestadual", "sem empresa nativa ou sem número")
            continue
        company = ClientCompany.objects.get(pk=company_pk)
        if not company.state_registration:
            company.state_registration = number
            company.save(update_fields=["state_registration", "updated_at"])
            stats.created["inscrições estaduais preenchidas"] += 1
        if _digits(company.state_registration) == _digits(number):
            marks.set(record, f"hub.ClientCompany:{company_pk}")
        else:
            stats.skip(
                "core_empresainscricaoestadual", "inscrição adicional (empresa tem um só campo)"
            )
    marks.flush()


def _percent(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        return None


def convert_partners(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    existing = {
        (str(company_id), document or name.casefold()): pk
        for pk, company_id, document, name in CompanyPartner.objects.filter(
            organization=organization
        ).values_list("pk", "company_id", "document", "name")
    }
    marks = _Marks()
    pending: list[CompanyPartner] = []
    for record in _records(organization, "triagem_socioempresa"):
        data = record.payload
        company = companies.get(str(data.get("company_id")))
        name = _text(data.get("nome"), 180)
        if company is None or not name:
            stats.skip("triagem_socioempresa", "sem empresa nativa ou sem nome")
            continue
        document = _digits(data.get("cpf"))[:14]
        key = (str(company), document or name.casefold())
        pk = existing.get(key)
        if pk is None:
            made = CompanyPartner(
                organization=organization,
                company_id=company,
                name=name,
                document=document,
                share_percent=_percent(data.get("participacao")),
                source_updated_at=_datetime(data.get("updated_at")),
            )
            pending.append(made)
            existing[key] = made.pk
            pk = made.pk
            stats.created["sócios"] += 1
        else:
            stats.reused["sócios"] += 1
        marks.set(record, f"hub.CompanyPartner:{pk}")
        if len(pending) >= PAGE:
            CompanyPartner.objects.bulk_create(pending)
            pending = []
    if pending:
        CompanyPartner.objects.bulk_create(pending)
    marks.flush()


# ---- holidays (global by the owner's decision, inert until a platform reviewer approves) ----


def _holiday_scope(data: dict[str, Any]) -> str:
    where = str(data.get("abrangencia") or "").upper()
    uf = _text(data.get("uf"), 2).upper()
    if where == "ESTADUAL" and uf:
        return uf
    if where == "MUNICIPAL" and uf:
        return f"{uf}:{_slug(_text(data.get('municipio'), 120), 13)}"
    return "BR"


def convert_holidays(organization: Organization, stats: Stats) -> None:
    marks = _Marks()
    for record in _records(organization, "core_feriado"):
        data = record.payload
        day = _date(data.get("data"))
        if day is None:
            stats.skip("core_feriado", "data inválida")
            continue
        calendar, _ = BusinessCalendarYear.objects.get_or_create(
            scope=_holiday_scope(data),
            year=day.year,
            defaults={
                "legal_basis": "Importado do HubFedrizzi; sem base legal registrada",
                "source_url": HOLIDAY_SOURCE_URL,
            },
        )
        holiday, made = NonBusinessDay.objects.get_or_create(
            calendar=calendar, day=day, defaults={"name": _text(data.get("nome"), 120)}
        )
        stats.created["feriados (rascunho global)"] += int(made)
        stats.reused["feriados (rascunho global)"] += int(not made)
        marks.set(record, f"fiscal_calendar.NonBusinessDay:{holiday.pk}")
    marks.flush()


# ---- triage ---------------------------------------------------------------------------------


def _name_template(legacy: str, code: str) -> str:
    out = re.sub(r"\{empresa_codigo[^}]*\}", "{codigo}", legacy or "")
    out = out.replace("{tipo}", code.upper().replace("-", "_"))
    for token in ("{banco}", "{imobiliaria}", "{inquilino}", "{instituicao}"):
        out = out.replace(token, "{contraparte}")
    return out[:200] or "{codigo}_" + code.upper() + "_{periodo}"


def _folder_template(legacy: str) -> str:
    from django.core.exceptions import ValidationError

    from apps.triage.catalog import validate_folder_template

    out = (legacy or "").replace("{pasta_cliente}", "{dominio_code} - {company_name}")
    out = out.replace("{ano}/{mes}", "{period}").replace("/", "\\")
    try:
        return validate_folder_template(out)[:200]
    except ValidationError:
        return ""


def convert_document_types(organization: Organization, stats: Stats) -> None:
    marks = _Marks()
    for record in _records(organization, "triagem_documenttype"):
        data = record.payload
        code = _slug(_text(data.get("code"), 64), 64)
        if not code:
            stats.skip("triagem_documenttype", "sem código")
            continue
        document_type = DocumentType.objects.filter(organization=organization, code=code).first()
        if document_type is None:
            monthly = str(data.get("periodicity") or "mensal").lower() == "mensal"
            template = _name_template(str(data.get("name_template") or ""), code)
            document_type = DocumentType.objects.create(
                organization=organization,
                code=code,
                label=_text(data.get("label") or code, 160),
                name_template=template,
                folder_template=_folder_template(str(data.get("folder_template") or "")),
                # "eventual" types carry a year-only period label in HubFedrizzi.
                period_kind=(
                    DocumentType.PeriodKind.COMPETENCIA
                    if monthly
                    else DocumentType.PeriodKind.ANUAL
                ),
                counterparty_kind=(
                    DocumentType.CounterpartyKind.BANCO
                    if "{contraparte}" in template
                    else DocumentType.CounterpartyKind.NONE
                ),
                active=bool(data.get("active", True)),
                keywords=[str(k) for k in (data.get("keywords") or [])],
                expected_default=bool(data.get("required_by_default")),
            )
            stats.created["tipos de documento"] += 1
        else:
            stats.reused["tipos de documento"] += 1
        marks.set(record, f"triage.DocumentType:{document_type.pk}")
    marks.flush()


def convert_sender_rules(organization: Organization, stats: Stats) -> None:
    types = mapped_ids(organization, "triagem_documenttype", "triage.DocumentType:")
    marks = _Marks()
    best: dict[tuple[str, UUID], int] = {}
    rows: list[LegacyImportRecord] = []
    for record in _records(organization, "triagem_senderrule"):
        data = record.payload
        sender = _text(data.get("sender_pattern"), 254).casefold()
        type_pk = types.get(str(data.get("document_type_id")))
        if not sender or type_pk is None:
            stats.skip("triagem_senderrule", "sem remetente ou tipo nativo")
            continue
        confirmations = max(_int(data.get("confirmations")) or 0, 0)
        key = (sender, type_pk)
        best[key] = max(best.get(key, 0), confirmations)
        rows.append(record)
    natives: dict[tuple[str, UUID], str] = {}
    for (sender, native_type), confirmations in best.items():
        rule = SenderRule.objects.filter(
            organization=organization, sender=sender, document_type_id=native_type
        ).first()
        if rule is None:
            # The count survives as placeholder confirmations: CICA activates a sender at 3.
            rule = SenderRule.objects.create(
                organization=organization,
                sender=sender,
                document_type_id=native_type,
                confirmed_items=[f"hubfedrizzi:{n}" for n in range(min(confirmations, 30))],
            )
            stats.created["regras de remetente"] += 1
        else:
            stats.reused["regras de remetente"] += 1
        natives[(sender, native_type)] = str(rule.pk)
    for record in rows:
        data = record.payload
        key = (
            _text(data.get("sender_pattern"), 254).casefold(),
            types[str(data.get("document_type_id"))],
        )
        marks.set(record, f"triage.SenderRule:{natives[key]}")
    marks.flush()


def _learned_link(
    organization: Organization, kind: str, key: str, company_pk: UUID, stats: Stats
) -> LearnedLink:
    link, made = LearnedLink.objects.get_or_create(
        organization=organization, kind=kind, key=key, company_id=company_pk
    )
    stats.created["vínculos aprendidos"] += int(made)
    stats.reused["vínculos aprendidos"] += int(not made)
    return link


def convert_sender_companies(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    marks = _Marks()
    for record in _records(organization, "triagem_sendercompany"):
        data = record.payload
        sender = _text(data.get("sender"), 254).casefold()
        company = companies.get(str(data.get("company_id")))
        if not sender or company is None:
            stats.skip("triagem_sendercompany", "sem remetente ou empresa nativa")
            continue
        link = _learned_link(organization, LearnedLink.Kind.SENDER, sender, company, stats)
        marks.set(record, f"triage.LearnedLink:{link.pk}")
    marks.flush()


def convert_extraction_rules(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    rules = {r.source_pk: r for r in _records(organization, "triagem_extractionrule")}
    marks = _Marks()
    linked: set[str] = set()

    def rule_for(rule: LegacyImportRecord, company: UUID, value: str) -> str | None:
        mode = RULE_MODES.get(str(rule.payload.get("mode") or ""))
        if mode is None:
            return None
        anchor = "" if mode == ExtractionRule.Mode.CONTAINS else _text(rule.payload["anchor"], 120)
        value = _text(value, 200)
        native = ExtractionRule.objects.filter(
            organization=organization, company_id=company, mode=mode, anchor=anchor, value=value
        ).first()
        if native is None:
            native = ExtractionRule.objects.create(
                organization=organization,
                company_id=company,
                mode=mode,
                anchor=anchor,
                value=value,
                errors=min(_int(rule.payload.get("errors")) or 0, 3),
                active=bool(rule.payload.get("active", True)),
            )
            stats.created["regras de extração"] += 1
        else:
            stats.reused["regras de extração"] += 1
        return f"triage.ExtractionRule:{native.pk}"

    for alias in _records(organization, "triagem_rulealias"):
        rule = rules.get(str(alias.payload.get("rule_id")))
        company = companies.get(str(alias.payload.get("company_id")))
        value = _text(alias.payload.get("value_norm"), 254)
        if rule is None or company is None or not value:
            stats.skip("triagem_rulealias", "sem regra, empresa nativa ou valor")
            continue
        linked.add(rule.source_pk)
        if str(rule.payload.get("mode")) == "ofx_conta":
            link = _learned_link(organization, LearnedLink.Kind.ACCOUNT, value, company, stats)
            target: str | None = f"triage.LearnedLink:{link.pk}"
        else:
            target = rule_for(rule, company, value)
        if target is None:
            stats.skip("triagem_rulealias", "modo de regra sem equivalente")
            continue
        marks.set(alias, target)
        marks.set(rule, target)
    for rule in rules.values():
        if rule.source_pk in linked:
            continue
        data = rule.payload
        company = companies.get(str(data.get("company_id")))
        if company is None:
            stats.skip("triagem_extractionrule", "regra de layout sem empresa (sem alias)")
            continue
        target = rule_for(rule, company, str(data.get("anchor") or ""))
        if target is None:
            stats.skip("triagem_extractionrule", "modo de regra sem equivalente")
            continue
        marks.set(rule, target)
    marks.flush()


def convert_checklist(organization: Organization, stats: Stats) -> None:
    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    types = mapped_ids(organization, "triagem_documenttype", "triage.DocumentType:")
    marks = _Marks()
    for record in _records(organization, "triagem_checklistexpectation"):
        data = record.payload
        company = companies.get(str(data.get("company_id")))
        type_pk = types.get(str(data.get("document_type_id")))
        requirement = REQUIREMENT.get(str(data.get("requirement") or ""))
        if company is None or type_pk is None or requirement is None:
            stats.skip("triagem_checklistexpectation", "sem empresa, tipo ou exigência nativos")
            continue
        native, made = ChecklistExpectation.objects.get_or_create(
            organization=organization,
            company_id=company,
            document_type_id=type_pk,
            defaults={"requirement": requirement},
        )
        stats.created["expectativas do checklist"] += int(made)
        stats.reused["expectativas do checklist"] += int(not made)
        marks.set(record, f"triage.ChecklistExpectation:{native.pk}")
    for record in _records(organization, "triagem_checklistentry"):
        data = record.payload
        company = companies.get(str(data.get("company_id")))
        type_pk = types.get(str(data.get("document_type_id")))
        period = _text(data.get("period_label"), 16)
        if company is None or type_pk is None or not period:
            stats.skip("triagem_checklistentry", "sem empresa, tipo ou período nativos")
            continue
        entry, made = ChecklistEntry.objects.get_or_create(
            organization=organization,
            company_id=company,
            document_type_id=type_pk,
            period_label=period,
            defaults={"received_at": _datetime(data.get("received_at"))},
        )
        stats.created["entradas do checklist"] += int(made)
        stats.reused["entradas do checklist"] += int(not made)
        marks.set(record, f"triage.ChecklistEntry:{entry.pk}")
    marks.flush()


# ---- NFS-e synchronization state ------------------------------------------------------------


def convert_nfse_sync(organization: Organization, stats: Stats, *, enable: bool) -> None:
    """Keep each company's NSU checkpoint so CICA resumes where HubFedrizzi stopped.

    Synchronization stays OFF unless ``enable``: two systems polling the same ADN queue at
    once would race on the same NSU range, so the cutover turns it on, per company.
    """

    companies = mapped_ids(organization, "core_empresa", "hub.ClientCompany:")
    by_cnpj = {
        _digits(masked): pk
        for pk, masked in ClientCompany.objects.filter(
            organization=organization, pk__in=list(companies.values())
        ).values_list("pk", "cnpj_masked")
        if _digits(masked)
    }
    marks = _Marks()
    # Rows that kept their company link go first, so an orphan never wins over them.
    ordered = sorted(
        _records(organization, "nfse_sincronizacaonfse"),
        key=lambda r: r.payload.get("empresa_id") is None,
    )
    for record in ordered:
        data = record.payload
        # Some legacy rows lost their company link; the CNPJ they poll for still identifies it.
        company = companies.get(str(data.get("empresa_id"))) or by_cnpj.get(
            _digits(data.get("cnpj"))
        )
        if company is None:
            stats.skip("nfse_sincronizacaonfse", "empresa sem nativa")
            continue
        sync = NfseSync.objects.filter(organization=organization, company_id=company).first()
        if sync is None:
            active = enable and bool(data.get("ativo"))
            verified = _datetime(data.get("procuracao_verificada_em"))
            procuracao = PROCURACAO.get(
                str(data.get("procuracao") or ""), NfseSync.ProcuracaoStatus.UNKNOWN
            )
            sync = NfseSync.objects.create(
                organization=organization,
                company_id=company,
                enabled=active,
                status=NfseSync.Status.IDLE if active else NfseSync.Status.PAUSED,
                checkpoint_nsu=str(_int(data.get("ultimo_nsu")) or ""),
                credential_mode=(
                    NfseSync.CredentialMode.CERTIFICATE
                    if str(data.get("origem_credencial")) == "cliente"
                    else NfseSync.CredentialMode.PROCURACAO
                ),
                procuracao_status=procuracao,
                procuracao_checked_at=verified,
                procuracao_ok_at=(verified if procuracao == NfseSync.ProcuracaoStatus.OK else None),
                procuracao_notice=_text(data.get("ultimo_aviso"), 500),
                last_error_message=_text(data.get("ultimo_erro"), 500),
                last_run_at=_datetime(data.get("ultima_execucao")),
                last_success_at=(
                    _datetime(data.get("ultima_execucao"))
                    if str(data.get("status")) == "ok"
                    else None
                ),
                next_run_at=_datetime(data.get("proxima_consulta_em")) if active else None,
            )
            stats.created["sincronizações NFS-e"] += 1
        else:
            stats.reused["sincronizações NFS-e"] += 1
        marks.set(record, f"hub.NfseSync:{sync.pk}")
    marks.flush()


# ---- orchestration --------------------------------------------------------------------------

# table -> where it lands, for the parity report
PARITY_TARGETS: dict[str, str] = {
    "core_empresa": "hub.ClientCompany",
    "auth_user": "accounts.User + Membership (com --with-users)",
    "core_obrigacao": "hub.ActivityTemplate",
    "core_regimeobrigacao": "hub.ActivityTemplate (regimes)",
    "core_empresaobrigacao": "hub.ActivityTemplateAssignment",
    "workflow_envio": "hub.ObligationDelivery",
    "core_empresainscricaoestadual": "hub.ClientCompany.state_registration",
    "triagem_socioempresa": "hub.CompanyPartner",
    "core_feriado": "fiscal_calendar.NonBusinessDay",
    "triagem_documenttype": "triage.DocumentType",
    "triagem_senderrule": "triage.SenderRule",
    "triagem_sendercompany": "triage.LearnedLink (remetente)",
    "triagem_extractionrule": "triage.ExtractionRule / LearnedLink (conta)",
    "triagem_rulealias": "triage.ExtractionRule / LearnedLink (conta)",
    "triagem_checklistexpectation": "triage.ChecklistExpectation",
    "triagem_checklistentry": "triage.ChecklistEntry",
    "nfse_sincronizacaonfse": "hub.NfseSync",
}
# Why a table has no native home. Tables absent here are reported with a generic reason.
NO_NATIVE_HOME: dict[str, str] = {
    "triagem_triagecorrection": "correção de arquivo do worker antigo (sem item importado)",
    "triagem_triageitem": "itens de triagem dependem dos arquivos do MEDIA_ROOT",
    "triagem_triageevent": "log de eventos de itens não importados",
    "triagem_triageblob": "binários de triagem",
    "triagem_safetyscan": "varredura de segurança de arquivos",
    "core_sincronizacaodominio": "estado do sincronizador do HubFedrizzi",
    "nfse_certificado": "metadados de certificado; o .pfx e a senha não saem do servidor",
    "robo_nfse_notanfse": "vira NfseDocument no estágio --nfse-documents (relatório próprio)",
}

Converter = Callable[[], None]


def convert_all(
    organization: Organization,
    *,
    hold_generation: bool = False,
    enable_nfse_sync: bool = False,
) -> Stats:
    stats = Stats()
    steps: list[tuple[str, Converter]] = [
        ("obrigações", lambda: convert_obligations(organization, stats)),
        (
            "vínculos",
            lambda: convert_assignments(organization, stats, hold=hold_generation),
        ),
        ("entregas", lambda: convert_deliveries(organization, stats)),
        ("inscrições", lambda: convert_state_registrations(organization, stats)),
        ("sócios", lambda: convert_partners(organization, stats)),
        ("feriados", lambda: convert_holidays(organization, stats)),
        ("tipos", lambda: convert_document_types(organization, stats)),
        ("remetentes", lambda: convert_sender_rules(organization, stats)),
        ("vínculos de remetente", lambda: convert_sender_companies(organization, stats)),
        ("regras", lambda: convert_extraction_rules(organization, stats)),
        ("checklist", lambda: convert_checklist(organization, stats)),
        (
            "sincronização NFS-e",
            lambda: convert_nfse_sync(organization, stats, enable=enable_nfse_sync),
        ),
    ]
    for _name, step in steps:
        with transaction.atomic():
            step()
    return stats


def parity_lines(organization: Organization, stats: Stats) -> list[str]:
    """Source rows vs native rows, measured from the database, not from run counters."""

    out: list[str] = []
    records = LegacyImportRecord.objects.filter(organization=organization, source_system=SYSTEM)
    totals = dict(records.order_by().values_list("source_table").annotate(n=Count("pk")).order_by())
    mapped_totals = dict(
        records.exclude(mapped_to="")
        .order_by()
        .values_list("source_table")
        .annotate(n=Count("pk"))
        .order_by()
    )
    for table in sorted(totals):
        total = totals[table]
        target = PARITY_TARGETS.get(table)
        if target is None:
            why = NO_NATIVE_HOME.get(table, "sem modelo nativo ainda")
            out.append(
                f"paridade {table}: origem={total} nativo=0 ({why}; guardada em LegacyImportRecord)"
            )
            continue
        reasons = ", ".join(
            f"{n}x {why}" for why, n in sorted(stats.skipped.get(table, Counter()).items())
        )
        extra = f" | sem nativo: {reasons}" if reasons else ""
        out.append(
            f"paridade {table} → {target}: origem={total} "
            f"nativo={mapped_totals.get(table, 0)}{extra}"
        )
    for label, count in sorted(stats.created.items()):
        if count:
            out.append(f"nativo criado {label}: {count}")
    for label, count in sorted(stats.reused.items()):
        if count:
            out.append(f"nativo já existia {label}: {count}")
    return out
