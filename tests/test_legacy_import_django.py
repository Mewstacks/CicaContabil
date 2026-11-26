"""Importação do pacote do HubFedrizzi: idempotente, íntegra, sem segredo, sem vazar escritório."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.hub.legacy_import import BundleError, import_bundle
from apps.hub.models import ClientCompany, LegacyImportRecord
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


def make_bundle(root: Path, tables: dict[str, list[dict]], *, tamper: bool = False) -> Path:
    (root / "tables").mkdir(parents=True)
    manifest_tables = {}
    for name, rows in tables.items():
        lines = [
            json.dumps({"pk": str(r["id"]), "row": r}, sort_keys=True, ensure_ascii=False)
            for r in rows
        ]
        data = ("\n".join(lines) + "\n").encode("utf-8")
        (root / "tables" / f"{name}.jsonl").write_bytes(data)
        manifest_tables[name] = {
            "rows": len(rows),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    (root / "MANIFEST.json").write_text(
        json.dumps(
            {"format_version": 1, "tables": manifest_tables, "mongo_nfse": {"status": "ignorado"}}
        ),
        encoding="utf-8",
    )
    if tamper:
        path = root / "tables" / "core_empresa.jsonl"
        path.write_bytes(path.read_bytes().replace(b"Alfa", b"Beta"))
    return root


EMPRESAS = [
    {
        "id": 1,
        "codigo": "0001",
        "nome": "Alfa Ltda",
        "cnpj": "11.222.333/0001-81",
        "regime": "SIMPLES",
        "ativa": True,
        "inscricao_estadual": "123",
        "email_cliente": "a@alfa.test",
        "telefone": "5199",
    },
    {"id": 2, "codigo": "0002", "nome": "Beta SA", "cnpj": "", "regime": "RURAL", "ativa": False},
]
USERS = [
    {
        "id": 1,
        "email": "Ana@Fedrizzi.test",
        "first_name": "Ana",
        "last_name": "X",
        "is_active": True,
        "is_superuser": True,
        "password": "hash-vazou",
    },
    {"id": 2, "email": "inativo@fedrizzi.test", "is_active": False},
]


@pytest.fixture
def office():
    return Organization.objects.create(name="Fedrizzi", slug="fedrizzi-contabilidade")


def test_import_maps_companies_and_is_idempotent(office, tmp_path):
    bundle = make_bundle(tmp_path / "b", {"core_empresa": EMPRESAS})
    first = import_bundle(organization=office, path=bundle)
    assert first.tables["core_empresa"]["created"] == 2
    assert ClientCompany.objects.filter(organization=office).count() == 2
    alfa = ClientCompany.objects.get(organization=office, dominio_code="0001")
    assert alfa.tax_regime == "simples" and alfa.contact_email == "a@alfa.test"
    assert ClientCompany.objects.get(organization=office, dominio_code="0002").active is False
    second = import_bundle(organization=office, path=bundle)
    assert second.tables["core_empresa"]["same"] == 2
    assert LegacyImportRecord.objects.filter(organization=office).count() == 2
    assert ClientCompany.objects.filter(organization=office).count() == 2


def test_dry_run_writes_nothing(office, tmp_path):
    bundle = make_bundle(tmp_path / "b", {"core_empresa": EMPRESAS})
    report = import_bundle(organization=office, path=bundle, dry_run=True)
    assert report.tables["core_empresa"]["created"] == 2
    assert not LegacyImportRecord.objects.exists()
    assert not ClientCompany.objects.exists()


def test_tampered_bundle_is_rejected(office, tmp_path):
    bundle = make_bundle(tmp_path / "b", {"core_empresa": EMPRESAS}, tamper=True)
    with pytest.raises(BundleError):
        import_bundle(organization=office, path=bundle)
    assert not LegacyImportRecord.objects.exists()


def test_does_not_overwrite_office_corrections_and_stays_in_org(office, tmp_path):
    other = Organization.objects.create(name="Outro", slug="outro")
    ClientCompany.objects.create(organization=other, name="Alfa do outro", dominio_code="0001")
    ClientCompany.objects.create(
        organization=office, name="Alfa corrigida", dominio_code="0001", contact_email="novo@x.test"
    )
    import_bundle(organization=office, path=make_bundle(tmp_path / "b", {"core_empresa": EMPRESAS}))
    mine = ClientCompany.objects.get(organization=office, dominio_code="0001")
    assert mine.name == "Alfa corrigida" and mine.contact_email == "novo@x.test"
    assert mine.state_registration == "123"  # campo vazio foi completado
    assert ClientCompany.objects.get(organization=other).name == "Alfa do outro"
    assert not LegacyImportRecord.objects.filter(organization=other).exists()


def test_secrets_are_scrubbed_and_users_get_no_password(office, tmp_path):
    bundle = make_bundle(tmp_path / "b", {"auth_user": USERS})
    report = import_bundle(organization=office, path=bundle, with_users=True)
    record = LegacyImportRecord.objects.get(organization=office, source_pk="1")
    assert record.payload["password"] is None
    membership = Membership.objects.get(organization=office, user__email="ana@fedrizzi.test")
    assert membership.role == "admin" and not membership.user.has_usable_password()
    assert not Membership.objects.filter(user__email="inativo@fedrizzi.test").exists()
    assert report.mapped["vínculos criados"] == 1
