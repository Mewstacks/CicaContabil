# Memória de planejamento da CICA

## Comece pelos arquivos da raiz

- [PLANO-MESTRE.md](../../PLANO-MESTRE.md): plano único aprovado e dependências.
- [DECISOES.md](../../DECISOES.md): decisões, incluindo todas as respostas de 17/09/2026.
- [VALIDACOES.md](../../VALIDACOES.md): resultados observados e limites.
- [Etapas 00–13 e prompts](etapas/README.md): checklists de execução.
- [Inventário de conclusão](inventario-conclusao.md): aplicações, modelos, rotas, APIs, tarefas e serviços.

**Estado vigente:** etapas 00–03 concluídas localmente; etapa 04 em andamento e bloqueada por Q-33. As frentes locais independentes das etapas 05–11 têm evidências recentes — inclusive V-040 para o contrato local do cliente Asaas — mas não substituem dependências nem homologações externas. A limitação de D-60 à etapa 00 é histórica e não substitui o estado do [plano mestre](../../PLANO-MESTRE.md). Os registros datados abaixo permanecem como evidência histórica e não substituem a memória vigente na raiz.

Atualizado em 15/09/2026. Esta pasta reúne as decisões e dúvidas extraídas dos planos antigos do Claude, do histórico local do Codex, dos documentos do repositório e das confirmações recentes do responsável. Ela é uma memória de produto e execução; não equivale a homologação, aprovação de preço, parecer jurídico ou autorização de gasto.

## Como ler

1. [Fontes e histórico](fontes-e-historico.md) identifica a origem e a época de cada plano, inclusive ideias substituídas ou pertencentes a outros produtos.
2. [Decisões](decisoes.md) separa confirmação direta do responsável, regra registrada em plano e proposta sem confirmação. Um plano nunca prova que uma função foi implementada.
3. [Estado operacional](estado-operacional.md) compara intenção com evidência local e aponta o que falta validar para uma oferta vendável.
4. [Dúvidas abertas](duvidas-abertas.md) concentra respostas necessárias antes de fechar regras, alterar contratos, ativar integrações ou publicar promessas.
5. [Catálogo de triagem a confirmar](catalogo-triagem-a-confirmar.md) preserva a transcrição das 19 linhas da fotografia, sem tratá-las como taxonomia aprovada.
6. [Análise consolidada de 19/09/2026](analise-projeto-2026-09-19.md) sintetiza o objetivo final, arquitetura, maturidade por módulo e bloqueio atual.
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
