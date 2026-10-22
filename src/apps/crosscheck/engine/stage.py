"""Área de preparo: SQLite temporário em disco, valores em centavos inteiros.

O worker do Fly tem cerca de 110 MB livres e uma conferência pode ter centenas de milhares
de documentos. Em vez de dicionários em memória, o SPED e os XML são lidos em streaming para
estas tabelas e a comparação vira junção SQL. O arquivo mora num diretório temporário do
próprio worker e some junto com ele; nada aqui é estado durável.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .efd import DOCUMENT_MONEY_FIELDS, EfdDocument
from .fiscal_xml import (
    ParsedCte,
    ParsedEvent,
    ParsedNfe,
    counterpart_uf,
    status_group,
)
from .keys import is_valid_key

_COMMIT_EVERY = 5000

_SCHEMA = """
CREATE TABLE sped_doc (
    id INTEGER PRIMARY KEY,
    side INTEGER NOT NULL,
    reg TEXT NOT NULL,
    line INTEGER NOT NULL,
    ind_oper TEXT NOT NULL,
    ind_emit TEXT NOT NULL,
    cod_part TEXT NOT NULL,
    cod_mod TEXT NOT NULL,
    cod_sit TEXT NOT NULL,
    ser TEXT NOT NULL,
    sub TEXT NOT NULL,
    num_doc TEXT NOT NULL,
    key TEXT NOT NULL,
    mkey TEXT NOT NULL,
    key_valid INTEGER NOT NULL,
    chv_ref TEXT NOT NULL,
    tp_cte TEXT NOT NULL,
    dt_doc TEXT,
    dt_es TEXT,
    vl_doc INTEGER, vl_desc INTEGER, vl_abat_nt INTEGER, vl_merc INTEGER, vl_frt INTEGER,
    vl_seg INTEGER, vl_out_da INTEGER, vl_bc_icms INTEGER, vl_icms INTEGER,
    vl_bc_icms_st INTEGER, vl_icms_st INTEGER, vl_ipi INTEGER, vl_pis INTEGER,
    vl_cofins INTEGER, vl_pis_st INTEGER, vl_cofins_st INTEGER, vl_serv INTEGER, vl_nt INTEGER
);
CREATE TABLE sped_analytic (
    doc_id INTEGER NOT NULL,
    side INTEGER NOT NULL,
    line INTEGER NOT NULL,
    reg TEXT NOT NULL,
    cst TEXT NOT NULL,
    cfop TEXT NOT NULL,
    aliq INTEGER,
    vl_opr INTEGER, vl_bc_icms INTEGER, vl_icms INTEGER, vl_bc_icms_st INTEGER,
    vl_icms_st INTEGER, vl_red_bc INTEGER, vl_ipi INTEGER,
    cod_obs TEXT NOT NULL
);
CREATE TABLE xml_doc (
    key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    model TEXT NOT NULL,
    series TEXT NOT NULL,
    number TEXT NOT NULL,
    issued TEXT NOT NULL,
    tp_nf TEXT NOT NULL,
    emit_doc TEXT NOT NULL,
    emit_uf TEXT NOT NULL,
    emit_name TEXT NOT NULL,
    dest_doc TEXT NOT NULL,
    dest_uf TEXT NOT NULL,
    direction TEXT NOT NULL,
    cp_uf TEXT NOT NULL,
    c_stat TEXT NOT NULL,
    status_group TEXT NOT NULL,
    vnf INTEGER, vicms INTEGER, vipi INTEGER, vipi_devol INTEGER, vcred_sn INTEGER,
    vbc INTEGER, vbcst INTEGER, vst INTEGER, vprod INTEGER, vfrete INTEGER, vseg INTEGER,
    vdesc INTEGER, voutro INTEGER, vpis INTEGER, vcofins INTEGER, vtprest INTEGER,
    icms_by_cfop TEXT NOT NULL,
    icms51 TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE xml_event (
    key TEXT NOT NULL,
    tp_evento TEXT NOT NULL,
    c_stat TEXT NOT NULL,
    cancels INTEGER NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE xml_skip (
    source TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE TABLE dominio_uf (
    key TEXT NOT NULL,
    direcao TEXT NOT NULL,
    uf TEXT NOT NULL
);
CREATE TABLE cfop_set (cfop TEXT PRIMARY KEY);
"""

_INDEXES = """
CREATE INDEX sped_doc_key ON sped_doc (side, key);
CREATE INDEX sped_doc_mkey ON sped_doc (side, mkey);
CREATE INDEX sped_analytic_doc ON sped_analytic (doc_id);
CREATE INDEX xml_event_key ON xml_event (key);
CREATE INDEX dominio_uf_key ON dominio_uf (key);
"""

_INSERT_SPED_DOC = """
INSERT INTO sped_doc (
    side, reg, line, ind_oper, ind_emit, cod_part, cod_mod, cod_sit, ser, sub, num_doc, key,
    mkey, key_valid, chv_ref, tp_cte, dt_doc, dt_es,
    vl_doc, vl_desc, vl_abat_nt, vl_merc, vl_frt, vl_seg, vl_out_da, vl_bc_icms, vl_icms,
    vl_bc_icms_st, vl_icms_st, vl_ipi, vl_pis, vl_cofins, vl_pis_st, vl_cofins_st, vl_serv,
    vl_nt
) VALUES (
    :side, :reg, :line, :ind_oper, :ind_emit, :cod_part, :cod_mod, :cod_sit, :ser, :sub,
    :num_doc, :key, :mkey, :key_valid, :chv_ref, :tp_cte, :dt_doc, :dt_es,
    :vl_doc, :vl_desc, :vl_abat_nt, :vl_merc, :vl_frt, :vl_seg, :vl_out_da, :vl_bc_icms,
    :vl_icms, :vl_bc_icms_st, :vl_icms_st, :vl_ipi, :vl_pis, :vl_cofins, :vl_pis_st,
    :vl_cofins_st, :vl_serv, :vl_nt
)
"""

_INSERT_ANALYTIC = """
INSERT INTO sped_analytic (
    doc_id, side, line, reg, cst, cfop, aliq, vl_opr, vl_bc_icms, vl_icms, vl_bc_icms_st,
    vl_icms_st, vl_red_bc, vl_ipi, cod_obs
) VALUES (
    :doc_id, :side, :line, :reg, :cst, :cfop, :aliq, :vl_opr, :vl_bc_icms, :vl_icms,
    :vl_bc_icms_st, :vl_icms_st, :vl_red_bc, :vl_ipi, :cod_obs
)
"""

_INSERT_XML = """
INSERT OR IGNORE INTO xml_doc (
    key, kind, model, series, number, issued, tp_nf, emit_doc, emit_uf, emit_name, dest_doc,
    dest_uf, direction, cp_uf, c_stat, status_group,
    vnf, vicms, vipi, vipi_devol, vcred_sn, vbc, vbcst, vst, vprod, vfrete, vseg, vdesc,
    voutro, vpis, vcofins, vtprest, icms_by_cfop, icms51, source
) VALUES (
    :key, :kind, :model, :series, :number, :issued, :tp_nf, :emit_doc, :emit_uf, :emit_name,
    :dest_doc, :dest_uf, :direction, :cp_uf, :c_stat, :status_group,
    :vnf, :vicms, :vipi, :vipi_devol, :vcred_sn, :vbc, :vbcst, :vst, :vprod, :vfrete, :vseg,
    :vdesc, :voutro, :vpis, :vcofins, :vtprest, :icms_by_cfop, :icms51, :source
)
"""


class Stage:
    """Tabelas temporárias de uma conferência. Use como gerenciador de contexto."""

    def __init__(self, directory: str | Path) -> None:
        self.path = Path(directory) / "stage.sqlite3"
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = OFF")
        self.conn.execute("PRAGMA synchronous = OFF")
        self.conn.execute("PRAGMA temp_store = FILE")
        self.conn.execute("PRAGMA cache_size = -8192")
        self.conn.executescript(_SCHEMA)
        self._pending = 0
        self._indexed = False

    def __enter__(self) -> Stage:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        with suppress(sqlite3.Error):
            self.conn.close()

    # -- carga ---------------------------------------------------------------------------
    def _tick(self) -> None:
        self._pending += 1
        if self._pending >= _COMMIT_EVERY:
            self.conn.commit()
            self._pending = 0

    def add_sped_document(self, side: int, doc: EfdDocument) -> None:
        params: dict[str, Any] = {name: None for name in DOCUMENT_MONEY_FIELDS}
        params.update(doc.money)
        params.update(
            side=side,
            reg=doc.reg,
            line=doc.line,
            ind_oper=doc.ind_oper,
            ind_emit=doc.ind_emit,
            cod_part=doc.cod_part,
            cod_mod=doc.cod_mod,
            cod_sit=doc.cod_sit,
            ser=doc.ser,
            sub=doc.sub,
            num_doc=doc.num_doc,
            key=doc.key,
            mkey=doc.matching_key,
            key_valid=1 if (not doc.key or is_valid_key(doc.key)) else 0,
            chv_ref=doc.chv_ref,
            tp_cte=doc.tp_cte,
            dt_doc=doc.dt_doc.isoformat() if doc.dt_doc else None,
            dt_es=doc.dt_es.isoformat() if doc.dt_es else None,
        )
        cursor = self.conn.execute(_INSERT_SPED_DOC, params)
        doc_id = cursor.lastrowid
        if doc.analytics:
            self.conn.executemany(
                _INSERT_ANALYTIC,
                [
                    {
                        "doc_id": doc_id,
                        "side": side,
                        "line": item.line,
                        "reg": item.reg,
                        "cst": item.cst_icms,
                        "cfop": item.cfop,
                        "aliq": item.aliq,
                        "vl_opr": item.vl_opr,
                        "vl_bc_icms": item.vl_bc_icms,
                        "vl_icms": item.vl_icms,
                        "vl_bc_icms_st": item.vl_bc_icms_st,
                        "vl_icms_st": item.vl_icms_st,
                        "vl_red_bc": item.vl_red_bc,
                        "vl_ipi": item.vl_ipi,
                        "cod_obs": item.cod_obs,
                    }
                    for item in doc.analytics
                ],
            )
        self._tick()

    def add_xml(self, doc: ParsedNfe | ParsedCte, *, source: str, direction: str) -> bool:
        """Guarda o resumo do XML. `False` quando a chave já estava (XML duplicado)."""

        common: dict[str, Any] = {
            "key": doc.key,
            "kind": doc.kind,
            "model": doc.model,
            "series": doc.series,
            "number": doc.number,
            "issued": doc.issued,
            "emit_doc": doc.emit_doc,
            "emit_uf": doc.emit_uf,
            "emit_name": doc.emit_name,
            "direction": direction,
            "c_stat": doc.c_stat,
            "status_group": status_group(doc.c_stat),
            "source": source,
        }
        totals: dict[str, int | None] = {
            name: None
            for name in (
                "vnf", "vicms", "vipi", "vipi_devol", "vcred_sn", "vbc", "vbcst", "vst",
                "vprod", "vfrete", "vseg", "vdesc", "voutro", "vpis", "vcofins", "vtprest",
            )
        }  # fmt: skip
        if isinstance(doc, ParsedNfe):
            totals.update({name: doc.totals.get(name) for name in totals if name in doc.totals})
            totals["vcred_sn"] = doc.cred_sn
            common.update(
                tp_nf=doc.tp_nf,
                dest_doc=doc.dest_doc,
                dest_uf=doc.dest_uf,
                cp_uf=counterpart_uf(doc, direction),
                icms_by_cfop=json.dumps(doc.icms_by_cfop, sort_keys=True),
                icms51=json.dumps([asdict(item) for item in doc.icms51]),
            )
        else:
            totals.update(vtprest=doc.v_tprest, vicms=doc.v_icms, vbc=doc.v_bc, vnf=None)
            common.update(
                tp_nf="",
                dest_doc="",
                dest_uf="",
                cp_uf="",
                icms_by_cfop="{}",
                icms51="[]",
            )
        cursor = self.conn.execute(_INSERT_XML, {**common, **totals})
        self._tick()
        return cursor.rowcount > 0

    def add_event(self, event: ParsedEvent, source: str) -> None:
        self.conn.execute(
            "INSERT INTO xml_event (key, tp_evento, c_stat, cancels, source)"
            " VALUES (?, ?, ?, ?, ?)",
            (event.key, event.tp_evento, event.c_stat, 1 if event.cancels else 0, source),
        )
        self._tick()

    def add_skip(self, source: str, reason: str, detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO xml_skip (source, reason, detail) VALUES (?, ?, ?)",
            (source[:200], reason, detail[:200]),
        )
        self._tick()

    def add_dominio(self, key: str, direcao: str, uf: str) -> None:
        self.conn.execute(
            "INSERT INTO dominio_uf (key, direcao, uf) VALUES (?, ?, ?)", (key, direcao, uf)
        )
        self._tick()

    def set_cfops(self, cfops: set[str] | frozenset[str]) -> None:
        self.conn.execute("DELETE FROM cfop_set")
        self.conn.executemany("INSERT INTO cfop_set (cfop) VALUES (?)", [(c,) for c in cfops])

    def finish_loading(self) -> None:
        """Fecha a carga e cria os índices (depois, que é bem mais rápido do que antes)."""

        self.conn.commit()
        self._pending = 0
        if not self._indexed:
            self.conn.executescript(_INDEXES)
            self._indexed = True

    # -- consulta ------------------------------------------------------------------------
    def scalar(self, sql: str, params: tuple[Any, ...] | dict[str, Any] = ()) -> int:
        row = self.conn.execute(sql, params).fetchone()
        return int(row[0] or 0) if row is not None else 0

    def rows(
        self, sql: str, params: tuple[Any, ...] | dict[str, Any] = ()
    ) -> Iterator[sqlite3.Row]:
        cursor = self.conn.execute(sql, params)
        while True:
            batch = cursor.fetchmany(500)
            if not batch:
                return
            yield from batch

    def analytics(self, doc_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sped_analytic WHERE doc_id = ? ORDER BY line", (doc_id,)
        ).fetchall()

    def event_cancelled_keys(self) -> set[str]:
        return {
            row[0]
            for row in self.conn.execute("SELECT DISTINCT key FROM xml_event WHERE cancels = 1")
        }

    def skip_reasons(self) -> dict[str, int]:
        return {
            row[0]: int(row[1])
            for row in self.conn.execute("SELECT reason, COUNT(*) FROM xml_skip GROUP BY reason")
        }
