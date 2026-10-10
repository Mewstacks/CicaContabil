## Revisão de produto em 05/10/2026 — D-275/V-275

**Acompanhamento 10/10/2026 — D-295/V-294:** [inventário e protocolo de revisão de todos os controles](../auditoria-fluxos-serpro-finalizacao-2026-10-10.md). A enumeração estática foi feita; a execução botão a botão por papel, estado e viewport permanece aberta. O checklist abaixo só se encerra após registrar resultado e reteste por controle aplicável.

A [auditoria de produto](../auditoria-produto-2026-10-05.md) revisa funcionalidades, propósito
das telas e comparação online. O plano mestre contém os pacotes PC correspondentes. Nenhum gap
foi implementado nesta entrega de análise; a etapa 11 continua aberta.

- [x] Auditar transversalmente as famílias de telas e referências reais de produto.
- [x] Inspecionar 27 URLs/recortes em desktop/mobile com Playwright MCP e registrar recusas/limites.
- [x] Identificar inconsistência de escopo dos indicadores NFS-e e lacunas de revisão/curadoria/setup.
- [x] Preparar cenários por perfil e métricas propostas de usabilidade com contadores.
- [ ] Corrigir e validar PC-02/11/13/14/16/23/26/27 nas jornadas afetadas.
- [ ] Executar PC-29 com usuários; inspeção técnica não equivale a aceite de usabilidade real.
- [ ] Reconciliar oferta e capacidade homologada conforme PC-30, D-169/D-03/Q-33.

﻿# Etapa 11 â€” Validar todas as jornadas e interfaces

[Plano mestre](../../../PLANO-MESTRE.md) Â· [DecisÃµes](../../../DECISOES.md) Â· [ValidaÃ§Ãµes](../../../VALIDACOES.md)

Plano detalhado da revisÃ£o total solicitada em 22/09/2026: [telas, demonstraÃ§Ã£o e primeiro uso](../plano-revisao-total-ui-demo-onboarding-2026-09-22.md).

Matriz das 89 rotas de interface (ondas 0 a 8 executadas em 22/09/2026, com limites registrados em V-102): [matriz de telas](../matriz-telas-2026-09-22.md).

**Estado:** Em andamento: inspeÃ§Ãµes locais parciais registradas em V-039,
V-069, V-070, V-071, V-073, V-074, V-075, V-076, V-077, V-078, V-079, V-080, V-081, V-082, V-083, V-084, V-085, V-086, V-087, V-088, V-089, V-090, V-099, V-100, V-101, V-102 e V-103; nÃ£o hÃ¡ auditoria integral de todas as superfÃ­cies nem
homologaÃ§Ã£o de jornadas reais.

**DependÃªncias:** MÃ³dulos implementados.

## Cobertura atual da central â€” conferÃªncia de 24/09/2026

Esta tabela consolida o estado atual. Os checklists datados abaixo preservam o histÃ³rico de cada entrega; uma pendÃªncia antiga pode ter implementaÃ§Ã£o posterior indicada aqui. Implementado localmente nÃ£o significa homologado nem liberado para venda.

| Requisito do objetivo | EvidÃªncia atual inspecionada | O que falta para concluir |
|---|---|---|
| VisÃ£o geral como agenda pessoal, separada de carteira/gestÃ£o | dashboard em views.py filtra responsÃ¡vel, usa prazo efetivo, categorias temporais, paginaÃ§Ã£o e contexto administrativo; atribuiÃ§Ã£o em V-151 | Consulta renderizada por perfil em desktop/celular validada em V-173; faltam jornadas de altera??o completas e piloto com carteira real. |
| Fechamentos por empresa, competÃªncia e Ã¡rea, com causa/prova | closing_dashboard.py e operations.py; modelos definem requisitos e nÃ£o presumem cobertura completa; V-146/V-147 | Modelos aprovados no escritÃ³rio e observaÃ§Ãµes efetivas das fontes. V-175 confirmou que o agente atual nÃ£o entrega estado de fechamento/aceite e que `FOVGUIAINSS.SITUACAO` nÃ£o tem semÃ¢ntica homologada. |
| RecorrÃªncia idempotente e recuperaÃ§Ã£o | recurrence.py, task generate_recurring_activities e agendamento em settings; cursor persistente e concorrÃªncia com quatro conexÃµes PostgreSQL validada em V-172 | Beat/worker reais, queda e desempenho; nÃ£o basta configurar o agendamento. |
| Carteira explÃ­cita, revogaÃ§Ã£o, acesso em downloads/tarefas | controlplane.py, integra_access.py, contextos e workers; V-165 a V-170 | HomologaÃ§Ã£o do controlador, suporte e demais percursos completos. |
| NFS-e â†’ atividades | criaÃ§Ã£o de revisÃ£o e resoluÃ§Ã£o chamam sync_nfse_review_activity; comando de recomposiÃ§Ã£o; V-148 | HomologaÃ§Ã£o do percurso real e importaÃ§Ã£o de destino; V-171 corrige prova apÃ³s nova resoluÃ§Ã£o. |
| Triagem â†’ atividades | transiÃ§Ãµes em services.py e security.py chamam sync_triage_activity; arquivamento exige hash/data/destino; comando local | IdentificaÃ§Ã£o/reatribuiÃ§Ã£o ainda nÃ£o cobertas integralmente; agente e armazenamento reais. |
| ConciliaÃ§Ã£o â†’ atividades | pontos de entrada/normalizaÃ§Ã£o/confirmaÃ§Ã£o/desfazimento projetam arquivo e prova; histÃ³rico e comando de recomposiÃ§Ã£o | Arquivos reais, exportaÃ§Ã£o/importaÃ§Ã£o no destino e concorrÃªncia. |
| Folha â†’ atividades | payroll.py projeta fotografias; comparaÃ§Ã£o, revisÃ£o humana e recomposiÃ§Ã£o; V-157 a V-160 | ExtraÃ§Ã£o ERP homologada, amostras reais e inspeÃ§Ã£o do percurso. |
| DTE e Radar â†’ atividades | tasks/dte_access e reform.py chamam suas projeÃ§Ãµes; ciÃªncia separada de anÃ¡lise; Radar exige vÃ­nculo humano; comandos locais | Provedor/coleta reais, recuperaÃ§Ã£o e percurso visual completo. |
| Guias, documentos DCTFWeb e parcelamentos â†’ atividades/fechamentos | D-155 vincula cada registro Ã  atividade exclusiva; serviÃ§os, workers e comando de recomposiÃ§Ã£o projetam estado, evidÃªncia, impedimento e responsÃ¡vel sem chamada externa | Homologar semÃ¢ntica da fonte/fornecedor, recuperaÃ§Ã£o e transmissÃµes aprovadas. NÃ£o confundir emissÃ£o/consulta com aceite ou pagamento; reemissÃ£o continua dependente de D-149. |
| ObservaÃ§Ãµes de ERP â†’ processamento/obrigaÃ§Ãµes | record_source_observation implementa ordem temporal, repetiÃ§Ã£o e indisponibilidade | **SÃ³ hÃ¡ chamadas nos testes.** Adaptadores nÃ£o alimentam essa rotina; contrato e semÃ¢ntica da fonte precisam ser comprovados antes da ligaÃ§Ã£o. |
| Sem ERP e evidÃªncia humana | cadastros/modelos/evidÃªncias e avaliaÃ§Ãµes locais existentes | Homologar a jornada completa de cadastro atÃ© fechamento e posterior conexÃ£o sem duplicaÃ§Ã£o. |
| NFS-e exclusivo preservado | entrada prÃ³pria e exclusÃ£o da geraÃ§Ã£o recorrente; testes do modo comercial existentes | Piloto de configuraÃ§Ã£o DomÃ­nio Web, acumuladores, histÃ³rico e importaÃ§Ã£o homologada. |
| Auditoria, omissÃµes e recuperaÃ§Ã£o | eventos/evidÃªncias imutÃ¡veis, comandos por ponte e `recover_operational_center` para recomposiÃ§Ã£o local unificada (D-156); prazos/responsÃ¡veis preservados | Medir D-73 em ambiente autorizado; comprovar omissÃµes/revisÃµes no percurso completo. |
| ValidaÃ§Ã£o final e liberaÃ§Ã£o | PostgreSQL local V-172 e navegador local V-173/V-174, testes registrados por entrega, manual e documentaÃ§Ã£o | CenÃ¡rios concorrentes adicionais, fontes reais, recuperaÃ§Ã£o cronometrada, volume e aceite do proprietÃ¡rio continuam pendentes. |

Prioridade de implementaÃ§Ã£o restante: conferir o contrato das observaÃ§Ãµes de ERP, recuperar/provar resultados com fontes reais e tratar as lacunas concretas encontradas nos percursos. Perguntas de negÃ³cio sem resposta permanecem perguntas; esta matriz nÃ£o aprova regras novas nem altera preÃ§os.

**DecisÃµes relacionadas:** D-07, D-38, D-57.

## Escopo e checklist

- [x] Revisar site comercial, cadastro, aplicaÃ§Ã£o do escritÃ³rio, central de aprendizado e console Mewstack (V-100 a V-102; console sob MFA continua fora).
- [x] Corrigir aÃ§Ãµes sem saÃ­da, tabelas incompletas, estados confusos e ausÃªncia de evidÃªncia (V-100 a V-102).
- [ ] Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- [x] Aplicar ui-ux-pro-max e as Vercel Web Interface Guidelines nas superfÃ­cies alteradas (V-102). Watermelon nÃ£o foi consultada nesta execuÃ§Ã£o.
- [x] Inspecionar localmente parte das jornadas com navegador Playwright, registrar os estados alcanÃ§ados e fechar a sessÃ£o de QA.
- [ ] Conferir que oferta comercial e demonstraÃ§Ã£o refletem capacidades homologadas.

## Bloqueios e responsabilidade

As mÃ©tricas de aceite estÃ£o decididas em D-73, mas os estados inacessÃ­veis devem
ser registrados, nunca presumidos validados.

Regras e autorizaÃ§Ã£o externa: responsÃ¡vel pelo projeto. CÃ³digo, inventÃ¡rio e verificaÃ§Ã£o local: executor da etapa. Os IDs Q apontam ao [registro Ãºnico de dÃºvidas](../duvidas-abertas.md); nÃ£o criar a mesma pergunta em outro documento.

## Testes e aceite

Por perfil e mÃ³dulo: desktop/celular, navegaÃ§Ã£o, foco, teclado, carregamento/erro/vazio, recuperaÃ§Ã£o, console do navegador e evidÃªncia visual.

**CritÃ©rio de aceite:** O usuÃ¡rio conclui tarefas representativas sem intervenÃ§Ã£o interna nÃ£o prevista.

## EvidÃªncias e prÃ³ximo passo

V-039 registra 14 caminhos em desktop/celular, uma jornada fictÃ­cia de Triagem,
77 testes e a inspeÃ§Ã£o visual local. V-069 retomou a verificaÃ§Ã£o no navegador
interno: home, cadastro, abas, FAQ, viewport mÃ³vel, dashboard e Triagem
fictÃ­cia; a quarentena continuou bloqueando abertura/download e nÃ£o houve erro
de console nas superfÃ­cies percorridas. V-070 incluiu fila/detalhe de revisÃ£o
NFS-e e confirmou que a demonstraÃ§Ã£o recebe acesso restrito no console
Mewstack. V-071 percorreu Guias, DTE, Parcelamentos, ConciliaÃ§Ã£o, Radar e
Copiloto, onde empresa obrigatÃ³ria e fontes sintÃ©ticas ficaram explÃ­citas. V-073
tambÃ©m verificou a revisÃ£o NFS-e e sua paginaÃ§Ã£o em viewport mÃ³vel. V-074
percorreu a segunda pÃ¡gina da carteira de guias com 101 registros fictÃ­cios e
confirmou o retorno com filtros preservados, sem erro de console. V-075 fez o
mesmo na carteira de Parcelamentos e confirmou que o seletor por pÃ¡gina nÃ£o
excede o lote local de 30 empresas. V-076 acrescentou teste autenticado para a
paginaÃ§Ã£o da fila de conciliaÃ§Ã£o; a demonstraÃ§Ã£o de duas linhas nÃ£o foi usada
para alegar inspeÃ§Ã£o visual em volume. V-077 percorreu visualmente duas pÃ¡ginas
do histÃ³rico sintÃ©tico de Parcelamentos, preservando a empresa em foco. V-078
percorreu a segunda pÃ¡gina da cobertura de certificados em uma sessÃ£o fictÃ­cia,
retornou Ã  primeira e confirmou ausÃªncia de overflow horizontal em 390 px e de
erros de console. V-079 verificou em volume a ficha de empresa: os trÃªs
histÃ³ricos alcanÃ§aram a pÃ¡gina 2, a DTE retornou sem perder as outras pÃ¡ginas e
390 px nÃ£o teve overflow horizontal. V-080 percorreu a terceira pÃ¡gina filtrada
da auditoria de conciliaÃ§Ã£o com 201 eventos fictÃ­cios e retornou Ã  segunda sem
perder o filtro, tambÃ©m sem overflow em 390 px ou erro de console. V-081
conferiu no Radar fictÃ­cio a busca IBS, seu aviso e a superfÃ­cie mÃ³vel;
o teste de 101 alertas cobriu a terceira pÃ¡gina sem atribuir Ã  demonstraÃ§Ã£o uma
prova visual em volume. V-082 cobriu por teste o histÃ³rico de cobranÃ§a em trÃªs
pÃ¡ginas, mas o console Mewstack autenticado nÃ£o foi inspecionado visualmente
porque isso exigiria inserir credencial. V-083 verificou a superfÃ­cie mÃ³vel
vazia da Caixa DTE em 390 px, sem overflow horizontal ou erro de console; o
teste sintÃ©tico de 31 resultados provou a segunda pÃ¡gina sem atribuir Ã 
demonstraÃ§Ã£o uma inspeÃ§Ã£o visual de volume. V-084 verificou no onboarding
fictÃ­cio a seÃ§Ã£o de importaÃ§Ãµes vazia em 390 px, sem overflow horizontal ou
erro de console; o teste sintÃ©tico de 21 lotes provou a segunda pÃ¡gina sem
atribuir Ã  demonstraÃ§Ã£o uma inspeÃ§Ã£o visual de volume. V-085 verificou em 390
px as Ã¡reas Processamentos e ExportaÃ§Ãµes da ConciliaÃ§Ã£o, sem overflow horizontal
ou erro de console; o teste de 21 execuÃ§Ãµes e 21 exportaÃ§Ãµes provou as pÃ¡ginas
independentes sem atribuir Ã  demonstraÃ§Ã£o uma inspeÃ§Ã£o visual de volume. V-086
verificou a superfÃ­cie mÃ³vel vazia do Copiloto em 390 px, sem overflow
horizontal ou erro de console; o teste de 13 conversas provou a segunda pÃ¡gina,
a conversa selecionada e os vÃ­nculos preservados, sem atribuir Ã  demonstraÃ§Ã£o
uma inspeÃ§Ã£o visual de volume. V-087 cobriu por teste os fechamentos adiados
em duas pÃ¡ginas, mas o console Mewstack autenticado nÃ£o foi inspecionado
visualmente porque isso exigiria inserir credencial. V-088 cobriu por teste as
tentativas Claude incertas em duas pÃ¡ginas, mas o console Mewstack autenticado
nÃ£o foi inspecionado visualmente porque isso exigiria inserir credencial. V-089
verificou a decisÃ£o NFS-e da demonstraÃ§Ã£o em desktop e 390 px: o campo aponta
para a lista nativa de acumuladores da empresa, sem overflow horizontal ou erro
de console; a demonstraÃ§Ã£o nÃ£o foi usada para alegar catÃ¡logo real. V-090
percorreu a segunda pÃ¡gina de 51 candidatos sintÃ©ticos no detalhe da
ConciliaÃ§Ã£o e confirmou a superfÃ­cie em 390 px, sem overflow horizontal ou erro
de console; nÃ£o executou confirmaÃ§Ã£o, importaÃ§Ã£o ou exportaÃ§Ã£o. O Mac
permanece bloqueado para automaÃ§Ã£o nativa; console Mewstack autenticado,
todos os perfis/estados, leitor de tela, integraÃ§Ãµes e ambiente publicado
continuam sem auditoria. Nenhuma homologaÃ§Ã£o nova Ã© atribuÃ­da a esta etapa; os
demais itens do checklist continuam abertos. A existÃªncia de cÃ³digo ou testes
anteriores nÃ£o prova conclusÃ£o. Registrar comandos, ambiente, data, resultado
e limites em VALIDACOES.md e no registro de execuÃ§Ã£o. NÃ£o incluir segredos ou
dados de clientes.

## Prompt de execuÃ§Ã£o

> Execute a etapa 11 em todas as Ã¡reas da CICA, preservando o design existente. Siga integralmente o fluxo de UI do AGENTS.md, registre referÃªncias e valide tarefas completas com Playwright em desktop e celular. Corrija bloqueios funcionais e de acessibilidade e feche as sessÃµes abertas.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. NÃ£o refaÃ§a decisÃµes confirmadas. Pergunte ao responsÃ¡vel somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alteraÃ§Ãµes existentes. NÃ£o incorra em custos sem aprovaÃ§Ã£o especÃ­fica imediatamente anterior. Ao terminar, atualize os .md com mudanÃ§as, testes executados, evidÃªncias, limitaÃ§Ãµes, bloqueios e prÃ³ximo passo. NÃ£o marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitaÃ§Ã£o atual; a existÃªncia do prÃ³ximo prompt nÃ£o autoriza iniciar outra etapa.

## Continuidade da central operacional â€” 24/09/2026

A meta ativa exigiu agenda diária pessoal, carteira explícita, fechamentos por empresa/competência/área, geração recorrente e conexão dos módulos ao motor de atividades. Esses comportamentos locais foram concluídos nas versões D-125 a D-162; o que permanece aberto é a prova externa e o contrato técnico das fontes.

- [x] Remover ampliaÃ§Ã£o de carteira ao revogar a Ãºltima atribuiÃ§Ã£o de colaborador; manter visÃ£o administrativa local e fronteira externa (D-123).
- [x] Ordenar prÃ©via e fila pelo prazo efetivo, com atividades sem prazo ao final e desempate estÃ¡vel (D-124).
- [x] Separar agenda pessoal, pendências da carteira e gestão administrativa na Visão geral (D-125).
- [x] Apresentar fechamentos por empresa, competência e área com causa e evidência (D-128).
- [x] Automatizar recorrência aprovada, com idempotência e recuperação local (D-126/D-161).
- [x] Conectar pendências e resultados locais persistidos dos módulos às atividades, com recomposição unificada (D-155/D-156).
- [x] Validar localmente a jornada central em desktop/mobile, perfis e estados representativos (V-173 a V-186); piloto, fontes, carga e recuperação cronometrada permanecem abertos.

As correções iniciais abriram a implementação; a situação atual está reconciliada em V-190. Não conceder carteira automaticamente a colaboradores sem atribuição explícita.

## Agenda pessoal â€” D-125 (24/09/2026)

A VisÃ£o geral agora abre em Meu trabalho, inclusive para owner/admin, e filtra exclusivamente pelo responsÃ¡vel da tarefa dentro da carteira autorizada. Carteira apresenta trabalho compartilhado; GestÃ£o Ã© um recorte separado e restrito Ã  administraÃ§Ã£o. A agenda pagina 30 atividades, agrupa por prazo efetivo e mantÃ©m filtros/recorte na URL. A ausÃªncia de tarefa nÃ£o Ã© apresentada como confirmaÃ§Ã£o de fechamento. A distribuiÃ§Ã£o da equipe e as filas dos mÃ³dulos permanecem fora do recorte pessoal.

- [x] Implementar recortes pessoal, carteira e gestÃ£o, agrupamento por prazo e paginaÃ§Ã£o sem corte silencioso.
- [x] Agregar fechamentos e comprovações na página, integrar módulos locais e concluir recorrência (D-126/D-128/D-155).
- [x] Inspecionar renderização e interações locais em desktop/mobile com Edge/Playwright (V-173 a V-186); não substitui piloto externo.

ReferÃªncias: Karbon [tarefas](https://help.karbonhq.com/en/articles/1623614-overview-of-tasks) e [resumo/detalhe de trabalho](https://help.karbonhq.com/en/articles/5648259-what-is-the-difference-between-a-work-card-and-a-work-overlay): responsabilidade pessoal e contexto empresa/prazo. Watermelon `portfolio-dashboard`: agrupamento por prioridade. Refero nÃ£o expÃ´s telas pelo acesso disponÃ­vel; SaaSFrame permitiu consultar o catÃ¡logo pÃºblico, sem inspeÃ§Ã£o de fluxo restrito. Foram preservados os componentes e tokens CICA; nÃ£o se alega inspeÃ§Ã£o de referÃªncias autenticadas.

## RecorrÃªncia mensal â€” D-126 (24/09/2026)

- [x] Tarefa Celery/Beat local com cursor persistido por atribuiÃ§Ã£o, geraÃ§Ã£o mensal idempotente, retomada limitada e rollback conjunto de atividade/cursor.
- [x] Separar erro por atribuiÃ§Ã£o e registrar causa tÃ©cnica sem dados sensÃ­veis; geraÃ§Ã£o automÃ¡tica sem simular autor humano.
- [x] Excluir demonstraÃ§Ã£o, fontes de acesso vencidas, estado bloqueado, empresas inativas e NFS-e exclusivo; atribuiÃ§Ã£o invÃ¡lida gera atividade sem responsÃ¡vel.
- [ ] Homologar execuÃ§Ã£o concorrente PostgreSQL e queda real de worker/Beat no ambiente autorizado.

Operação e recuperação estão documentadas no manual de homologação externa. Fechamentos agregados e vínculo dos módulos locais foram concluídos; as fontes reais continuam abertas.

## Regra de fechamento â€” D-127 (24/09/2026)

- [x] Compartilhar verificaÃ§Ã£o de requisitos entre conclusÃ£o de atividade e avaliaÃ§Ã£o agregada: evidÃªncia, processamento, aceitaÃ§Ã£o e atualizaÃ§Ã£o da fonte.
- [x] NÃ£o tratar documento isolado como confirmaÃ§Ã£o humana; distinguir dispensa documentada de conclusÃ£o; pagamento independente.
- [x] Expor avaliação por empresa/área/competência na agenda com causas, sem avaliar apenas a parcela pessoal de um fechamento compartilhado (D-128).
- [ ] Ligar observaÃ§Ãµes homologadas dos mÃ³dulos ao estado atual e Ã s evidÃªncias; preservar conclusÃ£o anterior e reabertura no histÃ³rico.

A avaliação agregada está exposta na agenda desde D-128. O adaptador ERP que a alimentará com estados reais continua sem contrato semântico homologado.

## Fechamentos na agenda â€” D-128 (24/09/2026)

- [x] Expor requisitos por empresa autorizada, competÃªncia selecionÃ¡vel e Ã¡rea, considerando todos os responsÃ¡veis inclusive na visÃ£o pessoal.
- [x] Mostrar causa, responsÃ¡vel, prazo, atualizaÃ§Ã£o, contagem de evidÃªncias e acesso ao histÃ³rico; ausÃªncia de requisitos nÃ£o comprova fechamento.
- [x] Paginar empresas e preservar competÃªncia/filtros ao navegar na agenda.
- [x] Recompor o filtro mensal com rótulo acima do controle, ação compacta no desktop e largura integral no celular; revalidar claro/escuro, teclado, erro e URL (V-244).
- [ ] Homologar cobertura dos modelos de fechamento e conectar observaÃ§Ãµes reais dos mÃ³dulos.
- [x] Inspecionar localmente desktop/mobile, teclado e estados no navegador (V-173 a V-186); não substitui fonte ou piloto externo.

ComposiÃ§Ã£o preserva tokens, painÃ©is e hierarquia da agenda existente. UI/UX Pro Max consultado para divulgaÃ§Ã£o de detalhes e tratamento responsivo; recomendaÃ§Ã£o Tailwind nÃ£o foi transplantada para o CSS existente. Watermelon portfolio-dashboard orientou hierarquia por tarefa. Refero novamente nÃ£o expÃ´s conteÃºdo; SaaSFrame somente catÃ¡logo pÃºblico; Karbon retornou 403 nesta consulta (referÃªncia anterior registrada em V-144, sem nova inspeÃ§Ã£o alegada). Web Interface Guidelines atuais auditadas em dashboard.html, partial closing_dashboard.html e acrÃ©scimos de operations.css: controles nativos, rÃ³tulo/erro, foco, alvos, quebra de conteÃºdo, paginaÃ§Ã£o, links reais, estados vazios e cores existentes. V-244 comprovou visualmente o filtro mensal em desktop/mobile, claro/escuro, teclado e erro; a jornada completa de fechamento continua sujeita às provas externas registradas.

## Ponte NFS-e â†’ atividades â€” D-129 (24/09/2026)

- [x] Captura com revisÃ£o cria atividade vinculada; decisÃ£o humana conclui o trabalho local com evidÃªncia, sem simular importaÃ§Ã£o no ERP ou aceitaÃ§Ã£o oficial.
- [x] Caso, artefato, histÃ³rico e projeÃ§Ã£o operacional na mesma transaÃ§Ã£o; vÃ­nculo Ãºnico, repetiÃ§Ã£o sem duplicaÃ§Ã£o e recuperaÃ§Ã£o explÃ­cita por escritÃ³rio.
- [x] Impedir conclusÃ£o pela central enquanto o caso estiver aberto; preservar competÃªncia de emissÃ£o e nÃ£o inventar responsÃ¡vel/prazo.
- [x] Expor navegação direta da atividade ao caso de origem e inspecionar a jornada local no navegador (D-131/V-173).
- [ ] Completar recuperaÃ§Ã£o, fontes reais e demais percursos dos mÃ³dulos; D-155 jÃ¡ integra resultados Serpro persistidos sem encerrar aceite, pagamento ou fechamento.
- [ ] Homologar cliques concorrentes em PostgreSQL e fluxo real autorizado, incluindo NFS-e exclusivo.

## Ponte Triagem â†’ atividades â€” D-130 (24/09/2026)

- [x] VÃ­nculo Ãºnico de arquivo identificado com atividade; aprovaÃ§Ã£o nÃ£o conclui arquivamento.
- [x] AtualizaÃ§Ã£o transacional nas transiÃ§Ãµes humanas, varredura e retorno do agente; falha/rejeiÃ§Ã£o impedem a tarefa.
- [x] ConclusÃ£o exige estado arquivado, data, destino e hash; repetiÃ§Ã£o e recuperaÃ§Ã£o local por escritÃ³rio.
- [x] Navegação direta para o arquivo e inspeção visual local da jornada (D-131/V-173).
- [ ] Cobrir identificaÃ§Ã£o automÃ¡tica/reatribuiÃ§Ã£o de empresa ao concluir esse fluxo do mÃ³dulo; itens sem empresa ficam na fila prÃ³pria, sem atividade de empresa presumida.
- [ ] Homologar concorrÃªncia, agente e armazenamento reais; integrar demais mÃ³dulos.

## NavegaÃ§Ã£o Ã  origem e acesso â€” D-131 (24/09/2026)

- [x] Atividade vinculada leva Ã  revisÃ£o NFS-e ou arquivo da Triagem, com estado da origem e orientaÃ§Ã£o para decisÃ£o no mÃ³dulo.
- [x] Separar consulta de alteraÃ§Ã£o; auditor/financeiro nÃ£o alteram por POST direto e serviÃ§os usam a carteira vigente. SessÃ£o somente leitura nÃ£o oferece aÃ§Ãµes mutÃ¡veis.
- [x] Inspecionar jornada renderizada, teclado e responsividade locais (V-173 a V-186).
- [x] Implementar atribuição explícita das atividades avulsas/de módulo, com revalidação de vínculo, perfil e carteira (D-132/D-162).

UI/UX Pro Max consultado: busca de aÃ§Ã£o primÃ¡ria nÃ£o encontrou correspondÃªncia especÃ­fica; na repetiÃ§Ã£o houve apenas recomendaÃ§Ãµes gerais de feedback, sem transferir haptics/mobile para esta tela web. Watermelon nÃ£o encontrou bloco task, mas catÃ¡logo portfolio-dashboard confirmou hierarquia de tarefas jÃ¡ utilizada. Mantida composiÃ§Ã£o CICA e referÃªncia pÃºblica Karbon registrada em V-144, com acesso restrito nas consultas posteriores; nenhuma nova inspeÃ§Ã£o autenticada de Refero/SaaSFrame/Mobbin foi alegada. Web Interface Guidelines atuais revisadas no detalhe, partial e CSS: links reais, foco explÃ­cito, alvo de 44px, texto de acesso negado, quebra longa e nenhuma aÃ§Ã£o automÃ¡tica ao navegar. ValidaÃ§Ã£o visual permanece pendente.

## AtribuiÃ§Ã£o das atividades â€” D-132 (24/09/2026)

- [x] Administrador/proprietÃ¡rio atribui, redistribui ou remove responsÃ¡vel no detalhe da atividade aberta, com motivo e trilha.
- [x] DestinatÃ¡rio exige vÃ­nculo/usuÃ¡rio ativos, perfil operacional e carteira; nÃ£o cria permissÃ£o nem muda modelo recorrente.
- [x] Detectar envio com responsÃ¡vel anterior desatualizado; manter valores e erros no formulÃ¡rio. Atividade encerrada preserva atribuiÃ§Ã£o.
- [x] Tarefa atribuÃ­da entra em Meu trabalho; remoÃ§Ã£o volta Ã  carteira compartilhada; tratar responsÃ¡vel ausente sem falha de template.
- [ ] Homologar concorrência PostgreSQL; a interface local desktop/mobile foi inspecionada em V-173 a V-186.

UI/UX Pro Max orientou erros de campo mais resumo focÃ¡vel; formulÃ¡rio reutiliza data-form-errors de workspace.js. Watermelon busca form trouxe anÃºncios nÃ£o pertinentes (descartados); portfolio-dashboard mantÃ©m a referÃªncia de gestÃ£o por tarefa. Mantidas referÃªncias de produto e suas limitaÃ§Ãµes registradas em V-144/V-150, sem nova alegaÃ§Ã£o de inspeÃ§Ã£o autenticada. Guidelines atuais auditadas nos partials, detalhe, CSS e widgets: rÃ³tulos nativos, estado em POST com valores retidos, resumo com links/foco existente, 44px, cores semÃ¢nticas, quebra e estado sem responsÃ¡vel. Removido aria-label incorreto Grupo da DRE do campo ReferÃªncia da evidÃªncia, para usar seu rÃ³tulo visÃ­vel. Sem prova visual nova.

## ObservaÃ§Ãµes fora de ordem â€” D-133 (24/09/2026)

- [x] RepetiÃ§Ã£o exata com instante original reutiliza observaÃ§Ã£o; nÃ£o duplica evento/evidÃªncia.
- [x] Atualizar processamento e obrigaÃ§Ã£o independentemente por instante; retorno antigo nÃ£o reabre nem recua fotografia.
- [x] Empate conflitante preserva valor e exige conferÃªncia; retorno de outra dimensÃ£o nÃ£o remove conflito pendente.
- [x] EvidÃªncia vinculada Ã  observaÃ§Ã£o aplicada, sem conclusÃ£o automÃ¡tica ou simulaÃ§Ã£o de ator humano.
- [ ] Ligar adaptadores homologados Ã  rotina; validar atrasos/conflitos em fonte real e concorrÃªncia PostgreSQL.

## ConciliaÃ§Ã£o na agenda â€” D-134 / V-153

- [x] Atividade Ãºnica por arquivo, estados de processamento/trabalho distintos e origem protegida por empresa.
- [x] ConclusÃ£o com tratamento comprovado de todos os movimentos; reabertura apÃ³s desfazimento/revisÃ£o, preservando evidÃªncias.
- [x] RecuperaÃ§Ã£o explÃ­cita por escritÃ³rio e testes de fluxo local; sem confirmaÃ§Ã£o de importaÃ§Ã£o ERP.
- [x] Navegação contextual da atividade ao arquivo e permissões locais no percurso completo (D-136/V-173).
- [x] Corrigir reconfirmaÃ§Ã£o de relaÃ§Ã£o desfeita com histÃ³rico prÃ³prio imutÃ¡vel (D-135).
- [x] Expor decisÃµes no detalhe do movimento, com paginaÃ§Ã£o, legado e evidÃªncia escapada (D-137).
- [ ] Validar navegador, concorrÃªncia PostgreSQL e volume.

### HistÃ³rico de decisÃµes D-137

Consulta paginada por movimento/empresa/escritÃ³rio; resumo legÃ­vel com expansÃ£o nativa da evidÃªncia. Perfil consultivo nÃ£o recebe formulÃ¡rios de alteraÃ§Ã£o (servidor jÃ¡ recusava POST). UI/UX Pro Max: busca histÃ³rica sem correspondÃªncia especÃ­fica e segunda busca nÃ£o pertinente; adotada semÃ¢ntica nativa do projeto. Busca de stack confirmou quebra de textos longos. Watermelon nÃ£o encontrou timeline; portfolio-dashboard manteve referÃªncia da hierarquia de trabalho. Reutilizadas referÃªncias pÃºblicas Karbon/SaaSFrame/Refero e limites registrados em D-136, sem nova alegaÃ§Ã£o de acesso autenticado.

Auditoria das Web Interface Guidelines atuais em reconciliation_movement.html, partial reconciliation_decisions.html e trecho novo de operations.css: headings, time, details/summary nativos, links reais, paginaÃ§Ã£o na URL, estados vazio/legado, escape de evidÃªncia, foco explÃ­cito, alvo 44px e quebra de texto; datas/nÃºmeros usam localizaÃ§Ã£o Django. Corrigidas aÃ§Ãµes exibidas indevidamente ao perfil consultivo. Playwright retornou Transport closed em listagem/fechamento; nenhuma aba aberta, nenhum resultado visual de desktop/mobile/console alegado.

### NavegaÃ§Ã£o contextual D-136

- [x] Link da atividade abre processamentos/movimentos do arquivo autorizado; busca/paginaÃ§Ã£o preservam filtro, limpar busca nÃ£o remove arquivo.
- [x] Empresa/arquivo explÃ­citos, retorno Ã  atividade e remoÃ§Ã£o de filtro separada; indicadores gerais continuam identificados como carteira.
- [x] Arquivo invÃ¡lido/fora do escritÃ³rio retorna 404; mÃ³dulo desabilitado nÃ£o recebe link operacional.
- [x] Inspeção local desktop/mobile, teclado/foco e console realizada em V-173 a V-186.

UI/UX Pro Max consultado: navegaÃ§Ã£o por teclado e foco pertinentes; buscas de stack trouxeram z-index e depois nenhum resultado especÃ­fico, sem impor Tailwind ao CSS existente. Watermelon portfolio-dashboard confirmou hierarquia de tarefas. ReferÃªncias pÃºblicas: [Karbon](https://karbonhq.com/solution/project-management) para trabalho contextual, [SaaSFrame](https://www.saasframe.io/categories/dashboard) para organizaÃ§Ã£o por painÃ©is; [Refero](https://refero.design) sem conteÃºdo acessÃ­vel nessa consulta. Mantida linguagem visual CICA, sem alegar inspeÃ§Ã£o de fluxos autenticados. Auditoria das [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): activity_detail.html, reconciliation.html, partial reconciliation_source_context.html e trecho novo de operations.css usam links nativos, filtro na URL, textos explÃ­citos, escape automÃ¡tico, quebra de conteÃºdo longo, alvos de 44px e foco/hover. Sem animaÃ§Ã£o, imagem ou aÃ§Ã£o automÃ¡tica nova; sem style inline. Estado vazio usa estrutura existente. ValidaÃ§Ã£o renderizada permanece pendente.

### Entrada operacional da folha D-138

- [x] Tipo de importaÃ§Ã£o CSV/XLSX no fluxo existente, modelo CSV e instruÃ§Ãµes de formato; documento informado aparece na ficha da empresa.
- [x] Preservar campos ausentes, referÃªncia imutÃ¡vel e lote sem gravaÃ§Ã£o parcial; testar envio â†’ prÃ©via â†’ confirmaÃ§Ã£o â†’ consulta.
- [x] Recebimento de fotografias gera/reabre atividade de conferÃªncia (D-139).
- [x] PrÃ©via paginada de linhas da folha antes de confirmar (D-141).
- [ ] Homologar fontes/layouts reais e XLSX.
- [ ] InspeÃ§Ã£o desktop/mobile. Playwright MCP sem transporte; nenhuma sessÃ£o aberta.

UI/UX Pro Max consultado (ajuda, labels e feedback); Watermelon file-upload-1/2 orientou manter instruÃ§Ãµes junto ao envio, sem importar componentes incompatÃ­veis. Mantidas referÃªncias pÃºblicas e composiÃ§Ã£o de configuraÃ§Ã£o existentes. Web Interface Guidelines atuais revisadas em setup.html/novo choice: link real de download, instruÃ§Ã£o concreta, labels/erros e confirmaÃ§Ã£o existentes; nÃ£o hÃ¡ novo script ou animaÃ§Ã£o. A inspeÃ§Ã£o renderizada permanece pendente.

### ConferÃªncia de folha na central D-139

- [x] Uma atividade por empresa/competÃªncia, origem vinculada Ã  fotografia mais recentemente cadastrada.
- [x] Replay preserva conclusÃ£o; novo recebimento reabre e requer evidÃªncia humana posterior, sem apagar histÃ³rico.
- [x] ImportaÃ§Ã£o/fotografia/atividade transacionais; comando de recuperaÃ§Ã£o por escritÃ³rio e atribuiÃ§Ã£o existente reutilizada.
- [x] Atalho contextual Ã  ficha filtrada pela competÃªncia, retorno Ã  atividade e comparaÃ§Ã£o sem concluir trabalho (D-140).
- [ ] Regra de aplicabilidade dos documentos/obrigaÃ§Ãµes homologada, sem inferir fechamento pela conferÃªncia.
- [ ] ConcorrÃªncia PostgreSQL e jornada visual/externa.

### Contexto da competÃªncia D-140

UI/UX Pro Max orientou filtro explÃ­cito/estado na URL; busca de stack sem resultado especÃ­fico para links, mantida semÃ¢ntica nativa. Watermelon portfolio-dashboard consultado; reaproveitadas referÃªncias pÃºblicas e composiÃ§Ã£o CICA registradas nas entregas anteriores, sem nova inspeÃ§Ã£o autenticada. Web Interface Guidelines atuais auditadas em activity_detail.html, company_detail.html, partial payroll_activity_context.html e trechos de activities.css/operations.css: links nativos, rÃ³tulos concretos, valores escapados, perÃ­odo preservado no GET, estados vazio/competÃªncia, alvos 44px, foco e hover, quebra de conteÃºdo, scroll-margin nas Ã¢ncoras. A comparaÃ§Ã£o conserva labels e erro focÃ¡vel existentes. Playwright devolveu Transport closed em listagem e fechamento; nenhuma sessÃ£o aberta e nenhuma prova desktop/mobile/console.

### PrÃ©via da folha D-141

- [x] Linhas paginadas, valores originais/ausentes e empresa resolvida na fonte, sem persistÃªncia durante consulta.
- [x] ConteÃºdo restrito Ã  administraÃ§Ã£o da importaÃ§Ã£o; confirmaÃ§Ã£o oculta em perfil consultivo.
- [x] Testar 21 linhas em duas pÃ¡ginas, numeraÃ§Ã£o, escape e ausÃªncia de gravaÃ§Ã£o/acesso consultivo.
- [ ] Validar navegador e layout real. Playwright sem transporte; consulta CUA alternativa retornou apps/browsers vazios.

UI/UX Pro Max recomendou composiÃ§Ã£o em cartÃµes para evitar tabela larga no celular e quebra de tokens; Watermelon nÃ£o encontrou table, mas file-upload-1 confirmou continuidade do fluxo de envio. Reutilizadas referÃªncias pÃºblicas do contexto de configuraÃ§Ã£o, sem nova inspeÃ§Ã£o autenticada. Guidelines atuais auditadas em setup.html, partial payroll_import_preview.html e trecho CSS: lista/dl/headings nativos, paginaÃ§Ã£o na URL, foco/hover, 44px, valores escapados e quebra responsiva. Campos apresentados sÃ£o valores originais do arquivo, nÃ£o nÃºmeros recalculados/localizados. Nenhum novo script, imagem ou animaÃ§Ã£o.

### Contexto DTE D-144

- [x] Atividade aponta resumo local autorizado e mantÃ©m formulÃ¡rios prÃ³prios de evidÃªncia/anÃ¡lise.
- [x] Resumo retorna Ã  atividade vinculada; GET nÃ£o abre teor nem conclui trabalho.
- [x] Inspeção desktop/mobile, teclado e console concluída em V-263; nenhuma sessão permaneceu aberta.

UI/UX Pro Max consultado para retorno previsÃ­vel e foco; Watermelon portfolio-dashboard consultado para manter tarefa/contexto prÃ³ximos. ReferÃªncias pÃºblicas: [Karbon](https://karbonhq.com/solution/project-management), organizaÃ§Ã£o do trabalho com contexto; [SaaSFrame](https://www.saasframe.io/categories/dashboard), composiÃ§Ã£o de painÃ©is. [Refero](https://refero.design) retornou sem conteÃºdo inspecionÃ¡vel; nenhum fluxo autenticado alegado. Mantida composiÃ§Ã£o existente, sem novo sistema visual.

Auditoria das [Web Interface Guidelines atuais](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): activity_detail.html, dte_message_detail.html e partial dte_activity_context.html revisados. Links nativos e especÃ­ficos, navegaÃ§Ã£o rotulada, heading associado, conteÃºdo escapado, ausÃªncia/acesso negado explÃ­citos, foco/hover e alvos existentes de 44px em theme.css, grid/links com quebra. Sem JavaScript, imagens ou animaÃ§Ãµes novos. Contraste renderizado, responsividade e navegaÃ§Ã£o real continuam sem comprovaÃ§Ã£o por indisponibilidade do navegador.

### AnÃ¡lise do Radar D-145

- [x] FormulÃ¡rio de seleÃ§Ã£o e justificativa com erros focÃ¡veis, links de campo, labels e valores mantidos apÃ³s falha.
- [x] Links de origem e anÃ¡lises por carteira paginadas; envio indica processamento e protege alteraÃ§Ãµes nÃ£o enviadas.
- [x] Inspeção desktop/mobile, teclado, estados e console concluída em V-264; nenhuma sessão permaneceu aberta.

UI/UX Pro Max: produto de produtividade, resumo de erros e foco no stack HTML; mantida identidade CICA. Watermelon consultado (form/contact form): resultados announcement/footer sem correspondÃªncia verificada; nÃ£o usados como formulÃ¡rio. Reutilizada inspiraÃ§Ã£o portfolio-dashboard jÃ¡ consultada e referÃªncias pÃºblicas Karbon/SaaSFrame/Refero descritas acima, sem alegar fluxo autenticado.

Auditoria das guidelines atuais: reform.html, reform_analysis.html, activity_detail.html e reform-analysis.css/js. Links/botÃ£o nativos, navegaÃ§Ã£o rotulada, escape de conteÃºdo, URL externa HTTPS gov.br na nova tela, erro de formulÃ¡rio focÃ¡vel via workspace.js, campos Django com erro associado, foco/hover herdados, alvos 44px, quebra de texto e largura limitada; estado ocupado e restauraÃ§Ã£o no retorno do navegador. Sem imagem, animaÃ§Ã£o ou dados numÃ©ricos novos. Corrigido estado da saÃºde das fontes que ocultava falha atual quando havia sucesso anterior, mantendo data do sucesso. Visual/console nÃ£o verificados.

### Guia com resultado incerto D-148

- [ ] D-149: revisar a apresentaÃ§Ã£o provisÃ³ria de Resultado a confirmar para permitir reemissÃ£o com custo adicional autorizado pelo proprietÃ¡rio; manter filtro e distinÃ§Ã£o da tentativa anterior.
- [ ] Substituir orientaÃ§Ã£o de bloqueio na tela pelo fluxo cobrado apÃ³s definiÃ§Ã£o do adicional. NÃ£o considerar ausÃªncia de aÃ§Ã£o Emitir como aceite.
- [ ] Playwright desktop/mobile, teclado e console: transporte indisponÃ­vel em listagem/fechamento; nenhuma sessÃ£o aberta.

UI/UX Pro Max consultado para erro com prÃ³ximo passo e estados semÃ¢nticos; Watermelon portfolio-dashboard consultado. Reutilizadas hierarquia por tarefa e referÃªncias pÃºblicas Karbon/SaaSFrame/Refero jÃ¡ documentadas, preservando composiÃ§Ã£o CICA. A recomendaÃ§Ã£o genÃ©rica de botÃ£o Tentar novamente foi rejeitada neste caso por risco de repetiÃ§Ã£o cobrada.

Guidelines atuais auditadas em guides_center.html e guide_detail.html: select com label/nome/autocomplete, filtro na URL, status por texto alÃ©m da cor, alerta semÃ¢ntico, links/botÃµes nativos, foco/hover herdados e conteÃºdo escapado. Nova opÃ§Ã£o reutiliza controle nativo, aviso reutiliza componente existente; sem JS, imagem ou animaÃ§Ã£o novos. Estados renderizados nÃ£o inspecionados por indisponibilidade do navegador. RecuperaÃ§Ã£o documentada do resultado/consumo continua pendente na etapa 08.

### V-169 â€” HistÃ³rico das tentativas de guia

- [x] Ficha com estados por tentativa, datas, responsÃ¡vel disponÃ­vel, protocolo e distinÃ§Ã£o de legado/fictÃ­cio.
- [x] PaginaÃ§Ã£o de 20 eventos com contexto na URL; PDF anterior obtido localmente com acesso revalidado.
- [x] Testes de texto escapado, nÃ£o exposiÃ§Ã£o de retorno bruto, isolamento e revogaÃ§Ã£o.
- [ ] InspeÃ§Ã£o real desktop/celular, teclado, foco, estados vazios/erro e console: Playwright MCP sem transporte.
- [ ] ReemissÃ£o com custo de D-149 permanece separada e pendente.

UI/UX Pro Max consultado: primeira busca data history pagination retornou itens sem pertinÃªncia; busca refinada keyboard focus visible forneceu regras de foco visÃ­vel/nÃ£o oculto. Busca html-tailwind responsive overflow orientou conteÃºdo longo; adaptada a HTML/CSS Django, sem introduzir Tailwind. Watermelon blocks/activity nÃ£o encontrou correspondÃªncia; portfolio-dashboard foi consultado e contribuiu com hierarquia de estados, sem copiar cÃ³digo ou interface.

ReferÃªncias pÃºblicas: [Refero](https://refero.design/) consultado, sem conteÃºdo de fluxo acessÃ­vel; [SaaSFrame dashboards](https://www.saasframe.io/categories/dashboard), organizaÃ§Ã£o de informaÃ§Ã£o; [Karbon project management](https://karbonhq.com/solution/project-management), contexto operacional. NÃ£o houve inspeÃ§Ã£o autenticada dessas ferramentas. O padrÃ£o local de histÃ³rico da ConciliaÃ§Ã£o orientou densidade e paginaÃ§Ã£o, preservando identidade CICA.

Auditoria pelas [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), obtidas nesta execuÃ§Ã£o: guide_detail.html, partial guide_history.html e guide-history.css revisados. Hierarquia h2/h3, lista e dl semÃ¢nticos, time com data localizada Django, links nativos, foco explÃ­cito, quebra de protocolos, grid mÃ³vel, paginaÃ§Ã£o em URL e estado vazio implementados. NÃ£o hÃ¡ animaÃ§Ã£o, formulÃ¡rio nem carregamento assÃ­ncrono novo. Dados escapados e payload nÃ£o renderizado. Sem violaÃ§Ã£o material identificada na revisÃ£o estÃ¡tica; isso nÃ£o comprova contraste/layout/foco em navegador. Tentativas de listar/fechar Playwright retornaram Transport closed; nenhum navegador foi aberto. ValidaÃ§Ã£o visual continua pendente.


**Atualiza??o V-173 (24/09/2026):** Playwright local com Edge dispon?vel, apesar do MCP sem transporte. Central validada em 52 combina??es de p?gina/perfil/tema/viewport, 17 verifica??es, sem overflow ou erro de console. Capturas desktop/mobile inspecionadas; carteira e leitura do auditor verificadas. N?o foram validados todos os fluxos de altera??o, carregamento ou fontes reais. Scripts repet?veis: qa_ui_server.py (QA_REVIEW_SUITE=central), qa_central_fixture.py e qa_central_browser.cjs. Contextos/navegador e servidor encerrados. D-149/Q-40 seguem pendentes; meta ativa.

**V-177 (24/09/2026):** the local journey now covers evidence, completion, trail, and return to the agenda. For a completed activity, evidence remains available for audited corrections; block and second-completion actions are hidden because the service would reject them. Desktop/mobile synthetic validation recorded 64 screens and 22 checks without console errors or overflow. Real sources, network failure, reopening, concurrency, volume, and pilot remain pending.

**V-178 (24/09/2026):** local full regression passed: 948 tests, 3 known skips, and 25 subtests in 81.08 s. This increases confidence in the local integration, but it does not prove real sources, network recovery, concurrency under production load, timed recovery, or pilot acceptance.

**V-179 (24/09/2026):** source observation state changes now require the exact declared source capability under lock. This protects the central from a generic or unproven source setting processing or obligation status. It does not activate an adapter or substitute the required source contract and semantic mapping.

**V-180 (24/09/2026):** unified local recovery now has one-command coverage for persisted NFS-e plus guide, DCTFWeb, and PARCSN projections, including idempotent replay. This remains local-only; Triagem, reconciliation, payroll, DTE, Radar, real sources, timed recovery, volume, and pilot evidence remain open.

**V-181 (24/09/2026):** D-158 registra que qualquer custo ou modelo de cobranca requer definicao expressa do proprietario. O teste da recuperacao unificada agora cobre NFS-e, Triagem, Conciliacao, folha, DTE, guia, DCTFWeb e PARCSN no mesmo escritorio: oito fatos persistidos sem projecao sao recompostos em oito atividades e o replay e idempotente. Validacao local: 17 testes focados, Ruff, Django check e migrations. Continuam pendentes Radar, fontes reais, carga, recuperacao D-73, piloto e a reemissao cobrada D-149.

**V-182 (24/09/2026):** a recuperacao unificada tambem possui prova local do Radar: ela reprojeta somente a publicacao ja vinculada por escolha humana, sem coletar, inferir empresa, duplicar atividade ou registrar evento quando a versao e a mesma. Testes das pontes: 18 aprovados; Ruff, Django check, migrations e diff-check passaram. Fontes reais, falhas de rede, carga, D-73 e piloto continuam pendentes.

### Fonte desativada e retorno tardio (D-159)

- [x] Retorno bem-sucedido tardio fica auditavel, mas nao reativa a fonte, nao atualiza sua fotografia e nao promove a atividade para atualizada.
- [x] Falha tardia pode registrar indisponibilidade, preservando `disabled`.
- [x] Cobertura automatizada conjunta: central e pontes locais, 51 aprovados e 8 subtestes.
- [ ] Reativacao administrativa com permissao, tela e validacao visual ainda precisa de percurso especifico; nao presumir que a mudanca de status seja autorizada por outro fluxo.

**V-183 (24/09/2026):** D-159 corrige retorno tardio de fonte desativada. A prova local cobre preservacao de `disabled` e dos estados da atividade; nao cobre adaptador ERP, acao administrativa de reativacao, fonte real, carga ou piloto.

### Reativação explícita de fonte (D-160)

- [x] Owner/admin fora de suporte pode reativar somente fonte `disabled`, mediante checkbox obrigatório e mensagem de próximo passo.
- [x] Reativação conserva capacidades e fotografia, retorna para `not_configured`, não consulta fonte e registra auditoria de antes/depois.
- [x] Perfil auditor é recusado; POST sem confirmação conserva `disabled`.
- [x] Inspeção Playwright local/Edge: 66 telas e 24 verificações, desktop/390 px, foco de teclado no checkbox, sem overflow ou erro de console; servidor e navegador encerrados.
- [ ] Validar a ação com usuários reais, fonte reativada e nova sincronização autorizada; não confundir este percurso local com homologação ERP.

UI/UX Pro Max: busca `source reactivation confirmation` orientou confirmação explícita e mensagem de sucesso; `form confirmation focus` orientou foco visível. Watermelon: Agndex Dashboard (estado de integrações e configurações); referências públicas: [Refero Basedash](https://styles.refero.design/style/77b723ca-9583-4349-9b5e-2ef8b4fde002), [SaaSFrame Prelude](https://www.saasframe.io/examples/prelude-integrations-settings?733a3d33_page=2) e [Karbon](https://karbonhq.com/en-GB/integrations/aider/) para status explícito, divulgação progressiva e contexto da operação. Adotados: estado textual com próximo passo, ação localizada na fonte e confirmação antes de reativar; identidade CICA preservada. Web Interface Guidelines atualizadas foram revisadas para `setup.html` e `operations.css`: controle nativo, label clicável, foco visível, `autocomplete`, texto longo e layout móvel; sem violação material encontrada.

**V-184 (24/09/2026):** implementação e validações acima concluídas localmente; fontes externas, carga, recuperação D-73 e piloto seguem pendentes.

### Recorrência, carteira e responsável (D-161)

- [x] Motor recusa modelo/atribuição/empresa de escritórios diferentes antes de persistir atividade.
- [x] Geração manual e recorrente verificam perfil operacional, vínculo ativo e carteira corrente do responsável.
- [x] Atribuição antiga inválida gera atividade sem responsável e evento explicável, sem apagar a atribuição histórica.
- [x] Formulário administrativo recusa nova atribuição sem carteira; teste de POST confirma que não persiste o vínculo.
- [x] Playwright local/Edge percorreu página de modelos em 1440 e 390 px, com 70 telas/28 verificações gerais sem overflow ou erro de console; servidor/navegador encerrados.
- [ ] Exercitar mensagem de validação da atribuição inválida em navegador com carteira/control plane reais; a cobertura atual do erro é teste de integração Django, não homologação de escritório.

Web Interface Guidelines revisadas para o comportamento de erro da tela existente: controles e labels permanecem nativos, o erro é renderizado pelo formulário no campo e não há mudança de layout, ícone ou animação. UI/UX Pro Max e as referências de configuração operacional consultadas em V-184 permanecem aplicáveis; não houve nova direção visual.

**V-185 (24/09/2026):** implementação e validação local acima concluídas; fontes ERP, homologaçao, carga, recuperação D-73 e piloto seguem pendentes.

### Ordem consistente na ficha da empresa (D-124)

- [x] A ficha usa o mesmo prazo efetivo da agenda: interno quando preenchido; legal quando interno ausente; sem prazo ao final.
- [x] Teste cobre prazo legal vencido antes de prazo interno futuro, e item sem prazo apos os datados.
- [x] Playwright local/Edge inclui a ficha para owner, operador e auditor em 1440/390 px: 82 telas, 40 verificacoes, sem overflow nem erros de console; QA encerrado.

**V-186 (24/09/2026):** a ordenacao da ficha estava fora de D-124 por usar somente a ordenacao padrao do modelo. A lista agora usa a mesma expressao da agenda/fila. UI/UX Pro Max orientou manter a tabela responsiva existente; Watermelon nao retornou bloco de tabela adequado apos busca e nova busca. Referencia Karbon confirma o padrao de trabalho por responsavel, cliente e prazo. Web Interface Guidelines revisadas para a tela: tabela sem controles novos, links nativos e URL de paginacao preservada; nenhuma violacao material identificada. Isto nao substitui validacao de carteira real ou piloto.

### Escrita de atividade com vínculo atual (D-162)

- [x] Evidência, impedimento e conclusão revalidam membro ativo, usuário ativo, papel operacional e carteira no serviço.
- [x] Redistribuição exige o papel owner/admin atual, não uma cópia carregada antes da revogação.
- [x] Testes recusam rebaixamento e ator divergente sem criar evento, evidência ou alteração de estado.
- [ ] Exercitar revogação pelo controlador externo e concorrência PostgreSQL em ambiente homologado.

**V-187 (24/09/2026):** a correção é de permissão de serviço, sem mudança visual. A sessão e as telas continuam exibindo apenas capacidades já autorizadas; a escrita faz uma nova leitura para não confiar em estado de autorização antigo. Não substitui a integração do controlador, fontes ERP ou piloto.

**Complemento V-187 (24/09/2026):** regressão HTTP da área do escritório: `tests/test_hub_workspace_views_django.py` aprovou 76 testes em 59,27 s, cobrindo carteira, detalhes e POSTs das atividades após a revalidação de vínculo.

## Landing pÃºblica â€” D-163 / V-188 (24/09/2026)

- [x] Revisar promessa, hierarquia, demonstraÃ§Ã£o ilustrativa, recursos, integraÃ§Ãµes, FAQ e CTAs da pÃ¡gina inicial.
- [x] Consultar ui-ux-pro-max, Watermelon e referÃªncias online; registrar fontes e limites em [relatÃ³rio](../../cica-landing-review-2026-09-24.md).
- [x] Auditar todos os arquivos UI alterados pelas Web Interface Guidelines atuais e corrigir achados.
- [x] Inspecionar a landing com Playwright MCP em desktop/mobile, claro/escuro, teclado, foco, FAQ, links, temas e sem JavaScript; 12 combinaÃ§Ãµes sem overflow e 27 testes aprovados.
- [x] Fechar pÃ¡ginas/contexto adicional e encerrar servidor de QA.
- [ ] Medir conversÃ£o com trÃ¡fego real e homologar jornada comercial/integraÃ§Ãµes na etapa 12; esta revisÃ£o nÃ£o declara esses itens concluÃ­dos.

Detalhes e limites em V-188, VALIDACOES.md. Entrega limitada Ã  landing; demais pendÃªncias da etapa permanecem abertas.


## Reconciliação do checklist ativo — V-190 (24/09/2026)

Os itens acima foram revisados contra a implementação e as evidências V-125 a V-189. A agenda diária, os três recortes, os fechamentos agregados, a recorrência, as pontes locais dos módulos, a recuperação unificada, a ordenação por prazo efetivo e a revalidação da escrita já estão implementados. As caixas não concluídas agora representam somente provas ou contratos ainda ausentes: adaptação de estados ERP com semântica comprovada, contratos Siescon/Domínio, fontes e transmissão reais, concorrência/volume, recuperação cronometrada, piloto e regra comercial de reemissão D-149. Teste sintético e contagem de registros não substituem essas evidências.

### Evidência posterior à reconciliação — V-191 a V-193

- [x] Reexecutar a revisão local de recorrência e recuperação unificada: 63 testes e 16 subtestes aprovados; o único skip requer locks PostgreSQL.
- [x] Reinspecionar a central por Playwright/Edge: 82 telas, 40 verificações, três perfis, claro/escuro, 1440/390 px e cenário 844×390 com movimento reduzido, sem overflow ou console error; sessões e servidor isolado encerrados.
- [x] Pesquisar a semântica pública de Domínio e disponibilidade contratual pública do Siescon; o manual de homologação registra os artefatos necessários antes de ativar observações de processamento/obrigação.
- [ ] Obter o contrato técnico, realizar piloto autorizado e medir recuperação/carga. Essas são evidências externas, não pendências de implementação local.

## Correção da landing servida e skill permanente — V-195

- [x] Resolver a disputa da porta 8000 e verificar HTML/CSS novos na instância usada pelo proprietário; manter o servidor atual ativo.
- [x] Aplicar design e landing-page-design: fonte única, espaçamento consistente, ações sem flechas e FAQ ampliada.
- [x] Instalar landing-page-design de elayadesign/ai-design-skills e tornar seu uso obrigatório no AGENTS global.
- [x] Auditar os dois arquivos UI pelas guidelines atuais e validar 12 combinações de tamanho/tema no Playwright MCP, teclado, foco, links, temas e sem JavaScript.
- [x] Fechar todos os contextos e abas de validação; preservar o servidor do usuário.

V-188 validava somente a instância de QA; V-195 registra a correção e a inspeção da porta 8000. Permanecem os limites de conversão, homologação, Copiloto desativado nessa instância e preview social descritos no registro.

## Reconstrução integral da landing — D-168 / V-196

- [x] Descartar a composição anterior e criar estrutura, copy, demonstração de produto e CSS novos sem reutilizar `cica_motion.html`.
- [x] Trocar o verde dominante por papel quente, grafite e terracota; reservar verde para estado positivo real.
- [x] Manter teste de 14 dias como ação principal, demo e Copiloto condicionados e limites honestos das integrações.
- [x] Aplicar as skills de landing, conversão, marca, sistema visual, UI e UX relevantes; pesquisar Front, Karbon e Pennylane e consultar Watermelon.
- [x] Auditar as Web Interface Guidelines atuais, corrigir contraste e sincronizar `theme-color` com o fundo dos temas.
- [x] Validar a porta 8000 com Playwright MCP em 320, 375, 390, 768, 1024 e 1440 px, claro/escuro, teclado, foco, FAQ, links, rede, console e sem JavaScript.
- [x] Executar 27 testes focados e fechar as abas do Playwright, preservando o servidor local do usuário.
- [ ] Medir conversão e a jornada comercial com uso real; a reconstrução não comprova aumento de vendas nem homologa fonte externa.

O [relatório final](../../cica-landing-review-2026-09-24.md) substitui as direções visuais anteriores da mesma data. As demais pendências operacionais da etapa continuam abertas.

## Ajuste da rotina e das fontes — D-169 / V-197

- [x] Remover a lista numerada de três benefícios e substituí-la por uma atividade concreta com contexto operacional.
- [x] Remover os três cards de integração e toda linguagem de disponibilidade, preparação, configuração e validação da landing.
- [x] Apresentar Domínio, Integra Contador, e-mail e Siescon em uma faixa única de fontes conectadas.
- [x] Alinhar recursos e FAQ com a comunicação de produto completo solicitada pelo proprietário.
- [x] Reconsultar UI/UX Pro Max, Watermelon e as Web Interface Guidelines atuais; corrigir o achado de contraste.
- [x] Validar 12 combinações de viewport/tema, mobile/desktop, FAQ, sem JavaScript, console e contraste; 4 testes aprovados.

O ajuste é de apresentação pública e não executa provedor, custo, publicação ou medição de conversão.

## Homologação Fedrizzi V-198 — gate operacional preservado

- [x] Ler e espelhar dados allowlisted Fedrizzi sem escrita no Domínio: 576 empresas e 10.000 registros normalizados.
- [x] Habilitar os sete módulos pelo Console de desenvolvimento, sem ativar chamadas de IA ou fornecedor.
- [x] Confirmar em Edge desktop/celular que o gate de ativação impede acesso à agenda enquanto não há contrato vigente.
- [ ] Definir no Console contrato de homologação sem cobrança ou contrato real, com status e prazo aprovados, antes de abrir a agenda e criar modelos na carteira real.

Não foi presumido preço, prazo, cobrança nem regra de atividade. O contrato atual de guias não contém vencimentos e não permite fabricar cronograma de fechamento.

## Fedrizzi como parceiro interno — D-170 / V-199

- [x] Registrar condição não comercial, distinta de demo, sem fatura, preço, contrato ou provedor externo.
- [x] Disponibilizar no Console Developer/Admin a ativação e o encerramento confirmado, ambos auditados.
- [x] Aplicar a condição via tela na Fedrizzi e validar Console, Integrações e área operacional em desktop/celular/paisagem.
- [x] Corrigir a informação de teste de 14 dias na Integrações para o parceiro interno.
- [ ] Configurar modelos de trabalho, responsáveis e prazos aprovados antes de tratar a agenda vazia como uma pauta operacional real.

A ausência de vencimento nos cálculos de guia do contrato Domínio impede o sistema de criar datas ou obrigações por inferência. V-199 contém as evidências e os limites.

## V-200 — Prévia navegável das áreas da landing

25/09/2026. D-171 tornou a prova de produto da landing uma demonstração navegável. `home.html` agora apresenta tabs nativas para Central, Meu trabalho, Empresas, Documentos, Fiscal e Conciliação; cada uma exibe um recorte de trabalho consistente, inteiramente fictício. `cica-product-demo.js` controla o estado acessível, as setas Home/End/esquerda/direita, a âncora compartilhável `#demonstracao-*` e o retorno pelo histórico do navegador. Sem JavaScript, Meu trabalho continua renderizado como a tela inicial. A demonstração não autentica, não consulta a Fedrizzi nem qualquer outra fonte, e não tem ações que escrevem ou geram consumo.

UI/UX Pro Max foi aplicado para estado ativo, URL refletindo a tela e foco de teclado. Watermelon MCP não estava exposto nesta sessão. A pesquisa de referências usou [Karbon](https://karbonhq.com/solution/project-management) para a pauta por responsável, cliente e prazo, [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para a hierarquia de navegação lateral, e [Asana](https://help.asana.com/s/article/reporting-with-dashboards) para a leitura de tarefas e estados. Foram adaptados somente hierarquia, densidade e feedback; nenhuma interface, texto proprietário ou dado externo foi copiado.

A fonte atual das Web Interface Guidelines foi relida e a auditoria de `home.html`, `cica-landing.css` e `cica-product-demo.js` não encontrou violação material: buttons nativos, `tablist`/`tabpanel`, foco visível de 3 px, hover, movimento reduzido, texto com quebra e URL do estado. O MCP Playwright não estava disponível; a validação equivalente local em Edge percorreu as seis telas em 1440 e 390 px, clique, teclado, deep-link, retorno do histórico, contexto sem JavaScript e console. Não houve overflow horizontal nem erro de console. Capturas inspecionadas: `.playwright-mcp/landing-review/demo-desktop.png` e `demo-mobile.png`; contextos e browser foram fechados.

`pytest tests/test_cica_landing_django.py -q`: 4 aprovados em 65,30 s. `manage.py check --settings=config.settings.local`, sintaxe Node e `git diff --check` dos arquivos de escopo passaram. Limites: isto valida uma apresentação fictícia, não permissões, dados, operações ou resultados dos módulos autenticados.

## V-201 — Camada visual autenticada alinhada à landing

25/09/2026. D-172 substituiu a linguagem visual compartilhada das telas autenticadas sem tocar seus comportamentos. `cica-auth.css` e `cica-brand.css` agora aplicam Manrope local, papel quente, grafite, terracota, campos, botões, foco e feedback coerentes em login, cadastro, convites, recuperação e MFA. `workspace.css` aplica os mesmos tokens a todo o shell autenticado: cabeçalho, navegação, formulários, painéis, tabs, mensagens, setup e módulos que herdavam o tema anterior. Verde segue restrito a estados positivos. As URLs, forms, permissões, dados, integrações e gates operacionais foram preservados.

UI/UX Pro Max orientou hierarquia de onboarding, foco e configuração responsiva. Watermelon MCP não estava disponível. Referências: [Karbon](https://karbonhq.com/resources/videos/karbon-practice-management-best-practices-how-other-firms-are-using-karbon/) para setup de prática, [Asana](https://asana.com/resources/collections/getting-started-with-asana) para onboarding guiado e [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para hierarquia de workspace. Foram adaptados apenas padrões de densidade, orientação e estados, dentro da identidade CICA.

A validação local em Edge abriu login, cadastro, visão geral e configuração da Fedrizzi em 1440 e 390 px. Em todas as oito combinações: sem overflow horizontal, foco visível de 3 px e console sem erros. A configuração e a área de trabalho usaram o escritório parceiro interno Fedrizzi e não chamaram fonte, IA, Serpro ou cobrança. Capturas: `.playwright-mcp/d172-login-final.png`, `d172-final-signup-desktop.png`, `d172-final-workspace-desktop.png` e `d172-final-setup-mobile.png`. A fonte atual das Web Interface Guidelines foi aplicada: controles nativos, foco, responsividade, texto longo, movimento reduzido e estado de navegação na URL permanecem cobertos. O MCP Playwright não estava exposto; os contextos equivalentes locais foram fechados.

Validação automatizada em andamento nesta entrada: `test_cica_auth_flow.py`, `test_cica_signup_flow.py` e `test_hub_workspace_views_django.py`; `manage.py check --settings=config.settings.local` e `git diff --check` passaram. Limite: a camada compartilhada transforma a aparência de todas as telas que a consomem; refinamentos de estrutura específica continuam necessários se uma tela especializada revelar um problema em uso real.

## Reauditoria de facilidade de uso — D-211 / V-223

- [x] Pesquisar e melhorar descoberta do download em lote NFS-e; validar localmente desktop/celular e downloads fictícios.
- [x] Publicar e conferir as melhorias em produção (V-248: seleção, emitidas/tomadas, manifesto e legibilidade mobile).
- [ ] Repercorrer demais telas, inclusive as já auditadas, com pesquisa prévia e critérios de descoberta, clareza, esforço e recuperação.
- [x] Reauditar Acumuladores e Exportações NFS-e com busca, contexto, paginação e recuperação (V-253).
- [x] Tornar o relatório de retenções encontrável no próprio recorte da NFS-e, com ações explícitas PDF/Excel e contexto do conteúdo (V-254).
- [x] Validar seleção por empresa e entre páginas no fluxo comum com 165 notas sintéticas (V-224).
- [x] Reauditar histórico de downloads, recuperação de abertura de arquivo, identificação técnica recolhida e caminho para novo pacote (V-225).
- [x] Reauditar Empresas: busca numérica/alfanumérica, contagem filtrada, vazio, retorno do detalhe e recuperação de erro no cadastro (V-226).
- [x] Conectar revisões da empresa à NFS-e por ID autorizado, preservando contexto e lote entre empresas homônimas (V-227).
- [x] Revalidar histórico NFS-e de empresa pausada fora do escopo operacional (V-255): consulta/download preservados, escrita/coleta recusadas e carteira restrita sem ampliação.
- [x] Dar recuperação global segura a 400/403/404/500 (V-256): status real, texto neutro, ação clara, API em JSON e fallback 500 independente de template/banco.
- [x] Reauditar mapeamento e falha de processamento da Conciliação não-demo (V-257): próxima ação por exceção, mensagens verdadeiras, segredo não refletido e cartões mobile legíveis.
- [x] Completar erro de rede e validação publicada da carteira demo na nova passagem NFS-e (V-248); carteira operacional real continua dependente de autorização/homologação.

## Detalhe do escritório — D-188 / V-212

- [x] Consolidar sistemas, equipe, comercial e operação sem painéis repetidos.
- [x] Recolher homologção e Copiloto/retencão; ocultar seções operacionais vazias.
- [x] Oferecer os seis papéis vigentes no convite e excluir o papel legado.
- [x] Exibir a falha real de entrega, manter rollback e apontar erros aos campos.
- [x] Aplicar UI/UX Pro Max, Watermelon, referências SaaS e as Web Interface Guidelines atuais.
- [x] Validar desktop/tablet/celular, temas, movimento reduzido, teclado, foco, overflow, nomes acessíveis e console pelo Playwright local; browser encerrado.
- [ ] Configurar e homologar SMTP real antes de considerar convites operacionais em produção.
- [x] Publicar a alteração junto da correção de login/MFA na release 12, com snapshots prévios e health final aprovado (V-213).
- [x] Revisar a central de certificados em desktop/celular: modal fechado por padrão, cobertura com/sem A1, fila compacta, nome local, cancelamento e recuperação de erro por arquivo (V-217).
### Evidência V-218 — classificação na lista de notas

- [x] V-240: listagem/confirmar correspondência demo isoladas por sessão também para membro; auditor sem ação; upload demo recusado. Comparação disponível diretamente e filtro vazio orientado, sem carregar painéis compartilhados.
- [x] V-241: recusar as 12 rotas avançadas de Conciliação demo antes do acesso operacional, inclusive GET/POST de membro/visitante/auditor; retorno direto à comparação, testado desktop/mobile/teclado.
- [x] V-242: seleção de empresa explícita e segura na configuração não-demo; recuperação de empresa/filtro/identificador inválido, erros vinculados aos campos e responsividade com carteira sintética extensa.
- [x] V-243: tornar escolhas de empresa pesquisáveis e explícitas, apresentar importar → processar → revisar → exportar e manter a importação encontrável em carteiras extensas, com fallback nativo.
- [ ] Continuar Conciliação não-demo: reauditar mapeamento, processamento, revisão e estados de falha da exportação com dados operacionais autorizados, sem confundir testes sintéticos com homologação Q-39.

Em 29/09/2026, a classificação foi incorporada à tela principal, agrupada por empresa, com estados binários, competência anterior por padrão e download direto. Playwright local validou desktop e celular, teclado, foco, movimento reduzido, responsividade e ausência de erros; a release 21 publicou os mesmos assets. A área Revisões não aparece mais na navegação.

### Evidência V-219 — edição automática e ação em lote

Em 29/09/2026, a operação diária passou a usar o número fiscal da nota, edição do acumulador com salvamento automático e seleção por nota, empresa, página ou todos os resultados classificados do filtro. A barra contextual informa notas e empresas antes de habilitar o único download primário; NSU e hash não aparecem na interface. UI/UX Pro Max orientou seleção explícita e feedback imediato. Watermelon não retornou composição pertinente em duas buscas; foram adaptados padrões públicos de Linear, Shopify, Jira e Google Drive para seleção em massa, preservando a linguagem CICA. A auditoria das Web Interface Guidelines confirmou labels, controles nativos, `aria-live`, foco, alvos, estados desabilitados, quebra responsiva e movimento reduzido. Playwright MCP validou desktop e 390 px sem overflow ou erro de console; browser encerrado. O texto mantém Q-39 visível e não promete importação homologada no Domínio.

### V-248 — reauditoria publicada da NFS-e em lote

- [x] Confirmar em produção descoberta, filtros, escopo selecionado e downloads emitidas/tomadas.
- [x] Corrigir a identificação de empresa dentro do ZIP e manter manifesto/fotografia coerentes.
- [x] Elevar a legibilidade mobile e repetir desktop, celular, paisagem, temas, teclado, foco, vazio, loading, erro de rede, overflow e console.
- [ ] Repetir a jornada com carteira operacional real somente em ambiente e escopo autorizados; a demo e os testes não homologam o layout Domínio (Q-39).

### V-246 — Rotina fictícia completa na demo

- [x] Preencher agenda, carteira, gestão, modelos, fechamentos, evidências e histórico com um cenário sintético consistente.
- [x] Corrigir a agenda pessoal de visitantes e ocultar identidades temporárias alheias da gestão/filtros.
- [x] Auditar os dois templates alterados pelas guidelines atuais e verificar desktop/mobile, teclado, estados vazio/erro e console, localmente e em produção.

A demo possui 84 atividades; nove abertas na persona pessoal e 33 na carteira. Atividades são cenários de consulta, sem mutação compartilhada. Detalhes e fontes em [relatório](../../cica-demo-population-2026-10-01.md); homologações externas permanecem abertas.

### V-249 — Reauditoria da coleta NFS-e

- [x] Trocar texto técnico disperso por situação, próximo passo e exceções operacionais.
- [x] Revalidar desktop/mobile, temas, teclado, foco, redução de movimento, falha e recuperação.
- [x] Publicar a interface e confirmar sessão demo, assets e fila em produção.
- [ ] Continuar a reauditoria das demais telas, inclusive as já revisadas, com pesquisa prévia.

O Playwright local passou; o navegador automatizado não estava disponível depois do deploy, então
a produção foi validada por HTTP autenticado na demo e não foi declarada como inspeção visual.

### V-252 — Lista NFS-e orientada à conferência

- [x] Dar contexto na linha: movimento, contraparte, datas, serviço, valor, retenções, situação e acumulador.
- [x] Tornar entrada/saída um filtro explícito e preservar seleção/lote com feedback contextual.
- [x] Revalidar desktop 1440/1280 e mobile 375, teclado/foco, escuro, movimento reduzido, vazio e console.
- [ ] Medir o percurso com contadores em carteira operacional autorizada; a inspeção sintética não substitui piloto fiscal.

### V-255 — Histórico NFS-e de empresa pausada

- [x] Identificar no topo o modo histórico somente para consulta e explicar o que continua disponível.
- [x] Manter XML/ZIP e relatórios do acervo, sem coleta, classificação ou ampliação de carteira.
- [x] Trocar a ação impossível “Classificar” por “Ver pendências” e remover falso total pendente de nota já classificada.
- [x] Validar desktop/mobile, escuro, movimento reduzido, teclado/foco, estado vazio, seleção/download, overflow e console pelo Playwright MCP; browser e QA encerrados.
- [ ] Repetir com empresa operacional real somente em ambiente autorizado; a prova sintética não homologa fonte, layout ou política fiscal.

### V-256 — Erros globais recuperáveis

- [x] Registrar e testar handlers próprios para 400, 403, 404 e 500 com status HTTP correto.
- [x] Manter respostas de API em JSON e impedir enumeração de recurso protegido no 404.
- [x] Remover cache, bloquear sniffing e garantir fallback 500 sem template, banco ou detalhes internos.
- [x] Validar desktop/mobile, temas, movimento reduzido, teclado, foco, overflow, assets, console e retorno ao início pelo Playwright MCP; browser e QA encerrados.
- [ ] Repetir no ambiente publicado após autorização de deploy; esta entrega é validação local.

### V-257 — Mapeamento e falha de processamento da Conciliação

- [x] Priorizar mapeamento, conta, OCR ou falha antes de métricas e movimentos já normalizados.
- [x] Expor orientação segura e ação aplicável sem renderizar a exceção técnica persistida.
- [x] Diferenciar layout que iniciou processamento de layout salvo apenas para arquivos futuros.
- [x] Remover “Reaplicar regras” quando a execução não produziu movimentos.
- [x] Corrigir controles e links de erro para 44 px e converter processamentos em cartões no celular.
- [x] Validar desktop/mobile, escuro, movimento reduzido, teclado, foco, erro, escolhas preservadas, overflow e console pelo Playwright MCP; browser e QA encerrados.
- [x] Revisar localmente a tela individual e os estados sintéticos de exportação, inclusive confirmação, integridade, responsividade e erro.
- [ ] Repetir geração, download, importação e confirmação no Domínio autorizado após homologar Q-39; a prova sintética não valida o destino real.

### V-258 — Revisão individual e estados de exportação da Conciliação

- [x] Expor próximo passo único conforme movimento incompleto, revisado, rascunho, aprovado, exportado ou ignorado.
- [x] Preservar data no controle nativo, focar o resumo de erros e ocultar geração enquanto faltarem dados contábeis.
- [x] Revalidar SHA-256 no download e na confirmação; registrar ator/instante e manter confirmação idempotente.
- [x] Recusar arquivo adulterado sem alterar o estado e manter download de exportação confirmada.
- [x] Corrigir ações secundárias, alvos de 44 px, cartões mobile, overflow, hash longo e envio duplicado.
- [x] Validar desktop/mobile, escuro, movimento reduzido, teclado, foco, erro, confirmação e console pelo Playwright MCP.
- [ ] Homologar o layout e o retorno real no Domínio conforme Q-39 antes de habilitar geração/confirmação fora do QA.

### V-259 — Configuração da Conciliação

- [x] Corrigir o falso estado “pronto” com zero contas e distinguir requisito, recomendação e controles opcionais.
- [x] Expor uma próxima ação única e recolher formulários até pedido explícito, mantendo erro aberto e focado.
- [x] Preservar edição com aviso de saída, deep-link do painel e retorno à seção depois de cada escrita.
- [x] Paginar separadamente contas financeiras, plano de contas, centros de custo, períodos, layouts e regras.
- [x] Exigir motivo e confirmação progressiva para bloquear ou reabrir período.
- [x] Validar leitura sem mutação do Auditor autorizado e recusa 403 de POST.
- [x] Validar desktop/mobile, escuro, movimento reduzido, teclado, foco, erro, URL, alvos, overflow e console pelo Playwright MCP.
- [ ] Repetir a configuração com referências contábeis de uma empresa operacional autorizada; a prova sintética não homologa plano, banco ou Domínio.

### V-260 — Auditoria investigável da Conciliação

- [x] Substituir códigos internos na leitura principal por atividade, categoria e explicação legíveis.
- [x] Mostrar responsável, instante, registro afetado e resultado sem renderizar JSON, hash de IP ou metadado não permitido.
- [x] Combinar busca, atividade, resultado e intervalo na URL; recusar filtro inválido sem ampliar resultados.
- [x] Recolher UUIDs e código bruto em detalhe técnico, mantendo a referência disponível para suporte.
- [x] Paginar 50 eventos e distinguir trilha vazia de filtro sem correspondência.
- [x] Validar desktop/mobile escuro, movimento reduzido, teclado, foco de erro, detalhe, filtros, alvos, overflow e console pelo Playwright MCP.
- [ ] Definir retenção e eventual exportação somente quando a política operacional/comercial for aprovada; V-260 não cria essas regras.

### V-261 — Importação e prévia operacional da folha

- [x] Fluxo em três passos: escolher conteúdo, enviar arquivo e revisar antes de gravar.
- [x] Orientação contextual, modelo da folha, nome/tamanho do arquivo e impacto da confirmação explícitos.
- [x] Pré-validação integral da folha sem escrita, com diagnóstico por linha e confirmação oculta quando há pendência.
- [x] Arquivo idêntico já processado retorna ao histórico; formulários não enviados não recebem erros espúrios.
- [x] Histórico responsivo sem rolagem horizontal; paginação, escopo, permissões e transação preservados.
- [x] Playwright em desktop e 390 px, tema escuro, movimento reduzido, teclado/foco, erro/vazio e console.
- [ ] Homologar layouts reais CSV/XLSX com escritórios piloto; a validação local não substitui homologação externa.

### V-262 — Conferência agregada da folha por competência

- [x] Mostrar pessoas, bruto, descontos, encargos e líquido de cada fonte, sem inferir valores ausentes.
- [x] Iniciar pela competência e limitar os dois seletores ao mesmo mês, com pré-seleção sem execução automática.
- [x] Oferecer uma única ação por competência comparável e paginar o histórico sem consulta irrestrita no formulário.
- [x] Expressar diferenças como “a mais”/“a menos”, separar totais indisponíveis e apontar a atividade como próximo passo.
- [x] Corrigir foco e descrição do erro, alvos de 44 px, corte mobile, coluna redundante e ação duplicada.
- [x] Validar desktop/mobile, claro/escuro, movimento reduzido, erro, teclado/foco, URL, overflow e console pelo Playwright MCP.
- [ ] Homologar a conferência com pelo menos duas fontes reais autorizadas da mesma competência; a prova sintética não valida layout, origem nem rotina do escritório piloto.

### V-263 — Caixa Postal DTE orientada à leitura segura

- [x] Remover ação duplicada do assunto e manter um único “Abrir resumo” por mensagem.
- [x] Separar resumo local da abertura de teor que pode registrar ciência, com confirmação explícita.
- [x] Elevar filtros, metadados e ações para leitura confortável e alvos mínimos de 44 px.
- [x] Converter o histórico em cartões rotulados no celular, sem rolagem horizontal.
- [x] Preservar demo isolada por sessão, sem Serpro, ciência oficial ou consumo.
- [x] Validar desktop/mobile, claro/escuro, movimento reduzido, teclado/foco, vazio, erro, preparo, simulação, detalhe, overflow e console pelo Playwright MCP.
- [ ] Homologar consulta e abertura com credenciais, contrato e escopo DTE reais autorizados; a demo não prova ciência, paginação ou retorno do Serpro.

### V-264 — Radar como fila de triagem fiscal

- [x] Substituir a tabela horizontal por fila recente com fonte, tema, data, resumo e limite de interpretação.
- [x] Deixar “Analisar impacto” e “Abrir fonte oficial” visíveis sem rolagem; usar “Ver análises” no perfil consultivo.
- [x] Separar publicação de decisão humana e filtrar carteira extensa sem substituir o `select` nativo.
- [x] Preservar retorno aos filtros, vazio recuperável, falha de fonte sem erro bruto e aviso de saída somente para edição real.
- [x] Validar desktop/mobile, claro/escuro, movimento reduzido, teclado/foco, vazio, falha, loading, criação, Owner/Auditor, 44 px, overflow e console pelo Playwright MCP.
- [ ] Homologar coleta/completude das fontes e aplicabilidade em uma carteira fiscal real autorizada; a prova sintética não valida interpretação tributária.

### V-266 — Guias e DCTFWeb orientadas ao próximo passo

- [x] Colocar o caminho de consulta/emissão antes da carteira local extensa e manter as guias oficiais como fila prioritária quando existirem.
- [x] Expor uma ação principal por estado: emitir/repetir falha confirmada, acompanhar fila, baixar DARF ou aguardar conciliação.
- [x] Separar apuração Domínio, declaração, recibo e guia, sem apresentar chave interna como nome de documento.
- [x] Ocultar mensagem bruta do conector/provedor; manter apenas orientação segura e referência técnica recolhida.
- [x] Adaptar carteira, confirmação em lote, consulta e detalhe para celular, alvos de 44 px e zero rolagem horizontal.
- [x] Validar desktop/mobile/landscape, claro/escuro, movimento reduzido, filtros, vazio, lote, modal, teclado, falha, incerto, PDF demo, overflow e console pelo Playwright MCP.
- [ ] Homologar Serpro/contrato/credenciais e resolver D-149/Q-40 antes de declarar reemissão, custo e conclusão de atividade prontos para produção.
### V-267 — Parcelamentos orientados ao próximo passo

- [x] Colocar empresa selecionada, próximo passo, acordos e parcelas antes da carteira extensa.
- [x] Mostrar uma ação principal por estado, com revisão anterior a consulta, emissão ou lote.
- [x] Transformar tabelas em cartões legíveis no celular, com alvos de 44 px e sem overflow horizontal.
- [x] Ocultar erro bruto do provedor, preservar referência técnica recolhida e exigir confirmação para liberar operação incerta.
- [x] Validar desktop/mobile/landscape, escuro, movimento reduzido, lote, vazio, modal, teclado, foco, PDF demo e console.
- [ ] Homologar transporte, regras e documento oficial com ambiente Serpro autorizado.

### V-269 — Ficha de atividade orientada ao próximo passo

- [x] Colocar empresa, área, prazo, responsável, situação e próximo passo antes dos estados técnicos.
- [x] Traduzir requisitos de conclusão, recolher códigos e substituir tipos brutos do histórico por rótulos humanos.
- [x] Separar evidência, impedimento e conclusão; preservar dados/erros e focar o contexto inválido.
- [x] Tornar explícita a resolução do impedimento quando a conclusão válida limpa o motivo e preserva a trilha.
- [x] Validar perfil operacional e auditor, pendência, vazio, pronta, impedida, erro, modal, teclado, foco, desktop/mobile/landscape, tema escuro, movimento reduzido, overflow e console.
- [ ] Homologar atividades originadas por fontes reais autorizadas; a prova local não valida o retorno de Domínio, Serpro, caixa postal ou outra integração.

### V-270 — Central de atividades como fila de decisão

- [x] Mostrar trabalho em aberto por padrão e manter concluídas/dispensadas em filtro explícito.
- [x] Expor atraso, hoje, próximos sete dias, impedimento e fonte indisponível antes dos filtros detalhados, com contagens no escopo preservado.
- [x] Unificar área, situação, fonte, empresa, competência e responsabilidade em um formulário; tornar filtros ativos removíveis e a URL canônica/compartilhável.
- [x] Recusar filtro inválido ou combinação de prazo incompatível sem ampliar silenciosamente o resultado.
- [x] Mostrar próximo passo, prazo relativo/exato, responsável e situação; converter a tabela inteira em cartões rotulados no celular.
- [x] Validar desktop/mobile/landscape, claro/escuro, movimento reduzido, teclado/foco, erro/vazio, Owner/Auditor, back-forward cache, alvos, overflow e console pelo Playwright MCP.
- [ ] Medir o uso da fila com contadores em carteira operacional autorizada; a validação sintética não define modelos, prazos ou critérios reais do escritório.

### V-271 — Modelos de atividades como biblioteca operacional

- [x] Expor cobertura, modelos ativos, atribuições e próxima ação antes da configuração detalhada.
- [x] Separar definição, aplicação à empresa e geração de competência em etapas progressivas.
- [x] Paginar modelos/atribuições e substituir a lista irrestrita de empresas por contagens agregadas.
- [x] Recusar atribuição duplicada com erro recuperável e preservar pausa/retomada com trilha de auditoria.
- [x] Gerar a competência somente a partir de modelos mensais ativos, sem duplicar atividades.
- [x] Validar desktop/mobile/landscape, escuro, movimento reduzido, teclado/foco, erro, fluxo completo, alvos, overflow e console pelo Playwright MCP.
- [ ] Definir e homologar com o escritório piloto os modelos, responsáveis, prazos legais/internos e critérios de comprovação reais; a configuração sintética não decide essas regras.

### V-272 — Fechamentos por competência como fila de conferência

- [x] Resumir atenção, comprovação, lacunas e empresas sem sugerir total fora da página.
- [x] Priorizar exceções e mostrar empresa, área, progresso, próximo passo e uma ação direta.
- [x] Separar comprovados e manter atividades, evidências e requisitos em detalhe acessível.
- [x] Tratar ausência de requisitos como lacuna de cobertura, com destino adequado por perfil.
- [x] Recusar competência inválida sem ampliar ou substituir silenciosamente o recorte.
- [x] Validar desktop/mobile, claro/escuro, movimento reduzido, teclado/foco, detalhe, erro, navegação, overflow e console pelo Playwright MCP.
- [ ] Homologar os requisitos de fechamento e evidências com um escritório piloto e fontes reais autorizadas; a prova sintética não decide critérios contábeis.

### V-273 — Cadastro de empresas como carteira de ação

- [x] Expor prioridades da carteira antes dos filtros detalhados, respeitando o escopo autorizado.
- [x] Mostrar identidade, integrações, próximo passo e uma ação direta por empresa.
- [x] Manter busca visível e mover situação, vínculo, certificado e revisão para refinamento.
- [x] Isolar empresas sem código Domínio e recusar filtro inválido sem ampliar resultados.
- [x] Preservar dados e foco no cadastro inválido; manter paginação e cartões mobile.
- [x] Validar desktop/mobile/landscape, temas, movimento reduzido, teclado/foco, vazio, erro, modal,
  alvos, overflow e console pelo Playwright MCP.
- [ ] Homologar sincronização e edição do cadastro com a fonte Domínio real autorizada; a prova local
  não decide quem pode alterar dados sincronizados nem substitui o piloto.
