# Análises da carteira — validação (24/11/2026)

Escopo e pesquisa: [docs/specs/dominio-mcp-carteira.md](../../docs/specs/dominio-mcp-carteira.md). Banco: o Domínio real do escritório (SQL Anywhere 17.0.11, DSN `contabil`, usuário `EXTERNO`), somente leitura, sem janela de carga. Nenhum nome nem código de empresa aparece aqui.

## O que rodou

| Prova | Resultado |
|---|---|
| Testes do pacote | 951 passam e 1 pulado (o ensaio de carga) com `DOMINIO_MCP_LIVE=1` no ODBC real; sem a variável, os vivos ficam pulados; `ruff` e `mypy` limpos |
| Testes vivos da carteira (`tests/live/test_live_carteira.py`) | 30 passam: colunas declaradas, conferências da carteira inteira contra SQL escrito de outro jeito, orçamento de custo, datas absurdas |
| `.mcpb` reconstruído e provado em venv vazio fora do repositório | 11 ferramentas, glossário, erros estruturados (`PROVA OK`); refeito depois da revisão |
| Varredura da carteira inteira (9 consultas, paginando) | 8,3 s no total |

Tempo real medido por consulta, na carteira inteira de 630 empresas (386 mil notas de saída, 270 mil lançamentos): de 0,03 s a 1,3 s cada; o custo estimado pelo servidor vai de 358 a 24 mil, por isso o orçamento próprio (teto duro de 50 mil, que o cliente nunca escolhe).

## Conferências cruzadas no banco real

Nas 630 empresas, contra SQL escrito de outro jeito (`NOT EXISTS` no lugar de `LEFT JOIN`, `MAX()` por nota, soma direta), todas iguais e mantidas como testes vivos:

1. **Notas sem lançamento**, por segmento (saídas, entradas, serviços): contagem de notas distintas e valor, ao centavo.
2. **Acumulado de 12 meses** somado na carteira inteira: R$ 122.727.279,39 nos dois lados (antes da revisão; a correção de cancelamento não muda o valor, porque as notas canceladas têm valor zero).
3. **Cadastro**: 630 empresas, 602 ativas, 39 sem CNAE 2.0 e 212 sem regime vigente.
4. **Sem movimento** e **lançamentos zerados** em outubro: 44 e 569.
5. **Cancelamentos** por segmento, com a legenda de situação e a marca `cancelada_*`.
6. **Numeração**: 144 pares empresa-série iguais a `conferir_numeracao` (4 fora do teto de 12 KB); uma empresa grande: 162 lacunas e 175 números faltantes nos dois.
7. **Variação**: as 15 primeiras linhas recalculadas à mão; **paginação**: duas páginas de 5 = uma de 10 e as 630 empresas percorridas por `truncado` e `deslocamento`.

## Revisão independente (24/11/2026)

Um revisor de contexto limpo leu as oito consultas e rodou provas descartáveis no banco real: 1 achado alto, 2 médios e 7 baixos confirmados. Cada um virou teste (vermelho antes, quando coube em teste do pacote) e foi corrigido:

| # | Achado | Correção |
|---|---|---|
| 1 | alto: cancelamento só por `cancelada_*`; a situação do documento (2 cancelado, 7 denegado, 8 inutilizado, leiaute oficial da Central 672) era ignorada. 630 saídas de 2026 com situação 2 e `cancelada_sai = 'N'`; a taxa de cancelamento saía zero | cancelada = marca `S` ou situação 2, 7, 8, em saídas, serviços e (só pela situação) entradas; as outras consultas também tiram essas notas |
| 2 | médio: `notas` contava linhas (segmentos), não notas: 140.351 linhas contra 102.004 notas | unidade é a nota (espécie, série, número; na entrada também o fornecedor); novo campo `parciais` para nota com só parte dos segmentos lançada; `documentos_total` de `sem_movimento` também |
| 3 | médio: o roteiro `briefing_da_carteira` mandava `2026-10`, formato que as ferramentas recusam | as datas saem prontas (`AAAA-MM-01` e último dia do mês); mês malformado é recusado |
| 4 | médio: limite de R$ 4,8 milhões atribuído por `rfed_par` 2 e 4, legendado "Microempresa" (inferido); sem MEI; sem limite proporcional | Simples = `simplesn_optante_par = 'S'` (a flag real; coincide com 2 e 4 em todas as vigências); MEI = R$ 81 mil; limite proporcional no ano de início (R$ 400 mil por mês de atividade) com o percentual contra ele |
| 5 | baixo: aviso "MEI não é avaliado" sem respaldo | MEI passou a ser avaliado (o banco real não tem MEI) |
| 6 | baixo: `meses_minimos = 0` "inclui empresa nova" era falso | mínimo 1; empresa sem histórico não tem variação |
| 7 | baixo: data absurda (`9999-12-31`) virava erro cru do banco | datas fora de 1990 a 2100 são recusadas em toda consulta verificada |
| 8 | baixo: `ultimo_movimento` incluía movimento depois da janela | `ultimo_movimento` vai até o fim da janela e `movimento_posterior` mostra a volta |
| 9 | baixo: orçamentos de 2000 em consultas que custam menos de 5; o teto duro só valia no carregamento | orçamento medido na janela mais larga (de 10 a 30.000, cerca de 4 vezes o custo); teste vivo exige orçamento maior que o custo e menor que 10 vezes ele; o executor também limita ao teto duro |
| 10 | baixo: razão social de empresário individual é nome de pessoa e sai em lote | não corrigido: a política trata `razao_emp` como texto livre desde `empresas`; está dito no guia (privacidade). Cabe `allow_pii` ou revisão |

Também corrigido o desempate de `notas_canceladas` (agora inclui o segmento).

## O que a conferência pegou (e a hipótese que caiu)

- **Ligação nota → lançamento.** A primeira hipótese, `ctlancto.ndoc_lan` = número da nota, deu 90% de acerto numa empresa e parecia certa. Era coincidência: ao comparar valor e data, a nota de R$ 51 de 3 de setembro "casava" com um lançamento de R$ 52 de 2 de março. A ligação real é `ndoc_lan` = código interno da nota (`codi_sai`, `codi_ent`, `codi_ser`) com `orig_lan` 5, 6 e 7; valor e data são idênticos e o Domínio indexa isso em `IDX_DOCTO`.
- **A revisão achou o que a minha conferência não achou:** cancelamento por situação, nota contada como linha, legenda do regime. Conferir contra outra formulação do mesmo SQL só prova que o SQL faz o que eu escrevi; a revisão provou contra o que o Domínio diz.
- **Divisão por zero** em `variacao_faturamento` (empresa com média zero): `NULLIF`. O banco avalia a expressão antes do filtro.
- **CNAE:** a coluna `cnae_emp` está vazia em quase todas as empresas; o CNAE 2.0 real é `i_cnae20`.
- **Numeração:** saltos gigantes (centenas de milhões) são outra numeração, não omissão; por isso `lacuna_maxima` (padrão 10.000).
- **`conferir_numeracao` já existente** recusava empresa grande (custo estimado 19,5 contra limite 10) e leva 0,3 s: ganhou orçamento próprio.
- **Teto de 12 KB:** corta a resposta em cerca de 80 linhas, antes do limite de 500; o `truncado` e o `deslocamento` resolvem e o teste vivo percorre as 630 empresas por eles.
- **Cancelamento:** a marca `cancelada_*` sozinha deixava a taxa em zero; o leiaute de importação do Domínio (Central 672) legenda a situação 2, 7 e 8, e as notas com situação 2 têm valor zero em todos os segmentos de 2026.

## Números de hoje (só para provar que roda; o banco está em migração)

| Análise | Resultado agregado |
|---|---|
| Notas sem lançamento (jan a out/2026) | 304 empresas com pelo menos uma; 126 com 100% sem lançamento (não integram escrita com contabilidade); 103.417 notas distintas sem lançamento e 140 só em parte |
| Faturamento e limite (out/2026) | 271 empresas com faturamento; 253 optantes do Simples; 251 abaixo de 50% do limite, 1 entre 50% e 70%, 1 acima de 100% (um único mês de faturamento alto explica); só 1 tem 12 meses completos de histórico |
| Sem movimento (out/2026) | 308 empresas ativas com escrita; 44 já movimentaram e pararam, 264 nunca movimentaram no Domínio |
| Variação de 30% ou mais (out/2026) | 92 empresas, 48 delas com queda |
| Cadastro | 630 empresas (602 ativas): 212 sem regime vigente, 39 sem CNAE 2.0, 27 inativas ainda marcadas com módulo |
| Lançamentos contábeis zerados (out/2026) | 569 empresas, 303 sem nenhum lançamento na história |
| Cancelamentos (jan a out/2026) | 30 segmentos empresa-tipo com 5% ou mais e 10 notas ou mais (eram 4 antes da correção da situação do documento) |
| Numeração (jan a out/2026) | saídas: 51 pares empresa-série em 40 empresas, nenhuma duplicidade; serviços: 97 pares, 1 com duplicidade |

## Limites

- **Não conferido contra o relatório oficial do Domínio.** As análises batem entre si e com consultas independentes; a contadora precisa passar o olho em cada aviso. Isso vale em especial para a base do faturamento (valor contábil menos excluído nas saídas, mais serviços, sem os ajustes da receita bruta legal) e para a legenda inferida do regime (`rfed_par`).
- O banco está em migração: só 59 das 602 empresas ativas têm saídas em 2026 e quase todo o histórico anterior é de poucas empresas. Os números acima não são o retrato do escritório.
- Não foi feito o ensaio de carga T4.9 (janela do dono). O orçamento por consulta é medido, não calibrado. Comando para rodar quando houver janela: `$env:DOMINIO_MCP_LIVE='1'; $env:DOMINIO_MCP_LOAD_WINDOW='1'; uv run --directory dominio-mcp pytest -q -m live tests/live/test_live_load.py -s`.
- Limite proporcional do ano de início e MEI seguem a LC 123/2006 lida de segunda mão e precisam da contadora; o banco real não tem MEI.
- `.mcpb` não instalado no Claude Desktop; nenhum cliente real conectado.
- Perguntas 9 (erros da EFD Contribuições) e 10 (balancete e referencial) seguem sem consulta; `build-pack --aceitar` (L2 livre) segue com o dono.
