#requires -Version 5.1
<# Customer-safe 1.0.5 -> 1.0.6 update. Never decrypt or print the agent configuration. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$MsiPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedSha256,
    [ValidateRange(3,300)][int]$TimeoutSeconds = 90
)
$ErrorActionPreference = 'Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if(-not [Environment]::Is64BitProcess -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Use Windows PowerShell x64 como administrador.' }
$exe=Join-Path $env:ProgramFiles 'CICA Agent\Service\Cica.Agent.Service.exe'
$configuration=Join-Path $env:ProgramData 'CICA\Agent\agent.config'
$statusFile=Join-Path $env:ProgramData 'CICA\Agent\agent-status.json'
if(-not (Test-Path -LiteralPath $exe) -or -not (Test-Path -LiteralPath $configuration)) { throw 'Agente configurado não encontrado; nada alterado.' }
$installedService=Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
if(-not $installedService -or $installedService.PathName.Trim('"') -ne $exe -or $installedService.StartName -ne 'LocalSystem') { throw 'Serviço esperado não encontrado; nada alterado.' }
if(Get-Process -Name 'Cica.Agent.Configurator' -ErrorAction SilentlyContinue) { throw 'Feche o configurador antes de atualizar.' }
$sourceVersion=(Get-Item -LiteralPath $exe).VersionInfo.FileVersion
if($sourceVersion -notin @('1.0.5.0','1.0.6.0')) { throw 'Versão de origem inesperada; nada alterado.' }
$MsiPath=(Resolve-Path -LiteralPath $MsiPath).Path
if((Get-FileHash -LiteralPath $MsiPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSha256) { throw 'SHA-256 do MSI não confere; nada alterado.' }
$manifest=Get-Content -LiteralPath (Join-Path (Split-Path $MsiPath) 'release.json') -Raw | ConvertFrom-Json
if($manifest.version -ne '1.0.6' -or $manifest.sha256 -ne $ExpectedSha256) { throw 'Manifesto do MSI 1.0.6 não confere; nada alterado.' }
$before=(Get-FileHash -LiteralPath $configuration -Algorithm SHA256).Hash
$output=Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Upgrade-1.0.6-' + [Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($output)
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
foreach($sid in @($identity.User,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
}
Set-Acl -LiteralPath $output -AclObject $acl
$started=[DateTimeOffset]::UtcNow
$msiExit=0
if($sourceVersion -eq '1.0.5.0') {
    $install=Start-Process msiexec.exe -ArgumentList @('/i',('"'+$MsiPath+'"'),'/qn','/norestart','/l*v',('"'+(Join-Path $output 'upgrade.log')+'"')) -Wait -PassThru
    $msiExit=$install.ExitCode
    if($msiExit -notin @(0,3010)) { throw ('Atualização MSI não concluída. Código: '+$msiExit+'. Preserve configuração e não refaça pareamento.') }
}
if((Get-Item -LiteralPath $exe).VersionInfo.FileVersion -ne '1.0.6.0') { throw 'Binário 1.0.6 não confirmado; preserve os arquivos para análise.' }
$after=(Get-FileHash -LiteralPath $configuration -Algorithm SHA256).Hash
if($after -ne $before) { throw 'Bytes protegidos da configuração mudaram; preserve para análise, sem sobrescrever ou parear novamente.' }
$state=$null
$fresh=$false
$deadline=[DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
do {
    try {
        $state=Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
        $fresh=$state.version -eq '1.0.6' -and [DateTimeOffset]::Parse($state.observed_at_utc) -ge $started
    } catch { $fresh=$false }
    if($fresh -and $state.state -in @('ready','update_available')) { break }
    Start-Sleep -Milliseconds 400
} while([DateTimeOffset]::UtcNow -lt $deadline)
$service=Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
$healthy=$service.State -eq 'Running' -and $service.StartMode -eq 'Auto' -and $service.StartName -eq 'LocalSystem'
$result=[ordered]@{
    source_version=$sourceVersion; installed_version='1.0.6'; msi_sha256=$ExpectedSha256
    configuration_encrypted_bytes_preserved=($before -eq $after)
    service_state=$service.State; start_mode=$service.StartMode; service_account=$service.StartName
    runtime_state=$(if($state){$state.state}else{'unavailable'}); fresh_status=[bool]$fresh
    observed_at_utc=$(if($state){$state.observed_at_utc}else{$null})
    msi_exit_code=$msiExit; reboot_required=($msiExit -eq 3010); backend_verification_required=$true
}
$json=$result | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $output 'verification.json'),$json,[Text.UTF8Encoding]::new($false))
Write-Output $json
Write-Host ('Relatório privado: '+$output)
if(-not $healthy -or -not $fresh -or $state.state -notin @('ready','update_available') -or $msiExit -eq 3010) {
    throw 'Atualização instalada, mas ciclo saudável ainda não comprovado. Preserve configuração, não reinstale nem refaça pareamento; informe o JSON seguro.'
}
