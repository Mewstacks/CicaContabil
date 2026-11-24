"""Fotografia somente leitura do que os clientes atuais têm (L4 de docs/specs/produto-vendavel.md).

Rodada antes e depois de um deploy, `--compare` prova que nenhuma organização existente
perdeu linha, mudou configuração ou teve coluna alterada. Só faz SELECT e consulta ao
catálogo do banco; não grava nada, não imprime nome, CNPJ nem conteúdo fiscal (apenas slug,
contagens e nomes de coluna).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import DatabaseError, connections, router, transaction

from apps.hub.models import (
    Certificate,
    ClientCompany,
    NfseDocument,
    NfseSync,
    OfficeProfile,
    ProductModule,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantLifecycle

SNAPSHOT_VERSION = 1


def _project_models() -> list[Any]:
    found = []
    for model in apps.get_models():
        if not model.__module__.startswith("apps."):
            continue
        if router.db_for_read(model) != "default":
            continue
        found.append(model)
    return sorted(found, key=lambda item: item._meta.db_table)


def _schema() -> dict[str, list[str]]:
    """Colunas como o Django as define (tipo e nulidade). Não lê o catálogo do banco: o
    estado do banco é função das migrações, e assim o comando roda igual em SQLite e
    PostgreSQL e continua válido antes de uma coluna nova existir."""

    connection = connections["default"]
    return {
        model._meta.db_table: sorted(
            f"{field.column}:{field.db_type(connection)}:{'null' if field.null else 'notnull'}"
            for field in model._meta.local_concrete_fields
        )
        for model in _project_models()
    }


def _row_counts() -> dict[str, int]:
    """Rows per table. A table the database does not have yet (a model newer than the
    last applied migration) is left out instead of failing the whole snapshot."""

    counts: dict[str, int] = {}
    for model in _project_models():
        try:
            with transaction.atomic():
                counts[model._meta.db_table] = model._default_manager.count()
        except DatabaseError:
            continue
    return counts


PROFILE_LEGACY_FIELDS = ("contract_status", "require_mfa", "require_dominio_code")


def _profile_config(organization: Organization) -> dict[str, Any]:
    """Lê só colunas escolhidas, sem carregar a linha inteira: assim o comando roda também
    contra um banco ao qual a migração mais nova ainda não foi aplicada."""

    query = OfficeProfile.objects.filter(organization=organization)
    config: dict[str, Any] = dict.fromkeys(PROFILE_LEGACY_FIELDS)
    row = query.values(*PROFILE_LEGACY_FIELDS).first()
    if row is not None:
        config.update(row)
    # O modo nasceu com a coleta por procuração; antes disso todo escritório era legado.
    config["nfse_collection_mode"] = "certificate"
    if any(field.name == "nfse_collection_mode" for field in OfficeProfile._meta.fields):
        try:
            with transaction.atomic():
                value = query.values_list("nfse_collection_mode", flat=True).first()
        except DatabaseError:
            value = None
        if value:
            config["nfse_collection_mode"] = value
    return config


def _organization(organization: Organization) -> dict[str, Any]:
    lifecycle_state = (
        TenantLifecycle.objects.filter(organization=organization)
        .values_list("state", flat=True)
        .first()
    )
    modules = sorted(
        ProductModule.objects.filter(organization=organization, enabled=True).values_list(
            "code", flat=True
        )
    )
    syncs = NfseSync.objects.filter(organization=organization)
    config: dict[str, Any] = {
        "is_active": organization.is_active,
        "is_demo": organization.is_demo,
        "is_internal_test_partner": organization.is_internal_test_partner,
        "modules": modules,
        "lifecycle_state": lifecycle_state,
        **_profile_config(organization),
    }
    counts: dict[str, int] = {
        "memberships": Membership.objects.filter(organization=organization).count(),
        "companies": ClientCompany.objects.filter(organization=organization).count(),
        "companies_active": ClientCompany.objects.filter(
            organization=organization, active=True
        ).count(),
        "certificates": Certificate.objects.filter(organization=organization).count(),
        "nfse_syncs": syncs.count(),
        "nfse_syncs_enabled": syncs.filter(enabled=True).count(),
        "nfse_documents": NfseDocument.objects.filter(organization=organization).count(),
    }
    return {"config": config, "counts": counts}


def take_snapshot() -> dict[str, Any]:
    return {
        "version": SNAPSHOT_VERSION,
        "taken_at": datetime.now(UTC).isoformat(),
        "organizations": {
            organization.slug: _organization(organization)
            for organization in Organization.objects.order_by("slug")
        },
        "table_rows": _row_counts(),
        "schema": _schema(),
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Violações de `after` em relação a `before`. Vazio quando nada do legado mudou."""

    problems: list[str] = []
    if before.get("version") != after.get("version"):
        return [
            f"versão da fotografia diferente: {before.get('version')} vs {after.get('version')}"
        ]
    for slug, old in before["organizations"].items():
        new = after["organizations"].get(slug)
        if new is None:
            problems.append(f"organização {slug}: desapareceu")
            continue
        for key, value in old["config"].items():
            if new["config"].get(key) != value:
                problems.append(
                    f"organização {slug}: configuração {key} mudou de {value!r} "
                    f"para {new['config'].get(key)!r}"
                )
        for key, value in old["counts"].items():
            if new["counts"].get(key, 0) < value:
                problems.append(
                    f"organização {slug}: contagem {key} caiu de {value} "
                    f"para {new['counts'].get(key, 0)}"
                )
    for table, count in before["table_rows"].items():
        remaining = after["table_rows"].get(table, 0)
        if remaining < count:
            problems.append(f"tabela {table}: linhas caíram de {count} para {remaining}")
    for table, columns in before["schema"].items():
        current = set(after["schema"].get(table, []))
        if table not in after["schema"]:
            problems.append(f"tabela {table}: removida")
            continue
        for column in columns:
            if column not in current:
                problems.append(f"tabela {table}: coluna alterada ou removida ({column})")
    return problems


class Command(BaseCommand):
    help = (
        "Fotografia somente leitura das organizações existentes. Sem argumento imprime o JSON; "
        "--compare ANTES DEPOIS sai com erro se algo do legado mudou."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--output", help="Arquivo de saída (JSON).")
        parser.add_argument(
            "--compare", nargs=2, metavar=("ANTES", "DEPOIS"), help="Compara duas fotografias."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["compare"]:
            before_path, after_path = (Path(item) for item in options["compare"])
            before = json.loads(before_path.read_text(encoding="utf-8"))
            after = json.loads(after_path.read_text(encoding="utf-8"))
            problems = compare_snapshots(before, after)
            if problems:
                for problem in problems:
                    self.stderr.write(problem)
                raise CommandError(f"{len(problems)} violação(ões) do legado.")
            self.stdout.write("legado idêntico: nenhuma violação.")
            return
        payload = json.dumps(take_snapshot(), indent=2, sort_keys=True, ensure_ascii=False)
        if options["output"]:
            Path(options["output"]).write_text(payload + "\n", encoding="utf-8")
            self.stdout.write(f"fotografia gravada em {options['output']}")
        else:
            self.stdout.write(payload)
