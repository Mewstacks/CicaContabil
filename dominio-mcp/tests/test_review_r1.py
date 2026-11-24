"""Achados da revisao adversarial do Codex, rodada 1 (21/11/2026): um teste por achado.

Cada teste foi escrito antes da correcao e visto vermelho (triagem em `.agent/review/`). Os numeros
no nome do teste sao os do relatorio.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.budget import Quarantined, RateBudget, RateLimited
from dominio_mcp.catalog import Catalog, ForeignKey
from dominio_mcp.config import Limits, Settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.freshness import PackStale
from dominio_mcp.literals import UnsafeLiteral, encode_literal, like_escape
from dominio_mcp.odbc import ExecutionUncertain, RawResult, build_session
from dominio_mcp.overlay import overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import PolicyClass, mask_text
from dominio_mcp.query_spec import ConsultaEstruturada, QueryRefused, coerce
from dominio_mcp.scope import check_scope
from dominio_mcp.server import error_result
from dominio_mcp.shaping import ShapeContext, shape_result
from fake_odbc import Block, FakeDriver, Rows
from packs import build_demo_pack, col, table
from qhelp import POLICY, compile_, refused

PLANS = Path(__file__).parent / "fixtures" / "plans"
CHEAP = (PLANS / "full_scan.txt").read_text(encoding="utf-8")
WINDOW = {"coluna": "dsai_sai", "op": "between", "valor": ["2026-01-01", "2026-03-31"]}
COMPANY = {"coluna": "codi_emp", "op": "=", "valor": 1}


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def custom_pack(
    tmp_path: Path, tables: list[Any], fks: tuple[ForeignKey, ...] = (), *, policy: Any = POLICY
) -> Pack:
    catalog = Catalog("bethadba", {t.key: t for t in tables}, fks)
    accepted = frozenset((k, c.name.lower()) for k, t in catalog.tables.items() for c in t.columns)
    build_pack(
        tmp_path / "custom.sqlite3",
        catalog=catalog,
        policy=policy,
        overlay=overlay_from_files({}),
        accepted=accepted,
        dsn="contabil",
    )
    return Pack(tmp_path / "custom.sqlite3")


# --- 1. execucao com autorizacao de um pack antigo ---------------------------------------------


class SwappingGuard:
    """O pack muda entre `precheck` (usado para compilar) e `check` (dentro da admissao)."""

    def __init__(self, first: Pack, second: Pack) -> None:
        self.first, self.second = first, second

    def precheck(self) -> Pack:
        return self.first

    def check(self, execute: Any) -> Pack:
        return self.second


def test_01_a_pack_swapped_during_the_call_refuses_before_any_statement(tmp_path: Path) -> None:
    first = build_demo_pack(tmp_path, name="a.sqlite3")
    second = build_demo_pack(tmp_path, skip=frozenset({("geempre", "nome_emp")}), name="b.sqlite3")
    assert first.meta.version != second.meta.version
    settings = Settings(dsn="contabil", home=tmp_path)
    driver = FakeDriver()
    session = build_session(settings, driver=driver, confirm_seconds=0.3, lock_wait_seconds=0.3)
    engine = QueryEngine(
        settings=settings, policy=POLICY, guard=SwappingGuard(first, second), session=session
    )
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(["codi_emp", "nome_emp"], [(1, "ACME")]),
    ]
    with pytest.raises(PackStale):
        engine.run({"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 2})
    assert len(driver.server.script) == 2, "nem a estimativa de custo pode ter sido pedida"


# --- 2. igualdade implicita da FK sem passar pela politica -------------------------------------


def test_02_a_join_whose_key_column_is_secret_is_refused(tmp_path: Path) -> None:
    contas = table(
        "contas", [col("id", "integer", 4), col("senha_conta", "varchar", 8)], ("id",), 10
    )
    codigos = table(
        "codigos", [col("codigo", "varchar", 8), col("rotulo", "varchar", 20)], ("codigo",), 10_000
    )
    fk = ForeignKey("contas", ("senha_conta",), "codigos", ("codigo",))
    custom = custom_pack(tmp_path, [contas, codigos], (fk,))
    assert custom.column("contas", "senha_conta") is not None
    assert custom.column("contas", "senha_conta").klass is PolicyClass.SEGREDO  # type: ignore[union-attr]
    spec = {"tabela": "contas", "colunas": ["id"], "juntar": [{"tabela": "codigos"}]}
    assert refused(custom, spec).code == "juncao_bloqueada"


def test_02_a_join_on_ordinary_keys_still_works(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["codi_sai"],
        "juntar": [{"tabela": "geempre"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert compile_(pack, spec, scope=True).sql.count("INNER JOIN") == 1


# --- 3. texto de tabela por empregado ----------------------------------------------------------


def test_03_free_text_in_an_employee_table_is_payroll_not_free_text() -> None:
    employees = table(
        "foempregados",
        [
            col("codi_emp", "integer", 4),
            col("i_empregados", "integer", 4),
            col("observacao", "varchar", 200),
            col("cpf_emp", "varchar", 14),
        ],
        ("codi_emp", "i_empregados"),
        995,
    )
    classes = POLICY.classify_table(employees, frozenset({"codi_emp"}), lambda _t, _c: True)
    assert (classes["observacao"].klass, classes["observacao"].category) == (
        PolicyClass.PESSOAL,
        "folha",
    )
    # a regra especifica de CPF continua mais forte que a de tabela por empregado
    assert (classes["cpf_emp"].klass, classes["cpf_emp"].category) == (PolicyClass.PESSOAL, "cpf")
    assert classes["i_empregados"].klass is PolicyClass.NORMAL  # chave segue livre


# --- 4. tres linhas com uma unica contribuicao -------------------------------------------------


def test_04_a_personal_sum_needs_three_non_null_contributions(pack: Pack) -> None:
    spec = {
        "tabela": "foempregados",
        "agrupar_por": ["codi_emp"],
        "agregacoes": [{"funcao": "sum", "coluna": "salario", "alias": "total"}],
    }
    compiled = compile_(pack, spec, allow_pii=frozenset({"folha"}))
    # a tabela tem chave de pessoa (`i_empregados`): conta pessoas distintas com valor (D-329)
    assert 'THEN "t0"."i_empregados" END)' in compiled.sql
    raw = RawResult((), [[1, 9000.0, 3, 1], [2, 500.0, 3, 3]], False, 1.0, _now())
    out = shape_result(compiled, raw, ShapeContext(pack_version="abc"))
    assert out["linhas"] == [[2, 500.0]], "so o grupo com tres contribuicoes sai"


def _now() -> Any:
    from datetime import UTC, datetime

    return datetime(2026, 11, 21, tzinfo=UTC)


# --- 5. filtro em texto livre e curinga `[` do LIKE --------------------------------------------


@pytest.mark.parametrize("needle", ["529.982.247-25", "52998", "[5][2][9]", "maria"])
def test_05_free_text_cannot_be_used_as_a_filter(pack: Pack, needle: str) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["codi_sai"],
        "filtros": [COMPANY, {"coluna": "obs_sai", "op": "contains", "valor": needle}],
    }
    assert refused(pack, spec).code == "coluna_bloqueada"


def test_05_like_treats_the_opening_bracket_literally() -> None:
    assert like_escape("[0-9]") == "![0-9]"
    assert like_escape("100%_a!b[x]") == "100!%!_a!!b![x]"


def test_05_a_text_filter_on_an_ordinary_column_reaches_the_database_as_a_literal(
    pack: Pack,
) -> None:
    spec = {
        "tabela": "geempre",
        "colunas": ["codi_emp"],
        "filtros": [{"coluna": "nome_emp", "op": "contains", "valor": "[5][2]"}],
    }
    assert compile_(pack, spec).params == ("%![5]![2]%",)


# --- 6. quarentena que nao consegue ser gravada ------------------------------------------------


def test_06_quarantine_that_cannot_be_written_still_blocks_the_next_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = FakeDriver()
    settings = Settings(dsn="contabil", home=tmp_path, limits=Limits(executions_per_minute=100))
    session = build_session(settings, driver=driver, confirm_seconds=0.2, lock_wait_seconds=0.3)
    driver.server.cancel_mode = "blocks"
    driver.server.script += [Block(ignore_cancel=True)]
    real_replace = os.replace

    def flaky_replace(src: Any, dst: Any) -> None:
        if str(dst).endswith(".quarantine.json"):
            raise PermissionError(13, "disco cheio")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    try:
        with pytest.raises(ExecutionUncertain):
            session.execute("SELECT lento", max_rows=5, timeout=0.1)
        with pytest.raises(Quarantined):
            session.execute("SELECT 1", max_rows=5)
        assert driver.server.script == [], (
            "nenhuma consulta pode rodar enquanto o termino e incerto"
        )
    finally:
        driver.server.release()


# --- 7. decimal com expoente enorme ------------------------------------------------------------


@pytest.mark.parametrize("text", ["1e5000000", "1e-5000000", "-1E+400"])
def test_07_a_decimal_with_a_huge_exponent_is_refused_before_it_is_expanded(text: str) -> None:
    with pytest.raises(ValueError):
        coerce("decimal", text)
    with pytest.raises(UnsafeLiteral):
        encode_literal("decimal", Decimal(text))


def test_07_ordinary_decimals_still_encode() -> None:
    assert encode_literal("decimal", Decimal("1234.50")) == "1234.50"
    assert coerce("decimal", "0.01") == Decimal("0.01")


# --- 8. celula grande nao pode ser trazida inteira ---------------------------------------------


@pytest.mark.parametrize("width", [None, 2_000_000_000])
def test_08_long_text_is_cut_at_the_server(tmp_path: Path, width: int | None) -> None:
    docs = table(
        "documentos",
        [
            col("codi_emp", "integer", 4),
            col("id_doc", "integer", 4),
            col("conteudo", "long varchar", width),
        ],
        ("codi_emp", "id_doc"),
        100,
    )
    custom = custom_pack(tmp_path, [docs])
    compiled = compile_(custom, {"tabela": "documentos", "colunas": ["id_doc", "conteudo"]})
    assert 'LEFT("t0"."conteudo", 400)' in compiled.sql
    assert 'LEFT("t0"."id_doc"' not in compiled.sql


def test_08_short_text_is_not_wrapped(pack: Pack) -> None:
    compiled = compile_(pack, {"tabela": "geempre", "colunas": ["nome_emp"]})
    assert "LEFT(" not in compiled.sql


# --- 9. telefone sem pontuacao -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Contato: +551132345678", "Contato: [telefone]"),
        ("fone 1132345678 ok", "fone [telefone] ok"),
        ("ligar (11) 3234 5678", "ligar [telefone]"),
        ("nota 12345 de 2026", "nota 12345 de 2026"),
    ],
)
def test_09_phone_numbers_without_punctuation_are_masked(text: str, expected: str) -> None:
    assert mask_text(text) == expected


# --- 10. juncoes que multiplicam o total -------------------------------------------------------


def test_10_two_independent_children_of_the_same_parent_are_refused(pack: Pack) -> None:
    spec = {
        "tabela": "geempre",
        "agregacoes": [{"funcao": "sum", "coluna": "efsaidas.vcon_sai", "alias": "total"}],
        "juntar": [{"tabela": "efsaidas"}, {"tabela": "foempregados"}],
        "filtros": [COMPANY],
    }
    assert refused(pack, spec).code == "juncao_multiplicadora"


def test_10_summing_a_parent_measure_after_joining_its_children_is_refused(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "agregacoes": [{"funcao": "sum", "coluna": "vcon_sai", "alias": "total"}],
        "juntar": [{"tabela": "efmvspro"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert refused(pack, spec).code == "agregacao_multiplicada"


def test_10_idempotent_aggregates_and_leaf_measures_stay_allowed(pack: Pack) -> None:
    leaf = {
        "tabela": "efsaidas",
        "agregacoes": [{"funcao": "sum", "coluna": "efmvspro.vlor_mvs", "alias": "total"}],
        "juntar": [{"tabela": "efmvspro"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert compile_(pack, leaf, scope=True).sql
    idempotent = {
        "tabela": "efsaidas",
        "agregacoes": [{"funcao": "max", "coluna": "vcon_sai", "alias": "maior"}],
        "juntar": [{"tabela": "efmvspro"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert compile_(pack, idempotent, scope=True).sql


# --- 11. data cadastral nao e janela de movimento ----------------------------------------------


def test_11_a_parent_registration_date_is_not_a_window_for_the_big_table(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["codi_sai"],
        "juntar": [{"tabela": "geempre"}],
        "filtros": [COMPANY, {"coluna": "geempre.dina_emp", "op": "=", "valor": "2025-01-01"}],
    }
    assert refused(pack, spec, scope=True).code == "sem_janela_de_datas"


def test_11_a_window_on_a_big_parent_still_limits_its_children(pack: Pack) -> None:
    spec = {
        "tabela": "efmvspro",
        "colunas": ["nume_mvs"],
        "juntar": [{"tabela": "efsaidas"}],
        "filtros": [COMPANY, {**WINDOW, "coluna": "efsaidas.dsai_sai"}],
    }
    check_scope(_validated(pack, spec))


def _validated(pack: Pack, spec: dict[str, Any]) -> Any:
    from dominio_mcp.query_spec import validate_query
    from qhelp import settings

    return validate_query(ConsultaEstruturada.model_validate(spec), pack, settings(), POLICY)


# --- 12. DISTINCT contorna a proibicao de agrupar dado mascarado -------------------------------


def test_12_distinct_over_a_document_column_is_refused(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["cgce_cli"],
        "distinto": True,
        "filtros": [COMPANY, WINDOW],
    }
    assert refused(pack, spec).code == "coluna_bloqueada"


def test_12_distinct_over_ordinary_columns_stays_allowed(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["seg_sai"],
        "distinto": True,
        "filtros": [COMPANY, WINDOW],
    }
    assert compile_(pack, spec).sql.startswith("SELECT DISTINCT")


# --- 13. teto de 12 KB na resposta final -------------------------------------------------------


def test_13_an_error_never_exceeds_the_cap_even_when_it_echoes_a_huge_name() -> None:
    huge = "z" * 20_000
    result = error_result("tabela_desconhecida", f"a tabela {huge!r} nao existe", {"tabela": huge})
    assert len(result.content[0].text.encode("utf-8")) <= 12 * 1024  # type: ignore[union-attr]


def test_13_an_oversized_name_is_rejected_as_a_malformed_spec(tmp_path: Path) -> None:
    pack = build_demo_pack(tmp_path)
    settings = Settings(dsn="contabil", home=tmp_path)
    session = build_session(settings, driver=FakeDriver(), lock_wait_seconds=0.3)

    class Guard:
        def precheck(self) -> Pack:
            return pack

        def check(self, execute: Any) -> Pack:
            return pack

    engine = QueryEngine(settings=settings, policy=POLICY, guard=Guard(), session=session)
    with pytest.raises(QueryRefused) as exc:
        engine.run({"tabela": "x" * 20_000, "colunas": ["a"]})
    assert exc.value.code == "especificacao_invalida" and len(exc.value.message) < 1_000


def test_13_verified_extras_count_against_the_cap(tmp_path: Path) -> None:
    from test_verified import TOOL, runner

    big = TOOL.replace("maximo: 10", "maximo: 500").replace("padrao: 2", "padrao: 500")
    big = big.replace("aviso: Diagnostico.", "aviso: " + "Aviso longo. " * 60)
    run, driver, _ = runner(tmp_path, big)
    wide = [(n, "E" * 150, "11222333000181") for n in range(1, 501)]
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(["codi_emp", "nome", "cnpj"], wide),
    ]
    out = run.run("empresas_teste", {"limite": 500})
    import json

    assert len(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode()) <= 12 * 1024
    assert out["truncado"] is True and out["aviso"]


# --- 14. orcamento de frequencia diante de lixo e de relogio que volta -------------------------


def test_14_a_corrupt_rate_file_blocks_one_window_and_then_recovers(tmp_path: Path) -> None:
    path = tmp_path / "rate.json"
    path.write_text("lixo", encoding="utf-8")
    now = [1000.0]
    budget = RateBudget(path, per_minute=1, clock=lambda: now[0])
    with pytest.raises(RateLimited):
        budget.check_and_record()
    now[0] = 1061.0
    budget.check_and_record()  # a janela passou
    with pytest.raises(RateLimited):
        budget.check_and_record()


def test_14_a_clock_that_goes_back_does_not_forget_recent_executions(tmp_path: Path) -> None:
    now = [1000.0]
    budget = RateBudget(tmp_path / "rate.json", per_minute=1, clock=lambda: now[0])
    budget.check_and_record()
    now[0] = 990.0
    with pytest.raises(RateLimited):
        budget.check_and_record()


# --- 15. intervalos que se sobrepoem na numeracao ----------------------------------------------


def test_15_numbering_gaps_use_the_running_maximum_of_every_earlier_range() -> None:
    from dominio_mcp.verified import load_shipped_tools

    sql = " ".join(load_shipped_tools()["conferir_numeracao"].variants["saidas"].sql.split())
    assert (
        "MAX(ultimo) OVER (PARTITION BY esp, serie ORDER BY nume ROWS BETWEEN UNBOUNDED "
        "PRECEDING AND CURRENT ROW) AS coberto" in sql
    )
    assert "b.nume - a.coberto > 1" in sql and "a.ultimo" not in sql


# --- rodada 2 do Codex (21/11/2026) ------------------------------------------------------------


def test_r2_1_quarantine_that_cannot_be_written_keeps_other_processes_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dominio_mcp.budget import ProcessLock, release_retained_locks

    driver = FakeDriver()
    settings = Settings(dsn="contabil", home=tmp_path, limits=Limits(executions_per_minute=100))
    session = build_session(settings, driver=driver, confirm_seconds=0.2, lock_wait_seconds=0.3)
    driver.server.cancel_mode = "blocks"
    driver.server.script += [Block(ignore_cancel=True)]
    real_replace = os.replace

    def flaky_replace(src: Any, dst: Any) -> None:
        if str(dst).endswith(".quarantine.json"):
            raise PermissionError(13, "disco cheio")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    try:
        with pytest.raises(ExecutionUncertain):
            session.execute("SELECT lento", max_rows=5, timeout=0.1)
        other = ProcessLock(tmp_path / "state" / "contabil.lock")  # "outro processo"
        assert other.acquire(0.2) is False, "a trava de processo segue presa: ninguem mais executa"
    finally:
        driver.server.release()
        release_retained_locks()


def test_r2_2_summing_a_parent_measure_from_the_child_side_is_refused(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "agregacoes": [{"funcao": "sum", "coluna": "geempre.codi_emp", "alias": "soma"}],
        "juntar": [{"tabela": "geempre"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert refused(pack, spec).code == "agregacao_multiplicada"


def test_r2_2_the_grain_table_can_still_be_summed_across_an_upward_join(pack: Pack) -> None:
    spec = {
        "tabela": "efsaidas",
        "agrupar_por": ["geempre.nome_emp"],
        "agregacoes": [{"funcao": "sum", "coluna": "vcon_sai", "alias": "total"}],
        "juntar": [{"tabela": "geempre"}],
        "filtros": [COMPANY, WINDOW],
    }
    assert compile_(pack, spec, scope=True).sql


def _policy_without_free_text_rules() -> Any:
    """A politica entregue classifica todo texto longo como texto livre (que ja nao agrupa nem
    ordena); sem essas duas regras a coluna longa fica `normal`, e so entao `coluna_longa` vale:
    defesa em profundidade para curadoria (override) ou politica de outro escritorio."""
    from importlib import resources

    import yaml

    from dominio_mcp.policy import Policy

    text = resources.files("dominio_mcp").joinpath("data/overlay/policy.yaml").read_text("utf-8")
    data = yaml.safe_load(text)
    data["column_rules"] = [
        r for r in data["column_rules"] if r["id"] not in ("texto_livre", "texto_longo")
    ]
    return Policy.from_text(yaml.safe_dump(data, allow_unicode=True))


@pytest.fixture
def long_text_pack(tmp_path: Path) -> Pack:
    docs = table(
        "documentos",
        [
            col("codi_emp", "integer", 4),
            col("id_doc", "integer", 4),
            col("conteudo", "long varchar", None),
            col("valor", "numeric", 15),
        ],
        ("codi_emp", "id_doc"),
        100,
    )
    return custom_pack(tmp_path, [docs], policy=_policy_without_free_text_rules())


@pytest.mark.parametrize(
    "spec",
    [
        {"tabela": "documentos", "colunas": ["conteudo"], "distinto": True},
        {
            "tabela": "documentos",
            "agrupar_por": ["conteudo"],
            "agregacoes": [{"funcao": "sum", "coluna": "valor", "alias": "total"}],
        },
        {"tabela": "documentos", "colunas": ["id_doc"], "ordenar_por": [{"coluna": "conteudo"}]},
    ],
)
def test_r2_3_text_that_must_be_cut_cannot_be_grouped_distinct_or_ordered(
    long_text_pack: Pack, spec: dict[str, Any]
) -> None:
    assert refused(long_text_pack, spec).code == "coluna_longa"


def test_r2_3_text_that_must_be_cut_can_still_be_read_and_compared_whole(
    long_text_pack: Pack,
) -> None:
    read = {"tabela": "documentos", "colunas": ["id_doc", "conteudo"]}
    assert 'LEFT("t0"."conteudo", 400)' in compile_(long_text_pack, read).sql
    whole = {
        "tabela": "documentos",
        "agregacoes": [{"funcao": "count_distinct", "coluna": "conteudo", "alias": "n"}],
    }
    assert 'COUNT(DISTINCT "t0"."conteudo")' in compile_(long_text_pack, whole).sql
