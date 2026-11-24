"""Telas do Contraprova.

Mesmo idioma dos módulos irmãos: `office_required` na porta, `_module_page_context` no
portão do módulo e do colaborador, `hub/workspace.html` como esqueleto. Ler exige o módulo
ligado e a empresa na carteira de quem pede; escrever exige também papel operacional
(dono, administrador, gestor ou operador) ou sessão de suporte com alteração autorizada.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from typing import Any, cast
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.audit.services import record_event
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required, refuse
from apps.organizations.models import Membership, Organization

from . import agent, limits, queries
from .engine.report import csv_header, csv_row, render_txt
from .engine.rules import OPERATIONS, RuleSet, describe
from .engine.tools import SPED_XML, TOOLS, UF_DOMINIO
from .forms import NewRunForm
from .models import CrosscheckRun, crosscheck_storage
from .services import (
    CrosscheckError,
    attach_files,
    cancel_run,
    dominio_source,
    readiness,
    remove_input,
    repeat_run,
    start_run,
)

WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.MANAGER,
    Membership.Role.OPERATOR,
}
#: Marca de ordem de bytes: o Excel brasileiro só abre CSV UTF-8 com acento se ela vier antes.
_BOM = chr(0xFEFF)
AGENT_TONES = {
    "queued": "is-warning",
    "claimed": "is-warning",
    "receiving": "is-warning",
    "succeeded": "is-active",
    "failed": "is-danger",
}
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")
_MAX_QUERY = 100


# ---------------------------------------------------------------------------------------
# Portão


def _can_write(context: dict[str, object]) -> bool:
    if context.get("support_session") is not None:
        return bool(context.get("support_can_mutate"))
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in WRITE_ROLES


def _can_download(context: dict[str, object]) -> bool:
    """Suporte somente leitura vê a tela, mas não leva o derivado do cliente (D-276)."""

    return context.get("support_session") is None or bool(context.get("support_can_mutate"))


def _gate(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.CROSSCHECK))
    if blocked is None:
        context["can_write"] = _can_write(context)
        context["can_download"] = _can_download(context)
        context["agent_enabled"] = bool(getattr(settings, "CONTRAPROVA_AGENT_ENABLED", False))
    return context, blocked


def _companies(context: dict[str, object]) -> QuerySet[ClientCompany]:
    return cast("QuerySet[ClientCompany]", context["companies"])


def _load_run(context: dict[str, object], run_id: object) -> CrosscheckRun:
    return get_object_or_404(
        CrosscheckRun.objects.select_related("company", "organization", "created_by"),
        pk=run_id,
        organization=cast(Organization, context["office"]),
        company__in=_companies(context),
    )


def _no_store[R: HttpResponseBase](response: R) -> R:
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _wants_json(request: HttpRequest) -> bool:
    return "application/json" in request.headers.get("Accept", "")


# ---------------------------------------------------------------------------------------
# Lista


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    base = queries.visible_runs(office, _companies(context))
    q = request.GET.get("q", "").strip()[:_MAX_QUERY]
    tool = request.GET.get("ferramenta", "")
    tool = tool if tool in TOOLS else ""
    state = request.GET.get("situacao", "")
    state = state if state in queries.STATE_FILTERS else "todas"
    runs = queries.filter_runs(base, q=q, tool=tool, state=state)
    page = Paginator(runs, queries.PAGE_SIZE).get_page(request.GET.get("pagina"))
    params = {key: value for key, value in request.GET.items() if key != "pagina" and value}
    context.update(
        {
            "page_title": "Contraprova",
            "page": page,
            "total_runs": base.count(),
            "filters": {"q": q, "ferramenta": tool, "situacao": state},
            "filters_applied": bool(q or tool or state != "todas"),
            "query_without_page": urlencode(params),
            "tools": list(TOOLS.values()),
            "state_filters": [
                ("todas", "Todas"),
                ("andamento", "Em andamento"),
                ("divergencia", "Com divergência"),
                ("falha", "Com falha"),
                ("rascunho", "Rascunhos"),
            ],
        }
    )
    return render(request, "crosscheck/index.html", context)


# ---------------------------------------------------------------------------------------
# Nova conferência


@office_required
@require_http_methods(["GET", "POST"])
def new_run(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_write"]:
        return refuse(request, "Seu acesso só consulta as conferências.")
    office = cast(Organization, context["office"])
    initial = {
        "tool": request.GET.get("ferramenta")
        if request.GET.get("ferramenta") in TOOLS
        else SPED_XML,
        "company": request.GET.get("empresa") or None,
    }
    form = NewRunForm(
        request.POST or None,
        companies=_companies(context),
        agent_enabled=bool(context["agent_enabled"]),
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        from .services import create_draft

        try:
            run = create_draft(
                organization=office,
                company=form.cleaned_data["company"],
                tool=form.cleaned_data["tool"],
                competence=form.cleaned_data["competence"],
                options=form.options,
                actor=request.user,
                request=request,
            )
        except CrosscheckError as exc:
            for message in exc.messages:
                form.add_error(None, message)
        else:
            return redirect("crosscheck:run-detail", run_id=run.id)
    context.update(
        {
            "page_title": "Contraprova",
            "form": form,
            "tools": list(TOOLS.values()),
            "operations": list(OPERATIONS.items()),
        }
    )
    return render(request, "crosscheck/new.html", context)


# ---------------------------------------------------------------------------------------
# Conferência


def _role_blocks(run: CrosscheckRun) -> list[dict[str, Any]]:
    tool = TOOLS[run.tool]
    inputs = list(run.inputs.all())
    caps = {
        "efd": limits.MAX_SPED_BYTES,
        "xml": limits.MAX_ZIP_BYTES,
        "dominio": limits.MAX_DOMINIO_BYTES,
    }
    blocks: list[dict[str, Any]] = []
    for role in tool.roles:
        if role.kind == "dominio" and dominio_source(run) == "agente":
            continue
        items = [item for item in inputs if item.role == role.code]
        blocks.append(
            {
                "role": role,
                "items": items,
                "can_add": len(items) < role.maximum,
                "max_bytes": caps[role.kind],
                "accept": role.accept,
                "multiple": role.kind == "xml",
                "optional": role.minimum == 0 and role.kind != "dominio",
            }
        )
    return blocks


def _tab_for(run: CrosscheckRun, code: str) -> Any:
    return TOOLS[run.tool].tab(code) if code else TOOLS[run.tool].tabs[0]


def _result_context(request: HttpRequest, run: CrosscheckRun) -> dict[str, Any]:
    tool = TOOLS[run.tool]
    tab = _tab_for(run, request.GET.get("aba", ""))
    counts = queries.tab_counts(run, tool)
    q = request.GET.get("q", "").strip()[:_MAX_QUERY]
    field = request.GET.get("campo", "")[:40]
    cfop = request.GET.get("cfop", "").strip()[:20]
    operation = request.GET.get("operacao", "")
    rows = queries.findings_for_tab(run, tab, q=q, field=field, cfop=cfop, operation=operation)
    page = Paginator(rows, queries.FINDINGS_PAGE_SIZE).get_page(request.GET.get("pagina"))
    params = {key: value for key, value in request.GET.items() if key != "pagina" and value}
    tabs = []
    for item in tool.tabs:
        link = {key: value for key, value in params.items() if key in {"q", "cfop", "operacao"}}
        link["aba"] = item.code
        tabs.append(
            {
                "code": item.code,
                "label": item.label,
                "count": counts[item.code],
                "current": item.code == tab.code,
                "url": "?" + urlencode(link),
            }
        )
    return {
        "tabs": tabs,
        "max_findings_text": f"{limits.MAX_FINDINGS_STORED:,}".replace(",", "."),
        "tab": tab,
        "tab_count": counts[tab.code],
        "page": page,
        "filters": {"q": q, "campo": field, "cfop": cfop, "operacao": operation},
        "filters_applied": bool(q or field or cfop or operation),
        "field_options": queries.field_options(run, tab),
        "query_without_page": urlencode(params),
        "download_query": urlencode(
            {key: value for key, value in params.items() if key != "aba"} | {"aba": tab.code}
        ),
        "rules_lines": describe(RuleSet.from_snapshot(run.rules_snapshot), run.tool),
        "files_seen": run.summary.get("files", []),
        "warnings": run.problem_messages("warning"),
    }


@office_required
@require_GET
def run_detail(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    run = _load_run(context, run_id)
    tool = TOOLS[run.tool]
    context.update({"page_title": "Contraprova", "run": run, "tool": tool})
    if run.state == CrosscheckRun.State.DRAFT:
        issues = readiness(run)
        if tool.code == UF_DOMINIO and dominio_source(run) == "agente":
            status = agent.status_payload(agent.latest_job(run))
            context["agent"] = {
                **status,
                "active": status["state"] in {"queued", "claimed", "receiving"},
                "tone": AGENT_TONES.get(status["state"], "is-muted"),
            }
        context.update(
            {
                "role_blocks": _role_blocks(run),
                "issues": issues,
                "blocking": [item for item in issues if item.severity == "error"],
                "notes": [item for item in issues if item.severity == "warning"],
                "rules_lines": describe(RuleSet.from_snapshot(run.rules_snapshot), run.tool),
                "max_loose_xml": limits.MAX_LOOSE_XML_PER_REQUEST,
                "max_loose_bytes": limits.MAX_LOOSE_XML_BYTES_PER_REQUEST,
                "max_xml_bytes": limits.MAX_XML_BYTES,
            }
        )
    elif run.state == CrosscheckRun.State.DONE and run.has_result:
        context.update(_result_context(request, run))
    elif run.state in {CrosscheckRun.State.FAILED, CrosscheckRun.State.CANCELED}:
        context.update(
            {
                "errors": run.problem_messages("error"),
                "warnings": run.problem_messages("warning"),
                "can_repeat": run.inputs_available and run.inputs.exists(),
            }
        )
    return render(request, "crosscheck/run.html", context)


@office_required
@require_GET
def run_status(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return JsonResponse({"error": "forbidden"}, status=blocked.status_code)
    run = _load_run(context, run_id)
    payload = {
        "state": run.state,
        "state_label": run.get_state_display(),
        "stage": run.stage_label,
        "done": run.progress_done,
        "total": run.progress_total,
        "terminal": run.is_terminal,
        "cancel_requested": run.cancel_requested_at is not None,
    }
    if run.tool == UF_DOMINIO and dominio_source(run) == "agente":
        payload["agent"] = agent.status_payload(agent.latest_job(run))
    return _no_store(JsonResponse(payload))


def _require_write(request: HttpRequest, context: dict[str, object]) -> HttpResponse | None:
    if context["can_write"]:
        return None
    if _wants_json(request):
        return JsonResponse({"errors": ["Seu acesso só consulta as conferências."]}, status=403)
    return refuse(request, "Seu acesso só consulta as conferências.")


@office_required
@require_POST
def run_attach(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    role = request.POST.get("role", "")
    uploads = request.FILES.getlist("files")
    try:
        result = attach_files(run, role, uploads, actor=request.user, request=request)
        errors = result.errors
        stored = result.stored
    except CrosscheckError as exc:
        errors, stored = exc.messages, []
    if _wants_json(request):
        payload = {
            "stored": [
                {
                    "id": str(item.id),
                    "name": item.original_name,
                    "size": item.size_bytes,
                    "role": item.role,
                }
                for item in stored
            ],
            "errors": errors,
        }
        return JsonResponse(payload, status=200 if stored or not errors else 422)
    for message in errors:
        messages.error(request, message)
    return redirect("crosscheck:run-detail", run_id=run.id)


@office_required
@require_POST
def run_remove(request: HttpRequest, run_id: object, input_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    try:
        remove_input(run, cast(Any, input_id), actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
    return redirect("crosscheck:run-detail", run_id=run.id)


@office_required
@require_POST
def run_start(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    try:
        started, reused = start_run(run, actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("crosscheck:run-detail", run_id=run.id)
    if reused:
        messages.info(request, "Já existe uma conferência igual; este é o resultado dela.")
    return redirect("crosscheck:run-detail", run_id=started.id)


@office_required
@require_POST
def run_agent_request(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    try:
        agent.request_agent_job(run, actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
    return redirect("crosscheck:run-detail", run_id=run.id)


@office_required
@require_POST
def run_agent_file(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    try:
        agent.switch_to_file(run, actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
    return redirect("crosscheck:run-detail", run_id=run.id)


@office_required
@require_POST
def run_cancel(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    try:
        cancel_run(run, actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("crosscheck:run-detail", run_id=run.id)
    if run.state == CrosscheckRun.State.DRAFT:
        return redirect("crosscheck:index")
    return redirect("crosscheck:run-detail", run_id=run.id)


@office_required
@require_POST
def run_repeat(request: HttpRequest, run_id: object) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    denied = _require_write(request, context)
    if denied:
        return denied
    run = _load_run(context, run_id)
    options: dict[str, Any] = {}
    if request.POST.get("tolerance_cents", "").strip():
        options["tolerance_cents"] = request.POST["tolerance_cents"].strip()
    if request.POST.get("operation") in OPERATIONS:
        options["operation"] = request.POST["operation"]
    try:
        fresh = repeat_run(run, options=options or None, actor=request.user, request=request)
    except CrosscheckError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("crosscheck:run-detail", run_id=run.id)
    return redirect("crosscheck:run-detail", run_id=fresh.id)


# ---------------------------------------------------------------------------------------
# Downloads


class _Echo:
    def write(self, value: str) -> str:
        return value


def _filename(run: CrosscheckRun, extension: str, tab: str = "") -> str:
    stem = f"contraprova-{run.tool}-{run.competence:%Y-%m}" + (f"-{tab}" if tab else "")
    return f"{_FILENAME_SAFE.sub('', stem)}.{extension}"


def _tab_findings(request: HttpRequest, run: CrosscheckRun) -> tuple[Any, Iterator[Any]]:
    tab = _tab_for(run, request.GET.get("aba", ""))
    rows = queries.findings_for_tab(
        run,
        tab,
        q=request.GET.get("q", "").strip()[:_MAX_QUERY],
        field=request.GET.get("campo", "")[:40],
        cfop=request.GET.get("cfop", "").strip()[:20],
        operation=request.GET.get("operacao", ""),
    )

    def chunks() -> Iterator[Any]:
        last = 0
        while True:
            batch = list(rows.filter(seq__gt=last)[:2000])
            if not batch:
                return
            for row in batch:
                yield queries.to_finding(row)
            last = batch[-1].seq

    return tab, chunks()


@office_required
@require_GET
def run_download(request: HttpRequest, run_id: object, fmt: str) -> HttpResponseBase:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if not context["can_download"]:
        return refuse(request, "A sessão de suporte somente leitura não baixa arquivos do cliente.")
    run = _load_run(context, run_id)
    if run.state != CrosscheckRun.State.DONE or not run.has_result:
        raise Http404
    tool = TOOLS[run.tool]
    record_event(
        action="crosscheck.run.downloaded",
        actor=request.user,
        organization=run.organization,
        target=run,
        request=request,
        metadata={"run_id": str(run.id), "tool": run.tool, "format": fmt},
    )
    if fmt == "xlsx":
        handle = crosscheck_storage().open(run.result_file.name or "", "rb")
        attachment = FileResponse(
            handle, as_attachment=True, filename=_filename(run, "xlsx"), content_type=XLSX_TYPE
        )
        return _no_store(attachment)
    tab, findings = _tab_findings(request, run)
    if fmt == "csv":
        writer = csv.writer(_Echo(), delimiter=";", lineterminator="\r\n")

        def lines() -> Iterator[str]:
            yield _BOM + writer.writerow(csv_header(tool))
            for finding in findings:
                yield writer.writerow(csv_row(finding))

        streaming = StreamingHttpResponse(lines(), content_type="text/csv; charset=utf-8")
        streaming["Content-Disposition"] = (
            f'attachment; filename="{_filename(run, "csv", tab.code)}"'
        )
        return _no_store(streaming)
    if fmt == "txt":
        text, total = render_txt(tool, findings, limit=5000)
        if total > 5000:
            text += f"\n\n(Mostrando 5000 de {total}. O XLSX traz todos.)"
        response = HttpResponse(text, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{_filename(run, "txt", tab.code)}"'
        )
        return _no_store(response)
    raise Http404


@office_required
@require_GET
def dominio_template(request: HttpRequest) -> HttpResponse:
    """Modelo de planilha do Domínio: cabeçalho e uma linha de exemplo."""

    _context, blocked = _gate(request)
    if blocked:
        return blocked
    body = _BOM + "chave;uf;direcao\r\n" + "35" + "0" * 42 + ";SP;S\r\n"
    response = HttpResponse(body, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="modelo-dominio.csv"'
    return _no_store(response)
