# Carga no servidor do Domínio — critérios e ensaio (A11, T4.9)

**Estado: critérios escritos; ensaio pendente da janela autorizada pelo dono.** Nada abaixo foi medido ainda. Os critérios foram escritos **antes** do ensaio e só mudam com registro aqui (data e motivo), nunca depois de ver o resultado.

## O que o ensaio decide

O programa só executa L1 e L2 depois de `SELECT PLAN(?)`: o servidor estima o custo sem executar a consulta. Hoje os limites são **provisórios** (`Limits.plan_cost_budget = 10`, `plan_rows_budget = 1.000.000`, `executions_per_minute = 20`), tirados só das estimativas (medidas em 21/11/2026, sem executar): indexada ≈ 0,5, varredura inteira de `efsaidas` ≈ 1,0, auto-junção patológica ≈ 2,35e+06. O ensaio troca "provisório" por "calibrado" respondendo duas perguntas.

1. **Uma consulta admitida atrapalha o escritório?** Sonda de interferência: uma consulta indexada trivial (`geempre` por chave) em **outra conexão**, repetida enquanto a consulta pesada roda.
2. **O custo estimado prevê o tempo real?** Tabela estimado × real de pelo menos 10 consultas, para fixar o orçamento com fator de segurança.

## Critérios de aceite (fixados antes do ensaio)

| # | Critério | Valor |
|---|---|---|
| C1 | p95 da sonda **durante** a consulta pesada ≤ 2× o p95 da linha de base | e ≤ 250 ms |
| C2 | linha de base | pelo menos 50 amostras com o servidor sem a consulta pesada, na mesma janela |
| C3 | amostras durante a consulta pesada | pelo menos 30, tiradas só enquanto ela roda |
| C4 | tabela estimado × real | pelo menos 10 consultas distintas (empresa pequena e grande, janelas de 1, 3, 12 e 13 meses, com e sem junção) |
| C5 | orçamento de custo | o maior custo estimado cujo tempo real ficou ≤ 10 s, dividido por um fator de segurança de 3 (arredondado para baixo) |
| C6 | tempo real | nenhuma consulta admitida passa de 30 s (o limite é alvo, não garantia: se passar, o orçamento desce) |
| C7 | interferência | se C1 falhar, o orçamento desce até passar; se não passar nem no menor custo útil, o ensaio **reprova** e L2 em tabela grande continua desligado |

## Como rodar (só com a janela autorizada)

Pré-requisitos: o dono autorizou o horário e avisou quem usa o Domínio; nenhum fechamento ou folha rodando; o teste só executa leitura (agregados) e usa um pack temporário com aceite de poucas colunas.

```powershell
$env:DOMINIO_MCP_LIVE = '1'
$env:DOMINIO_MCP_LOAD_WINDOW = '1'     # declaração explícita de que a janela foi autorizada
uv run --directory dominio-mcp pytest -q -m live tests/live/test_live_load.py -s
```

O teste imprime a tabela estimado × real e os p95; copie o resultado para a seção abaixo com data, horário da janela e quem autorizou.

## Resultado

_Pendente._ Preencher: data e janela, quem autorizou, linha de base (p50 e p95), p95 durante, tabela estimado × real, orçamento calibrado e o que mudou em `Limits`.
