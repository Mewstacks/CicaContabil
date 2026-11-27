"""Arquivos do pacote do HubFedrizzi: hash conferido, ligados ao registro nativo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from tests.test_legacy_convert_django import empresa, make_bundle

from apps.closing.models import ClosingDocument
from apps.fap.models import FapItem
from apps.hub.legacy_files import import_files
from apps.hub.legacy_import import import_bundle
from apps.organizations.models import Organization
from apps.rpa.models import RpaArtifact

pytestmark = pytest.mark.django_db

RECEIPT = b"%PDF recibo"
FAP = b"%PDF fap"
SHA_RECEIPT = hashlib.sha256(RECEIPT).hexdigest()
SHA_FAP = hashlib.sha256(FAP).hexdigest()

TABLES: dict[str, list[dict[str, Any]]] = {
    "core_empresa": [empresa(1, "0001", "Alfa", "11.222.333/0001-81")],
    "fechamento_recibo": [
        {
            "id": 1,
            "empresa_id": 1,
            "ano": 2026,
            "mes": 8,
            "nome_original": "a.pdf",
            "arquivo": "recibos/a.pdf",
            "hash_arquivo": SHA_RECEIPT,
            "parseado_ok": True,
        },
        {
            "id": 2,
            "empresa_id": 1,
            "ano": 2026,
            "mes": 9,
            "nome_original": "b.pdf",
            "arquivo": "recibos/b.pdf",
            "hash_arquivo": "f" * 64,
            "parseado_ok": True,
        },
    ],
    "fap_lotefap": [{"id": 1, "ano": 2027, "estado": "concluido"}],
    "fap_itemfap": [
        {
            "id": 1,
            "lote_id": 1,
            "empresa_id": 1,
            "codigo_dominio": "2",
            "estado": "concluido",
            "pdf": "fap/1/1/x.pdf",
            "sha256_pdf": SHA_FAP,
        },
        {
            "id": 2,
            "lote_id": 1,
            "empresa_id": 1,
            "codigo_dominio": "3",
            "estado": "concluido",
            "pdf": "fap/1/2/y.pdf",
            "sha256_pdf": SHA_FAP,
        },
    ],
}
FILES = {
    "recibos/a.pdf": RECEIPT,
    "recibos/b.pdf": b"adulterado",
    "fap/1/1/x.pdf": FAP,
    "fap/1/2/y.pdf": FAP,
    "triagem/quarentena/u/z.pdf": b"t",
    "mapeamentos/m.pdf": b"m",
}


def build(root: Path) -> Path:
    bundle = make_bundle(root, TABLES)
    manifest = json.loads((bundle / "MANIFEST.json").read_text(encoding="utf-8"))
    items = {}
    for name, data in FILES.items():
        target = bundle / "files" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        # o manifesto traz o hash do que o exportador leu; "adulterado" foi trocado depois
        digest = hashlib.sha256(b"original" if name == "recibos/b.pdf" else data).hexdigest()
        items[name] = {"sha256": digest, "size": len(data)}
    manifest["files"] = {"count": len(items), "items": items}
    (bundle / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


@pytest.fixture
def office(settings, tmp_path) -> Organization:
    settings.MEDIA_ROOT = tmp_path / "media"
    return Organization.objects.create(name="Fedrizzi", slug="fedrizzi-contabilidade")


def test_files_are_stored_by_hash_and_tied_to_native_rows(office, tmp_path):
    bundle = build(tmp_path / "b")
    import_bundle(organization=office, path=bundle)
    report = import_files(organization=office, path=bundle)
    assert report.stored["recibos"] == 1 and report.stored["FAP"] == 2
    assert report.skipped["hash diferente do manifesto ou do registro"] == 1
    assert report.no_home["binário de item de triagem (os itens não foram importados)"] == 1
    assert any("paridade arquivos: pacote=6 ligados=3" in x for x in report.lines())

    document = ClosingDocument.objects.get(organization=office, original_name="a.pdf")
    assert document.file.read() == RECEIPT and document.byte_size == len(RECEIPT)
    assert not ClosingDocument.objects.get(original_name="b.pdf").file
    items = list(FapItem.objects.filter(organization=office).order_by("code"))
    assert items[0].pdf is not None and items[0].pdf == items[1].pdf  # mesmo PDF, um artefato
    assert items[0].pdf.file.read() == FAP and items[0].sha256 == SHA_FAP
    assert RpaArtifact.objects.filter(organization=office).count() == 1
    assert items[0].pdf.job.state == "succeeded" and items[0].pdf.job.kind == "legacy.fap.import"


def test_second_run_and_dry_run_change_nothing(office, tmp_path):
    bundle = build(tmp_path / "b")
    import_bundle(organization=office, path=bundle)
    dry = import_files(organization=office, path=bundle, dry_run=True)
    assert dry.stored["recibos"] == 1 and not RpaArtifact.objects.exists()
    assert not ClosingDocument.objects.get(original_name="a.pdf").file
    import_files(organization=office, path=bundle)
    again = import_files(organization=office, path=bundle)
    assert not again.stored and again.existing["recibos"] == 1 and again.existing["FAP"] == 2
    assert RpaArtifact.objects.count() == 1


def test_requires_the_records_first_and_never_crosses_offices(office, tmp_path):
    bundle = build(tmp_path / "b")
    empty = import_files(organization=office, path=bundle)
    assert not empty.stored and sum(empty.skipped.values()) == 6
    other = Organization.objects.create(name="Outro", slug="outro")
    import_bundle(organization=office, path=bundle)
    import_files(organization=other, path=bundle)
    assert not ClosingDocument.objects.filter(organization=other).exists()
    assert not RpaArtifact.objects.filter(organization=other).exists()
