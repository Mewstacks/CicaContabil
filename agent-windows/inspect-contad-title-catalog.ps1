#requires -Version 5.1
<# D-345: fixed fiscal title-family catalog only; no business records or protected agent config. #>
[CmdletBinding()]
param([switch]$Compact)
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) { throw 'Use Windows PowerShell de 64 bits.' }
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $outputDirectory=$null
$stage='credential_prompt'
$family='^ef(entradas|saidas|servicos)(par|pag|_lancto|pag_lancto)?$'
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
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Complemento fiscal: somente estrutura de tabelas. Informe a credencial local; nao envie senha ao chat.'
    if ($null -eq $credential) { throw 'Consulta cancelada.' }
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open()
    $builder.Clear(); $credential=$null; $timer=[Diagnostics.Stopwatch]::StartNew()
    $stage='selecting_fixed_fiscal_family'
    $allTables=$connection.GetSchema('Tables',[string[]]@($null,'bethadba',$null))
    $selected=@($allTables.Rows | Where-Object {
        ([string]$_.TABLE_SCHEM -ieq 'bethadba') -and
        ([string]$_.TABLE_TYPE -ieq 'TABLE') -and
        ([string]$_.TABLE_NAME -imatch $family)
    } | Sort-Object TABLE_NAME)
    if ($selected.Count -lt 1 -or $selected.Count -gt 15) { throw 'Familia fiscal ausente ou excedeu limite.' }
    $names=@($selected | ForEach-Object { [string]$_.TABLE_NAME })
    if (@($names | Sort-Object -Unique).Count -ne $names.Count) { throw 'Tabela fiscal duplicada.' }
    foreach ($name in $names) {
        if ($name.Length -gt 128 -or $name -match '\p{C}' -or $name -notmatch $family) { throw 'Nome fora da familia fixa.' }
    }
    $placeholders=(@($names | ForEach-Object {'?'}) -join ',')
    $stage='reading_target_ids'
    $tables=Read-CatalogRows -Limit 15 -Fields @('table_id','table_name','table_type') -Values (@('bethadba')+$names) -Query @"
SELECT TOP 16 t.table_id, t.table_name, t.table_type
FROM SYS.SYSTAB t JOIN SYS.SYSUSER u ON u.user_id=t.creator
WHERE u.user_name=? AND t.table_name IN ($placeholders)
ORDER BY t.table_id
"@
    if ($tables.Count -ne $names.Count) { throw 'Identidade fiscal incompleta.' }
    $objects=New-Object 'System.Collections.Generic.List[object]'; $columnCount=0
    $stage='reading_columns'
    foreach ($table in $tables) {
        if ($table.table_type -ne 1 -or $timer.Elapsed.TotalSeconds -gt 150) { throw 'Tabela/tempo de catalogo incompativel.' }
        $raw=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',[string]$table.table_name,$null))
        $rows=@($raw.Rows | Where-Object {
            ([string]$_.TABLE_SCHEM -ieq 'bethadba') -and
            ([string]$_.TABLE_NAME -ieq $table.table_name)
        } | Sort-Object { [int]$_.ORDINAL_POSITION })
        if ($rows.Count -lt 1 -or $rows.Count -gt 1000) { throw 'Colunas fiscais ausentes ou acima do limite.' }
        $columns=New-Object 'System.Collections.Generic.List[object]'
        foreach ($row in $rows) {
            $name=[string]$row.COLUMN_NAME
            if ($name.Length -lt 1 -or $name.Length -gt 128 -or $name -match '\p{C}') { throw 'Coluna de catalogo incompativel.' }
            $columns.Add([ordered]@{name=$name;type=[string]$row.TYPE_NAME;size=[string]$row.COLUMN_SIZE;nullable=[int]$row.NULLABLE;decimal_digits=[string]$row.DECIMAL_DIGITS})
        }
        $columnCount+=$columns.Count
        if ($columnCount -gt 15000) { throw 'Colunas fiscais excederam limite global.' }
        $objects.Add([ordered]@{table_id=$table.table_id;name=$table.table_name;columns=@($columns.ToArray())})
    }
    $stage='reading_declared_keys'
    $keys=Read-CatalogRows -Limit 2048 -Fields @('table_id','index_id','index_category','unique_code','not_enforced','index_name','sequence','column_id','column_name','primary_column_id') -Values (@('bethadba')+$names) -Query @"
SELECT TOP 2049 i.table_id, i.index_id, i.index_category, i."unique", i.not_enforced,
 i.index_name, ic.sequence, ic.column_id, c.column_name, ic.primary_column_id
FROM SYS.SYSIDX i
JOIN SYS.SYSTAB t ON t.table_id=i.table_id
JOIN SYS.SYSUSER u ON u.user_id=t.creator
JOIN SYS.SYSIDXCOL ic ON ic.table_id=i.table_id AND ic.index_id=i.index_id
JOIN SYS.SYSTABCOL c ON c.table_id=ic.table_id AND c.column_id=ic.column_id
WHERE u.user_name=? AND t.table_name IN ($placeholders)
 AND (i.index_category IN (1,2) OR i."unique" IN (1,2,5))
ORDER BY i.table_id, i.index_id, ic.sequence
"@
    $stage='reading_declared_relations'
    $relations=Read-CatalogRows -Limit 4096 -Fields @('foreign_table_id','foreign_index_id','primary_table_id','primary_index_id','foreign_schema','foreign_table','primary_schema','primary_table','match_type','check_on_commit','nulls','sequence','foreign_column_id','foreign_column','primary_column_id','primary_column') -Values (@('bethadba')+$names+@('bethadba')+$names) -Query @"
SELECT TOP 4097 f.foreign_table_id, f.foreign_index_id, f.primary_table_id, f.primary_index_id,
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
WHERE (fu.user_name=? AND ft.table_name IN ($placeholders))
 OR (pu.user_name=? AND pt.table_name IN ($placeholders))
ORDER BY f.foreign_table_id, f.foreign_index_id, ic.sequence
"@
    $connection.Close()
    if ($timer.Elapsed.TotalSeconds -gt 150) { throw 'Tempo do complemento excedido.' }
    $result=[ordered]@{
        version='contad-title-catalog-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o')
        schema='bethadba';family=$family;objects=@($objects.ToArray());key_columns=$keys;relation_columns=$relations
        declared_metadata_only=$true;financial_semantics_approved=$false;business_values_selected=$false
        agent_configuration_read=$false;erp_write_performed=$false;uploaded=$false
    }
    $stage='writing_private_report'
    $json=$result | ConvertTo-Json -Depth 9 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($json)
    if ($bytes.Length -gt 4194304) { throw 'Relatorio excedeu quatro MiB.' }
    $outputDirectory=Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Titulos-Estrutura-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($outputDirectory)
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $userSid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    foreach ($sid in @($userSid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')),(New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
        $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    }
    Set-Acl -LiteralPath $outputDirectory -AclObject $acl
    $path=Join-Path $outputDirectory 'estrutura-titulos.json'
    [IO.File]::WriteAllBytes($path,$bytes)
    $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Compact) {
        $buffer=New-Object IO.MemoryStream
        $gzip=New-Object IO.Compression.GZipStream($buffer,[IO.Compression.CompressionMode]::Compress,$true)
        try { $gzip.Write($bytes,0,$bytes.Length) } finally { $gzip.Dispose() }
        try { $packed=[Convert]::ToBase64String($buffer.ToArray()) } finally { $buffer.Dispose() }
        [ordered]@{version='contad-title-catalog-transfer-v1';sha256=$sha;bytes=$bytes.Length;encoding='gzip-base64';data=$packed} | ConvertTo-Json -Compress | Write-Output
    } else {
        [ordered]@{completed=$true;tables=$names;columns=$columnCount;keys=$keys.Count;relations=$relations.Count;sha256=$sha;report_file=$path;business_values_selected=$false} | ConvertTo-Json -Depth 3 | Write-Output
    }
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]';$states=New-Object 'System.Collections.Generic.List[string]'
    $exception=$_.Exception
    for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {
            foreach ($item in @($exception.Errors | Select-Object -First 20)) {
                if ($item.SQLState -match '^[A-Z0-9]{5}$') { $states.Add($item.SQLState) }
            }
        }
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-title-catalog-diagnostic-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 4 | Write-Output
    Write-Error 'Complemento nao concluido; envie somente o diagnostico seguro, sem senha.' -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
    if ($null -ne $builder) { $builder.Clear() }
    $credential=$null
}
