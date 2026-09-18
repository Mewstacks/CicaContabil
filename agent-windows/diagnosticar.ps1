[CmdletBinding()]
param(
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$dataRoot = Join-Path $env:ProgramData 'CICA\Agent'
$statusPath = Join-Path $dataRoot 'agent-status.json'
$servicePath = Join-Path $env:ProgramFiles 'CICA Agent\Service\Cica.Agent.Service.exe'
$configuratorPath = Join-Path $env:ProgramFiles 'CICA Agent\Configurator\Cica.Agent.Configurator.exe'

function Get-SystemOdbcCount {
    $path = 'SOFTWARE\ODBC\ODBC.INI\ODBC Data Sources'
    $count = 0
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, $view)
        try {
            $key = $base.OpenSubKey($path)
            try {
                if ($null -ne $key) { $count += @($key.GetValueNames()).Count }
            }
            finally { if ($null -ne $key) { $key.Dispose() } }
        }
        finally { $base.Dispose() }
    }
    return $count
}

function Test-SqlAnywhereDriver {
    $path = 'SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers'
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, $view)
        try {
            $key = $base.OpenSubKey($path)
            try {
                if ($null -ne $key -and @($key.GetValueNames() | Where-Object { $_ -match 'SQL Anywhere' }).Count -gt 0) {
                    return $true
                }
            }
            finally { if ($null -ne $key) { $key.Dispose() } }
        }
        finally { $base.Dispose() }
    }
    return $false
}

$service = Get-Service -Name 'CicaAgent' -ErrorAction SilentlyContinue
$status = $null
if (Test-Path -LiteralPath $statusPath) {
    try { $status = Get-Content -Raw -LiteralPath $statusPath | ConvertFrom-Json }
    catch { $status = [pscustomobject]@{ state = 'invalid_status_file'; detail = 'O arquivo de estado não contém JSON válido.' } }
}

$result = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    service_installed = $null -ne $service
    service_status = if ($null -ne $service) { $service.Status.ToString() } else { 'NotInstalled' }
    service_binary_present = Test-Path -LiteralPath $servicePath
    configurator_present = Test-Path -LiteralPath $configuratorPath
    configuration_present = Test-Path -LiteralPath (Join-Path $dataRoot 'agent.config')
    runtime_state = if ($null -ne $status) { [string]$status.state } else { 'not_available' }
    runtime_detail = if ($null -ne $status) { [string]$status.detail } else { 'O agente ainda não gravou estado local.' }
    runtime_observed_at_utc = if ($null -ne $status) { [string]$status.observed_at_utc } else { $null }
    system_odbc_dsn_count = Get-SystemOdbcCount
    sql_anywhere_driver_present = Test-SqlAnywhereDriver
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 3
}
else {
    $result.GetEnumerator() | ForEach-Object { '{0}: {1}' -f $_.Key, $_.Value }
}

if (-not $result.service_installed -or -not $result.service_binary_present -or -not $result.configurator_present) {
    exit 2
}
if ($result.runtime_state -in @('configuration_error', 'authorization_error', 'invalid_status_file')) {
    exit 3
}
