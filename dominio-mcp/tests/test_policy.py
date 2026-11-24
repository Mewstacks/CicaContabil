from __future__ import annotations

import pytest

from dominio_mcp.catalog import Catalog, Column, ForeignKey, Table
from dominio_mcp.policy import (
    ColumnPolicy,
    Policy,
    PolicyClass,
    PolicyError,
    is_valid_cnpj,
    load_policy,
    mask_document,
    mask_pii,
    mask_text,
)


def col(
    name: str, type_: str = "char", width: int | None = 10, comment: str | None = None
) -> Column:
    return Column(name, 1, type_, width, 0, True, comment)


def table(name: str, cols: list[Column], pk: tuple[str, ...] = ()) -> Table:
    return Table(name, "BASE", 10, None, tuple(cols), pk, (), None)


POLICY = load_policy()


def classify(
    tbl: Table,
    column: str,
    *,
    accepted: bool = False,
    fk_columns: frozenset[str] = frozenset(),
    policy: Policy = POLICY,
) -> ColumnPolicy:
    result = policy.classify_table(tbl, fk_columns, lambda t, c: accepted)
    return result[column.lower()]


def one(column: Column, *, table_name: str = "tabela", accepted: bool = False) -> ColumnPolicy:
    return classify(table(table_name, [column]), column.name, accepted=accepted)


# --- segredo ---


def test_denied_table_blocks_every_column_even_harmless_ones() -> None:
    tbl = table("gecertificadosdigitais", [col("nome"), col("codi_emp", "integer", 4)])
    for name in ("nome", "codi_emp"):
        cp = classify(tbl, name, accepted=True)
        assert cp.klass is PolicyClass.SEGREDO
        assert cp.rule == "denied_tables"


@pytest.mark.parametrize(
    "name",
    [
        "senha_modulo_web",
        "PASSWORD_X",
        "x_pwd",
        "pwd",
        "token_api",
        "certificado_digital",
        "frase_secreta",
        "private_key",
        "credencial_x",
        "segredo_x",
        "client_secret",
    ],
)
def test_secret_column_names_are_always_blocked(name: str) -> None:
    cp = one(col(name, "varchar", 40), accepted=True)
    assert cp.klass is PolicyClass.SEGREDO


@pytest.mark.parametrize(
    "comment",
    [
        "Senha de acesso ao portal",
        "Certificado digital da empresa",
        "Token da API",
        "chave privada",
    ],
)
def test_secret_comments_are_blocked(comment: str) -> None:
    cp = one(col("tp_acesso", "varchar", 40, comment), accepted=True)
    assert cp.klass is PolicyClass.SEGREDO
    assert cp.rule == "denied_column_comment_patterns"


@pytest.mark.parametrize("type_", ["binary", "long binary", "varbinary", "image"])
def test_binary_columns_are_blocked(type_: str) -> None:
    assert one(col("conteudo", type_, 1000), accepted=True).klass is PolicyClass.SEGREDO


def test_secret_class_cannot_be_overridden_by_curation() -> None:
    text = (
        "version: 1\ndenied_tables: []\ndenied_column_name_patterns: ['senha']\n"
        "column_overrides:\n  - {table: tabela, column: senha_x, class: normal}\n"
    )
    policy = Policy.from_text(text)
    tbl = table("tabela", [col("senha_x", "varchar", 20)])
    assert classify(tbl, "senha_x", accepted=True, policy=policy).klass is PolicyClass.SEGREDO


# --- documento e pessoal ---


def test_document_columns_are_recognised_by_name_comment_type_and_width() -> None:
    assert one(col("cgce_emp", "char", 14, "CNPJ da empresa")).klass is PolicyClass.DOCUMENTO
    assert one(col("cpf_cnpj", "char", 14)).klass is PolicyClass.DOCUMENTO
    assert one(col("cgc_num", "numeric", 14)).klass is PolicyClass.DOCUMENTO
    # tipo da inscricao (1 - CNPJ/2 - CPF) nao e documento: e smallint
    tipo = one(
        col("tins_emp", "smallint", 2, "Tipo da inscricao (1 - CNPJ/2 - CPF)"), accepted=True
    )
    assert tipo.klass is PolicyClass.NORMAL


def test_cpf_column_is_personal_data() -> None:
    cp = one(col("cpf_func", "char", 11))
    assert (cp.klass, cp.category) == (PolicyClass.PESSOAL, "cpf")
    assert one(col("usa_cpf", "smallint", 2), accepted=True).klass is PolicyClass.NORMAL


@pytest.mark.parametrize(
    ("column", "category"),
    [
        (col("x1", "varchar", 60, "Endereco do cliente"), "endereco"),
        (col("x2", "varchar", 20, "Telefone de contato"), "contato"),
        (col("x3", "varchar", 60, "E-mail do contador"), "contato"),
        (col("x4", "date", 4, "Data de nascimento"), "nascimento"),
        (col("x5", "varchar", 20, "Conta corrente do fornecedor"), "bancario"),
        (col("x6", "numeric", 15, "Salario base"), "folha"),
        (col("x7", "varchar", 60, "Nome do empregado"), "nome"),
        (col("ende_emp", "varchar", 40), "endereco"),
        (col("fone_emp", "varchar", 15), "contato"),
    ],
)
def test_personal_categories_by_comment_and_name(column: Column, category: str) -> None:
    cp = one(column, accepted=True)
    assert (cp.klass, cp.category) == (PolicyClass.PESSOAL, category)


def test_employee_table_only_leaves_keys_free() -> None:
    tbl = table(
        "FOEVENTOS_MENSAL",
        [
            col("codi_emp", "integer", 4),
            col("i_empregados", "integer", 4),
            col("competencia", "date", 4),
            col("i_eventos", "integer", 4),
            col("valor_calc", "numeric", 15),
            col("dt_registro", "date", 4),
        ],
        pk=("codi_emp", "i_empregados", "competencia"),
    )
    fk = frozenset({"i_eventos"})
    free = {
        n: classify(tbl, n, accepted=True, fk_columns=fk).klass
        for n in ("codi_emp", "i_empregados", "competencia", "i_eventos")
    }
    assert set(free.values()) == {PolicyClass.NORMAL}
    for name in ("valor_calc", "dt_registro"):
        cp = classify(tbl, name, accepted=True, fk_columns=fk)
        assert (cp.klass, cp.category, cp.rule) == (
            PolicyClass.PESSOAL,
            "folha",
            "tabela_por_empregado",
        )


# --- texto livre e auditoria ---


@pytest.mark.parametrize(
    "name", ["GELOG_UTILITARIOS", "FOESOCIAL_LOG", "GEATENDIMENTOACOES", "audados"]
)
def test_audit_and_log_tables_block_their_text_columns(name: str) -> None:
    tbl = table(name, [col("mensagem", "varchar", 250), col("qtde", "integer", 4)])
    msg = classify(tbl, "mensagem", accepted=True)
    assert (msg.klass, msg.blocked_reason) == (PolicyClass.TEXTO_LIVRE, "auditoria_log")
    assert classify(tbl, "qtde", accepted=True).klass is PolicyClass.NORMAL


def test_catalog_tables_are_not_mistaken_for_log_tables() -> None:
    for name in ("EFATENDIMENTO_NFE_CATALOGO", "FOEMPREGADOS_EXAMES_TOXICOLOGICOS"):
        tbl = table(name, [col("descricao", "varchar", 120)])
        cp = classify(tbl, "descricao", accepted=True)
        assert cp.blocked_reason is None


def test_free_text_by_name_and_by_width() -> None:
    assert one(col("observacao", "long varchar", 32767)).klass is PolicyClass.TEXTO_LIVRE
    assert one(col("obs_nota", "varchar", 30)).klass is PolicyClass.TEXTO_LIVRE
    assert one(col("descricao", "varchar", 120)).klass is PolicyClass.TEXTO_LIVRE
    nome = one(col("nome_emp", "varchar", 60), accepted=True)
    assert nome.klass is PolicyClass.NORMAL


# --- nao classificada, aceita e curadoria ---


def test_unmatched_column_is_unclassified_until_accepted() -> None:
    column = col("vcon_sai", "numeric", 15, "Valor contabil")
    assert one(column).klass is PolicyClass.NAO_CLASSIFICADA
    assert one(column, accepted=True).klass is PolicyClass.NORMAL


def test_accepting_never_unlocks_sensitive_classes() -> None:
    assert one(col("cpf_func", "char", 11), accepted=True).klass is PolicyClass.PESSOAL
    assert one(col("senha", "varchar", 20), accepted=True).klass is PolicyClass.SEGREDO


def test_owner_curation_can_declare_a_column_normal_or_personal() -> None:
    text = (
        "version: 1\ncolumn_rules:\n"
        "  - {id: obs, class: texto_livre, name: ['^obs'], types: text, min_width: 1}\n"
        "column_overrides:\n"
        "  - {table: efsaidas, column: obs_ok, class: normal}\n"
        "  - {table: efsaidas, column: vcon_sai, class: pessoal, category: folha}\n"
    )
    policy = Policy.from_text(text)
    tbl = table("EFSAIDAS", [col("obs_ok", "varchar", 20), col("vcon_sai", "numeric", 15)])
    assert classify(tbl, "obs_ok", policy=policy).klass is PolicyClass.NORMAL
    cp = classify(tbl, "vcon_sai", policy=policy)
    assert (cp.klass, cp.category, cp.rule) == (PolicyClass.PESSOAL, "folha", "column_overrides")


def test_classify_catalog_uses_foreign_keys_for_the_employee_rule() -> None:
    parent = table("FOEVENTOS", [col("i_eventos", "integer", 4)], pk=("i_eventos",))
    child = table(
        "FOMENSAL",
        [
            col("i_empregados", "integer", 4),
            col("i_eventos", "integer", 4),
            col("valor", "numeric", 15),
        ],
        pk=("i_empregados",),
    )
    catalog = Catalog(
        owner="bethadba",
        tables={"foeventos": parent, "fomensal": child},
        foreign_keys=(ForeignKey("FOMENSAL", ("i_eventos",), "FOEVENTOS", ("i_eventos",)),),
    )
    result = POLICY.classify_catalog(catalog, lambda t, c: True)
    assert result[("fomensal", "i_eventos")].klass is PolicyClass.NORMAL
    assert result[("fomensal", "valor")].klass is PolicyClass.PESSOAL
    assert result[("foeventos", "i_eventos")].klass is PolicyClass.NORMAL


# --- acesso por classe ---


def policy_of(klass: PolicyClass, category: str | None = None, blocked: str | None = None):  # type: ignore[no-untyped-def]
    return ColumnPolicy(klass, category, "teste", blocked)


NO_PII: frozenset[str] = frozenset()


def test_blocked_classes_allow_nothing() -> None:
    for cp in (
        policy_of(PolicyClass.SEGREDO),
        policy_of(PolicyClass.NAO_CLASSIFICADA),
        policy_of(PolicyClass.TEXTO_LIVRE, blocked="auditoria_log"),
    ):
        access = POLICY.access(cp, frozenset({"cpf", "documento", "folha"}))
        assert not access.select
        assert not access.group and not access.order
        assert access.filter_ops == frozenset() and access.aggregates == frozenset()
        assert access.reason


def test_normal_allows_everything() -> None:
    access = POLICY.access(policy_of(PolicyClass.NORMAL), NO_PII)
    assert access.select and access.group and access.order
    assert access.mask == "none"
    assert {"=", "in", "between", "prefix", "contains"} <= access.filter_ops
    assert {"count", "sum", "avg", "min", "max", "count_distinct"} == access.aggregates


def test_document_is_masked_filterable_only_by_equality_and_never_grouped() -> None:
    access = POLICY.access(policy_of(PolicyClass.DOCUMENTO), NO_PII)
    assert access.select and access.mask == "documento"
    assert access.filter_ops == frozenset({"=", "in"})
    assert not access.group and not access.order and access.aggregates == frozenset()
    released = POLICY.access(policy_of(PolicyClass.DOCUMENTO), frozenset({"documento"}))
    assert released.mask == "none"
    assert not released.group and not released.order and released.aggregates == frozenset()


def test_personal_data_needs_its_own_category_released() -> None:
    cp = policy_of(PolicyClass.PESSOAL, "cpf")
    blocked = POLICY.access(cp, frozenset({"contato"}))
    assert not blocked.select and blocked.reason == "pessoal_nao_liberado:cpf"
    released = POLICY.access(cp, frozenset({"cpf"}))
    assert released.select and released.mask == "pessoal"
    assert released.filter_ops == frozenset()
    assert not released.group and not released.order
    assert released.aggregates == frozenset({"count", "sum", "avg"})
    assert released.suppress_small_groups is True


def test_free_text_is_masked_and_never_filtered_grouped_ordered_or_aggregated() -> None:
    # Filtro em texto livre era um oraculo (revisao do Codex, achado 5): so se le, mascarado.
    access = POLICY.access(policy_of(PolicyClass.TEXTO_LIVRE), NO_PII)
    assert access.select and access.mask == "texto"
    assert access.filter_ops == frozenset()
    assert not access.group and not access.order and access.aggregates == frozenset()


# --- mascaras ---


@pytest.mark.parametrize(
    "value",
    [
        "11222333000181",
        "11.222.333/0001-81",
        " 11222333000181 ",
        "12.ABC.345/01DE-35",
        "12ABC34501DE35",
    ],
)
def test_valid_cnpj_numeric_and_alphanumeric(value: str) -> None:
    assert is_valid_cnpj(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "11222333000182",
        "00000000000000",
        "11111111111111",
        "1122233300018",
        "abc",
        "",
        "12.ABC.345/01DE-36",
    ],
)
def test_invalid_cnpj(value: str) -> None:
    assert is_valid_cnpj(value) is False


def test_mask_document_lets_only_a_valid_cnpj_through() -> None:
    assert mask_document("11.222.333/0001-81", allow=False) == "11.222.333/0001-81"
    assert mask_document("529.982.247-25", allow=False) == "529.***.***-25"
    assert mask_document("52998224725", allow=False) == "529.***.***-25"
    assert mask_document("123", allow=False) == "***"
    assert mask_document("texto qualquer", allow=False) == "***"
    assert mask_document(None, allow=False) is None
    assert mask_document("529.982.247-25", allow=True) == "529.982.247-25"


def test_mask_document_recovers_numeric_documents_that_lost_leading_zeros() -> None:
    assert mask_document(11222333000181.0, allow=False) == "11222333000181"
    assert mask_document(4252011000110.0, allow=False) == "04252011000110"
    # CNPJ de base 000 cuja cauda tambem fecha como CPF (o do Banco do Brasil) e ambiguo com um CPF
    # preenchido com zeros: sai mascarado (D-329)
    assert mask_document(191.0, allow=False) == "***"
    assert mask_document(52998224725, allow=False) == "529.***.***-25"
    assert mask_document(5.5, allow=False) == "***"


def test_mask_pii_hides_everything_but_a_cpf_shape() -> None:
    assert mask_pii("52998224725", "cpf") == "529.***.***-25"
    assert mask_pii("529.982.247-25", "cpf") == "529.***.***-25"
    assert mask_pii("1234", "cpf") == "***"
    assert mask_pii("Rua Tal, 10", "endereco") == "***"
    assert mask_pii(3500.0, "folha") == "***"
    assert mask_pii(None, "folha") is None


def test_mask_text_masks_patterns_and_leaves_ordinary_numbers() -> None:
    assert mask_text("CPF 529.982.247-25 do socio") == "CPF [cpf] do socio"
    assert mask_text("cpf 52998224725.") == "cpf [cpf]."
    assert mask_text("contato joao.silva@exemplo.com.br urgente") == "contato [email] urgente"
    assert mask_text("fone (11) 91234-5678 ou 3456-7890") == "fone [telefone] ou [telefone]"
    assert mask_text("nota 12345678 competencia 202611") == "nota 12345678 competencia 202611"
    assert mask_text("CNPJ 11.222.333/0001-81") == "CNPJ 11.222.333/0001-81"
    assert mask_text(None) is None


# --- carga e validacao do arquivo de regras ---


def test_shipped_policy_loads_and_has_a_stable_hash() -> None:
    assert load_policy().sha == POLICY.sha
    assert len(POLICY.sha) == 64
    assert "gecertificadosdigitais" in POLICY.denied_tables


def test_policy_hash_follows_the_text() -> None:
    a = Policy.from_text("version: 1\n")
    b = Policy.from_text("version: 1\ndenied_tables: [x]\n")
    assert a.sha != b.sha


@pytest.mark.parametrize(
    "text",
    [
        "version: 2\n",
        "version: 1\nsurpresa: 1\n",
        "version: 1\ncolumn_rules:\n  - {class: normal, name: ['x']}\n",
        "version: 1\ncolumn_rules:\n  - {id: a, class: inventada, name: ['x']}\n",
        "version: 1\ncolumn_rules:\n  - {id: a, class: pessoal, name: ['(']}\n",
        "version: 1\ncolumn_rules:\n  - {id: a, class: pessoal, category: tudo, name: ['x']}\n",
        "version: 1\ncolumn_rules:\n  - {id: a, class: normal, name: ['x']}\n",
        "version: 1\ncolumn_overrides:\n  - {table: t, column: c, class: nao_classificada}\n",
        "- lista\n",
        "version: [\n",
    ],
)
def test_invalid_policy_files_fail_closed(text: str) -> None:
    with pytest.raises(PolicyError):
        Policy.from_text(text)
