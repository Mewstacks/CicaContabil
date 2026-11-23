[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$MsiPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedSha256,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [ValidateSet("1.0.0.0", "1.0.1.0", "1.0.2.0")][string]$SourceVersion = "1.0.1.0",
    [ValidateSet("1.0.1", "1.0.2", "1.0.3")][string]$TargetVersion = "1.0.3"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute como administrador, sem alterar a politica de execucao.'
}
$os = Get-CimInstance Win32_OperatingSystem
if ($os.ProductType -ne 1 -or [int]$os.BuildNumber -lt 22000 -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Este ensaio exige PC de teste Windows 11 AMD64.'
}
$servicePath = Join-Path $env:ProgramFiles 'CICA Agent\Service\Cica.Agent.Service.exe'
$configPath = Join-Path $env:ProgramData 'CICA\Agent\agent.config'
if (Test-Path -LiteralPath $configPath) {
    throw 'Configuracao existente: atualizacao de teste recusada; nada foi sobrescrito.'
}
$service = Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
if (-not $service -or $service.PathName.Trim('"') -ne $servicePath) {
    throw 'Instalacao CICA esperada nao encontrada; ensaio recusado.'
}
$oldVersion = (Get-Item -LiteralPath $servicePath).VersionInfo.FileVersion
if ($oldVersion -ne $SourceVersion) { throw "A origem precisa ser exatamente CICA Agent $SourceVersion." }
if ([version]($TargetVersion + ".0") -le [version]$SourceVersion) { throw "O alvo deve ser posterior a origem." }
if (Get-Process -Name 'Cica.Agent.Configurator' -ErrorAction SilentlyContinue) {
    throw 'Feche o configurador CICA antes de atualizar; os campos abertos foram preservados.'
}
$MsiPath = (Resolve-Path -LiteralPath $MsiPath).Path
$observedHash = (Get-FileHash -LiteralPath $MsiPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($observedHash -ne $ExpectedSha256) { throw 'Hash do MSI diferente do artefato conferido.' }
$manifestPath = Join-Path (Split-Path -Parent $MsiPath) 'release.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.version -ne $TargetVersion -or $manifest.sha256 -ne $ExpectedSha256) {
    throw 'Manifesto diferente da versao/hash aprovados para este ensaio.'
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
$checks = New-Object 'System.Collections.Generic.List[string]'
$failure = $null
$exitCode = $null
try {
    $checks.Add("original_" + $SourceVersion + "_unconfigured_and_pinned_" + $TargetVersion)
    if (Test-Path -LiteralPath $configPath) { throw 'Configuracao criada durante o preflight; interrompido.' }
    $upgrade = Start-Process msiexec.exe -ArgumentList @(
        '/i', ('"' + $MsiPath + '"'), '/qn', '/norestart', '/l*v',
        ('"' + (Join-Path $OutputDirectory 'upgrade.log') + '"')
    ) -Wait -PassThru
    $exitCode = $upgrade.ExitCode
    if ($exitCode -ne 0) { throw "A atualizacao nao terminou sem reinicio: codigo $exitCode." }
    $checks.Add('msiexec_upgrade_exit_0')
    if ((Get-Item -LiteralPath $servicePath).VersionInfo.FileVersion -ne ($TargetVersion + ".0")) {
        throw "Versao instalada nao confere com $TargetVersion."
    }
    $checks.Add("installed_service_" + $TargetVersion)
    $service = Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
    if ($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or $service.StartName -ne 'LocalSystem') {
        throw 'Servico nao esta automatico/LocalSystem/Running apos a atualizacao.'
    }
    $checks.Add('service_running_automatic_localsystem')
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    $statusPath = Join-Path $env:ProgramData 'CICA\Agent\agent-status.json'
    $state = $null
    do {
        try { $state = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json }
        catch { $state = $null }
        if ($state -and $state.state -eq 'awaiting_configuration') { break }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    if (-not $state -or $state.state -ne 'awaiting_configuration') {
        throw 'Servico nao confirmou espera sem configuracao.'
    }
    if (Test-Path -LiteralPath $configPath) { throw 'Configuracao inesperada preservada; conferir antes de prosseguir.' }
    $checks.Add('awaiting_configuration_without_erp_or_pairing')
}
catch { $failure = $_.Exception.Message }
$report = [ordered]@{
    passed = ($null -eq $failure)
    failure = $failure
    source_version = $oldVersion
    target_version = ($TargetVersion + ".0")
    msi_sha256 = $observedHash
    msi_exit_code = $exitCode
    checks = @($checks.ToArray())
    pairing_tested = $false
    service_odbc_tested = $false
    gui_odbc_tested = $false
    agent_left_installed = $true
    uninstall_tested = $false
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'windows-11-upgrade.json') -Encoding UTF8
$report | ConvertTo-Json -Depth 5
if ($failure) { throw $failure }
