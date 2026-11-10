#requires -Version 5.1
<#
D-323/Q-28: metadata and aggregate company-status counts only.
No source data samples, financial values, saved passwords or network upload.
ODBC metadata: https://learn.microsoft.com/dotnet/api/system.data.odbc.odbcconnection.getschema
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitProcess) { throw 'Use o Windows PowerShell de 64 bits.' }
Add-Type -AssemblyName System.Data
$connection = $null
$builder = $null
$credential = $null
$outputDirectory = $null
try {
    # Local entry only. Never inspect the registry or decrypt the agent configuration.
    $credential = Get-Credential -UserName 'EXTERNO' -Message 'Somente leitura: informe a credencial local do Domínio. Não a envie ao chat.'
    if ($null -eq $credential) { throw 'Consulta cancelada.' }
    $builder = New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN'] = 'CICA_CONTAD'
    $builder['UID'] = $credential.UserName
    $builder['PWD'] = $credential.GetNetworkCredential().Password
    $connection = New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout = 20
    $connection.Open()
    $builder.Clear()
    $credential = $null
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $tables = $connection.GetSchema('Tables', [string[]]@($null, 'bethadba', $null, $null))
    $selected = @($tables.Rows | Where-Object {
        ([string]$_.TABLE_SCHEM -ieq 'bethadba') -and (
            ([string]$_.TABLE_NAME -ieq 'GEEMPRE') -or
            ([string]$_.TABLE_NAME -imatch '^CT') -or
            ([string]$_.TABLE_NAME -imatch '^EF.*(PARC|PAGA|RECE|BAIX|CLIENTE|FORNE|BANCO|CONTA)')
        )
    } | Sort-Object TABLE_NAME)
    if ($selected.Count -gt 1500) { throw 'Mais de 1500 objetos pertinentes; refine o inventário. Nenhum resultado parcial será apresentado como completo.' }
    $objects = New-Object 'System.Collections.Generic.List[object]'
    $columnCount = 0
    foreach ($table in $selected) {
        if ($timer.Elapsed.TotalMinutes -gt 5) { throw 'Inventário excedeu cinco minutos; não concluído.' }
        $tableName = [string]$table.TABLE_NAME
        $columns = $connection.GetSchema('Columns', [string[]]@($null, 'bethadba', $tableName, $null))
        $ownColumns = @($columns.Rows | Where-Object {
            ([string]$_.TABLE_SCHEM -ieq 'bethadba') -and ([string]$_.TABLE_NAME -ieq $tableName)
        } | Sort-Object { [int]$_.ORDINAL_POSITION })
        if ($ownColumns.Count -eq 0) { throw 'Objeto sem metadados de colunas; inventário não concluído.' }
        $columnCount += $ownColumns.Count
        if ($columnCount -gt 50000) { throw 'Inventário excedeu 50000 colunas; não concluído.' }
        $fields = @($ownColumns | ForEach-Object {
            [ordered]@{
                name = [string]$_.COLUMN_NAME
                type = [string]$_.TYPE_NAME
                ordinal = [int]$_.ORDINAL_POSITION
                nullable = [int]$_.NULLABLE
                size = [string]$_.COLUMN_SIZE
                decimal_digits = [string]$_.DECIMAL_DIGITS
            }
        })
        $objects.Add([ordered]@{ schema = 'bethadba'; name = $tableName; kind = [string]$table.TABLE_TYPE; columns = $fields })
    }
    $company = @($objects | Where-Object { $_.name -ieq 'GEEMPRE' })
    if ($company.Count -ne 1) { throw 'Cadastro GEEMPRE não identificado de modo único.' }
    $names = @($company[0].columns | ForEach-Object { $_.name.ToUpperInvariant() })
    foreach ($required in @('CODI_EMP', 'NOME_EMP', 'CGCE_EMP', 'STAT_EMP')) {
        if ($names -notcontains $required) { throw 'Cadastro incompatível com o contrato observado; nenhuma consulta de dados executada.' }
    }
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 60
    $command.CommandText = 'SELECT TOP 21 stat_emp, COUNT(*) FROM bethadba.geempre GROUP BY stat_emp ORDER BY stat_emp'
    $reader = $command.ExecuteReader()
    $statuses = New-Object 'System.Collections.Generic.List[object]'
    $companyTotal = [long]0
    try {
        while ($reader.Read()) {
            if ($statuses.Count -ge 20) { throw 'Mais de vinte situações; inventário agregado não concluído.' }
            $statusCount = [long]$reader.GetValue(1)
            $companyTotal += $statusCount
            $statuses.Add([ordered]@{ source_status = [string]$reader.GetValue(0); count = $statusCount })
        }
    } finally { $reader.Dispose(); $command.Dispose() }
    $connection.Close()
    $result = [ordered]@{
        version = 'contad-schema-inventory-v1'
        observed_at_utc = [DateTime]::UtcNow.ToString('o')
        financial_period_start = '2026-09-01'
        object_selection = 'GEEMPRE; CT*; EF*(PARC|PAGA|RECE|BAIX|CLIENTE|FORNE|BANCO|CONTA)'
        objects = @($objects.ToArray())
        object_count = $objects.Count
        column_count = $columnCount
        company_status_counts = @($statuses.ToArray())
        company_count = $companyTotal
        status_mapping_approved = $false
        keys_relations_and_financial_semantics_verified = $false
        elapsed_seconds = [Math]::Round($timer.Elapsed.TotalSeconds, 2)
    }
    $outputDirectory = Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Inventario-' + [Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($outputDirectory)
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    foreach ($sid in @($userSid, (New-Object Security.Principal.SecurityIdentifier('S-1-5-18')), (New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $outputDirectory -AclObject $acl
    $outputPath = Join-Path $outputDirectory 'inventario.json'
    $json = $result | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($outputPath, $json, (New-Object Text.UTF8Encoding($false)))
    Write-Host ('Inventário concluído: {0} objetos, {1} colunas, {2} empresas.' -f $objects.Count, $columnCount, $result.company_count)
    Write-Host ('Arquivo local restrito: ' + $outputPath)
    Write-Host ('SHA-256: ' + (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLowerInvariant())
    Write-Host 'Nenhum dado foi enviado. Metadados não comprovam chaves, relações ou semântica financeira.'
} catch {
    # ODBC exception text can contain connection details. Return only the exception type.
    Write-Error ('Inventário não concluído. Tipo: ' + $_.Exception.GetType().Name + '. Preserve a janela para orientação, sem compartilhar credenciais.') -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
    if ($null -ne $builder) { $builder.Clear() }
    $credential = $null
}
