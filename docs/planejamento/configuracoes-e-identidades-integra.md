# Configurações e identidades do Integra Contador

Atualizado em 16/09/2026.

## Decisão de interface

O Console Mewstack apresenta uma categoria por vez, com índice lateral, URL profunda e formulários independentes. Quando uma submissão contém erros, a categoria correspondente abre automaticamente. A decisão segue o padrão observado no GitHub Desktop, no layout de configurações do Shopify Polaris e na navegação administrativa da Atlassian: categorias estáveis, largura controlada e edição focada. O Watermelon UI não retornou uma composição equivalente para este caso.

## Identidades de cada solicitação Serpro

- `contratante`: CNPJ da Mewstack que contratou o Integra Contador, configurado uma vez no servidor.
- `autorPedidoDados`: CNPJ do escritório contábil responsável, obtido do cadastro daquele escritório.
- `contribuinte`: CNPJ ou CPF da empresa selecionada para a operação.

`INTEGRA_AUTOR_PEDIDO_CNPJ` permanece apenas como fallback de comandos técnicos antigos sem contexto de escritório. As operações DTE, DCTFWeb, guias e Parcelamentos passam explicitamente o CNPJ do escritório e não usam o CNPJ da empresa como autor.

## Provas e limite atual

Testes automatizados verificam a separação das três identidades e a estrutura navegável da tela. A inspeção Playwright não pôde ser concluída porque o MCP retornou `Transport closed`. Antes da ativação real, ainda é obrigatório homologar a procuração e, quando aplicável, o termo `AUTENTICAPROCURADOR` no contrato Serpro da Mewstack.
