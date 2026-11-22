"""Pacote sintetico para testes de L2: mini Dominio com tabelas grandes, pessoais e bloqueadas."""

from __future__ import annotations

from pathlib import Path

from dominio_mcp.catalog import Catalog, Column, ForeignKey, Index, Table
from dominio_mcp.overlay import overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import load_policy
from dominio_mcp.readable import ReadableReport


def col(
    name: str, type_: str, width: int | None = None, comment: str | None = None, *, pos: int = 0
) -> Column:
    return Column(name, pos, type_, width, 2 if type_ == "numeric" else 0, True, comment)


def table(
    name: str,
    cols: list[Column],
    pk: tuple[str, ...],
    rows: int,
    indexes: tuple[Index, ...] = (),
    kind: str = "BASE",
    view: str | None = None,
) -> Table:
    numbered = tuple(
        Column(c.name, i + 1, c.type, c.width, c.scale, c.nullable, c.comment)
        for i, c in enumerate(cols)
    )
    return Table(name, kind, rows, f"Tabela {name}", numbered, pk, indexes, view)


def demo_catalog() -> Catalog:
    geempre = table(
        "geempre",
        [
            col("codi_emp", "integer", 4),
            col("nome_emp", "varchar", 60),
            col("cgce_emp", "char", 14, "CNPJ da empresa"),
            col("ende_emp", "varchar", 40, "Endereco da empresa"),
            col("dina_emp", "date", 4),
        ],
        ("codi_emp",),
        600,
    )
    efsaidas = table(
        "efsaidas",
        [
            col("codi_emp", "integer", 4),
            col("codi_sai", "integer", 4),
            col("dsai_sai", "date", 4),
            col("vcon_sai", "numeric", 15),
            col("seg_sai", "smallint", 2),
            col("obs_sai", "varchar", 200, "Observacao da nota"),
            col("cgce_cli", "char", 14, "CNPJ ou CPF do cliente"),
            col("situ_sai", "smallint", 2, "Situacao (1 - Normal/2 - Cancelada)"),
        ],
        ("codi_emp", "codi_sai", "seg_sai"),
        386_290,
        (Index("IDX_DATA_SAI", ("codi_emp", "dsai_sai"), 0, 3),),
    )
    efmvspro = table(
        "efmvspro",
        [
            col("codi_emp", "integer", 4),
            col("codi_sai", "integer", 4),
            col("seg_sai", "smallint", 2),
            col("nume_mvs", "integer", 4),
            col("vlor_mvs", "numeric", 15),
        ],
        ("codi_emp", "codi_sai", "seg_sai", "nume_mvs"),
        917_584,
    )
    foempregados = table(
        "foempregados",
        [
            col("codi_emp", "integer", 4),
            col("i_empregados", "integer", 4),
            col("nome", "varchar", 60, "Nome do empregado"),
            col("salario", "numeric", 15),
            col("data_adm", "date", 4),
        ],
        ("codi_emp", "i_empregados"),
        995,
    )
    cert = table(
        "gecertificadosdigitais",
        [col("codi_emp", "integer", 4), col("nome", "varchar", 60)],
        ("codi_emp",),
        10,
    )
    pequena = table(
        "efclientes",
        [
            col("codi_emp", "integer", 4),
            col("codi_cli", "integer", 4),
            col("nome_cli", "varchar", 60),
            col("uf_cli", "char", 2),
        ],
        ("codi_emp", "codi_cli"),
        19_916,
    )
    visao = table(
        "vw_totais",
        [col("codi_emp", "integer", 4), col("total", "numeric", 15)],
        (),
        0,
        kind="VIEW",
        view="SELECT codi_emp, 1 AS total FROM bethadba.geempre",
    )
    tables = {t.key: t for t in (geempre, efsaidas, efmvspro, foempregados, cert, pequena, visao)}
    fks = (
        ForeignKey("efsaidas", ("codi_emp",), "geempre", ("codi_emp",)),
        ForeignKey(
            "efmvspro",
            ("codi_emp", "codi_sai", "seg_sai"),
            "efsaidas",
            ("codi_emp", "codi_sai", "seg_sai"),
        ),
        ForeignKey("foempregados", ("codi_emp",), "geempre", ("codi_emp",)),
        ForeignKey("efclientes", ("codi_emp",), "geempre", ("codi_emp",)),
    )
    return Catalog("bethadba", tables, fks)


def build_demo_pack(
    tmp_path: Path,
    *,
    accept_all: bool = True,
    skip: frozenset[tuple[str, str]] = frozenset(),
    readable: ReadableReport | None = None,
    approved_views: dict[str, str] | None = None,
    name: str = "demo.sqlite3",
) -> Pack:
    catalog = demo_catalog()
    accepted = (
        frozenset((k, c.name.lower()) for k, t in catalog.tables.items() for c in t.columns) - skip
        if accept_all
        else frozenset()
    )
    build_pack(
        tmp_path / name,
        catalog=catalog,
        policy=load_policy(),
        overlay=overlay_from_files({}),
        accepted=accepted,
        approved_views=approved_views,
        readable=readable,
        dsn="contabil",
    )
    return Pack(tmp_path / name)
