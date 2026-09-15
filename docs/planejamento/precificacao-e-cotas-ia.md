# Pesquisa de custo e proposta de cotas da IA

Atualizado em 15/09/2026. **Proposta para decisão, não preço ou franquia aprovados.** O responsável escolheu Claude Sonnet via chave central no `.env` e pediu limites ideais por escritório. Os planos antigos descrevem cotas por organização e nenhuma cobrança avulsa por pergunta; `pricing.py` ainda indica R$ 249/mês para o Copiloto, mas esse valor de código não confirma a oferta final. A Triagem usará a mesma chave, porém seu consumo documental exige orçamento próprio.

## Referência verificável

A [tabela oficial Anthropic](https://platform.claude.com/docs/en/models/overview) identifica `claude-sonnet-5` a **US$ 2 por milhão de tokens de entrada** e **US$ 10 por milhão de tokens de saída**. O [BCB/PTAX de 14/09/2026](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do) mostra R$ 5,1696 por US$ 1. Uma resposta compacta de 3.000 tokens de entrada e 900 de saída custaria cerca de **US$ 0,015, ou R$ 0,08**, antes de variação cambial, cache, impostos e desvios de tamanho. A aplicação limita o contexto enviado e `max_tokens` a 900 para Sonnet 5. Esse cálculo é cenário, não medição de uso real.

| Controle proposto para o Copiloto | Valor inicial | Motivo |
| --- | --- | --- |
| Reserva máxima por pergunta | R$ 0,15 | Cobrir variação do cenário de R$ 0,08 e bloquear antes da chamada |
| Franquia mensal por escritório | 500 perguntas | Reservar até R$ 75/mês para um Copiloto de código a R$ 249/mês; o custo no cenário seria ~R$ 40 |
| Teto diário por escritório | R$ 10 | Evitar concentração anormal de chamadas em um dia |
| Teto mensal por escritório | R$ 75 | Parar no máximo da franquia; sem excedente automático |
| Teste de 14 dias | 20 perguntas | Permitir avaliação com custo reservado máximo de R$ 3 por escritório |

Esses valores equivalem, no cenário, a cerca de 16% da mensalidade do módulo; a reserva conservadora chega a 30%. A proporção real depende do preço final, mix de chamadas, quantidade de escritórios, câmbio e volume da Triagem. O plano comercial pode precisar de franquias por porte; não inventar multiplicador para empresas sem confirmação. `PlanServiceRate` e políticas por escritório devem congelar a franquia contratada e bloquear ao atingir o teto; elevação/revogação exigem autoridade e trilha definidas.

## Decisões ainda necessárias

1. O modelo completo será `claude-sonnet-5` na conta da Mewstack, ou outra versão Sonnet disponível? A conta/API e os preços precisam ser conferidos antes da ativação.
2. A proposta de 500 perguntas/R$ 0,15/R$ 10/R$ 75 e 20 perguntas de teste atende aos planos comerciais anteriores? Qual preço e multiplicador por porte ficam aprovados?
3. Qual franquia **separada da Triagem** vale para anexos, páginas/OCR e reprocessamento? Um documento longo pode custar muito mais que uma pergunta compacta.
4. Quem pode elevar tetos, se há excedente mediante aceite, e qual limite absoluto global Mewstack vale no mês?
5. Que conteúdo pode ir à Anthropic, com que mascaramento, aviso contratual e retenção? Sem isso não liberar anexos reais.

Testes de roteamento e payload podem usar respostas simuladas sem cobrança. Uma chamada real à API Anthropic tem custo por uso; antes dela, informar escopo, preço estimado e reversão e obter confirmação explícita específica, conforme `AGENTS.md`.
