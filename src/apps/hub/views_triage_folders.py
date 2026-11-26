"""Triagem: the office's folder tree, rules by document type and client folders."""

from __future__ import annotations

import uuid
from typing import Any, cast

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_collaborators, _module_page_context, office_required, refuse
from apps.organizations.models import Organization
from apps.triage import folders
from apps.triage.models import (
    ClientFolder,
    DestinationProfile,
    DocumentType,
    FolderModel,
    ObligationFolderRule,
)

_ACTIONS = {
    "toggle",
    "rename",
    "add",
    "remove",
    "rule_save",
    "rule_remove",
    "provision",
    "inventory",
}


class NodeForm(forms.Form):
    revision = forms.IntegerField(min_value=1)
    node = forms.CharField(required=False, max_length=36)
    name = forms.CharField(required=False, max_length=120)
    variable = forms.ChoiceField(
        required=False, choices=[(v, v) for v in sorted(folders.VARIABLES)]
    )


class RuleForm(forms.Form):
    document_type = forms.UUIDField()
    kind = forms.ChoiceField(choices=ObligationFolderRule.Kind.choices)
    node = forms.CharField(max_length=36)


def _flat(tree: list[folders.Node]) -> list[dict[str, Any]]:
    return [
        {
            "id": node["id"],
            "name": node["name"],
            "variable": node["variable"],
            "depth": len(parents),
            "label": f"{'- ' * len(parents)}{node['name']}",
        }
        for node, parents in folders.iter_nodes(tree)
    ]


def _crumb(tree: list[folders.Node], node_id: str) -> str:
    try:
        node, parents = folders.find_node(tree, node_id)
    except ValidationError:
        return ""
    return " / ".join(step["name"] for step in (*parents, node))


def _edit_tree(tree: list[folders.Node], data: dict[str, Any], action: str) -> None:
    name = str(data["name"]).strip()
    variable = str(data["variable"] or "")
    if action == "add":
        child: folders.Node = {
            "id": str(uuid.uuid4()),
            "name": name or variable.upper(),
            "variable": variable,
            "use": "",
            "children": [],
        }
        if not data["node"]:
            tree.append(child)
            return
        target, _ = folders.find_node(tree, data["node"])
        target["children"].append(child)
        return
    target, parents = folders.find_node(tree, data["node"])
    if action == "rename":
        target["name"] = name or target["name"]
        target["variable"] = variable
        return
    siblings = parents[-1]["children"] if parents else tree
    siblings.remove(target)


@office_required
@require_http_methods(["GET", "POST"])
def triage_folders(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    can_manage = _can_manage_collaborators(context) and not office.is_demo
    model = FolderModel.objects.filter(organization=office).first()
    profile = DestinationProfile.objects.filter(organization=office).first()
    error = ""
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Somente o administrador altera as pastas.")
        action = request.POST.get("action", "")
        if action not in _ACTIONS:
            return refuse(request, "Ação inválida.")
        try:
            _apply(request, office, action)
        except ValidationError as exc:
            error = " ".join(exc.messages)
        else:
            return redirect("hub:triage-folders")
        model = FolderModel.objects.filter(organization=office).first()
    tree = model.tree if model else []
    rules = ObligationFolderRule.objects.filter(organization=office).select_related("document_type")
    states = dict(
        ClientFolder.objects.filter(organization=office)
        .values_list("state")
        .annotate(total=Count("id"))
    )
    context.update(
        {
            "page_title": "Pastas",
            "can_manage_folders": can_manage,
            "folder_model": model,
            "folder_tree": tree,
            "folder_nodes": _flat(tree),
            "folder_enabled": bool(
                profile and profile.folder_model_enabled and model and model.active
            ),
            "folder_rules": [{"rule": rule, "crumb": _crumb(tree, rule.node_id)} for rule in rules],
            "document_types": DocumentType.objects.filter(organization=office, active=True),
            "rule_kinds": ObligationFolderRule.Kind.choices,
            "variables": [v for v in sorted(folders.VARIABLES) if v],
            "folder_states": {
                "created": states.get(ClientFolder.State.CREATED, 0),
                "pending": states.get(ClientFolder.State.PENDING, 0),
                "failed": states.get(ClientFolder.State.FAILED, 0),
            },
            "folder_error": error,
        }
    )
    return render(request, "hub/triage_folders.html", context, status=400 if error else 200)


def _apply(
    request: HttpRequest,
    office: Organization,
    action: str,
) -> None:
    actor = cast(User, request.user)
    if action == "toggle":
        current = folders.ensure_model(office)
        enable = request.POST.get("enabled") == "1"
        if enable:
            folders.validate_tree(current.tree)
        current.active = enable
        current.save(update_fields=["active", "updated_at"])
        DestinationProfile.objects.update_or_create(
            organization=office, defaults={"folder_model_enabled": enable}
        )
    elif action in {"rename", "add", "remove"}:
        node_form = NodeForm(request.POST)
        if not node_form.is_valid():
            raise ValidationError("Revise os campos.")
        current = folders.ensure_model(office)
        if node_form.cleaned_data["revision"] != current.revision:
            raise ValidationError("O modelo mudou. Recarregue.")
        tree = current.tree
        _edit_tree(tree, node_form.cleaned_data, action)
        folders.save_tree(current, tree)
        # A rule that points at a retired node stops resolving instead of guessing.
        live = {node["id"] for node, _ in folders.iter_nodes(current.tree)}
        ObligationFolderRule.objects.filter(organization=office).exclude(node_id__in=live).update(
            enabled=False
        )
    elif action == "rule_save":
        rule_form = RuleForm(request.POST)
        if not rule_form.is_valid():
            raise ValidationError("Revise os campos.")
        current = folders.ensure_model(office)
        folders.find_node(current.tree, rule_form.cleaned_data["node"])
        doc = DocumentType.objects.filter(
            organization=office, pk=rule_form.cleaned_data["document_type"]
        ).first()
        if doc is None:
            raise ValidationError("Tipo não encontrado.")
        ObligationFolderRule.objects.update_or_create(
            organization=office,
            document_type=doc,
            kind=rule_form.cleaned_data["kind"],
            defaults={
                "node_id": rule_form.cleaned_data["node"],
                "source": ObligationFolderRule.Source.MANUAL,
                "enabled": True,
            },
        )
    elif action == "rule_remove":
        rule_id = request.POST.get("rule", "")
        if _is_uuid(rule_id):
            ObligationFolderRule.objects.filter(organization=office, pk=rule_id).delete()
    elif action == "provision":
        folders.queue_provision(office, apply=True)
    elif action == "inventory":
        folders.queue_inventory(office)
    record_event(
        action=f"triage.folders.{action}",
        actor=actor,
        organization=office,
        target=office,
        request=request,
        metadata={},
    )
    messages.success(request, "Guardado.")


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
