# Etapa 13 — Ativar IA local na máquina definitiva

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Não iniciada nesta execução.

**Dependências:** 05 e disponibilidade do equipamento; não bloqueia a venda inicial por API.

**Decisões relacionadas:** D-46, D-48 a D-52.

## Escopo e checklist

- [ ] Inspecionar hardware e selecionar modelo compatível mediante decisão registrada.
- [ ] Executar treinamento real e avaliação independente por escritório.
- [ ] Medir qualidade, latência, concorrência e consumo de recursos.
- [ ] Homologar isolamento de adaptadores e operação sem API.
- [ ] Migrar o padrão para local somente após aprovação dos resultados.
- [ ] Manter API como reserva autorizada e permitir retorno à versão anterior.

## Bloqueios e responsabilidade

Q-30, Q-34 e Q-35. Hardware/modelo e resultados ainda não homologados.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Benchmark por área/escritório, inferência concorrente, seleção de adaptador, ausência de vazamento, indisponibilidade local, fallback negado/autorizado e rollback.

**Critério de aceite:** Treino real, qualidade e capacidade comprovados na máquina definitiva; mudança de rota aprovada e retorno de versão demonstrado.

## Evidências e próximo passo

Nenhuma homologação nova atribuída a esta etapa. A existência de código ou testes anteriores não prova conclusão. Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 13 quando a máquina definitiva estiver disponível. Consulte as decisões de IA já registradas, valide hardware e modelo, execute treinamento e avaliação reais e apresente as evidências para a mudança de rota. Preserve isolamento por escritório e fallback externo somente autorizado.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
