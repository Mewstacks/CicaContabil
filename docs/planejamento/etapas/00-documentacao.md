## Guia funcional para QA em 09/10/2026 — V-293

- [x] Inventariar áreas e entradas atuais do sistema em um guia na raiz.
- [x] Descrever funções, perfis, jornadas, estados, critérios de evidência e pendências sem declarar homologação nova.
- [x] Conferir links locais e manter separados demo, validação local, produção e aceite externo.

Entrega: [CICA-QA.md](../../../CICA-QA.md). A etapa 00 recebe este material de apoio; os estados
funcionais das etapas 01–14 não mudam por causa da documentação. Evidência em V-293.

## Revisão de planejamento em 05/10/2026 — D-275/V-275

- [x] Confrontar estado histórico, código atual e decisões posteriores sem apagar memória.
- [x] Pesquisar sistemas similares online e registrar fontes e limites de acesso.
- [x] Avaliar funcionalidades, sentido das telas, usabilidade e gaps de ponta a ponta.
- [x] Incorporar 31 pacotes de conclusão ao plano mestre, preservando etapas 00–13.
- [x] Separar defeitos, homologação, propostas novas e hipóteses para teste com usuários.
- [x] Registrar cobertura renderizada atual e seus limites em V-275.

A execução dos pacotes pertence às respectivas etapas funcionais e à próxima solicitação; não é
um item documental tratado como implementado nesta entrega.

Diagnóstico: [auditoria de produto](../auditoria-produto-2026-10-05.md). Esta atualização conclui
o planejamento solicitado e não muda o aceite funcional de nenhuma outra etapa.

# Etapa 00 — Consolidar decisões, inventário e pendências

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Concluída em 17/09/2026 — somente consolidação documental. Evidência V-003 em VALIDACOES.md. Nenhuma etapa de implementação iniciada.

**Dependências:** Nenhuma.

**Decisões relacionadas:** D-46 a D-60.

## Escopo e checklist

- [x] Gravar integralmente o plano e as decisões confirmadas.
- [x] Inventariar módulos, rotas, tarefas, APIs, serviços Windows e integrações.
- [x] Confrontar documentação antiga com o código e decisões posteriores.
- [x] Registrar cada pendência uma única vez, com etapa afetada e responsável pela resposta.
- [x] Preservar o trabalho local existente; não descartar nem sobrescrever alterações.
- [x] Agrupar as perguntas restantes por condições comerciais, regras documentais, dados autorizados para IA, ambientes de homologação e metas operacionais; perguntar somente o ainda não decidido.

## Bloqueios e responsabilidade

Nenhum bloqueio para documentar; as decisões abertas não impedem esta etapa.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Conferir links locais, IDs de decisões, cobertura de 00 a 13, inventário estático e ausência de alterações de código nesta etapa.

**Critério de aceite:** Outra pessoa consegue identificar o próximo trabalho, suas decisões e seus bloqueios sem reconstruir conversas antigas.

## Evidências e próximo passo

Conferência documental: 23 arquivos, 135 links locais, 14 etapas, 60 IDs de decisão e 36 IDs de perguntas; sem links locais ausentes ou IDs duplicados. As etapas contêm dependências, decisões, checklist, bloqueios, testes, aceite, evidências e prompt. `git diff --check -- '*.md'` passou. Ver V-003 na raiz.

Nenhuma homologação externa foi executada. Os resultados V-001 são da análise anterior à edição documental. Próximo trabalho preparado: etapa 01; não executar sem nova solicitação, conforme D-60.

## Prompt de execução

> Execute a etapa 00 do plano mestre da CICA. Materialize os documentos e prompts deste plano, consolide as decisões já confirmadas e elimine contradições documentais sem apagar o histórico. Confira o código atual. Não pergunte novamente decisões registradas; apresente somente lacunas ou conflitos concretos.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
