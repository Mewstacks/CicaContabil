"""Synthetic export permission, never evidence for a real office or import."""

from uuid import uuid4

from apps.hub.accounting_import import record_export_homologation
from apps.hub.models import ProductModule
from apps.hub.reconciliation_service import get_accounting_export_adapter
from apps.platform.models import TenantContract


def homologate_synthetic(organization, **overrides):
    if not TenantContract.objects.filter(organization=organization).exists():
        TenantContract.objects.create(
            organization=organization, status="active", selected_modules=["reconciliation"],
        )
    ProductModule.objects.get_or_create(
        organization=organization,
        code="reconciliation",
        defaults={"enabled": True},
    )
    options = dict(
        organization=organization,
        target="dominio",
        adapter_version=get_accounting_export_adapter("dominio").version,
        request_key=uuid4(),
        approved=True,
        evidence_reference="SYNTHETIC TEST ONLY / no ERP import",
        evidence_sha256="1" * 64,
        artifact_sha256="2" * 64,
        importer_version="SYNTHETIC-NONPRODUCTION",
        human_decision_reference="SYNTHETIC TEST FIXTURE / not a human approval",
    )
    options.update(overrides)
    return record_export_homologation(**options)
