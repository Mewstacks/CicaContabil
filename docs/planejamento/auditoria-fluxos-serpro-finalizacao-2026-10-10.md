# CICA — revisão dos fluxos e plano de finalização (10/10/2026)

Complemento operacional do [PLANO-MESTRE](../../PLANO-MESTRE.md), decisão D-295. Os pacotes PC-01–31 e as etapas 00–13 continuam sendo a estrutura de execução. Este documento distingue **código inspecionado**, **teste local**, **interação renderizada**, **homologação externa** e **liberação**. Inventário não significa que cada controle foi clicado ou que cada operação Serpro foi chamada.

## Estado e alcance desta revisão

- Foram enumeradas **366 rotas Django** (incluindo 191 rotas administrativas) em [inventário de rotas](inventario-rotas-2026-10-10.csv) e **1.216 controles** em 111 dos 116 templates examinados em [inventário de controles](inventario-controles-2026-10-10.csv). A extração é estática; templates condicionais, controles criados em JavaScript e permissões em tempo de execução exigem inspeção renderizada.
- As 307 referências estáticas a `{% url %}` encontradas nos templates têm nome de rota resolvido. Isso não prova que a view conclui sua ação.
- A validação externa de importação NFS-e foi **confirmada como concluída pelo responsável em 10/10/2026**. Não repetir nem pedir comprovante para prosseguir. PC-03/Q-39 deixam de ser bloqueio neste plano. Os demais pontos NFS-e (coleta, lote, classificação, recuperação, precisão e publicação coerente) conservam seus próprios critérios.
- Regressão local mais recente: **1.385 testes aprovados, 6 ignorados e 145 subtestes aprovados** com `--basetemp` na área de trabalho. Os ignorados dependem de Playwright Python opcional ou locks/transações independentes em PostgreSQL. Esse resultado não substitui PostgreSQL/CI, navegador, fonte externa ou piloto.
- O catálogo Integra possui **19 operações**. O cliente restringe serviço e verbo, usa OAuth e certificado mTLS, e as chamadas passam por workers e registros de consumo. Não houve chamada real ao Serpro nesta revisão.

## Achados que alteram a ordem de trabalho

| ID | Código/evidência | Risco e ação | Fechamento |
|---|---|---|---|
| F-01 · P0 · corrigido localmente | `src/apps/hub/tasks.py` revalida `run.requested_by` por item antes de `caixapostal.mensagens`, via `can_execute_company_operation`. | Revogação posterior à aprovação falha o item, libera a reserva como não faturável e impede a chamada ao cliente. | Teste de revogação após enfileiramento passou; ainda falta cenário em PostgreSQL com concorrência e homologação externa autorizada. |
| F-02 · P1 · corrigido localmente | `src/apps/integra/client.py` deriva a chave OAuth de impressão criptográfica de credencial, ambiente, contratante e certificado configurado. | Token de identidade anterior não é reutilizado após troca de chave/segredo/ambiente; a chave de cache não expõe segredo. | Teste de duas identidades passou; rotação em ambiente autorizado continua pendente. |
| F-03 · P1 | Há catálogo/handlers locais e testes simulados para Integra, porém V anteriores ainda não registram aceite real por operação. | Confrontar **cada serviço contratado** com versão, autorização, procuração, payload, resposta, custo, ambiguidade e recuperação; não extrapolar consulta para transmissão. | Matriz por operação com resultado do ambiente autorizado, documento/protocolo e custo, quando aplicável. |
| F-06 · P1 · corrigido localmente | O comando administrativo `integra_smoke` chamava serviço catalogado diretamente. | Agora é prévia sem rede; chamada exige `--execute` e, para serviço faturável em produção, `--approve-billable-production`. | Três testes cobrem prévia, bloqueio de custo e execução explícita; isso não substitui trilha de consumo do produto. |
| F-04 · P1 | 1.216 controles inventariados; só resolução estática de URL e testes parciais foram feitos nesta revisão. | Executar cada controle visível por papel, estado e viewport; registrar defeitos reproduzíveis, inclusive botões sem efeito e ações que alteram dados inesperadamente. | CSV enriquecido com execução, resultado, evidência, issue e reteste; zero P0/P1 aberto na liberação correspondente. |
| F-05 · P1 | Plano mestre e etapas preservam textos históricos que chamam Q-39 de aberto; a etapa 12 ainda diz “não iniciada” apesar das releases V-202–279. | Usar o estado corrente do topo do plano e D-295; reconciliar os checklists durante PC-01, sem apagar histórico de validações. | Matriz única por capacidade/release sem dois estados atuais contraditórios. |

**Limite:** F-01 e F-02 foram corrigidos e testados localmente, sem incidente ou cobrança indevida constatados. Não equivalem a validação PostgreSQL concorrente nem a homologação externa.

## Matriz de revisão de jornadas e botões

Para cada linha do CSV de controles, registrar: rota renderizada, papel, organização/empresa, estado de dados, ação esperada, ação observada, autorização, persistência/efeito colateral, feedback, evidência, resultado e issue. Repetir as ações destrutivas e pagas somente em ambiente e dados autorizados. Conferir também os controles gerados por JavaScript e os da área administrativa, que não estão integralmente descritos pelo CSV de templates do produto.

| Jornada de ponta a ponta | PC | Cenários obrigatórios para fechar |
|---|---|---|
| Público, cadastro, login, MFA, convite, recuperação, contrato e primeiro resultado | 06, 07, 08, 11, 26, 30 | Link, formulário, validação, e-mail, expiração, papel, cobrança/acesso, recusa e recuperação. |
| Carteira, empresa, equipe, agente Domínio, fontes e backup | 11, 17, 25, 26 | Adicionar/editar/revogar, escopo entre escritórios, instalação limpa, credenciais ausentes, atualização, falha de rede e arquivo final. |
| Agenda, atividade, recorrência, revisão, fechamento e evidência | 12–14, 29 | Criar/atribuir/concluir/reabrir, competência e prazo, requisitos sem fonte, erro, concorrência, perfil consultivo, histórico e prova. |
| NFS-e: A1, coleta, lista, filtros, classificação, lote, relatório e recuperação | 02–05 | Empresa/competência, NSU/página, duplicidade, certificado vencido, resultado incerto, download consistente, piloto fiscal. Importação externa já aceita por D-295. |
| Triagem: e-mail/agent, arquivo, extração, revisão, destino e checklist | 15, 16 | Duplicata, quarentena, empresa incerta, correção antes de aprovar, retentativa, hash, vínculo e documento recuperável. |
| DTE, DCTFWeb, guias, parcelamentos e ciência | 18 | Aprovação, procuração, custo/reserva, revogação entre fila e execução, documento/protocolo, falha/incerto, reconsulta sem duplicar, ciência separada de leitura. |
| Conciliação, folha, DRE, caixa, relatórios e Siescon | 19–21, 25 | Importar/mapear/revisar/exportar/conferir ERP; total e origem, diferença, PDF/XLSX, retry, layout e incompatibilidade declarados. |
| Radar, Copiloto, curadoria e rentabilidade | 22–24 e pacotes aplicáveis do plano | Fonte e frescor, resposta insuficiente, revisão humana, custo, isolamento, cobertura de dados e preço/margem só quando regra aprovada. |
| Faturamento, console, suporte, privacidade e operação | 07–10, 28–30 | Webhook idempotente, estorno, alteração de acesso, auditoria, retenção/exclusão, health, restore, rollback e incidente. |

Em **cada** percurso: testar papel autorizado e negado, estado vazio/com dados/carregando/erro/incerto, desktop/celular, teclado/foco, confirmação de ação irreversível, retorno após falha, mensagens e console. Validar a ação real e o registro final; presença visual ou HTTP 200 isolado não basta. A tela publicada deve corresponder à release e aos recursos realmente ofertados.

## Integra Contador / Serpro — contrato por operação

O ponto de entrada local é `src/apps/integra/catalog.py` e `client.py`; os fluxos de aprovação, consumo e trabalho estão em `src/apps/hub/services.py`, `tasks.py`, `dte_access.py` e `integra_access.py`. A matriz abaixo cobre todas as 19 chaves do catálogo; o catálogo é intenção implementada, não prova de contrato ativo ou homologação.

| Família | Chaves de serviço | Conferir no teste autorizado |
|---|---|---|
| Representação/DTE | `procuracao.obter`, `dte.situacao` | Titular/representante, vigência, resposta negativa, revogação e cache. |
| Caixa Postal | `caixapostal.indicador`, `caixapostal.mensagens`, `caixapostal.detalhe` | Indicador sem custo versus consultas, paginação/ponteiro, deduplicação, conteúdo sensível, leitura versus ciência, revogação durante lote. |
| DCTFWeb | `dctfweb.guia`, `dctfweb.xml`, `dctfweb.recibo`, `dctfweb.declaracao_completa` | Competência, documento/recibo correto, vínculo, indisponibilidade, custo, emissão sem presumir transmissão. |
| PARCSN | `parcelamento.parcsn.pedidos`, `parcelamento.parcsn.detalhe`, `parcelamento.parcsn.pagamento`, `parcelamento.parcsn.parcelas`, `parcelamento.parcsn.das` | Pedido/parcela/guia, datas/valor, reemissão D-149, duplicidade, resposta parcial e pagamento sem presumir quitação. |
| Outras guias e situação | `pgdasd.das`, `pgmei.das`, `pgmei.divida`, `sitfis.protocolo`, `sitfis.relatorio` | Exposição real na UI/serviço, sequenciamento protocolo→relatório, documento e autorização por empresa. |

Para **cada chave**: cruzar contrato/versão vigente, verbo e payload, credenciais e mTLS por ambiente, CNPJ autor/contribuinte, procuração, limite e custo; testar sucesso, 401/403, 429, 5xx, timeout após envio e resposta malformada. Conferir reserva, liquidação, log sem segredo, estado `incerto`, idempotência, reconsulta e bloqueio de repetição paga. Testar rotação de chaves/certificados e indisponibilidade do gateway. O comando de smoke exige confirmação explícita e não registra consumo operacional, portanto só serve para ambiente autorizado e nunca substitui os fluxos do produto. Mudança de contrato exige revisão do catálogo e das decisões, não endpoint livre. A documentação geral do [gateway Serpro](https://centraldeajuda.serpro.gov.br/duvidas/pt/avisos/avisomudancagateway/) e das [chaves/certificados](https://centraldeajuda.serpro.gov.br/duvidas/pt/area-do-cliente/chaves/) é referência de operação; o contrato detalhado de cada serviço deve ser conferido no acesso contratado.

## Sequência de conclusão e gates

1. **Validar as proteções Serpro em ambiente representativo (PC-18).** F-01/F-02 estão corrigidos localmente. Executar concorrência em PostgreSQL e, quando autorizado, rastrear as chamadas `IntegraClient.call` para demonstrar autorização no momento do efeito e rotação sem reuso de token.
2. **Executar a matriz de botões e jornadas (PC-01/11/29).** Ordenar CSV por família; testar cada controle aplicável em ambiente local/demo, registrar falha e retestar somente percursos afetados após correção. Nas telas modificadas, aplicar ui-ux-pro-max, Watermelon/pesquisa de produto, Web Interface Guidelines e Playwright desktop/celular/teclado/console, fechando as sessões.
3. **Concluir o produto NFS-e (PC-02/04/05 + PC-06/09/30 aplicáveis).** Aceitar a validação externa relatada; medir amostra fiscal e ciclo A1/NSU/retomada, resolver bloqueios reais, conferir oferta, suporte e restauração. Publicar somente com matriz de capacidade e aceite correspondentes.
4. **Completar as integrações e ciclos ainda abertos (PC-15–25).** Homologar Serpro por chave e por operação de negócio, Triagem, agente/Domínio, Siescon, conciliação/ERP, relatórios, IA e Radar com fonte, custo e retorno. Registrar capacidades não contratadas como indisponíveis, sem simular conclusão.
5. **Fechar operação comercial e produção (PC-06–10/26–30).** E-mail, cobrança→acesso, privacidade, suporte, CI obrigatório, migração/rollback, backup/restauração cronometrada, alarmes e carga D-73. Produzir dossiê e aceite **por módulo e release**; a suíte inteira só é liberada quando todos os pacotes aplicáveis tiverem evidência. PC-31/IA local definitiva permanece posterior conforme D-50/51.

Critério de saída de cada pacote: requisito e permissão decididos, percurso completo, testes de falha, evidência de fonte/destino quando aplicável, métricas D-73, documentação operacional, versão publicada e aceite. A matriz deve usar colunas separadas **implementado / validado localmente / publicado / homologado / liberado**. Sem evidência de uma coluna, ela fica pendente, exceto a confirmação expressa da NFS-e registrada em D-295.

## Referências de interação usadas nesta revisão

O catálogo Watermelon foi consultado para dashboard SaaS e tabela; não retornou exemplo pertinente. Refero e SaaSFrame também foram pesquisados sem resultado pertinente acessível. Foram usados os fluxos reais de [tarefas TaxDome](https://help.taxdome.com/article/tasks-explained), [ações em lote TaxDome](https://help.taxdome.com/article/1148-mr-1804-workflow-basic-bulk-actions), [filtros TaxDome](https://help.taxdome.com/article/111-managing-tasks) e [tarefas Karbon](https://help.karbonhq.com/en/articles/1623614-overview-of-tasks) como inspiração para conferir dono/prazo, escopo visível de seleção, filtros persistentes e feedback de ações. Isso não propõe redesenho nem substitui o design existente da CICA. A revisão de código tomou como critério as [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): nomes acessíveis, foco, erros em campos, feedback assíncrono, confirmação e estados responsivos.
