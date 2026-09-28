# Instalação local — agente CICA

## O que este pacote instala

- Serviço Windows `CicaAgent`, iniciado automaticamente.
- Configurador `Cica.Agent.Configurator`, também disponível em **CICA → Configurar CICA Agent** no menu Iniciar.
- Ponte ODBC x86 `Cica.Agent.OdbcBridge`, usada somente para o Siescon.
- Diretório protegido `C:\ProgramData\CICA\Agent` para a configuração DPAPI.

Sem configuração concluída, o serviço permanece em espera e não tenta acessar ERP, pastas ou rede.

## Preparação nesta estação

1. Confirmar Windows 64 bits e permissão de administrador.
2. Para Domínio Local, confirmar DSN de sistema e driver SQL Anywhere de **64 bits**. Para Siescon, confirmar DSN de sistema Pervasive/PSQL de **32 bits**; o serviço permanece x64 e conversa com esse driver somente pela ponte incluída no pacote.
3. Definir a pasta raiz Windows somente quando a Triagem for ativada; o agente recusará caminhos fora dela e redirecionamentos.
4. Executar `CicaAgent.msi` como administrador.

## Configuração local verificável

1. Abrir o configurador instalado.
2. Selecionar Domínio Web, Domínio Local ou Siescon. O configurador alterna entre a visão ODBC de 64 bits do Domínio e a de 32 bits do Siescon e mostra apenas drivers compatíveis.
3. Para uma fonte local, usar **Testar conexão**. No Domínio o teste consulta somente uma empresa pela consulta fixa allowlisted; no Siescon a ponte confirma a abertura do DSN sem executar o catálogo fiscal.
4. Informar a pasta raiz de arquivos apenas se ela já estiver definida para a Triagem.

A raiz usada pelo agente pareado passa a ser atualizada pela configuração **Destino** da Triagem no site da CICA. O configurador local mantém esse campo apenas para diagnóstico e preparação sem site publicado. Nesta versão, use pasta local absoluta; não use letra de unidade mapeada nem UNC.

O endereço HTTPS, código temporário, certificado do agente e pareamento com a CICA dependem do ambiente hospedado e ficam na etapa 12, por D-81. Eles não são necessários para validar a instalação, o DSN, o driver ou a proteção local da configuração.

## Diagnóstico e remoção

- Serviço: `Get-Service CicaAgent`.
- Logs: Visualizador de Eventos do Windows, origem do serviço CICA Agent.
- Configuração local: `C:\ProgramData\CICA\Agent\agent.config` (protegida por DPAPI; não copiar nem editar).
- Estado do agente: `C:\ProgramData\CICA\Agent\agent-status.json`. O arquivo não contém senha, certificado, DSN nem dados do ERP. Estados: `awaiting_configuration`, `configuration_error`, `authorization_error`, `synchronizing`, `ready` e `temporary_error`. `authorization_error` pode indicar revogação ou pareamento incompatível e exige conferência no console CICA; o agente não apaga a configuração por conta própria.
- Certificado: quando estiver a menos de 30 dias do vencimento, o agente gera um CSR novo com a chave privada local e usa `certificate/renew` para renovar. A troca só é efetiva quando o servidor CICA e o proxy de mTLS estiverem homologados na etapa 12.
- Atualização: o heartbeat informa uma versão mais nova como `update_available`, mas o serviço nunca executa um MSI sozinho. Gere cada pacote com `./build.ps1 -Version 1.2.3`; o artefato inclui `CicaAgent.msi.sha256` e `release.json`. Publique e valide o checksum no console CICA na etapa 12; o administrador do escritório executa o MSI assinado para atualizar.
- Diagnóstico rápido local: execute PowerShell como administrador e rode `& <pasta-do-repositório>\agent-windows\diagnosticar.ps1 -AsJson`. Ele informa instalação, serviço, presença do configurador e da ponte x86, presença de configuração, estado seguro do runtime, quantidade de DSNs do sistema e presença do driver SQL Anywhere. Não abre o `agent.config`, não testa conexão, não lê dados do ERP nem mostra senhas, certificados ou nomes de DSN. Código 2 indica pacote incompleto; código 3 indica configuração/autorização que requer correção no console ou configurador.
- Remoção: Aplicativos instalados do Windows. A remoção do pacote não apaga automaticamente documentos de Triagem nem dados do Domínio.
