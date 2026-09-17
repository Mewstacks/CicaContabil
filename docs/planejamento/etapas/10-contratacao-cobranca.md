# Etapa 10 — Concluir contratação, tokens e cobrança

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 02; pode avançar antes das homologações fiscais.

**Decisões relacionadas:** D-08 a D-15, D-44, D-45.

## Escopo e checklist

- [ ] Fechar com o responsável preços, franquias, pesos, tetos, carência e regras de mudança de contrato.
- [ ] Concluir cliente Asaas; o webhook existente não cobre criação e operação integral da cobrança.
- [ ] Homologar Pix, boleto, cartão, atrasos, estornos e eventos fora de ordem.
- [ ] Garantir fatura única, consumo auditável e proteção contra duplicidade.
- [ ] Separar integralmente contratos manuais da automação Asaas.
- [ ] Implementar somente leitura e reativação conforme regras expressamente aprovadas.

## Bloqueios e responsabilidade

Q-01 a Q-06 e Q-08; sandbox/contrato em Q-28.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Cobrança repetida, webhook duplicado/fora de ordem, pagamento tardio, disputa, reserva pendente, mudança de plano e imunidade dos contratos manuais ao Asaas.

**Critério de aceite:** Contrato, acesso, consumo e fatura concordam, inclusive em concorrência e falhas.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 10. Use o modelo comercial confirmado e pergunte apenas valores e regras ainda pendentes. Complete e homologue Asaas e cobrança manual, com tokens inteiros, franquias por módulo e teto aceito. Não publique preços nem crie cobranças reais sem aprovação correspondente.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
