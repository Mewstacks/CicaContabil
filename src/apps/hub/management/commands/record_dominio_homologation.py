"""Record the office's Domínio import test as export homologation (D-380).

Run only after the office imported the preview file in its own Domínio and
confirmed the result. Without ``--apply`` it only shows what would be recorded.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.hub.accounting_import import (
    ImportReceiptError,
    export_homologated,
    record_export_homologation,
)
from apps.hub.accounting_preview import open_preview_content
from apps.hub.models import AccountingExport, AccountingExportPreview
from apps.hub.reconciliation_service import get_accounting_export_adapter

NAMESPACE = uuid.UUID("5b0d7a1e-38f4-4c6e-9d0b-380d380d3800")


class Command(BaseCommand):
    help = "Registra (ou revoga) a homologação Domínio a partir de uma prévia importada."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--organization", required=True, type=uuid.UUID, help="UUID do escritório."
        )
        parser.add_argument("--preview", required=True, help="ID da prévia importada no Domínio.")
        parser.add_argument(
            "--importer-version", required=True, help="Versão do Domínio onde foi importada."
        )
        parser.add_argument(
            "--decision",
            required=True,
            help="Quem confirmou a importação, quando e onde está a evidência.",
        )
        parser.add_argument("--revoke", action="store_true")
        parser.add_argument(
            "--allow-direct-use",
            action="store_true",
            help="Confirma homologação real em escritório de uso direto (D-397).",
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        adapter = get_accounting_export_adapter(AccountingExport.Target.DOMINIO)
        try:
            preview = AccountingExportPreview.objects.select_related("organization").get(
                pk=options["preview"], organization_id=options["organization"]
            )
        except (AccountingExportPreview.DoesNotExist, ValueError) as exc:
            raise CommandError("Prévia não encontrada neste escritório.") from exc
        if preview.adapter_version != adapter.version:
            raise CommandError(
                f"A prévia usa {preview.adapter_version}; o adaptador atual é {adapter.version}."
            )
        try:
            with open_preview_content(preview) as stream:
                content = stream.read()
        except Exception as exc:
            raise CommandError("Arquivo da prévia indisponível; nada foi registrado.") from exc
        artifact = hashlib.sha256(content).hexdigest()
        if artifact != preview.content_hash:
            raise CommandError("O arquivo da prévia diverge do hash; nada foi registrado.")
        approved = not options["revoke"]
        evidence = {
            "preview_id": str(preview.pk),
            "company_id": str(preview.company_id),
            "period": [preview.period_start.isoformat(), preview.period_end.isoformat()],
            "artifact_sha256": artifact,
            "importer_version": options["importer_version"],
            "decision": options["decision"],
            "approved": approved,
        }
        canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()
        evidence_sha = hashlib.sha256(canonical).hexdigest()
        request_key = uuid.uuid5(NAMESPACE, evidence_sha)
        summary = {
            "organization": str(preview.organization_id),
            "adapter_version": adapter.version,
            "approved": approved,
            "preview": str(preview.pk),
            "artifact_sha256": artifact,
            "evidence_sha256": evidence_sha,
            "request_key": str(request_key),
            "homologated_before": export_homologated(
                preview.organization, adapter.target, adapter.version
            ),
            "applied": False,
        }
        if options["apply"]:
            from apps.hub.direct_use import direct_use_enabled

            if (
                approved
                and direct_use_enabled(preview.organization)
                and not options["allow_direct_use"]
            ):
                raise CommandError(
                    "Escritório em uso direto (D-393) exporta sem homologação; registre só uma "
                    "importação real conferida, com --allow-direct-use. Nada foi registrado."
                )
            try:
                _, created = record_export_homologation(
                    organization=preview.organization,
                    target=adapter.target,
                    adapter_version=adapter.version,
                    request_key=request_key,
                    approved=approved,
                    evidence_reference=f"Prévia {preview.pk} importada no Domínio",
                    evidence_sha256=evidence_sha,
                    artifact_sha256=artifact,
                    importer_version=options["importer_version"],
                    human_decision_reference=options["decision"],
                )
            except ImportReceiptError as exc:
                raise CommandError(str(exc)) from exc
            summary.update(
                applied=True,
                created=created,
                homologated_after=export_homologated(
                    preview.organization, adapter.target, adapter.version
                ),
            )
        self.stdout.write(json.dumps(summary, ensure_ascii=False, sort_keys=True))
