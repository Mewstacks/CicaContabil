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
    if((Get-Item $exe).VersionInfo.FileVersion -ne '1.0.10.0') { throw 'Baseline is not 1.0.10.' }
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
    try { & (Join-Path $PSScriptRoot 'upgrade-ledger-self-service.ps1') -MsiPath $target -ExpectedSha256 $targetHash -TimeoutSeconds 15 }
    catch { $expectedDiagnostic=$_.Exception.Message.StartsWith('Atualização instalada, mas ciclo saudável') }
    if(-not $expectedDiagnostic) { throw 'Upgrade did not complete with expected synthetic diagnostic.' }
    if((Get-Item $exe).VersionInfo.FileVersion -ne '1.0.11.0' -or (Get-FileHash $config).Hash -ne $hash) { throw 'Version/configuration was not preserved.' }
    $service=Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
    if($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or $service.StartName -ne 'LocalSystem') { throw 'Unexpected service account or mode after upgrade.' }
    $state=Get-Content $statusFile -Raw | ConvertFrom-Json
    if($state.version -ne '1.0.11' -or $state.state -ne 'configuration_error' -or -not $state.detail.Contains('HTTPS')) { throw 'SYSTEM did not reopen the original DPAPI configuration.' }
    $start=[DateTimeOffset]::UtcNow
    Restart-Service CicaAgent
    $deadline=$start.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 400
        $state=Get-Content $statusFile -Raw | ConvertFrom-Json
    } while(([DateTimeOffset]$state.observed_at_utc) -lt $start -and [DateTimeOffset]::UtcNow -lt $deadline)
    if(([DateTimeOffset]$state.observed_at_utc) -lt $start -or $state.version -ne '1.0.11' -or (Get-FileHash $config).Hash -ne $hash) { throw 'Restart did not preserve the upgraded configuration.' }
    # Exercise the updater decision with a synthetic fresh status, independently of
    # the real SYSTEM/DPAPI proof above. No backend or ERP success is claimed here.
    function Get-Content {
        [CmdletBinding()]
        param([string]$LiteralPath,[switch]$Raw)
        if($LiteralPath -eq $statusFile) {
            return (@{version='1.0.11';state='source_review_required';observed_at_utc=[DateTimeOffset]::UtcNow.ToString('O')} | ConvertTo-Json)
        }
        Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw:$Raw
    }
    try {
        $reviewResult = & (Join-Path $PSScriptRoot 'upgrade-ledger-self-service.ps1') -MsiPath $target -ExpectedSha256 $targetHash -TimeoutSeconds 3
        $reviewReport = $reviewResult | ConvertFrom-Json
        if(-not $reviewReport.source_review_required -or -not $reviewReport.fresh_status -or -not $reviewReport.configuration_encrypted_bytes_preserved -or -not $reviewReport.backend_verification_required) {
            throw 'A healthy service with a source requiring review must preserve that pending review.'
        }
    } finally {
        Remove-Item Function:\Get-Content
    }
    @{passed=$true;baseline_source='57bcfe26065b800336ccb23e90ad0c2d0ed3b9b5';from='1.0.10';to='1.0.11';encrypted_bytes_preserved=$true;system_dpapi_reopened=$true;restart_verified=$true;source_review_required_handling_tested=$true;source_review_test_synthetic=$true;network_erp_used=$false;source_sha=$env:GITHUB_SHA} |
        ConvertTo-Json | Set-Content (Join-Path $folder 'upgrade-test.json') -Encoding UTF8
    Write-Host 'Upgrade 1.0.10 -> 1.0.11 preserved encrypted configuration, SYSTEM DPAPI and restart.'
} finally {
    if($syntheticWritten -and (Test-Path $config)) { Stop-Service CicaAgent -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $config }
    if($installed -or (Get-Service CicaAgent -ErrorAction SilentlyContinue)) {
        $uninstall=if((Test-Path $exe) -and (Get-Item $exe).VersionInfo.FileVersion -eq '1.0.11.0') { $target } else { (Resolve-Path $BaselineMsi).Path }
        Install-Msi $uninstall '/x' 'upgrade-uninstall.log'
    }
}
