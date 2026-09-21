# Memória de planejamento da CICA

## Comece pelos arquivos da raiz

- [PLANO-MESTRE.md](../../PLANO-MESTRE.md): plano único aprovado e dependências.
- [DECISOES.md](../../DECISOES.md): decisões, incluindo todas as respostas de 17/09/2026.
- [VALIDACOES.md](../../VALIDACOES.md): resultados observados e limites.
- [Etapas 00–13 e prompts](etapas/README.md): checklists de execução.
- [Inventário de conclusão](inventario-conclusao.md): aplicações, modelos, rotas, APIs, tarefas e serviços.
- [Relatório consolidado de desenvolvimento de 21/09](relatorio-desenvolvimento-2026-09-21.md): entregas locais, evidências, limites e bloqueios vigentes.

**Estado vigente:** etapas 00–03 concluídas localmente; etapa 04 em andamento e bloqueada por Q-33. V-041 revalidou em 21/09 o estado local, a recusa segura da exportação Siescon e a sincronização com `origin/main`, sem homologação externa. V-044–V-068 reduziram localmente a dívida de tipos de 535 ocorrências para zero nos 190 arquivos verificados, sem alterar integrações; V-068 repetiu a regressão integral com 762 testes aprovados. V-072 concluiu a prova local do runtime privado e do bloqueio de fallback externo sem opt-in; V-073 avançou detalhe e paginação NFS-e com dados sintéticos, V-074 eliminou o corte silencioso da carteira de guias, V-075 fez o mesmo na carteira de Parcelamentos respeitando seu lote de 30, V-076 na fila OFX × Domínio, V-077 no histórico de operações PARCSN e V-078 na cobertura de certificados. As frentes locais independentes das etapas 05–11 têm evidências recentes — inclusive V-040 para o contrato local do cliente Asaas — mas não substituem dependências nem homologações externas. A limitação de D-60 à etapa 00 é histórica e não substitui o estado do [plano mestre](../../PLANO-MESTRE.md). Os registros datados abaixo permanecem como evidência histórica e não substituem a memória vigente na raiz.

**Atualização V-079:** a ficha de empresa agora permite percorrer seus três históricos locais sem corte silencioso, com evidência sintética de navegador e regressão integral de 769 testes. Integrações fiscais continuam pendentes.

**Atualização V-080:** a trilha da auditoria de conciliação agora pagina eventos sem corte silencioso, preserva o filtro e foi verificada com 201 eventos fictícios; a regressão integral local alcançou 770 testes aprovados. Integrações e homologações continuam pendentes.

**Atualização V-081:** o Radar da Reforma agora pagina alertas sem corte silencioso e mantém seus filtros; a prova de 101 alertas é sintética e a regressão integral local alcançou 771 testes aprovados. Fontes oficiais e homologações continuam pendentes.

**Atualização V-082:** o console da plataforma agora permite percorrer o histórico manual de faturas sem corte silencioso; a prova de 25 faturas é sintética e a regressão integral local alcançou 772 testes aprovados. Cobrança e homologação continuam pendentes.

**Atualização V-083:** a Caixa DTE agora permite percorrer seu histórico de resultados sem corte silencioso e sem alterar a página das mensagens; a prova de 31 itens é sintética e a regressão integral local alcançou 773 testes aprovados. Serpro, consumo e homologação continuam pendentes.

**Atualização V-084:** o onboarding agora permite percorrer o histórico de importações sem corte silencioso e conserva fonte e prévia selecionadas; a prova de 21 lotes é sintética e a regressão integral local alcançou 774 testes aprovados. Upload, backup e homologação Domínio continuam pendentes.

**Atualização V-085:** a Conciliação agora permite percorrer seus históricos de processamentos e exportações sem corte silencioso e sem deslocar a outra trilha; a prova de 21 itens em cada histórico é sintética e a regressão integral local alcançou 775 testes aprovados. ERP e homologação de exportação continuam pendentes.

**Atualização V-086:** o Copiloto agora permite percorrer todo o histórico de conversas abertas sem corte silencioso e preserva a conversa selecionada; a prova de 13 conversas é sintética e a regressão integral local alcançou 776 testes aprovados. IA, curadoria e homologação continuam pendentes.

**Atualização V-087:** o console da plataforma agora permite percorrer todos os fechamentos ainda adiados sem corte silencioso; a prova de 31 ocorrências é sintética e a regressão integral local alcançou 777 testes aprovados. Cobrança e homologação Asaas continuam pendentes.

**Atualização V-088:** o console da plataforma agora permite percorrer todas as tentativas Claude incertas sem corte silencioso; a prova de 21 auditorias é sintética e a regressão integral local alcançou 778 testes aprovados. IA e homologação operacional continuam pendentes.

**Atualização V-089:** a revisão NFS-e agora valida o acumulador no catálogo da própria empresa; a prova de regras e observações é sintética e a regressão integral local alcançou 779 testes aprovados. ADN e homologação fiscal continuam pendentes.

**Atualização V-090:** o detalhe de conciliação agora permite percorrer todos os candidatos no recorte de datas, sem corte silencioso após 50; a prova de 51 candidatos é sintética e a regressão integral local alcançou 780 testes aprovados. ERP, arquivo e homologação de exportação continuam pendentes.

**Atualização V-091:** o detalhe da Triagem agora permite percorrer todo o histórico persistido do arquivo sem corte silencioso; a prova de 21 eventos é sintética e a regressão integral local alcançou 781 testes aprovados. Caixa, scanner, agente e homologação do destino continuam pendentes.

**Atualização V-092:** a carteira de movimentos da Conciliação agora preserva as páginas abertas de Processamentos e Exportações ao navegar; a prova de 21/21/51 registros é sintética e a regressão integral local manteve 781 testes aprovados. ERP, arquivo e homologação de exportação continuam pendentes.

**Atualização V-093:** a fila OFX × Domínio agora preserva as páginas abertas de Processamentos, Movimentos e Exportações; a prova de 101 correspondências é sintética e a regressão integral local manteve 781 testes aprovados. ERP, arquivo e homologação de exportação continuam pendentes.

**Atualização V-094:** a Caixa DTE agora preserva simultaneamente a página de mensagens e a página do histórico de consultas; a prova de 31/26 registros é sintética e a regressão integral local manteve 781 testes aprovados. Serpro, consumo e homologação continuam pendentes.

**Atualização V-095:** Jornadas não figura mais no catálogo do produto, mantendo apenas enum, schema e migrações históricos conforme D-43; a regressão integral local manteve 781 testes aprovados. Migração de produção e homologação comercial continuam fora desta evidência.

**Atualização V-096:** formulários, views e template operacionais órfãos de Jornadas foram removidos conforme D-43, preservando enum, modelos, tabelas e migrações históricos; a regressão integral local manteve 781 testes aprovados. Migração de produção e homologação comercial continuam fora desta evidência.

**Atualização V-097:** a Conciliação rejeita XLSX corrompido antes de persistir uma fonte e sua prévia CSV só lê as linhas exibidas; a regressão integral local alcançou 783 testes aprovados. A prova é local, sem arquivo, ERP ou OCR homologados.

**Atualização V-098:** a Conciliação rejeita PDF malformado antes de persistir fonte, lote ou processamento e mantém PDF digitalizado válido no fluxo de OCR local; a regressão integral local alcançou 784 testes aprovados. A prova é local, sem OCR, arquivo, ERP ou exportação homologados.

Atualizado em 15/09/2026. Esta pasta reúne as decisões e dúvidas extraídas dos planos antigos do Claude, do histórico local do Codex, dos documentos do repositório e das confirmações recentes do responsável. Ela é uma memória de produto e execução; não equivale a homologação, aprovação de preço, parecer jurídico ou autorização de gasto.

## Como ler

1. [Fontes e histórico](fontes-e-historico.md) identifica a origem e a época de cada plano, inclusive ideias substituídas ou pertencentes a outros produtos.
2. [Decisões](decisoes.md) separa confirmação direta do responsável, regra registrada em plano e proposta sem confirmação. Um plano nunca prova que uma função foi implementada.
3. [Estado operacional](estado-operacional.md) compara intenção com evidência local e aponta o que falta validar para uma oferta vendável.
4. [Dúvidas abertas](duvidas-abertas.md) concentra respostas necessárias antes de fechar regras, alterar contratos, ativar integrações ou publicar promessas.
5. [Catálogo de triagem a confirmar](catalogo-triagem-a-confirmar.md) preserva a transcrição das 19 linhas da fotografia, sem tratá-las como taxonomia aprovada.
6. [Análise consolidada de 21/09/2026](analise-projeto-2026-09-21.md) sintetiza o objetivo final, arquitetura, maturidade por módulo, revalidação e bloqueio atual. A [análise anterior de 19/09](analise-projeto-2026-09-19.md) permanece como evidência histórica.
7. [Matriz de evidências de conclusão](matriz-evidencias-2026-09-19.md) conecta cada etapa às provas locais, homologações ausentes e bloqueios objetivos.
8. [Avaliação histórica de Jornadas](avaliacao-jornadas.md) registra a função substituída pela Triagem.
9. [Pesquisa de custo e proposta de cotas da IA](precificacao-e-cotas-ia.md) calcula um cenário Sonnet e separa proposta de aprovação.
10. [Registro de execução](registro-de-execucao.md) guarda testes, mudanças, limites e provas externas ainda necessárias.
11. [Auditoria das telas de 15/09](auditoria-ui-2026-09-15.md) registra pesquisa de interface, revisão das diretrizes web e inspeção Playwright com seus limites.
12. [Operação Asaas](asaas-operacao.md) separa o receptor de webhook já implementado da criação de cobranças e da homologação ainda pendente.
13. [Operação do Radar da Reforma](radar-operacao.md) registra a coleta existente, o estado mostrado ao escritório e as provas locais sem ampliar a promessa do módulo.
14. [Ativação operacional da IA](ia-operacao.md) registra a chave central, controles, contagem gratuita e uma geração sintética real autorizada sem armazenar segredo.
15. [Conexão das caixas de e-mail](conexao-caixas-email.md) define a jornada simples do escritório, a preparação OAuth central da Mewstack, a exigência de verificação Google e as provas ainda necessárias.
16. [Ações do responsável](acoes-do-responsavel.md) separa o que já foi provado da preparação de contas, credenciais, contratos e regras que só o responsável pode autorizar.
17. [Revisão crítica da conexão de e-mail](auditoria-triagem-oauth-2026-09-15.md) registra a jornada renderizada, evidência de desktop/celular/teclado e bloqueios concretos de uso real.
18. [Padrão de pasta Windows por empresa](padrao-pastas-windows.md) define o componente com nome + código Domínio e separa a validação local do arquivamento no agente.
19. [Mensalidade, franquia e tokens por módulo](precificacao-tokens-modulos.md) pesquisa concorrentes/custos, registra o modelo decidido e distingue números propostos de preços aprovados.
20. [Conversa e recuperação do Copiloto](auditoria-copiloto-conversa-recuperacao-2026-09-15.md) registra o bloqueio real de empresa no envio, a correção, o estado incerto visível, idempotência e limites do suporte.
21. [Coleta NFS-e pelo ADN](auditoria-nfse-adn-2026-09-16.md) registra o contrato oficial, cliente mTLS, checkpoint, recuperação, área de trabalho e a homologação externa ainda pendente.

## Regra de atualização

Cada nova decisão deve registrar texto exato da escolha, data, quem confirmou, fonte, escopo, efeito sobre decisões anteriores e pendências decorrentes. Se duas fontes divergem, registrar o conflito e perguntar; não escolher pelo código, pela data do plano ou pela preferência de quem implementa. Uma confirmação posterior e explícita do responsável pode resolver o conflito, mas somente no escopo que ela cobre.

Para estado técnico, distinguir **existe no código**, **tem teste automatizado**, **foi exercitado em ambiente real** e **está liberado para venda**. Alterações não commitadas aparecem como trabalho em andamento e exigem nova verificação antes de serem tratadas como entrega.

Os arquivos de sessão do Codex e de planos do Claude ficam fora do repositório. As escolhas essenciais estão transcritas aqui para que a memória não dependa da presença desses arquivos na máquina de outra pessoa. Não copiar credenciais, certificados, dados de cliente, chaves ou conteúdo integral de conversas para a documentação.
