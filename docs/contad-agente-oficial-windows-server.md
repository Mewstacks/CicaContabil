# Agente oficial CONTAD no Windows Server

Procedimento técnico D-324/D-325/D-326, PC-19, etapas 03/09/12. A sequência única de entrega
permanece no [prompt canônico](contad-prompt-finalizacao-2026-11-06.txt).
Este guia descreve o corte de equipamento, não amplia as fontes autorizadas.

## Estado e pré-requisitos

Última publicação comprovada: release 75/fonte c8b0c50, V-328. Agente anterior
com MSI 1.0.3 e manifesto piloto; MSI 1.0.4 preparado não possui o protocolo de
substituição em duas fases. **V-338:** MSI **1.0.5/.NET 10.0.15** da fonte **53b834b** aprovado no
[CI Windows 42863201809](https://github.com/Mewstacks/CicaContabil/actions/runs/42863201809),
com 62 testes e 26 checks instalados. Hash/manifesto/relatório conferidos; pacote
preservado em Downloads/CICA-CONTAD-Agente-1.0.5-NET10-2026-11-10.
MSI sem assinatura de editor. Backend compatível e instalação/corte reais pendentes.

**D-325/V-337, 10/11:** responsável aprovou .NET 10 LTS, revisando D-289.
Os projetos e CI foram migrados; publicação local dos três componentes inclui
runtime autocontido **10.0.15**. Testes no Mac: 59 aprovados e três exclusivos
de Windows pendentes. MSI e ciclo do instalador em Windows posteriormente aprovados em V-338;
instalação na cliente não realizada. A [matriz Microsoft](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)
inclui o **Windows Server 2022 Standard, 21H2/build 20348.5761** observado em
V-331. PowerShell x64/Administrador observados em V-332. Compatibilidade de
plataforma não substitui a prova do pacote/ODBC/DPAPI sob LocalSystem.

O responsável disponibilizou AnyDesk. A ferramenta nativa desta sessão encontrou
o aplicativo aberto, mas obter sua janela por nome/bundle ID falhou com timeout
-10005. Não houve leitura da tela do Server nem ação remota. Isso não invalida
o acesso que o responsável disponibilizou. A identificação do Server 2022
foi obtida agora pela imagem fornecida, sem leitura ou controle da sessão.

Antes de instalar, conferir na máquina destinada à CONTAD:

1. Edição/build, arquitetura AMD64, Windows PowerShell x64 e sessão administrativa.
   Identificar Desktop Experience ou Server Core: o configurador atual usa
   WinForms. Server Core exige outra preparação, sem prometer que essa GUI roda.
2. Serviço/configuração CICA já existentes. Se encontrados, preservar e investigar
   identidade antes de sobrescrever; não copiar `agent.config` de outro PC.
3. Driver SQL Anywhere x64 compatível e DSN **de sistema** local ao Server.
   No novo Server, CICA_CONTAD foi preparado com SQL Anywhere **16 x64**,
   SrvContabil/Contabil e Host/Port vazios, a partir de Contabil 64.
   Teste interativo e limpeza/salvamento informados em V-335/V-336. Preservar
   o DSN usado pelo ERP e inserir EXTERNO somente no Windows.
4. Conexão do configurador e sob LocalSystem, TLS/HTTPS de saída e relógio correto.
   Não abrir porta de entrada, alterar firewall, reiniciar servidor/ERP ou
   instalar driver sem comprovar a necessidade e o escopo da alteração.

O pacote é autocontido; não instalar Python ou SDK no Server para operar o
agente. Conferir a matriz oficial do [.NET 10](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)
e o driver disponível na versão real observada. Compatibilidade da plataforma
não substitui a prova do pacote/ODBC na CONTAD. A proteção DPAPI usa contexto
[LocalMachine](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.dataprotectionscope?view=net-10.0),
por isso a nova instalação configura os segredos na própria máquina e preserva
as ACLs para Administradores/SYSTEM.

## Preparar sem interromper o agente anterior

Primeiro publicar/testar a versão exata do backend e gerar/conferir MSI 1.0.5
em Windows descartável. Não emitir código de substituição na release 75: ela
ainda não implementa esse protocolo. Código antigo e MSI 1.0.4 não o substituem.

Após observar a instalação íntegra, executar no ambiente administrativo CICA:

```text
python manage.py portfolio_sync_status --organization <CONTAD> --agent <ANTERIOR>
python manage.py prepare_agent_replacement --organization <CONTAD> --previous <ANTERIOR> --output <NOVO-ARQUIVO-PRIVADO.json> --minutes 30
```

O comando exige o agente anterior ativo e manifesto válido não vazio, copia
exatamente esse recorte e recusa outro código válido/candidato pendente.
Grava o código somente em novo arquivo 0600, sem sobrescrever arquivo/symlink
ou imprimir o segredo. Entregar por canal privado; não publicar esse JSON.
Sem `--output` não há emissão. Expiração permitida: 1–60 minutos.

No configurador 1.0.5 elevado, cadastrar HTTPS da CICA, identidade da nova máquina,
conexão local e o novo código. A declaração `X-Hub-Agent-Replacement: staged-v1`
é obrigatória; cliente antigo não consome o código. O servidor gera UUID/segredo
próprios e candidato `pending`, sem mudar o agente anterior. O serviço persiste
DPAPI/ACL e informa `awaiting_activation`; heartbeat/configuração funcionam,
enquanto coleta, ingestão, arquivos e backups permanecem recusados. Não interpretar
esse estado como `ready` ou sincronização concluída.

Provar Running/Automatic/LocalSystem, reabertura da configuração após reiniciar
**somente CicaAgent**, ODBC somente leitura, ACL e ausência de credencial em
logs/DSN dedicado. Não interpretar apenas o heartbeat como prova de ODBC/DPAPI.
Se o configurador falhar após consumir código, investigar e revogar somente
o candidato órfão antes de emitir outro; o anterior segue ativo.

## Efetuar o corte e comprovar

Depois das provas Windows, obter UUID do candidato e revisão no diagnóstico.
O operador técnico executa explicitamente, no servidor CICA:

```text
python manage.py activate_official_agent --organization <CONTAD> --candidate <NOVO> --previous <ANTERIOR> --scope-revision <REVISAO-VALIDADA>
```

Exige mesma organização, equipamentos identificados de forma diferente,
candidato pendente vinculado ao anterior ativo, revisão/manifestos idênticos
e heartbeat entre agora e cinco minutos atrás. O corte grava em uma transação
anterior revogado + novo ativo/oficial + auditoria. Restrição de banco permite
um único oficial por escritório. Falha de auditoria reverte todos esses estados;
repetição idêntica depois do sucesso não gera outra troca/auditoria. Requisições
de cadastro/extrato/carteira que já estejam em andamento terminam antes do corte;
depois dele o anterior é recusado. Revogações não apagam dados ou scans.

Conferir `is_official=true`, anterior `revoked`, assinatura anterior recusada,
novo ciclo `ready` e recepção real do recorte no CICA. Desativar serviço antigo
após o corte quando a máquina estiver acessível; a recusa no backend não depende
desse passo. Não desinstalar/apagar a configuração antiga antes de preservar a
evidência técnica. Identidades de empresa/conta/movimento continuam no escritório;
o novo agente inicia seu próprio scan e a recepção evita duplicação dos fatos.
Não transferir o cursor do equipamento anterior ou criar outra CONTAD.

Falha antes do corte: revogar candidato e manter o anterior. Falha depois do
corte: diagnosticar; não restaurar uma credencial revogada. Um retorno de máquina
exige outra substituição explícita com novo pareamento. Nunca reativar o anterior
automaticamente por falha de rede ou ausência de heartbeat.

## Continuar carteira e aceite

Somente após comprovar o corte, executar no novo Server o inventário de metadados
preparado em `agent-windows/inspect-contad-schema.ps1`, adaptando o nome do DSN
se a inspeção real exigir. Situações/fontes precisam de revisão Q-28/Q-46 antes
do manifesto de carteira. Histórico financeiro desde 01/09/2026, cadastros/contas
integrais e demais requisitos do prompt seguem vigentes. Contas, Razão e títulos
não passam a existir porque o agente mudou de máquina.

Publicação, MSI/instalação real, inventário, dados, D-73, Q-47, recuperação,
treinamento e aceite ficam em estados separados. O novo agente só pode ser
relatado como oficial **após** o corte real e sua conferência no backend.

## Passo a passo dentro do Windows Server — operador, 10/11/2026

**V-335/V-336, resultado atual:** operador informou sucesso no reteste e
confirmou limpeza de User ID/Password e salvamento de CICA_CONTAD, preservando
Database. Não repetir a preparação ou o teste sem motivo. Isso é relato humano,
sem inspeção de segredos no registro. Serviço/instalação/LocalSystem continuam
pendentes. **D-325/V-337:** .NET 10 autorizado e migração local verificada;
MSI 1.0.5 testado em Windows em V-338; aguardar backend compatível antes do passo 4.

**V-334, falha histórica:** teste informado recusou login Integrated. Na
configuração **CICA_CONTAD** (não no DSN original), conferir Login →
Authentication=Database. Preencher EXTERNO e senha apenas no Windows para
ODBC → Test Connection. Esse botão exige credenciais; os campos vazios eram
para salvar o DSN. Após o teste limpar User ID/Password antes de salvar. Não
alterar login_mode do banco, escolher outro driver ou enviar captura contendo
credenciais. A captura do erro não mostra DSN/driver/campos atuais; sucesso
não pode ser inferido. Referência: [SAP, Login/Test Connection](https://help.sap.com/doc/ea6cb9dac4f44341a0450f90f5c66096/17.0/en-US/User-interface-context-Sensitive-Help-en.pdf).

**V-333, destino recebido:** Login da conexão inspecionada mostra Server name
SrvContabil, Database name Contabil, Host/Port vazios, Authentication Database e
Action Connect to a running database on another computer. User ID/Password
vazios na captura. Cancelar sem salvar a inspeção do original e preparar novo
DSN de Sistema CICA_CONTAD usando SQL Anywhere 16 (x64), esses parâmetros e sem
usuário/senha salvos. Não preencher IP/porta arbitrários nem mudar o driver.
Network/Advanced não foram inspecionados: não alegar cópia integral ou conexão
concluída. Teste autenticado explícito no Windows segue após a criação confirmada.

**Evidência já recebida, V-331/V-332:** Server 2022 Standard/21H2/build
20348.5761; PowerShell x64/Administrador, serviço sem listagem e configuração
ausente. No ODBC de sistema, Contabil 64 usa SQL Anywhere 16; Contabil 32 usa
17; e-Robo 17 64 também existe. CICA_CONTAD não aparece. Próxima ação é conferir
servidor/banco de Contabil 64 sem salvar/alterar ou ler senha. Não repetir os
passos já comprovados nem supor que os DSNs tenham o mesmo destino.

**Passos 1–3 já percorridos com as evidências acima.** O MSI 1.0.5 está
validado e preservado em Downloads/CICA-CONTAD-Agente-1.0.5-NET10-2026-11-10,
com checksum, release.json e relatório. O backend de substituição **não foi
publicado**; instalação/pareamento nos passos 4–8 aguardam essa liberação e
código novo. Não usar MSI/código anteriores ou copiar o pareamento do PC antigo.

1. **Identificar o Windows.** Abrir Win+R → `winver` e registrar edição/ano e
   versão/build. Abrir Windows PowerShell **64 bits como administrador**:

   ```powershell
   Get-CimInstance Win32_OperatingSystem |
       Select-Object Caption, Version, BuildNumber, OSArchitecture
   $PSVersionTable.PSVersion
   [Environment]::Is64BitProcess
   ```

   O último resultado deve ser True. Se o comando não existir no Windows
   antigo, informar o texto do winver, sem instalar PowerShell/.NET para tentar
   contornar. Confirmar compatibilidade antes do MSI. Server Core requer outra
   preparação: o configurador atual é gráfico. O pacote é autocontido; não
   instalar SDK/Python como pré-requisito. .NET 10 LTS foi aprovado em D-325
   após a identificação do Server 2022; não repetir essa decisão.

2. **Conferir instalação anterior no novo Server.** No mesmo PowerShell:

   ```powershell
   Get-Service CicaAgent -ErrorAction SilentlyContinue
   Test-Path "$env:ProgramData\CICA\Agent\agent.config"
   ```

   Em uma máquina limpa, o primeiro não lista serviço e o segundo retorna
   False. Se houver serviço/configuração, preservar e identificar antes de
   sobrescrever. Não parar o agente do computador antigo nesta preparação.
   Abrir https://cicacontabil.com.br no navegador e conferir HTTPS sem aviso
   de certificado; isso ainda não prova API/HMAC nem conectividade do serviço.

3. **Conferir conexão Domínio/ODBC x64.** Abrir Win+R:

   ```text
   %windir%\System32\odbcad32.exe
   ```

   Na aba Drivers, verificar SQL Anywhere x64 compatível com o Domínio local.
   Na aba DSN de Sistema, verificar conexão dedicada `CICA_CONTAD`. Se ausente,
   sua criação usa servidor/banco/endereço reais da instalação Domínio dessa
   máquina; não inventar porta/nome ou copiar senha/configuração do outro PC.
   Não alterar DSN original do ERP nem criar DSN de Usuário. Ausência de driver
   exige componente oficial compatível; não baixar de fontes avulsas.
   Testar a conexão com EXTERNO e senha inserida apenas no Windows. Não guardar
   a senha no DSN. Driver/DSN da instalação anterior não comprovam os do Server.

4. **Após a entrega do pacote validado, conferir os arquivos.** Copiar
   `CicaAgent.msi`, `release.json` e checksum entregues para
   `C:\CICA-Instalacao`. Ler a versão do release.json e calcular:

   ```powershell
   Get-FileHash 'C:\CICA-Instalacao\CicaAgent.msi' -Algorithm SHA256
   ```

   Deve ser a versão 1.0.5 aprovada para esta troca (ou sucessora explicitamente
   entregue), com hash igual ao informado na entrega. Se não conferir, não
   instalar. Backend compatível e código de substituição são preparados pela
   operação CICA, não pelo Windows da cliente.

5. **Instalar sem reiniciar o Server.** No PowerShell elevado:

   ```powershell
   $cicaInstalacao = Start-Process msiexec.exe -Wait -PassThru -ArgumentList '/i "C:\CICA-Instalacao\CicaAgent.msi" /passive /norestart /L*v "C:\CICA-Instalacao\instalacao.log"'
   $cicaInstalacao.ExitCode
   ```

   Resultado 0 indica sucesso; outro código deve ser informado antes de
   prosseguir. Código 3010 pede reinício; não reiniciar o servidor automaticamente.
   Não usar scripts de teste do CI ou de Windows 11 na máquina da cliente.

   ```powershell
   Get-CimInstance Win32_Service -Filter "Name='CicaAgent'" |
       Select-Object Name, State, StartMode, StartName
   ```

   Esperado: CicaAgent / Running / Auto / LocalSystem. Sem pareamento,
   `agent-status.json` deve informar awaiting_configuration.

6. **Configurar e testar ODBC interativo.** Abrir elevado:

   ```powershell
   Start-Process "$env:ProgramFiles\CICA Agent\Configurator\Cica.Agent.Configurator.exe" -Verb RunAs
   ```

   | Campo | Preencher |
   |---|---|
   | Endereço HTTPS da CICA | https://cicacontabil.com.br |
   | Nome deste servidor | Rótulo identificável, por exemplo CONTAD-SERVIDOR |
   | Fonte de dados | Domínio Local — DSN de 64 bits |
   | DSN do ERP local | CICA_CONTAD, depois de conferido no Server |
   | Driver SQL Anywhere | O x64 compatível encontrado nessa máquina |
   | Usar autenticação já configurada no DSN | Desmarcada para credencial explícita |
   | Usuário do banco | EXTERNO |
   | Senha do banco | Inserir somente no configurador do Windows |
   | Pasta raiz para arquivos | Deixar vazia neste recorte |

   Clicar **Testar conexão**, antes de conectar à CICA. Esperado:
   “Conexão confirmada. O Domínio está pronto para sincronizar.” Isso comprova
   o teste somente leitura sob a sessão do operador, não sob LocalSystem.

7. **Parear como candidato.** Depois da confirmação de backend/pacote,
   solicitar o código novo de substituição por canal privado. Preencher o
   código temporário e clicar **Conectar à CICA** uma vez. Não é senha de login
   da Grazi nem código antigo. Conferir recorte apresentado; migração inicial
   herda o piloto e não habilita carteira inteira. Se houver erro após consumo,
   informar sem repetir pareamentos/compartilhar códigos; tratar candidato
   órfão antes de outro código.

8. **Provar reabertura da configuração e aguardar ativação.** Reiniciar somente
   o serviço CICA, aguardar até 90 segundos e ler o estado seguro:

   ```powershell
   Restart-Service CicaAgent
   Get-CimInstance Win32_Service -Filter "Name='CicaAgent'" |
       Select-Object Name, State, StartMode, StartName
   Get-Content "$env:ProgramData\CICA\Agent\agent-status.json" -Raw |
       ConvertFrom-Json |
       Select-Object state, version, observed_at_utc, detail
   ```

   Esperado antes do corte: Running / Auto / LocalSystem e awaiting_activation,
   versão entregue e horário posterior ao reinício. Se o horário ainda for
   antigo, aguardar e repetir apenas a leitura. Esse estado não lê o ERP: não
   comprova ODBC sob LocalSystem ou recepção de dados. Não abrir/exportar
   `agent.config` nem remover sua proteção.

9. **Ativação oficial é ação da operação CICA.** O operador do Server informa
   os resultados sem senha/código; a operação confere as provas, heartbeat,
   identidades e revisão, completa verificações faltantes e executa o corte no
   backend. Somente ele ativa o novo e revoga o anterior. Comando Django do
   backend não é executado no Windows da cliente. Depois do corte, o serviço
   deve chegar a ready (ou update_available, que também sucede ciclo concluído).
   Conferir no backend recebimento, conta/empresa/competência e ausência de
   duplicação, preservando os 163 eventos do piloto como a mesma amostra.
   A leitura real sob LocalSystem precisa ser comprovada; não deduzi-la do
   teste do configurador ou do simples serviço Running.

10. **Conferência final e falhas.** Repetir o reinício somente do serviço após
    o corte e conferir novo ciclo/recepção sem duplicação. Não desligar a rede
    do Server de produção para testar indisponibilidade; esse ensaio exige
    procedimento específico. Só desativar o serviço do PC antigo após corte
    confirmado. Carteira completa, inventário e fontes novas são o próximo
    passo, não consequência automática da instalação.

Para acompanhamento, enviar somente: Windows/build/arquitetura, versão do
agente, resultado do teste ODBC, State/StartMode/StartName e os quatro campos
seguros de agent-status.json. Se falhar, informar etapa e mensagem. Nunca
enviar senha, código temporário, conteúdo de agent.config ou extrato/registro
do ERP. Arquivo de instalação/Visualizador de Eventos é consultado localmente;
compartilhar apenas erro pertinente revisado, não logs completos por padrão.
