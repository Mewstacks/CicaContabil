<# Remove o servico "CICA - Conector MCP do Dominio" e o programa. Os dados (pareamento) so saem com -ApagarDados. #>
[CmdletBinding()]
param([switch]$ApagarDados)

$ErrorActionPreference = 'Stop'
$Servico = 'DominioMcpAgent'
$papel = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $papel.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'ERRO: abra o PowerShell como Administrador.' -ForegroundColor Red
    exit 1
}
if (Get-Service -Name $Servico -ErrorAction SilentlyContinue) {
    Stop-Service -Name $Servico -Force -ErrorAction SilentlyContinue
    & sc.exe delete $Servico | Out-Null
}
Remove-Item -Recurse -Force (Join-Path $env:ProgramFiles 'HubContador\dominio-mcp') -ErrorAction SilentlyContinue
if ($ApagarDados) {
    Remove-Item -Recurse -Force (Join-Path $env:ProgramData 'HubContador\dominio-mcp') -ErrorAction SilentlyContinue
}
Write-Host 'Removido. Desconecte o computador tambem na tela Conector MCP do CICA.'
