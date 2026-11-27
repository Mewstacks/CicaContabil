"""Montagem dos dois escritórios (A e B) e do povoador genérico da matriz de isolamento.

O escritório B recebe uma linha de CADA modelo ligado a um tenant, com texto reconhecível
("ZZ-B-SEGREDO-n") em todo campo de texto livre. A prova da matriz é negativa: um usuário de A
nunca vê esse texto nem muda essas linhas.

Não há factory_boy no projeto, então o povoador percorre `_meta` e gera um valor por tipo de campo.
O que ele não consegue construir fica em `Tenant.failures` e o teste compara com uma lista
congelada: modelo novo sem construtor aparece como diferença, não como lacuna silenciosa.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import itertools
import json
import re
import time
import uuid
from collections import Counter
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from datetime import time as clock
from decimal import Decimal
from functools import cache
from typing import Any
from urllib.parse import urlencode, urlsplit

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache as django_cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import DatabaseError, connection, models, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import get_resolver
from django.urls.resolvers import RoutePattern, URLResolver
from django.utils import timezone

from apps.accounts.models import User
from apps.crosscheck.synthetic import make_cnpj
from apps.hub.models import (
    Certificate,
    ClientCompany,
    CompanyAccessGrant,
    Connector,
    DreMappingSet,
    NfseSync,
    OfficeProfile,
    ProductModule,
)
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.organizations.models import Membership, Organization
from apps.platform.models import PlatformConfiguration

MARK_A = "ZZ-A-PROPRIO"
MARK_B = "ZZ-B-SEGREDO"
PASSWORD = "senha-longa-de-teste-2026"

# Chaves de funcionalidade que ligam rotas inteiras. Sem elas o dono de B também leva 404 ou
# 503 e a rota ficaria sem controle positivo. Nenhuma abre acesso externo.
WORLD_SETTINGS: dict[str, Any] = {
    "CICA_REPORTING_URL": "http://reporting.invalid",
    "CICA_REPORTING_SHARED_SECRET": "segredo-so-de-teste",
    "RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED": True,
    "CONTRAPROVA_AGENT_ENABLED": True,
    "PROFITABILITY_SYNC_ENABLED": True,
}

# Apps cujas tabelas guardam dado de escritório ou de usuário de escritório.
TENANT_APPS = frozenset(
    {
        "accounts",
        "audit",
        "closing",
        "crosscheck",
        "delivery",
        "hub",
        "intelligence",
        "organizations",
        "platform",
        "privacy",
        "profitability",
        "triage",
    }
)

SKIP: Any = object()

# Modelos que o povoador não cria, porque mudariam o regime do escritório B em vez de só
# dar dado a ele (e invalidariam o controle positivo).
WORLD_SKIP_MODELS = frozenset(
    {
        # Cache assinado do controle central: com ele o dono de B cairia em "autorização expirada".
        "hub.ControlPlaneBinding",
        # Nasce em PROVISIONING por padrão: o escritório inteiro ficaria bloqueado.
        "platform.TenantLifecycle",
        # Papel de operador da plataforma e sessão de suporte são de staff, fora da matriz.
        "platform.PlatformAccess",
        "platform.SupportSession",
        # Singleton global semeado por migração, sem ligação com escritório.
        "platform.PlatformConfiguration",
        # Linha de produção (CONTAD): `clean()` exige fonte, empresa e escritório coerentes.
        "hub.AccountingImportReceipt",
        "hub.ReconciliationCompanyDiscovery",
        "hub.ReconciliationDiscoveredChartAccount",
        "hub.ReconciliationDiscoverySourceBlock",
    }
)

# Além da linha base, cada modelo ganha uma linha por valor de cada campo de opções (um campo
# por vez, no máximo MAX_VARIANTS): rotas que só enxergam a linha num estado (pronta, concluída,
# pendente) acham a linha certa sem receita por rota.
MAX_VARIANTS = 10


class CannotBuild(Exception):
    """O povoador não sabe montar uma linha deste modelo."""


# --------------------------------------------------------------------------------------------
# Escritórios
# --------------------------------------------------------------------------------------------


@dataclass
class Tenant:
    key: str
    mark: str
    office: Organization
    owner: User
    operator: User
    auditor: User
    memberships: dict[str, Membership]
    companies: list[ClientCompany] = field(default_factory=list)
    rows: dict[str, list[models.Model]] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    # Linhas das receitas: vão primeiro nos pareamentos, porque são as que as rotas abrem.
    preferred: set[tuple[str, Any]] = field(default_factory=set)

    def first(self, label: str) -> models.Model | None:
        rows = self.rows.get(label)
        return rows[0] if rows else None

    def add(self, row: models.Model) -> None:
        self.rows.setdefault(row._meta.label, []).append(row)

    @property
    def marker(self) -> str:
        return self.mark.lower()


def _masked(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def make_tenant(
    *, key: str, mark: str, slug: str, cnpj_root: str, mode: str = "certificate"
) -> Tenant:
    """Escritório com os módulos ofertados ligados, três papéis e três empresas."""

    office = Organization.objects.create(name=f"{mark}-ESCRITORIO", slug=slug)
    domain = f"{mark.lower()}.example"
    office_cnpj = make_cnpj(cnpj_root, "0001")
    profile = OfficeProfile.objects.create(
        organization=office,
        legal_name=f"{mark}-RAZAO-SOCIAL",
        cnpj=office_cnpj,
        nfse_collection_mode=mode,
    )
    users: dict[str, User] = {}
    memberships: dict[str, Membership] = {}
    for role, label in (
        (Membership.Role.OWNER, "dono"),
        (Membership.Role.OPERATOR, "operador"),
        (Membership.Role.AUDITOR, "auditor"),
    ):
        user = User.objects.create_user(
            email=f"{label}@{domain}",
            password=PASSWORD,
            full_name=f"{mark}-{label.upper()}",
        )
        users[label] = user
        memberships[str(role)] = Membership.objects.create(
            organization=office, user=user, role=role
        )
    tenant = Tenant(
        key=key,
        mark=mark,
        office=office,
        owner=users["dono"],
        operator=users["operador"],
        auditor=users["auditor"],
        memberships=memberships,
    )
    tenant.add(profile)
    for membership in memberships.values():
        tenant.add(membership)
    for code in OFFERED_MODULE_CODES:
        tenant.add(
            ProductModule.objects.create(
                organization=office, code=code, enabled=True, enabled_at=timezone.now()
            )
        )
    for index in range(1, 4):
        cnpj = make_cnpj(f"{int(cnpj_root) + index:08d}", "0001")
        tenant.companies.append(
            ClientCompany.objects.create(
                organization=office,
                name=f"{mark}-EMPRESA-{index}",
                cnpj_masked=_masked(cnpj),
                dominio_code=str(100 + index),
                contact_name=f"{mark}-CONTATO-{index}",
                contact_email=f"contato{index}@{domain}",
            )
        )
    for company in tenant.companies:
        tenant.add(company)
    # Operador e auditor enxergam as empresas por concessão, como num escritório real; sem ela
    # as páginas deles viriam vazias e a varredura não provaria nada para esses papéis.
    for role in (Membership.Role.OPERATOR, Membership.Role.AUDITOR):
        for company in tenant.companies:
            tenant.add(
                CompanyAccessGrant.objects.create(
                    organization=office,
                    membership=memberships[str(role)],
                    company=company,
                    modules=list(OFFERED_MODULE_CODES),
                    capabilities=["*"],
                )
            )
    return tenant


# --------------------------------------------------------------------------------------------
# Quais modelos pertencem a um tenant
# --------------------------------------------------------------------------------------------


def _all_models() -> list[type[models.Model]]:
    return sorted(
        (m for m in apps.get_models() if m._meta.app_label in TENANT_APPS),
        key=lambda m: m._meta.label,
    )


def _fk_targets(model: type[models.Model]) -> set[type[models.Model]]:
    return {
        f.related_model
        for f in model._meta.concrete_fields
        if f.is_relation and isinstance(f.related_model, type)
    }


@cache
def bound_models() -> list[type[models.Model]]:
    """Modelos que chegam a Organization ou a User por cadeia de chaves estrangeiras."""

    candidates = _all_models()
    bound: set[type[models.Model]] = set()
    changed = True
    while changed:
        changed = False
        for model in candidates:
            if model in bound or model in (Organization, User):
                continue
            targets = _fk_targets(model)
            if Organization in targets or User in targets or targets & bound:
                bound.add(model)
                changed = True
    return sorted(bound, key=lambda m: m._meta.label)


# --------------------------------------------------------------------------------------------
# Povoador genérico
# --------------------------------------------------------------------------------------------

_DATE_PART_HINTS = {"year": 2026, "ano": 2026, "month": 9, "mes": 9, "day": 1, "dia": 1}


class Factory:
    """Cria uma linha por modelo para um tenant, gerando valores por tipo de campo."""

    def __init__(self, tenant: Tenant, serial: Iterator[int], shared: dict[str, models.Model]):
        self.tenant = tenant
        self.serial = serial
        self.shared = shared
        self.bound = {m._meta.label for m in bound_models()}
        self._stack: list[str] = []
        self._pending: list[tuple[str, models.Model]] = []
        self._rich = True
        self._forced: tuple[str, dict[str, Any]] | None = None
        self.last_error = ""

    # -- API ------------------------------------------------------------------------------

    def ensure(self, model: type[models.Model]) -> models.Model:
        """Linha existente do tenant para este modelo, ou uma nova."""

        label = model._meta.label
        found = self._lookup(label)
        if found is not None:
            return found
        if label in WORLD_SKIP_MODELS:
            raise CannotBuild(f"{label} fica fora do mundo de teste")
        if label in self._stack:
            raise CannotBuild(f"dependência circular em {label}")
        if self._stack:
            return self._build(model)
        error: Exception | None = None
        for rich in (True, False):
            self._rich = rich
            mark = len(self._pending)
            try:
                # Um savepoint por tentativa: dependências criadas por uma tentativa que
                # falhou somem do banco junto com ela, em vez de virar linhas órfãs.
                with transaction.atomic():
                    row = self._build(model)
            except CannotBuild as exc:
                del self._pending[mark:]
                error = exc
                continue
            self._flush()
            return row
        raise CannotBuild(str(error))

    def populate(self) -> None:
        for model in bound_models():
            label = model._meta.label
            if label in WORLD_SKIP_MODELS or self.tenant.rows.get(label):
                continue
            try:
                self.ensure(model)
            except CannotBuild as exc:
                self.tenant.failures[label] = str(exc)
        for model in bound_models():
            self._populate_variants(model)

    def _populate_variants(self, model: type[models.Model]) -> None:
        base = self.tenant.first(model._meta.label)
        if base is None or model._meta.label in WORLD_SKIP_MODELS:
            return
        made = 0
        for f in model._meta.concrete_fields:
            if (
                not f.choices
                or f.primary_key
                or f.is_relation
                or isinstance(f, models.BooleanField)
            ):
                continue
            for value in _choice_values(f):
                if made >= MAX_VARIANTS:
                    return
                if value != getattr(base, f.name) and self._make_variant(model, f.name, value):
                    made += 1

    def _make_variant(self, model: type[models.Model], name: str, value: Any) -> bool:
        return self.add_row(model._meta.label, **{name: value}) is not None

    def add_row(self, label: str, **forced: Any) -> models.Model | None:
        """Uma linha a mais do modelo, com estes campos fixos; `None` se o banco recusar."""

        model = apps.get_model(label)
        self._forced = (label, forced)
        self.last_error = ""
        try:
            for rich in (True, False):
                self._rich = rich
                mark = len(self._pending)
                try:
                    with transaction.atomic():
                        row = self._build(model)
                except CannotBuild as exc:
                    del self._pending[mark:]
                    self.last_error = str(exc)
                    continue
                self._flush()
                return row
            return None
        finally:
            self._forced = None

    # -- registro -------------------------------------------------------------------------

    def _lookup(self, label: str) -> models.Model | None:
        store = self.tenant.rows.get(label) if label in self.bound else None
        if store:
            return store[0]
        if label not in self.bound and label in self.shared:
            return self.shared[label]
        for pending_label, row in self._pending:
            if pending_label == label:
                return row
        return None

    def _flush(self) -> None:
        for label, row in self._pending:
            if label in self.bound:
                self.tenant.rows.setdefault(label, []).append(row)
            else:
                self.shared[label] = row
        self._pending.clear()

    # -- construção -----------------------------------------------------------------------

    def _build(self, model: type[models.Model]) -> models.Model:
        label = model._meta.label
        self._stack.append(label)
        try:
            kwargs: dict[str, Any] = {}
            for f in model._meta.concrete_fields:
                value = self._value(model, f)
                if value is not SKIP:
                    kwargs[f.name] = value
            try:
                with transaction.atomic():
                    row = model(**kwargs)
                    row.save()
            except CannotBuild:
                raise
            except Exception as exc:
                raise CannotBuild(f"{label}: {type(exc).__name__}: {exc}"[:300]) from exc
        finally:
            self._stack.pop()
        self._pending.append((label, row))
        return row

    def _value(self, model: type[models.Model], f: Any) -> Any:
        if self._forced and self._forced[0] == model._meta.label and f.name in self._forced[1]:
            return self._forced[1][f.name]
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            return SKIP
        if getattr(f, "generated", False) or isinstance(f, models.AutoField):
            return SKIP
        if f.primary_key and (f.has_default() or not f.is_relation):
            return SKIP if f.has_default() else uuid.uuid4()
        if f.is_relation:
            return self._relation(model, f)
        return self._scalar(model, f)

    def _relation(self, model: type[models.Model], f: Any) -> Any:
        target = f.related_model
        optional = f.null or f.blank
        if target is model:
            if optional:
                return SKIP
            raise CannotBuild(f"{model._meta.label}.{f.name} aponta para o próprio modelo")
        if optional and not (self._rich and target in (ClientCompany, User)):
            return SKIP
        if target is Organization:
            return self.tenant.office
        if target is User:
            return self.tenant.owner
        if target is Membership:
            return self.tenant.memberships[str(Membership.Role.OWNER)]
        if target is ContentType:
            return ContentType.objects.get_for_model(Organization)
        if target is ClientCompany:
            return self.tenant.companies[0]
        if isinstance(target, str) or not isinstance(target, type):
            raise CannotBuild(f"alvo não resolvido em {model._meta.label}.{f.name}")
        return self.ensure(target)

    def _scalar(self, model: type[models.Model], f: Any) -> Any:
        if f.choices:
            if f.has_default():
                return SKIP
            return _first_choice(f)
        text = isinstance(f, models.CharField | models.TextField)
        if f.has_default() and not (text and self._rich and f.default == ""):
            return SKIP
        if f.null and not (text and self._rich):
            return SKIP
        if text:
            if f.blank and not self._rich:
                return SKIP
            return self._text(model, f)
        if isinstance(f, models.BooleanField):
            return False
        if isinstance(f, models.DecimalField):
            fits_one = f.max_digits - f.decimal_places >= 1
            return Decimal(1 if fits_one else "0.5").quantize(Decimal(1).scaleb(-f.decimal_places))
        if isinstance(f, models.FloatField):
            return 1.0
        if isinstance(f, models.IntegerField):
            return self._integer(f)
        if isinstance(f, models.DateTimeField):
            return timezone.now()
        if isinstance(f, models.DateField):
            return date(2026, 9, 1)
        if isinstance(f, models.TimeField):
            return clock(12, 0)
        if isinstance(f, models.DurationField):
            return timedelta(minutes=1)
        if isinstance(f, models.UUIDField):
            return uuid.uuid4()
        if isinstance(f, models.JSONField):
            # A field that may not be blank rejects `{}` (production models of the CONTAD line).
            return {} if f.blank else {"matrix": self.tenant.mark}
        if isinstance(f, models.BinaryField):
            return b"x"
        if isinstance(f, models.GenericIPAddressField):
            return "203.0.113.7"
        if isinstance(f, models.FileField):
            return self._file(f)
        raise CannotBuild(f"tipo de campo sem gerador: {model._meta.label}.{f.name} {type(f)}")

    def _integer(self, f: Any) -> int:
        if f.unique:
            return next(self.serial)
        for hint, value in _DATE_PART_HINTS.items():
            if f.name == hint or f.name.endswith(f"_{hint}") or f.name.startswith(f"{hint}_"):
                return value
        return 1

    def _text(self, model: type[models.Model], f: Any) -> str:
        n = next(self.serial)
        name = f.name.lower()
        limit = getattr(f, "max_length", None) or 10_000
        mark = self.tenant.mark
        if isinstance(f, models.EmailField) or "email" in name:
            value = f"{mark}-{n}@{mark.lower()}.example".lower()
        elif isinstance(f, models.URLField) or name.endswith("url"):
            value = f"https://{mark.lower()}.example/{n}"
        elif isinstance(f, models.SlugField) or name == "slug":
            value = f"{mark}-{n}".lower()
        elif "cnpj" in name and limit >= 14:
            value = make_cnpj(f"{20_000_000 + n:08d}", "0001")
        elif any(token in name for token in ("sha256", "digest", "hash")) and limit >= 64:
            value = hashlib.sha256(f"{mark}-{n}".encode()).hexdigest()
        elif name in {"competence", "competencia"} and limit >= 7:
            value = "2026-09"
        elif limit >= 44 and name in {"access_key", "chave", "chave_acesso", "key"}:
            value = f"{n:044d}"
        else:
            value = f"{mark}-{n}"
        if len(value) > limit:
            value = f"{mark[-1]}{n}"[:limit]
        return value

    def _file(self, f: Any) -> ContentFile[bytes]:
        n = next(self.serial)
        name = f.name.lower()
        mark = f"{self.tenant.mark}-{n}"
        if "pdf" in name:
            extension, body = "pdf", f"%PDF-1.4\n% {mark}\n%%EOF\n"
        elif "xml" in name:
            extension, body = "xml", f'<?xml version="1.0"?><nota><obs>{mark}</obs></nota>'
        elif "csv" in name:
            extension, body = "csv", f"campo\n{mark}\n"
        else:
            extension, body = "txt", f"{mark} conteudo do arquivo\n"
        return ContentFile(body.encode(), name=f"{mark}.{extension}")


def _choice_values(f: Any) -> list[Any]:
    values: list[Any] = []
    for value, label in f.choices:
        if isinstance(label, (list, tuple)):
            values.extend(inner for inner, _ in label)
        else:
            values.append(value)
    return values


def _first_choice(f: Any) -> Any:
    for value, label in f.choices:
        if isinstance(label, (list, tuple)):
            return label[0][0]
        return value
    raise CannotBuild(f"campo {f.name} sem opções")


def build_rows(tenant: Tenant, serial: Iterator[int], shared: dict[str, models.Model]) -> None:
    factory = Factory(tenant, serial, shared)
    factory.populate()
    apply_fixups(factory)


def new_serial() -> Iterator[int]:
    return itertools.count(1)


# --------------------------------------------------------------------------------------------
# Linhas coerentes para as rotas que só enxergam a linha num estado exato
# --------------------------------------------------------------------------------------------
# O povoador genérico dá a cada modelo uma linha plausível, mas várias rotas só abrem uma linha
# que obedece a um contrato entre tabelas (arquivo com hash conferido, PDF dentro do envelope do
# Serpro, lote de execução com as empresas contadas). Sem isso o dono de B também leva 404 e a
# rota fica sem controle positivo. Cada receita adiciona UMA linha ideal; nada é editado.


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def pdf_payload(tag: str) -> str:
    """Envelope do Serpro (DCTFWeb) com um PDF mínimo, como `extract_pdf` espera."""

    inner = json.dumps({"PDFByteArrayBase64": _b64(f"%PDF-1.7\n{tag}\n%%EOF")})
    return json.dumps({"dados": inner})


def das_payload(tag: str) -> str:
    inner = json.dumps({"docArrecadacaoPdfB64": _b64(f"%PDF-1.7\n{tag}\n%%EOF")})
    return json.dumps({"status": 200, "dados": inner})


def _file_bytes(row: models.Model, name: str) -> bytes:
    field_file = getattr(row, name)
    with field_file.open("rb") as handle:
        return bytes(handle.read())


def _recipe(factory: Factory, label: str, **forced: Any) -> models.Model | None:
    """Uma linha ideal; se o banco recusar, a falha entra em `failures` e o teste a congela."""

    row = factory.add_row(label, **forced)
    if row is None:
        factory.tenant.failures[f"receita {label}"] = factory.last_error
    else:
        factory.tenant.preferred.add((label, row.pk))
    return row


def apply_fixups(factory: Factory) -> None:
    tenant = factory.tenant
    mark = tenant.mark
    company = tenant.companies[0]

    def extra(label: str, **forced: Any) -> models.Model | None:
        return _recipe(factory, label, **forced)

    guide = extra("hub.FiscalGuide", status="issued", provider_payload=pdf_payload(mark))
    if guide is not None:
        extra(
            "hub.FiscalGuideAttemptEvent",
            guide=guide,
            status="issued",
            request_snapshot={},
            provider_payload=pdf_payload(mark),
        )
    extra(
        "hub.DctfWebDocument",
        kind="declaration",
        status="available",
        competence="10/2026",
        provider_payload=pdf_payload(mark),
    )
    extra(
        "hub.ParcelamentoOperation",
        kind="das",
        status="available",
        provider_payload=das_payload(mark),
    )

    document = tenant.first("hub.NfseDocument")
    if document is not None:
        package = extra(
            "hub.NfseExport",
            state="ready",
            document_count=1,
            snapshot={"documents": [{"document_id": str(document.pk)}]},
        )
        if package is not None:
            package.documents.add(document)  # type: ignore[attr-defined]

    run = extra("hub.DteRun", status="awaiting_approval", total_companies=1)
    if run is not None:
        extra("hub.DteRunItem", run=run, company=company)

    export = extra("hub.AccountingExport", state="ready")
    if export is not None:
        digest = hashlib.sha256(_file_bytes(export, "content")).hexdigest()
        type(export).objects.filter(pk=export.pk).update(content_hash=digest)

    rows = json.dumps(
        [{"nome": f"{mark}-LINHA-DA-CARTEIRA", "cnpj": make_cnpj("30123456", "0001")}]
    )
    for status in ("preview", "completed"):
        extra(
            "hub.ImportBatch",
            kind="companies",
            status=status,
            mapping={"roster": True, "headers": ["nome", "cnpj"]},
            encrypted_payload=rows,
            row_count=1,
            errors=[],
        )

    _triage_chain(factory)
    _agent_work(factory)
    _failed_collection(tenant)
    DreMappingSet.objects.filter(organization=tenant.office).update(is_active=True)


def _failed_collection(tenant: Tenant) -> None:
    """Coleta de NFS-e com falha e A1 válido: o que "repetir coletas" realmente repete."""

    certificate = tenant.first("hub.Certificate")
    sync = tenant.first("hub.NfseSync")
    if certificate is None or sync is None:
        return
    Certificate.objects.filter(pk=certificate.pk).update(
        valid_until=timezone.now() + timedelta(days=365), revoked_at=None
    )
    NfseSync.objects.filter(pk=sync.pk).update(
        certificate=certificate, enabled=True, status="error"
    )


def _agent_work(factory: Factory) -> None:
    """Trabalho já reivindicado pelo agente do escritório: é o que as rotas do agente abrem."""

    tenant = factory.tenant
    agent = tenant.first("intelligence.EdgeAgent")
    if agent is None:
        return
    claimed = str(agent.pk)
    Connector.objects.filter(organization=tenant.office, kind="dominio_agent").update(enabled=True)
    work = (
        ("triage.AgentFileJob", {"status": "claimed", "claimed_by": claimed}),
        ("triage.AgentFolderJob", {"status": "claimed", "claimed_by": claimed}),
        (
            "hub.ImportBatch",
            {"kind": "dominio_backup", "status": "processing", "mapping": {"claimed_by": claimed}},
        ),
        ("crosscheck.CrosscheckAgentJob", {"state": "claimed", "claimed_by": claimed}),
    )
    for label, forced in work:
        _recipe(factory, label, **forced)


def _triage_chain(factory: Factory) -> None:
    """Anexo liberado (prévia) e anexo arquivado na biblioteca (download), com hash conferido."""

    from apps.triage.models import TriageBlob, TriageSafetyScan

    tenant = factory.tenant
    mailbox = tenant.first("triage.Mailbox")
    document_type = tenant.first("triage.DocumentType")
    payload = f"{tenant.mark} conteudo do anexo\n".encode()
    digest = hashlib.sha256(payload).hexdigest()
    for status, archived in (("aguardando_revisao", False), ("arquivado", True)):
        item_id = uuid.uuid4()
        forced: dict[str, Any] = {
            "id": item_id,
            "status": status,
            "original_name": f"{tenant.mark}-{status}.pdf",
            "content_hash": digest,
            "company": tenant.companies[0],
            "mailbox": mailbox,
            "document_type": document_type,
        }
        if archived:
            path = f"private/triage/library/{tenant.office.id}/{item_id}/anexo.txt"
            forced |= {
                "destination_kind": "internal",
                "destination_path": path,
                "destination_hash": digest,
                "final_name": "anexo.txt",
            }
        item = _recipe(factory, "triage.TriageItem", **forced)
        if item is None:
            continue
        TriageBlob.objects.create(
            organization=tenant.office,
            triage_item=item,
            content=ContentFile(payload, name="anexo.bin"),
            content_type="text/plain",
        )
        TriageSafetyScan.objects.create(
            organization=tenant.office,
            triage_item=item,
            verdict="clean",
            format_verdict="valid",
            content_hash=digest,
        )
        if archived:
            default_storage.save(forced["destination_path"], ContentFile(payload))


# --------------------------------------------------------------------------------------------
# Mundo: A, B e quem é de quem
# --------------------------------------------------------------------------------------------


@dataclass
class World:
    a: Tenant
    b: Tenant
    shared: dict[str, models.Model]

    @property
    def b_ids(self) -> set[str]:
        """Todo identificador que pertence a B, em minúsculas, para caçar vazamento por id."""

        ids = {str(self.b.office.id)}
        for rows in self.b.rows.values():
            ids.update(str(row.pk).lower() for row in rows)
        ids.update(str(user.id) for user in (self.b.owner, self.b.operator, self.b.auditor))
        return {value.lower() for value in ids}


def build_world(*, mode: str = "certificate") -> World:
    # O Copiloto só aparece para escritório quando a plataforma o libera; sem isso as rotas dele
    # respondem 404 a qualquer um e a matriz não provaria nada sobre elas.
    PlatformConfiguration.objects.update_or_create(
        key="default", defaults={"copilot_available_for_offices": True}
    )
    serial = new_serial()
    shared: dict[str, models.Model] = {}
    a = make_tenant(key="A", mark=MARK_A, slug="escritorio-a", cnpj_root="11222300", mode=mode)
    b = make_tenant(key="B", mark=MARK_B, slug="escritorio-b", cnpj_root="44555600", mode=mode)
    for tenant in (a, b):
        build_rows(tenant, serial, shared)
        tenant.rows.setdefault(Organization._meta.label, []).append(tenant.office)
    return World(a=a, b=b, shared=shared)


def set_collection_mode(world: World, mode: str) -> None:
    OfficeProfile.objects.filter(organization__in=[world.a.office, world.b.office]).update(
        nfse_collection_mode=mode
    )


# --------------------------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------------------------

PARAM_RE = re.compile(r"<(?:(?P<converter>\w+):)?(?P<name>\w+)>")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
GHOST_UUID = "5ca1ab1e-0000-4000-8000-00000000d00d"


@dataclass(frozen=True)
class Param:
    name: str
    converter: str


@dataclass(frozen=True)
class Route:
    key: str
    name: str
    pattern: str
    params: tuple[Param, ...]
    callback: Any = field(compare=False, repr=False, hash=False)

    @property
    def uuid_params(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.params if p.converter == "uuid")

    @property
    def other_params(self) -> tuple[Param, ...]:
        return tuple(p for p in self.params if p.converter != "uuid")

    def url(self, values: Mapping[str, Any]) -> str:
        def fill(match: re.Match[str]) -> str:
            value = str(values[match["name"]])
            return f".{value}" if match["converter"] == "drf_format_suffix" else value

        return "/" + PARAM_RE.sub(fill, self.pattern)


def collect_routes() -> list[Route]:
    """Toda folha do resolver, com o namespace e o prefixo das inclusões."""

    found: list[tuple[str, str, Any]] = []

    def walk(patterns: Iterable[Any], prefix: str, namespace: str) -> None:
        for entry in patterns:
            if isinstance(entry, URLResolver):
                inner = f"{namespace}{entry.namespace}:" if entry.namespace else namespace
                walk(entry.url_patterns, prefix + str(entry.pattern), inner)
                continue
            if not isinstance(entry.pattern, RoutePattern):
                raise AssertionError(f"rota por regex sem tratamento: {entry.pattern}")
            found.append((f"{namespace}{entry.name or ''}", prefix + str(entry.pattern), entry))

    walk(get_resolver().url_patterns, "", "")
    routes: list[Route] = []
    for name, pattern, entry in found:
        params = tuple(
            Param(m["name"], m["converter"] or "str") for m in PARAM_RE.finditer(pattern)
        )
        key = name or pattern
        if any(p.converter == "drf_format_suffix" for p in params):
            key += "~fmt"
        routes.append(Route(key, name, pattern, params, entry.callback))
    keys = [route.key for route in routes]
    if len(keys) != len(set(keys)):
        raise AssertionError("chave de rota repetida")
    return routes


# --------------------------------------------------------------------------------------------
# Requisições observadas
# --------------------------------------------------------------------------------------------

WRITE_RE = re.compile(
    r'^\s*(INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM)\s+"?(\w+)"?', re.IGNORECASE
)
REDIRECTS = frozenset({301, 302, 303, 307, 308})
NONCE_RE = re.compile(r'nonce="[^"]*"')
CSRF_RE = re.compile(r'(name="csrfmiddlewaretoken" value=")[^"]*')
# Tabelas que uma tentativa recusada pode gravar sem que isso seja dado de negócio.
BENIGN_TABLES = frozenset({"django_session", "audit_auditevent"})
MAX_BODY = 3_000_000


@dataclass
class Observed:
    status: int
    location: str
    content_type: str
    body: str
    writes: tuple[tuple[str, str], ...]
    queries: int
    seconds: float
    changes: tuple[Change, ...] = ()

    @property
    def redirect(self) -> bool:
        return self.status in REDIRECTS

    @property
    def path(self) -> str:
        return urlsplit(self.location).path

    def normalized_location(self) -> str:
        return UUID_RE.sub("<uuid>", self.location)

    def digest(self) -> str:
        """Impressão do corpo sem o que muda a cada resposta (nonce, token CSRF e ids ecoados)."""

        body = NONCE_RE.sub('nonce=""', self.body)
        body = CSRF_RE.sub(r"\1", body)
        body = UUID_RE.sub("<uuid>", body)
        return hashlib.sha256(body.encode()).hexdigest()

    def unexpected_writes(self) -> list[str]:
        return [f"{verb} {table}" for verb, table in self.writes if table not in BENIGN_TABLES]

    def summary(self) -> str:
        if self.redirect:
            return f"{self.status} -> {self.location[:90]}"
        return f"{self.status} {self.content_type.split(';')[0]}"


def _writes(queries: Iterable[Mapping[str, str]]) -> tuple[tuple[str, str], ...]:
    seen: list[tuple[str, str]] = []
    for query in queries:
        match = WRITE_RE.match(query["sql"])
        if match is None:
            continue
        verb = match.group(1).split()[0].upper()
        pair = (verb, match.group(2))
        if pair not in seen:
            seen.append(pair)
    return tuple(seen)


def _read(response: Any) -> bytes:
    if getattr(response, "streaming", False):
        return b"".join(response.streaming_content)[:MAX_BODY]
    return bytes(response.content)[:MAX_BODY]


class Actor:
    """Uma pessoa logada num escritório, com seu próprio cliente de teste."""

    def __init__(
        self,
        label: str,
        tenant: Tenant,
        user: User,
        *,
        session_office: Organization | None = None,
    ) -> None:
        self.label = label
        self.tenant = tenant
        self.user = user
        self.client = Client(raise_request_exception=False)
        self.client.force_login(user)
        # `session_office` forja o escritório que a sessão e o cabeçalho da API dizem ser o atual.
        self.claimed = session_office or tenant.office
        session = self.client.session
        session["hub_organization_id"] = str(self.claimed.id)
        session.save()
        self._cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.sent = 0

    def _call(
        self, method: str, path: str, data: Mapping[str, Any] | None, headers: dict[str, str]
    ) -> Any:
        call = getattr(self.client, method.lower())
        if method in {"PUT", "PATCH", "DELETE"}:
            return call(
                path,
                data=json.dumps(dict(data or {})),
                content_type="application/json",
                headers=headers,
            )
        return call(path, data=dict(data or {}), headers=headers)

    def send(
        self,
        method: str,
        path: str,
        data: Mapping[str, Any] | None = None,
        *,
        watch: bool = False,
    ) -> Observed:
        """Uma requisição que nunca deixa rastro: roda dentro de um savepoint desfeito.

        Com `watch`, compara todas as linhas de tenant antes e depois (lento: só para quem
        gravou algo suspeito).
        """

        self.sent += 1
        django_cache.clear()
        self.client.cookies.pop("messages", None)
        if self._cookie:
            self.client.cookies[settings.SESSION_COOKIE_NAME] = self._cookie
        headers: dict[str, str] = {}
        if path.startswith("/api/v1/"):
            headers = {
                "X-Organization-ID": str(self.claimed.id),
                "Accept": "application/json",
            }
        started = time.perf_counter()
        before = snapshot() if watch else {}
        connection.queries_log.clear()
        with CaptureQueriesContext(connection) as captured, transaction.atomic():
            response = self._call(method, path, data, headers)
            raw = _read(response)
            try:
                after = snapshot() if watch else {}
            except DatabaseError:  # a view deixou a transação abortada (PostgreSQL)
                after = before
            transaction.set_rollback(True)
        elapsed = time.perf_counter() - started
        return Observed(
            status=response.status_code,
            location=str(response.headers.get("Location", "")),
            content_type=str(response.headers.get("Content-Type", "")),
            body=raw.decode("utf-8", errors="replace"),
            writes=_writes(captured.captured_queries),
            queries=len(captured.captured_queries),
            seconds=elapsed,
            changes=tuple(diff_snapshots(before, after)) if watch else (),
        )


class AgentActor(Actor):
    """O agente Windows de um escritório: pede por POST com o corpo assinado em HMAC."""

    def __init__(self, label: str, tenant: Tenant) -> None:
        self.label = label
        self.tenant = tenant
        self.user = tenant.owner
        self.client = Client(raise_request_exception=False)
        self.claimed = tenant.office
        self._cookie = ""
        self.sent = 0
        agent = tenant.first("intelligence.EdgeAgent")
        if agent is None:
            raise AssertionError("o escritório não tem agente")
        self.agent_id = str(agent.pk)
        self.secret = str(agent.shared_secret)  # type: ignore[attr-defined]

    def _call(
        self, method: str, path: str, data: Mapping[str, Any] | None, headers: dict[str, str]
    ) -> Any:
        body = json.dumps(dict(data or {})).encode()
        stamp = str(int(time.time()))
        signature = hmac.new(
            self.secret.encode(), stamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            path,
            data=body,
            content_type="application/json",
            secure=True,  # a produção recusa o agente fora de HTTPS (`_agent`)
            headers={
                "X-Hub-Agent-ID": self.agent_id,
                "X-Hub-Agent-Timestamp": stamp,
                "X-Hub-Agent-Signature": signature,
            },
        )


# --------------------------------------------------------------------------------------------
# Fotografia do banco, para provar que a linha de B não mudou
# --------------------------------------------------------------------------------------------


def snapshot_models() -> list[type[models.Model]]:
    return [*bound_models(), Organization, User]


def snapshot() -> dict[str, dict[Any, dict[str, Any]]]:
    shot: dict[str, dict[Any, dict[str, Any]]] = {}
    for model in snapshot_models():
        pk = model._meta.pk.attname
        shot[model._meta.label] = {row[pk]: row for row in model._base_manager.values()}
    return shot


@dataclass(frozen=True)
class Change:
    kind: str  # "mudou" | "apagada" | "nova"
    label: str
    pk: str
    organization_id: str
    detail: str

    def __str__(self) -> str:
        where = f" org={self.organization_id[:8]}" if self.organization_id else ""
        return f"{self.label} {self.pk[:8]} {self.kind}{where} {self.detail}".strip()


def diff_snapshots(
    before: Mapping[str, Mapping[Any, Mapping[str, Any]]],
    after: Mapping[str, Mapping[Any, Mapping[str, Any]]],
) -> list[Change]:
    out: list[Change] = []
    for label, old in before.items():
        new = after.get(label, {})
        for pk, row in old.items():
            owner = str(row.get("organization_id") or "")
            if pk not in new:
                out.append(Change("apagada", label, str(pk), owner, ""))
            elif new[pk] != row:
                changed = sorted(k for k in row if row[k] != new[pk].get(k))
                out.append(Change("mudou", label, str(pk), owner, ",".join(changed)))
        for pk, row in new.items():
            if pk not in old:
                out.append(
                    Change("nova", label, str(pk), str(row.get("organization_id") or ""), "")
                )
    return out


# --------------------------------------------------------------------------------------------
# Pareamento: qual linha de B serve a qual parâmetro de rota
# --------------------------------------------------------------------------------------------

# O nome do parâmetro (`document_id` -> "document") casa com a última palavra do nome do
# modelo (`NfseDocument`). O que não casa por nome entra aqui.
NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "candidate": ("intelligence.LearningCandidate",),
    "case": ("hub.ReviewCase",),
    "collaborator": ("profitability.Colaborador",),
    "event": ("hub.FiscalGuideAttemptEvent",),
    "input": ("crosscheck.CrosscheckInput",),
    "invitation": ("platform.Invitation",),
    "match": ("hub.ReconciliationMatch",),
    "membership": ("organizations.Membership",),
    "message": ("hub.DteMessage", "intelligence.Message"),
    "movement": ("hub.NormalizedMovement",),
    "operation": ("hub.ParcelamentoOperation",),
    "organization": ("organizations.Organization",),
    "resource": ("hub.AccountingBalanceSnapshot", "hub.CashScenario"),
    "source": (
        "hub.ReconciliationSourceFile",
        "hub.DominioBankEntry",
        "hub.AccountingEntry",
        "hub.BankStatementImport",
    ),
}

# Valores plausíveis para o que não é uuid.
STATIC_VALUES: dict[str, tuple[str, ...]] = {
    "agreement": ("1",),
    "capability": ("complete", "companies"),
    "competence": ("2026-09",),
    "decision": ("approve", "reject"),
    "document": ("termos-de-uso",),
    "export_format": ("pdf", "xlsx"),
    "fmt": ("xlsx", "csv"),
    "format": ("json",),
    "provider": ("gmail_api", "ms365_graph"),
    "resource": ("dre", "cash"),
    "token": ("token-inexistente-de-teste",),
    "tour_id": ("welcome", "nfse"),
    "uidb64": ("MQ",),
}
ROWS_PER_MODEL = 40
MAX_PAIRS_PER_VARIANT = 2
MAX_STATIC_COMBOS = 4


def _words(model: type[models.Model]) -> list[str]:
    return re.findall(r"[A-Z][a-z0-9]*", model.__name__)


def compatible_models(route: Route, param: str, tenant: Tenant) -> list[type[models.Model]]:
    """Modelos de `tenant` que podem ser a coisa que o parâmetro nomeia."""

    labels = sorted(label for label, rows in tenant.rows.items() if rows)
    registered = {label: apps.get_model(label) for label in labels}
    if param == "pk":
        queryset = getattr(getattr(route.callback, "cls", None), "queryset", None)
        model = getattr(queryset, "model", None)
        return [model] if model is not None and model._meta.label in registered else []
    stem = param.removesuffix("_id")
    token = stem.split("_")[-1].capitalize()
    exact = [m for m in registered.values() if _words(m)[-1] == token]
    loose = [m for m in registered.values() if token in _words(m)]
    chosen = list(exact or loose)
    for label in NAME_ALIASES.get(stem, ()):
        model = registered.get(label)
        if model is not None and model not in chosen:
            chosen.append(model)
    return sorted(chosen, key=lambda m: m._meta.label)


def related_row(row: models.Model, wanted: Iterable[type[models.Model]]) -> models.Model | None:
    """Sobe pelas chaves estrangeiras de `row` até achar uma linha de um dos modelos."""

    targets = tuple(wanted)
    seen = {(row._meta.label, row.pk)}
    frontier = [row]
    for _ in range(3):
        following: list[models.Model] = []
        for current in frontier:
            for f in current._meta.concrete_fields:
                if not (f.is_relation and (f.many_to_one or f.one_to_one)):
                    continue
                try:
                    target = getattr(current, f.name)
                except ObjectDoesNotExist:
                    continue
                if target is None or (target._meta.label, target.pk) in seen:
                    continue
                if isinstance(target, targets):
                    return target
                seen.add((target._meta.label, target.pk))
                following.append(target)
        frontier = following
    return None


AGENT_PREFIX = "agent-v2-"

# Corpo mínimo que cada rota do agente aceita sem recusar antes de olhar o id (o agente fala JSON).
AGENT_PAYLOADS: dict[str, tuple[dict[str, Any], ...]] = {
    "agent-v2-crosscheck-batch": ({"sequence": 0, "rows": []},),
    "agent-v2-crosscheck-complete": ({"row_count": 0, "pages": 0},),
    "agent-v2-crosscheck-failure": ({"error_code": "odbc_error"},),
    "agent-v2-profitability-run-batch": ({"sequence": 0, "rows": []},),
    "agent-v2-profitability-run-complete": ({"row_count": 0},),
    "agent-v2-profitability-run-failure": ({"code": "agent_failure"},),
    "agent-v2-file-complete": ({"success": False, "detail": "falha de teste"},),
    "agent-v2-folder-complete": ({"success": False, "detail": "falha de teste"},),
}


def agent_payloads(route: Route) -> list[str]:
    extras = AGENT_PAYLOADS.get(route.key, ())
    return [json.dumps(payload, sort_keys=True) for payload in ({}, *extras)]


@dataclass(frozen=True)
class Variant:
    method: str
    payload: str = ""  # JSON do corpo (POST) ou da consulta (GET)

    @property
    def data(self) -> dict[str, Any]:
        return dict(json.loads(self.payload)) if self.payload else {}

    @property
    def label(self) -> str:
        data = self.data
        if not data:
            return self.method
        if list(data) == ["action"]:
            return f"{self.method}[action={data['action']}]"
        return f"{self.method}[{self.payload}]"


@dataclass(frozen=True)
class Probe:
    """Um pedido pronto: o que se manda e para onde."""

    method: str
    url: str
    payload: str = ""

    @property
    def data(self) -> dict[str, Any]:
        return dict(json.loads(self.payload)) if self.payload else {}


def discovered_actions(callback: Any) -> list[str]:
    """Valores de `action` que a view compara, lidos do código dela."""

    target = getattr(callback, "view_class", None) or getattr(callback, "cls", None)
    target = target or inspect.unwrap(callback)
    try:
        source = inspect.getsource(target)
    except (OSError, TypeError):
        return []
    found = set(re.findall(r'\baction\s*(?:==|!=)\s*"([\w:-]+)"', source))
    for group in re.findall(r"\baction\s+(?:not\s+)?in\s*[\{\(\[]([^\}\)\]]+)[\}\)\]]", source):
        found.update(re.findall(r'"([\w:-]+)"', group))
    return sorted(found)


def _placeholder(tenant: Tenant, text: str) -> str:
    """`@company` e `@office` viram o id do escritório de quem faz o pedido."""

    if text == "@company":
        return str(tenant.companies[0].pk)
    if text == "@office":
        return str(tenant.office.id)
    return text


def _action(name: str) -> str:
    return json.dumps({"action": name})


def variants_for(route: Route) -> list[Variant]:
    if route.key.startswith(AGENT_PREFIX):
        return [Variant("POST", payload) for payload in agent_payloads(route)]
    out = [Variant("GET"), Variant("POST")]
    out.extend(Variant("POST", _action(action)) for action in discovered_actions(route.callback))
    if route.pattern.startswith("api/v1/"):
        out.extend(Variant(method, '{"name": "ZZ-A-TENTATIVA"}') for method in ("PATCH", "PUT"))
        out.append(Variant("DELETE"))
    return out


@dataclass(frozen=True)
class BodySpec:
    """Rota cujo id de linha vem no corpo ou na consulta, não no caminho."""

    route: str
    field: str
    labels: tuple[str, ...]
    method: str = "POST"
    as_list: bool = False
    fixed: tuple[tuple[str, str], ...] = ()

    @property
    def key(self) -> str:
        return f"{self.route}#{self.field}@{self.method}"


def body_variants_for(route: Route, spec: BodySpec) -> list[Variant]:
    if route.key.startswith(AGENT_PREFIX):
        return [Variant("POST", payload) for payload in agent_payloads(route)]
    if spec.method == "GET":
        return [Variant("GET")]
    return [
        Variant("POST"),
        *(Variant("POST", _action(action)) for action in discovered_actions(route.callback)),
    ]


_COMPANY = ("hub.ClientCompany",)
_BULK = (("reason", "motivo de teste"), ("internal_due_on", "2026-12-01"))
_REASON = (("reason", "motivo de teste"),)
_COMPETENCE = (("competence", "09/2026"),)
_EXPORT_PERIOD = (
    ("company_id", "@company"),
    ("period_start", "2026-09-01"),
    ("period_end", "2026-09-30"),
    ("reexport_reason", "motivo de teste"),
)

# Onde o id de uma linha viaja no corpo ou na consulta (o IDOR clássico): cada um é pedido pelo
# dono de B (controle) e pelo dono de A, que põe o id de B no campo.
BODY_SPECS: tuple[BodySpec, ...] = (
    BodySpec("hub:switch-office", "organization_id", ("organizations.Organization",)),
    BodySpec(
        "hub:activity-bulk-action",
        "activity_ids",
        ("hub.OperationalActivity",),
        as_list=True,
        fixed=_BULK,
    ),
    BodySpec("hub:activity-models", "template_id", ("hub.ActivityTemplate",)),
    BodySpec("hub:activity-models", "assignment_id", ("hub.ActivityTemplateAssignment",)),
    BodySpec("hub:activities", "company", _COMPANY, method="GET"),
    BodySpec("hub:nfse-center", "company", _COMPANY, method="GET"),
    BodySpec("hub:nfse-center", "company_id", _COMPANY, method="GET"),
    BodySpec("hub:nfse-queue-retry", "company_id", _COMPANY),
    BodySpec("hub:dctfweb-consult", "company", _COMPANY, method="GET", fixed=_COMPETENCE),
    BodySpec("hub:dctfweb-consult", "company", _COMPANY, fixed=_COMPETENCE),
    BodySpec("hub:parcelamentos", "company", _COMPANY, method="GET"),
    BodySpec("hub:dte-center", "company", _COMPANY, method="GET"),
    BodySpec(
        "hub:reconciliation-movement-bulk-action",
        "movement_ids",
        ("hub.NormalizedMovement",),
        as_list=True,
        fixed=_REASON,
    ),
    BodySpec("hub:reconciliation-export-create", "company_id", _COMPANY),
    BodySpec(
        "hub:reconciliation-export-create",
        "reexport_of",
        ("hub.AccountingExport",),
        fixed=_EXPORT_PERIOD,
    ),
    BodySpec("hub:reconciliation-configuration", "period_id", ("hub.AccountingPeriod",)),
    BodySpec("hub:reconciliation-configuration", "rule_id", ("hub.ReconciliationRule",)),
    BodySpec("hub:confirm-reconciliation", "dominio_entry_id", ("hub.DominioBankEntry",)),
    BodySpec("hub:confirm-reconciliation", "source_entry", ("hub.AccountingEntry",)),
    BodySpec("hub:reconciliation-movement", "entry_id", ("hub.AccountingEntry",)),
    BodySpec("hub:reconciliation-movement", "reconciliation_id", ("hub.MovementReconciliation",)),
    BodySpec("hub:setup", "batch_id", ("hub.ImportBatch",), method="GET"),
    BodySpec("hub:setup", "source_id", ("hub.DataSource",), method="GET"),
    BodySpec("agent-v2-sync", "batch_id", ("hub.ImportBatch",)),
)


@dataclass
class Combo:
    values: dict[str, str]
    rows: dict[str, models.Model]
    label: str


def static_combos(route: Route) -> list[dict[str, str]]:
    names = [p.name for p in route.other_params]
    pools = [STATIC_VALUES.get(name, ("x",)) for name in names]
    combos = [dict(zip(names, values, strict=True)) for values in itertools.product(*pools)]
    return combos[:MAX_STATIC_COMBOS]


def combos_for(route: Route, tenant: Tenant) -> list[Combo]:
    """Uma tupla de ids de `tenant` por linha candidata do último parâmetro uuid."""

    params = route.uuid_params
    pools = {p: compatible_models(route, p, tenant) for p in params}
    anchor = params[-1]
    out: list[Combo] = []
    for model in pools[anchor]:
        label = model._meta.label
        rows = sorted(
            tenant.rows.get(label, []), key=lambda row: (label, row.pk) not in tenant.preferred
        )
        for row in rows[:ROWS_PER_MODEL]:
            chosen: dict[str, models.Model] = {anchor: row}
            for p in params[:-1]:
                parent = related_row(row, pools[p]) or first_row(pools[p], tenant)
                if parent is not None:
                    chosen[p] = parent
            if len(chosen) != len(params):
                continue
            for extra in static_combos(route):
                values = {name: str(chosen[name].pk) for name in params} | extra
                out.append(Combo(values, chosen, f"{model._meta.label}"))
    return out


def first_row(pool: Iterable[type[models.Model]], tenant: Tenant) -> models.Model | None:
    for model in pool:
        rows = tenant.rows.get(model._meta.label)
        if rows:
            return rows[0]
    return None


# --------------------------------------------------------------------------------------------
# Veredito
# --------------------------------------------------------------------------------------------

BENIGN_LABELS = frozenset({"audit.AuditEvent"})
# Pedaço do marcador, não o marcador inteiro: se a página ecoar a consulta, o eco não conta como
# vazamento, mas uma linha de B encontrada pela busca (que contém o marcador inteiro) conta.
POISON_TEXT = MARK_B.rsplit("-", 1)[-1]


def leaks_in(world: World, body: str, *, exclude: Iterable[str] = ()) -> list[str]:
    """O que do mundo de B aparece num texto: marcador de B e ids de linhas de B."""

    low = body.lower()
    hits: list[str] = []
    if world.b.marker in low:
        hits.append(f"marcador {world.b.mark}")
    ids = (set(UUID_RE.findall(low)) & world.b_ids) - {value.lower() for value in exclude}
    if ids:
        hits.append("id(s) de B no corpo: " + ", ".join(sorted(ids)[:3]))
    return hits


def shows_rows(world: World, body: str) -> bool:
    """A página mostra linha ou empresa de B, e não só o nome do escritório no cabeçalho."""

    low = body.lower()
    return bool(re.search(rf"{re.escape(world.b.marker)}-(\d|empresa)", low))


def marks_in(marker: str, body: str) -> frozenset[str]:
    """Quais linhas do escritório (marcador com número, ou empresa) a página mostra."""

    return frozenset(re.findall(rf"{re.escape(marker)}-(?:\d+|empresa-\d+)", body.lower()))


def pairing_gap(marker: str, control: Observed, ghost: Observed) -> str:
    """Vazio quando o controle prova que a rota enxerga a linha de B; senão, o motivo.

    Pareado = a resposta de B à linha real difere da resposta a um id que não existe: status,
    destino do redirect, linhas do escritório no corpo ou tabelas gravadas. Mais rígido que "não
    deu 404/405/400/500": um 302 para a lista, igual ao do id inexistente, não prova nada. Mais
    largo também: um 400 de formulário vazio, onde o inexistente dá 404, prova que a busca
    achou a linha. O corpo inteiro só entra como último recurso (ver `Runner.gap`).
    """

    if control.redirect and "/entrar/" in control.location:
        return "login"
    same = (
        control.status == ghost.status
        and control.normalized_location() == ghost.normalized_location()
        and marks_in(marker, control.body) == marks_in(marker, ghost.body)
        and set(control.writes) == set(ghost.writes)
    )
    return f"igual ao inexistente ({control.summary()})" if same else ""


def judge(
    world: World,
    seen: Observed,
    ghost: Observed,
    control: Observed,
    pks: Iterable[str],
) -> list[str]:
    """Problemas na resposta que A recebeu ao tocar numa linha de B.

    O que A recebe tem de ser o que um id inexistente recebe: 403/404, ou o mesmo redirect, ou
    o mesmo status (o corpo é conferido à parte, em `Runner.body_differs`).
    """

    ids = {pk.lower() for pk in pks}
    problems = [f"corpo: {hit}" for hit in leaks_in(world, seen.body, exclude=ids)]
    if seen.status in {403, 404}:
        return problems
    if seen.redirect:
        as_ghost = (
            seen.status == ghost.status
            and seen.normalized_location() == ghost.normalized_location()
        )
        names_resource = any(pk in seen.location.lower() for pk in ids) or (
            control.redirect and seen.path == control.path and seen.path != ghost.path
        )
        if names_resource and not as_ghost:
            problems.append(f"redireciona para a página do recurso: {seen.location[:120]}")
    elif seen.status != ghost.status:
        problems.append(f"{seen.status} onde um id inexistente dá {ghost.status}")
    return problems


# --------------------------------------------------------------------------------------------
# Resultados
# --------------------------------------------------------------------------------------------


@dataclass
class PairResult:
    route: str
    variant: str
    scenario: str
    label: str
    url: str
    control: str
    seen: str
    problems: list[str]
    oracle: bool = False
    healthy: bool = True


@dataclass
class RouteResult:
    key: str
    combos: int = 0
    pairs: list[PairResult] = field(default_factory=list)
    unpaired: Counter[str] = field(default_factory=Counter)
    seconds: float = 0.0

    @property
    def proved(self) -> bool:
        return any(pair.healthy for pair in self.pairs)

    @property
    def problems(self) -> list[str]:
        return [
            f"{pair.variant} {pair.scenario} {pair.label}: {problem}"
            for pair in self.pairs
            for problem in pair.problems
        ]

    def absorb(self, other: RouteResult, mode: str) -> None:
        self.combos += other.combos
        self.pairs.extend(other.pairs)
        for reason, count in other.unpaired.items():
            self.unpaired[f"[{mode}] {reason}"] += count
        self.seconds += other.seconds


@dataclass
class SweepResult:
    key: str
    requests: int = 0
    informative: bool = False
    problems: list[str] = field(default_factory=list)
    statuses: Counter[int] = field(default_factory=Counter)

    def absorb(self, other: SweepResult) -> None:
        self.requests += other.requests
        self.informative = self.informative or other.informative
        self.problems.extend(other.problems)
        self.statuses.update(other.statuses)


# --------------------------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------------------------


class Runner:
    def __init__(self, world: World, *, impostor: bool = False) -> None:
        """`impostor` põe o dono e o agente de B no lugar dos de A: o detector tem de gritar."""

        self.world = world
        stand_in = world.b if impostor else world.a
        self.a = Actor("dono-A (impostor)" if impostor else "dono-A", stand_in, stand_in.owner)
        self.b = Actor("dono-B", world.b, world.b.owner)
        self.agent_a = AgentActor("agente-A (impostor)" if impostor else "agente-A", stand_in)
        self.agent_b = AgentActor("agente-B", world.b)
        self.sweepers = [
            self.a,
            Actor("operador-A", world.a, world.a.operator),
            Actor("auditor-A", world.a, world.a.auditor),
            Actor(
                "dono-A, sessão forjada para B",
                world.a,
                world.a.owner,
                session_office=world.b.office,
            ),
        ]
        self.forged = self.sweepers[-1]
        self._forged_done: set[tuple[str, str]] = set()
        self._ghosts: dict[tuple[Any, ...], Observed] = {}

    def actors(self, route: Route) -> tuple[Actor, Actor]:
        """(quem ataca, quem controla): dono de A e de B, ou o agente de cada um."""

        if route.key.startswith(AGENT_PREFIX):
            return self.agent_a, self.agent_b
        return self.a, self.b

    def requests(self) -> int:
        actors = {id(a): a for a in [self.a, self.b, self.agent_a, self.agent_b, *self.sweepers]}
        return sum(actor.sent for actor in actors.values())

    # -- fantasma: o mesmo pedido com ids que não existem em lugar nenhum ---------------------

    def ghost(self, actor: Actor, probe: Probe) -> Observed:
        key = (actor.label, probe)
        if key not in self._ghosts:
            self._ghosts[key] = actor.send(probe.method, probe.url, probe.data)
        return self._ghosts[key]

    def forget_baselines(self) -> None:
        self._ghosts.clear()
        self._forged_done.clear()

    def gap(self, actor: Actor, marker: str, control: Observed, ghost_probe: Probe) -> str:
        """`pairing_gap`, e o corpo inteiro como último recurso.

        Se tudo o mais é igual ao inexistente, compara o corpo (sem nonce, CSRF e ids) com duas
        respostas novas ao inexistente: se elas divergem entre si a página é instável e o corpo
        não prova nada; se não, qualquer diferença prova que a rota enxergou a linha.
        """

        reason = pairing_gap(marker, control, self.ghost(actor, ghost_probe))
        if not reason or not 200 <= control.status < 300:
            return reason
        first = actor.send(ghost_probe.method, ghost_probe.url, ghost_probe.data)
        second = actor.send(ghost_probe.method, ghost_probe.url, ghost_probe.data)
        if first.digest() != second.digest():
            return reason
        return "" if control.digest() != first.digest() else reason

    def body_differs(self, actor: Actor, ghost_probe: Probe, seen: Observed) -> bool:
        """O corpo que A recebeu difere do que um id inexistente recebe (páginas estáveis)."""

        if seen.digest() == self.ghost(actor, ghost_probe).digest():
            return False
        first = actor.send(ghost_probe.method, ghost_probe.url, ghost_probe.data)
        second = actor.send(ghost_probe.method, ghost_probe.url, ghost_probe.data)
        return first.digest() == second.digest() and seen.digest() != first.digest()

    def observe(self, actor: Actor, probe: Probe) -> tuple[Observed, list[Change]]:
        """A requisição e, se gravou algo suspeito, o que exatamente mudou."""

        seen = actor.send(probe.method, probe.url, probe.data)
        if not seen.unexpected_writes():
            return seen, []
        again = actor.send(probe.method, probe.url, probe.data, watch=True)
        return seen, [c for c in again.changes if c.label not in BENIGN_LABELS]

    # -- rotas com id no caminho -------------------------------------------------------------

    def run_route(self, route: Route) -> RouteResult:
        result = RouteResult(route.key)
        started = time.perf_counter()
        a, b = self.actors(route)
        combos = combos_for(route, self.world.b)
        result.combos = len(combos)
        if not combos:
            result.unpaired["sem linha compatível em B"] += 1
        proved: Counter[tuple[str, str]] = Counter()
        variants = variants_for(route)
        for combo in combos:
            for variant in variants:
                if proved[(variant.label, combo.label)] >= MAX_PAIRS_PER_VARIANT:
                    continue
                if self._one(route, combo, variant, result, a, b):
                    proved[(variant.label, combo.label)] += 1
        result.seconds = time.perf_counter() - started
        return result

    def _one(
        self, route: Route, combo: Combo, variant: Variant, result: RouteResult, a: Actor, b: Actor
    ) -> bool:
        ghost_values = dict(combo.values) | {p: GHOST_UUID for p in route.uuid_params}
        control = Probe(variant.method, route.url(combo.values), variant.payload)
        ghost = Probe(variant.method, route.url(ghost_values), variant.payload)
        seen_by_b = b.send(control.method, control.url, control.data)
        gap = self.gap(b, self.world.b.marker, seen_by_b, ghost)
        if gap:
            result.unpaired[f"{variant.label} {gap}"] += 1
            return False
        healthy = self._a_reaches_its_own(route, combo, variant, ghost, a)
        if not healthy:
            result.unpaired[f"{variant.label} A não alcança a própria linha"] += 1
        pks = [combo.values[p] for p in route.uuid_params]
        pairs = [
            self._foreign(
                route, variant.label, "todos de B", combo.label, control, ghost, seen_by_b, pks, a
            )
        ]
        if len(route.uuid_params) > 1:
            for param in route.uuid_params:
                mixed = self._mixed_values(route, combo, param)
                if mixed is None:
                    continue
                values, mixed_ghost = mixed
                pairs.append(
                    self._foreign(
                        route,
                        variant.label,
                        f"só {param} é de B",
                        combo.label,
                        Probe(variant.method, route.url(values), variant.payload),
                        Probe(variant.method, route.url(mixed_ghost), variant.payload),
                        seen_by_b,
                        pks,
                        a,
                    )
                )
        if (
            not route.key.startswith(AGENT_PREFIX)
            and (route.key, variant.label) not in self._forged_done
        ):
            # O dono de A com a sessão (e o cabeçalho da API) dizendo que o escritório é o B.
            self._forged_done.add((route.key, variant.label))
            pairs.append(
                self._foreign(
                    route,
                    variant.label,
                    "sessão forjada para B",
                    combo.label,
                    control,
                    ghost,
                    seen_by_b,
                    pks,
                    self.forged,
                )
            )
        for pair in pairs:
            pair.healthy = healthy
        result.pairs.extend(pairs)
        return healthy

    def _a_reaches_its_own(
        self, route: Route, combo: Combo, variant: Variant, ghost: Probe, a: Actor
    ) -> bool:
        """Controle simétrico: o mesmo pedido, na linha equivalente de A, tem de ser achado.

        Sem isso um 404 de A poderia vir de A estar bloqueado e não do filtro de escritório.
        """

        values = dict(combo.values)
        for param, row in combo.rows.items():
            label = row._meta.label
            index = self.world.b.rows[label].index(row)
            mine = self.world.a.rows.get(label, [])
            if index >= len(mine):
                return False
            values[param] = str(mine[index].pk)
        own = a.send(variant.method, route.url(values), variant.data)
        return self.gap(a, self.world.a.marker, own, ghost) == ""

    def _mixed_values(
        self, route: Route, combo: Combo, foreign: str
    ) -> tuple[dict[str, str], dict[str, str]] | None:
        values = dict(combo.values)
        for param in route.uuid_params:
            if param == foreign:
                continue
            row = first_row(compatible_models(route, param, self.world.a), self.world.a)
            if row is None:
                return None
            values[param] = str(row.pk)
        return values, values | {foreign: GHOST_UUID}

    def _foreign(
        self,
        route: Route,
        variant_label: str,
        scenario: str,
        label: str,
        attack: Probe,
        ghost: Probe,
        control_seen: Observed,
        pks: Iterable[str],
        a: Actor,
    ) -> PairResult:
        seen, changes = self.observe(a, attack)
        baseline = self.ghost(a, ghost)
        problems = judge(self.world, seen, baseline, control_seen, pks)
        if (
            not problems
            and seen.status == baseline.status
            and 200 <= seen.status < 300
            and self.body_differs(a, ghost, seen)
        ):
            problems.append("corpo diferente do que um id inexistente recebe")
        problems.extend(f"gravou: {change}" for change in changes)
        oracle = (
            seen.status in {403, 404}
            and baseline.status in {403, 404}
            and seen.status != baseline.status
        )
        return PairResult(
            route=route.key,
            variant=variant_label,
            scenario=scenario,
            label=label,
            url=attack.url,
            control=control_seen.summary(),
            seen=seen.summary(),
            problems=problems,
            oracle=oracle,
        )

    # -- ids no corpo ou na consulta ---------------------------------------------------------

    def run_body(self, spec: BodySpec, route: Route) -> RouteResult:
        """O id de B vai no corpo (POST) ou na consulta (GET), não no caminho."""

        result = RouteResult(spec.key)
        started = time.perf_counter()
        a, b = self.actors(route)
        statics = (static_combos(route) or [{}])[0]
        rows = [
            row
            for label in spec.labels
            for row in self._ordered(self.world.b, label)[:ROWS_PER_MODEL]
        ]
        result.combos = len(rows)
        if not rows:
            result.unpaired["sem linha compatível em B"] += 1
        proved: Counter[tuple[str, str]] = Counter()
        for row in rows:
            for variant in body_variants_for(route, spec):
                quota = (variant.label, row._meta.label)
                if proved[quota] >= MAX_PAIRS_PER_VARIANT:
                    continue
                if self._one_body(route, spec, row, variant, statics, result, a, b):
                    proved[quota] += 1
        result.seconds = time.perf_counter() - started
        return result

    def _ordered(self, tenant: Tenant, label: str) -> list[models.Model]:
        return sorted(
            tenant.rows.get(label, []),
            key=lambda row: (label, row.pk) not in tenant.preferred,
        )

    def _body_probe(
        self,
        route: Route,
        spec: BodySpec,
        variant: Variant,
        tenant: Tenant,
        statics: Mapping[str, str],
        value: str,
    ) -> Probe:
        path = dict(statics)
        for param in route.uuid_params:
            row = first_row(compatible_models(route, param, tenant), tenant)
            path[param] = str(row.pk) if row is not None else GHOST_UUID
        fixed = {key: _placeholder(tenant, text) for key, text in spec.fixed}
        data = variant.data | fixed | {spec.field: [value] if spec.as_list else value}
        return Probe(spec.method, route.url(path), json.dumps(data, sort_keys=True))

    def _one_body(
        self,
        route: Route,
        spec: BodySpec,
        row: models.Model,
        variant: Variant,
        statics: Mapping[str, str],
        result: RouteResult,
        a: Actor,
        b: Actor,
    ) -> bool:
        world = self.world
        control = self._body_probe(route, spec, variant, world.b, statics, str(row.pk))
        ghost_b = self._body_probe(route, spec, variant, world.b, statics, GHOST_UUID)
        label = f"{spec.method}[{variant.label}] {spec.field}"
        seen_by_b = b.send(control.method, control.url, control.data)
        gap = self.gap(b, world.b.marker, seen_by_b, ghost_b)
        if gap:
            result.unpaired[f"{label} {gap}"] += 1
            return False
        index = world.b.rows[row._meta.label].index(row)
        mine = world.a.rows.get(row._meta.label, [])
        own_probe = self._body_probe(
            route,
            spec,
            variant,
            world.a,
            statics,
            str(mine[index].pk) if index < len(mine) else GHOST_UUID,
        )
        ghost_a = self._body_probe(route, spec, variant, world.a, statics, GHOST_UUID)
        own = a.send(own_probe.method, own_probe.url, own_probe.data)
        healthy = index < len(mine) and self.gap(a, world.a.marker, own, ghost_a) == ""
        if not healthy:
            result.unpaired[f"{label} A não alcança a própria linha"] += 1
        attack = self._body_probe(route, spec, variant, world.a, statics, str(row.pk))
        pair = self._foreign(
            route,
            label,
            "id de B no corpo",
            row._meta.label,
            attack,
            ghost_a,
            seen_by_b,
            [str(row.pk)],
            a,
        )
        pair.healthy = healthy
        result.pairs.append(pair)
        return healthy

    # -- rotas sem id ------------------------------------------------------------------------

    def poison_query(self) -> tuple[str, set[str]]:
        """Consulta que tenta puxar dado de B: busca pelo texto e filtros por id de B."""

        b_company = self.world.b.companies[0]
        office = str(self.world.b.office.id)
        params = {
            "q": POISON_TEXT,
            "search": POISON_TEXT,
            "busca": POISON_TEXT,
            "competence": "2026-09",
            "company": str(b_company.pk),
            "company_id": str(b_company.pk),
            "organization": office,
            "office": office,
        }
        return urlencode(params), {str(b_company.pk), office}

    def run_sweep(self, route: Route) -> SweepResult:
        result = SweepResult(route.key)
        if route.key.startswith(AGENT_PREFIX):
            return self._sweep_agent(route, result)
        poison, echoed = self.poison_query()
        for statics in static_combos(route) if route.params else [{}]:
            url = route.url(statics)
            control = self.b.send("GET", url)
            result.requests += 1
            if shows_rows(self.world, control.body):
                result.informative = True
            for actor in self.sweepers:
                for target, ignore in ((url, ()), (f"{url}?{poison}", echoed)):
                    seen, changes = self.observe(actor, Probe("GET", target))
                    result.requests += 1
                    result.statuses[seen.status] += 1
                    where = f"{actor.label} {seen.summary()}"
                    result.problems.extend(
                        f"{where}: {hit}" for hit in leaks_in(self.world, seen.body, exclude=ignore)
                    )
                    result.problems.extend(
                        f"{where}: gravou {change}" for change in changes if self._touches_b(change)
                    )
        return result

    def _sweep_agent(self, route: Route, result: SweepResult) -> SweepResult:
        """O agente de A pede trabalho: nada de B pode voltar nem mudar."""

        for statics in static_combos(route) if route.params else [{}]:
            url = route.url(statics)
            for payload in agent_payloads(route):
                probe = Probe("POST", url, payload)
                control = self.agent_b.send("POST", url, probe.data)
                result.requests += 1
                if shows_rows(self.world, control.body):
                    result.informative = True
                seen, changes = self.observe(self.agent_a, probe)
                result.requests += 1
                result.statuses[seen.status] += 1
                where = f"{self.agent_a.label} {seen.summary()}"
                result.problems.extend(f"{where}: {hit}" for hit in leaks_in(self.world, seen.body))
                result.problems.extend(
                    f"{where}: gravou {change}" for change in changes if self._touches_b(change)
                )
        return result

    def _touches_b(self, change: Change) -> bool:
        return change.organization_id == str(self.world.b.office.id) or (
            change.pk.lower() in self.world.b_ids
        )


# --------------------------------------------------------------------------------------------
# Orquestração
# --------------------------------------------------------------------------------------------

# Rotas que só existem para escritório no modo procuração; as demais rodam nos dois modos.
MODES = ("certificate", "procuracao")


@dataclass
class MatrixResult:
    world: World
    param: dict[str, RouteResult] = field(default_factory=dict)
    sweep: dict[str, SweepResult] = field(default_factory=dict)
    body: dict[str, RouteResult] = field(default_factory=dict)
    differential: dict[str, str] = field(default_factory=dict)
    differential_checked: int = 0
    seconds: float = 0.0
    requests: int = 0


def run_matrix(world: World, routes: Iterable[Route], excluded: Collection[str]) -> MatrixResult:
    result = MatrixResult(world)
    runner = Runner(world)
    started = time.perf_counter()
    todo = [route for route in routes if route.key not in excluded]
    by_key = {route.key: route for route in todo}
    for mode in MODES:
        set_collection_mode(world, mode)
        runner.forget_baselines()  # a página muda com o modo: o inexistente de um não vale no outro
        for spec in BODY_SPECS:
            route = by_key.get(spec.route)
            if route is not None:
                one = runner.run_body(spec, route)
                result.body.setdefault(spec.key, RouteResult(spec.key)).absorb(one, mode)
        for route in todo:
            if route.uuid_params:
                one = runner.run_route(route)
                result.param.setdefault(route.key, RouteResult(route.key)).absorb(one, mode)
            else:
                swept = runner.run_sweep(route)
                result.sweep.setdefault(route.key, SweepResult(route.key)).absorb(swept)
    set_collection_mode(world, MODES[0])
    run_differential(world, runner, todo, result)
    result.seconds = time.perf_counter() - started
    result.requests = runner.requests()
    return result


def run_differential(
    world: World, runner: Runner, routes: Iterable[Route], result: MatrixResult
) -> None:
    """As páginas de A não podem mudar quando entra um terceiro escritório com dados.

    Pega o que o marcador não pega: contagem, total ou ordem calculados sem filtro de escritório.
    Só valem as páginas estáveis (duas respostas seguidas iguais, sem o nonce e o token CSRF).
    """

    pages = [
        route
        for route in routes
        if not route.uuid_params and not route.key.startswith(AGENT_PREFIX)
    ]
    urls = {
        route.key: route.url(
            {p.name: (STATIC_VALUES.get(p.name) or ("x",))[0] for p in route.params}
        )
        for route in pages
    }
    before: dict[str, str] = {}
    for key, url in urls.items():
        first = runner.a.send("GET", url)
        again = runner.a.send("GET", url)
        if first.status == 200 and first.digest() == again.digest():
            before[key] = first.digest()
    outsider = make_tenant(key="C", mark="ZZ-C-TERCEIRO", slug="escritorio-c", cnpj_root="77888900")
    build_rows(outsider, itertools.count(50_000), world.shared)
    for key, digest in before.items():
        result.differential_checked += 1
        after = runner.a.send("GET", urls[key])
        if after.digest() != digest:
            result.differential[key] = "a página de A mudou quando entrou outro escritório"


# --------------------------------------------------------------------------------------------
# Relatório
# --------------------------------------------------------------------------------------------


def report_lines(
    matrix: MatrixResult,
    routes: Iterable[Route],
    excluded: Mapping[str, str],
    accepted_unpaired: Mapping[str, str],
    accepted_unpaired_body: Mapping[str, str] | None = None,
) -> list[str]:
    routes = list(routes)
    with_params = [r for r in routes if r.params]
    proved = sorted(k for k, r in matrix.param.items() if r.proved)
    unpaired = sorted(k for k, r in matrix.param.items() if not r.proved)
    pairs = [pair for r in matrix.param.values() for pair in r.pairs if pair.healthy]
    by_method = Counter(pair.variant.split("[")[0] for pair in pairs)
    mixed = sum(1 for pair in pairs if pair.scenario.startswith("só "))
    forged = sum(1 for pair in pairs if pair.scenario == "sessão forjada para B")
    oracle = sum(1 for pair in pairs if pair.oracle)
    informative = sorted(k for k, r in matrix.sweep.items() if r.informative)
    rows_b = sum(len(rows) for rows in matrix.world.b.rows.values())
    lines = [
        "",
        "=== Matriz de isolamento entre escritorios (A nao enxerga nem altera B) ===",
        f"Rotas no resolver: {len(routes)} | com parametro de caminho: {len(with_params)} | "
        f"sem parametro: {len(routes) - len(with_params)}",
        f"Provadas por par (id/linha de B pedido pelo dono de A): {len(proved)} rotas, "
        f"{len(pairs)} pares ({by_method['GET']} GET, {by_method['POST']} POST, "
        f"{len(pairs) - by_method['GET'] - by_method['POST']} PATCH/PUT/DELETE; "
        f"{mixed} mistos com um id de A e outro de B, {forged} com a sessao forjada para B)",
        f"Varridas sem id (GET como dono, operador e auditor de A, com consulta envenenada e "
        f"sessao forjada para B): {len(matrix.sweep)} rotas; {len(informative)} mostram "
        f"linhas de B ao proprio dono de B",
        f"Nao pareadas (sem controle positivo): {len(unpaired)}",
    ]
    lines += [f"    {key}: {accepted_unpaired.get(key, 'SEM MOTIVO')}" for key in unpaired]
    body_proved = sorted(k for k, r in matrix.body.items() if r.proved)
    body_unpaired = sorted(k for k, r in matrix.body.items() if not r.proved)
    body_pairs = sum(len(r.pairs) for r in matrix.body.values())
    lines.append(
        f"Id no corpo ou na consulta (IDOR): {len(body_proved)} de {len(matrix.body)} campos "
        f"provados ({body_pairs} pares); sem controle positivo: {len(body_unpaired)}"
    )
    reasons = accepted_unpaired_body or {}
    lines += [f"    {key}: {reasons.get(key, 'SEM MOTIVO')}" for key in body_unpaired]
    in_body_specs = {spec.route for spec in BODY_SPECS}
    post_only = sorted(
        key
        for key, swept in matrix.sweep.items()
        if set(swept.statuses) == {405} and key not in in_body_specs
    )
    lines.append(
        f"Varridas que respondem 405 a todo GET (so POST) e sem campo de corpo provado: "
        f"{len(post_only)}"
    )
    lines += [f"    {key}" for key in post_only]
    lines.append(
        f"Diferencial (pagina de A igual com um terceiro escritorio presente): "
        f"{matrix.differential_checked} paginas estaveis, {len(matrix.differential)} mudaram"
    )
    lines.append(f"Excluidas da matriz: {len(excluded)}")
    lines += [f"    {key}: {reason}" for key, reason in sorted(excluded.items())]
    lines += [
        f"Mundo de B: {rows_b} linhas em {len(matrix.world.b.rows)} modelos; "
        f"nao construidos: {sorted(matrix.world.b.failures) or 'nenhum'}",
        f"Respostas 403/404 que denunciam a existencia da linha (status diferente do id "
        f"inexistente): {oracle} pares",
        f"Requisicoes: {matrix.requests} em {matrix.seconds:.1f} s",
    ]
    return lines
