"""O catálogo de consultas do ERP, fixado por hash.

Portado do Lucrums por D-281 e é o que o conector da CICA não tinha: cada consulta
vive em `contracts/datasets/`, o manifesto guarda o SHA-256 dela, e nem o agente nem
a nuvem aceitam despachar uma consulta cujo hash não confira. Uma alteração de SQL
que não passe pelo manifesto simplesmente não roda.

O arquivo é conferido na carga, não no uso: manifesto com versão errada, SQL
faltando, hash divergente, parâmetro a mais ou a menos, ponto-e-vírgula no meio ou
coluna de identidade que o SELECT não devolve derrubam a configuração inteira em vez
de falharem em silêncio num ciclo à noite.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class DatasetParameter:
    name: str
    type: str
    odbc_type: str


def catalog_key(source_system: str, code: str) -> str:
    """A chave é composta porque o mesmo código existe em mais de um ERP: o
    `companies` do Domínio e o do Siescon são contratos diferentes. A origem vem
    sempre do conector, nunca do que o cliente manda no corpo da requisição."""

    return f"{source_system}:{code}"


@dataclass(frozen=True)
class DatasetDefinition:
    code: str
    source_system: str
    schema_version: int
    sql_file: str
    query_sha256: str
    validated: bool
    parameters: tuple[DatasetParameter, ...]
    columns: tuple[dict[str, str], ...]
    identity_columns: tuple[str, ...]
    identity_mode: str
    # Colunas que o SELECT NÃO devolve e o backend preenche do contexto do run.
    # Existem porque nem toda fonte carrega, na linha, a coordenada que a linha
    # significa: no Siescon a folha mora em `S:\Dados\<NNNN>\SAEC_COL.DAT`, uma
    # pasta por empresa, e a empresa é o **diretório** — não há coluna `codi_emp`
    # para trazer. Pedir esse código ao operador a cada execução seria pedir de
    # volta uma informação que o sistema já tem: a empresa-fonte armada.
    context_columns: tuple[str, ...]
    allowed_run_kinds: tuple[str, ...]
    requires_source_role: str
    max_rows_per_run: int
    sql: str


@dataclass(frozen=True)
class DatasetCatalog:
    manifest_version: int
    definitions: dict[str, DatasetDefinition]
    manifest_sha256: str

    def get(
        self, source_system: str, code: str, schema_version: int | None = None
    ) -> DatasetDefinition:
        try:
            definition = self.definitions[catalog_key(source_system, code)]
        except KeyError as exc:
            raise ValueError("Dataset desconhecido.") from exc
        if schema_version is not None and definition.schema_version != schema_version:
            raise ValueError("Versão de dataset divergente.")
        return definition

    def get_dispatchable(
        self, source_system: str, code: str, schema_version: int
    ) -> DatasetDefinition:
        definition = self.get(source_system, code, schema_version)
        if not definition.validated:
            raise ValueError("Dataset ainda não validado em preflight.")
        return definition


def _catalog_root() -> Path:
    configured = getattr(settings, "DATASET_CATALOG_ROOT", "")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "contracts" / "datasets"


def load_catalog(root: Path | None = None) -> DatasetCatalog:
    catalog_root = root or _catalog_root()
    manifest_path = catalog_root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        payload = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ImproperlyConfigured("Catálogo de datasets indisponível ou inválido.") from exc
    if not isinstance(payload, dict) or payload.get("manifestVersion") != 2:
        raise ImproperlyConfigured("Versão do catálogo de datasets não suportada.")

    raw_definitions = payload.get("datasets")
    if not isinstance(raw_definitions, list) or not raw_definitions:
        raise ImproperlyConfigured("O catálogo não contém datasets.")

    definitions: dict[str, DatasetDefinition] = {}
    for raw in raw_definitions:
        if not isinstance(raw, dict):
            raise ImproperlyConfigured("Definição de dataset inválida.")
        definition = _load_definition(catalog_root, raw)
        key = catalog_key(definition.source_system, definition.code)
        if key in definitions:
            raise ImproperlyConfigured(f"Dataset duplicado: {key}.")
        definitions[key] = definition
    return DatasetCatalog(
        manifest_version=2,
        definitions=definitions,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def _load_definition(root: Path, raw: dict[str, Any]) -> DatasetDefinition:
    required = {
        "code",
        "sourceSystem",
        "schemaVersion",
        "sqlFile",
        "querySha256",
        "validated",
        "parameters",
        "columns",
        "identityColumns",
        "allowedRunKinds",
        "maxRowsPerRun",
    }
    missing = required - raw.keys()
    if missing:
        raise ImproperlyConfigured(f"Dataset sem campos obrigatórios: {sorted(missing)}.")
    sql_file = str(raw["sqlFile"])
    if Path(sql_file).name != sql_file:
        raise ImproperlyConfigured("sqlFile deve ser um nome de arquivo local.")
    # A origem entra na chave do catálogo, então precisa ser um identificador
    # simples — nada de ":" ou vazio partindo a chave em dois.
    source_system = str(raw["sourceSystem"])
    if not re.fullmatch(r"[a-z0-9_]+", source_system):
        raise ImproperlyConfigured(f"Sistema de origem inválido: {source_system!r}.")
    try:
        sql_bytes = (root / sql_file).read_bytes()
        sql = sql_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ImproperlyConfigured(f"SQL indisponível: {sql_file}.") from exc
    digest = hashlib.sha256(sql_bytes).hexdigest()
    if digest != raw["querySha256"]:
        raise ImproperlyConfigured(f"Hash divergente para {sql_file}.")
    normalized_sql = sql.lstrip().upper()
    if not normalized_sql.startswith(("SELECT", "WITH")) or ";" in sql:
        raise ImproperlyConfigured(
            f"Somente um SELECT sem ponto-e-vírgula é permitido: {sql_file}."
        )

    parameters = tuple(
        DatasetParameter(
            name=str(parameter["name"]),
            type=str(parameter["type"]),
            odbc_type=str(parameter["odbcType"]),
        )
        for parameter in raw["parameters"]
    )
    if sql.count("?") != len(parameters):
        raise ImproperlyConfigured(f"Quantidade de parâmetros divergente em {sql_file}.")
    parameter_names = [parameter.name for parameter in parameters]
    if len(parameter_names) != len(set(parameter_names)):
        raise ImproperlyConfigured(f"Parâmetros duplicados em {sql_file}.")

    columns = tuple(
        {"name": str(column["name"]), "type": str(column["type"])} for column in raw["columns"]
    )
    column_names = {column["name"] for column in columns}
    context_columns = tuple(str(value) for value in raw.get("contextColumns", ()))
    if not set(context_columns).issubset(column_names):
        raise ImproperlyConfigured(f"Contexto referencia coluna ausente em {sql_file}.")

    identity_columns = tuple(str(value) for value in raw["identityColumns"])
    if not set(identity_columns).issubset(column_names):
        raise ImproperlyConfigured(f"Identidade referencia coluna ausente em {sql_file}.")
    # A identidade é calculada pelo agente sobre o que o SELECT devolveu, então
    # não pode depender de coluna que só existe depois, no backend.
    if set(identity_columns) & set(context_columns):
        raise ImproperlyConfigured(f"Identidade usa coluna de contexto em {sql_file}.")

    return DatasetDefinition(
        code=str(raw["code"]),
        source_system=source_system,
        schema_version=int(raw["schemaVersion"]),
        sql_file=sql_file,
        query_sha256=digest,
        validated=bool(raw["validated"]),
        parameters=parameters,
        columns=columns,
        identity_columns=identity_columns,
        identity_mode=str(raw.get("identityMode", "row")),
        context_columns=context_columns,
        allowed_run_kinds=tuple(str(value) for value in raw["allowedRunKinds"]),
        requires_source_role=str(raw.get("requiresSourceRole", "")),
        max_rows_per_run=int(raw["maxRowsPerRun"]),
        sql=sql,
    )
