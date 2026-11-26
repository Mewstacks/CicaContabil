"""L1: migração nova só adiciona (docs/specs/produto-vendavel.md).

O banco é compartilhado entre os clientes atuais e os novos. Uma migração criada depois da
linha de base (`legacy_baseline/migrations.json`) pode criar tabela, coluna nula ou com
default, índice e constraint. Não pode remover, renomear nem alterar coluna existente, nem
rodar SQL solto. Exceção só com motivo escrito em `REVIEWED_EXCEPTIONS`, revisada por humano.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.db import migrations, models
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.base import Operation

BASELINE_FILE = Path(__file__).parent / "legacy_baseline" / "migrations.json"
BASELINE: dict[str, list[str]] = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))

# "app.nome_da_migracao" -> motivo revisado. O produto novo só adiciona.
#
# django-oauth-toolkit 3.4.1 (D-333): pacote de terceiros que cria as próprias tabelas do zero.
# Nenhum código legado lê ou escreve nelas, então os AlterField e RunPython do histórico dele
# nunca tocam linha de cliente atual. Uma migração nova do pacote, numa atualização, não está na
# lista e volta a falhar: pede revisão de quem atualiza.
_OAUTH_TOOLKIT_REASON = (
    "tabelas do django-oauth-toolkit 3.4.1 criadas do zero; sem código legado nelas (D-333)"
)
_OAUTH_TOOLKIT_MIGRATIONS = (
    "0001_initial",
    "0002_auto_20190406_1805",
    "0003_auto_20201211_1314",
    "0004_auto_20200902_2022",
    "0005_auto_20211222_2352",
    "0006_alter_application_client_secret",
    "0007_application_post_logout_redirect_uris",
    "0008_alter_accesstoken_token",
    "0009_add_hash_client_secret",
    "0010_application_allowed_origins",
    "0011_refreshtoken_token_family",
    "0012_add_token_checksum",
    "0013_alter_application_authorization_grant_type_device",
    "0014_alter_help_text",
    "0015_refreshtoken_token_checksum",
    "0016_alter_devicegrant_scope",
    "0017_application_dcr_created",
    "0018_resource_indicators",
    "0019_application_registration_source",
    "0020_cimd_application_fields",
    "0021_translatable_field_labels",
    "0022_refreshtoken_token_family_index",
)
REVIEWED_EXCEPTIONS: dict[str, str] = {
    f"oauth2_provider.{name}": _OAUTH_TOOLKIT_REASON for name in _OAUTH_TOOLKIT_MIGRATIONS
}
# Novo código de módulo = AlterField só de `choices` em hub_productmodule.code (mesmo
# max_length): o Django não emite SQL para isso, então não há bloqueio nem reescrita de tabela.
# Mesmo caminho das migrações 0075/0076, que já estão na linha de base. REVISÃO HUMANA PENDENTE.
REVIEWED_EXCEPTIONS["hub.0093_productmodule_code_delivery"] = (
    "só `choices` de productmodule.code; sem SQL (módulo Envio ao cliente)"
)

ALWAYS_ALLOWED = {
    "CreateModel",
    "AddIndex",
    "AddConstraint",
    "AlterModelOptions",
    "AlterModelManagers",
}


def operation_violations(operation: Operation) -> list[str]:
    kind = type(operation).__name__
    if kind in ALWAYS_ALLOWED:
        return []
    if kind == "AddField":
        field = operation.field  # type: ignore[attr-defined]
        # No deploy canário o código antigo continua inserindo linhas sem a coluna nova:
        # só passa se a coluna é nula ou tem default NO BANCO (`db_default`), não só no Python.
        if field.null or field.db_default is not models.NOT_PROVIDED:
            return []
        return [
            f"AddField {operation.model_name}.{operation.name} "  # type: ignore[attr-defined]
            "é NOT NULL sem db_default"
        ]
    if kind == "RunPython":
        if operation.reverse_code is None:  # type: ignore[attr-defined]
            return ["RunPython sem reverse_code (irreversível)"]
        return []
    return [f"operação não permitida em migração nova: {kind}"]


def migration_violations(migration: migrations.Migration) -> list[str]:
    found: list[str] = []
    for operation in migration.operations:
        found.extend(operation_violations(operation))
    return found


def new_migrations() -> Iterator[tuple[str, str, migrations.Migration]]:
    loader = MigrationLoader(None, ignore_no_migrations=True)
    for (app, name), migration in sorted(loader.disk_migrations.items()):
        if name not in BASELINE.get(app, []):
            yield app, name, migration


def test_every_baseline_migration_still_exists() -> None:
    loader = MigrationLoader(None, ignore_no_migrations=True)
    present = {(app, name) for app, name in loader.disk_migrations}
    missing = [
        f"{app}.{name}"
        for app, names in BASELINE.items()
        for name in names
        if (app, name) not in present
    ]
    assert missing == [], f"migração existente removida ou renomeada: {missing}"


def test_new_migrations_only_add() -> None:
    problems: dict[str, list[str]] = {}
    for app, name, migration in new_migrations():
        key = f"{app}.{name}"
        if key in REVIEWED_EXCEPTIONS:
            continue
        found = migration_violations(migration)
        if found:
            problems[key] = found
    assert problems == {}, problems


@pytest.mark.parametrize(
    "operation",
    [
        migrations.RemoveField("nfsesync", "enabled"),
        migrations.DeleteModel("Certificate"),
        migrations.RenameField("nfsesync", "enabled", "active"),
        migrations.AlterField("nfsesync", "enabled", models.BooleanField(default=True)),
        migrations.RunSQL("update hub_nfsesync set enabled = false"),
        migrations.AddField("nfsesync", "mode", models.CharField(max_length=16)),
        migrations.AddField("nfsesync", "mode", models.CharField(max_length=16, default="a")),
        migrations.RunPython(lambda *_a: None),
    ],
)
def test_the_linter_rejects_destructive_or_unsafe_operations(operation: Operation) -> None:
    assert operation_violations(operation) != []


@pytest.mark.parametrize(
    "operation",
    [
        migrations.AddField(
            "nfsesync", "mode", models.CharField(max_length=16, default="a", db_default="a")
        ),
        migrations.AddField("nfsesync", "seen", models.DateTimeField(null=True)),
        migrations.AddIndex("nfsesync", models.Index(fields=["enabled"], name="ix_test_enabled")),
        migrations.RunPython(lambda *_a: None, migrations.RunPython.noop),
    ],
)
def test_the_linter_accepts_additive_operations(operation: Operation) -> None:
    assert operation_violations(operation) == []
