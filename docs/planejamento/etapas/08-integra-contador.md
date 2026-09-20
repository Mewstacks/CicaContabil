# Etapa 08 — Concluir Central Integra Contador

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento em 19/09/2026. V-034 validou localmente DTE, DCTFWeb, PARCSN, consumo e retorno incerto; não houve chamada Serpro, credencial ou documento real.

**Dependências:** 02 e controles de consumo da 10.

**Decisões relacionadas:** D-08, D-14, D-38 a D-42, D-45.

## Escopo e checklist

- [x] DTE: consulta, paginação, teor, autorização específica de ciência e recuperação de retorno incerto. Implementado e validado com transporte simulado; falta a prova Serpro.
- [x] DCTFWeb: declaração, recibo e guia; preservar o escopo registrado sem transmissão. Implementado/testado localmente; falta o contrato e a chamada real.
- [x] Parcelamentos: concluir PARCSN e consultar o responsável antes de ampliar modalidades. O recorte é PARCSN; Q-36 continua obrigatório antes de ampliar.
- [ ] Homologar credenciais centrais, certificados, representação e serviços.
- [x] Validar estimativa, autorização, reserva, liquidação e persistência de documentos. Cobertura local de cotação, token, PDF e estado persistido.
- [x] Impedir repetição automática de operações com resultado incerto. Transporte incerto preserva o estado e não repete chamada automaticamente.

## Bloqueios e responsabilidade

Q-28 e Q-36; Q-05 e Q-30 foram resolvidas por D-76/D-79 e D-72/D-73. Chamadas cobradas exigem autorização específica.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Permissão de ciência, paginação, autorização/custo, indisponibilidade, resultado incerto, idempotência, PDF persistido e consumo conciliado.

**Critério de aceite:** Cada operação prometida completa a jornada real, com documentos, protocolo, consumo e falhas rastreáveis.

## Evidências e próximo passo

V-034 registra 63 testes locais para DTE, DCTFWeb, PARCSN, cliente, autorização, consumo e recuperação. O próximo passo depende de contrato, credenciais centrais, representação, ambiente e amostra Serpro autorizados por canal seguro; uma chamada cobrada requer confirmação específica imediatamente anterior. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 08. Homologue DTE, DCTFWeb e Parcelamentos com credenciais centrais Mewstack e escopo já aprovado. Preserve autorização de ciência e controles de consumo. Antes de qualquer chamada cobrada, solicite aprovação específica de custo; não repita chamadas de resultado incerto.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
