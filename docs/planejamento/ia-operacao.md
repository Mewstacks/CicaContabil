# Ativação operacional da IA

Atualizado em 15/09/2026. A IA deve permanecer indisponível para escritórios até que todas as verificações abaixo sejam verdadeiras. Este documento não autoriza uma chamada cobrada à Anthropic.

## Estado verificado nesta máquina

Em 15/09, após o responsável adicionar a chave, `uv run python manage.py configure_claude_local_key` confirmou sua presença sem imprimi-la. `uv run python manage.py verify_claude_token_endpoint` recebeu resposta da Anthropic para `claude-sonnet-5`: **16 tokens de entrada contados** com texto sintético. A [contagem de tokens é gratuita](https://platform.claude.com/docs/en/build-with-claude/token-counting). Após autorização específica do responsável para **uma** chamada cobrada, `verify_claude_messages --cost-approved` gerou uma resposta real com texto sintético; a API informou **16 tokens de entrada e 64 de saída**. Pela tarifa oficial, isso corresponde a US$ 0,000672 antes de câmbio/impostos. Não foram enviados dados de cliente. Essa prova valida chave, modelo e transporte Anthropic; ainda não valida a política de cotas, a interface do Copiloto nem uso real por escritório. A configuração central estava com Claude desativado, modelo vazio e limites por solicitação/dia/mês iguais a zero; ainda é preciso configurar e revalidar esses controles para ativar o Copiloto.

O segredo pertence à Mewstack e deve ser colocado somente no `.env` da instalação, na variável `CICA_CLAUDE_API_KEY`. Nunca deve ser cadastrado por escritório, enviado ao navegador, impresso em logs, incluído em ticket ou salvo nesta documentação.

## Sequência para ativar com segurança

1. A chave central já foi adicionada ao `.env`; reiniciar cada processo operacional que precise carregar a variável.
2. O comando de presença e a prova gratuita por API acima passaram. Reexecutá-los após rotação da chave ou mudança do modelo, sem imprimir segredo.
3. Confirmar o modelo publicado pela conta; a configuração atual espera `claude-sonnet-5`.
4. Definir os três limites da Mewstack e, para cada escritório aprovado, os limites por solicitação, diário e mensal. A proposta de valores está em [precificação e cotas](precificacao-e-cotas-ia.md), mas não é aprovação comercial.
5. A chamada sintética aprovada acima foi executada uma vez. O comando `uv run python manage.py verify_claude_messages --cost-approved` continua protegido: **uma** chamada por execução, sem retry, a `/v1/messages`, Sonnet 5 com esforço baixo e máximo de **64 tokens de saída**, sem dados de cliente. **Não repetir sem nova confirmação específica de custo imediatamente antes do teste.** O custo desta prova foi calculado em **US$ 0,000672** (aprox. R$ 0,0035 pela PTAX usada na [pesquisa de cotas](precificacao-e-cotas-ia.md), antes de câmbio/impostos); cobrança única por uso, sem recorrência. Basta não repetir o comando para interromper novos custos; a flag do comando não substitui a aprovação do responsável.
6. Validar resposta, cabeçalhos, ausência de segredo/payload em log, trilha `EgressAudit`, bloqueio antes do teto, falha recuperável e persistência de conversa. Só então liberar um escritório piloto com dados autorizados.

## Controles já presentes no código

- A rota usa a chave de ambiente Mewstack antes de qualquer segredo legado e não aceita chave do escritório.
- O payload é limitado e mascara CPF/CNPJ, e-mail e atribuições óbvias de segredo; o audit guarda hash, custo estimado, modelo, ator e permissão, não o conteúdo.
- A rota Claude exige habilitação global, política/consentimento vigente por escritório, papel permitido e tetos por solicitação, dia e mês antes de enviar a requisição.
- Quando o runtime local estiver configurado e responder, ele tem precedência; Claude fica como caminho temporário e fallback após timeout do runtime local.

## Referências verificadas

`claude-sonnet-5` é o ID atual e custa US$ 2 por milhão de tokens de entrada e US$ 10 por milhão de saída segundo a [documentação Sonnet 5](https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5). A Anthropic permite configurar limite mensal de gasto na Console e limites de gasto/taxa por workspace; eles complementam, mas não substituem, os controles CICA por escritório ([limites](https://platform.claude.com/docs/en/api/rate-limits), [workspaces](https://platform.claude.com/docs/en/manage-claude/workspaces)). O endpoint de contagem de tokens é gratuito e pode compor uma estimativa futura antes da mensagem real ([contagem](https://platform.claude.com/docs/en/build-with-claude/token-counting)).

## Decisões ainda exigidas

- Teto aprovado em reais para cada chamada, dia e mês da Mewstack.
- Franquia/teto de cada escritório e regra de elevação ou revogação.
- Conteúdo que pode sair à Anthropic, base contratual, mascaramento e retenção.
- Critério de troca para o PC local: local obrigatório, Claude como fallback ou Claude removido.

Ver [decisões](decisoes.md), [dúvidas abertas](duvidas-abertas.md) e [estado operacional](estado-operacional.md) para o escopo comercial e de privacidade.
