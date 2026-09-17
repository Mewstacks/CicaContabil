# Etapa 02 — Fechar cadastro, acesso e administração

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 01.

**Decisões relacionadas:** D-02, D-04, D-07, D-39.

## Escopo e checklist

- [ ] Completar cadastro, confirmação de e-mail, recuperação, convites, MFA e fim do teste.
- [ ] Conferir permissões por escritório, empresa, módulo e operação.
- [ ] Validar empresas, certificados, equipe e primeiros passos.
- [ ] Completar o console Mewstack para suporte, contratos, integrações e falhas.
- [ ] Garantir que demonstrações não acessem dados ou serviços reais.
- [ ] Homologar e-mail transacional e seus estados de falha.

## Bloqueios e responsabilidade

Q-01 a Q-06 e Q-29: não inventar regras de acesso comercial nem SMTP.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Matriz de autorização por rota/API, isolamento, convite e recuperação expirados, MFA, fim do teste, e-mail entregue/falho e bloqueio de egressão da demo.

**Critério de aceite:** Proprietário, administrador, operador, financeiro, auditor e suporte só realizam ações autorizadas, inclusive por acesso direto às APIs.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 02. Complete o ciclo de entrada e administração da CICA, incluindo permissões, MFA, empresas, certificados e suporte. Valide as jornadas por perfil e o isolamento entre escritórios. Consulte decisões existentes antes de perguntar regras comerciais ou de acesso.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
