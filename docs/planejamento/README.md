# MemÃ³ria de planejamento da CICA

## Comece pelos arquivos da raiz

- [PLANO-MESTRE.md](../../PLANO-MESTRE.md): plano Ãºnico aprovado e dependÃªncias.
- [DECISOES.md](../../DECISOES.md): decisÃµes, incluindo todas as respostas de 17/09/2026.
- [VALIDACOES.md](../../VALIDACOES.md): resultados observados e limites.
- [Etapas 00â€“13 e prompts](etapas/README.md): checklists de execuÃ§Ã£o.
- [InventÃ¡rio de conclusÃ£o](inventario-conclusao.md): aplicaÃ§Ãµes, modelos, rotas, APIs, tarefas e serviÃ§os.
- [Roteiro do responsável para liberação](roteiro-do-responsavel-para-liberacao.md): materiais, decisões e aceite necessários para cada dependência externa.
- [RelatÃ³rio consolidado de desenvolvimento de 21/09](relatorio-desenvolvimento-2026-09-21.md): entregas locais, evidÃªncias, limites e bloqueios vigentes.

**Estado vigente:** etapas 00â€“03 concluÃ­das localmente; etapa 04 em andamento e bloqueada por Q-33. V-041 revalidou em 21/09 o estado local, a recusa segura da exportaÃ§Ã£o Siescon e a sincronizaÃ§Ã£o com `origin/main`, sem homologaÃ§Ã£o externa. V-044â€“V-068 reduziram localmente a dÃ­vida de tipos de 535 ocorrÃªncias para zero nos 190 arquivos verificados, sem alterar integraÃ§Ãµes; V-068 repetiu a regressÃ£o integral com 762 testes aprovados. V-072 concluiu a prova local do runtime privado e do bloqueio de fallback externo sem opt-in; V-073 avanÃ§ou detalhe e paginaÃ§Ã£o NFS-e com dados sintÃ©ticos, V-074 eliminou o corte silencioso da carteira de guias, V-075 fez o mesmo na carteira de Parcelamentos respeitando seu lote de 30, V-076 na fila OFX Ã— DomÃ­nio, V-077 no histÃ³rico de operaÃ§Ãµes PARCSN e V-078 na cobertura de certificados. As frentes locais independentes das etapas 05â€“11 tÃªm evidÃªncias recentes â€” inclusive V-040 para o contrato local do cliente Asaas â€” mas nÃ£o substituem dependÃªncias nem homologaÃ§Ãµes externas. A limitaÃ§Ã£o de D-60 Ã  etapa 00 Ã© histÃ³rica e nÃ£o substitui o estado do [plano mestre](../../PLANO-MESTRE.md). Os registros datados abaixo permanecem como evidÃªncia histÃ³rica e nÃ£o substituem a memÃ³ria vigente na raiz.

**AtualizaÃ§Ã£o V-079:** a ficha de empresa agora permite percorrer seus trÃªs histÃ³ricos locais sem corte silencioso, com evidÃªncia sintÃ©tica de navegador e regressÃ£o integral de 769 testes. IntegraÃ§Ãµes fiscais continuam pendentes.

**AtualizaÃ§Ã£o V-080:** a trilha da auditoria de conciliaÃ§Ã£o agora pagina eventos sem corte silencioso, preserva o filtro e foi verificada com 201 eventos fictÃ­cios; a regressÃ£o integral local alcanÃ§ou 770 testes aprovados. IntegraÃ§Ãµes e homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-081:** o Radar da Reforma agora pagina alertas sem corte silencioso e mantÃ©m seus filtros; a prova de 101 alertas Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 771 testes aprovados. Fontes oficiais e homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-082:** o console da plataforma agora permite percorrer o histÃ³rico manual de faturas sem corte silencioso; a prova de 25 faturas Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 772 testes aprovados. CobranÃ§a e homologaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-083:** a Caixa DTE agora permite percorrer seu histÃ³rico de resultados sem corte silencioso e sem alterar a pÃ¡gina das mensagens; a prova de 31 itens Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 773 testes aprovados. Serpro, consumo e homologaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-084:** o onboarding agora permite percorrer o histÃ³rico de importaÃ§Ãµes sem corte silencioso e conserva fonte e prÃ©via selecionadas; a prova de 21 lotes Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 774 testes aprovados. Upload, backup e homologaÃ§Ã£o DomÃ­nio continuam pendentes.

**AtualizaÃ§Ã£o V-085:** a ConciliaÃ§Ã£o agora permite percorrer seus histÃ³ricos de processamentos e exportaÃ§Ãµes sem corte silencioso e sem deslocar a outra trilha; a prova de 21 itens em cada histÃ³rico Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 775 testes aprovados. ERP e homologaÃ§Ã£o de exportaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-086:** o Copiloto agora permite percorrer todo o histÃ³rico de conversas abertas sem corte silencioso e preserva a conversa selecionada; a prova de 13 conversas Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 776 testes aprovados. IA, curadoria e homologaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-087:** o console da plataforma agora permite percorrer todos os fechamentos ainda adiados sem corte silencioso; a prova de 31 ocorrÃªncias Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 777 testes aprovados. CobranÃ§a e homologaÃ§Ã£o Asaas continuam pendentes.

**AtualizaÃ§Ã£o V-088:** o console da plataforma agora permite percorrer todas as tentativas Claude incertas sem corte silencioso; a prova de 21 auditorias Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 778 testes aprovados. IA e homologaÃ§Ã£o operacional continuam pendentes.

**AtualizaÃ§Ã£o V-089:** a revisÃ£o NFS-e agora valida o acumulador no catÃ¡logo da prÃ³pria empresa; a prova de regras e observaÃ§Ãµes Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 779 testes aprovados. ADN e homologaÃ§Ã£o fiscal continuam pendentes.

**AtualizaÃ§Ã£o V-090:** o detalhe de conciliaÃ§Ã£o agora permite percorrer todos os candidatos no recorte de datas, sem corte silencioso apÃ³s 50; a prova de 51 candidatos Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 780 testes aprovados. ERP, arquivo e homologaÃ§Ã£o de exportaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-091:** o detalhe da Triagem agora permite percorrer todo o histÃ³rico persistido do arquivo sem corte silencioso; a prova de 21 eventos Ã© sintÃ©tica e a regressÃ£o integral local alcanÃ§ou 781 testes aprovados. Caixa, scanner, agente e homologaÃ§Ã£o do destino continuam pendentes.

**AtualizaÃ§Ã£o V-092:** a carteira de movimentos da ConciliaÃ§Ã£o agora preserva as pÃ¡ginas abertas de Processamentos e ExportaÃ§Ãµes ao navegar; a prova de 21/21/51 registros Ã© sintÃ©tica e a regressÃ£o integral local manteve 781 testes aprovados. ERP, arquivo e homologaÃ§Ã£o de exportaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-093:** a fila OFX Ã— DomÃ­nio agora preserva as pÃ¡ginas abertas de Processamentos, Movimentos e ExportaÃ§Ãµes; a prova de 101 correspondÃªncias Ã© sintÃ©tica e a regressÃ£o integral local manteve 781 testes aprovados. ERP, arquivo e homologaÃ§Ã£o de exportaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-094:** a Caixa DTE agora preserva simultaneamente a pÃ¡gina de mensagens e a pÃ¡gina do histÃ³rico de consultas; a prova de 31/26 registros Ã© sintÃ©tica e a regressÃ£o integral local manteve 781 testes aprovados. Serpro, consumo e homologaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-095:** Jornadas nÃ£o figura mais no catÃ¡logo do produto, mantendo apenas enum, schema e migraÃ§Ãµes histÃ³ricos conforme D-43; a regressÃ£o integral local manteve 781 testes aprovados. MigraÃ§Ã£o de produÃ§Ã£o e homologaÃ§Ã£o comercial continuam fora desta evidÃªncia.

**AtualizaÃ§Ã£o V-096:** formulÃ¡rios, views e template operacionais Ã³rfÃ£os de Jornadas foram removidos conforme D-43, preservando enum, modelos, tabelas e migraÃ§Ãµes histÃ³ricos; a regressÃ£o integral local manteve 781 testes aprovados. MigraÃ§Ã£o de produÃ§Ã£o e homologaÃ§Ã£o comercial continuam fora desta evidÃªncia.

**AtualizaÃ§Ã£o V-097:** a ConciliaÃ§Ã£o rejeita XLSX corrompido antes de persistir uma fonte e sua prÃ©via CSV sÃ³ lÃª as linhas exibidas; a regressÃ£o integral local alcanÃ§ou 783 testes aprovados. A prova Ã© local, sem arquivo, ERP ou OCR homologados.

**AtualizaÃ§Ã£o V-098:** a ConciliaÃ§Ã£o rejeita PDF malformado antes de persistir fonte, lote ou processamento e mantÃ©m PDF digitalizado vÃ¡lido no fluxo de OCR local; a regressÃ£o integral local alcanÃ§ou 784 testes aprovados. A prova Ã© local, sem OCR, arquivo, ERP ou exportaÃ§Ã£o homologados.

**AtualizaÃ§Ã£o V-099:** a demonstraÃ§Ã£o isolada da ConciliaÃ§Ã£o passou por inspeÃ§Ã£o local em desktop e celular, sem overflow horizontal ou erros de console; nÃ£o houve upload, integraÃ§Ã£o, cobranÃ§a ou homologaÃ§Ã£o.

Atualizado em 15/09/2026. Esta pasta reÃºne as decisÃµes e dÃºvidas extraÃ­das dos planos antigos do Claude, do histÃ³rico local do Codex, dos documentos do repositÃ³rio e das confirmaÃ§Ãµes recentes do responsÃ¡vel. Ela Ã© uma memÃ³ria de produto e execuÃ§Ã£o; nÃ£o equivale a homologaÃ§Ã£o, aprovaÃ§Ã£o de preÃ§o, parecer jurÃ­dico ou autorizaÃ§Ã£o de gasto.

## Como ler

1. [Fontes e histÃ³rico](fontes-e-historico.md) identifica a origem e a Ã©poca de cada plano, inclusive ideias substituÃ­das ou pertencentes a outros produtos.
2. [DecisÃµes](decisoes.md) separa confirmaÃ§Ã£o direta do responsÃ¡vel, regra registrada em plano e proposta sem confirmaÃ§Ã£o. Um plano nunca prova que uma funÃ§Ã£o foi implementada.
3. [Estado operacional](estado-operacional.md) compara intenÃ§Ã£o com evidÃªncia local e aponta o que falta validar para uma oferta vendÃ¡vel.
4. [DÃºvidas abertas](duvidas-abertas.md) concentra respostas necessÃ¡rias antes de fechar regras, alterar contratos, ativar integraÃ§Ãµes ou publicar promessas.
5. [CatÃ¡logo de triagem a confirmar](catalogo-triagem-a-confirmar.md) preserva a transcriÃ§Ã£o das 19 linhas da fotografia, sem tratÃ¡-las como taxonomia aprovada.
6. [AnÃ¡lise consolidada de 21/09/2026](analise-projeto-2026-09-21.md) sintetiza o objetivo final, arquitetura, maturidade por mÃ³dulo, revalidaÃ§Ã£o e bloqueio atual. A [anÃ¡lise anterior de 19/09](analise-projeto-2026-09-19.md) permanece como evidÃªncia histÃ³rica.
7. [Matriz de evidÃªncias de conclusÃ£o](matriz-evidencias-2026-09-19.md) conecta cada etapa Ã s provas locais, homologaÃ§Ãµes ausentes e bloqueios objetivos.
8. [AvaliaÃ§Ã£o histÃ³rica de Jornadas](avaliacao-jornadas.md) registra a funÃ§Ã£o substituÃ­da pela Triagem.
9. [Pesquisa de custo e proposta de cotas da IA](precificacao-e-cotas-ia.md) calcula um cenÃ¡rio Sonnet e separa proposta de aprovaÃ§Ã£o.
10. [Registro de execuÃ§Ã£o](registro-de-execucao.md) guarda testes, mudanÃ§as, limites e provas externas ainda necessÃ¡rias.
11. [Auditoria das telas de 15/09](auditoria-ui-2026-09-15.md) registra pesquisa de interface, revisÃ£o das diretrizes web e inspeÃ§Ã£o Playwright com seus limites.
12. [OperaÃ§Ã£o Asaas](asaas-operacao.md) separa o receptor de webhook jÃ¡ implementado da criaÃ§Ã£o de cobranÃ§as e da homologaÃ§Ã£o ainda pendente.
13. [OperaÃ§Ã£o do Radar da Reforma](radar-operacao.md) registra a coleta existente, o estado mostrado ao escritÃ³rio e as provas locais sem ampliar a promessa do mÃ³dulo.
14. [AtivaÃ§Ã£o operacional da IA](ia-operacao.md) registra a chave central, controles, contagem gratuita e uma geraÃ§Ã£o sintÃ©tica real autorizada sem armazenar segredo.
15. [ConexÃ£o das caixas de e-mail](conexao-caixas-email.md) define a jornada simples do escritÃ³rio, a preparaÃ§Ã£o OAuth central da Mewstack, a exigÃªncia de verificaÃ§Ã£o Google e as provas ainda necessÃ¡rias.
16. [AÃ§Ãµes do responsÃ¡vel](acoes-do-responsavel.md) separa o que jÃ¡ foi provado da preparaÃ§Ã£o de contas, credenciais, contratos e regras que sÃ³ o responsÃ¡vel pode autorizar.
17. [RevisÃ£o crÃ­tica da conexÃ£o de e-mail](auditoria-triagem-oauth-2026-09-15.md) registra a jornada renderizada, evidÃªncia de desktop/celular/teclado e bloqueios concretos de uso real.
18. [PadrÃ£o de pasta Windows por empresa](padrao-pastas-windows.md) define o componente com nome + cÃ³digo DomÃ­nio e separa a validaÃ§Ã£o local do arquivamento no agente.
19. [Mensalidade, franquia e tokens por mÃ³dulo](precificacao-tokens-modulos.md) pesquisa concorrentes/custos, registra o modelo decidido e distingue nÃºmeros propostos de preÃ§os aprovados.
20. [Conversa e recuperaÃ§Ã£o do Copiloto](auditoria-copiloto-conversa-recuperacao-2026-09-15.md) registra o bloqueio real de empresa no envio, a correÃ§Ã£o, o estado incerto visÃ­vel, idempotÃªncia e limites do suporte.
21. [Coleta NFS-e pelo ADN](auditoria-nfse-adn-2026-09-16.md) registra o contrato oficial, cliente mTLS, checkpoint, recuperaÃ§Ã£o, Ã¡rea de trabalho e a homologaÃ§Ã£o externa ainda pendente.

## Regra de atualizaÃ§Ã£o

Cada nova decisÃ£o deve registrar texto exato da escolha, data, quem confirmou, fonte, escopo, efeito sobre decisÃµes anteriores e pendÃªncias decorrentes. Se duas fontes divergem, registrar o conflito e perguntar; nÃ£o escolher pelo cÃ³digo, pela data do plano ou pela preferÃªncia de quem implementa. Uma confirmaÃ§Ã£o posterior e explÃ­cita do responsÃ¡vel pode resolver o conflito, mas somente no escopo que ela cobre.

Para estado tÃ©cnico, distinguir **existe no cÃ³digo**, **tem teste automatizado**, **foi exercitado em ambiente real** e **estÃ¡ liberado para venda**. AlteraÃ§Ãµes nÃ£o commitadas aparecem como trabalho em andamento e exigem nova verificaÃ§Ã£o antes de serem tratadas como entrega.

Os arquivos de sessÃ£o do Codex e de planos do Claude ficam fora do repositÃ³rio. As escolhas essenciais estÃ£o transcritas aqui para que a memÃ³ria nÃ£o dependa da presenÃ§a desses arquivos na mÃ¡quina de outra pessoa. NÃ£o copiar credenciais, certificados, dados de cliente, chaves ou conteÃºdo integral de conversas para a documentaÃ§Ã£o.
