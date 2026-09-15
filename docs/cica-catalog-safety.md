# Catálogo comercial: proteção inicial dos contratos

Revisão local em 13/09/2026. Não constitui homologação comercial.

## Correções verificadas

- O endpoint de configuração não reescreve planos referenciados por contratos, inclusive testes e contratos arquivados. Retorna 409 sem persistir alterações. Novas condições exigem outro registro de catálogo.
- Um identificador de plano malformado ou inexistente retorna 404, sem criar um plano acidentalmente.
- A seleção do plano para edição ocorre com bloqueio de linha em transação. Concorrência real em PostgreSQL ainda não foi ensaiada.
- A mensalidade contratual zero não é interpretada como ausência de preço durante consumo ou faturamento. A herança inicial do catálogo permanece no evento de criação do contrato.
- O formulário de catálogo usa Decimal para converter a mensalidade inicial.

## Evidências

- `tests/test_cica_configuration.py` e `tests/test_platform_billing.py`: 16 testes passaram.
- Pagamentos, serviços, tenant, cadastro e segurança do cadastro: 22 testes passaram.
- Ruff nos cinco arquivos Python alterados: passou.
- Não houve alteração de template, estilo ou animação nesta rodada. Não houve nova validação visual.

## Limites e trabalho restante

- A proteção de edição implementada cobre o endpoint de configuração, não mutações diretas por ORM ou outros caminhos administrativos.
- Todo contrato novo passa a congelar os módulos do plano em `selected_modules`; permissões e autorização operacional preferem esse snapshot. Uma alteração explícita de plano pelo console atualiza o snapshot do contrato e fica auditada. Contratos antigos com snapshot vazio mantêm o fallback legado até revisão comercial.
- Tarifas por serviço ainda podem ser acrescentadas por snapshot tardio. Seu versionamento e aceite precisam ser revisados.
- O contrato agora registra se o valor foi definido pelo console. `R$ 0,00` aprovado fica bloqueado como isenção/teste; somente contrato novo sem valor definido herda o preço do catálogo uma vez.
- A interface de revisão/versionamento, mensagens amigáveis de conflito e publicação comercial permanece pendente.
- Estes testes não demonstram um ciclo completo em Asaas nem autorizam publicar preços.
