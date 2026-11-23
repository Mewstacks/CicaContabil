"""Portão de qualidade (E8): a seleção dos arquivos e o veredito, sem rodar as ferramentas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "quality_gate.py"


@pytest.fixture(scope="module")
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("quality_gate_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_porcelain_separates_new_from_modified_and_drops_deleted(gate: Any) -> None:
    output = "\n".join(
        [
            " M src/apps/hub/views.py",
            "?? src/apps/hub/company_roster.py",
            "A  tests/test_new.py",
            "R  old/name.py -> src/apps/hub/renamed.py",
            " D src/apps/hub/gone.py",
            '?? "src/apps/hub/with space.py"',
            "",
        ]
    )

    assert gate.parse_porcelain(output) == [
        ("modified", "src/apps/hub/views.py"),
        ("added", "src/apps/hub/company_roster.py"),
        ("added", "tests/test_new.py"),
        ("modified", "src/apps/hub/renamed.py"),
        ("added", "src/apps/hub/with space.py"),
    ]


def test_name_status_of_committed_changes(gate: Any) -> None:
    output = "A\tsrc/a.py\nM\tsrc/b.py\nD\tsrc/c.py\nR100\tsrc/old.py\tsrc/new.py\n"

    assert gate.parse_name_status(output) == [
        ("added", "src/a.py"),
        ("modified", "src/b.py"),
        ("modified", "src/new.py"),
    ]


def test_only_existing_python_files_count_and_new_wins_over_modified(gate: Any) -> None:
    changes = [
        ("modified", "scripts/quality_gate.py"),
        ("added", "scripts/quality_gate.py"),
        ("added", "README.md"),
        ("added", "src/apps/hub/nao_existe.py"),
        ("modified", "tests/test_quality_gate.py"),
    ]

    added, modified = gate.python_changes(changes)

    assert added == ["scripts/quality_gate.py"]
    assert modified == ["tests/test_quality_gate.py"]


@pytest.mark.parametrize(
    ("path", "typed"),
    [
        ("src/apps/hub/company_roster.py", True),
        ("src/apps/hub/migrations/0078_nfse_procuracao.py", False),
        ("src/apps/hub/admin.py", False),
        ("src/config/settings/base.py", False),
        ("tests/test_company_roster.py", False),
        ("scripts/quality_gate.py", False),
    ],
)
def test_mypy_only_sees_application_code_outside_the_excluded_paths(
    gate: Any, path: str, typed: bool
) -> None:
    assert (path in gate.mypy_targets([path])) is typed


@pytest.mark.parametrize(
    ("path", "formatted"),
    [
        ("src/apps/hub/company_roster.py", True),
        ("tests/test_company_roster.py", True),
        ("scripts/quality_gate.py", True),
        ("src/apps/platform/migrations/0034_contract_billing_mode.py", False),
        ("migrations/0001_initial.py", False),
    ],
)
def test_generated_migrations_are_not_held_to_ruff_format(
    gate: Any, path: str, formatted: bool
) -> None:
    assert (path in gate.format_targets([path])) is formatted


def test_the_gate_names_the_guard_tests_that_exist() -> None:
    gate_source = SCRIPT.read_text(encoding="utf-8")
    root = SCRIPT.parents[1]

    for relative in ("tests/test_migration_safety.py", "tests/test_legacy_contract.py"):
        assert relative in gate_source and (root / relative).is_file()


def test_the_verdict_fails_when_any_blocking_step_fails(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake_run(label: str, command: list[str]) -> bool:
        calls.append(label)
        return "mypy" not in label

    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "changed_files", lambda base: (["src/apps/hub/x.py"], []))

    assert gate.main(["--base", "main"]) == 1
    assert any("mypy" in label for label in calls) and any("ruff check" in label for label in calls)


def test_a_failure_in_an_altered_legacy_file_is_informative_only(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake_run(label: str, command: list[str]) -> bool:
        calls.append(label)
        return "informativo" not in label

    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "changed_files", lambda base: ([], ["src/apps/hub/views.py"]))

    assert gate.main([]) == 0  # os erros herdados de views.py não derrubam a mudança
    assert any("informativo" in label for label in calls)


def test_the_verdict_passes_and_skips_empty_steps(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(gate, "run", lambda label, command: calls.append(label) or True)
    monkeypatch.setattr(gate, "changed_files", lambda base: ([], []))

    assert gate.main([]) == 0
    assert not any("mypy" in label or "format" in label for label in calls)  # nada novo a olhar
    assert any("makemigrations" in label for label in calls)


def test_the_audit_step_is_opt_in(gate: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(gate, "run", lambda label, command: calls.append(label) or True)
    monkeypatch.setattr(gate, "changed_files", lambda base: ([], []))

    gate.main([])
    assert "pip-audit" not in calls
    gate.main(["--audit"])
    assert "pip-audit" in calls


@pytest.mark.parametrize("ref", ["--output=x", "-p", "main; rm -rf /", "a b", ""])
def test_a_base_that_could_act_as_a_git_option_is_refused(gate: Any, ref: str) -> None:
    with pytest.raises(SystemExit):
        gate.changed_files(ref)
