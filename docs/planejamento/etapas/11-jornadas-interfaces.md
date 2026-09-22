# Etapa 11 — Validar todas as jornadas e interfaces

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

Plano detalhado da revisão total solicitada em 22/09/2026: [telas, demonstração e primeiro uso](../plano-revisao-total-ui-demo-onboarding-2026-09-22.md).

Matriz das 89 rotas de interface (ondas 0 a 8 executadas em 22/09/2026, com limites registrados em V-102): [matriz de telas](../matriz-telas-2026-09-22.md).

**Estado:** Em andamento: inspeções locais parciais registradas em V-039,
V-069, V-070, V-071, V-073, V-074, V-075, V-076, V-077, V-078, V-079, V-080, V-081, V-082, V-083, V-084, V-085, V-086, V-087, V-088, V-089, V-090, V-099, V-100, V-101, V-102 e V-103; não há auditoria integral de todas as superfícies nem
homologação de jornadas reais.

**Dependências:** Módulos implementados.

**Decisões relacionadas:** D-07, D-38, D-57.

## Escopo e checklist

- [x] Revisar site comercial, cadastro, aplicação do escritório, central de aprendizado e console Mewstack (V-100 a V-102; console sob MFA continua fora).
- [x] Corrigir ações sem saída, tabelas incompletas, estados confusos e ausência de evidência (V-100 a V-102).
- [ ] Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- [x] Aplicar ui-ux-pro-max e as Vercel Web Interface Guidelines nas superfícies alteradas (V-102). Watermelon não foi consultada nesta execução.
- [x] Inspecionar localmente parte das jornadas com navegador Playwright, registrar os estados alcançados e fechar a sessão de QA.
- [ ] Conferir que oferta comercial e demonstração refletem capacidades homologadas.

## Bloqueios e responsabilidade

As métricas de aceite estão decididas em D-73, mas os estados inacessíveis devem
ser registrados, nunca presumidos validados.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Por perfil e módulo: desktop/celular, navegação, foco, teclado, carregamento/erro/vazio, recuperação, console do navegador e evidência visual.

**Critério de aceite:** O usuário conclui tarefas representativas sem intervenção interna não prevista.

## Evidências e próximo passo

V-039 registra 14 caminhos em desktop/celular, uma jornada fictícia de Triagem,
77 testes e a inspeção visual local. V-069 retomou a verificação no navegador
interno: home, cadastro, abas, FAQ, viewport móvel, dashboard e Triagem
fictícia; a quarentena continuou bloqueando abertura/download e não houve erro
de console nas superfícies percorridas. V-070 incluiu fila/detalhe de revisão
NFS-e e confirmou que a demonstração recebe acesso restrito no console
Mewstack. V-071 percorreu Guias, DTE, Parcelamentos, Conciliação, Radar e
Copiloto, onde empresa obrigatória e fontes sintéticas ficaram explícitas. V-073
também verificou a revisão NFS-e e sua paginação em viewport móvel. V-074
percorreu a segunda página da carteira de guias com 101 registros fictícios e
confirmou o retorno com filtros preservados, sem erro de console. V-075 fez o
mesmo na carteira de Parcelamentos e confirmou que o seletor por página não
excede o lote local de 30 empresas. V-076 acrescentou teste autenticado para a
paginação da fila de conciliação; a demonstração de duas linhas não foi usada
para alegar inspeção visual em volume. V-077 percorreu visualmente duas páginas
do histórico sintético de Parcelamentos, preservando a empresa em foco. V-078
percorreu a segunda página da cobertura de certificados em uma sessão fictícia,
retornou à primeira e confirmou ausência de overflow horizontal em 390 px e de
erros de console. V-079 verificou em volume a ficha de empresa: os três
históricos alcançaram a página 2, a DTE retornou sem perder as outras páginas e
390 px não teve overflow horizontal. V-080 percorreu a terceira página filtrada
da auditoria de conciliação com 201 eventos fictícios e retornou à segunda sem
perder o filtro, também sem overflow em 390 px ou erro de console. V-081
conferiu no Radar fictício a busca IBS, seu aviso e a superfície móvel;
o teste de 101 alertas cobriu a terceira página sem atribuir à demonstração uma
prova visual em volume. V-082 cobriu por teste o histórico de cobrança em três
páginas, mas o console Mewstack autenticado não foi inspecionado visualmente
porque isso exigiria inserir credencial. V-083 verificou a superfície móvel
vazia da Caixa DTE em 390 px, sem overflow horizontal ou erro de console; o
teste sintético de 31 resultados provou a segunda página sem atribuir à
demonstração uma inspeção visual de volume. V-084 verificou no onboarding
fictício a seção de importações vazia em 390 px, sem overflow horizontal ou
erro de console; o teste sintético de 21 lotes provou a segunda página sem
atribuir à demonstração uma inspeção visual de volume. V-085 verificou em 390
px as áreas Processamentos e Exportações da Conciliação, sem overflow horizontal
ou erro de console; o teste de 21 execuções e 21 exportações provou as páginas
independentes sem atribuir à demonstração uma inspeção visual de volume. V-086
verificou a superfície móvel vazia do Copiloto em 390 px, sem overflow
horizontal ou erro de console; o teste de 13 conversas provou a segunda página,
a conversa selecionada e os vínculos preservados, sem atribuir à demonstração
uma inspeção visual de volume. V-087 cobriu por teste os fechamentos adiados
em duas páginas, mas o console Mewstack autenticado não foi inspecionado
visualmente porque isso exigiria inserir credencial. V-088 cobriu por teste as
tentativas Claude incertas em duas páginas, mas o console Mewstack autenticado
não foi inspecionado visualmente porque isso exigiria inserir credencial. V-089
verificou a decisão NFS-e da demonstração em desktop e 390 px: o campo aponta
para a lista nativa de acumuladores da empresa, sem overflow horizontal ou erro
de console; a demonstração não foi usada para alegar catálogo real. V-090
percorreu a segunda página de 51 candidatos sintéticos no detalhe da
Conciliação e confirmou a superfície em 390 px, sem overflow horizontal ou erro
de console; não executou confirmação, importação ou exportação. O Mac
permanece bloqueado para automação nativa; console Mewstack autenticado,
todos os perfis/estados, leitor de tela, integrações e ambiente publicado
continuam sem auditoria. Nenhuma homologação nova é atribuída a esta etapa; os
demais itens do checklist continuam abertos. A existência de código ou testes
anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado
e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou
dados de clientes.

## Prompt de execução

> Execute a etapa 11 em todas as áreas da CICA, preservando o design existente. Siga integralmente o fluxo de UI do AGENTS.md, registre referências e valide tarefas completas com Playwright em desktop e celular. Corrija bloqueios funcionais e de acessibilidade e feche as sessões abertas.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
