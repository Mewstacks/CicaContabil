# Instalação local — agente CICA

Em 04/11/2026, D-310/V-311 definiu o novo pareamento por **HTTPS + HMAC**,
sem CA privada ou certificado de cliente. A seção da versão 1.0.3 ao final
descreve esse fluxo. As provas 1.0.0–1.0.2 abaixo registram versões anteriores;
o PC de teste continua na 1.0.1.0, sem novo pareamento.

## O que este pacote instala

- Serviço Windows `CicaAgent`, iniciado automaticamente.
- Configurador `Cica.Agent.Configurator`, também disponível em **CICA → Configurar CICA Agent** no menu Iniciar.
- Ponte ODBC x86 `Cica.Agent.OdbcBridge`, usada somente para o Siescon.
- Diretório protegido `C:\ProgramData\CICA\Agent` para a configuração DPAPI.

Sem configuração concluída, o serviço permanece em espera e não tenta acessar ERP, pastas ou rede.

## Ensaio do instalador em Windows descartável

O fluxo `.github/workflows/agent-windows-validation.yml` gera o MSI, compara o
SHA-256 com `release.json` e executa `test-installer.ps1` em runner Windows
descartável. O ensaio instala, verifica binários/arquiteturas, inicia o serviço,
abre/fecha o configurador, executa o diagnóstico instalado, testa DPAPI com uma
configuração sintética inválida, repara, reinicia e remove o pacote.

O script recusa execução fora de runner GitHub Windows descartável e recusa
uma máquina com agente/configuração existente. Não executar esse roteiro no PC
da cliente: o ensaio remove a própria instalação ao terminar. Ele não comprova
driver/DSN, pareamento real, leitura do Domínio ou importação contábil.

Em caso de sucesso, o fluxo conserva os artefatos
`CicaAgent-tested-windows-x64` (MSI, checksum, manifesto e inventário) e
`CicaAgent-windows-validation` (resultados e logs) por um dia. Baixar e conferir
o hash antes do uso; preservar uma cópia local. Um pacote gerado sem certificado
de assinatura continua sendo pacote de teste, mesmo com checksum conferido.

## Evidência Windows 11

Em 03/11/2026, o mesmo MSI x64 1.0.0 aprovado no Server 2022 foi testado em
**Windows 11 Enterprise ARM64, build 26200, ProductType=1**. O workflow
`agent-windows-11-validation.yml` baixa os bytes originais, exige Windows 11
cliente e registra SO/arquitetura antes do ensaio. As 25 verificações passaram:
[run 41669715057](https://github.com/Mewstacks/CicaContabil/actions/runs/41669715057).
Relatórios locais em `artifacts/windows-11-arm/`; MSI original em `artifacts/`.

Esse teste comprova o ciclo do pacote x64/ponte x86 sob compatibilidade do
Windows ARM64. A prova adicional em **Windows 11 Pro Intel/AMD por RDP**
passou em 03/11/2026 (V-307): 24 verificações, com o agente mantido instalado
sem configuração ERP. Não implica suporte/homologação de driver SQL Anywhere
ARM64, DSN/ODBC real ou pareamento. Não executar `test-installer.ps1` no PC por
RDP: ele é reservado ao runner descartável e remove sua própria instalação.

## Ensaio no PC de teste Windows 11 Intel/AMD

`test-windows11-pc.ps1` é o roteiro específico para PC disponibilizado para teste.
Exige PowerShell x64 como administrador, Windows 11 cliente e o MSI de teste
1.0.0 com SHA fixado no roteiro. Recusa agente/pastas/configuração preexistentes,
instala, confere GUI/serviço/ACL/diagnóstico/DPAPI/reparo/reinício e mantém o
agente instalado sem configuração. Não é roteiro de atualização de cliente.
Não altera política de execução; se houver bloqueio, conferir a política vigente.

Executar na pasta do pacote com MSI, checksum, manifesto e roteiro:
`& .\test-windows11-pc.ps1 -MsiPath .\CicaAgent.msi -OutputDirectory .\validation`.
Logs e relatório ficam em `validation/windows-11-pc-test.json`. Não confundir com
`test-installer.ps1`, que é reservado ao runner e remove sua própria instalação.

## Preparação nesta estação

1. Confirmar Windows 64 bits e permissão de administrador.
2. Para Domínio Local, confirmar DSN de sistema e driver SQL Anywhere de **64 bits**. Para Siescon, confirmar DSN de sistema Pervasive/PSQL de **32 bits**; o serviço permanece x64 e conversa com esse driver somente pela ponte incluída no pacote.
3. Definir a pasta raiz Windows somente quando a Triagem for ativada; o agente recusará caminhos fora dela e redirecionamentos.
4. Executar `CicaAgent.msi` como administrador.

## Configuração local verificável

1. Abrir o configurador instalado **como administrador**, pois a configuração é protegida para Administradores e SYSTEM.
2. Selecionar Domínio Web, Domínio Local ou Siescon. O configurador alterna entre a visão ODBC de 64 bits do Domínio e a de 32 bits do Siescon e mostra apenas drivers compatíveis.
3. Para uma fonte local, usar **Testar conexão**. No Domínio o teste consulta somente uma empresa pela consulta fixa allowlisted; no Siescon a ponte confirma a abertura do DSN sem executar o catálogo fiscal.
4. Informar a pasta raiz de arquivos apenas se ela já estiver definida para a Triagem.

Na versão **1.0.1**, Domínio Local oferece **Usar autenticação já configurada
no DSN**, marcada por padrão em uma configuração nova. Os campos de usuário e
senha ficam desabilitados e não são copiados para a configuração salva nesse
modo. Desmarque somente para fornecer credenciais explícitas. Não existe troca
automática de identidade após erro de senha. Configurações antigas sem o campo
`UseDsnAuthentication` mantêm o modo explícito anterior. O modo de backup
Domínio Web e o Siescon conservam suas credenciais próprias.

Em V-309, o DSN existente funcionava, mas o configurador 1.0.0 o sobrescrevia
com outros valores. A opção nova resolveu o erro 28000 no PC Windows 11 Pro
de teste: atualização 1.0.1 e **conexão confirmada** pelo configurador instalado.
Naquele ensaio, o servidor CICA retornou 503 por falta da CA de emissão do
agente. A versão 1.0.3 dispensa essa CA após a publicação do backend compatível;
sucesso ODBC não significa pareamento ou sincronização concluídos.

`test-upgrade-windows11-pc.ps1` valida a atualização deste ensaio em PC de teste
sem configuração ERP; versões aceitas constam na seção 1.0.3. Exige administrador,
hash aprovado e manifesto; recusa configuração existente ou configurador
aberto e mantém a instalação ao final. Não usar o roteiro de CI que remove
o pacote nem tratar esse ensaio restrito como atualização geral de clientes.

A raiz usada pelo agente pareado passa a ser atualizada pela configuração **Destino** da Triagem no site da CICA. O configurador local mantém esse campo apenas para diagnóstico e preparação sem site publicado. Nesta versão, use pasta local absoluta; não use letra de unidade mapeada nem UNC.

O endereço HTTPS, código temporário e pareamento com a CICA dependem do ambiente hospedado e ficam na etapa 12, por D-81. Eles não são necessários para validar a instalação, o DSN, o driver ou a proteção local da configuração. O novo fluxo D-310 não exige certificado de cliente.

## Diagnóstico e remoção

- Serviço: `Get-Service CicaAgent`.
- Diagnóstico do pacote instalado: `& "$env:ProgramFiles\CICA Agent\Configurator\diagnosticar.ps1" -AsJson`.
- Logs: Visualizador de Eventos do Windows, origem do serviço CICA Agent.
- Configuração local: `C:\ProgramData\CICA\Agent\agent.config` (protegida por DPAPI; não copiar nem editar).
- Estado do agente: `C:\ProgramData\CICA\Agent\agent-status.json`. O arquivo não contém senha, certificado, DSN nem dados do ERP. Estados: `awaiting_configuration`, `configuration_error`, `authorization_error`, `synchronizing`, `ready` e `temporary_error`. `authorization_error` pode indicar revogação ou pareamento incompatível e exige conferência no console CICA; o agente não apaga a configuração por conta própria.
- Certificado, somente em configuração legada `mtls`: quando estiver a menos de 30 dias do vencimento, o agente gera um CSR novo com a chave privada local e usa `certificate/renew` para renovar. Essa opção depende da CA e do proxy mTLS homologados na etapa 12. O modo `hmac` dispensa esse ciclo.
- Atualização: o heartbeat informa uma versão mais nova como `update_available`, mas o serviço nunca executa um MSI sozinho. Gere cada pacote com `./build.ps1 -Version 1.2.3`; o artefato inclui `CicaAgent.msi.sha256` e `release.json`. Publique e valide o checksum no console CICA na etapa 12; o administrador do escritório executa o MSI assinado para atualizar.
- Diagnóstico rápido local: execute PowerShell como administrador e rode `& <pasta-do-repositório>\agent-windows\diagnosticar.ps1 -AsJson`. Ele informa instalação, serviço, presença do configurador e da ponte x86, presença de configuração, estado seguro do runtime, quantidade de DSNs do sistema e presença do driver SQL Anywhere. Não abre o `agent.config`, não testa conexão, não lê dados do ERP nem mostra senhas, certificados ou nomes de DSN. Código 2 indica pacote incompleto; código 3 indica configuração/autorização que requer correção no console ou configurador.
- Remoção: Aplicativos instalados do Windows. A remoção do pacote não apaga automaticamente documentos de Triagem nem dados do Domínio.

## Piloto financeiro restrito — 1.0.2, D-309/V-310

O Domínio Local exige manifesto `dominio-pilot-v1` emitido pelo servidor para
uma empresa, FinancialAccount existente, competência anterior completa e IDs
de extrato revisados. O configurador mostra o recorte e recusa ausência; código
com recorte exige protocolo `scoped-v1`. O serviço filtra empresa/extratos/datas
antes de enviar. O servidor verifica novamente cada página e recusa o lote
inteiro fora do recorte. Sem manifesto não há sincronização financeira v2.
No piloto restrito o serviço não executa backup, arquivos, rentabilidade ou IA.
I_LANCAMENTO não prova conta por si só: confrontar o cabeçalho e o banco.

O pacote 1.0.2 foi aprovado no run
[41845516300](https://github.com/Mewstacks/CicaContabil/actions/runs/41845516300):
38 testes .NET e 25 verificações de instalação/reparo/reinício/remoção em
Windows Server 2022 descartável. Artefato local em `artifacts/windows-1.0.2/`,
SHA-256 `e5bef0da853b740d3286087a863ad74922e2252ab6d969a2d8e2e333512158cc`.
Sem assinatura de editor. Conferir o manifesto e hash de novo antes de instalar.

O roteiro `test-upgrade-windows11-pc.ps1` agora aceita origem 1.0.1.0 e alvo
1.0.2, conservando guardas de administrador, PC AMD64, GUI fechada, ausência de
configuração e hash/manifesto exatos. Não aplicar a PC configurado por esse roteiro.
A tentativa de transferência pela rede local não respondeu; nenhum instalador
1.0.2 foi executado no PC e a instalação 1.0.1 permanece intacta. A espera sem
configuração evita leitura/envio indevidos. Não houve alteração de DSN/firewall.
A conexão interativa do configurador já passou em V-309; serviço LocalSystem,
pareamento/mTLS/recuperação com o destino real ainda exigem prova própria.

Persistência final D-309/V-310: configuração DPAPI é gravada em arquivo
criptografado temporário na pasta protegida, com flush e substituição atômica;
falha conserva o arquivo anterior e limpa o temporário. Ciclos sem mudança de
recorte/destino não regravam configuração. O pacote final foi revalidado no
Windows com 38 testes .NET, incluindo falha por bloqueio de arquivo, e 25 checks
MSI (run 41845516300). Sem atualização no PC ou alteração do DSN.

## Pareamento sem CA privada — 1.0.3, D-310/V-311

O configurador 1.0.3 pede pareamento explícito `authentication_mode=hmac` via
HTTPS. Não gera CSR/PFX, não precisa de certificado de cliente e o serviço não
executa renovação nesse modo. O certificado HTTPS do servidor continua sendo
verificado pelo Windows; redirecionamentos não recebem a requisição assinada.
O segredo individual fica protegido por DPAPI/ACL; configurador e serviço usam
substituição atômica da configuração. A pasta é restringida antes de gravar.

Backend precisa receber a atualização correspondente antes do pareamento.
Servidor antigo que só emite certificados não é contornado: código não vira
outro modo silenciosamente. Configurações antigas sem `AuthenticationMode`
continuam no modo `mtls`; código com recorte mantém empresa/conta/período/IDs.
Instalação que configure mTLS obrigatório explicitamente recusa modo HMAC.

CI Windows: 44 testes .NET e 26 checks, incluindo leitura da configuração HMAC
sem PFX por LocalSystem antes de tentar HTTPS de loopback, sem ERP ou serviço
externo. Pacote 1.0.3 em `artifacts/windows-1.0.3/run-41854423194/`,
SHA-256 `5850a351f9ea54f4b72131c840af5a34534ce9bbe521c62ec605a32695fd8253`;
CI e limites em V-311. Script de
atualização aceita origem 1.0.1.0/1.0.2.0 e alvo 1.0.3 com guardas preservadas.
O PC real conserva 1.0.1.0; não houve nova transferência, instalação ou pareamento.

## Reconferência da candidata — D-311/V-312, 05/11/2026

MSI 1.0.3 reconferido com o mesmo SHA-256 acima. Os 43 arquivos do agente
foram comparados ao commit CI `1bf854958cecae319abc050241f7b83753903265`;
somente esta documentação difere. Teste .NET atual no Mac: 43 aprovados e um
skip Windows. Os 44 testes/26 checks Windows de V-311 são evidência anterior,
sem nova execução Windows do MSI nesta rodada. Não houve atualização do agente.

Backend candidato, migrações, configuração HTTPS/HMAC e retorno estão em
[release CONTAD](../docs/contad-release-2026-11-05.md). Pacote fonte e manifesto
ficam nas evidências locais ignoradas, sem publicação. O login/atualização do
aplicativo Domínio no RDP é outra operação; não constitui pareamento CICA ou
prova ODBC sob LocalSystem. Preservar autenticação do DSN já confirmada.
