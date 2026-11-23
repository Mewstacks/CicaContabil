#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$MsiPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not [Environment]::Is64BitProcess -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra Windows PowerShell x64 como administrador.'
}
$servicePath = Join-Path $env:ProgramFiles 'CICA Agent\Service\Cica.Agent.Service.exe'
$configurationPath = Join-Path $env:ProgramData 'CICA\Agent\agent.config'
$statusPath = Join-Path $env:ProgramData 'CICA\Agent\agent-status.json'
if (-not (Test-Path -LiteralPath $configurationPath -PathType Leaf)) { throw 'Agente configurado nao encontrado. Nao parear novamente por este roteiro.' }
$service = Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
if (-not $service -or $service.PathName.Trim('"') -ne $servicePath -or $service.StartName -ne 'LocalSystem') {
    throw 'Servico configurado esperado nao encontrado; nada alterado.'
}
if (Get-Process -Name 'Cica.Agent.Configurator' -ErrorAction SilentlyContinue) { throw 'Feche o configurador antes de atualizar.' }
$sourceVersion = (Get-Item -LiteralPath $servicePath).VersionInfo.FileVersion
if ($sourceVersion -notin @('1.0.3.0', '1.0.4.0')) { throw 'Origem diferente de 1.0.3 ou alvo 1.0.4; nada alterado.' }
$MsiPath = (Resolve-Path -LiteralPath $MsiPath).Path
if ((Get-FileHash -LiteralPath $MsiPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSha256) { throw 'Hash do MSI nao confere.' }
$manifest = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $MsiPath) 'release.json') -Raw | ConvertFrom-Json
if ($manifest.version -ne '1.0.4' -or $manifest.sha256 -ne $ExpectedSha256) { throw 'Manifesto nao confere com o alvo 1.0.4.' }
$beforeHash = (Get-FileHash -LiteralPath $configurationPath -Algorithm SHA256).Hash.ToLowerInvariant()
# Hash only: never decrypt, print or copy credentials. No registry/DSN edits.
$outputDirectory = Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Upgrade-' + [Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($outputDirectory)
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
foreach ($sid in @($identity.User, (New-Object Security.Principal.SecurityIdentifier('S-1-5-18')), (New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')))
}
Set-Acl -LiteralPath $outputDirectory -AclObject $acl
$started = [DateTime]::UtcNow
$exitCode = 0
if ($sourceVersion -eq '1.0.3.0') {
    $install = Start-Process msiexec.exe -ArgumentList @('/i', ('"' + $MsiPath + '"'), '/qn', '/norestart', '/l*v', ('"' + (Join-Path $outputDirectory 'upgrade.log') + '"')) -Wait -PassThru
    $exitCode = $install.ExitCode
    if ($exitCode -ne 0) { throw ('MSI nao concluiu sem reinicio. Codigo: ' + $exitCode + '. Nao remova configuracao nem refaca pareamento.') }
}
if ((Get-Item -LiteralPath $servicePath).VersionInfo.FileVersion -ne '1.0.4.0') { throw 'Versao instalada nao confere.' }
$afterHash = (Get-FileHash -LiteralPath $configurationPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($afterHash -ne $beforeHash) { throw 'Configuracao mudou durante o upgrade. Preserve os arquivos para revisao; nao sobrescreva nem refaca pareamento.' }
$service = Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
if ($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or $service.StartName -ne 'LocalSystem') {
    throw 'Servico nao confirmou Running/Auto/LocalSystem.'
}
$state = $null
$deadline = [DateTime]::UtcNow.AddSeconds(45)
do {
    try { $state = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json } catch { $state = $null }
    if ($state -and [DateTime]::Parse($state.observed_at_utc).ToUniversalTime() -ge $started -and $state.state -in @('ready', 'update_available')) { break }
    Start-Sleep -Milliseconds 400
} while ([DateTime]::UtcNow -lt $deadline)
$fresh = $state -and [DateTime]::Parse($state.observed_at_utc).ToUniversalTime() -ge $started
$result = [ordered]@{
    version = '1.0.4'; source_version = $sourceVersion; msi_sha256 = $ExpectedSha256
    configuration_encrypted_bytes_preserved = ($beforeHash -eq $afterHash)
    state = $service.State; start_mode = $service.StartMode; identity = $service.StartName
    fresh_cycle = [bool]$fresh
    runtime_state = $(if ($state) { $state.state } else { 'unavailable' })
    elapsed_seconds = [Math]::Round(([DateTime]::UtcNow - $started).TotalSeconds, 2)
    backend_verification_required = $true
}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDirectory 'verification.json') -Encoding UTF8
$result | ConvertTo-Json
Write-Host ('Evidencia local: ' + $outputDirectory)
if (-not $fresh -or $state.state -notin @('ready', 'update_available')) {
    throw 'Atualizacao instalada, mas ciclo real nao confirmado nesta espera. Preserve configuracao e informe o estado; nao parear novamente.'
}
