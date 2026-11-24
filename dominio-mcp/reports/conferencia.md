# Conferência L1 × L2 e rastros (A9, T7.4)

Data: 21/11/2026. Banco: SAP SQL Anywhere 17.0.11.7312, DSN de sistema `contabil` (usuário Externo). Somente leitura. Nenhum valor de negócio é impresso aqui: só contagens e resultados de comparação.

## Prova viva

```powershell
$env:DOMINIO_MCP_LIVE = '1'
uv run --directory dominio-mcp pytest -q -m live tests/live/test_live_verified.py
```

Resultado em 21/11/2026: **5 passaram em 15 s**. O teste monta um pack temporário (aceitando só quatro colunas de `efsaidas`, para a consulta independente do L2) e usa a empresa com mais linhas em `efsaidas`, janela de 01/06/2025 a 30/06/2025.

| Prova | Resultado |
|---|---|
| As quatro ferramentas L1 carregam contra o pack real (nenhuma desligada por dependência) | ok |
| `empresas` devolve as seis colunas declaradas e a legenda de `situacao` e de `regime_codigo`; filtro por `codi_emp` devolve uma linha só | ok |
| `empresa_perfil` devolve uma linha de 14 colunas com contagens inteiras e não negativas | ok |
| `movimento_fiscal` (L1) × agregação independente em `consulta_estruturada` (L2): mesmo número de linhas e mesma soma de `vcon_sai` (diferença menor que 0,01), contando saídas não canceladas mais as de `cancelada_sai` nulo | ok |
| `conferir_numeracao` roda para saídas e serviços e só devolve `lacuna` ou `duplicidade` | ok (forma; veja "Não provado") |
| Todo resultado traz `lido_em` e `consistencia: leitura_nao_confirmada`; `custo_estimado` abaixo do orçamento (10) | ok |

## L1 sem aceite, L2 recusado

No pack real **sem** `--aceitar` (0 colunas `normal`, pack `cb446dc299f3`), em 21/11/2026, só estrutura impressa:

- `empresas`, `empresa_perfil`, `movimento_fiscal` e `conferir_numeracao` rodam e devolvem as colunas declaradas: o YAML revisado faz o papel de curadoria para a classe `nao_classificada`.
- `consulta_estruturada` em `geempre.codi_emp` e em `sum(efsaidas.vcon_sai)` é recusada com `coluna_bloqueada` (motivo `nao_classificada`).

## Não provado

- **Conferência contra o relatório oficial do Domínio** de `movimento_fiscal` (e de `empresa_perfil`): depende da contadora, com a empresa e a competência que ela escolher.
- **`conferir_numeracao` com lacunas reais conhecidas:** o teste prova a forma e que roda nas duas espécies; falta uma empresa e uma série em que a contadora saiba onde há lacuna e duplicidade.
- **Carga (A11, T4.9):** os limites seguem provisórios até o ensaio em janela autorizada ([carga.md](carga.md)). A conferência L1 × L2 acima não mede interferência no servidor.
- `consistencia` é um rótulo, não uma garantia: a leitura roda com `isolation_level = 0` e pode ver dado ainda não confirmado.
