"""Portão de qualidade da mudança (E8): o que o CI de hoje não cobre, sem reformatar o repositório.

O repositório tem arquivos antigos sem `ruff format` e com erros de tipagem herdados (14 em V-300).
Exigir isso de uma vez travaria tudo, e exigir de todo arquivo que a mudança toca obrigaria a
reformatar código legado. O portão é estrito só com o que a mudança **cria**:

    python scripts/quality_gate.py                   # contra a main, com o que está no disco
    python scripts/quality_gate.py --base HEAD~1
    python scripts/quality_gate.py --audit           # soma pip-audit (usa a rede)

Bloqueiam, nesta ordem:
1. `ruff check .` (o que o CI já faz);
2. `ruff format --check` nos `.py` **novos** (fora migrações, que o Django gera);
3. `mypy` nos `.py` **novos** de `src/` (fora migrações, admin e settings, como no `pyproject`);
4. `manage.py makemigrations --check --dry-run`;
5. `pytest` da guarda do legado e das migrações (L1 e L4 de docs/specs/produto-vendavel.md);
6. `pip-audit` (opcional).
Só informa, sem bloquear: `mypy` nos arquivos de `src/` que a mudança **alterou** (o que já estava
errado antes não é culpa de quem mexeu ao lado).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MYPY_EXCLUDE = re.compile(r"(/migrations/|/admin\.py$|/settings/)")
SAFE_REF = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/~^@{}-]*")
GUARD_TESTS = ("tests/test_migration_safety.py", "tests/test_legacy_contract.py")

Change = tuple[str, str]  # ("added" | "modified", caminho)


def parse_porcelain(output: str) -> list[Change]:
    """`git status --porcelain`: novos (`??`, `A`), alterados e renomeados; sem apagados."""

    changes: list[Change] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:]
        if "D" in status:
            continue
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        kind = "added" if status == "??" or "A" in status else "modified"
        changes.append((kind, path.strip().strip('"')))
    return changes


def parse_name_status(output: str) -> list[Change]:
    """`git diff --name-status`: `A\\tcaminho`, `M\\tcaminho`, `R100\\tantigo\\tnovo`."""

    changes: list[Change] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or parts[0].startswith("D"):
            continue
        changes.append(("added" if parts[0].startswith("A") else "modified", parts[-1]))
    return changes


def python_changes(changes: list[Change]) -> tuple[list[str], list[str]]:
    """(novos, alterados) só de `.py` que existem no disco; novo vence alterado."""

    added: set[str] = set()
    modified: set[str] = set()
    for kind, path in changes:
        if not path.endswith(".py") or not (ROOT / path).is_file():
            continue
        (added if kind == "added" else modified).add(path)
    return sorted(added), sorted(modified - added)


def format_targets(files: list[str]) -> list[str]:
    """Migrações são geradas pelo Django (aspas simples) e não passam pelo `ruff format`."""

    return [f for f in files if "/migrations/" not in "/" + f]


def mypy_targets(files: list[str]) -> list[str]:
    return [f for f in files if f.startswith("src/") and not MYPY_EXCLUDE.search("/" + f)]


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv; the only variable part is validated
        ["git", *args],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def changed_files(base: str) -> tuple[list[str], list[str]]:
    if not SAFE_REF.fullmatch(base):
        raise SystemExit(f"Referência git inválida: {base!r}")
    committed = _git("diff", "--name-status", f"{base}...HEAD")
    working = _git("status", "--porcelain", "--untracked-files=all")
    return python_changes([*parse_name_status(committed), *parse_porcelain(working)])


def run(label: str, command: list[str]) -> bool:
    print(f"\n== {label}\n$ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)  # noqa: S603 - fixed argv
    print(f"-- {'ok' if result.returncode == 0 else 'FALHOU'}: {label}", flush=True)
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--base", default="main", help="ramo de comparação (padrão: main)")
    parser.add_argument("--audit", action="store_true", help="roda pip-audit (usa a rede)")
    args = parser.parse_args(argv)
    py = [sys.executable, "-m"]
    added, modified = changed_files(args.base)
    typed = mypy_targets(added)
    formatted = format_targets(added)
    print(f"{len(added)} .py novo(s), {len(modified)} alterado(s); {len(typed)} novo(s) no mypy.")
    results = {
        "ruff check": run("ruff check", [*py, "ruff", "check", "."]),
        "ruff format": (
            run("ruff format (só novos)", [*py, "ruff", "format", "--check", *formatted])
            if formatted
            else True
        ),
        "mypy": run("mypy (só novos em src/)", [*py, "mypy", *typed]) if typed else True,
        "migrations": run(
            "makemigrations --check",
            [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
        ),
        "guarda do legado": run(
            "guarda do legado e das migrações", [*py, "pytest", "-q", *GUARD_TESTS]
        ),
    }
    if args.audit:
        results["pip-audit"] = run("pip-audit", [*py, "pip_audit"])
    informative = mypy_targets(modified)
    if informative:
        run("mypy nos alterados (informativo, não bloqueia)", [*py, "mypy", *informative])
    failed = [name for name, ok in results.items() if not ok]
    print("\n" + ("Tudo certo." if not failed else "Falhou: " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
