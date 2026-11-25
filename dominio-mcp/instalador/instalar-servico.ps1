<#
Instala o servico "CICA - Conector MCP do Dominio" neste computador (onde fica o ODBC do Dominio).
O servico so faz conexao de saida para o CICA; nao abre porta.

  .\instalar-servico.ps1 -Hub https://seu-cica -Codigo <codigo da tela Conector MCP>

-SomenteConferir  confere Python, DSN, pacote e banco sem instalar nada e sem gastar o codigo.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Hub,
    [string]$Codigo = '',
    [string]$Nome = $env:COMPUTERNAME,
    [string]$Dsn = 'contabil',
    [string]$Cert = '',
    [string]$Chave = '',
    [string]$Ca = '',
    [switch]$SomenteConferir
)

$ErrorActionPreference = 'Stop'
$Servico = 'DominioMcpAgent'
$Programa = Join-Path $env:ProgramFiles 'HubContador\dominio-mcp'
$Dados = Join-Path $env:ProgramData 'HubContador\dominio-mcp'

function Passo($texto) { Write-Host "==> $texto" -ForegroundColor Cyan }
function Falha($texto) { Write-Host "ERRO: $texto" -ForegroundColor Red; exit 1 }

# 1. Administrador
$papel = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $papel.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Falha 'abra o PowerShell como Administrador.'
}
if (-not $SomenteConferir -and [string]::IsNullOrWhiteSpace($Codigo)) {
    Falha 'passe -Codigo (gerado na tela Conector MCP do CICA).'
}
if ($Hub -notmatch '^https://') { Falha 'o endereco do CICA precisa comecar com https://' }

# 2. Python 3.12+
Passo 'Procurando o Python 3.12 ou mais novo'
$python = $null
foreach ($versao in '3.13', '3.12') {
    $saida = & py "-$versao" -c "import sys;print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $saida) { $python = $saida.Trim(); break }
}
if (-not $python) { Falha 'instale o Python 3.12 (python.org) marcando "py launcher" e rode de novo.' }
Write-Host "    $python"

# 3. DSN de sistema (o servico roda como SYSTEM e nao enxerga DSN de usuario)
Passo "Conferindo o DSN de sistema '$Dsn'"
$achou = $false
foreach ($visao in 'Registry64', 'Registry32') {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey('LocalMachine', $visao)
    $chave = $base.OpenSubKey('SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources')
    if ($chave -and ($chave.GetValueNames() -contains $Dsn)) { $achou = $true }
}
if (-not $achou) {
    Falha "nao existe o DSN de SISTEMA '$Dsn'. Crie em ODBC (64 bits) > DSN de sistema, aba Sistema."
}

# 4. Pacote ao lado do script
$roda = Get-ChildItem -Path $PSScriptRoot -Filter 'dominio_mcp-*.whl' | Sort-Object Name | Select-Object -Last 1
if (-not $roda) { Falha 'nao achei dominio_mcp-*.whl ao lado deste script.' }
Write-Host "    $($roda.Name)"

if ($SomenteConferir) { Write-Host 'Conferido: pode instalar.' -ForegroundColor Green; exit 0 }

# 5. Reinstalacao limpa
if (Get-Service -Name $Servico -ErrorAction SilentlyContinue) {
    Passo 'Removendo a instalacao anterior'
    Stop-Service -Name $Servico -Force -ErrorAction SilentlyContinue
    & sc.exe delete $Servico | Out-Null
    Start-Sleep -Seconds 2
}

# 6. Programa e dados (so SYSTEM e Administradores leem a pasta de dados)
Passo 'Instalando o programa'
New-Item -ItemType Directory -Force -Path $Programa, $Dados | Out-Null
& icacls $Dados /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' | Out-Null
& $python -m venv $Programa
$venv = Join-Path $Programa 'Scripts\python.exe'
& $venv -m pip install --quiet --upgrade pip
& $venv -m pip install --quiet "$($roda.FullName)[servico]"
if ($LASTEXITCODE -ne 0) { Falha 'a instalacao dos pacotes falhou (internet liberada?).' }
& $venv -m pywin32_postinstall -install | Out-Null

$env:DOMINIO_MCP_HOME = $Dados
$env:DOMINIO_MCP_DSN = $Dsn
$cli = Join-Path $Programa 'Scripts\dominio-mcp.exe'

# 7. Banco: catalogo e conferencia (antes de gastar o codigo)
Passo 'Lendo o catalogo do banco (alguns minutos)'
& $cli build-pack
if ($LASTEXITCODE -ne 0) { Falha 'nao consegui ler o catalogo do Dominio. Rode: dominio-mcp doctor' }
& $cli doctor
if ($LASTEXITCODE -ne 0) { Falha 'a conferencia do banco falhou.' }

# 8. Pareamento
Passo 'Pareando com o CICA'
$argumentos = @('agent-enroll', '--hub', $Hub, '--codigo', $Codigo, '--nome', $Nome)
if ($Cert) { $argumentos += @('--cert', $Cert, '--chave', $Chave) }
if ($Ca) { $argumentos += @('--ca', $Ca) }
& $cli @argumentos
if ($LASTEXITCODE -ne 0) { Falha 'o CICA recusou o codigo (expira em 30 min; gere outro na tela).' }

# 9. Servico automatico, com reinicio sozinho
Passo 'Criando o servico'
& $venv -m dominio_mcp.service --startup auto install | Out-Null
& sc.exe failure $Servico reset= 86400 actions= restart/5000/restart/5000/restart/60000 | Out-Null
$chaveServico = "HKLM:\SYSTEM\CurrentControlSet\Services\$Servico"
New-ItemProperty -Path $chaveServico -Name 'Environment' -PropertyType MultiString `
    -Value @("DOMINIO_MCP_HOME=$Dados", "DOMINIO_MCP_DSN=$Dsn") -Force | Out-Null
Start-Service -Name $Servico
Start-Sleep -Seconds 5
if ((Get-Service -Name $Servico).Status -ne 'Running') {
    Falha "o servico nao ficou ativo. Veja o Visualizador de Eventos > Aplicativo ($Servico)."
}
Write-Host 'Servico ativo. Na tela Conector MCP do CICA o computador deve aparecer Online.' -ForegroundColor Green
