"""Estruturas de busca do pack (T2.7): FTS5, trigramas do nome e prior estrutural.

- `fts_tables`: BM25 sobre nome, comentario e colunas da tabela (acento nao importa). O nome entra
  tambem sem o prefixo de modulo de 2 letras (`efsaidas` vira `saidas`), porque e assim que o
  contador fala;
- `tri_tables` e `tri_columns`: trigramas do nome, para erro de digitacao e pedaco de nome;
- `features`: sinais do proprio banco que corrigem a busca lexical ingenua (15% no top-5 sem eles,
  81% com eles no prototipo): quantas FKs apontam para a tabela, volume, tabelas filhas (nome
  `<pai>_...`), numero de colunas, tamanho e partes do nome, modulo.

Tabela de credencial nunca entra na busca; coluna de segredo tambem nao.
"""

from __future__ import annotations

import sqlite3

from dominio_mcp.textnorm import index_text, stem

COLS_TEXT_LIMIT = 6000

_SCHEMA = """
CREATE VIRTUAL TABLE fts_tables USING fts5(
  table_key UNINDEXED, name, comment, cols, tokenize = 'unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE tri_tables USING fts5(table_key UNINDEXED, name, tokenize = 'trigram');
CREATE VIRTUAL TABLE tri_columns USING fts5(
  table_key UNINDEXED, column_key UNINDEXED, name, tokenize = 'trigram'
);
CREATE TABLE features (
  table_key TEXT PRIMARY KEY, kind TEXT NOT NULL, module TEXT NOT NULL, fk_in INTEGER NOT NULL,
  fk_out INTEGER NOT NULL, kids INTEGER NOT NULL, rows INTEGER, ncols INTEGER NOT NULL,
  name_len INTEGER NOT NULL, parts INTEGER NOT NULL, obsolete INTEGER NOT NULL
);
"""

_TRI_COLUMNS = """
INSERT INTO tri_columns (table_key, column_key, name)
SELECT c.table_key, c.key, c.name FROM columns c
JOIN tables t ON t.key = c.table_key
WHERE c.klass != 'segredo' AND COALESCE(t.blocked_reason, '') != 'tabela_de_credencial'
"""


def name_tokens(name: str) -> str:
    """Nome sem o prefixo de modulo, mais as partes (radicais), so para o indice."""
    lowered = name.lower()
    parts = lowered.split("_")
    head = parts[0]
    first = head[2:] if len(head) > 2 else head
    pieces = [first, *parts[1:], *parts]
    return " ".join(dict.fromkeys(stem(piece) for piece in pieces if piece))


def count_children(names: set[str]) -> dict[str, int]:
    """Quantas tabelas se chamam `<pai>_...` (o pai e o maior prefixo que existe como tabela)."""
    kids: dict[str, int] = {}
    for name in names:
        if "_" not in name:
            continue
        parent = name.rsplit("_", 1)[0]
        while parent:
            if parent in names:
                kids[parent] = kids.get(parent, 0) + 1
                break
            parent = parent.rsplit("_", 1)[0] if "_" in parent else ""
    return kids


def create_search_structures(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    rows = conn.execute(
        "SELECT key, name, kind, module, approx_rows, COALESCE(comment, ''), obsolete "
        "FROM tables WHERE COALESCE(blocked_reason, '') != 'tabela_de_credencial'"
    ).fetchall()
    columns_text: dict[str, list[str]] = {}
    ncols: dict[str, int] = {}
    for table_key, name, comment in conn.execute(
        "SELECT table_key, name, COALESCE(comment, '') FROM columns "
        "WHERE klass != 'segredo' ORDER BY table_key, position"
    ):
        columns_text.setdefault(table_key, []).append(f"{name} {comment}".strip())
    for table_key, count in conn.execute("SELECT table_key, COUNT(*) FROM columns GROUP BY 1"):
        ncols[table_key] = count
    fk_in: dict[str, int] = {}
    fk_out: dict[str, int] = {}
    for child, parent in conn.execute("SELECT child, parent FROM fks"):
        fk_out[child] = fk_out.get(child, 0) + 1
        fk_in[parent] = fk_in.get(parent, 0) + 1
    kids = count_children({r[0] for r in rows})

    for key, name, kind, module, approx, comment, obsolete in rows:
        cols = index_text(" ".join(columns_text.get(key, [])))[:COLS_TEXT_LIMIT]
        conn.execute(
            "INSERT INTO fts_tables (table_key, name, comment, cols) VALUES (?,?,?,?)",
            (key, name_tokens(name), index_text(comment), cols),
        )
        conn.execute("INSERT INTO tri_tables (table_key, name) VALUES (?,?)", (key, name))
        conn.execute(
            "INSERT INTO features VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                key,
                kind,
                module,
                fk_in.get(key, 0),
                fk_out.get(key, 0),
                kids.get(key, 0),
                approx,
                ncols.get(key, 0),
                len(name),
                name.count("_") + 1,
                obsolete,
            ),
        )
    conn.execute(_TRI_COLUMNS)
