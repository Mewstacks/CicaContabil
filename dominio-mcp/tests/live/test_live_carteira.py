"""Teste vivo das analises de carteira (DC-1) no banco real: so leitura, sem imprimir valor.

Cada analise roda no SQL Anywhere 17, devolve exatamente as colunas prometidas e bate com uma
consulta independente (a de empresa unica, o L2 ou um SQL simples). A conferencia contra o relatorio
oficial do Dominio continua pendente (contadora).

Rode com:  $env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
"""

# ruff: noqa: E501, S608  (SQL de conferencia com constantes do proprio teste, sem entrada externa)

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from test_live_verified import Rig

from dominio_mcp.config import Limits

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def rig(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Rig]:
    # a carteira roda muitas consultas em sequencia: teto de execucoes no maximo permitido
    instance = Rig(tmp_path_factory.mktemp("live_carteira"), Limits(executions_per_minute=120))
    try:
        yield instance
    finally:
        instance.session.close()


WINDOW = {"inicio": "2026-01-01", "fim": "2026-10-31"}


def rows(out: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(zip(out["colunas"], row, strict=True)) for row in out["linhas"]]


def run(rig: Rig, analysis: str, **args: Any) -> dict[str, Any]:
    return rig.verified.run(f"carteira_{analysis}", {"limite": 200, **args})


@pytest.mark.parametrize(
    ("analysis", "args", "columns"),
    [
        (
            "notas_sem_contabilizacao",
            WINDOW,
            ["codi_emp", "razao_emp", "segmento", "notas", "contabilizadas", "sem_lancamento"],
        ),
        (
            "faturamento_e_limite",
            {"fim": "2026-10-15"},
            ["codi_emp", "acumulado_12m", "limite"],
        ),
        ("sem_movimento", {**WINDOW, "so_com_historico": 1}, ["codi_emp", "ultimo_movimento"]),
        ("variacao_faturamento", {"mes": "2026-10-15"}, ["codi_emp", "variacao_percentual"]),
        ("cadastro", {"so_pendencias": 1}, ["codi_emp", "pendencias"]),
        (
            "lancamentos_contabeis",
            {**WINDOW, "so_zeradas": 1},
            ["codi_emp", "lancamentos_na_janela"],
        ),
        (
            "notas_canceladas",
            {**WINDOW, "percentual_minimo": 0, "documentos_minimos": 1},
            ["codi_emp", "canceladas"],
        ),
        ("numeracao", {"documento": "saidas", **WINDOW}, ["codi_emp", "lacunas", "duplicidades"]),
        ("numeracao", {"documento": "servicos", **WINDOW}, ["codi_emp", "lacunas", "duplicidades"]),
    ],
)
def test_each_analysis_runs_on_the_real_database_with_its_declared_columns(
    rig: Rig,
    analysis: str,
    args: dict[str, Any],
    columns: list[str],
) -> None:
    out = run(rig, analysis, **args)
    tool = rig.verified.tools[f"carteira_{analysis}"]
    assert out["colunas"] == [o.nome for o in tool.saidas]
    assert set(columns) <= set(out["colunas"])
    assert out["quantidade"] == len(out["linhas"]) and out["quantidade"] <= 200
    assert out["consulta"].startswith(f"carteira_{analysis} v1 (") and out["aviso"]


def test_uncounted_notes_match_the_per_company_count_of_the_ledger_link(rig: Rig) -> None:
    portfolio = rows(run(rig, "notas_sem_contabilizacao", **WINDOW))
    assert portfolio, "a carteira real tem empresas com nota sem lancamento"
    sample = next(r for r in portfolio if r["segmento"] == "saidas")
    single = rows(run(rig, "notas_sem_contabilizacao", codi_emp=sample["codi_emp"], **WINDOW))
    again = next(r for r in single if r["segmento"] == "saidas")
    assert (again["notas"], again["sem_lancamento"]) == (sample["notas"], sample["sem_lancamento"])
    assert sample["notas"] == (
        sample["contabilizadas"] + sample["parciais"] + sample["sem_lancamento"]
    )


def test_twelve_month_revenue_matches_the_monthly_movement_of_the_same_company(rig: Rig) -> None:
    top = rows(run(rig, "faturamento_e_limite", fim="2026-10-15"))
    sample = next(r for r in top if r["meses_com_dados"] == 10 and r["acumulado_12m"])
    movement = rig.verified.run(
        "movimento_fiscal",
        {
            "codi_emp": sample["codi_emp"],
            "inicio": "2025-11-01",
            "fim": "2026-10-31",
            "limite": 100,
        },
    )
    total = sum(
        Decimal(str(m["valor_contabil"]))
        for m in rows(movement)
        if m["fonte"] in ("saidas", "servicos")
    )
    # `movimento_fiscal` soma o valor contabil; a carteira subtrai o valor excluido das saidas
    assert abs(Decimal(str(sample["acumulado_12m"])) - total) <= total * Decimal("0.10") + 1
    assert sample["acumulado_12m"] >= sample["faturamento_mes"] >= 0


def test_portfolio_numbering_matches_the_single_company_check(rig: Rig) -> None:
    top = rows(run(rig, "numeracao", documento="saidas", **WINDOW))
    sample = next(r for r in top if r["lacunas"] and r["lacunas"] < 150)
    single = rig.verified.run(
        "conferir_numeracao",
        {"codi_emp": sample["codi_emp"], "documento": "saidas", "limite": 500, **WINDOW},
    )
    gaps = [
        r
        for r in rows(single)
        if r["tipo"] == "lacuna"
        and r["especie"] == sample["especie"]
        and str(r["serie"]).strip() == str(sample["serie"]).strip()
        and r["quantidade"] <= 10_000
    ]
    assert (len(gaps), sum(r["quantidade"] for r in gaps)) == (
        sample["lacunas"],
        sample["numeros_faltantes"],
    )


def all_pages(rig: Rig, **args: Any) -> list[dict[str, Any]]:
    """Segue `truncado` (o teto de 12 KB corta antes das 500 linhas) usando o deslocamento."""
    collected: list[dict[str, Any]] = []
    for _ in range(40):
        out = rig.verified.run(
            "carteira_cadastro", {"limite": 500, "deslocamento": len(collected), **args}
        )
        collected += rows(out)
        if not out["truncado"]:
            return collected
    raise AssertionError("paginacao nao terminou")


def test_registry_pending_flags_agree_with_the_registry_list(rig: Rig) -> None:
    everyone = all_pages(rig)
    flagged = all_pages(rig, so_pendencias=1)
    expected = {r["codi_emp"] for r in everyone if r["pendencias"]}
    assert {r["codi_emp"] for r in flagged} == expected
    assert len({r["codi_emp"] for r in everyone}) == len(everyone) > 500


def test_paging_by_offset_never_repeats_or_skips_a_company(rig: Rig) -> None:
    first = rig.verified.run("carteira_cadastro", {"limite": 5})
    second = rig.verified.run("carteira_cadastro", {"limite": 5, "deslocamento": 5})
    full = rig.verified.run("carteira_cadastro", {"limite": 10})
    ids = [r["codi_emp"] for r in rows(first)] + [r["codi_emp"] for r in rows(second)]
    assert ids == [r["codi_emp"] for r in rows(full)] and len(set(ids)) == 10


def test_no_analysis_leaks_a_secret_or_a_personal_column(rig: Rig) -> None:
    for tool in rig.verified.tools.values():
        if tool.name.startswith("carteira_"):
            classes = {o.classe.value for o in tool.saidas}
            assert classes <= {"normal", "texto_livre"}, tool.name


# --- totais da carteira inteira contra SQL escrito de outro jeito (DC-1) ----------------------


def raw_scalar(rig: Rig, sql: str) -> Any:
    with rig.session.slot() as slot:
        return slot.execute(sql, (), max_rows=2, timeout=120).rows[0]


def all_rows(rig: Rig, analysis: str, **args: Any) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for _ in range(80):
        out = rig.verified.run(
            f"carteira_{analysis}", {"limite": 500, "deslocamento": len(collected), **args}
        )
        collected += rows(out)
        if not out["truncado"]:
            return collected
    raise AssertionError("paginacao nao terminou")


# (tabela, chave do documento, data, valor, filtro de situacao e cancelamento, origem, codigo interno)
LINKED = {
    "saidas": (
        "efsaidas s",
        "s.codi_esp, TRIM(s.seri_sai), s.nume_sai",
        "s.dsai_sai",
        "ISNULL(s.vcon_sai, 0)",
        " AND ISNULL(s.cancelada_sai, 'N') <> 'S' AND ISNULL(s.situacao_sai, 0) NOT IN (2, 7, 8)",
        "5",
        "s.codi_sai",
    ),
    "entradas": (
        "efentradas s",
        "s.codi_esp, TRIM(s.seri_ent), s.nume_ent, s.codi_for",
        "s.dent_ent",
        "ISNULL(s.vcon_ent, 0)",
        " AND ISNULL(s.situacao_ent, 0) NOT IN (2, 7, 8)",
        "6",
        "s.codi_ent",
    ),
    "servicos": (
        "efservicos s",
        "s.codi_esp, TRIM(s.seri_ser), s.nume_ser",
        "s.dser_ser",
        "ISNULL(s.vcon_ser, 0)",
        " AND ISNULL(s.cancelada_ser, 'N') <> 'S' AND ISNULL(s.situacao_ser, 0) NOT IN (2, 7, 8)",
        "7",
        "s.codi_ser",
    ),
}


def aliased(key: str) -> str:
    """Nomeia as colunas da chave: coluna de tabela derivada precisa de nome."""
    return ", ".join(f"{part.strip()} AS k{i}" for i, part in enumerate(key.split(",")))


@pytest.mark.parametrize("segment", ["saidas", "entradas", "servicos"])
def test_notes_without_ledger_match_an_independent_document_count(rig: Rig, segment: str) -> None:
    table, key, day, value, status, origin, code = LINKED[segment]
    # outra formulacao: LEFT JOIN direto ao razao e MAX() por nota; sem lancamento = nenhum segmento ligado
    count, total = raw_scalar(
        rig,
        "SELECT COUNT(*), SUM(v) FROM (SELECT s.codi_emp, "
        f"{aliased(key)}, SUM({value}) AS v, MAX(CASE WHEN l.codi_emp IS NULL THEN 0 ELSE 1 END) AS linked "
        f"FROM bethadba.{table} JOIN bethadba.geempre g ON g.codi_emp = s.codi_emp "
        f"LEFT OUTER JOIN bethadba.ctlancto l ON l.codi_emp = s.codi_emp AND l.orig_lan = {origin} AND l.ndoc_lan = {code} "
        f"WHERE g.stat_emp = 'A' AND g.ucta_emp = 1 AND {day} BETWEEN '2026-01-01' AND '2026-10-31'{status} "
        f"GROUP BY s.codi_emp, {key}) t WHERE linked = 0",
    )
    mine = [
        r for r in all_rows(rig, "notas_sem_contabilizacao", **WINDOW) if r["segmento"] == segment
    ]
    assert sum(r["sem_lancamento"] for r in mine) == count
    assert round(sum(Decimal(str(r["valor_sem_lancamento"])) for r in mine), 2) == round(
        Decimal(str(total or 0)), 2
    )


def test_portfolio_twelve_month_revenue_matches_an_independent_sum(rig: Rig) -> None:
    mine = all_rows(rig, "faturamento_e_limite", fim="2026-10-15")
    (total,) = raw_scalar(
        rig,
        "SELECT SUM(v) FROM ("
        "SELECT SUM(ISNULL(s.vcon_sai, 0) - ISNULL(s.vexc_sai, 0)) AS v FROM bethadba.efsaidas s "
        "JOIN bethadba.geempre g ON g.codi_emp = s.codi_emp WHERE g.stat_emp = 'A' AND g.uefi_emp = 1 "
        "AND s.dsai_sai BETWEEN '2025-11-01' AND '2026-10-31' AND ISNULL(s.cancelada_sai, 'N') <> 'S' "
        "UNION ALL SELECT SUM(ISNULL(v.vcon_ser, 0)) FROM bethadba.efservicos v "
        "JOIN bethadba.geempre g ON g.codi_emp = v.codi_emp WHERE g.stat_emp = 'A' AND g.uefi_emp = 1 "
        "AND v.dser_ser BETWEEN '2025-11-01' AND '2026-10-31' AND ISNULL(v.cancelada_ser, 'N') <> 'S') t",
    )
    assert round(sum(Decimal(str(r["acumulado_12m"])) for r in mine), 2) == round(
        Decimal(str(total)), 2
    )


def test_registry_counts_match_independent_counts(rig: Rig) -> None:
    mine = all_pages(rig)
    total, active = raw_scalar(
        rig,
        "SELECT COUNT(*), SUM(CASE WHEN stat_emp = 'A' THEN 1 ELSE 0 END) FROM bethadba.geempre",
    )
    assert (len(mine), sum(1 for r in mine if r["situacao"] == "A")) == (total, active)
    (no_regime,) = raw_scalar(
        rig,
        "SELECT COUNT(*) FROM bethadba.geempre g WHERE g.stat_emp = 'A' AND g.uefi_emp = 1 AND NOT EXISTS "
        "(SELECT 1 FROM bethadba.efparametro_vigencia p WHERE p.codi_emp = g.codi_emp "
        "AND p.vigencia_par <= CURRENT DATE)",
    )
    assert sum(1 for r in mine if "sem_regime" in r["pendencias"]) == no_regime


def test_empty_companies_match_independent_not_exists_counts(rig: Rig) -> None:
    window = ("2026-10-01", "2026-10-31")
    quiet = all_rows(rig, "sem_movimento", inicio=window[0], fim=window[1], so_com_historico=1)
    (want,) = raw_scalar(
        rig,
        "SELECT COUNT(*) FROM bethadba.geempre g WHERE g.stat_emp = 'A' AND g.uefi_emp = 1 "
        "AND NOT EXISTS (SELECT 1 FROM bethadba.efsaidas s WHERE s.codi_emp = g.codi_emp "
        f"AND s.dsai_sai BETWEEN '{window[0]}' AND '{window[1]}') "
        "AND NOT EXISTS (SELECT 1 FROM bethadba.efentradas e WHERE e.codi_emp = g.codi_emp "
        f"AND e.dent_ent BETWEEN '{window[0]}' AND '{window[1]}') "
        "AND NOT EXISTS (SELECT 1 FROM bethadba.efservicos v WHERE v.codi_emp = g.codi_emp "
        f"AND v.dser_ser BETWEEN '{window[0]}' AND '{window[1]}') "
        "AND (EXISTS (SELECT 1 FROM bethadba.efsaidas s WHERE s.codi_emp = g.codi_emp) "
        "OR EXISTS (SELECT 1 FROM bethadba.efentradas e WHERE e.codi_emp = g.codi_emp) "
        "OR EXISTS (SELECT 1 FROM bethadba.efservicos v WHERE v.codi_emp = g.codi_emp))",
    )
    assert len(quiet) == want
    zero = all_rows(rig, "lancamentos_contabeis", inicio=window[0], fim=window[1], so_zeradas=1)
    (want_ledger,) = raw_scalar(
        rig,
        "SELECT COUNT(*) FROM bethadba.geempre g WHERE g.stat_emp = 'A' AND g.ucta_emp = 1 AND NOT EXISTS "
        f"(SELECT 1 FROM bethadba.ctlancto l WHERE l.codi_emp = g.codi_emp AND l.data_lan BETWEEN '{window[0]}' AND '{window[1]}')",
    )
    assert len(zero) == want_ledger


CANCELLED = {
    "saidas": (
        "efsaidas s",
        "s.codi_esp, TRIM(s.seri_sai), s.nume_sai",
        "s.dsai_sai",
        "s.cancelada_sai = 'S' OR ISNULL(s.situacao_sai, 0) IN (2, 7, 8)",
    ),
    "entradas": (
        "efentradas s",
        "s.codi_esp, TRIM(s.seri_ent), s.nume_ent, s.codi_for",
        "s.dent_ent",
        "ISNULL(s.situacao_ent, 0) IN (2, 7, 8)",
    ),
    "servicos": (
        "efservicos s",
        "s.codi_esp, TRIM(s.seri_ser), s.nume_ser",
        "s.dser_ser",
        "s.cancelada_ser = 'S' OR ISNULL(s.situacao_ser, 0) IN (2, 7, 8)",
    ),
}


@pytest.mark.parametrize("segment", ["saidas", "entradas", "servicos"])
def test_cancelled_documents_count_the_status_legend_and_the_flag(rig: Rig, segment: str) -> None:
    table, key, day, cond = CANCELLED[segment]
    (issued,) = raw_scalar(
        rig,
        f"SELECT COUNT(*) FROM (SELECT s.codi_emp FROM bethadba.{table} JOIN bethadba.geempre g "
        "ON g.codi_emp = s.codi_emp WHERE g.stat_emp = 'A' AND g.uefi_emp = 1 "
        f"AND {day} BETWEEN '2026-01-01' AND '2026-10-31' GROUP BY s.codi_emp, {key} "
        f"HAVING MAX(CASE WHEN {cond} THEN 1 ELSE 0 END) = 1) t",
    )
    mine = all_rows(rig, "notas_canceladas", percentual_minimo=0, documentos_minimos=1, **WINDOW)
    assert sum(r["canceladas"] for r in mine if r["segmento"] == segment) == issued
    assert issued > 0, "o banco real tem nota cancelada em cada segmento"


def test_the_flag_alone_would_have_missed_most_cancelled_sales(rig: Rig) -> None:
    (flag_only,) = raw_scalar(
        rig,
        "SELECT COUNT(*) FROM bethadba.efsaidas WHERE cancelada_sai = 'S' "
        "AND dsai_sai BETWEEN '2026-01-01' AND '2026-10-31'",
    )
    (by_status,) = raw_scalar(
        rig,
        "SELECT COUNT(*) FROM bethadba.efsaidas WHERE ISNULL(situacao_sai, 0) IN (2, 7, 8) "
        "AND dsai_sai BETWEEN '2026-01-01' AND '2026-10-31'",
    )
    assert by_status > flag_only


def test_simples_limit_follows_the_real_optant_flag_not_the_inferred_regime_code(rig: Rig) -> None:
    mine = all_rows(rig, "faturamento_e_limite", fim="2026-10-15")
    optants = [r for r in mine if r["optante_simples"] == "S"]
    assert optants and all(r["limite"] for r in optants)
    assert all(r["limite"] is None for r in mine if r["optante_simples"] != "S")
    assert all(r["limite"] == 81000 for r in mine if r["mei"] == "S")
    assert all(r["limite"] == 4800000 for r in optants if r["mei"] != "S")
    proportional = [r for r in mine if r["limite_proporcional"]]
    assert all(str(r["inicio_atividade"]).startswith("2026") for r in proportional)
    for r in proportional:
        assert r["limite_proporcional"] == 400000 * (13 - int(str(r["inicio_atividade"])[5:7]))


def test_quiet_companies_report_later_movement_separately(rig: Rig) -> None:
    quiet = all_rows(
        rig, "sem_movimento", inicio="2026-10-01", fim="2026-10-31", so_com_historico=1
    )
    assert all(
        not r["ultimo_movimento"] or str(r["ultimo_movimento"]) <= "2026-10-31" for r in quiet
    )
    assert all(
        not r["movimento_posterior"] or str(r["movimento_posterior"]) > "2026-10-31" for r in quiet
    )
    assert any(r["movimento_posterior"] for r in quiet), "ha empresa que voltou a movimentar depois"


def test_variation_never_reports_a_company_without_history(rig: Rig) -> None:
    mine = all_rows(rig, "variacao_faturamento", mes="2026-10-15")
    assert mine and all(r["meses_anteriores"] >= 2 for r in mine)
    loose = all_rows(rig, "variacao_faturamento", mes="2026-10-15", meses_minimos=1)
    assert all(r["meses_anteriores"] >= 1 for r in loose) and len(loose) >= len(mine)


def test_implausible_dates_are_refused_on_the_real_tools(rig: Rig) -> None:
    from dominio_mcp.query_spec import QueryRefused

    with pytest.raises(QueryRefused):
        rig.verified.run("carteira_faturamento_e_limite", {"fim": "9999-12-31"})
    with pytest.raises(QueryRefused):
        rig.verified.run("carteira_variacao_faturamento", {"mes": "0001-01-01"})


WIDEST = {"inicio": "2025-10-01", "fim": "2026-10-31"}


def test_every_declared_budget_covers_its_measured_cost_and_is_not_loose(rig: Rig) -> None:
    """O orcamento declarado cobre o custo estimado na janela mais larga e nao passa de 10x ele."""
    import datetime

    from dominio_mcp.admission import estimate_plan
    from dominio_mcp.verified import _PARAM_KINDS, assemble, render_literal

    day = datetime.date.fromisoformat
    cases = {
        "carteira_notas_sem_contabilizacao": WIDEST,
        "carteira_faturamento_e_limite": {"fim": "2026-10-15"},
        "carteira_sem_movimento": WIDEST,
        "carteira_variacao_faturamento": {"mes": "2026-10-15"},
        "carteira_cadastro": {},
        "carteira_lancamentos_contabeis": WIDEST,
        "carteira_notas_canceladas": WIDEST,
        "carteira_numeracao": {"documento": "saidas", **WIDEST},
        "conferir_numeracao": {"codi_emp": rig.company, "documento": "saidas", **WIDEST},
    }
    for name, args in cases.items():
        tool = rig.verified.tools[name]
        values = {p.nome: p.padrao for p in tool.params if p.padrao is not None}
        values.update({k: day(v) if k in ("inicio", "fim", "mes") else v for k, v in args.items()})
        variant = (
            tool.variants[values[tool.variant_param]] if tool.variant_param else tool.variants[None]
        )
        sql, names = assemble(variant.sql, values, 101, 1)
        kinds = {p.nome: _PARAM_KINDS[p.tipo] for p in tool.params}
        literal = render_literal(sql, names, kinds, values)
        with rig.session.slot() as slot:
            cost = estimate_plan(slot.execute, literal).cost
        assert tool.orcamento is not None, name
        budget = tool.orcamento[0]
        assert cost <= budget, (name, cost, budget)
        assert budget <= max(10, cost * 10), (name, cost, budget)
