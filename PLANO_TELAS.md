# Revisão completa das telas, restauração da demo e onboarding guiado da CICA

## Resumo

Revisar integralmente as 44 telas e 34 ações atualmente inventariadas, preservando a identidade visual da CICA, mas reorganizando a experiência em torno da rotina real do operador contábil:

- mostrar imediatamente escritório, empresa, competência e estado;
- destacar pendências e exceções, não gráficos decorativos;
- reduzir textos repetidos e esconder detalhes técnicos até serem necessários;
- oferecer uma ação principal clara por área;
- restaurar a demonstração pública isolada;
- adicionar orientação guiada no primeiro acesso ao sistema e a cada módulo;
- validar todos os fluxos em desktop e celular, por perfil e por estado.

Referências adotadas: Conta Azul Mais, Karbon, QuickBooks Accountant, Dext, BlackLine, SaaSFrame, Watermelon UI, documentação oficial da Receita/NFS-e e padrões W3C. O princípio central será: automatizar o óbvio e concentrar o operador nas exceções que exigem julgamento.

## Implementação

### 1. Fundação compartilhada

- Consolidar tokens de cor, tipografia, espaçamento, foco, bordas e estados em um único sistema visual.
- Manter azul para ações, verde para concluído, âmbar para atenção e vermelho para bloqueio/erro.
- Padronizar cabeçalho, contexto do escritório, navegação, abas, filtros, painéis, tabelas, cartões mobile, paginação e confirmações.
- Toda tela deverá responder acima da primeira dobra:
  1. onde estou;
  2. qual contexto está selecionado;
  3. o que exige atenção;
  4. qual é a próxima ação.
- Limitar descrições comuns a uma frase. Explicações técnicas ficarão em expansões, ajuda contextual ou documentação.
- Mostrar ações em lote somente depois de existir seleção.
- Preservar filtros, página, empresa e competência ao abrir detalhes e retornar.
- Criar componentes padronizados para vazio, carregamento, sucesso, erro recuperável, permissão negada, bloqueio e resultado incerto.
- Status nunca dependerá apenas de cor e nenhuma ação ficará disponível somente no hover.

### 2. Demonstração

- Corrigir a divergência entre o slug configurado `cica-demo` e a organização existente `escritorio-demo`.
- Manter obrigatórios `DEMO_ENTRY_ENABLED`, `DEMO_SESSION_ISOLATION_READY`, organização ativa e `is_demo=True`.
- Restaurar “Ver demonstração” no cabeçalho, hero e CTA final da home.
- Criar entrada curta explicando:
  - dados totalmente fictícios;
  - nenhuma chamada externa ou cobrança;
  - progresso limitado à sessão do navegador.
- Adicionar uma saída clara da demo e impedir que o visitante alcance administração compartilhada.
- Preservar progresso por sessão para NFS-e, DTE, Parcelamentos, Conciliação, Triagem e Copiloto.
- Revalidar isolamento entre dois navegadores e garantir que encerrar a sessão elimine o progresso daquele visitante.
- Nunca apresentar PDF, protocolo ou resultado fictício como documento oficial.

### 3. Site, cadastro e autenticação

- Reduzir a landing a: problema, módulos, forma de operação, integrações/limites e CTA.
- Manter promessas comerciais alinhadas somente ao que está implementado ou homologado.
- Unificar cadastro, convite, login, MFA e recuperação de senha no mesmo padrão visual.
- Erros deverão aparecer junto ao campo e em resumo focalizado quando houver múltiplos erros.
- Preservar valores digitados após erro.
- Mostrar uma próxima ação concreta em confirmação, link expirado, conta bloqueada e ativação pendente.
- Permitir gerenciadores de senha, colar senha/código e navegação integral por teclado.

### 4. Visão geral

- Transformar a home autenticada em pauta operacional do dia.
- Prioridade visual:
  1. prazos ou efeitos jurídicos;
  2. falhas e resultados incertos;
  3. revisões humanas;
  4. configurações ausentes.
- Indicadores deverão abrir exatamente os registros que originaram o número.
- Remover cartões sem ação operacional.
- Para escritório sem carteira, substituir métricas vazias por checklist: cadastrar empresa, configurar acesso, certificado e primeira integração.
- Para escritório ativo, mostrar pendência, empresa, causa, idade e ação de resolução.

### 5. Empresas, equipe, certificados e configurações

- Empresas: busca por nome, CNPJ e código Domínio; filtros por situação, certificado e pendência.
- Ficha da empresa: resumo, documentos, revisões, DTE e histórico, evitando duplicação de listas completas.
- Equipe: papel, operações e empresas concedidas, com resumo antes de salvar.
- Certificados: empresa, validade, cobertura, erro mais recente e ação necessária.
- Configurações: separar “Precisa configurar”, “Funcionando” e “Atenção”.
- Ações destrutivas deverão citar a pessoa, empresa ou integração afetada.
- Usuários sem permissão verão explicação curta e caminho para solicitar acesso, sem exposição de dados protegidos.

### 6. NFS-e e revisão fiscal

- Filtros principais: empresa, período e situação.
- Exibir empresa, emissão, tipo, situação, acumulador, confiança e origem.
- Diferenciar claramente:
  - capturada;
  - classificada automaticamente;
  - aguardando revisão;
  - decidida manualmente.
- Revisão desktop em duas áreas: evidência/origem e decisão; empilhada no celular.
- Sugestões da IA serão rotuladas como sugestão e acompanhadas da evidência utilizada.
- Decisão manual registrará responsável, data, acumulador e justificativa quando aplicável.
- Antes de gerar ZIP, mostrar período, empresas, quantidade, estrutura de pastas e itens ainda sem classificação.
- Preservar a regra de acumulador válido no catálogo da empresa.

### 7. Guias e DCTFWeb

- Organizar a carteira por empresa e competência.
- Separar visualmente:
  - apuração do Domínio;
  - declaração DCTFWeb;
  - recibo;
  - DARF;
  - pagamento conhecido.
- Nunca usar um único status “pronto” para conceitos diferentes.
- Antes da consulta, exibir empresas, competências, operações, tokens e eventual excedente.
- Depois da consulta, exibir protocolo, horário, resultado e documento persistido.
- Bloquear emissão enquanto declaração, recibo e situação oficial exigida não estiverem comprovados.
- Downloads reutilizarão o documento salvo, sem repetir consulta externa.

### 8. Caixa DTE

- Fila com empresa, tipo, assunto, recebimento, prazo e situação da ciência.
- Estados: não consultada, resumo disponível, abertura pendente, ciência registrada e resultado incerto.
- Abrir mensagem com possível efeito jurídico exigirá confirmação explícita da consequência.
- Detalhe deverá reunir conteúdo, anexos, protocolo, responsável e histórico.
- Mensagens e consultas continuarão com paginações independentes.
- Falha ou resultado incerto nunca poderá disparar repetição automática.

### 9. Parcelamentos

- Carteira pesquisável de empresas aptas.
- Seleção em lote limitada ao tamanho já autorizado.
- Detalhe separado em pedido, consolidação, parcelas e DAS.
- Destacar parcela atual, atrasadas e situação informada pela fonte.
- Antes da consulta/emissão, apresentar escopo e consumo.
- Resultado incerto bloqueará nova emissão até conferência humana.
- PDF existente será reutilizado sem nova chamada.

### 10. Conciliação OFX × Domínio

- Fluxo explícito: fonte → prévia → processamento → revisão → exportação.
- Mostrar quantidades e valores dos dois lados.
- Recolher correspondências automáticas e priorizar ambiguidades e não conciliados.
- Comparação lado a lado com data, valor, histórico, documento e motivo da sugestão.
- Permitir confirmar, rejeitar, desfazer e agrupar, sempre com autoria e horário.
- Confiança percentual não será usada isoladamente como justificativa.
- Conclusão mostrará totais conciliados, diferença, exceções restantes e versão da exportação.

### 11. Triagem documental

- Estados: recebendo, processando, revisar, aprovado, arquivando, arquivado e bloqueado.
- Priorizar quarentena, falha de identificação e ausência de destino.
- Detalhe com remetente, assunto, anexo, verificação de segurança, empresa sugerida e destino.
- Configuração de Microsoft, Google e IMAP em assistentes separados por provedor.
- Mostrar pré-requisitos antes dos campos de configuração.
- Destino Windows deverá exibir saúde do agente e prova da gravação, não apenas o caminho.
- Demo permitirá concluir o fluxo com arquivo fictício e sem tocar caixas ou pastas reais.

### 12. Radar da Reforma

- Filtros por termo, tema, fonte e data.
- Cada alerta mostrará resumo curto, fonte, publicação/coleta e estado de revisão.
- Conteúdo desatualizado ou fonte indisponível receberá aviso.
- Diferenciar publicação coletada de interpretação fiscal validada.
- Ação principal será abrir a evidência ou enviar para revisão.

### 13. Copiloto e aprendizado

- Empresa obrigatória e sempre visível durante a conversa.
- Resposta dividida em conclusão, fontes, limitações e possíveis próximos passos.
- Citações deverão abrir a evidência exata.
- Ausência de fonte deverá gerar recusa clara.
- Respostas e classificações continuarão como rascunho até decisão humana.
- Histórico de conversas preservará página e conversa selecionada.
- Central de aprendizado mostrará origem, escopo, versão, diferença e responsável pela revisão.
- Conhecimento de um escritório nunca será apresentado como compartilhado com outro.

### 14. Console Mewstack

- Dashboard orientado a exceções: escritórios bloqueados, cobrança incerta, integração falha, egressão incerta e suporte ativo.
- Detalhe do escritório dividido em contrato, módulos, consumo, integrações, falhas e auditoria.
- Separar ações comerciais das ações técnicas.
- Sessão de suporte exibirá permanentemente escritório, nível de acesso e botão de encerramento.
- Segredos existentes nunca serão reexibidos em campos ou confirmações.

### 15. Tutorial guiado

Implementar três níveis:

1. Boas-vindas ao sistema, uma vez por usuário: pauta, navegação e ajuda.
2. Orientação no primeiro acesso à tela principal de cada módulo: estado, filtro/fila e ação principal.
3. Botão permanente “Como usar” para repetir a orientação.

Regras fechadas:

- máximo de três passos por orientação;
- sempre oferecer Pular, Voltar e Fechar;
- não abrir automaticamente em detalhes, confirmações ou com formulário já preenchido;
- progresso persistido por usuário e versão;
- na demo, progresso somente em `sessionStorage`;
- conteúdo adaptado ao papel do usuário;
- diálogo HTML nativo com foco contido;
- Escape fecha e devolve foco ao acionador;
- compatível com leitor de tela e movimento reduzido;
- nova versão aparece somente quando o fluxo do módulo mudar materialmente;
- estados vazios continuarão ensinando a primeira ação mesmo após o tutorial ser dispensado.

## Interfaces e dados

- Adicionar preferência versionada de onboarding por usuário: tutorial global concluído e módulos concluídos.
- Não armazenar conteúdo fiscal, empresa ou respostas da demo nessa preferência.
- Expor ao frontend somente: identificador do tutorial, versão, papel e estado concluído.
- Criar catálogo declarativo dos tutoriais por módulo, evitando textos e seletores espalhados pelos templates.
- Componentes compartilhados receberão contratos consistentes para título, descrição curta, estado, ação principal, ação secundária e ajuda.
- Não alterar APIs externas, contratos Serpro/ADN, cobrança ou regras fiscais nesta revisão.

## Ordem de execução

1. Inventário e baseline das 78 rotas.
2. Fundação visual e componentes compartilhados.
3. Restauração da demo, público e autenticação.
4. Visão geral, empresas, NFS-e, revisões, Guias, DTE e Parcelamentos.
5. Conciliação, Triagem, certificados e configurações.
6. Radar, Copiloto e aprendizado.
7. Equipe, onboarding administrativo e console Mewstack.
8. Tutorial guiado.
9. Auditoria final, regressão e documentação.

Prioridade de correção:

1. ações quebradas, perigosas ou sem recuperação;
2. perda de empresa, competência, filtro ou página;
3. confusão entre dado real, fictício ou confirmado;
4. permissões incorretas;
5. teclado, foco, contraste e responsividade;
6. excesso de texto e inconsistência visual;
7. refinamentos estéticos.

## Plano de testes

- Viewports: 1440×1000, 1024×768, 768×1024, 390×844 e 375×667.
- Temas: claro, escuro e sistema.
- Perfis: visitante demo, proprietário, administrador, operador, financeiro, auditor, suporte e perfis Mewstack aplicáveis.
- Estados: inicial, vazio, preenchido, filtrado, carregando, sucesso, erro, bloqueado, permissão negada e resultado incerto.
- Volumes: zero, um, uma página, múltiplas páginas e conteúdo longo.
- Navegação: link direto, voltar do navegador, retorno à lista, troca de escritório e suporte delegado.
- Acessibilidade: teclado completo, foco visível, foco não encoberto, Escape, retorno de foco, leitor de tela, contraste e movimento reduzido.
- Demo: dois navegadores independentes, encerramento de sessão, ausência de persistência compartilhada e bloqueio de egressão.
- Segurança: POST forjado, repetição de ação, segredo não revelado e papel sem permissão.
- Executar Ruff, Django check, migrações em modo de verificação, testes focados e regressão integral.
- Buscar e aplicar a versão atual das Vercel Web Interface Guidelines em todos os arquivos alterados.
- Executar Playwright em desktop e celular, verificar console e fechar todas as sessões abertas.

## Critérios de aceite

- As 44 telas possuem inspeção representativa registrada.
- As 34 ações possuem confirmação, resultado ou recuperação verificável.
- Nenhuma tela vazia termina sem explicação e próximo passo aplicável.
- Nenhuma ação principal fica sem rótulo ou consequência clara.
- Nenhum fluxo coberto perde silenciosamente empresa, competência, filtro ou página.
- Nenhum viewport definido apresenta overflow horizontal.
- Nenhum fluxo validado apresenta erro no console.
- Tutorial é concluível, pulável e reabrível somente com teclado.
- Demo volta a ser acessível pela home quando os gates estiverem ativos.
- Demo permanece isolada e não acessa integração, cobrança ou dados reais.
- Saídas de IA nunca aparecem como decisão contábil confirmada.
- Nenhuma simulação local é registrada como homologação externa.

## Premissas

- A identidade visual, navegação principal e stack Django Templates/CSS/JavaScript serão preservadas.
- A revisão cobre toda a etapa 11, mas não autoriza deploy ou homologação das integrações.
- A demo continuará pública somente quando todos os controles de isolamento estiverem ativos.
- O tutorial será progressivo e contextual, não um tour obrigatório por todas as páginas.
- Detalhes fiscais e jurídicos necessários não serão removidos; serão reorganizados por hierarquia e revelação progressiva.
- As remoções preexistentes de `stage02-signup-desktop.png` e `stage02-signup-mobile.png` não fazem parte desta execução.
