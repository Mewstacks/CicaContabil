"""Telas do Fechamento por Recibo.

Mesmo idioma dos módulos irmãos (Triagem e Contraprova): ``office_required`` na porta,
``_module_page_context`` no portão do módulo e do colaborador, ``hub/workspace.html`` como
esqueleto. Ler exige o módulo ligado e a empresa na carteira de quem pede; escrever exige
também papel operacional (dono, administrador, gestor ou operador) ou suporte autorizado.
"""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.closing import engine, services
from apps.closing.forms import DecisionForm, FieldForm, LayoutForm, SampleForm, UploadForm
from apps.closing.models import ClosingConference, ClosingDocument, ClosingField, ClosingLayout
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required, refuse
from apps.organizations.models import Membership, Organization

WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.OPERATOR,
}
WIDE_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.MANAGER}
PAGE_SIZE = 25
MAX_QUERY = 100
MAX_FILES = 20

FILTERS = [
    ("todos", "Todos"),
    ("decidir", "Para decidir"),
    ("quarentena", "Quarentena"),
    ("baixados", "Baixados"),
]


def _can_write(context: dict[str, object]) -> bool:
    if context.get("support_session") is not None:
        return bool(context.get("support_can_mutate"))
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in WRITE_ROLES


def _gate(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.CLOSING))
    if blocked is None:
        context["can_write"] = _can_write(context)
    return context, blocked


def _office(context: dict[str, object]) -> Organization:
    return cast(Organization, context["office"])


def _companies(context: dict[str, object]) -> QuerySet[ClientCompany]:
    return cast("QuerySet[ClientCompany]", context["companies"])


def _visible(context: dict[str, object], user: User) -> QuerySet[ClosingDocument]:
    """Documentos do escritório na carteira de quem pede.

    Um arquivo ainda sem empresa não pertence a nenhuma carteira: quem enviou o vê, e os
    papéis que enxergam o escritório inteiro também.
    """
    membership = context.get("membership")
    wide = isinstance(membership, Membership) and membership.role in WIDE_ROLES
    unassigned = Q(company__isnull=True) & (Q() if wide else Q(uploaded_by=user))
    return ClosingDocument.objects.filter(organization=_office(context)).filter(
        Q(company__in=_companies(context)) | unassigned
    )


def _load(context: dict[str, object], user: User, document_id: UUID) -> ClosingDocument:
    return get_object_or_404(
        _visible(context, user).select_related("company", "layout"), pk=document_id
    )


def _no_store[R: HttpResponseBase](response: R) -> R:
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _wide(context: dict[str, object]) -> bool:
    if context.get("support_session") is not None:
        return bool(context.get("support_can_mutate"))
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in WIDE_ROLES


def _need_write(request: HttpRequest, context: dict[str, object]) -> HttpResponse | None:
    if not context["can_write"]:
        return refuse(request, "Seu acesso só consulta o Fechamento.")
    return None


# --- documentos ----------------------------------------------------------------------


def _filter_documents(qs: QuerySet[ClosingDocument], *, q: str, state: str, month: str) -> Any:
    if q:
        qs = qs.filter(Q(original_name__icontains=q) | Q(company__name__icontains=q))
    if month:
        try:
            year, mon = month.split("-")
            qs = qs.filter(competence__year=int(year), competence__month=int(mon))
        except (ValueError, TypeError):
            pass
    latest = ClosingConference.objects.filter(document=OuterRef("pk")).order_by("-created_at")
    qs = qs.annotate(
        last_outcome=Subquery(latest.values("outcome")[:1]),
        last_resolution=Subquery(latest.values("resolution")[:1]),
        last_checklist=Subquery(latest.values("checklist")[:1]),
    )
    if state == "quarentena":
        qs = qs.filter(state=ClosingDocument.State.QUARANTINE)
    elif state == "decidir":
        qs = qs.filter(
            state=ClosingDocument.State.ACCEPTED,
            last_resolution="",
            last_outcome__in=["diverged", "waiting", "read"],
        ).exclude(Q(last_outcome="read") & ~Q(layout__requires_human=True))
    elif state == "baixados":
        qs = qs.filter(last_checklist="done")
    return qs


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    base = _visible(context, cast(User, request.user)).exclude(
        state=ClosingDocument.State.DISCARDED
    )
    q = request.GET.get("q", "").strip()[:MAX_QUERY]
    month = request.GET.get("mes", "")[:7]
    state = request.GET.get("situacao", "")
    state = state if state in dict(FILTERS) else "todos"
    documents = _filter_documents(base, q=q, state=state, month=month).select_related(
        "company", "layout"
    )
    page = Paginator(documents, PAGE_SIZE).get_page(request.GET.get("pagina"))
    for item in page.object_list:
        item.latest = item.conferences.first()
    params = {key: value for key, value in request.GET.items() if key != "pagina" and value}
    context.update(
        {
            "page_title": "Fechamento",
            "page": page,
            "total": base.count(),
            "filters": {"q": q, "mes": month, "situacao": state},
            "filters_applied": bool(q or month or state != "todos"),
            "query_without_page": urlencode(params),
            "state_filters": FILTERS,
            "upload_form": UploadForm(),
        }
    )
    return render(request, "closing/index.html", context)


@office_required
@require_POST
def upload(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    files = request.FILES.getlist("documents")
    if not files:
        messages.error(request, "Escolha ao menos um arquivo.")
        return redirect("closing:index")
    if len(files) > MAX_FILES:
        messages.error(request, f"Envie até {MAX_FILES} arquivos por vez.")
        return redirect("closing:index")
    office = _office(context)
    accepted = 0
    last: ClosingDocument | None = None
    for item in files:
        try:
            last = services.ingest_upload(
                organization=office,
                actor=cast(User, request.user),
                upload=item,
                request=request,
                allowed_companies=_companies(context),
                visible_documents=_visible(context, cast(User, request.user)),
            )
            accepted += 1
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    if accepted == 1 and last is not None:
        return redirect("closing:document", document_id=last.pk)
    if accepted:
        messages.success(request, f"{accepted} arquivos recebidos.")
    return redirect("closing:index")


@office_required
@require_GET
def document(request: HttpRequest, document_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _load(context, cast(User, request.user), document_id)
    conferences = list(item.conferences.select_related("resolved_by", "layout")[:20])
    latest = conferences[0] if conferences else None
    context.update(
        {
            "page_title": item.original_name,
            "document": item,
            "latest": latest,
            "history": conferences[1:],
            "decision_form": DecisionForm(),
            "reads": _reads(item),
            "can_decide": bool(context["can_write"] and latest and latest.needs_person),
            "can_make_layout": bool(context["can_write"] and _wide(context)),
        }
    )
    return render(request, "closing/document.html", context)


def _reads(item: ClosingDocument) -> list[tuple[str, str]]:
    from apps.closing.models import Variable

    rows: list[tuple[str, str]] = []
    for variable, value in item.read_values.items():
        label = Variable(variable).label if variable in Variable.values else variable
        rows.append((label, str(value)))
    return rows


@office_required
@require_GET
def document_file(request: HttpRequest, document_id: UUID) -> HttpResponseBase:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if context.get("support_session") is not None and not context.get("support_can_mutate"):
        return refuse(request, "Suporte somente leitura não baixa o arquivo do cliente.")
    item = _load(context, cast(User, request.user), document_id)
    try:
        stream = item.file.open("rb")
    except (OSError, ValueError) as exc:
        raise Http404 from exc
    response = FileResponse(stream, as_attachment=True, filename=item.original_name)
    return _no_store(response)


@office_required
@require_POST
def document_reread(request: HttpRequest, document_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _load(context, cast(User, request.user), document_id)
    try:
        item = services.reread(
            item, actor=cast(User, request.user), allowed_companies=_companies(context)
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("closing:document", document_id=item.pk)


@office_required
@require_POST
def document_discard(request: HttpRequest, document_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _load(context, cast(User, request.user), document_id)
    services.discard(item, actor=cast(User, request.user), request=request)
    messages.success(request, "Arquivo descartado.")
    return redirect("closing:index")


@office_required
@require_POST
def conference_decide(request: HttpRequest, document_id: UUID, conference_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _load(context, cast(User, request.user), document_id)
    conference = get_object_or_404(ClosingConference, pk=conference_id, document=item)
    form = DecisionForm(request.POST)
    accept = request.POST.get("decision") == "accept"
    if not form.is_valid():
        messages.error(request, "Informe o motivo da decisão.")
    else:
        try:
            services.resolve(
                conference,
                actor=cast(User, request.user),
                accept=accept,
                reason=form.cleaned_data["reason"],
                request=request,
            )
            messages.success(request, "Decisão registrada.")
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    return redirect("closing:document", document_id=item.pk)


@office_required
@require_POST
def document_to_layout(request: HttpRequest, document_id: UUID) -> HttpResponse:
    """Abre um layout em rascunho usando este arquivo como amostra (só quem vê a carteira toda)."""
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    if not _wide(context):
        return refuse(request, "Só quem vê a carteira inteira cria layout a partir de um arquivo.")
    item = _load(context, cast(User, request.user), document_id)
    office = _office(context)
    base = "novo-layout"
    code, n = base, 1
    while ClosingLayout.objects.filter(organization=office, code=code).exists():
        n += 1
        code = f"{base}-{n}"
    layout = ClosingLayout.objects.create(
        organization=office, code=code, label="Novo layout", sample_text=item.text[:60000]
    )
    return redirect("closing:layout", layout_id=layout.pk)


# --- layouts -------------------------------------------------------------------------


def _layout(context: dict[str, object], layout_id: UUID) -> ClosingLayout:
    return get_object_or_404(
        ClosingLayout.objects.prefetch_related("fields"),
        pk=layout_id,
        organization=_office(context),
    )


@office_required
@require_GET
def layouts(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    context.update(
        {
            "page_title": "Layouts",
            "layouts": ClosingLayout.objects.filter(organization=_office(context)),
        }
    )
    return render(request, "closing/layouts.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def layout_new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    office = _office(context)
    form = LayoutForm(request.POST or None, organization=office)
    if request.method == "POST" and form.is_valid():
        layout = form.save()
        record_event(
            action="closing.layout.created",
            actor=cast(User, request.user),
            organization=office,
            target=layout,
            request=request,
            metadata={"code": layout.code},
        )
        return redirect("closing:layout", layout_id=layout.pk)
    context.update({"page_title": "Novo layout", "form": form, "creating": True})
    return render(request, "closing/layout.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def layout(request: HttpRequest, layout_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _layout(context, layout_id)
    office = _office(context)
    form = LayoutForm(request.POST or None, instance=item, organization=office)
    if request.method == "POST":
        if denied := _need_write(request, context):
            return denied
        if form.is_valid():
            form.save()
            messages.success(request, "Layout guardado.")
            return redirect("closing:layout", layout_id=item.pk)
    # A amostra é texto de documento de cliente: só quem vê a carteira inteira a vê.
    can_see_sample = _wide(context)
    sample_text = item.sample_text if can_see_sample else ""
    rows = services.diagnose(item, sample_text) if sample_text.strip() else []
    problems = services.activation_problems(item)
    context.update(
        {
            "page_title": item.label,
            "layout": item,
            "form": form,
            "fields": item.fields.all(),
            "field_form": FieldForm(layout=item),
            "can_see_sample": can_see_sample,
            "sample_form": SampleForm(initial={"sample_text": sample_text}),
            "diagnosis": rows,
            "problems": problems,
        }
    )
    return render(request, "closing/layout.html", context)


@office_required
@require_POST
def layout_field_add(request: HttpRequest, layout_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _layout(context, layout_id)
    form = FieldForm(request.POST, layout=item)
    if form.is_valid():
        field = form.save(commit=False)
        field.position = item.fields.count()
        try:
            field.full_clean(exclude=["layout", "organization"])
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            field.save()
            _deactivate_if_broken(item)
    else:
        messages.error(request, "; ".join(str(m) for errs in form.errors.values() for m in errs))
    return redirect("closing:layout", layout_id=item.pk)


@office_required
@require_POST
def layout_field_remove(request: HttpRequest, layout_id: UUID, field_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _layout(context, layout_id)
    get_object_or_404(ClosingField, pk=field_id, layout=item).delete()
    _deactivate_if_broken(item)
    return redirect("closing:layout", layout_id=item.pk)


def _deactivate_if_broken(item: ClosingLayout) -> None:
    """Um layout ativo que perdeu um campo obrigatório volta a rascunho."""
    item = ClosingLayout.objects.prefetch_related("fields").get(pk=item.pk)
    if item.active and [p for p in services.activation_problems(item) if "amostra" not in p]:
        item.active = False
        item.save(update_fields=["active", "updated_at"])


@office_required
@require_POST
def layout_sample(request: HttpRequest, layout_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    if not _wide(context):
        return refuse(request, "Só quem vê a carteira inteira troca a amostra.")
    item = _layout(context, layout_id)
    form = SampleForm(request.POST, request.FILES)
    if form.is_valid():
        upload_file = form.cleaned_data["sample"]
        text = form.cleaned_data["sample_text"]
        if upload_file is not None:
            result = engine.read_text(upload_file.read(services.MAX_BYTES), upload_file.name)
            if not result.text.strip():
                messages.error(request, result.message or "Não consegui ler texto neste arquivo.")
                return redirect("closing:layout", layout_id=item.pk)
            text = result.text
        item.sample_text = text[:60000]
        item.save(update_fields=["sample_text", "updated_at"])
    return redirect("closing:layout", layout_id=item.pk)


@office_required
@require_POST
def layout_activate(request: HttpRequest, layout_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := _need_write(request, context):
        return denied
    item = _layout(context, layout_id)
    if request.POST.get("action") == "deactivate":
        item.active = False
        item.save(update_fields=["active", "updated_at"])
        messages.success(request, "Layout desativado.")
    else:
        problems = services.activation_problems(item)
        if problems:
            messages.error(request, problems[0])
        else:
            item.active = True
            item.save(update_fields=["active", "updated_at"])
            record_event(
                action="closing.layout.activated",
                actor=cast(User, request.user),
                organization=item.organization,
                target=item,
                request=request,
                metadata={"code": item.code},
            )
            messages.success(request, "Layout ativado.")
    return redirect("closing:layout", layout_id=item.pk)
