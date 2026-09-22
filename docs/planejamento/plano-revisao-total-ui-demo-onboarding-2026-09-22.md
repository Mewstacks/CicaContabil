# Plano de revisão total das telas, demonstração e primeiro uso

Data: 22/09/2026  
Escopo: etapa 11 — jornadas e interfaces  
Estado: plano de execução; nenhuma alteração de interface ou comportamento foi feita por este documento.

## 1. Objetivo

Revisar integralmente as superfícies da CICA para que um operador contábil consiga:

1. reconhecer onde está e qual empresa/competência está em foco;
2. identificar o que exige atenção sem ler blocos extensos;
3. concluir a tarefa principal com o menor número razoável de decisões;
4. distinguir dado real, dado fictício, sugestão de IA, pendência e resultado confirmado;
5. aprender o sistema e cada módulo no primeiro uso sem tutorial obrigatório ou permanente;
6. entrar novamente na demonstração pública isolada, sem dados, integrações ou cobranças reais.

O trabalho abrange as **76 templates HTML**, as superfícies compartilhadas de CSS/JavaScript e as **78 rotas inventariadas**: 44 telas/estados e 34 ações, downloads ou APIs com efeito visível. A revisão anterior tinha 34 telas com inspeção visual, 15 fluxos exercitados e 29 rotas ainda sem inspeção específica. A nova execução deve fechar a matriz inteira sem transformar simulação local em homologação externa.

## 2. Diagnóstico atual

### 2.1 O que deve ser preservado

- A identidade CICA, a navegação por áreas e os tokens semânticos já existentes.
- A organização orientada a pendências da Visão geral.
- Tabelas densas no desktop e cartões legíveis no celular.
- Escopo de escritório sempre visível.
- Estados de permissão, demonstração, resultado incerto e trilha de auditoria.
- Tema claro/escuro/sistema, foco visível e navegação por teclado.
- Isolamento por sessão e bloqueio de egressão da demonstração.

### 2.2 Problemas que o plano precisa resolver

- Textos de apoio longos e repetidos competem com a tarefa principal.
- Nem todas as páginas deixam evidente a próxima ação ou o motivo de um bloqueio.
- A ajuda está espalhada em instruções de página, sem um padrão curto e recuperável.
- Estados vazios, de carregamento, falha e permissão não seguem ainda um contrato único.
- Alguns fluxos exigem que o operador reconstrua mentalmente empresa, competência, origem e consequência.
- A demonstração sumiu da home local por divergência de configuração: o ambiente aponta para `cica-demo`, enquanto a organização fictícia existente usa `escritorio-demo`. Os controles `DEMO_ENTRY_ENABLED` e `DEMO_SESSION_ISOLATION_READY` continuam ativos; a rota e os testes de isolamento continuam no código.

## 3. Pesquisa de mercado e padrões adotados

### 3.1 Produtos e comportamentos observados

| Referência | Padrão útil para a CICA | Adaptação proposta |
|---|---|---|
| [Conta Azul Mais — painel inicial](https://ajuda.contaazul.com/hc/pt-br/articles/47096374385677-Conta-Azul-Mais-como-funciona-o-novo-painel-inicial) | Home diferente para carteira vazia e carteira ativa; indicadores clicáveis; pendências com gravidade, cliente, origem e atalho para resolver | Visão geral adaptativa, sem gráficos decorativos: primeira configuração quando vazio; pauta e exceções quando ativo |
| [Karbon — gestão para escritórios contábeis](https://karbonhq.com/solution/bookkeeping/) | Trabalho recorrente por cliente, prazos, responsáveis, documentos e revisão em um fluxo compartilhado | Toda fila CICA preserva empresa, competência, responsável/estado e próxima ação |
| [QuickBooks Online Accountant — practice management](https://quickbooks.intuit.com/ca/accountants/features/practice-management/) | Projetos, tarefas, clientes e documentos no mesmo contexto; filtros por cliente e responsável | Filtros operacionais devem reduzir a carteira e sobreviver ao detalhe/retorno |
| [Dext — inbox documental](https://help.dext.com/en/articles/416748-the-sales-inbox) | Separação explícita entre entrada, processamento, revisão/aprovação e arquivo | Triagem usa estados simples, mutuamente compreensíveis e com ação compatível |
| [BlackLine — transaction matching](https://www.blackline.com/products/financial-close/transaction-matching/) | Automação do óbvio e trabalho humano concentrado nas exceções; busca, motivo, aprovação e auditoria | Conciliação começa pelas ambiguidades e preserva evidência, motivo e autoria da decisão |
| [SaaSFrame — estados vazios](https://www.saasframe.io/patterns/empty-state) | Vazio explica por que não há conteúdo e oferece uma ação concreta | Nenhuma tela termina em branco ou em “nenhum registro” sem próximo passo possível |
| Watermelon UI — Astrix, Tallie, Demostack e Gridline | Workspaces responsivos, orientados a revisão, exceções e contexto operacional | Usar hierarquia compacta, superfícies neutras, uma ação primária e estados semanticamente distintos |

Refero, Mobbin e Pageflows foram pesquisados para padrões equivalentes, mas a busca pública não retornou exemplos próximos e inspecionáveis o bastante para sustentar decisões específicas. Eles não serão citados como evidência visual da execução.

### 3.2 Pesquisa específica do domínio fiscal

- A [documentação atual da NFS-e Nacional](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual) reforça que documento, evento, NSU, origem e esquema precisam permanecer rastreáveis.
- O [manual da DCTFWeb](https://www.gov.br/receitafederalsimples/pt-br/centrais-de-conteudo/publicacoes/manuais/manual-dctfweb/manual-dctfweb-outubro-2021.pdf) mostra que declaração, situação, saldo, transmissão e documento de arrecadação são conceitos diferentes. A interface não deve colapsá-los em um único “pronto”.
- A Receita informa que o pagamento não altera automaticamente o saldo exibido na DCTFWeb; portanto, a CICA deve separar “guia emitida”, “pagamento conhecido” e “situação consultada”.
- O [serviço oficial de Parcelamento do Simples](https://www.gov.br/pt-br/servicos/parcelar-imposto-simples) separa solicitação, acompanhamento, emissão de parcela e risco de rescisão. A tela CICA deve manter essas etapas distintas.
- A listagem oficial do e-CAC diferencia mensagens gerais e específicas na Caixa Postal; a CICA deve mostrar tipo, empresa, data, consequência e evidência da abertura.

### 3.3 Pesquisa de onboarding e acessibilidade

- A pesquisa do Nielsen Norman Group sobre [tutorial inicial versus ajuda contextual](https://www.nngroup.com/articles/onboarding-tutorials/) recomenda ajuda progressiva, acionada perto da tarefa, em vez de walkthrough longo e intrusivo.
- O catálogo local `ui-ux-pro-max` confirmou: tutorial sempre pulável, com Voltar/Pular, hierarquia clara, foco visível, layout mobile-first e estados vazios com ação.
- O [W3C para diálogos HTML](https://www.w3.org/WAI/WCAG22/Techniques/html/H102) exige foco movido para o diálogo, foco contido enquanto aberto, fechamento por Escape e retorno ao acionador.
- O [padrão WAI-ARIA de diálogo modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) orienta título visível, ordem de foco previsível e ação explícita de fechar.

### 3.4 Direção visual

O resultado combinado da pesquisa é uma interface de “confiança silenciosa”:

- superfícies neutras e densidade média/alta;
- azul reservado a interação e foco;
- verde, âmbar e vermelho apenas para significado operacional;
- títulos curtos, verbos concretos e no máximo uma frase de apoio por bloco;
- números somente quando levam a uma lista verificável;
- movimento discreto, nunca necessário para compreender estado;
- ícones vetoriais consistentes, sempre acompanhados de texto quando a ação não for universal;
- nenhuma troca integral de identidade, fonte ou arquitetura visual apenas por tendência.

## 4. Contrato comum de todas as telas

Toda tela operacional deverá responder, acima da primeira dobra, às quatro perguntas:

1. **Onde estou?** Módulo, escritório e, quando aplicável, empresa/competência.
2. **O que está acontecendo?** Estado atual em linguagem contábil, não técnica.
3. **O que exige atenção?** Exceção, prazo, falha, permissão ou ausência de configuração.
4. **O que posso fazer agora?** Uma ação primária; ações secundárias ficam subordinadas.

Padrões transversais obrigatórios:

- título de uma linha e descrição opcional de uma frase;
- uma ação primária por região de trabalho;
- filtros essenciais sempre visíveis; avançados sob expansão;
- seleção em lote só revela a barra de ações depois de existir seleção;
- detalhe preserva o retorno à lista com filtros e página;
- status nunca depende apenas de cor;
- datas com contexto e fuso quando relevante;
- valores monetários alinhados e formatados em pt-BR;
- confirmação proporcional ao risco e descrição objetiva da consequência;
- sucesso informa o que aconteceu e o próximo passo;
- falha preserva dados digitados e indica recuperação;
- estado incerto impede repetição automática;
- estado vazio explica causa e oferece uma ação ou informa quem pode agir;
- carregamento mantém a estrutura da tela e anuncia atualização;
- permissão negada explica o limite sem revelar conteúdo protegido;
- demo traz identificação persistente, mas compacta, e nunca imita resultado oficial sem rótulo fictício.

## 5. O que se espera de cada ferramenta

### 5.1 Site, cadastro, acesso e demonstração

**Tarefa esperada:** entender a proposta, experimentar com segurança, criar acesso, recuperar conta e chegar à primeira ação útil.

**Padrão de mercado:** promessa curta, prova visual do produto, CTA principal, alternativa de demo, etapas de cadastro reduzidas e retorno claro de confirmação.

**Plano:**

- devolver “Ver demonstração” ao cabeçalho, hero e CTA final quando o ambiente estiver realmente apto;
- corrigir a divergência de slug sem remover os gates de isolamento;
- reduzir a landing a problema, módulos, funcionamento, integrações/limites e CTA;
- manter termos técnicos e comerciais em expansão ou páginas próprias;
- fazer cadastro, convite, login, MFA e recuperação compartilharem o mesmo padrão de erro, sucesso e próxima ação;
- mostrar na entrada da demo três limites: dados fictícios, nenhuma consulta externa, progresso restrito à sessão.

### 5.2 Visão geral do escritório

**Tarefa esperada:** começar o dia sabendo o que está atrasado, bloqueado ou aguardando decisão.

**Plano:**

- manter no topo apenas carteira ativa, exceções relevantes e atalhos de resolução;
- priorizar por risco operacional: prazo/efeito jurídico, falha/incerteza, revisão humana e configuração faltante;
- cada número deve abrir exatamente o conjunto que o originou;
- substituir blocos informativos passivos por “pendência + causa + ação”;
- estado inicial sem carteira vira checklist de configuração, não dashboard vazio.

### 5.3 Empresas, equipe, certificados e configurações

**Tarefa esperada:** localizar cliente, entender cobertura, conceder o mínimo acesso e deixar integrações prontas.

**Plano:**

- carteira pesquisável por nome, CNPJ e código Domínio, com filtros de aptidão e pendência;
- ficha da empresa como contexto unificado, sem duplicar listas inteiras;
- permissões por papel, operação e empresa, com resumo legível antes de salvar;
- certificado mostra empresa, validade, cobertura, último uso/erro e ação segura;
- configuração dividida em “Precisa configurar”, “Funcionando” e “Atenção”, com detalhes técnicos recolhidos;
- ações destrutivas com nome da pessoa/empresa afetada e confirmação específica.

### 5.4 NFS-e e revisão fiscal

**Tarefa esperada:** localizar notas, trabalhar por competência, revisar baixa confiança e preparar saída rastreável.

**Plano:**

- filtros principais: empresa, período e situação;
- tabela desktop e cartões mobile com empresa, emissão, tipo, situação, acumulador e confiança;
- separar “capturada”, “classificada”, “em revisão” e “decidida manualmente”;
- revisão em duas colunas no desktop: evidência/origem e decisão; empilhada no celular;
- exibir sugestão de IA como sugestão, nunca como fato;
- decisão manual registra acumulador, responsável, data e justificativa quando exigida;
- download em lote mostra recorte, quantidade, organização do ZIP e itens sem classificação antes de gerar.

### 5.5 Guias e DCTFWeb

**Tarefa esperada:** encontrar empresa/competência, conferir a apuração local, consultar documentos oficiais autorizados e reutilizar evidências.

**Plano:**

- carteira por empresa e competência, com vencimento, origem, componentes e situação;
- distinguir apuração Domínio, declaração DCTFWeb, recibo, DARF e pagamento conhecido;
- antes de qualquer consulta: empresas, competências, operações, tokens e custo/excedente;
- depois: protocolo, horário, resultado, documento disponível e caminho de recuperação;
- impedir “Emitir” quando pré-condições oficiais não estiverem provadas;
- downloads oficiais reutilizam documento persistido sem nova chamada.

### 5.6 Caixa DTE

**Tarefa esperada:** localizar mensagens por empresa, compreender urgência e abrir conteúdo com consciência do possível efeito jurídico.

**Plano:**

- fila com empresa, remetente/tipo, assunto, recebimento, prazo e estado de ciência;
- distinguir “não consultada”, “resumo disponível”, “abertura pendente”, “ciência registrada” e “resultado incerto”;
- confirmação de abertura descreve consequência antes da ação;
- detalhe mantém mensagem, anexos/evidências, protocolo e histórico no mesmo contexto;
- mensagens e histórico de consultas continuam paginados separadamente.

### 5.7 Parcelamentos

**Tarefa esperada:** consultar situação, ver acordo/parcelas e emitir DAS quando permitido.

**Plano:**

- carteira de empresas aptas com busca e seleção limitada ao lote autorizado;
- detalhe separa pedido, consolidação, parcelas e documento de arrecadação;
- destacar parcela atual, atrasadas e risco informado pela fonte sem inventar conclusão jurídica;
- emissão mostra competência/parcela, vencimento e documento resultante;
- resultado incerto bloqueia repetição até conferência.

### 5.8 Conciliação OFX × Domínio

**Tarefa esperada:** importar no contexto correto, validar mapeamento, trabalhar exceções e exportar somente após revisão.

**Plano:**

- fluxo visível de cinco etapas: fonte, prévia, processamento, revisão, exportação;
- resumo por quantidade e valor dos dois lados;
- auto-match fica recolhido; a fila principal mostra ambiguidades e não conciliados;
- comparação lado a lado com data, valor, histórico, documento e motivo da sugestão;
- confirmar, rejeitar, desfazer e agrupar com trilha de autoria;
- não usar porcentagem de confiança isolada como justificativa;
- conclusão mostra saldo/diferença, exceções restantes e versão da exportação.

### 5.9 Triagem documental

**Tarefa esperada:** saber se a caixa está recebendo, revisar anexos seguros, identificar empresa/tipo e comprovar destino.

**Plano:**

- estados equivalentes ao modelo de inbox: recebendo, processando, revisar, aprovado, arquivando, arquivado e bloqueado;
- fila prioriza quarentena, falha de identificação e ausência de destino;
- detalhe reúne remetente, assunto, anexo, verificação de segurança, empresa sugerida e destino;
- configuração de caixas vira assistente por provedor, com pré-requisitos antes dos campos;
- destino Windows exibe estado do agente e prova de escrita, não apenas o caminho configurado;
- demo mostra o fluxo completo com arquivo fictício e rótulos explícitos.

### 5.10 Radar da Reforma

**Tarefa esperada:** localizar atualização relevante, verificar fonte e transformar informação revisada em pauta.

**Plano:**

- filtros por termo, tema, fonte e data;
- cada alerta mostra título, resumo curto, fonte, publicação/coleta e status de revisão;
- conteúdo antigo ou fonte indisponível recebe aviso visível;
- não confundir coleta com validação jurídica;
- ação principal abre fonte/evidência ou marca para revisão, conforme permissão.

### 5.11 Copiloto e Central de aprendizado

**Tarefa esperada:** perguntar sobre uma empresa com fontes verificáveis e revisar exemplos antes de reutilizá-los.

**Plano:**

- empresa obrigatória e persistente no cabeçalho da conversa;
- perguntas sugeridas somente como ponto de partida, sem poluir o estado ativo;
- resposta separa conclusão, fontes, limitações e ações possíveis;
- citação abre exatamente a evidência sustentadora;
- ausência de fonte produz recusa clara, não resposta plausível;
- classificação permanece rascunho até decisão humana;
- aprendizado mostra origem, escopo, revisão, versão e diferença antes de aprovar;
- seguir o princípio confirmado por pesquisa recente em contabilidade: IA desloca esforço para revisão e qualidade, mas recomendações não consensuais aumentam risco e exigem julgamento profissional ([Journal of Accounting Research, 2026](https://onlinelibrary.wiley.com/doi/abs/10.1111/1475-679x.70052)).

### 5.12 Console Mewstack

**Tarefa esperada:** suporte e operação interna com risco controlado, sem se parecer com a área do escritório.

**Plano:**

- dashboard por exceção: escritórios bloqueados, cobrança incerta, egressão incerta, integração falha e suporte ativo;
- detalhe do escritório organiza contrato, módulos, consumo, integrações, falhas e auditoria em seções curtas;
- sessão de suporte mostra escopo e capacidade de alteração durante toda a visita;
- ações comerciais e técnicas ficam separadas;
- formulários de segredo nunca repetem valor existente nem o expõem em confirmação.

## 6. Tutorial guiado de primeiro uso

### 6.1 Modelo proposto

O tutorial terá três camadas, sem tour longo por todas as telas:

1. **Boas-vindas ao sistema, uma vez por pessoa:** três passos curtos — pauta, navegação e ajuda.
2. **Orientação por módulo, no primeiro acesso à tela principal:** no máximo três pontos — estado, filtro/fila e ação principal.
3. **Ajuda contextual permanente:** botão “Como usar” reabre a orientação; estados vazios ensinam a primeira ação no próprio conteúdo.

Regras:

- sempre oferecer Pular, Voltar e Fechar;
- não abrir automaticamente em detalhes, confirmações ou durante tarefa iniciada;
- não reaparecer após conclusão, salvo acionamento manual;
- registrar progresso por usuário e versão do tutorial; demo usa somente sessão;
- conteúdo varia por papel e módulo;
- nenhum passo depende exclusivamente de animação ou posição visual;
- diálogo acessível, foco contido, Escape e retorno ao acionador;
- respeitar `prefers-reduced-motion`;
- celular usa cartão inferior ou diálogo central sem esconder a ação descrita;
- mudanças materiais de fluxo incrementam a versão e permitem mostrar apenas a novidade.

### 6.2 Conteúdo por módulo

Cada orientação responderá somente:

- para que serve esta área;
- como encontrar o trabalho;
- como reconhecer uma pendência;
- qual ação conclui a tarefa;
- onde consultar histórico/ajuda.

Não incluirá regras fiscais extensas, marketing, documentação técnica ou descrição de todos os botões.

## 7. Plano de execução por ondas

### Onda 0 — Baseline e matriz integral

- Atualizar inventário de 78 rotas e 76 templates.
- Mapear cada tela por persona, tarefa, estados e efeito.
- Capturar baseline desktop 1440 px, tablet 768 px e celular 390/375 px.
- Registrar claro, escuro, teclado, foco, console e overflow.
- Separar defeito visual, defeito funcional, regra pendente e dependência externa.

**Aceite:** nenhuma tela ou ação fica fora da matriz; cada pendência tem severidade e evidência.

### Onda 1 — Fundação visual e componentes compartilhados

- Consolidar tokens, cabeçalhos, painéis, tabelas/cartões, filtros, barras de lote, estados e confirmações.
- Criar contrato comum para vazio, carregamento, erro, bloqueio, sucesso e resultado incerto.
- Reduzir texto repetido nas bases compartilhadas.
- Corrigir primeiro os componentes que afetam várias telas.

**Aceite:** superfícies equivalentes têm mesma hierarquia, linguagem, foco e comportamento responsivo.

### Onda 2 — Demo, público e acesso

- Corrigir a divergência do slug da demo e validar os gates.
- Revalidar isolamento entre dois navegadores e descarte da sessão.
- Revisar landing, proposta, cadastro, convite, login, MFA e recuperação.
- Criar início da demo com roteiro curto e saída clara.

**Aceite:** visitante entra na demo pela home, reconhece que tudo é fictício e não consegue gerar egressão, cobrança ou mutação compartilhada.

### Onda 3 — Núcleo diário do operador

- Visão geral, empresas, NFS-e, revisões, Guias/DCTFWeb, DTE e Parcelamentos.
- Priorizar filas, filtros persistentes, contexto da empresa/competência e decisões de risco.

**Aceite:** tarefas representativas terminam sem intervenção interna e sem perda de contexto.

### Onda 4 — Processamento documental e financeiro

- Conciliação, Triagem, certificados, caixas e destinos.
- Validar upload/importação, prévia, revisão, estados incertos, recuperação e trilha.

**Aceite:** operador sabe o que entrou, o que foi automatizado, o que precisa decidir e o que foi efetivamente concluído.

### Onda 5 — Inteligência e conhecimento

- Radar, Copiloto e Central de aprendizado.
- Revisar fontes, citações, recusas, rascunhos, curadoria e escopo por empresa/escritório.

**Aceite:** nenhuma saída de IA se apresenta como decisão contábil confirmada e toda afirmação operacional pode ser rastreada.

### Onda 6 — Administração do escritório e plataforma

- Equipe, permissões, configurações, onboarding, cobrança/contratos e console Mewstack.
- Revisar diferenças por papel e suporte delegado.

**Aceite:** cada perfil vê apenas ações permitidas e consegue entender por que uma ação não está disponível.

### Onda 7 — Tutorial guiado

- Implementar boas-vindas, orientação por módulo e reabertura manual.
- Escrever conteúdo por papel e validar persistência/versionamento.
- Testar teclado, leitor de tela, Escape, retorno de foco e movimento reduzido.

**Aceite:** usuário novo consegue apontar a próxima ação após a orientação; usuário experiente consegue ignorá-la sem fricção.

### Onda 8 — Auditoria e regressão final

- Buscar a versão atual das Vercel Web Interface Guidelines.
- Auditar todos os arquivos UI alterados e corrigir violações materiais.
- Executar testes Django, Ruff, schema, JavaScript e suíte relevante.
- Percorrer a matriz integral com Playwright em desktop e celular, incluindo teclado, foco, menus, diálogos, filtros, paginação, vazio, erro, carregamento, permissão e console.
- Fechar todas as sessões Playwright e servidores temporários.
- Atualizar `VALIDACOES.md`, etapa 11 e registro de execução com limites reais.

**Aceite:** matriz sem bloqueio funcional crítico; nenhum overflow horizontal; console sem erros; nenhuma alegação de homologação externa baseada em demo ou mock.

## 8. Ordem de prioridade

1. Demo ausente e estados que impedem entrada.
2. Ações quebradas, sem saída ou com risco de repetição/custo.
3. Perda de empresa, competência, filtro ou página.
4. Mensagens que confundem simulação, dado real ou resultado confirmado.
5. Permissões e ações visíveis para papel incorreto.
6. Falhas de teclado, foco, contraste e responsividade.
7. Excesso de texto e inconsistência visual.
8. Refinamentos estéticos e microinterações.

## 9. Matriz de validação mínima

| Dimensão | Cobertura |
|---|---|
| Viewports | 1440×1000, 1024×768, 768×1024, 390×844 e 375×667 |
| Temas | claro, escuro e sistema |
| Entrada | mouse, teclado, toque e movimento reduzido |
| Perfis | visitante demo, proprietário, administrador, operador, financeiro, auditor, suporte e perfis Mewstack aplicáveis |
| Estados | inicial, vazio, preenchido, filtrado, carregando, sucesso, validação, erro recuperável, bloqueado, permissão negada e resultado incerto |
| Volume | zero, um, uma página, mais de uma página e conteúdo longo |
| Navegação | link direto, voltar do navegador, retorno à lista, troca de escritório e sessão de suporte |
| Segurança | POST forjado, repetição, demo isolada, ausência de egressão e segredo não revelado |

## 10. Métricas de sucesso

- 100% das 44 telas/estados com inspeção representativa documentada.
- 100% das 34 ações com resposta, confirmação ou recuperação verificável.
- Zero ação principal sem rótulo, efeito ou retorno claro.
- Zero tela vazia sem explicação e próximo passo aplicável.
- Zero perda silenciosa de filtros/página/contexto nas jornadas cobertas.
- Zero overflow horizontal nos viewports definidos.
- Zero erro de console nos fluxos percorridos.
- Tutorial concluível, pulável e reabrível somente por teclado.
- Demo acessível pela home quando apta e isolada entre sessões.
- Redução mensurável de texto repetido, sem remover informação jurídica, fiscal ou de segurança necessária.

## 11. Entregáveis da futura execução

- matriz atualizada de rotas, telas, estados e personas;
- relatório antes/depois por onda;
- componentes e padrões compartilhados documentados;
- roteiro e conteúdo do tutorial por módulo;
- demo restaurada com testes de isolamento;
- capturas representativas desktop/mobile;
- relatório de auditoria Vercel com correções;
- evidências Playwright e resultados de testes;
- atualização de decisões, validações, etapa 11 e registro de execução.

## 12. Limites

Este plano não autoriza deploy, chamada externa, API cobrada, envio de e-mail, conexão a caixa real, uso de certificado real, alteração de dados de cliente ou homologação. Pesquisa de mercado orienta interação e composição; não substitui regras confirmadas da CICA nem autoriza copiar identidade, texto ou ativos de terceiros.
