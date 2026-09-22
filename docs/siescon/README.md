# Siescon — base técnica do adaptador

Este material veio do projeto Lucrums na incorporação do módulo Rentabilidade e é, por
**D-117**, a base técnica do adaptador Siescon — no lugar do contrato do fornecedor que
Q-33 esperava. Com ele, a etapa 04 deixou de estar bloqueada por falta de documentação.

| Arquivo | O que é |
|---|---|
| [analise-siescon.md](analise-siescon.md) | O levantamento: o que o Siescon guarda, onde, e por que não expõe SQL |
| [layout-v0.sql](layout-v0.sql) | O DDL que cria os DDFs sem os quais o Pervasive não aceita `SELECT` |
| [consultas-v0.sql](consultas-v0.sql) | As consultas de referência sobre esse layout |
| [o-que-preciso.md](o-que-preciso.md) | O que precisa ser pedido ao escritório antes de executar qualquer coisa |
| [preparar-siescon-admin.ps1](preparar-siescon-admin.ps1) | Preparação do ambiente, para executar com autorização |
| [ensaiar-ddf-em-copia.ps1](ensaiar-ddf-em-copia.ps1) | Ensaio dos DDFs **numa cópia**, antes de tocar na base do escritório |
| [criar-tabela-folha.ps1](criar-tabela-folha.ps1) | Criação da tabela de folha, que é a fonte do custo por hora |

## O limite, registrado junto com a autorização

O layout foi **inferido** por perfilamento estrutural dos arquivos, não documentado pelo
fornecedor. Duas consequências práticas, ambas parte de D-117:

Uma atualização do Siescon pode mudar a estrutura sem aviso. A leitura tem de falhar de
forma visível — o catálogo fixado por SHA-256 e a conferência de colunas contra o contrato
existem para isso — em vez de devolver número errado em silêncio.

As consultas Siescon entram no catálogo como as demais e permanecem marcadas como não
validadas até serem exercitadas contra uma base autorizada. `taxation` continua nesse
estado; `companies`, `users` e `salaries` já foram exercitadas do lado da origem.

## Como o conector lê

O Pervasive só publica driver ODBC de 32 bits, e um processo não carrega driver de outra
arquitetura. O serviço CICA continua x64 e delega a leitura à ponte
`Cica.Agent.OdbcBridge`, publicada em `odbc-bridge/` dentro da pasta do serviço. Ver
[o README do agente](../../agent-windows/README.md).

Nenhum script desta pasta é executado por inferência: todos tocam a base do escritório e
dependem de autorização explícita, conforme o próprio [o-que-preciso.md](o-que-preciso.md).
