# Revisão completa CICA × CONTAD em uso direto — 23/11/2026

Revisão **somente leitura** do código em `origin/main` `e1b1040` (produção v120), feita em laboratório
local com dados sintéticos. Nenhuma correção, commit, deploy, escrita em produção, chamada à IA ou
mensagem externa. Nenhuma decisão nova foi registrada em `DECISOES.md`; as divergências com decisões
existentes estão apontadas na seção 6.

> **Atualização de 23/11/2026 (mesmo dia):** as correções desta revisão foram implementadas, sem
> publicação: D-396 (itens 4.1, 4.3, 4.4 e rótulos de títulos, branch `codex/contad-correcoes-revisao`,
> V-446) e D-397 (item 4.2 e os demais itens da seção 7, branch `claude/contad-revisao-restante`,
> V-448). Prints “depois” na mesma pasta, com prefixo `depois-`. O texto abaixo é o retrato da v120.

## 1. Resumo executivo

1. O 1º mês funciona de ponta a ponta no laboratório (OFX → vínculo → confirmação → regras → lançamento → .txt lote 19); 566 testes aprovados.
2. **Alta:** em conta vinculada pelo OFX (D-385), o Razão não é pedido no 2º mês nem em OFX que cruza meses; tudo para (reproduzido).
3. **Alta:** risco de lançamento em dobro: Razão incompleto já libera lançamento e só a mesma data protege (4 duplicidades no laboratório).
4. **Alta:** o "desfazer" de confirmação automática é revertido, e um movimento exportado anula em silêncio as confirmações do mês.
5. **Alta:** regra DE-PARA retirada (Razão ou IA) não desfaz os lançamentos aprovados que já gerou; eles seguem para o próximo arquivo.
6. **Alta (tela):** títulos mostram código ("Título ea9d8ba1 · Parcela Parcela bfa42c59") em vez da nota, também no relatório, no CSV e nos nomes de regra.
7. **Alta (tela):** quase toda a jornada ainda fala em revisão ("Aguardando revisão", "Precisam de revisão", "A conferir"), contra D-393 item 4.
8. As telas não mostram o que a CICA lançou nem o que já foi exportado; a cliente não consegue acompanhar o uso direto.
9. Celular a 375 px, tema escuro e contraste de texto ok em todas as telas medidas; pendências menores de foco e quebra de datas.
10. São 18 correções priorizadas (seção 7); as 6 primeiras somam cerca de 5–8 dias, e a nº 4 exige decisão nova.

## 2. Método e evidências

- **Worktree:** `contad-revisao-de59d3`, HEAD = `origin/main` `e1b1040` (conferido após `git fetch`). O checkout principal não foi tocado.
- **Leitura prévia:** AGENTS, PLANO-MESTRE, D-375–D-395, V-415–V-445, guia `contad-uso-direto.md` e etapas 09 e 12.
- **Testes, sempre `-p no:cacheprovider`:**
  - 28 arquivos ligados à CONTAD: **566 aprovados, 8 pulados**. Os pulados são de concorrência e só rodam em PostgreSQL.
  - Recortes rodados pelos revisores auxiliares: 307 aprovados/4 pulados e 158/3 (com sobreposição).
  - 4 sondas de cenário, executadas fora do repositório e removidas depois: Razão do 2º mês, OFX que cruza meses, desfazer reconfirmado e lote anulado por exportado. As 4 reproduziram o defeito.
- **Laboratório:** servidor Django descartável com SQLite no scratchpad, sem saída de rede e sem chave de IA. Três escritórios sintéticos, todos em `CICA_DIRECT_USE_ORGANIZATION_IDS`:
  - **A:** conciliação, DE-PARA, lançamento e exportação;
  - **B:** Contas do Domínio, "vincula pelo OFX" e "sem Razão";
  - **C:** títulos interpretados pela D-394.
  - Login sem senha por sessão criada no banco sintético. Telas vistas no navegador do app em 1366 px e 375 px, nos temas claro e escuro, com checagem automática de rolagem horizontal, rótulos, contraste e altura de botões.
  - A entrada do `.claude/launch.json` foi removida ao final; o arquivo voltou ao original.
- **Prints:** pasta [`revisao-contad-2026-11-23/`](revisao-contad-2026-11-23/), 24 imagens do laboratório, sem dado real.

## 3. Funcionalidades

Legenda: ✅ funciona · ⚠️ funciona com ressalvas · ❌ lacuna/defeito. Risco: A (alto), M (médio), B (baixo).

| # | Funcionalidade | Situação | Evidência | Risco principal |
|---|---|---|---|---|
| 1a | Importação OFX/CSV/XLSX/PDF | ⚠️ | `views.py:10443` (`reconciliation_upload`); hash e FITID em `reconciliation_service.py:151-185`, `reconciliation.py:243`. Reenvio idêntico não duplica; OFX com 2 contas é recusado. | **M:** OFX em Windows‑1252 perde acentos. Confirmado: "MANUTENÇÃO" virou "MANUTEN��O" (`reconciliation.py:80`). Afeta regras, IA e histórico exportado. **M (hipótese):** PDF e OFX do mesmo mês se duplicam, porque só o OFX tem FITID. |
| 1b | Vínculo automático pelo OFX (D-385) | ⚠️ | `account_auto_link.py:125-180`; feito no laboratório B (print 13/14). | **A:** o vínculo grava só o mês da última data do OFX (`account_auto_link.py:164`), e isso trava o Razão nos meses seguintes (ver 2a). **M:** OFX de outra empresa é aceito sem alerta; a conta da empresa A fica com a conta bancária da B. |
| 1c | "Conta do extrato, lida do OFX (sem Razão)" (D-393 item 6) | ✅ | `account_auto_link.py:207-234`; feito no laboratório B (print 15). | **B:** a opção também aparece para empresa com banco no plano já vinculado (`:212`) e pode criar uma conta paralela. |
| 2a | Pedido automático do Razão (D-386) | ❌ a partir do 2º mês | `views.py:10589-10658`; `ledger_requests.py:430` exige o mês em `allowed_months`, gravado em `account_discovery_review.py:470`. Sondas: OFX de outubro numa conta vinculada em setembro dá "O Razão não foi pedido automaticamente"; OFX de 28/09 a 02/10 não cria nenhum pedido (o vínculo usa `last_date`, o pedido usa `first_date`). | **A:** sem Razão não há confirmação (D-388), regra (D-392) nem lançamento (D-393). A cliente não sabe destravar, porque teria de confirmar o mês em Contas do Domínio. |
| 2b | Confirmação automática das coincidências (D-388) | ❌ | `auto_confirm.py:24-90`; `reconciliation_workbench.py:64,118-128`; `reconciliation_service.py:1168-1171,1186-1215`. | **A:** o desfazer é revertido. A alocação UNDONE volta a CONFIRMED na rodada seguinte (sonda: 1 reconfirmada). **A:** um movimento já exportado aborta o `atomic` inteiro, e `except Exception: return 0` não deixa log nem aviso (sonda: 0 de 3 confirmadas). Isso acontece quando o Razão é recoletado depois de a CONTAD importar o .txt. **B:** no reenvio, o autor é quem importou, não quem pediu o Razão. |
| 2c | Revisão opcional das confirmações (D-390/D-393) | ⚠️ | `auto_confirmation_review.py:97`; aparece "Valendo como confirmadas" e "Registrar revisão (opcional)" (print 06). | **M:** a medição D-73 fica corrompida, porque um erro desfeito volta como acerto (consequência de 2b). |
| 3 | Conferência, relatório, CSV técnico e saldos pelo OFX (D-389) | ✅ | `reconciliation_report.py:96,470`; `reconciliation.py:136-187`. No laboratório, saldo inicial 10.055,30 = final 10.500,00 − 444,70 (print 07). | **B:** período padrão = primeiro ao último movimento, não o mês cheio. **M (tela):** o lançamento gerado pela CICA não aparece; o movimento lançado continua "A conferir". |
| 4a | DE-PARA pelo Razão ativo sem revisão (D-391/392/393) | ✅ | `direct_use.py:73-108`, `depara_ledger.py:325-362`; no laboratório, 3 regras ativas (print 09). | **A:** regra retirada vira DISABLED (`depara_ledger.py:325-341`), mas os lançamentos aprovados ficam e são exportados. **B:** regra retirada não volta quando a evidência reaparece (o nome já existe). |
| 4b | DE-PARA com IA (D-395) | ⚠️ (só por teste; sem chamada) | `depara_ai_auto.py`: portão em `:70-78`, teto em `:162-177,264-297`, medição em `:375-437`, retirada em `:457-487`, alvos em `:489-532`. Testes: `test_depara_ai_auto.py` (7). | **M:** a chamada paga roda dentro da requisição web. `refresh_ledger_suggestions` usa `on_commit` na própria requisição (`depara_ledger.py:345-362`), com timeout de 90 s por chamada. **M:** a medição às cegas usa padrões que já têm histórico (os mais fáceis) e a regra vale para padrões nunca vistos; os 90% podem superestimar o acerto. Regra já ativada não é reavaliada. **B:** pergunta em dobro sob gatilhos simultâneos (o `ASKED` é gravado depois da chamada). **B:** o teto conta no mínimo 1 centavo por chamada (≈100 chamadas/dia), com trava por escritório e teto global. **B:** rascunho "IA — sem histórico" não aparece em nenhuma tela. |
| 5a | Lançamento do que falta no Razão (D-393 item 3) | ⚠️ | `direct_use.py:111-220`. No laboratório, com datas iguais: 777 lançado, 778 e RESG confirmados, 780/781 (ambíguos) pulados, sem regra não lançado. | **A:** "mês com Razão" = qualquer coleta importada (`_ledger_months`, `:111-129`), sem conferir se o Razão está completo ou atualizado. Não há nova coleta periódica. **A:** "parecido com o Razão" só considera a **mesma data** (`:182`). No 1º laboratório, com datas deslocadas de 1 a 6 dias, 4 movimentos escriturados viraram lançamentos aprovados. A exportação não reavalia os registros parecidos que chegaram depois. |
| 5b | Exportação lote 19 sem homologação (D-380/D-393) | ✅ | `accounting_import.py:154-170` (`export_allowed`), `reconciliation_service.py:1974,2087`. Arquivo gerado no laboratório: 01 = 54, 02 = 150, 03 = 664 e 99 = 100 posições; partida 4/8 de 432,10; CRLF; cp1252 (print 03). Não reexporta, trava e confere hash. | **M (tela):** "Conferir importação" leva a uma página travada: "Este adaptador ainda não está homologado… registro aguarda a homologação" e "Incerto" (print 04). **B:** o histórico exportado é o da regra ("LIQUIDACAO BOLETO") e perde o número do documento do extrato. Leiaute sem importação real observada (D-380). |
| 6a | Coleta de títulos pela tela | ✅ | `title_requests.py:28-268`, `title_request_views.py:50-65`. | **M:** a lista diz "interpretados automaticamente" mesmo quando o resultado foi `sem_conta` (`title_requests.py:405-416`), que é o caso das 4 capturas de produção (V-443). |
| 6b | Interpretação C01/C02 (D-394) | ⚠️ | `title_auto.py`: os 7 itens da D-394 conferidos; `test_title_auto.py` (12). No laboratório: parcela de 100,00 com 2 baixas, autor "CICA — interpretação automática" (print 16/17). | **M:** `vlor` negativo ou malformado cai para `vbru` em vez de recusar (`:89-96`), contrariando os itens 2 e 4. **M:** a revisão humana de parcela é substituída pela leitura automática no gatilho seguinte (`:280-293`; leitura de código), e a tela de fontes continua oferecendo "Revisar parcela". **B:** a criação de conta pela descoberta ou pela configuração não dispara a interpretação (item 7). |
| 6c | Visão, relatório e CSV de títulos | ❌ (identificação) | `title_labels.py:18-21` não conhece a ação automática `native_titles_auto_interpreted`, e `title_auto.py:331-340` não grava `provenance`. | **A (uso):** a cliente não consegue achar a nota. Ver seção 5. |
| 6d | Vínculo baixa × extrato | ⚠️ | `title_allocation.py:78-241`: só prévia; o vínculo exige confirmação humana. | **M:** no uso direto ninguém confirma, então títulos × banco nunca fica vinculado (coerente com a D-394, mas é lacuna de uso). |
| 7 | Carteira, Contas do Domínio, planos e descoberta | ✅ | `reconciliation_portfolio.py:92-371`, `account_discovery.py:278-331`; prints 10–12. | **B:** a carteira não mostra o que foi lançado nem o que falta exportar. A volumetria de 146 empresas não foi reproduzida. |
| 8 | Comandos `uso_direto`, `titulos_auto`, `depara_razao`, `record_dominio_homologation` | ⚠️ | Só leitura do código. Simulação por padrão em 3 deles; `depara_razao create/create-all` grava sem simulação. | **B:** escritório passado como texto gera traceback `ValidationError` em vez de `CommandError`, sem escrita. **B:** `titulos_auto` processa empresa inativa. **B:** nada impede gravar homologação para escritório em uso direto (D-393 item 1 depende de disciplina). **M:** `uso_direto --apply` chama a IA paga sem aviso explícito. |
| 9 | Isolamento, papéis, auditoria e usuário técnico | ✅ | Todos os pontos que chamam `direct_use_enabled`/`ai_enabled` conferidos; querysets filtrados por escritório; auditor só lê; robô `is_active=False`, sem senha e sem vínculo (não entra). Testes de escritório fora da lista passam. | **B:** UUID em maiúsculas na variável nunca casa (falha fechada). **B:** teto global da IA com trava por escritório; só importa se houver 2 escritórios habilitados. |

## 4. Achados que pedem ação antes de a CONTAD usar o 2º mês

### 4.1 Razão não pedido a partir do 2º mês (D-386) — ALTA
- **Onde:** `account_auto_link.py:164` grava a confirmação só para `max(last_date, 2026-09)`. `ledger_requests.py:430` recusa mês fora de `allowed_months`, e `views.py:10605-10609` pede o mês da **primeira** data.
- **Cenário:** a SURIA (ou qualquer conta vinculada pela importação) recebe o OFX de outubro. A tela mostra "O Razão não foi pedido automaticamente: Confira o vínculo desta conta…" e para.
- O aviso fica **acima da área visível**: depois de importar, a página abre rolada em "Solicitações" (print 14).
- **Recomendação:**
  - ao importar OFX numa conta vinculada pela D-385, confirmar sozinho os meses cobertos pelo arquivo e pedir o Razão de cada um;
  - conferir em produção (somente leitura) o `allowed_months` da conta da SURIA.

### 4.2 Lançamento em dobro (D-393 item 3) — ALTA
O código cumpre a letra da decisão ("Razão já chegou"), mas não a intenção ("não duplicar o que a CONTAD já escriturou"):
- **Razão incompleto:** a importação do OFX dispara o pedido do Razão. Se o mês ainda não foi escriturado, o Razão chega vazio ou parcial, e tudo o que as regras reconhecem vira lançamento aprovado. Depois a CONTAD escritura à mão **e** importa o .txt.
- **Data diferente:** o filtro de "parecido" usa data, valor e direção exatos (`direct_use.py:182`). Escrituração em D+1, ou na data do documento, não protege.
- **Na exportação:** `create_export` só chama `validate_journal_entry`, que olha apenas conciliação confirmada (`reconciliation_service.py:1739-1744`), e não reavalia os registros parecidos que chegaram depois.
- **Recomendação (exige decisão nova):**
  - recoletar o Razão imediatamente antes de gerar o arquivo e reavaliar;
  - considerar "parecido" com janela de alguns dias;
  - opcionalmente, só lançar meses com o Razão coletado depois de um marco (por exemplo, dia N do mês seguinte).

### 4.3 Confirmação automática: desfazer revertido e lote anulado (D-388/D-390) — ALTA
- **Desfazer revertido:** `exact_conference_pairs` só considera ocupadas as alocações CONFIRMED, e `confirm_reconciliation` reaproveita a UNDONE via `get_or_create`. Fazer o desfazer "pegar" é correção pequena.
- **Lote anulado:** o lote inteiro roda num único `atomic`, e um movimento exportado levanta erro. Fica preso em `except Exception: return 0`, sem log.
  - Isso acontece justamente no ciclo previsto pelo uso direto: exportar, a CONTAD importar e o Razão ser recoletado.
  - **Recomendação:** pular o movimento exportado e isolar cada par num savepoint com log.

### 4.4 Lançamentos de regra retirada continuam exportáveis — ALTA
- `create_drafts` e `retire_contradicted` só desativam a regra. Os lançamentos APPROVED que ela gerou continuam válidos (`reconciliation_service.py:1597-1611`) e saem no próximo .txt.
- Para a IA isso é mais sério, porque "contradita pelo Razão" significa erro comprovado.
- **Recomendação:** ao retirar a regra, invalidar os lançamentos D-393 aprovados e ainda não exportados que ela gerou.
- Conclusão por leitura de código; não executado.

## 5. Telas

Todas as telas da jornada tiveram **0 px de rolagem horizontal** a 375 px, e o contraste de texto passou nos dois temas nas telas medidas (conciliação, movimentos e conferência). Problemas encontrados:

| Tela | Problema | Print | Prioridade |
|---|---|---|---|
| Títulos e baixas | Código técnico no lugar da nota: "Título ea9d8ba1 / Parcela Parcela bfa42c59" ("Parcela" repetido). Cabeçalho "Parcelas da fotografia revisada" sem ninguém ter revisado. "Fotografia" é jargão. | [16](revisao-contad-2026-11-23/16-titulos-e-baixas.jpg) | **Alta** |
| Relatório de títulos | Mesmo código em parcelas, baixas e histórico ("Baixa 1151818d"). Mostra "Interpretação automática D-394 (tipos oficiais Domínio 6168/6169)", ou seja, ID de decisão para a cliente. "Fotografia revisada", "Composição revisada", SHA-256. CSV com UUID, hashes de 64 caracteres e datas ISO. | [17](revisao-contad-2026-11-23/17-relatorio-titulos.jpg) | **Alta** |
| Conciliação · Visão geral | Indicadores "Precisam de revisão 2 · Abrir fila" e "Conciliados 0" com 2 confirmações feitas; "Registros recebidos da fonte 0" com Razão recebido. Os números contradizem o uso direto e a própria conferência. | [00](revisao-contad-2026-11-23/00-conciliacao-visao-geral.jpg) | **Alta** |
| Conciliação · Importações | Toda linha diz "Aguardando revisão — Os movimentos estão prontos para a conferência humana"; etapa "Revisar movimentos" / "Conferir Razão independente". | [01](revisao-contad-2026-11-23/01-conciliacao-importacoes.jpg) | **Alta** |
| Conferência do extrato | O movimento já lançado e exportado pela CICA (777) aparece "A conferir · Comparar e revisar"; os ambíguos dizem "Confira a evidência"; "Diferença zero não dispensa conferir os 5 restantes". Não diz o que a CICA lançou, o que ficou de fora por ser parecido com o Razão e o que ficou sem regra. | [06](revisao-contad-2026-11-23/06-conferencia-extrato.jpg) | **Alta** |
| Movimentos | Coluna Classificação mostra "DE-PARA Razão 0d00713d1ab3d16a5b59f2aa". "Pronto" para os ambíguos não lançados, igual ao lançado. Data quebra em duas linhas ("22/10/202 / 6") e valor também em 1366 px. "Qualidade 100%" é jargão. | [02](revisao-contad-2026-11-23/02-conciliacao-movimentos.jpg) | Média |
| Relatório de conferência | Saldos do OFX corretos. Texto final "Cobertura e aceite pendentes" / "A cobertura do Razão depende da conferência da fonte pela contadora". Lançamento da CICA ausente. Período padrão parcial. | [07](revisao-contad-2026-11-23/07-relatorio-conferencia.jpg) | Média |
| Exportações | Funciona e diz "Pronto para importar no Domínio". Falta mostrar quantos lançamentos estão prontos antes de gerar. Período vem vazio. A mensagem de sucesso fala em "hash 99c0ceac75f3" e volta para a Visão geral, não para a lista. | [03](revisao-contad-2026-11-23/03-conciliacao-exportacoes.jpg) | Média |
| Conferir importação (exportação) | Página sem saída no uso direto: "adaptador ainda não está homologado… registro aguarda a homologação", tudo "Incerto". Contas só por código ("4 · R$"). | [04](revisao-contad-2026-11-23/04-exportacao-conferir-importacao.jpg) | Média |
| Conferir OFX (aba) | Diz "Sem extratos OFX" e zeros com 2 OFX importados; texto "A comparação exige um Razão independente…". É fila legada, contraditória para a cliente. | [23](revisao-contad-2026-11-23/23-conferir-ofx-vazio.jpg) | Média |
| Nova importação | "Arquivos gerais — não formam Razão independente", "Lote físico (Caixa 12, malote 3)" e "Origem" são jargão e campos sem uso para a CONTAD. Bom: a lista de contas mostra "vincula pelo OFX". | [13](revisao-contad-2026-11-23/13-nova-importacao.jpg) | Média |
| Após importar → Extrato e Razão | A página abre rolada em "Solicitações", e os avisos do topo (inclusive "Razão não foi pedido") ficam fora da tela. O formulário "Vínculo com o Domínio" (empresa do plano, filial, débito/crédito, evidência) aparece no dia a dia. "Aguardando revisão" na lista de extratos. Competência padrão = mês corrente, não o último fechado. | [14](revisao-contad-2026-11-23/14-apos-importacao-aviso-fora-da-tela.jpg), [05](revisao-contad-2026-11-23/05-extrato-e-razao.jpg) | Média |
| Importação sem Razão | Funciona, com mensagem clara. A linha segue "Aguardando revisão… conferência humana". | [15](revisao-contad-2026-11-23/15-importacao-sem-razao.jpg) | Baixa |
| Revisar fontes de títulos | Título "Revisar", "Confira uma parcela por vez", "ainda sem interpretação financeira aprovada" quando a D-394 já interpretou. Oferece "Revisar parcela", que pode ser sobrescrita. Datas ISO ("2026-10-01 (fim não incluído)"). Mostra a nota (10) corretamente. | [19](revisao-contad-2026-11-23/19-revisar-fontes-titulos.jpg) | Média |
| Buscar títulos (coletas) | "Conferir lote" é jargão; competência padrão = mês corrente. A mensagem "interpretados automaticamente" aparece mesmo sem conta (ver 6a). | [18](revisao-contad-2026-11-23/18-buscar-titulos-coletas.jpg) | Média |
| Carteira | Filtros "Vínculo de conta pendente"/"Revisar cadastro ou importação" e rodapé "A cobertura e as correspondências precisam de conferência". Não mostra lançados nem pendentes de exportação. | [10](revisao-contad-2026-11-23/10-carteira.jpg) | Baixa |
| Contas do Domínio | Rodapé "A conta bancária só fica disponível… depois que os dados ainda não comprovados forem conferidos" contradiz a D-385. "Conferir vínculo" em todas as contas. Nomes "Synthetic company" são do laboratório. | [11](revisao-contad-2026-11-23/11-contas-do-dominio.jpg), [12](revisao-contad-2026-11-23/12-contas-do-dominio-empresa.jpg) | Baixa |
| Revisar DE-PARA / Sugestões pelo Razão | Tela clara (padrão, contas com nome, evidência, "Ativa"). O nome do menu "Revisar DE-PARA" contradiz o uso direto. As regras da IA não aparecem aqui. | [08](revisao-contad-2026-11-23/08-revisar-depara.jpg), [09](revisao-contad-2026-11-23/09-sugestoes-pelo-razao.jpg) | Baixa |
| "Como usar" (guia da Conciliação) | Os 3 passos falam em "revisão", "Confirmar, rejeitar ou agrupar", em desacordo com `contad-uso-direto.md`. | — | Média |
| Geral — acessibilidade | Anel de foco dos campos com 28% de opacidade no tema escuro (estimado ≈2:1, abaixo de 3:1). Atalhos secundários com 39 px (já registrado em V-430). Os campos de empresa com busca têm `label` apontando para o campo de busca e o `select` oculto fica sem rótulo (os ocultos não afetam leitor de tela). Sem rolagem horizontal; contraste de texto ok. | [20](revisao-contad-2026-11-23/20-celular-titulos-claro.jpg)–[22](revisao-contad-2026-11-23/22-celular-conferencia-claro.jpg) | Baixa |

**Onde mais aparece código técnico em vez de identificador humano:**
- tabela e busca de *Títulos e baixas* (`reconciliation_titles.html:20-21`);
- histórico de vínculos com `title_key[:16]` (`title_views.py:149-153`);
- relatório de títulos (`reconciliation_titles_report.html:10-14`);
- CSV de títulos, que sempre traz chaves de 64 caracteres, até em revisão humana (`title_views.py:672-750`);
- prévia de vínculo baixa × extrato (`reconciliation_titles_preview.html:6-7`);
- nome das regras "DE-PARA Razão/IA + 24 hex" na lista de movimentos e na configuração (`depara_ledger.py:309`, `depara_ai_auto.py:602`);
- mensagem "Arquivo gerado com hash…".

As telas de fonte recebida mostram Nota/Parcela corretamente (`reconciliation_native_titles.html:17`).

## 6. Contradições com decisões registradas

| Decisão | O que o código ou a tela faz |
|---|---|
| D-386 item 1 | Razão não é pedido no 2º mês nem em OFX que cruza meses (4.1). |
| D-388 | "Cada confirmação pode ser desfeita": o desfazer é revertido na rodada seguinte. Autor = quem importou, no caminho de reenvio. |
| D-390 | A medição de precisão conta como mantida a confirmação que foi desfeita e reconfirmada. |
| D-393 item 3 | Cumprida na letra, não na intenção de evitar duplicidade (4.2). |
| D-393 item 4 | "Deixa de aparecer como pendência": a Visão geral mostra "Precisam de revisão", as importações dizem "Aguardando revisão" e a conferência diz "A conferir". |
| D-393 item 6 | A opção "sem Razão" também aparece para empresa com banco no plano já vinculado. |
| D-394 itens 2 e 4 | `vlor` negativo ou malformado usa `vbru` em vez de deixar a parcela sem interpretação. |
| D-394 item 4 | A recusa vale para **qualquer** vínculo confirmado, mesmo igual ao novo (mais restritivo que a decisão). |
| D-394 item 5 | Sem conta com vínculo ao Razão, usa a conta mais antiga sem vínculo (interpretação do código, não escrita na decisão). |
| D-394 item 7 | A criação de conta pela descoberta ou pela configuração não dispara a interpretação; só a importação dispara. |

## 7. Correções sugeridas (priorizadas)

Esforço: **P** ≤ ½ dia · **M** 1–2 dias · **G** 3+ dias (com testes e QA de tela). Os itens marcados com † exigem decisão nova registrada antes (AGENTS.md).

| # | Correção | Prioridade | Esforço |
|---|---|---|---|
| 1 | Pedir o Razão de todo mês coberto pelo OFX em conta vinculada pela D-385: confirmar `allowed_months` pelos meses do arquivo. Conferir a conta da SURIA em produção. | Alta | M |
| 2 | Desfazer que "pega": excluir dos pares exatos o par já desfeito. | Alta | P |
| 3 | Confirmação automática tolerante: pular movimento exportado, um savepoint por par e log no lugar de `return 0` silencioso. | Alta | P |
| 4 † | Proteção contra lançamento em dobro: recoletar e reavaliar o Razão antes de exportar, janela de datas no "parecido" e/ou marco de mês fechado. | Alta | M–G |
| 5 | Retirar regra → invalidar os lançamentos D-393 aprovados e não exportados dessa regra. | Alta | P |
| 6 | Rótulos de títulos: incluir a ação automática em `title_labels.ACTIONS`, gravar `provenance` no evento D-394, tirar o "Parcela" duplicado e usar nota/parcela no CSV. | Alta | P–M |
| 7 | Linguagem de uso direto nas telas: trocar "Aguardando revisão", "conferência humana", "Precisam de revisão", "A conferir", rodapés e guia "Como usar" por estados reais (Lançado pela CICA · Exportado em … · Parecido com o Razão, não lançado · Sem regra). | Alta | M |
| 8 | Mostrar, por movimento, conferência e carteira, o que a CICA lançou e o que foi exportado; ocultar "Conferir OFX" e "Conferir importação" (ou explicar) no uso direto. | Média | M |
| 9 | Ler OFX respeitando `CHARSET:1252` (ou tentar UTF‑8 → cp1252 como no CSV). | Média | P |
| 10 | Alertar quando o OFX traz conta bancária já vinculada a outra empresa do escritório. | Média | P |
| 11 | Mandar a rotina D-393/D-395 para tarefa assíncrona (Celery), fora da requisição. | Média | P |
| 12 | Títulos: mensagem real quando o resultado for `sem_conta`; recusar `vlor` negativo; esconder "Revisar parcela" ou proteger a revisão humana no uso direto; disparar a D-394 na criação de conta por qualquer caminho. | Média | M |
| 13 | Após importar, abrir a página no topo, com o aviso visível; competência padrão = último mês fechado (Extrato e Razão, coletas). | Média | P |
| 14 | Exportações: mostrar quantos lançamentos estão prontos, sugerir o período, mensagem sem "hash" e voltar para a lista com "Baixar arquivo". | Média | P |
| 15 † | Histórico do lote 19 com o complemento do extrato (número do documento), não só o padrão da regra. | Baixa | P |
| 16 | IA: gravar o "perguntado" antes da chamada (evita pagar duas vezes); reavaliar regra ativa da IA quando o Razão confirmar o mês. | Baixa | P |
| 17 | Movimentos: largura da coluna de data e valor; anel de foco com contraste ≥ 3:1 no escuro; atalhos com 44 px. | Baixa | P |
| 18 | Comandos: `CommandError` para escritório inválido; `titulos_auto` só com empresa ativa; trava em `record_dominio_homologation` para escritório em uso direto; aviso de custo em `uso_direto --apply`. | Baixa | P |

## 8. Limites da revisão

- **Produção não consultada:** nenhuma leitura foi feita por `fly ssh`. Não se sabe se a conta da SURIA já está presa no defeito 4.1, quantos lançamentos D-393 existem nem se algum OFX real veio em cp1252. Recomenda-se leitura pontual somente leitura.
- **Razão nativo pelo agente Domínio:** no laboratório, o Razão entrou como CSV. O caminho do agente (`NativeLedgerCollection`, recoleta e `ledger_content_conflict`) foi visto só por código e pelos testes unitários. A tela de acompanhamento com agente ativo e a abertura automática da conferência não foram exercitadas.
- **IA:** nenhuma chamada foi feita (proibido e sem chave no laboratório). Comportamento visto por código e pelos 7 testes com provedor simulado; a medição às cegas em dados reais não aconteceu (V-445). O tempo da requisição web com a chamada síncrona não foi medido.
- **Concorrência:** 8 testes de travas e disputas só rodam em PostgreSQL e foram pulados no SQLite. A exportação simultânea e a pergunta em dobro à IA não foram testadas.
- **Importador do Domínio:** o leiaute do .txt foi conferido só contra o código e a especificação. Não houve importação real (D-380).
- **Volume:** carteira de 146 empresas, planos reais, nomes longos e paginação real não foram reproduzidos. As telas com dados reais podem ter quebras não vistas.
- **Ferramentas de UI:** as skills ui-ux-pro-max, Watermelon e web-design-guidelines não estão disponíveis nesta sessão, e Playwright não foi executado. Foram usados o navegador do app, checagens automáticas (rolagem, rótulos, contraste, altura de alvos) e inspeção manual.
- **Por leitura de código, sem execução:** retirada de regra × lançamentos aprovados (4.4), sobrescrita de revisão humana de títulos e duplicidade PDF × OFX.
- **Prints:** são do laboratório sintético (escritórios "Laboratório A/B/C", empresas fictícias) e servem de referência de leiaute e texto, não de dados.
