"""Import a bundle exported from a legacy system (HubFedrizzi) into ONE office.

Rules: idempotent (same bundle twice changes nothing), every row is kept verbatim in
``LegacyImportRecord`` first, native models are filled from those rows, nothing outside the
target organization is read or written, and a failure rolls the whole import back.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany, LegacyImportRecord
from apps.organizations.models import Membership, Organization

SUPPORTED_FORMAT = 1
SECRET_KEY = re.compile(
    r"(senha|password|passwd|secret|token|cifrad|encrypted|api_?key|private|pfx|credential)",
    re.IGNORECASE,
)
REGIME_MAP = {
    "SIMPLES": ClientCompany.TaxRegime.SIMPLES,
    "PRESUMIDO": ClientCompany.TaxRegime.PRESUMIDO,
    "REAL": ClientCompany.TaxRegime.REAL,
    "MEI": ClientCompany.TaxRegime.MEI,
}


class BundleError(ValueError):
    """The bundle is unreadable, altered or from an unknown format."""


@dataclass
class ImportReport:
    tables: dict[str, Counter] = field(default_factory=dict)
    mapped: Counter = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    bundle_sha256: str = ""

    def table(self, name: str) -> Counter:
        return self.tables.setdefault(name, Counter())

    def lines(self) -> list[str]:
        out = [f"bundle sha256: {self.bundle_sha256}"]
        for name in sorted(self.tables):
            c = self.tables[name]
            out.append(
                f"{name}: lidas={c['read']} novas={c['created']} "
                f"atualizadas={c['updated']} iguais={c['same']}"
            )
        for key in sorted(self.mapped):
            out.append(f"nativo {key}: {self.mapped[key]}")
        out.extend(f"AVISO {w}" for w in self.warnings)
        return out


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scrub(value: Any) -> Any:
    """Defense in depth: a secret that slipped past the exporter never lands in the DB."""
    if isinstance(value, dict):
        return {
            key: (None if SECRET_KEY.search(str(key)) else _scrub(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


class Bundle:
    """Read-only view of an export zip or folder, with every checksum verified up front."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._zip = zipfile.ZipFile(path) if path.is_file() else None
        try:
            self.manifest = json.loads(self._read("MANIFEST.json").decode("utf-8"))
        except (KeyError, FileNotFoundError, ValueError) as exc:
            raise BundleError("MANIFEST.json ausente ou ilegível.") from exc
        if self.manifest.get("format_version") != SUPPORTED_FORMAT:
            raise BundleError("Formato de pacote desconhecido.")
        self.sha256 = _sha256_bytes(_canonical(self.manifest))

    def _read(self, name: str) -> bytes:
        if self._zip is not None:
            return self._zip.read(name)
        return (self.path / name).read_bytes()

    def verify(self) -> list[str]:
        problems: list[str] = []
        for table, info in self.manifest.get("tables", {}).items():
            if "error" in info:
                problems.append(f"{table}: erro na exportação ({info['error']})")
                continue
            if not info.get("rows"):
                continue
            data = self._read(f"tables/{table}.jsonl")
            if _sha256_bytes(data) != info["sha256"]:
                raise BundleError(f"{table}: checksum diferente do manifesto (pacote alterado).")
            if len(data.splitlines()) != info["rows"]:
                raise BundleError(f"{table}: contagem de linhas diferente do manifesto.")
        mongo = self.manifest.get("mongo_nfse", {})
        if mongo.get("status") == "ok" and mongo.get("rows"):
            data = self._read("mongo_nfse.jsonl")
            if _sha256_bytes(data) != mongo["sha256"]:
                raise BundleError("mongo_nfse: checksum diferente do manifesto.")
        elif mongo.get("status") not in {"ok", "ignorado"}:
            problems.append(f"mongo_nfse: {mongo.get('status')} {mongo.get('error', '')}".strip())
        return problems

    def rows(self, member: str):
        for line in self._read(member).decode("utf-8").splitlines():
            if line.strip():
                yield json.loads(line)


def _upsert_records(
    organization: Organization, bundle: Bundle, table: str, member: str, report: ImportReport
) -> None:
    counter = report.table(table)
    existing = {
        rec.source_pk: rec
        for rec in LegacyImportRecord.objects.filter(
            organization=organization, source_system="hubfedrizzi", source_table=table
        )
    }
    for item in bundle.rows(member):
        counter["read"] += 1
        pk = str(item["pk"])
        payload = _scrub(item["row"])
        digest = _sha256_bytes(_canonical(payload))
        record = existing.get(pk)
        if record is None:
            LegacyImportRecord.objects.create(
                organization=organization,
                source_system="hubfedrizzi",
                source_table=table,
                source_pk=pk,
                payload=payload,
                payload_sha256=digest,
                bundle_sha256=bundle.sha256,
            )
            counter["created"] += 1
        elif record.payload_sha256 != digest:
            record.payload = payload
            record.payload_sha256 = digest
            record.bundle_sha256 = bundle.sha256
            record.save(update_fields=["payload", "payload_sha256", "bundle_sha256", "updated_at"])
            counter["updated"] += 1
        else:
            counter["same"] += 1


def _map_companies(organization: Organization, report: ImportReport) -> None:
    rows = LegacyImportRecord.objects.filter(
        organization=organization, source_system="hubfedrizzi", source_table="core_empresa"
    )
    for record in rows:
        data = record.payload
        code = str(data.get("codigo") or "").strip()
        if not code:
            report.warnings.append(f"core_empresa pk={record.source_pk}: sem código; só guardada")
            continue
        regime = REGIME_MAP.get(str(data.get("regime") or "").upper(), "outro")
        values = {
            "name": str(data.get("nome") or code)[:180],
            "cnpj_masked": str(data.get("cnpj") or "")[:18],
            "active": bool(data.get("ativa", True)),
            "tax_regime": regime,
            "state_registration": str(data.get("inscricao_estadual") or "")[:30],
            "municipal_registration": str(data.get("inscricao_municipal") or "")[:30],
            "contact_email": str(data.get("email_cliente") or "")[:254],
            "contact_phone": str(data.get("telefone") or "")[:30],
            "external_key": f"hubfedrizzi:{record.source_pk}"[:160],
        }
        company = ClientCompany.objects.filter(organization=organization, dominio_code=code).first()
        if company is None:
            company = ClientCompany(organization=organization, dominio_code=code, **values)
            company.save()
            report.mapped["empresas criadas"] += 1
        else:
            changed = [k for k, v in values.items() if getattr(company, k) != v]
            # Conservative: never overwrite what the office already corrected in CICA.
            blanks = [k for k in changed if not getattr(company, k)]
            for key in blanks:
                setattr(company, key, values[key])
            if blanks:
                company.save()
                report.mapped["empresas completadas"] += 1
            else:
                report.mapped["empresas iguais"] += 1
        if record.mapped_to != f"hub.ClientCompany:{company.pk}":
            record.mapped_to = f"hub.ClientCompany:{company.pk}"
            record.save(update_fields=["mapped_to", "updated_at"])


def _map_users(organization: Organization, report: ImportReport) -> None:
    rows = LegacyImportRecord.objects.filter(
        organization=organization, source_system="hubfedrizzi", source_table="auth_user"
    )
    for record in rows:
        data = record.payload
        email = str(data.get("email") or "").strip().casefold()
        if not email or not data.get("is_active", True):
            report.mapped["usuários ignorados (sem e-mail ou inativos)"] += 1
            continue
        user = User.objects.filter(email=email).first()
        if user is None:
            full = f"{data.get('first_name') or ''} {data.get('last_name') or ''}".strip()
            user = User(email=email, full_name=full[:150])
            user.set_unusable_password()
            user.save()
            report.mapped["usuários criados (sem senha)"] += 1
        role = Membership.Role.ADMIN if data.get("is_superuser") else Membership.Role.OPERATOR
        _, made = Membership.objects.get_or_create(
            organization=organization, user=user, defaults={"role": role, "is_active": True}
        )
        report.mapped["vínculos criados" if made else "vínculos existentes"] += 1


def import_bundle(
    *, organization: Organization, path: Path, dry_run: bool = False, with_users: bool = False
) -> ImportReport:
    bundle = Bundle(path)
    report = ImportReport(bundle_sha256=bundle.sha256)
    report.warnings.extend(bundle.verify())
    with transaction.atomic():
        for table, info in sorted(bundle.manifest["tables"].items()):
            if info.get("rows") and "error" not in info:
                _upsert_records(organization, bundle, table, f"tables/{table}.jsonl", report)
        mongo = bundle.manifest.get("mongo_nfse", {})
        if mongo.get("status") == "ok" and mongo.get("rows"):
            _upsert_records(organization, bundle, "mongo_nfse", "mongo_nfse.jsonl", report)
        _map_companies(organization, report)
        if with_users:
            _map_users(organization, report)
        record_event(
            action="hub.legacy_import.applied" if not dry_run else "hub.legacy_import.dry_run",
            organization=organization,
            metadata={
                "bundle_sha256": bundle.sha256,
                "tables": {k: dict(v) for k, v in report.tables.items()},
                "mapped": dict(report.mapped),
            },
        )
        if dry_run:
            transaction.set_rollback(True)
    return report
