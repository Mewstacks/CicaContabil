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
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.legacy_convert import (
    Stats,
    assign_responsible,
    convert_all,
    parity_lines,
)
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
    tables: dict[str, Counter[str]] = field(default_factory=dict)
    mapped: Counter[str] = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    parity: list[str] = field(default_factory=list)
    bundle_sha256: str = ""

    def table(self, name: str) -> Counter[str]:
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
        out.extend(self.parity)
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

    def read_bytes(self, name: str) -> bytes:
        """One whole member; for small files only (the big tables are streamed by ``rows``)."""
        return self._read(name)

    def _open(self, name: str) -> IO[bytes]:
        """Binary stream of one member; never loads a big table into memory."""
        if self._zip is not None:
            return self._zip.open(name)
        return (self.path / name).open("rb")

    def _sha256_member(self, name: str) -> tuple[str, int]:
        digest = hashlib.sha256()
        lines = 0
        with self._open(name) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                lines += chunk.count(b"\n")
        return digest.hexdigest(), lines

    def verify(self) -> list[str]:
        problems: list[str] = []
        for table, info in self.manifest.get("tables", {}).items():
            if "error" in info:
                problems.append(f"{table}: erro na exportação ({info['error']})")
                continue
            if not info.get("rows"):
                continue
            digest, lines = self._sha256_member(f"tables/{table}.jsonl")
            if digest != info["sha256"]:
                raise BundleError(f"{table}: checksum diferente do manifesto (pacote alterado).")
            if lines != info["rows"]:
                raise BundleError(f"{table}: contagem de linhas diferente do manifesto.")
        mongo = self.manifest.get("mongo_nfse", {})
        if mongo.get("status") == "ok" and mongo.get("rows"):
            digest, _lines = self._sha256_member("mongo_nfse.jsonl")
            if digest != mongo["sha256"]:
                raise BundleError("mongo_nfse: checksum diferente do manifesto.")
        elif mongo.get("status") not in {"ok", "ignorado"}:
            problems.append(f"mongo_nfse: {mongo.get('status')} {mongo.get('error', '')}".strip())
        return problems

    def rows(self, member: str) -> Iterator[dict[str, Any]]:
        with self._open(member) as handle:
            for raw in handle:
                if raw.strip():
                    yield json.loads(raw.decode("utf-8"))


# Tables whose XML goes straight to ``NfseDocument`` (see ``legacy_nfse``): the legacy row keeps
# its metadata but not a second copy of the XML.
XML_MOVED = {"robo_nfse_notanfse": "xml"}


def _upsert_records(
    organization: Organization, bundle: Bundle, table: str, member: str, report: ImportReport
) -> None:
    counter = report.table(table)
    # Only key + digest are loaded: a re-run over 700 MB of payloads must not fit in RAM.
    existing = {
        pk: (rec_id, digest)
        for rec_id, pk, digest in LegacyImportRecord.objects.filter(
            organization=organization, source_system="hubfedrizzi", source_table=table
        ).values_list("id", "source_pk", "payload_sha256")
    }
    for item in bundle.rows(member):
        counter["read"] += 1
        pk = str(item["pk"])
        payload = _scrub(item["row"])
        if table in XML_MOVED and isinstance(payload, dict):
            payload[XML_MOVED[table]] = None
        digest = _sha256_bytes(_canonical(payload))
        found = existing.get(pk)
        if found is None:
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
        elif found[1] != digest:
            LegacyImportRecord.objects.filter(pk=found[0]).update(
                payload=payload,
                payload_sha256=digest,
                bundle_sha256=bundle.sha256,
                updated_at=timezone.now(),
            )
            counter["updated"] += 1
        else:
            counter["same"] += 1


def _map_companies(organization: Organization, report: ImportReport, stats: Stats) -> None:
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
        release_day = data.get("dia_liberacao_email")
        release_day = release_day if isinstance(release_day, int) else None
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
            "email_release_day": release_day if release_day and 1 <= release_day <= 31 else None,
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
        assign_responsible(organization, company, str(data.get("responsavel") or ""), stats)
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
        if record.mapped_to != f"accounts.User:{user.pk}":
            record.mapped_to = f"accounts.User:{user.pk}"
            record.save(update_fields=["mapped_to", "updated_at"])


def import_bundle(
    *,
    organization: Organization,
    path: Path,
    dry_run: bool = False,
    with_users: bool = False,
    skip: frozenset[str] = frozenset(),
    convert: bool = True,
    hold_generation: bool = False,
    enable_nfse_sync: bool = False,
    activate_layouts: bool = False,
) -> ImportReport:
    bundle = Bundle(path)
    report = ImportReport(bundle_sha256=bundle.sha256)
    report.warnings.extend(bundle.verify())
    with transaction.atomic():
        for table, info in sorted(bundle.manifest["tables"].items()):
            if table in skip:
                report.warnings.append(f"{table}: pulada por pedido (continua no pacote)")
            elif info.get("rows") and "error" not in info:
                _upsert_records(organization, bundle, table, f"tables/{table}.jsonl", report)
        mongo = bundle.manifest.get("mongo_nfse", {})
        if mongo.get("status") == "ok" and mongo.get("rows"):
            report.warnings.append(
                f"mongo_nfse: {mongo['rows']} notas não são guardadas cruas; "
                "entram direto em NfseDocument pelo estágio --nfse-documents"
            )
        stats = Stats()
        _map_companies(organization, report, stats)
        if with_users:
            _map_users(organization, report)
        if convert:
            converted = convert_all(
                organization,
                hold_generation=hold_generation,
                enable_nfse_sync=enable_nfse_sync,
                activate_layouts=activate_layouts,
            )
            for key, count in converted.created.items():
                stats.created[key] += count
            for key, count in converted.reused.items():
                stats.reused[key] += count
            for table, reasons in converted.skipped.items():
                stats.skipped.setdefault(table, Counter()).update(reasons)
            stats.warnings.extend(converted.warnings)
        report.warnings.extend(stats.warnings)
        report.parity = parity_lines(organization, stats)
        record_event(
            action="hub.legacy_import.applied" if not dry_run else "hub.legacy_import.dry_run",
            organization=organization,
            metadata={
                "bundle_sha256": bundle.sha256,
                "tables": {k: dict(v) for k, v in report.tables.items()},
                "mapped": dict(report.mapped),
                "parity": report.parity,
            },
        )
        if dry_run:
            transaction.set_rollback(True)
    return report
