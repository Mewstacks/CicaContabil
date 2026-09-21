# Etapa 10 — Concluir contratação, tokens e cobrança

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 21/09/2026. D-76/D-79 já resolveram Q-01–Q-06; V-033 confirmou contrato, tokens, fatura e eventos locais, V-040 confirmou o contrato de requisição do cliente Asaas e V-048/V-053/V-056/V-061 retestaram formulários, livros, configuração e contratos locais. V-082 eliminou o corte silencioso do histórico manual de faturas e V-087 fez o mesmo para os fechamentos ainda adiados no console. Não houve criação de cobrança, configuração sandbox ou chamada Asaas.

**Dependências:** 02; pode avançar antes das homologações fiscais.

**Decisões relacionadas:** D-08 a D-15, D-44, D-45.

## Escopo e checklist

- [-] Fechar com o responsável preços, franquias, pesos, tetos, carência e regras de mudança de contrato. Carência, somente leitura, teste e ciclo foram decididos; Q-08 ainda impede fixar os limites de IA/Triagem que dependem do orçamento.
- [x] Implementar o contrato local do cliente Asaas: ambientes explícitos, chave injetada, localização por `externalReference`, criação sem dados de cartão e sem repetição automática de `POST` (V-040).
- [ ] Concluir a orquestração Asaas: ligar dados comerciais autorizados, cliente, cobrança e `PaymentAttempt`; o webhook existente não cobre a criação e operação integral da cobrança.
- [ ] Homologar Pix, boleto, cartão, atrasos, estornos e eventos fora de ordem.
- [x] Garantir fatura única, consumo auditável e proteção contra duplicidade. Livro de preços, reserva/liquidação, competência e eventos idempotentes foram validados localmente.
- [x] Separar integralmente contratos manuais da automação Asaas. O webhook trata apenas tentativas Asaas e o fluxo manual é interno/auditável.
- [x] Implementar somente leitura e reativação conforme regras expressamente aprovadas. As transições locais refletem D-79; a prova de pagamento/estorno real continua pendente.

## Bloqueios e responsabilidade

Q-08; sandbox/contrato em Q-28. Q-01 a Q-06 estão resolvidas por D-76/D-79, mas ainda exigem prova operacional nesta etapa.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Cobrança repetida, webhook duplicado/fora de ordem, pagamento tardio, disputa, reserva pendente, mudança de plano e imunidade dos contratos manuais ao Asaas.

**Critério de aceite:** Contrato, acesso, consumo e fatura concordam, inclusive em concorrência e falhas.

## Evidências e próximo passo

V-033 registra 44 testes locais para contrato, cobrança, tokens e acesso. V-040 acrescenta o contrato local de cliente/cobrança, com transporte substituível e nenhuma chave ou chamada real; V-048 revalidou os formulários, V-053 os livros de consumo/faturamento, V-056 a configuração/controle local e V-061 tarefas, webhook, snapshots contratuais e páginas legais (69 testes). V-082 paginou o histórico manual em teste com 25 faturas sintéticas, sem tocar valores, contratos ou status. V-087 criou 31 ocorrências de fechamento adiadas sintéticas para confirmar a segunda página no console sem executar faturamento, reserva ou alteração de contrato; a inspeção visual autenticada não foi automatizada porque exigiria inserir credenciais. Ainda falta ligar dados comerciais autorizados, cliente, cobrança e `PaymentAttempt`, além de tratar retornos de Pix, boleto e cartão em ambiente autorizado; o sandbox/contrato continua em Q-28 e a homologação fica na etapa 12 por D-87. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 10. Use o modelo comercial confirmado e pergunte apenas valores e regras ainda pendentes. Complete e homologue Asaas e cobrança manual, com tokens inteiros, franquias por módulo e teto aceito. Não publique preços nem crie cobranças reais sem aprovação correspondente.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
