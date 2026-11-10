#requires -Version 5.1
#requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$Dsn = 'CICA_CONTAD',
    [string]$DatabaseUser = 'EXTERNO',
    [Security.SecureString]$DatabasePassword,
    [switch]$Worker,
    [guid]$RunId = [guid]::Empty
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($PSVersionTable.PSEdition -ne 'Desktop' -or -not [Environment]::Is64BitProcess) {
    throw 'Execute no Windows PowerShell 5.1 de 64 bits, como administrador.'
}
Add-Type -AssemblyName System.Security
Add-Type -AssemblyName System.Data
$cicaProbeRoot = Join-Path $env:ProgramData 'CICA\OdbcChecks'
$cicaAgentRoot = Join-Path $env:ProgramData 'CICA\Agent'

function Get-CicaPrivateAcl([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    if ((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint) { return $false }
    $cicaRules = (Get-Acl -LiteralPath $Path).GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])
    $cicaAllowed = @($cicaRules | Where-Object { $_.AccessControlType -eq 'Allow' })
    return ($cicaAllowed.Count -ge 2 -and
        @($cicaAllowed | Where-Object { $_.IdentityReference.Value -notin @('S-1-5-18', 'S-1-5-32-544') }).Count -eq 0 -and
        @($cicaAllowed | Where-Object { $_.IdentityReference.Value -eq 'S-1-5-18' }).Count -gt 0 -and
        @($cicaAllowed | Where-Object { $_.IdentityReference.Value -eq 'S-1-5-32-544' }).Count -gt 0)
}

function New-CicaPrivateDirectory([string]$Path) {
    $cicaSecurity = [Security.AccessControl.DirectorySecurity]::new()
    $cicaSecurity.SetAccessRuleProtection($true, $false)
    foreach ($cicaSid in @('S-1-5-18', 'S-1-5-32-544')) {
        $cicaRule = [Security.AccessControl.FileSystemAccessRule]::new(
            [Security.Principal.SecurityIdentifier]::new($cicaSid),
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow)
        $cicaSecurity.AddAccessRule($cicaRule)
    }
    [void][IO.Directory]::CreateDirectory($Path, $cicaSecurity)
    if (-not (Get-CicaPrivateAcl $Path)) { throw 'Pasta de teste sem ACL privada; nada foi enviado.' }
}

function Invoke-CicaSystemProbe {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') {
        throw 'O processo de teste precisa executar como SYSTEM.'
    }
    if ($RunId -eq [guid]::Empty) { throw 'Identificador de teste ausente.' }
    $cicaWork = Join-Path $cicaProbeRoot ($RunId.ToString('N'))
    if ($PSScriptRoot -ne $cicaWork -or -not (Get-CicaPrivateAcl $cicaWork)) {
        throw 'Origem do teste ou ACL inválida.'
    }
    $cicaInputPath = Join-Path $cicaWork 'input.json'
    $cicaResultPath = Join-Path $cicaWork 'result.json'
    $cicaPlain = $null
    $cicaConnection = $null
    $cicaCommand = $null
    $cicaReader = $null
    $cicaReport = [ordered]@{
        probe_version = '1.0.0'
        run_id = $RunId.ToString('N')
        executed_as_system = $true
        execution_sid = 'S-1-5-18'
        process_x64 = [Environment]::Is64BitProcess
        odbc_connection_ok = $false
        minimal_select_ok = $false
        query_returned_row = $false
        error_code = $null
        sql_states = @()
        native_error_codes = @()
        agent_config_acl_private = (Get-CicaPrivateAcl (Join-Path $cicaAgentRoot 'agent.config'))
        agent_version = $null
        agent_state = $null
        agent_observed_at_utc = $null
        observed_at_utc = [DateTime]::UtcNow.ToString('O')
    }
    try {
        $cicaRequest = Get-Content -LiteralPath $cicaInputPath -Raw | ConvertFrom-Json
        $cicaProtected = [Convert]::FromBase64String($cicaRequest.password_protected)
        $cicaPlain = [Security.Cryptography.ProtectedData]::Unprotect(
            $cicaProtected, $RunId.ToByteArray(), [Security.Cryptography.DataProtectionScope]::LocalMachine)
        $cicaBuilder = [Data.Odbc.OdbcConnectionStringBuilder]::new()
        $cicaBuilder.Dsn = [string]$cicaRequest.dsn
        $cicaBuilder['UID'] = [string]$cicaRequest.database_user
        $cicaBuilder['PWD'] = [Text.Encoding]::UTF8.GetString($cicaPlain)
        $cicaConnection = [Data.Odbc.OdbcConnection]::new($cicaBuilder.ConnectionString)
        $cicaConnection.Open()
        $cicaReport.odbc_connection_ok = $true
        $cicaCommand = $cicaConnection.CreateCommand()
        # Same bounded, read-only test as Configurator. Never return ERP values.
        $cicaCommand.CommandText = 'SELECT TOP 1 codi_emp FROM bethadba.geempre'
        $cicaCommand.CommandTimeout = 15
        $cicaReader = $cicaCommand.ExecuteReader([Data.CommandBehavior]::SingleRow)
        $cicaReport.query_returned_row = $cicaReader.Read()
        $cicaReport.minimal_select_ok = $true
    }
    catch {
        $cicaException = $_.Exception
        while ($null -ne $cicaException.InnerException) { $cicaException = $cicaException.InnerException }
        $cicaReport.error_code = 'probe_failed'
        if ($cicaException -is [Data.Odbc.OdbcException]) {
            $cicaReport.error_code = 'odbc_failed'
            $cicaReport.sql_states = @($cicaException.Errors | ForEach-Object { $_.SQLState } | Select-Object -Unique)
            $cicaReport.native_error_codes = @($cicaException.Errors | ForEach-Object { $_.NativeError } | Select-Object -Unique)
        }
        # Exception.Message/connection strings may contain credentials. Never emit them.
    }
    finally {
        if ($null -ne $cicaReader) { $cicaReader.Dispose() }
        if ($null -ne $cicaCommand) { $cicaCommand.Dispose() }
        if ($null -ne $cicaConnection) { $cicaConnection.Dispose() }
        if ($null -ne $cicaPlain) { [Array]::Clear($cicaPlain, 0, $cicaPlain.Length) }
        Remove-Item -LiteralPath $cicaInputPath -Force -ErrorAction SilentlyContinue
    }
    $cicaStatusPath = Join-Path $cicaAgentRoot 'agent-status.json'
    if (Test-Path -LiteralPath $cicaStatusPath) {
        try {
            $cicaStatus = Get-Content -LiteralPath $cicaStatusPath -Raw | ConvertFrom-Json
            $cicaReport.agent_version = [string]$cicaStatus.version
            $cicaReport.agent_state = [string]$cicaStatus.state
            $cicaReport.agent_observed_at_utc = [string]$cicaStatus.observed_at_utc
        } catch { $cicaReport.error_code = 'agent_status_unreadable' }
    }
    [IO.File]::WriteAllText(($cicaResultPath + '.partial'), ($cicaReport | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move(($cicaResultPath + '.partial'), $cicaResultPath)
}

if ($Worker) { Invoke-CicaSystemProbe; return }
if ([string]::IsNullOrWhiteSpace($Dsn) -or [string]::IsNullOrWhiteSpace($DatabaseUser)) {
    throw 'DSN e usuário explícito são obrigatórios.'
}
New-CicaPrivateDirectory $cicaProbeRoot
$cicaRun = [guid]::NewGuid()
$cicaWorkDirectory = Join-Path $cicaProbeRoot ($cicaRun.ToString('N'))
if (Test-Path -LiteralPath $cicaWorkDirectory) { throw 'Pasta já existe; nenhum teste iniciado.' }
New-CicaPrivateDirectory $cicaWorkDirectory
$cicaTaskName = 'CICA-ODBC-TEST-' + $cicaRun.ToString('N')
$cicaTaskRegistered = $false
$cicaPlainBytes = $null
$cicaPasswordPointer = [IntPtr]::Zero
$cicaResult = $null
$cicaOwnPassword = $null -eq $DatabasePassword
try {
    if ($null -eq $DatabasePassword) {
        $DatabasePassword = Read-Host 'Senha do banco (somente neste Windows; entrada oculta)' -AsSecureString
    }
    if ($DatabasePassword.Length -eq 0) { throw 'Senha vazia; teste não iniciado.' }
    $cicaPasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($DatabasePassword)
    $cicaPlainBytes = [Text.Encoding]::UTF8.GetBytes([Runtime.InteropServices.Marshal]::PtrToStringBSTR($cicaPasswordPointer))
    $cicaEncrypted = [Security.Cryptography.ProtectedData]::Protect(
        $cicaPlainBytes, $cicaRun.ToByteArray(), [Security.Cryptography.DataProtectionScope]::LocalMachine)
    $cicaRequest = @{
        dsn = $Dsn
        database_user = $DatabaseUser
        password_protected = [Convert]::ToBase64String($cicaEncrypted)
    }
    $cicaInput = Join-Path $cicaWorkDirectory 'input.json'
    [IO.File]::WriteAllText($cicaInput, ($cicaRequest | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    $cicaWorkerScript = Join-Path $cicaWorkDirectory 'worker.ps1'
    Copy-Item -LiteralPath $PSCommandPath -Destination $cicaWorkerScript
    $cicaPowerShell = Join-Path $env:windir 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $cicaArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $cicaWorkerScript + '" -Worker -RunId ' + $cicaRun.ToString('N')
    $cicaAction = New-ScheduledTaskAction -Execute $cicaPowerShell -Argument $cicaArguments
    $cicaPrincipal = New-ScheduledTaskPrincipal -UserId 'S-1-5-18' -LogonType ServiceAccount -RunLevel Highest
    $cicaSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 90)
    [void](Register-ScheduledTask -TaskName $cicaTaskName -Action $cicaAction -Principal $cicaPrincipal -Settings $cicaSettings)
    $cicaTaskRegistered = $true
    Start-ScheduledTask -TaskName $cicaTaskName
    $cicaDeadline = [DateTime]::UtcNow.AddSeconds(100)
    $cicaResultFile = Join-Path $cicaWorkDirectory 'result.json'
    while (-not (Test-Path -LiteralPath $cicaResultFile) -and [DateTime]::UtcNow -lt $cicaDeadline) {
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-Path -LiteralPath $cicaResultFile)) { throw 'Teste não retornou no prazo; tarefa e credencial serão removidas.' }
    $cicaResult = Get-Content -LiteralPath $cicaResultFile -Raw | ConvertFrom-Json
    if ($cicaResult.run_id -ne $cicaRun.ToString('N') -or -not $cicaResult.executed_as_system) {
        throw 'Identidade do resultado não confere.'
    }
    $cicaFinalFile = Join-Path $cicaProbeRoot ('result-' + $cicaRun.ToString('N') + '.json')
    $cicaResult | Add-Member -NotePropertyName report_file -NotePropertyValue $cicaFinalFile
}
finally {
    if ($cicaTaskRegistered) {
        Stop-ScheduledTask -TaskName $cicaTaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $cicaTaskName -Confirm:$false -ErrorAction SilentlyContinue
    }
    if ($null -ne $cicaPlainBytes) { [Array]::Clear($cicaPlainBytes, 0, $cicaPlainBytes.Length) }
    if ($cicaPasswordPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($cicaPasswordPointer) }
    if ($cicaOwnPassword -and $null -ne $DatabasePassword) { $DatabasePassword.Dispose() }
    Remove-Item -LiteralPath $cicaWorkDirectory -Recurse -Force
}
if (Get-ScheduledTask -TaskName $cicaTaskName -ErrorAction SilentlyContinue) {
    throw 'A tarefa temporária precisa ser removida; não considerar o teste concluído.'
}
$cicaResult | Add-Member -NotePropertyName temporary_task_removed -NotePropertyValue $true
$cicaResult | Add-Member -NotePropertyName temporary_files_removed -NotePropertyValue $true
[IO.File]::WriteAllText($cicaFinalFile, ($cicaResult | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
$cicaResult | ConvertTo-Json -Depth 5
