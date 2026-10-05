# Demonstração operacional — 01/10/2026

Decisão D-213. O inventário publicado encontrou oito empresas, 24 NFS-e, dez mensagens DTE e três guias, mas nenhum modelo, atividade ou evidência operacional. Além disso, a entrada cria uma conta temporária por visitante; atribuir tarefas ao proprietário não preenche a agenda pessoal desse visitante.

## Cenário

`seed_demo_operations --slug escritorio-demo` exige um escritório existente, ativo e marcado `is_demo`, trava a organização e executa em uma transação. Não chama serviços externos, storage, filas, cobrança, e-mail ou certificados. Recusa tenant real e conflito de identidade. Não redefine senhas nem sobrescreve atividades/evidências existentes. O `seed_demo` local também usa o mesmo populador.

Seis modelos cobrem fechamento contábil, divergências bancárias, fechamento fiscal, classificação de serviços, folha/encargos e documentos. São aplicados às sete empresas ativas nas competências atual e anterior: 84 atividades, 42 atribuições e três pessoas sintéticas com senha inutilizável. Datas são prazos internos ilustrativos, não vencimentos legais. Estados incluem pendente, em andamento, impedida, concluída e dispensada; há fonte indisponível, itens sem responsável e histórico de evidência humana explicitamente fictícia.

O visitante e o administrador demo exploram a agenda de Ana Martins dentro da carteira autorizada. Carteira e Gestão mostram o conjunto; contas temporárias de outros visitantes não aparecem na distribuição nem no filtro de responsáveis. Atividades demo são cenários de consulta: formulários de mutação não são anunciados no detalhe e POSTs são recusados também para membros. Simulações próprias dos outros módulos conservam seus mecanismos de sessão.

O comando é repetível: não duplica nem altera registros na mesma competência. Em uma competência nova adiciona somente os cenários ausentes. Não foi criado agendamento de renovação automática; executar o comando quando preparar um novo mês da demo. A data do cenário existente não é silenciosamente reescrita.

## Referências e revisão

UI/UX Pro Max foi lida integralmente. Buscas de produto apontaram ferramenta de produtividade e painel financeiro; a decisão adotada foi manter hierarquia, categorias e estados existentes, sem trocar tema ou composição. A busca de feedback foi apenas orientação geral; `table responsive` e `responsive` no stack HTML/Tailwind não tiveram resultado verificado. A skill landing-page-design foi consultada por seu escopo amplo de web UI, preservando as convenções do produto conforme AGENTS.

Watermelon MCP retornou e permitiu consultar `portfolio-dashboard`, descrito como tarefas agrupadas por prioridade e categoria. Foi adotada somente essa organização, já existente na CICA. Pesquisa Refero não expôs uma tela verificável. [SaaSFrame Latitude](https://www.saasframe.io/examples/latitude-project-dashboard) reforçou hierarquia de workspace; [Karbon Tasks](https://help.karbonhq.com/en/articles/1623614-overview-of-tasks) orientou responsável único, prazo e trabalho sem atribuição (conteúdo disponível na busca, abertura direta respondeu 403). Nenhuma interface ou marca foi copiada.

Web Design Guidelines: fonte Vercel atual lida integralmente, revisão completa de `dashboard.html` e `activity_detail.html`, seus includes e controles existentes. Sem violação material nova: parágrafos semânticos, dados localizados no servidor, links nativos, foco herdado, paginação e estados claros. Não foram criados CSS, animação, formulário ou operação assíncrona.

## Verificação local

- 43 testes focados e 72 subtestes passaram. Cobertura nova: cenário completo, replay imutável, recusa de tenant real, avanço de competência, agenda pessoal e recusa de POST em duas sessões e em membro demo.
- A primeira regressão encontrou fixture que supunha um único operador; agora ela seleciona explicitamente a persona de escopo parcial. Também ocorreu uma falha isolada de ordenação em teste de paginação do Console, que passou na repetição sem mudança de produto.
- Regressão integral final: 1.046 aprovados, cinco skips de concorrência PostgreSQL e 139 subtestes, em 145,80 s. Ruff do escopo, MyPy das views e arquivos novos, Django check e verificação de migrações passaram. Não há mudança de schema.
- Playwright MCP em QA isolado na porta 8015: Meu trabalho, Carteira e Gestão em 1440/375 px, filtros, detalhe, evidência de conclusão, estado vazio, erro de competência, teclado/Enter e foco de 3 px. Paisagem 812 × 375 com tema escuro e movimento reduzido; navegação sem JavaScript em contexto separado. Nenhum overflow ou erro de console observado. Capturas desktop/mobile inspecionadas em `.playwright-mcp/demo-populated-local-*.png`.
- A tentativa inicial na porta 8011 mostrou a instância anterior; a evidência válida foi repetida na porta exclusiva 8015. Não é prova de comportamento em todas as telas ou de fontes fiscais reais.

## Publicação

Imagem preparada sobre o digest exato da release 32, com apenas seis arquivos de código/templates desta entrega. A configuração temporária de release troca somente o comando de migração pelo populador demo, pois não há alteração de schema. A configuração canary, os recursos e as variáveis da produção são preservados. Incremento estimado abaixo de US$ 1,00, sem recurso recorrente novo.

Release 33 concluída. Inventário publicado: 84 atividades, seis modelos, 42 atribuições, três personas, 60 evidências e 168 eventos. Replay retornou `created: 0`; as oito empresas, 24 NFS-e, dez mensagens DTE e três guias preexistentes mantiveram suas contagens. Web/worker e health passaram. Playwright em produção conferiu as três visões em desktop/mobile, filtros, teclado/foco, detalhe, evidência, vazio/erro e tema escuro, sem overflow ou console errors. Capturas `.playwright-mcp/demo-production-*.png` inspecionadas. Abas/contextos e QA exclusivo encerrados. Evidência completa em V-246.
