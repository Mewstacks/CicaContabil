# Recuperação do esquema — medições (A3)

Busca: BM25 (FTS5) + trigramas do nome + glossário do contador + apelidos das tabelas centrais + prior estrutural (FKs que apontam, volume, tabelas filhas, nome curto), com radical simples do português no índice e na consulta. Sem embeddings (D-324). Pack real de 21/11/2026, 4.964 objetos. Overlay `dd8339226c7b` nas medições abaixo.

**Versão do overlay hoje: `d3e4275425b1`.** Depois das medições mudaram só `legends.yaml` (legendas de L1) e `policy.yaml` (ordem das regras e texto livre sem filtro, D-328); a busca não lê nenhum dos dois: `search.py` e `textnorm.py` não os usam. `glossary.yaml`, `core_tables.yaml`, `modules.yaml`, `search.py` e `textnorm.py` não mudaram depois do cego v2 (conferido pelos horários dos arquivos). O desenvolvimento rodado de novo no overlay atual e no pack reconstruído repete 26/34 no top-1 e 32/34 no top-5. O cego v2 **não** foi remedido: a regra é uma medição por versão do overlay e essas mudanças não tocam a busca.

Metas (A3, objetivo, não previsão): **recall@5 ≥ 90% e recall@1 ≥ 70% no conjunto cego**. Regras: o desenvolvimento serve para ajustar; o cego é congelado por hash antes, medido **uma vez por versão do overlay** e **queimado se falhar**.

## Medições

| Data | Conjunto | Código | Perguntas | recall@5 | recall@1 | Resultado |
|---|---|---|---|---|---|---|
| 21/11/2026 | cego v1 (`blind.yaml`) | RRF por posição, sem radical | 46 | 35/46 = **76%** | 20/46 = **43%** | **falhou: lote queimado** |
| 21/11/2026 | cego v2 (`blind2.yaml`) | BM25 normalizado, radical, apelido por cobertura | 32 | 29/32 = **91%** | 16/32 = **50%** | recall@5 atende; **recall@1 não atende** |
| 21/11/2026 | desenvolvimento (`dev.yaml`) | idem v2 | 34 | 32/34 = 94% | 26/34 = 76% | otimista: usado para ajustar |

## Leitura honesta

- O desenvolvimento chegou a 97% no top-5 antes do cego v1, que deu 76%: sobreajuste ao desenvolvimento. O v1 queimou e não foi usado para ajustar nada específico dele; as mudanças seguintes (radical do português e apelido proporcional à cobertura da pergunta) são gerais e foram conferidas no desenvolvimento.
- O v2 foi escrito **depois** de eu ver o resultado do v1, com outras tabelas: a independência dele é **menor** que a de um lote da contadora. O v1 também repete uma tabela do desenvolvimento (`ctconciliacao_bancaria`).
- **A3 não está atendido**: recall@1 de 50% no v2. O top-5 de 91% no v2 e de 76% no v1 mostra que o desempenho real fica entre os dois; a meta de 90% no top-5 só vale por um lote.
- Falhas do v2 (não usadas para ajustar nada): apuração por UF contra o saldo geral, e "novo honorários" confundido com o honorários antigo.
- Para o modelo, `buscar_esquema` devolve até 8 cartões: o top-5 pesa mais que o top-1. Ainda assim a meta é a combinada.

## O que falta para fechar A3

1. Lote cego da **contadora** (≥ 20 perguntas independentes, estratificadas por módulo e família), congelado por hash antes de qualquer ajuste.
2. Se o recall@1 continuar abaixo de 70% com o lote dela, o caminho previsto (D-324) é reavaliar embeddings, com custo e privacidade decididos pelo dono.
3. Cada nova medição do cego entra nesta tabela com data, versão do overlay e resultado.

## Comandos

```powershell
uv run --directory dominio-mcp pytest -q -m eval tests/eval -k test_dev_set -s
$env:DOMINIO_MCP_BLIND = '1'; uv run --directory dominio-mcp pytest -q -m eval tests/eval -k test_blind -s
```
