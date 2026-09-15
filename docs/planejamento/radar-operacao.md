# Operação do Radar da Reforma

Atualizado em 15/09/2026. Este documento registra somente o que o Radar executa e prova localmente. Não transforma a coleta em consultoria tributária nem declara homologação de disponibilidade das fontes.

## Função entregue no trabalho local

O job diário já registra, para Receita Federal, Ministério da Fazenda e Planalto, a última coleta, o último sucesso, a quantidade de itens vistos e o erro técnico quando a fonte falha. A tela do escritório agora apresenta sempre as três fontes e informa, em linguagem operacional:

- **Coleta concluída**, com data e hora da última atualização;
- **Falha na coleta**, avisando que a próxima execução tentará novamente, sem expor o erro interno; ou
- **Ainda não coletada**, antes da primeira execução.

O filtro de fonte continua no endereço da página (`?fonte=rfb`), e os alertas mantêm links para a publicação oficial. A tela não calcula impacto individual por cliente e não oferece recomendação tributária automática.

## Pesquisa e direção de interface

O catálogo Watermelon UI foi consultado para blocos de status de integração; não houve bloco correspondente à combinação “integração + status + dashboard”. O padrão adotado foi confirmado por referências de produtos SaaS: [SaaSFrame — integrações](https://www.saasframe.io/categories/integrations), [Dust — fluxo de conexões](https://www.saasframe.io/product/flows) e [Uvodo — integrações](https://www.saasframe.io/examples/uvodo-integrations). A adaptação usa cartões agrupados por fonte, estado textual e informação de última execução, preservando a estrutura e os componentes já usados na CICA.

## Evidência local de 15/09/2026

- `tests/test_hub_workspace_views_django.py`: 43 testes aprovados, incluindo filtro, primeira coleta e falha sem vazamento do erro técnico.
- `uv run ruff check src/apps/hub/views.py tests/test_hub_workspace_views_django.py`: aprovado.
- `uv run pytest -q`: 476 aprovados, 1 ignorado e 2 subtestes aprovados; `manage.py check`, `makemigrations --check --dry-run` e `git diff --check` também passaram.
- Playwright MCP em `127.0.0.1:8001`: Radar inspecionado autenticado em 1689 × 1005 e 390 × 844; os três cartões aparecem, não escapam no mobile e o foco do link de salto fica visível. O filtro por teclado gerou `?fonte=rfb`. Não houve mensagens de erro ou aviso no console.
- A lista de alertas é uma tabela de 640 px mínimos no mobile e rola dentro de `.data-table-wrap`; o documento não desloca horizontalmente (`window.scrollX` permaneceu zero).

## Limite para venda

Ainda falta exercitar a tarefa Celery/beat e as três fontes em ambiente de homologação e registrar reexecução idempotente, indisponibilidade, recuperação e relevância das publicações. A fonte marcada como concluída no banco local não comprova disponibilidade futura. Ver também [estado operacional](estado-operacional.md) e [registro de execução](registro-de-execucao.md).
