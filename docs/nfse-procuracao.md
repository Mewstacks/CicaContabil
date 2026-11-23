# NFS-e por procuração (D-304, D-305)

Escritório criado depois de D-304 coleta NFS-e pelo ADN com o **próprio e-CNPJ A1** e a **procuração** de cada cliente, em vez do A1 de cada empresa. Escritório que já existe continua exatamente como está (modo `certificate`). Spec: [produto-vendavel.md](specs/produto-vendavel.md).

## Fonte oficial

Manual dos Contribuintes, Guia das APIs do ADN, v1.1 (03/11/2026), §1.1.1(a) e §1.1.2. `GET /contribuintes/DFe/{NSU}?cnpjConsulta=` de outro contribuinte (raiz de CNPJ diferente da do certificado) exige procuração válida cadastrada pelo outorgante no Portal de Serviços da Receita Federal (`https://servicos.receitafederal.gov.br/`); sem ela o ADN devolve **E2245**. A resposta traz `TipoConsulta`: `InscricaoCertificado`, `CnpjBase` ou `Procuracao`.

## Fluxo

1. O escritório (owner ou admin) envia o e-CNPJ em **Cadastros › Procurações**. O arquivo é validado (abre, tem chave, não venceu, CNPJ da mesma raiz do escritório) e guardado cifrado; nunca volta à tela.
2. A carteira entra por planilha em **Coleta automática › Carteira** (CSV ou XLSX com `nome`, `cnpj`, `email` e `codigo`; prévia linha a linha, relatório de erros em CSV; D-310). O e-mail do cliente é o que permite pedir a procuração. Cada empresa ativa vira uma linha de coleta (`NfseSync` de modo `procuracao`). A fila pergunta ao ADN pelo NSU de cada empresa com o e-CNPJ do escritório e o `cnpjConsulta` da empresa.
3. Sem procuração, a empresa fica **Sem procuração** (não é erro) e é reverificada a cada 6 h.
4. O escritório pede a procuração por e-mail, por clique: **Pedir aos selecionados** ou **Pedir a todos sem procuração**. O cliente a cadastra no Portal de Serviços com **outorgado = CNPJ do escritório**, **serviço = NFS-e** e a validade que quiser; pode levar até 24 h para valer.
5. Na próxima verificação (ou em **Verificar**) a empresa vira **Em dia** e as notas passam a chegar. Empresa de mesma raiz do escritório (matriz e filiais) não precisa de procuração.

## Estados

| Estado | Origem | O que fazer |
|---|---|---|
| A verificar | linha nova ou sem resposta ainda | aguardar a fila ou clicar Verificar |
| Sem procuração | ADN 400 E2245 | pedir ao cliente; nova sonda em 6 h |
| Em dia | ADN 200, ou 404 com E2220/E2230 (sem notas novas) | nada |
| Com erro | E2243/E2244/E2246/E2247, E2210–E2213, 401/403, payload inválido | ler a mensagem da linha; E22xx de certificado bloqueia o escritório por 1 h |

Respostas transitórias não mudam o estado da procuração: 404 sem código, 5xx, rede e E2214 (ADN sem acesso à LCR) refazem a tentativa com recuo de 15 min dobrando até 6 h; 429 pausa a fila 60 s; 495 coloca o e-CNPJ em quarentena por 15 min.

## Ritmo

Uma chamada em voo por e-CNPJ, no mínimo 1 s entre chamadas, até 2 páginas (100 notas) por empresa por vez, cadência de 1 h para empresa em dia. A fila encadeia a próxima empresa do mesmo e-CNPJ 1 s depois. Não usa a fila nem o worker de A1 por empresa: as duas filas nunca selecionam linhas uma da outra (`tests/test_nfse_procuracao.py::test_the_two_lanes_never_select_each_others_rows`).

## Ligar em produção (nada disso foi feito)

0. `manage.py product_readiness` (de preferência `--strict`) lista o que ainda falta para vender: suporte da plataforma em somente leitura, e-mail, contatos, termos revisados, planos, Asaas, esta fila e os opcionais Turnstile e Sentry. Não imprime segredo.
1. `legacy_snapshot` do banco de produção, guardado. Rode **da máquina local** com o `.env` apontando para o Neon de produção: o comando só faz SELECT, não lê campo cifrado e não imprime nome nem CNPJ. Não rode por `flyctl ssh console`: web e worker têm 512 MB com pouca folga e o kernel mata um `manage.py` de ~130 MB. Como o comando só existe a partir desta entrega, o "antes" sai do banco de produção com esta imagem **antes** do deploy (a migração 0078 ainda não aplicada: ele pula tabela e coluna que não existem) e o "depois" logo após.
2. `NFSE_ADN_ENVIRONMENT=production` (a procuração não existe no ambiente restrito) e `NFSE_PROCURACAO_SYNC_ENABLED=true`. Com a flag desligada nenhuma tarefa nova roda e a agenda do Celery fica idêntica à anterior.
3. **Capacidade.** O worker atual é um só (`shared-cpu-1x` 512 MB, `--concurrency=1`) e a fila de A1 já o ocupa. Rodar a fila nova sem atrasar a Bianchi exige processo ou memória adicional: custo a confirmar com valor exato antes de aplicar (CLAUDE.md).
4. Piloto com um escritório real: e-CNPJ real e ao menos um cliente com procuração outorgada. Fedrizzi é o candidato (já opera assim no HubFedrizzi).
5. Depois do deploy, `legacy_snapshot --output depois.json` e `legacy_snapshot --compare antes.json depois.json` precisam sair sem violação (contagens só podem crescer; configuração e colunas existentes não podem mudar).

## O que não está provado

Nenhuma chamada ao ADN real foi feita nesta entrega: os testes usam transporte falso com os códigos do manual. A leitura de `TipoConsulta` e o tratamento de E2245/495/429 seguem o manual e o HubFedrizzi, e precisam do piloto. O caminho de menu exato no Portal de Serviços para o cliente cadastrar a procuração não foi verificado (o e-mail só cita o portal e os dados da procuração).
