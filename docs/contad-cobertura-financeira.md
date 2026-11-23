# Descoberta da cobertura financeira CONTAD

`inspect-contad-portfolio-profile.ps1` consulta somente códigos técnicos e
contagens para as empresas que a origem seleciona por `STAT_EMP=A`. Inclui
empresas sem parâmetros contábeis, sem conta candidata ou sem lançamentos.
Situações diferentes de A não são interpretadas, ativadas ou desativadas.

São três consultas fixas, executadas duas vezes: configuração bruta de
CTPARMTO, candidatos de CTCONTACAIXA com quantidade de referências bancárias
pela chave composta declarada, e contagem mensal de CTLANCTO por empresa,
empresa do plano e filial. O período começa em setembro de 2026 e termina
no primeiro dia do mês corrente, sem incluir a competência ainda aberta.
Não há valores, nomes, inscrições, agência, identificador bancário, documentos
ou históricos. A existência de uma referência de cadastro não comprova
vínculo bancário de uma operação nem associa a conta caixa ao código do Razão.

O script usa Windows PowerShell x64, o DSN CICA_CONTAD existente e credencial
preenchida diretamente no Windows. Não lê configuração/DPAPI do agente,
troca DSN, altera parâmetros do Domínio ou instala componentes. Não solicitar
senha no chat. `test-contad-portfolio-profile.ps1` é exclusivo do Windows
descartável de CI, com conexão sintética; nunca executá-lo no cliente.

Limites: 500 empresas, 5.000 candidatos de contas, 10.000 grupos mensais,
um milhão de registros por grupo e cinco milhões no total, 40 segundos por
consulta e 300 segundos conferidos entre leituras. O timeout do driver pode
exceder o relógio global durante uma chamada bloqueante; não é um SLA de
processamento financeiro. Recusa excesso, duplicação de identidade,
configuração múltipla, campos/tipos incompatíveis e diferença entre as duas
leituras. Não apresenta resultado parcial como completo. Duas leituras
iguais comprovam estabilidade destes códigos/contagens, sem equivaler a
snapshot transacional dos fatos financeiros ou semântica homologada.

O JSON até 16 KiB sai diretamente; acima disso usa gzip/base64 com tamanho
original e SHA-256, até 4 MiB descompactados. Diagnósticos apresentam etapa,
código fixo e códigos ODBC, omitindo mensagens do driver e credenciais.
Só executar a versão exata que passou no CI Windows e cujo hash foi conferido.

Análise offline do retorno privado:

```sh
PYTHONPATH=src python scripts/analyze_contad_portfolio.py \
  --input /caminho/privado/retorno.json \
  --output /caminho/privado/analise-nova.json
```

O analisador valida contrato, hash/transporte, limites, identidades e período.
Gera matriz por empresa/competência com os códigos brutos, planos observados,
ausências e ambiguidades. Zero em uma competência indica ausência de linhas
no recorte consultado, não ausência de obrigações ou aprovação contábil.
O arquivo é criado com permissão privada 0600, sem substituir destino existente.
`input_file_sha256` identifica os bytes recebidos; `source_sha256` identifica
o documento interpretado em JSON canônico, incluindo observação e flags.
Não imprime códigos/conteúdo no terminal e não acessa Django, rede ou ERP.

Esta descoberta não cria FinancialAccount/LedgerAccount, regras, jobs ou
autorização de coleta de valores. O próximo escopo financeiro exige prova
da correspondência entre empresa, plano, filial, conta e banco e as
contagens próprias da coleta mensal; `queue_portfolio_ledger` continua
fazendo apenas prévia até confirmação operacional aplicável. Dados e
retornos reais ficam privados, fora de Git/CI/IA. Revisão de sugestões,
importação Domínio e aceite D-73 mantêm seus próprios critérios.

## Complemento de contas configuradas para conciliação

O modo explícito `-ReconciliationAccountsOnly` faz duas consultas fixas por
leitura: empresas/configurações e códigos de CTCONCILIACAO_CONTA, com Tipo e
Situação literais do CTCONTAS pela chave declarada empresa do plano/conta.
Não repete a consulta de movimentos nem considera conta caixa como banco.
Mantém o mesmo seletor A, duas leituras, limites e transporte; o resultado
interno usa `contad-reconciliation-account-profile-v1` e o analisador reconhece
ambos os modos. Campos de período são contexto da descoberta, sem representar
consulta temporal das configurações. Ausência de conta no catálogo é explícita;
duplicação de chave ou multiplicação no vínculo é recusada. Flags A/S/I e a
presença em configuração não aprovam natureza/atividade analítica, relação
com banco físico, saldo ou fatos. Não seleciona a data de conciliação.
