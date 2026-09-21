# Etapa 02 — Fechar cadastro, acesso e administração

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Concluída em 18/09/2026 no nível de implementação e validação local (V-007 a V-009, com suporte de transporte retestado em V-052). E-mail real, DNS e SMTP permanecem para homologação integrada da etapa 12, conforme D-77; não são alegados como homologados aqui.

**Dependências:** 01.

**Decisões relacionadas:** D-02, D-04, D-07, D-39.

## Escopo e checklist

- [x] Cadastro, confirmação de e-mail, recuperação, convites, MFA e encerramento do teste implementados e testados localmente.
- [x] Permissões por escritório, empresa, módulo e operação verificadas por rotas e APIs locais.
- [x] Empresas, certificados, equipe e primeiros passos validados em jornadas e testes locais.
- [x] Console Mewstack para suporte, contratos, integrações e falhas verificado localmente.
- [x] Demonstração isolada de dados e operações reais coberta por testes locais.
- [x] E-mails transacionais possuem HTML, texto de reserva e testes locais de falha; homologação Brevo/DNS é da etapa 12 (D-77/D-78).

## Bloqueios e responsabilidade

Não há bloqueio próprio da etapa. D-79 encerra regras de acesso comercial; a operação de cobrança fica para a etapa 10. D-77/D-78 transferem SMTP, DNS e entrega Brevo reais à etapa 12.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Matriz de autorização por rota/API, isolamento, convite e recuperação expirados, MFA, fim do teste, e-mail entregue/falho e bloqueio de egressão da demo.

**Critério de aceite:** Proprietário, administrador, operador, financeiro, auditor e suporte só realizam ações autorizadas, inclusive por acesso direto às APIs.

## Evidências e próximo passo

V-007: 83 testes de cadastro, convite, MFA, permissões, isolamento, contrato e acesso operacional passaram em 54,47 s. V-008: confirmação de cadastro, convite e recuperação passaram a ter HTML CICA e texto de reserva; 62 testes passaram. V-009 acrescenta 22 testes de APIs/permissões, 4 testes de demonstração isolada e inspeção Playwright autenticada: MFA, painel, equipe, empresas e configurações; em celular não houve overflow, foco foi visível e o console não teve erro. Uma semeadura local de demo foi corretamente recusada por existir escritório operacional com o slug; a barreira foi tratada como evidência, sem sobrescrever dados locais. V-079 revalidou a ficha de empresa em volume local, paginando seus históricos sem abrir escopo de permissões ou integração. D-77 transfere SMTP real, DNS e entrega para a etapa 12.

## Prompt de execução

> Execute a etapa 02. Complete o ciclo de entrada e administração da CICA, incluindo permissões, MFA, empresas, certificados e suporte. Valide as jornadas por perfil e o isolamento entre escritórios. Consulte decisões existentes antes de perguntar regras comerciais ou de acesso.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
