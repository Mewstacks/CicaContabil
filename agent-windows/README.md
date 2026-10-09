# Agente CICA para Windows

Native .NET 8 Windows service and guided configurator. The MSI supports:

- Sincronização de leitura do Domínio Local por SQL Anywhere de 64 bits.
- Sincronização de leitura do Siescon por Pervasive/PSQL de 32 bits, isolada na ponte x86.
- Trabalhos de backup Domínio Web enviados manualmente na CICA.
- approved Triagem attachments copied to the office's Windows folder.

Leia o fluxo de instalação e diagnóstico em [INSTALACAO.md](INSTALACAO.md).
Os contratos técnicos Domínio confirmados por metadados estão em [CONTRATOS-DOMINIO.md](CONTRATOS-DOMINIO.md).

O pacote é único. No configurador, o escritório escolhe Domínio Web, Domínio Local ou Siescon.
Para Domínio Local ele lista somente DSNs de sistema e drivers SQL Anywhere de 64 bits; para
Siescon, somente DSNs Pervasive/PSQL da visão de 32 bits, testados pela ponte x86. A credencial
vai à ponte por entrada padrão, nunca por argumento de processo ou log.
The native CICA service is the installed and supported component for read-only Domínio/Siescon
synchronization, Domínio Web backups, and Triagem archiving. The Python agent is restricted to
temporary diagnostics and migration. For Triagem, the configurator stores the approved root with DPAPI and the server
sends only a relative company/document path. The service refuses path escape and reparse-point
redirects, proves the configured root, writes a temporary file, validates SHA-256 and size, and
renames atomically. CICA keeps the item in `Arquivando` until that proof returns.

The service only opens outbound HTTPS connections. Enrollment creates the private key and CSR
on the office computer; the API returns only the signed client certificate and its chain. Runtime
configuration is protected with Windows DPAPI (`LocalMachine`) and the MSI restricts its folder to
Administrators and `LocalSystem`.

Domínio Web `.dom` files are password-protected ZIP-compatible containers. The agent extracts the
`contabil.db` file with the per-file Onvio key, then opens the database with an installed SQL
Anywhere 16/17 ODBC driver. SAP/Thomson Reuters runtime files are proprietary and are deliberately
não redistribuídos pela CICA.

## Contratos de consulta

Desde a incorporação do módulo Rentabilidade (D-281, D-284), as consultas que o
agente executa **não vivem mais no código-fonte**. Elas ficam em
`contracts/datasets/`, na raiz do repositório, com o manifesto que fixa o SHA-256
de cada uma — o mesmo arquivo que o servidor lê. O manifesto e os arquivos SQL são
incorporados no binário e conferidos quando o serviço sobe: hash divergente,
consulta que não começa em `SELECT`, ponto-e-vírgula no meio ou contagem de
parâmetros diferente da declarada derrubam o serviço com a razão no log, em vez de
falhar calado num ciclo noturno.

A nuvem manda o **código** do contrato e o hash que espera; o SQL sai do catálogo
incorporado. Um conector apontado para o Domínio nunca executa consulta do Siescon,
mesmo que o código exista nos dois — a chave do catálogo carrega o sistema de
origem, e o sistema vem da configuração do conector.

Alterar uma consulta significa alterar o arquivo em `contracts/datasets/` **e** o
hash no manifesto. Sem os dois, nem o agente nem o servidor a aceitam.

## Siescon e a ponte de 32 bits

Por D-290, o levantamento Siescon trazido do Lucrums é a base técnica do adaptador.
O Pervasive, que o Siescon usa, só publica driver ODBC de 32 bits, e um processo
não carrega driver de outra arquitetura — então o serviço continua x64 e delega a
leitura a `Cica.Agent.OdbcBridge`, publicada em `odbc-bridge/` dentro da pasta do
serviço. A ponte fala por entrada e saída padrão, sem rede e sem arquivo
temporário, e a credencial nunca vai pela linha de comando.

O limite está registrado junto da autorização: o layout foi **inferido** por
perfilamento estrutural, não documentado pelo fornecedor. Uma atualização do
Siescon pode mudar a estrutura sem aviso, e por isso a leitura tem de falhar de
forma visível em vez de devolver número errado em silêncio.

## Atualização

O agente compara a versão instalada com a que o servidor devolve e registra
`update_available` no diagnóstico. Ele **não baixa, não executa e não instala** MSI
automaticamente — ver V-022 e D-291. O conector de origem fazia isso; absorver esse
comportamento reverteria uma escolha já validada, num binário assinado que roda
dentro do servidor do cliente.

Build the MSI on Windows:

```powershell
.\build.ps1
```

The deterministic outputs are written to `artifacts/`, including a SHA-256 checksum and dependency
inventory. O build recusa o pacote se serviço, configurador, ponte x86 ou diagnóstico estiverem
ausentes, e o CI repete a geração completa em `windows-latest`. Publish the checksum alongside the stable MSI download URL. Existing Python agents keep
using `/api/v1/intelligence/agent/*` during migration.
