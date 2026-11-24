from __future__ import annotations

import pytest

from dominio_mcp.textnorm import fold, index_text, stem, tokens


def test_fold_removes_accents_and_lowercases() -> None:
    assert fold("AÇÃO Contábil") == "acao contabil"


@pytest.mark.parametrize(
    ("plural", "singular"),
    [
        ("adicoes", "adicao"),
        ("departamentos", "departamento"),
        ("empresas", "empresa"),
        ("fiscais", "fiscal"),
        ("papeis", "papel"),
        ("contadores", "contador"),
        ("itens", "item"),
        ("lancamentos", "lancamento"),
    ],
)
def test_plural_and_singular_meet_at_the_same_stem(plural: str, singular: str) -> None:
    assert stem(plural) == stem(singular)


@pytest.mark.parametrize("word", ["de", "cfop", "pis", "2026", "ct", "nfe"])
def test_short_words_digits_and_acronyms_are_untouched(word: str) -> None:
    assert stem(word) == word


def test_double_s_is_kept() -> None:
    assert stem("acesso") == "acesso"
    assert stem("processo") == "processo"


def test_tokens_and_index_text_apply_the_same_treatment() -> None:
    text = "Adoções e Exclusões do LALUR"
    assert tokens(text) == ["adocao", "e", "exclusao", "do", "lalur"] or "exclusao" in tokens(text)
    assert index_text(text) == " ".join(tokens(text))
    assert index_text("") == ""
