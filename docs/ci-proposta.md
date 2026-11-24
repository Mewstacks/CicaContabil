# Proposta de mudança no CI (E8, 20/11/2026) — aguarda seu OK

`.github/workflows/ci.yml` **não foi editado**: regra global do projeto (nunca mexer em workflow de CI sem pedido). O que já está pronto e testado fica em [scripts/quality_gate.py](../scripts/quality_gate.py) (24 testes em [test_quality_gate.py](../tests/test_quality_gate.py)). Rodar à mão:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --base main
```

## O que o CI faz hoje e o que falta

| Hoje (`ci.yml`, job `verify`) | Falta (E8) |
|---|---|
| `ruff check .`, `manage.py check`, `makemigrations --check`, `pytest -q`, `pytest --ds=config.settings.test_postgresql`, três `docker build` | `ruff format --check` e `mypy` **só nos arquivos novos**, guarda do legado e das migrações explícita, `pip-audit`, cobertura |

O portão é estrito só com o que a mudança cria. Arquivos antigos que ela apenas toca não são obrigados a ser reformatados nem a ter tipagem limpa (14 erros herdados, V-300); o `mypy` neles só informa.

## Passo a acrescentar no job `verify` (depois de `uv sync`)

```yaml
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          persist-credentials: false
          fetch-depth: 0          # o portão compara com origin/main
      # ... passos existentes ...
      - run: uv run python scripts/quality_gate.py --base origin/main
```

Em pull request o `--base origin/main` compara o que a branch cria. O portão repete `ruff check`, `makemigrations --check` e os testes de guarda do legado (30 s): se preferir não duplicar, os dois primeiros podem sair do `ci.yml` depois.

## Opcionais, cada um precisa de decisão

| Item | Comando | Observação |
|---|---|---|
| Auditoria de dependências | `uv run python scripts/quality_gate.py --audit` | usa a rede (`pip-audit` 2.10.0 já está em `dev`); falha em vulnerabilidade conhecida |
| Cobertura | `uv run pytest --cov=src/apps --cov-fail-under=85` | `pytest-cov` já está em `dev`; o piso de 85 está em `pyproject.toml`; mede a suíte inteira, acrescenta alguns minutos |
| Fluxo cadastro → procuração no navegador | Playwright | o repositório não tem Playwright instalado (V-300); exigiria dependência nova e navegador no runner |
| Licença das dependências novas | `uv run pip-licenses` | não há dependência nova nesta entrega (usa só `openpyxl`, `cryptography`, `defusedxml`, que já estavam) |

Quando você disser "aplica", a mudança é só o passo acima e o `fetch-depth`.
