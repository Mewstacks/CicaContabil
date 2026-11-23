#requires -Version 5.1
<# D-335: fixed catalog metadata only. Never select business rows or saved secrets. #>
[CmdletBinding()]
param([switch]$AsJson)
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitProcess) { throw 'Use Windows PowerShell de 64 bits.' }
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $outputDirectory=$null
$stage='credential_prompt'
$targets=@('GEEMPRE','CTCONTAS','CTCONTACAIXA','CTCONTACAIXA_CONTA_BANCARIA','CTLANCTO','CTCLANCTO','CTCCUSTO','EFCLIENTES','EFFORNECE')

function Read-CatalogRows {
    param([string]$Query, [object[]]$Values, [string[]]$Fields, [int]$Limit)
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandTimeout=40; $command.CommandText=$Query
        foreach ($value in $Values) {
            $parameter=$command.Parameters.Add('p',[System.Data.Odbc.OdbcType]::VarChar,128)
            $parameter.Value=[string]$value
        }
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) { throw 'Contrato de catálogo incompatível.' }
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            if ($rows.Count -ge $Limit -or $timer.Elapsed.TotalSeconds -gt 150) { throw 'Limite do complemento excedido.' }
            $row=[ordered]@{}
            for ($i=0; $i -lt $Fields.Count; $i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin @('primary_column_id','primary_column','not_enforced')) { throw 'Metadado obrigatório ausente.' }
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($field -match '(_id|_category|_code|sequence|table_type|match_type)$') {
                    if ($value -is [string]) { throw 'Tipo numérico de catálogo incompatível.' }
                    $number=[long]$value
                    if ($number -lt 0 -or $number -gt 4294967295 -or [decimal]$value -ne $number) { throw 'Número de catálogo fora do limite.' }
                    $row[$field]=$number
                } else {
                    $name=([string]$value).TrimEnd([char[]]@(' '))
                    if ($name.Length -lt 1 -or $name.Length -gt 128 -or $name -match '\p{C}') { throw 'Identificador de catálogo fora do limite.' }
                    $row[$field]=$name
                }
            }
            $rows.Add($row)
        }
        return ,$rows.ToArray()
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        $command.Dispose()
    }
}

try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Somente metadados de chaves: informe a credencial local do Domínio. Não envie a senha ao chat.'
    if ($null -eq $credential) { throw 'Consulta cancelada.' }
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open()
    $builder.Clear(); $credential=$null; $timer=[Diagnostics.Stopwatch]::StartNew()
    $stage='reading_target_tables'
    $tables=Read-CatalogRows -Limit 9 -Fields @('table_id','table_name','table_type') -Values (@('bethadba')+$targets) -Query @'
SELECT TOP 10 t.table_id, t.table_name, t.table_type
FROM SYS.SYSTAB t JOIN SYS.SYSUSER u ON u.user_id=t.creator
WHERE u.user_name=? AND UPPER(t.table_name) IN (?,?,?,?,?,?,?,?,?)
ORDER BY t.table_id
'@
    if ($tables.Count -ne $targets.Count -or @($tables | ForEach-Object {$_.table_name.ToUpperInvariant()} | Sort-Object -Unique).Count -ne $targets.Count) { throw 'Objetos esperados não identificados de modo único.' }
    foreach ($target in $targets) {
        if (@($tables | Where-Object {$_.table_name -ieq $target -and $_.table_type -eq 1}).Count -ne 1) { throw 'Tabela base esperada ausente.' }
    }
    $stage='reading_declared_keys'
    $keys=Read-CatalogRows -Limit 1024 -Fields @('table_id','index_id','index_category','unique_code','not_enforced','index_name','sequence','column_id','column_name','primary_column_id') -Values (@('bethadba')+$targets) -Query @'
SELECT TOP 1025 i.table_id, i.index_id, i.index_category, i."unique", i.not_enforced,
 i.index_name, ic.sequence, ic.column_id, c.column_name, ic.primary_column_id
FROM SYS.SYSIDX i
JOIN SYS.SYSTAB t ON t.table_id=i.table_id
JOIN SYS.SYSUSER u ON u.user_id=t.creator
JOIN SYS.SYSIDXCOL ic ON ic.table_id=i.table_id AND ic.index_id=i.index_id
JOIN SYS.SYSTABCOL c ON c.table_id=ic.table_id AND c.column_id=ic.column_id
WHERE u.user_name=? AND UPPER(t.table_name) IN (?,?,?,?,?,?,?,?,?)
 AND (i.index_category IN (1,2) OR i."unique" IN (1,2,5))
ORDER BY i.table_id, i.index_id, ic.sequence
'@
    $stage='reading_declared_relations'
    $relations=Read-CatalogRows -Limit 2048 -Fields @('foreign_table_id','foreign_index_id','primary_table_id','primary_index_id','foreign_schema','foreign_table','primary_schema','primary_table','match_type','check_on_commit','nulls','sequence','foreign_column_id','foreign_column','primary_column_id','primary_column') -Values (@('bethadba')+$targets+@('bethadba')+$targets) -Query @'
SELECT TOP 2049 f.foreign_table_id, f.foreign_index_id, f.primary_table_id, f.primary_index_id,
 fu.user_name, ft.table_name, pu.user_name, pt.table_name, f.match_type, f.check_on_commit,
 f.nulls, ic.sequence, ic.column_id, fc.column_name, ic.primary_column_id, pc.column_name
FROM SYS.SYSFKEY f
JOIN SYS.SYSTAB ft ON ft.table_id=f.foreign_table_id
JOIN SYS.SYSUSER fu ON fu.user_id=ft.creator
JOIN SYS.SYSTAB pt ON pt.table_id=f.primary_table_id
JOIN SYS.SYSUSER pu ON pu.user_id=pt.creator
JOIN SYS.SYSIDXCOL ic ON ic.table_id=f.foreign_table_id AND ic.index_id=f.foreign_index_id
JOIN SYS.SYSTABCOL fc ON fc.table_id=ic.table_id AND fc.column_id=ic.column_id
LEFT JOIN SYS.SYSTABCOL pc ON pc.table_id=f.primary_table_id AND pc.column_id=ic.primary_column_id
WHERE (fu.user_name=? AND UPPER(ft.table_name) IN (?,?,?,?,?,?,?,?,?))
 OR (pu.user_name=? AND UPPER(pt.table_name) IN (?,?,?,?,?,?,?,?,?))
ORDER BY f.foreign_table_id, f.foreign_index_id, ic.sequence
'@
    $connection.Close()
    if ($timer.Elapsed.TotalSeconds -gt 150) { throw 'Tempo do complemento excedido.' }
    $result=[ordered]@{
        version='contad-relations-v1'; completed=$true; observed_at_utc=[DateTime]::UtcNow.ToString('o')
        schema='bethadba'; targets=$targets; tables=$tables; key_columns=$keys; relation_columns=$relations
        declared_metadata_only=$true; financial_semantics_approved=$false; business_values_selected=$false
        agent_configuration_read=$false; erp_write_performed=$false; uploaded=$false
    }
    $stage='writing_private_report'
    $json=$result | ConvertTo-Json -Depth 8
    if ([Text.Encoding]::UTF8.GetByteCount($json) -gt 2097152) { throw 'Relatório excedeu dois MiB.' }
    $outputDirectory=Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Relacoes-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($outputDirectory)
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $userSid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    foreach ($sid in @($userSid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')),(New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
        $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    Set-Acl -LiteralPath $outputDirectory -AclObject $acl
    $path=Join-Path $outputDirectory 'relacoes.json'
    [IO.File]::WriteAllText($path,$json,(New-Object Text.UTF8Encoding($false)))
    if ($AsJson) { $result | ConvertTo-Json -Depth 8 -Compress | Write-Output }
    else {
        [ordered]@{version='contad-relations-summary-v1';completed=$true;tables=$tables.Count;key_columns=$keys.Count;relation_columns=$relations.Count;report_file=$path;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();financial_semantics_approved=$false;uploaded=$false} | ConvertTo-Json | Write-Output
    }
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]'; $states=New-Object 'System.Collections.Generic.List[string]'; $native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for ($depth=0; $null -ne $exception -and $depth -lt 8; $depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {
            foreach ($item in @($exception.Errors | Select-Object -First 20)) {
                if ($item.SQLState -match '^[A-Z0-9]{5}$') { $states.Add($item.SQLState) }
                $native.Add([int]$item.NativeError)
            }
        }
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-relations-diagnostic-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 | Write-Output
    Write-Error 'Complemento não concluído. Envie somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
    if ($null -ne $builder) { $builder.Clear() }
    $credential=$null
}
