"""Durable financial-report exports coordinated by Django and rendered by Node."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_membership
from apps.hub.models import (
    AccountingBalanceSnapshot,
    CashScenario,
    DreMappingSet,
    FinancialReportExport,
)
from apps.hub.reporting import cash_report_snapshot, dre_report_snapshot
from apps.intelligence.reporting_client import ReportingServiceUnavailable, render_snapshot
from apps.organizations.models import Membership, Organization


class FinancialReportExportError(ValueError):
    pass


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    ).hexdigest()


def prepare_export(
    *,
    organization: Organization,
    company_id: uuid.UUID,
    resource: str,
    resource_id: uuid.UUID,
    export_format: str,
    actor: User,
    request: object | None = None,
) -> FinancialReportExport:
    if export_format not in set(FinancialReportExport.Format.values):
        raise FinancialReportExportError("Formato de relatorio invalido.")
    source: AccountingBalanceSnapshot | CashScenario | None
    if resource == FinancialReportExport.Resource.DRE:
        source = AccountingBalanceSnapshot.objects.select_related("company").filter(
            id=resource_id, organization=organization, company_id=company_id
        ).first()
        if source is None:
            raise FinancialReportExportError("Fotografia cont?bil n?o encontrada.")
        mapping = (
            DreMappingSet.objects.filter(organization=organization, is_active=True)
            .order_by("-version")
            .first()
        )
        if mapping is None:
            raise FinancialReportExportError("Nenhum mapa DRE ativo esta configurado.")
        snapshot = dre_report_snapshot(snapshot=source, mapping_set=mapping)
        filename_stem = f"dre-{source.company.name}-{source.competence:%Y-%m}"
    elif resource == FinancialReportExport.Resource.CASH:
        source = CashScenario.objects.select_related("company").filter(
            id=resource_id, organization=organization, company_id=company_id
        ).first()
        if source is None:
            raise FinancialReportExportError("Cenario de caixa nao encontrado.")
        snapshot = cash_report_snapshot(scenario=source)
        filename_stem = f"caixa-{source.company.name}-{source.reference_date:%Y-%m-%d}"
    else:
        raise FinancialReportExportError("Recurso de relatorio invalido.")

    export = FinancialReportExport.objects.create(
        organization=organization,
        company=source.company,
        requested_by=actor,
        resource=resource,
        source_id=source.id,
        export_format=export_format,
        filename_stem=slugify(filename_stem) or "relatorio-cica",
        snapshot=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        snapshot_sha256=_snapshot_hash(snapshot),
    )
    record_event(
        action="hub.financial_report.queued",
        actor=actor,
        organization=organization,
        target=export,
        request=request,
        metadata={
            "resource": resource,
            "format": export_format,
            "source_id": str(source.id),
            "snapshot_sha256": export.snapshot_sha256,
        },
    )
    return export


def _requester_still_authorized(export: FinancialReportExport) -> bool:
    membership = Membership.objects.filter(
        organization=export.organization, user=export.requested_by, is_active=True
    ).select_related("organization").first()
    if membership is None or not export.organization.is_active:
        return False
    return company_queryset_for_membership(membership).filter(id=export.company_id).exists()


def process_export(export_id: str) -> str:
    try:
        parsed_id = uuid.UUID(export_id)
    except (TypeError, ValueError, AttributeError):
        return "invalid_id"
    now = timezone.now()
    token = uuid.uuid4()
    with transaction.atomic():
        export = FinancialReportExport.objects.select_for_update().filter(id=parsed_id).first()
        if export is None:
            return "missing"
        if export.state == FinancialReportExport.State.READY:
            return "ready"
        if export.state == FinancialReportExport.State.RENDERING and (
            export.lease_until is None or export.lease_until >= now
        ):
            return "busy"
        if export.state not in {
            FinancialReportExport.State.WAITING,
            FinancialReportExport.State.RENDERING,
        }:
            return "not_waiting"
        export.state = FinancialReportExport.State.RENDERING
        export.lease_token = token
        export.lease_until = now + timedelta(minutes=6)
        export.started_at = now
        export.failure_code = ""
        export.save(
            update_fields=[
                "state", "lease_token", "lease_until", "started_at", "failure_code", "updated_at"
            ]
        )

    try:
        export = FinancialReportExport.objects.select_related(
            "organization", "company", "requested_by"
        ).get(id=parsed_id)
        if not _requester_still_authorized(export):
            FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
                state=FinancialReportExport.State.FAILED,
                failure_code="access_revoked",
                completed_at=timezone.now(),
            )
            return "access_revoked"
        try:
            snapshot = json.loads(export.snapshot)
        except (TypeError, json.JSONDecodeError):
            FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
                state=FinancialReportExport.State.FAILED,
                failure_code="invalid_snapshot",
                completed_at=timezone.now(),
            )
            return "invalid_snapshot"
        if not isinstance(snapshot, dict) or _snapshot_hash(snapshot) != export.snapshot_sha256:
            FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
                state=FinancialReportExport.State.FAILED,
                failure_code="invalid_snapshot",
                completed_at=timezone.now(),
            )
            return "invalid_snapshot"
        payload = render_snapshot(snapshot=snapshot, export_format=export.export_format)
        content_type = (
            "application/pdf"
            if export.export_format == FinancialReportExport.Format.PDF
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        with transaction.atomic():
            current = FinancialReportExport.objects.select_for_update().get(id=parsed_id)
            if current.lease_token != token:
                return "superseded"
            current.content.save(
                f"{current.filename_stem}.{current.export_format}",
                ContentFile(payload),
                save=False,
            )
            current.output_sha256 = hashlib.sha256(payload).hexdigest()
            current.content_type = content_type
            current.state = FinancialReportExport.State.READY
            current.completed_at = timezone.now()
            current.failure_code = ""
            current.save(
                update_fields=[
                    "content",
                    "output_sha256",
                    "content_type",
                    "state",
                    "completed_at",
                    "failure_code",
                    "updated_at",
                ]
            )
        record_event(
            action="hub.financial_report.rendered",
            actor=export.requested_by,
            organization=export.organization,
            target=current,
            metadata={
                "resource": current.resource,
                "format": current.export_format,
                "source_id": str(current.source_id),
                "snapshot_sha256": current.snapshot_sha256,
                "output_sha256": current.output_sha256,
            },
        )
        return "ready"
    except ReportingServiceUnavailable:
        FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
            state=FinancialReportExport.State.FAILED,
            failure_code="renderer_unavailable",
            completed_at=timezone.now(),
        )
        return "renderer_unavailable"
    except Exception:
        FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
            state=FinancialReportExport.State.FAILED,
            failure_code="unexpected",
            completed_at=timezone.now(),
        )
        return "unexpected"
    finally:
        FinancialReportExport.objects.filter(id=parsed_id, lease_token=token).update(
            lease_token=None, lease_until=None
        )
