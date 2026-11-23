[CmdletBinding()]
param(
    [string]$MsiPath,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$scriptFile = $MyInvocation.MyCommand.Path
$scriptRoot = Split-Path -Parent $scriptFile
if (-not $MsiPath) { $MsiPath = Join-Path $scriptRoot 'CicaAgent.msi' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $scriptRoot 'validation' }
$os = Get-CimInstance Win32_OperatingSystem
if ($os.ProductType -ne 1 -or $os.Caption -notmatch 'Windows 11' `
    -or [int]$os.BuildNumber -lt 22000 -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Este ensaio exige Windows 11 cliente Intel/AMD x64.'
}
Add-Type -AssemblyName System.Security
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra PowerShell como administrador. Nenhuma politica de seguranca sera alterada.'
}
if (Get-Service -Name 'CicaAgent' -ErrorAction SilentlyContinue) {
    throw 'O PC ja tem CicaAgent; nenhuma instalacao existente sera alterada.'
}
$dataRoot = Join-Path $env:ProgramData 'CICA\Agent'
$configPath = Join-Path $dataRoot 'agent.config'
if (Test-Path -LiteralPath $dataRoot) { throw 'Pasta de dados preexistente: ensaio recusado.' }
if (Test-Path -LiteralPath (Join-Path $env:ProgramFiles 'CICA Agent')) {
    throw 'Pasta de instalacao preexistente: ensaio recusado.'
}
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
$testConfigHash = $null
$failure = $null
$gui = $null

function Assert-Check([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "Falha: $Name" }
    $checks.Add($Name)
    Write-Host "PASS: $Name"
}

function Invoke-Msi([string]$Action, [string]$LogName) {
    $logPath = Join-Path $OutputDirectory $LogName
    if ($Action -notin @('/i', '/fa')) { throw 'Este roteiro nao remove o agente do PC.' }
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

function Remove-SyntheticConfiguration {
    if (Test-Path -LiteralPath $configPath) {
        if (-not $testConfigHash -or (Get-FileHash -LiteralPath $configPath).Hash -ne $testConfigHash) {
            throw 'Configuracao alterada durante o ensaio; arquivo preservado e servico parado para revisao.'
        }
        Remove-Item -LiteralPath $configPath
    }
}

try {
    $timestamp = [DateTimeOffset]::UtcNow
    $roundtrip = @{ observed = $timestamp.ToString('o') } | ConvertTo-Json | ConvertFrom-Json
    $observed = [DateTimeOffset]$roundtrip.observed
    Assert-Check ([Math]::Abs(($observed - $timestamp).TotalMilliseconds) -lt 1) 'status timestamps preserve subsecond freshness after JSON parsing'
    $manifest = Get-Content -Raw -LiteralPath (Join-Path (Split-Path $MsiPath) 'release.json') | ConvertFrom-Json
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $MsiPath).Hash.ToLowerInvariant()
    $hashFile = (Get-Content -Raw -LiteralPath "$MsiPath.sha256").Trim().Split(' ')[0]
    Assert-Check ($hash -eq '0f2877a5872452506d94b770e51f8d95c03f9dec908da2af907ab0da54612393') 'original MSI bytes pinned before execution'
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

    $diagnostic = & "$PSHOME\powershell.exe" -NoProfile -File $diagnosticPath -AsJson | ConvertFrom-Json
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
    $stream = [IO.File]::Open($configPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $stream.Write($encrypted, 0, $encrypted.Length) }
    finally { $stream.Dispose() }
    $testConfigHash = (Get-FileHash -LiteralPath $configPath).Hash
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
    Remove-SyntheticConfiguration
    $testConfigWritten = $false
    $started = [DateTimeOffset]::UtcNow
    Start-Service -Name CicaAgent
    $state = Wait-AgentState 'awaiting_configuration' $started
    Assert-Check ($state.state -eq 'awaiting_configuration') 'restart recovers after configuration correction'
}
catch { $failure = $_.Exception.Message }
finally {
    if ($gui -and -not $gui.HasExited) { $gui.Kill() }
    if ($testConfigWritten) {
        try {
            Stop-Service CicaAgent -ErrorAction Stop
            Remove-SyntheticConfiguration
            $testConfigWritten = $false
            Start-Service CicaAgent
        }
        catch { $failure = 'Falha na restauracao segura: ' + $_.Exception.Message }
    }
    if ($installed -and -not $testConfigWritten) {
        try {
            $service = Get-Service CicaAgent
            $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
            Assert-Check (-not (Test-Path -LiteralPath $configPath)) 'agent left installed without ERP configuration'
        }
        catch { if (-not $failure) { $failure = $_.Exception.Message } }
    }
    [ordered]@{
        passed = -not [bool]$failure; failure = $failure; checks = @($checks.ToArray());
        test_script_sha256 = (Get-FileHash -LiteralPath $scriptFile).Hash.ToLowerInvariant();
        environment = @{ caption = $os.Caption; build = $os.BuildNumber; product_type = $os.ProductType; architecture = $env:PROCESSOR_ARCHITECTURE };
        agent_left_installed = $installed; uninstall_tested = $false;
        windows_version = [Environment]::OSVersion.VersionString;
        pairing_tested = $false; real_odbc_tested = $false;
        authenticode_status = (Get-AuthenticodeSignature -LiteralPath $MsiPath).Status.ToString();
        msi_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $MsiPath).Hash.ToLowerInvariant();
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDirectory 'windows-11-pc-test.json')
}
if ($failure) { throw $failure }
