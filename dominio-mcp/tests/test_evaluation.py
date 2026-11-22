from __future__ import annotations

from pathlib import Path

from dominio_mcp.evaluation import Question, evaluate, file_sha256, load_questions
from dominio_mcp.search import SearchHit


def hit(key: str) -> SearchHit:
    return SearchHit(key, key, "BASE", key[:2], 1.0, None, None, True, False, None, None, ())


class Stub:
    def __init__(self, answers: dict[str, list[str]]) -> None:
        self.answers = answers

    def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        return [hit(k) for k in self.answers.get(query, [])][:limit]


def q(text: str, expected: set[str], family: str = "cadastro", module: str = "ef") -> Question:
    return Question(text, frozenset(expected), family, module)


def test_recall_counts_first_place_top_five_and_failures() -> None:
    search = Stub(
        {
            "a": ["t1", "t2"],
            "b": ["x", "t2", "y"],
            "c": ["x", "y", "z", "w", "v", "t3"],
            "d": ["x"],
        }
    )
    questions = [
        q("a", {"t1"}),
        q("b", {"t2"}, family="movimento", module="ct"),
        q("c", {"t3"}),
        q("d", {"t4"}),
    ]
    result = evaluate(search, questions, {"t1", "t2", "t3", "t4"})
    assert (result.total, result.top1, result.top5, result.invalid) == (4, 1, 2, 0)
    assert result.recall1 == 0.25 and result.recall5 == 0.5
    assert [text for text, _ in result.failures] == ["c", "d"]
    assert result.by_module == {"ct": (1, 1), "ef": (1, 3)}
    assert result.by_family == {"cadastro": (1, 3), "movimento": (1, 1)}


def test_expected_tables_missing_from_the_pack_are_dropped_and_empty_questions_are_invalid() -> (
    None
):
    search = Stub({"a": ["real"], "b": ["real"]})
    questions = [q("a", {"real", "fantasma"}), q("b", {"fantasma"})]
    result = evaluate(search, questions, {"real"})
    assert (result.total, result.top1, result.invalid) == (1, 1, 1)


def test_empty_evaluation_has_zero_recall() -> None:
    result = evaluate(Stub({}), [], set())
    assert result.total == 0 and result.recall1 == 0.0 and result.recall5 == 0.0


def test_load_questions_and_hash(tmp_path: Path) -> None:
    path = tmp_path / "q.yaml"
    path.write_text(
        'questions:\n  - {q: "Notas fiscais", expected: [EfSaidas, efentradas], '
        "family: movimento, module: ef}\n",
        encoding="utf-8",
    )
    (question,) = load_questions(path)
    assert question.text == "Notas fiscais"
    assert question.expected == frozenset({"efsaidas", "efentradas"})
    assert (question.family, question.module) == ("movimento", "ef")
    first = file_sha256(path)
    path.write_text(path.read_text(encoding="utf-8") + "# x\n", encoding="utf-8")
    assert file_sha256(path) != first
