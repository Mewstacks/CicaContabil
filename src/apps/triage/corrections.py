"""A person corrects an already archived document: the wrong learned link is undone.

The archived bytes stay where they are (library path never moves); the record changes
company and/or type with a reason, the checklist follows, and whatever the engine had
learned from the wrong company (sender and account links, field rules born from this item)
is blocked so it cannot teach the same mistake again.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.triage import learning
from apps.triage.models import ChecklistEntry, DocumentType, TriageEvent, TriageItem
from apps.triage.services import record_checklist_delivery
from apps.triage.transitions import TriageStatus


def correct_archived(
    *,
    item: TriageItem,
    actor: User,
    reason: str,
    company: ClientCompany | None = None,
    document_type: DocumentType | None = None,
    request: object | None = None,
) -> TriageItem:
    reason = " ".join(reason.split())
    if not reason:
        raise ValidationError("Informe o motivo da correção.")
    if len(reason) > 500:
        raise ValidationError("O motivo aceita até 500 caracteres.")
    with transaction.atomic():
        item = (
            TriageItem.objects.select_for_update(of=("self",))
            .select_related("company", "document_type")
            .get(pk=item.pk, organization=item.organization)
        )
        if item.status != TriageStatus.ARCHIVED:
            raise ValidationError("Só um arquivo já arquivado pode ser corrigido aqui.")
        if company is not None and company.organization_id != item.organization_id:
            raise ValidationError("A empresa não pertence a este escritório.")
        if document_type is not None and document_type.organization_id != item.organization_id:
            raise ValidationError("O tipo de documento não pertence a este escritório.")
        wrong = item.company
        changed: list[str] = []
        if company is not None and company.pk != item.company_id:
            item.company = company
            changed.append("empresa")
        if document_type is not None and document_type.pk != item.document_type_id:
            item.document_type = document_type
            changed.append("tipo")
        if not changed:
            return item
        item.save(update_fields=["company", "document_type", "updated_at"])
        if "empresa" in changed:
            learning.undo_wrong_company(item, wrong)
        # The checklist follows the file: the proof of delivery moves to the right company.
        ChecklistEntry.objects.filter(organization=item.organization, triage_item=item).delete()
        record_checklist_delivery(item)
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            actor=actor,
            from_status=item.status,
            to_status=item.status,
            note=("Corrigido após arquivar: " + ", ".join(changed))[:500],
            reason=reason,
        )
    record_event(
        action="triage.item.corrected_after_archive",
        actor=actor,
        organization=item.organization,
        target=item,
        request=request,
        metadata={"changed": changed, "reason": reason},
    )
    return item
