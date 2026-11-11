# Chaves e relações das fontes CONTAD

D-335 complementa o inventário já recebido, sem repetir a descoberta de601
objetos ou atualizar o agente1.0.7. O próximo passo de contas/Razão depende de
chaves comprovadas, inclusive da empresa dona do plano de contas.

`agent-windows/inspect-contad-relations.ps1` lê somente projeções explícitas dos
catálogos SQL Anywhere Server: SYSTAB/SYSUSER, SYSIDX/SYSIDXCOL, SYSFKEY e
SYSTABCOL. Não seleciona senhas, comentários, defaults ou linhas de negócio.
Há três consultas fixas parametrizadas: nove tabelas base, até1024 colunas de
chaves/índices únicos e até2048 colunas de relações declaradas de entrada/saída.
Cada consulta tem timeout40s e uma linha adicional denuncia estouro do limite;
o complemento limita a leitura a150s e o relatório a2MiB.

Alvos: GEEMPRE, CTCONTAS, CTCONTACAIXA, CTCONTACAIXA_CONTA_BANCARIA,
CTLANCTO, CTCLANCTO, CTCCUSTO, EFCLIENTES e EFFORNECE. Todos constam do
inventário original, cujo SHA-256 permanece4b7be104…652e3c69. Não adicionar
tabelas de títulos com base apenas na semelhança de nomes.

Credencial local EXTERNO é solicitada pela janela Windows. O script não lê
registro, senha salva ou configuração DPAPI do agente; não envia dados. Grava
`Downloads\CICA-CONTAD-Relacoes-<id>\relacoes.json` em pasta de ACL privada
(usuário/SYSTEM/Administradores). Por padrão mostra resumo/caminho/hash;
`-AsJson` mostra os metadados completos para retorno textual, sem transferência
manual do script. Falhas mostram apenas etapa/tipos/SQLState/códigos nativos.

O download é HTTPS com commit fixo e SHA-256 verificado antes da execução.
O comando entregue não altera serviço, DSN, pareamento, escopo ou datasets,
não instala tarefa persistente e não habilita atualizações automáticas.

## Análise local

Com o JSON real recebido, executar no ambiente Python já existente do projeto:

```sh
PYTHONPATH=src python scripts/analyze_contad_relations.py \
  --catalog /caminho/privado/relacoes.json \
  --inventory /caminho/privado/inventario.json \
  --output /caminho/privado/analise-nova.json
```

A análise não inicia Django, não usa rede e não escreve no banco. Recusa JSON
duplicado/excessivo, campos desconhecidos, identidades conflitantes, chaves
incompletas, perda de ordem composta, relações sem índice correspondente e
colunas divergentes do inventário. O relatório é privado0600 e não substitui
um destino existente. Posições ODBC não são tratadas como IDs de coluna.

Pares FK seguem `SYSIDXCOL.primary_column_id`; a ordem da chave referenciada
pode diferir da ordem estrangeira. Preservam-se categoria/unicidade e o valor
bruto `not_enforced`, documentado pelo fornecedor como de uso interno; não
interpretá-lo como prova de integridade financeira. Referências fora da seleção
ficam identificadas sem alegar que a chave alvo foi confrontada.

Mesmo um catálogo consistente mantém `financial_collection_enabled=false` e
`human_reviewed=false`. Ausência de FK não comprova ausência de relação.
Plano compartilhado, partidas, sinais, cancelamentos, títulos/baixas, situaçãoM
e aceite financeiro continuam dependentes das provas próprias Q-28/Q-46/Q-47.

Referências do fornecedor: [SYSFKEY](https://help.sap.com/docs/SAP_SQL_Anywhere/93079d4ba8e44920ae63ffb4def91f5b/3be8a8d96c5f1014bb2cb502516a5227.html),
[SYSIDXCOL](https://help.sap.com/docs/SAP_SQL_Anywhere/93079d4ba8e44920ae63ffb4def91f5b/3be8e1416c5f1014aa0185d6ff33803a.html),
[SYSIDX](https://help.sap.com/docs/SAP_SQL_Anywhere/e38b2f6217f24bdb90a3ff8ae57b1dd5/3be8d99a6c5f10149158a1c4b55629f2.html).
