#requires -Version 5.1
<# CI ONLY. Never run on a customer's machine. Uses synthetic DPAPI configuration. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$BaselineMsi)
$ErrorActionPreference='Stop'
if($env:GITHUB_ACTIONS -ne 'true') { throw 'Ensaio exclusivo do CI descartável.' }
$config=Join-Path $env:ProgramData 'CICA\Agent\agent.config'
$exe=Join-Path $env:ProgramFiles 'CICA Agent\Service\Cica.Agent.Service.exe'
$statusFile=Join-Path $env:ProgramData 'CICA\Agent\agent-status.json'
if((Get-Service CicaAgent -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath $config)) { throw 'Ambiente já configurado; ensaio recusado.' }
$folder=Join-Path $PSScriptRoot 'artifacts\validation\upgrade'
[void][IO.Directory]::CreateDirectory($folder)
$target=Join-Path $PSScriptRoot 'artifacts\CicaAgent.msi'
function Install-Msi($path,$action,$logName) {
    $p=Start-Process msiexec.exe -ArgumentList @($action,('"'+$path+'"'),'/qn','/norestart','/l*v',('"'+(Join-Path $folder $logName)+'"')) -Wait -PassThru
    if($p.ExitCode -ne 0) { throw ('MSI test failed: '+$p.ExitCode) }
}
$installed=$false
$syntheticWritten=$false
try {
    Install-Msi (Resolve-Path $BaselineMsi).Path '/i' 'baseline-install.log'
    $installed=$true
    if((Get-Item $exe).VersionInfo.FileVersion -ne '1.0.5.0') { throw 'Baseline is not 1.0.5.' }
    Stop-Service CicaAgent
    Add-Type -AssemblyName System.Security
    $plain=[Text.Encoding]::UTF8.GetBytes((@{
        ServerUrl='http://127.0.0.1'; AgentId='synthetic-only'; SharedSecret='synthetic-only'
        CertificatePfxBase64=''; Dsn=$null; SqlAnywhereDriver=''; DatabaseUser=''
        DatabasePassword=''; WindowsArchiveRoot=$null; SourceSystem='dominio'
    } | ConvertTo-Json))
    $encrypted=[Security.Cryptography.ProtectedData]::Protect($plain,$null,[Security.Cryptography.DataProtectionScope]::LocalMachine)
    [IO.File]::WriteAllBytes($config,$encrypted)
    $syntheticWritten=$true
    $hash=(Get-FileHash $config).Hash
    Start-Service CicaAgent
    $targetHash=(Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedDiagnostic=$false
    try { & (Join-Path $PSScriptRoot 'upgrade-active-companies.ps1') -MsiPath $target -ExpectedSha256 $targetHash -TimeoutSeconds 15 }
    catch { $expectedDiagnostic=$_.Exception.Message.StartsWith('Atualização instalada, mas ciclo saudável') }
    if(-not $expectedDiagnostic) { throw 'Upgrade did not complete with expected synthetic diagnostic.' }
    if((Get-Item $exe).VersionInfo.FileVersion -ne '1.0.6.0' -or (Get-FileHash $config).Hash -ne $hash) { throw 'Version/configuration was not preserved.' }
    $service=Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
    if($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or $service.StartName -ne 'LocalSystem') { throw 'Unexpected service account or mode after upgrade.' }
    $state=Get-Content $statusFile -Raw | ConvertFrom-Json
    if($state.version -ne '1.0.6' -or $state.state -ne 'configuration_error' -or -not $state.detail.Contains('HTTPS')) { throw 'SYSTEM did not reopen the original DPAPI configuration.' }
    $start=[DateTimeOffset]::UtcNow
    Restart-Service CicaAgent
    $deadline=$start.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 400
        $state=Get-Content $statusFile -Raw | ConvertFrom-Json
    } while(([DateTimeOffset]$state.observed_at_utc) -lt $start -and [DateTimeOffset]::UtcNow -lt $deadline)
    if(([DateTimeOffset]$state.observed_at_utc) -lt $start -or $state.version -ne '1.0.6' -or (Get-FileHash $config).Hash -ne $hash) { throw 'Restart did not preserve the upgraded configuration.' }
    @{passed=$true;baseline_source='53b834b12318ed5177e4d736929ab58f2c31559a';from='1.0.5';to='1.0.6';encrypted_bytes_preserved=$true;system_dpapi_reopened=$true;restart_verified=$true;network_erp_used=$false;source_sha=$env:GITHUB_SHA} |
        ConvertTo-Json | Set-Content (Join-Path $folder 'upgrade-test.json') -Encoding UTF8
    Write-Host 'Upgrade 1.0.5 -> 1.0.6 preserved encrypted configuration, SYSTEM DPAPI and restart.'
} finally {
    if($syntheticWritten -and (Test-Path $config)) { Stop-Service CicaAgent -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $config }
    if($installed -or (Get-Service CicaAgent -ErrorAction SilentlyContinue)) {
        $uninstall=if((Test-Path $exe) -and (Get-Item $exe).VersionInfo.FileVersion -eq '1.0.6.0') { $target } else { (Resolve-Path $BaselineMsi).Path }
        Install-Msi $uninstall '/x' 'upgrade-uninstall.log'
    }
}
