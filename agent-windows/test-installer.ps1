[CmdletBinding()]
param(
    [string]$MsiPath = (Join-Path $PSScriptRoot 'artifacts\CicaAgent.msi'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'artifacts\validation')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' `
    -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Este ensaio instala/remove serviços. Execute somente em runner Windows descartável do GitHub.'
}
if (Get-Service -Name 'CicaAgent' -ErrorAction SilentlyContinue) {
    throw 'O runner já tem CicaAgent; nenhuma instalação existente será alterada.'
}
$dataRoot = Join-Path $env:ProgramData 'CICA\Agent'
$configPath = Join-Path $dataRoot 'agent.config'
if (Test-Path -LiteralPath $configPath) { throw 'Configuração existente: ensaio recusado.' }
$MsiPath = (Resolve-Path -LiteralPath $MsiPath).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
$installRoot = Join-Path $env:ProgramFiles 'CICA Agent'
$servicePath = Join-Path $installRoot 'Service\Cica.Agent.Service.exe'
$bridgePath = Join-Path $installRoot 'Service\odbc-bridge\Cica.Agent.OdbcBridge.exe'
$guiPath = Join-Path $installRoot 'Configurator\Cica.Agent.Configurator.exe'
$diagnosticPath = Join-Path $installRoot 'Configurator\diagnosticar.ps1'
$checks = [System.Collections.Generic.List[string]]::new()
$installed = $false
$testConfigWritten = $false
$failure = $null
$gui = $null

function Assert-Check([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "Falha: $Name" }
    $checks.Add($Name)
    Write-Host "PASS: $Name"
}

function Invoke-Msi([string]$Action, [string]$LogName) {
    $logPath = Join-Path $OutputDirectory $LogName
    $process = Start-Process msiexec.exe -ArgumentList @(
        $Action, "`"$MsiPath`"", '/qn', '/norestart', '/l*v', "`"$logPath`""
    ) -Wait -PassThru
    Assert-Check ($process.ExitCode -in @(0, 3010)) "msiexec $Action exit $($process.ExitCode)"
}

function Wait-AgentState([string]$Expected, [DateTimeOffset]$After) {
    $statusPath = Join-Path $dataRoot 'agent-status.json'
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $statusPath) {
            try {
                $state = Get-Content -Raw -LiteralPath $statusPath | ConvertFrom-Json
                # PowerShell may deserialize ISO dates as DateTime. Parse(string)
                # would stringify that value using the locale and lose fractions.
                $observed = [DateTimeOffset]$state.observed_at_utc
                if ($state.state -eq $Expected `
                    -and $observed -ge $After) {
                    return $state
                }
            }
            catch { Write-Verbose 'Aguardando gravação atômica do estado.' }
        }
        Start-Sleep -Milliseconds 400
    }
    if (Test-Path -LiteralPath $statusPath) {
        Copy-Item -LiteralPath $statusPath -Destination (Join-Path $OutputDirectory "timeout-$Expected.json")
    }
    throw "O serviço não informou o estado $Expected em 45 segundos."
}

function Get-PeMachine([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $reader = [IO.BinaryReader]::new($stream)
    try {
        $stream.Position = 0x3c
        $header = $reader.ReadInt32()
        $stream.Position = $header
        if ($reader.ReadUInt32() -ne 0x00004550) { throw 'Executável PE inválido.' }
        return $reader.ReadUInt16()
    }
    finally { $reader.Dispose(); $stream.Dispose() }
}

try {
    $timestamp = [DateTimeOffset]::UtcNow
    $roundtrip = @{ observed = $timestamp.ToString('o') } | ConvertTo-Json | ConvertFrom-Json
    $observed = [DateTimeOffset]$roundtrip.observed
    Assert-Check ([Math]::Abs(($observed - $timestamp).TotalMilliseconds) -lt 1) 'status timestamps preserve subsecond freshness after JSON parsing'
    $manifest = Get-Content -Raw -LiteralPath (Join-Path (Split-Path $MsiPath) 'release.json') | ConvertFrom-Json
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $MsiPath).Hash.ToLowerInvariant()
    $hashFile = (Get-Content -Raw -LiteralPath "$MsiPath.sha256").Trim().Split(' ')[0]
    Assert-Check ($manifest.sha256 -eq $hash -and $hashFile -eq $hash) 'MSI/hash/manifest agree'
    $started = [DateTimeOffset]::UtcNow
    Invoke-Msi '/i' 'install.log'
    $installed = $true
    $service = Get-Service -Name CicaAgent
    $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
    $details = Get-CimInstance Win32_Service -Filter "Name='CicaAgent'"
    Assert-Check ($details.StartMode -eq 'Auto' -and $details.StartName -eq 'LocalSystem') 'automatic LocalSystem service'
    foreach ($path in @($servicePath, $bridgePath, $guiPath, $diagnosticPath)) {
        Assert-Check (Test-Path -LiteralPath $path) "installed $([IO.Path]::GetFileName($path))"
    }
    Assert-Check ((Get-PeMachine $servicePath) -eq 0x8664) 'service is x64'
    Assert-Check ((Get-PeMachine $guiPath) -eq 0x8664) 'configurator is x64'
    Assert-Check ((Get-PeMachine $bridgePath) -eq 0x014c) 'ODBC bridge is x86'
    $state = Wait-AgentState 'awaiting_configuration' $started
    Assert-Check (-not (Test-Path -LiteralPath $configPath)) 'unconfigured service creates no ERP configuration'

    $acl = Get-Acl -LiteralPath $dataRoot
    $unsafe = @($acl.Access | Where-Object {
        $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Translate(
            [System.Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18', 'S-1-5-32-544')
    })
    Assert-Check ($acl.AreAccessRulesProtected -and $unsafe.Count -eq 0) 'configuration directory restricted to SYSTEM/Administrators'

    $gui = Start-Process -FilePath $guiPath -PassThru
    Assert-Check ($gui.WaitForInputIdle(15000)) 'configurator initializes Windows message loop'
    Start-Sleep -Seconds 2
    $gui.Refresh()
    Assert-Check (-not $gui.HasExited -and $gui.MainWindowTitle -eq 'Configurar agente CICA') 'configurator opens without crash'
    $gui.CloseMainWindow() | Out-Null
    Assert-Check ($gui.WaitForExit(10000)) 'configurator closes normally'

    $bridge = [Diagnostics.Process]::new()
    $bridge.StartInfo = [Diagnostics.ProcessStartInfo]::new($bridgePath)
    $bridge.StartInfo.UseShellExecute = $false
    $bridge.StartInfo.RedirectStandardInput = $true
    $bridge.StartInfo.RedirectStandardOutput = $true
    $bridge.StartInfo.RedirectStandardError = $true
    $bridge.Start() | Out-Null
    $bridge.StandardInput.WriteLine('not-json')
    $bridge.StandardInput.Close()
    $bridgeError = $bridge.StandardError.ReadToEnd()
    $bridge.WaitForExit(10000) | Out-Null
    Assert-Check ($bridge.HasExited -and $bridge.ExitCode -eq 1 -and $bridgeError.StartsWith('JsonException')) 'x86 bridge executes and rejects invalid input before ODBC'
    $bridge.Dispose()

    $diagnostic = & pwsh -NoProfile -File $diagnosticPath -AsJson | ConvertFrom-Json
    Assert-Check ($LASTEXITCODE -eq 0 -and $diagnostic.runtime_state -eq 'awaiting_configuration') 'installed diagnostic succeeds without DSN or pairing'
    $diagnostic | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutputDirectory 'diagnostic.json')

    # Synthetic configuration deliberately fails HTTPS validation before any network/ERP access.
    Stop-Service -Name CicaAgent
    $plain = [Text.Encoding]::UTF8.GetBytes((@{
        ServerUrl = 'http://127.0.0.1'; AgentId = 'synthetic-only'; SharedSecret = 'synthetic-only';
        CertificatePfxBase64 = ''; Dsn = $null; SqlAnywhereDriver = ''; DatabaseUser = '';
        DatabasePassword = ''; WindowsArchiveRoot = $null; SourceSystem = 'dominio'
    } | ConvertTo-Json))
    $encrypted = [Security.Cryptography.ProtectedData]::Protect(
        $plain, $null, [Security.Cryptography.DataProtectionScope]::LocalMachine)
    [IO.File]::WriteAllBytes($configPath, $encrypted)
    $testConfigWritten = $true
    [Array]::Clear($plain, 0, $plain.Length)
    $started = [DateTimeOffset]::UtcNow
    Start-Service -Name CicaAgent
    $state = Wait-AgentState 'configuration_error' $started
    Assert-Check ($state.detail.Contains('HTTPS')) 'LocalSystem decrypts DPAPI and rejects insecure server configuration'
    $beforeRepair = (Get-FileHash $configPath).Hash
    Invoke-Msi '/fa' 'repair.log'
    Assert-Check ((Get-FileHash $configPath).Hash -eq $beforeRepair) 'MSI repair preserves existing encrypted configuration'
    Stop-Service -Name CicaAgent
    Remove-Item -LiteralPath $configPath
    $testConfigWritten = $false
    $started = [DateTimeOffset]::UtcNow
    Start-Service -Name CicaAgent
    $state = Wait-AgentState 'awaiting_configuration' $started
    Assert-Check ($state.state -eq 'awaiting_configuration') 'restart recovers after configuration correction'
}
catch { $failure = $_.Exception.Message }
finally {
    if ($gui -and -not $gui.HasExited) { $gui.Kill() }
    if ($testConfigWritten -and (Test-Path -LiteralPath $configPath)) {
        Stop-Service CicaAgent -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $configPath
    }
    if ($installed -or (Get-Service CicaAgent -ErrorAction SilentlyContinue)) {
        try {
            Invoke-Msi '/x' 'uninstall.log'
            Assert-Check ($null -eq (Get-Service CicaAgent -ErrorAction SilentlyContinue)) 'uninstall removes service'
            Assert-Check (-not (Test-Path -LiteralPath $servicePath)) 'uninstall removes service executable'
        }
        catch { if (-not $failure) { $failure = $_.Exception.Message } }
    }
    [ordered]@{
        passed = -not [bool]$failure; failure = $failure; checks = @($checks.ToArray());
        source_sha = $env:GITHUB_SHA; run_id = $env:GITHUB_RUN_ID;
        windows_version = [Environment]::OSVersion.VersionString;
        pairing_tested = $false; real_odbc_tested = $false;
        authenticode_status = (Get-AuthenticodeSignature -LiteralPath $MsiPath).Status.ToString();
        msi_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $MsiPath).Hash.ToLowerInvariant();
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDirectory 'installer-test.json')
}
if ($failure) { throw $failure }
