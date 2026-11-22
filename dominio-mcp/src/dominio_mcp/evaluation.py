"""Avaliacao da recuperacao do esquema (A3, T3.2).

Duas coisas separadas: o conjunto de **desenvolvimento** (serve para ajustar o overlay) e o
**cego** (congelado por hash antes de qualquer ajuste, medido uma vez por versao do overlay e
"queimado" se falhar). Relevancia = conjunto de tabelas aceitas por pergunta; tabela esperada
que nao existe no pack sai do conjunto (e a pergunta sem nenhuma tabela valida e reportada).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

from dominio_mcp.search import SearchHit


class Searcher(Protocol):
    def search(self, query: str, *, limit: int = 8) -> list[SearchHit]: ...


@dataclass(frozen=True, slots=True)
class Question:
    text: str
    expected: frozenset[str]
    family: str
    module: str


@dataclass(frozen=True, slots=True)
class EvalResult:
    total: int
    top1: int
    top5: int
    invalid: int
    failures: list[tuple[str, list[str]]] = field(default_factory=list)
    by_module: dict[str, tuple[int, int]] = field(default_factory=dict)
    by_family: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def recall1(self) -> float:
        return self.top1 / self.total if self.total else 0.0

    @property
    def recall5(self) -> float:
        return self.top5 / self.total if self.total else 0.0


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_questions(path: Path) -> list[Question]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = []
    for item in data["questions"]:
        questions.append(
            Question(
                text=str(item["q"]),
                expected=frozenset(str(t).lower() for t in item["expected"]),
                family=str(item.get("family", "")),
                module=str(item.get("module", "")),
            )
        )
    return questions


def evaluate(
    search: Searcher, questions: list[Question], known_tables: set[str], *, k: int = 5
) -> EvalResult:
    top1 = top5 = invalid = 0
    failures: list[tuple[str, list[str]]] = []
    module_hits: Counter[str] = Counter()
    module_total: Counter[str] = Counter()
    family_hits: Counter[str] = Counter()
    family_total: Counter[str] = Counter()
    for question in questions:
        valid = question.expected & known_tables
        if not valid:
            invalid += 1
            continue
        keys = [hit.key for hit in search.search(question.text, limit=8)]
        position = next((i for i, key in enumerate(keys) if key in valid), None)
        top1 += position == 0
        in_k = position is not None and position < k
        top5 += in_k
        module_total[question.module] += 1
        family_total[question.family] += 1
        module_hits[question.module] += in_k
        family_hits[question.family] += in_k
        if not in_k:
            failures.append((question.text, keys[:3]))
    total = len(questions) - invalid
    return EvalResult(
        total=total,
        top1=top1,
        top5=top5,
        invalid=invalid,
        failures=failures,
        by_module={m: (module_hits[m], n) for m, n in sorted(module_total.items())},
        by_family={f: (family_hits[f], n) for f, n in sorted(family_total.items())},
    )
