"""Safety gate for semantic packages before data enters the private mirror."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.audit.services import record_event
from apps.intelligence.models import DataCatalogEntry, DominioSchemaObject, SemanticPackage

MAX_PACKAGE_ROWS = 1_000
MAX_PACKAGE_PERIOD_DAYS = 366
MAX_PACKAGE_STALENESS_SECONDS = 7 * 86_400
MAX_DEPENDENCIES = 20
MAX_CARD_FIELDS = 5


@dataclass(frozen=True)
class PackageValidation:
    valid: bool
    reason: str


def _fields_from_dependencies(package: SemanticPackage) -> tuple[set[str], str | None]:
    dependencies = package.schema_dependencies
    if not isinstance(dependencies, list) or not 1 <= len(dependencies) <= MAX_DEPENDENCIES:
        return set(), "Pacote precisa declarar entre uma e vinte dependências de schema."
    all_fields: set[str] = set()
    seen: set[tuple[str, str, str]] = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            return set(), "Dependência de schema inválida."
        schema_name = dependency.get("schema_name", "")
        object_name = dependency.get("object_name")
        object_kind = dependency.get("object_kind")
        declared_columns = dependency.get("columns")
        if not all(
            isinstance(value, str) and value for value in (schema_name, object_name, object_kind)
        ):
            return set(), "Dependência de schema incompleta."
        if (
            not isinstance(declared_columns, list)
            or not declared_columns
            or len(declared_columns) > 80
        ):
            return set(), "Dependência sem colunas aprovadas."
        columns = {column for column in declared_columns if isinstance(column, str) and column}
        if len(columns) != len(declared_columns):
            return set(), "Coluna de dependência inválida."
        assert isinstance(schema_name, str)
        assert isinstance(object_name, str)
        assert isinstance(object_kind, str)
        identity: tuple[str, str, str] = (schema_name, object_name, object_kind)
        if identity in seen:
            return set(), "Dependência de schema repetida."
        seen.add(identity)
        schema_object = DominioSchemaObject.objects.filter(
            organization=package.organization,
            schema_name=schema_name,
            object_name=object_name,
            object_kind=object_kind,
            approved_for_package=True,
        ).first()
        if schema_object is None:
            return set(), "Dependência não aprovada no catálogo Domínio."
        if schema_object.sensitivity == DataCatalogEntry.Sensitivity.EXCLUDED:
            return set(), "Dependência contém dados excluídos por política."
        known_columns = {
            str(column.get("name"))
            for column in schema_object.columns
            if isinstance(column, dict) and isinstance(column.get("name"), str)
        }
        if not columns.issubset(known_columns):
            return set(), "Pacote declara coluna ausente do schema aprovado."
        all_fields.update(columns)
    return all_fields, None


def validate_semantic_package(package: SemanticPackage) -> PackageValidation:
    """Return a bounded, non-SQL business package decision for mirror/chat use."""
    if not package.tool_name or not package.query_name:
        return PackageValidation(False, "Pacote precisa ter ferramenta e consulta registrada.")
    if not 1 <= package.max_rows <= MAX_PACKAGE_ROWS:
        return PackageValidation(False, "Limite de linhas do pacote inválido.")
    if not 1 <= package.max_period_days <= MAX_PACKAGE_PERIOD_DAYS:
        return PackageValidation(False, "Período máximo do pacote inválido.")
    if not 1 <= package.max_staleness_seconds <= MAX_PACKAGE_STALENESS_SECONDS:
        return PackageValidation(False, "Janela de atualização do pacote inválida.")
    fields, error = _fields_from_dependencies(package)
    if error:
        return PackageValidation(False, error)
    specification = package.test_specification
    if not isinstance(specification, dict):
        return PackageValidation(False, "Especificação de teste inválida.")
    card_fields = specification.get("card_fields", [])
    if not isinstance(card_fields, list) or len(card_fields) > MAX_CARD_FIELDS:
        return PackageValidation(False, "Campos de evidência inválidos.")
    exposed = {field for field in card_fields if isinstance(field, str) and field}
    if len(exposed) != len(card_fields):
        return PackageValidation(False, "Campo de evidência inválido.")
    required = {package.company_key, package.primary_key, *exposed}
    if not required.issubset(fields):
        return PackageValidation(False, "Pacote expõe campo não aprovado no schema.")
    return PackageValidation(True, "Pacote validado contra o catálogo aprovado.")


def semantic_package_ready(package: SemanticPackage) -> bool:
    return package.enabled and validate_semantic_package(package).valid


def activate_semantic_package(
    *, package: SemanticPackage, actor: object = None, request: object = None
) -> PackageValidation:
    """The only supported activation path; direct ODBC sync rechecks the same gate."""
    with transaction.atomic():
        package = SemanticPackage.objects.select_for_update().get(id=package.id)
        validation = validate_semantic_package(package)
        if not validation.valid:
            return validation
        package.enabled = True
        package.save(update_fields=["enabled", "updated_at"])
    record_event(
        action="intelligence.semantic_package.activated",
        actor=actor,
        organization=package.organization,
        target=package,
        request=request,
        metadata={"tool_name": package.tool_name, "query_name": package.query_name},
    )
    return validation
