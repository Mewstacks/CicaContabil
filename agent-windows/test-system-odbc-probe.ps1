# Disposable Windows CI only. Never run this test suite on a customer's server.
#requires -Version 5.1
#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$cicaProbe = Join-Path $PSScriptRoot 'testar-odbc-system.ps1'
$cicaEvidence = Join-Path $PSScriptRoot 'artifacts\validation\system-odbc-probe.json'
$cicaSyntheticPassword = 'synthetic-CI-only-ODBC-}'';pwd=ignored-2026'
$cicaSecurePassword = ConvertTo-SecureString $cicaSyntheticPassword -AsPlainText -Force
$cicaResult = $null
try {
    foreach ($cicaFile in @($cicaProbe, $PSCommandPath)) {
        $cicaTokens = $null
        $cicaErrors = $null
        [void][Management.Automation.Language.Parser]::ParseFile($cicaFile, [ref]$cicaTokens, [ref]$cicaErrors)
        if ($cicaErrors.Count -gt 0) { throw 'PowerShell parser rejected the diagnostic.' }
    }
    $cicaMissingDsn = 'CICA_CI_ABSENT_' + [guid]::NewGuid().ToString('N')
    $cicaOutput = & $cicaProbe -Dsn $cicaMissingDsn -DatabaseUser 'SYNTHETIC_CI' -DatabasePassword $cicaSecurePassword
    if (($cicaOutput | Out-String).Contains($cicaSyntheticPassword)) { throw 'Credential leaked into output.' }
    $cicaResult = ($cicaOutput | Out-String) | ConvertFrom-Json
    if (-not $cicaResult.executed_as_system -or -not $cicaResult.process_x64) { throw 'Test did not run under SYSTEM/x64.' }
    if ($cicaResult.odbc_connection_ok -or $cicaResult.minimal_select_ok -or $cicaResult.query_returned_row) { throw 'Missing DSN reported a successful ERP test.' }
    if ($cicaResult.error_code -ne 'odbc_failed' -or 'IM002' -notin $cicaResult.sql_states) { throw 'Expected bounded missing-DSN failure.' }
    $cicaRoot = Join-Path $env:ProgramData 'CICA\OdbcChecks'
    if (Test-Path -LiteralPath (Join-Path $cicaRoot $cicaResult.run_id)) { throw 'Temporary credential directory remains.' }
    if (Get-ScheduledTask -TaskName ('CICA-ODBC-TEST-' + $cicaResult.run_id) -ErrorAction SilentlyContinue) { throw 'Temporary SYSTEM task remains.' }
    $cicaSafeReport = Get-Content -LiteralPath $cicaResult.report_file -Raw
    if ($cicaSafeReport.Contains($cicaSyntheticPassword) -or $cicaSafeReport.Contains('password_protected')) { throw 'Report retained credential material.' }
    $cicaRules = (Get-Acl -LiteralPath $cicaResult.report_file).GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])
    if (@($cicaRules | Where-Object { $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Value -notin @('S-1-5-18', 'S-1-5-32-544') }).Count -gt 0) { throw 'Report ACL allows other users.' }
    $cicaHostPowerShell = Join-Path $env:windir 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $cicaRefusalInfo = [Diagnostics.ProcessStartInfo]::new($cicaHostPowerShell,
        ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $cicaProbe + '" -Worker -RunId ' + [guid]::NewGuid().ToString('N')))
    $cicaRefusalInfo.UseShellExecute = $false
    $cicaRefusalInfo.RedirectStandardOutput = $true
    $cicaRefusalInfo.RedirectStandardError = $true
    $cicaRefusalProcess = [Diagnostics.Process]::Start($cicaRefusalInfo)
    try {
        if (-not $cicaRefusalProcess.WaitForExit(30000)) { $cicaRefusalProcess.Kill(); throw 'Refusal test timed out.' }
        if ($cicaRefusalProcess.ExitCode -eq 0) { throw 'Interactive account was accepted as SYSTEM.' }
    } finally { $cicaRefusalProcess.Dispose() }
    $cicaReceipt = [ordered]@{
        passed = $true
        powershell = $PSVersionTable.PSVersion.ToString()
        windows = [Environment]::OSVersion.VersionString
        actual_system_task = $true
        x64 = $true
        private_input_read_and_deleted = $true
        synthetic_password_absent_output_report = $true
        missing_dsn_failed_without_erp_read = $true
        task_and_temporary_files_removed = $true
        report_acl_admin_system_only = $true
        non_system_worker_refused = $true
        real_client_odbc_tested = $false
    }
    [void][IO.Directory]::CreateDirectory((Split-Path -Parent $cicaEvidence))
    [IO.File]::WriteAllText($cicaEvidence, ($cicaReceipt | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    $cicaReceipt | ConvertTo-Json
}
finally {
    $cicaSecurePassword.Dispose()
    if ($null -ne $cicaResult -and (Test-Path -LiteralPath $cicaResult.report_file)) {
        Remove-Item -LiteralPath $cicaResult.report_file -Force
    }
}
