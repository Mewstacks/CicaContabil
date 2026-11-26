"""Exporta o HubFedrizzi para um pacote que o CICA importa. SOMENTE LEITURA.

Rodar no servidor da Fedrizzi, na pasta do HubFedrizzi, com o Python do próprio projeto:

    cd C:\\actions-runner\\_work\\HubFedrizzi\\HubFedrizzi
    .venv\\Scripts\\python.exe C:\\caminho\\export_hubfedrizzi.py --out C:\\temp\\fedrizzi-export

O que faz: abre uma transação SOMENTE LEITURA no Postgres, lê cada tabela dos apps do
HubFedrizzi e grava uma linha JSON por registro; lê as notas do MongoDB; copia (opcional)
os arquivos do MEDIA_ROOT que as tabelas referenciam. Escreve MANIFEST.json com contagem e
SHA-256 de tudo. Não altera nenhuma linha, nenhum arquivo e nenhuma configuração.

Segredos NUNCA saem: campos com nome de senha/token/chave/cifrado viram null e a tabela de
certificados exporta só metadados (o arquivo .pfx e a senha ficam no servidor).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

FORMAT_VERSION = 1
SOURCE_SYSTEM = "hubfedrizzi"
SECRET_FIELD = re.compile(
    r"(senha|password|passwd|secret|token|cifrad|encrypted|api_?key|private|pfx|credential)",
    re.IGNORECASE,
)
# Tabelas inteiras que não saem: o conteúdo é o próprio segredo.
SKIP_TABLES = {"django_session", "core_tentativalogin", "django_admin_log", "auth_permission"}
# Tabelas que saem sem o arquivo (só metadados).
NO_FILES_TABLES = {"nfse_certificado"}


def _json_default(value: object) -> object:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__b64__": base64.b64encode(bytes(value)).decode("ascii")}
    return str(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _setup_django(project_dir: Path):
    sys.path.insert(0, str(project_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    return django


def _export_tables(out: Path, files_root: Path | None, with_files: bool) -> dict:
    from django.apps import apps
    from django.db import connection, transaction
    from django.db.models import FileField

    tables: dict[str, dict] = {}
    referenced_files: dict[str, str] = {}
    data_dir = out / "tables"
    data_dir.mkdir(parents=True, exist_ok=True)

    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
        models = sorted(apps.get_models(), key=lambda m: m._meta.db_table)
        for model in models:
            table = model._meta.db_table
            if table in SKIP_TABLES or model._meta.proxy or model._meta.auto_created:
                continue
            concrete = [f for f in model._meta.concrete_fields]
            redacted = [f.attname for f in concrete if SECRET_FIELD.search(f.name)]
            file_fields = [f.attname for f in concrete if isinstance(f, FileField)]
            if table == "auth_user":
                redacted = sorted(set(redacted) | {"password"})
            target = data_dir / f"{table}.jsonl"
            count = 0
            try:
                with transaction.atomic():  # savepoint: uma tabela com erro não derruba o resto
                    queryset = model._base_manager.all().order_by("pk")
                    with target.open("w", encoding="utf-8", newline="\n") as handle:
                        for row in queryset.values(*[f.attname for f in concrete]).iterator(
                            chunk_size=500
                        ):
                            for name in redacted:
                                if name in row:
                                    row[name] = None
                            for name in file_fields:
                                relative = row.get(name)
                                if relative and with_files and table not in NO_FILES_TABLES:
                                    referenced_files[str(relative)] = table
                                if table in NO_FILES_TABLES:
                                    row[name] = None
                            handle.write(
                                json.dumps(
                                    {"pk": str(row.get(model._meta.pk.attname)), "row": row},
                                    default=_json_default,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                            count += 1
            except Exception as exc:
                tables[table] = {
                    "model": model._meta.label,
                    "rows": 0,
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                }
                continue
            tables[table] = {
                "model": model._meta.label,
                "rows": count,
                "sha256": _sha256_file(target),
                "redacted_fields": redacted,
                "file_fields": file_fields,
            }
    return {"tables": tables, "files": referenced_files}


def _export_mongo(out: Path) -> dict:
    from django.conf import settings

    cfg = getattr(settings, "MONGO", None)
    if not cfg:
        return {"status": "sem_configuracao"}
    try:
        from pymongo import MongoClient
    except ImportError:
        return {"status": "pymongo_ausente"}
    client = MongoClient(cfg["URI"], serverSelectionTimeoutMS=8000)
    try:
        collection = client[cfg["DB"]][cfg["COLLECTION_NFSE"]]
        target = out / "mongo_nfse.jsonl"
        count = 0
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            for document in collection.find({}, no_cursor_timeout=False).sort("_id", 1):
                document["_id"] = str(document["_id"])
                handle.write(
                    json.dumps(
                        {"pk": document["_id"], "row": document},
                        default=_json_default,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                count += 1
        return {"status": "ok", "rows": count, "sha256": _sha256_file(target)}
    except Exception as exc:
        return {"status": "erro", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    finally:
        client.close()


def _copy_files(out: Path, files_root: Path, referenced: dict[str, str]) -> dict:
    files_dir = out / "files"
    entries: dict[str, dict] = {}
    missing = 0
    root = files_root.resolve()
    for relative in sorted(referenced):
        source = (root / relative).resolve()
        if root not in source.parents or not source.is_file():
            missing += 1
            continue
        destination = files_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        entries[relative] = {"sha256": _sha256_file(destination), "size": source.stat().st_size}
    return {"count": len(entries), "missing": missing, "items": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="pasta de saída (será criada)")
    parser.add_argument("--project", default=".", help="pasta do HubFedrizzi (padrão: atual)")
    parser.add_argument("--no-files", action="store_true", help="não copiar arquivos")
    parser.add_argument("--no-mongo", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        print(f"Pasta de saída não está vazia: {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    _setup_django(project_dir)
    from django.conf import settings

    started = datetime.now().isoformat(timespec="seconds")
    exported = _export_tables(out, None, with_files=not args.no_files)
    mongo = {"status": "ignorado"} if args.no_mongo else _export_mongo(out)
    media_root = Path(str(getattr(settings, "MEDIA_ROOT", "") or project_dir / "media_protegida"))
    files = (
        {"count": 0, "missing": 0, "items": {}}
        if args.no_files or not media_root.exists()
        else _copy_files(out, media_root, exported["files"])
    )
    manifest = {
        "format_version": FORMAT_VERSION,
        "source_system": SOURCE_SYSTEM,
        "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "tables": exported["tables"],
        "mongo_nfse": mongo,
        "files": {"count": files["count"], "missing": files["missing"], "items": files["items"]},
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    bundle = out.with_suffix(".zip")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(out).as_posix())
    total = sum(item["rows"] for item in exported["tables"].values())
    print(f"Tabelas: {len(exported['tables'])} | linhas: {total}")
    print(f"Mongo NFS-e: {mongo.get('status')} {mongo.get('rows', '')}")
    print(f"Arquivos copiados: {files['count']} (faltando: {files['missing']})")
    print(f"Pacote: {bundle}")
    print(f"SHA-256: {_sha256_file(bundle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
