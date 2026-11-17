#requires -Version 5.1
<# D-373/Q-28. Fixed cadastral SELECTs only. Never reads agent.config, writes ERP,
   selects transaction values or infers a cash-to-ledger mapping. Private ZIP stays local. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
Add-Type -AssemblyName System.IO.Compression
$connection=$null; $builder=$null; $credential=$null; $timer=$null
$stage='credential_prompt'; $reason='UNCLASSIFIED'; $outputDirectory=$null
$completed=$false; $readDirectories=@()
$textFailure=$null
$periodStart=[DateTime]::new(2026,9,1); $periodEnd=[DateTime]::new(2026,12,1)
$expectedCompanyCount=146
$expectedCompanyCodeSha256='4ab91c9e80c1b20275c5878b3ec3f844deec7f6b155d94fdb90b79fbf6626f55'
function Reject-Details {param([string]$Code); $script:reason=$Code; throw 'Descoberta cadastral recusado.'}
function Check-Deadline {
    if ($null -ne $timer -and $timer.Elapsed.TotalSeconds -gt 1800) {Reject-Details 'TIME_LIMIT'}
}
function Reject-SourceText {
    param([string]$Field,[object]$Value,[int]$Limit,[string]$Violation)
    # Never include the text, its row key, SQL, credentials or printable codepoints.
    $type=if ($null -eq $Value) {'null'} else {$Value.GetType().FullName}
    $length=$null; $scalars=$null; $inspected=0; $nonprinting=0; $truncated=$false
    $positions=New-Object 'System.Collections.Generic.List[object]'
    if ($Value -is [string]) {
        $length=$Value.Length; $scalars=0; $valid=$true
        $scanLimit=[Math]::Min($length,512)
        for ($index=0;$index -lt $scanLimit;$index++) {
            $unit=$Value[$index]; $category=[Globalization.CharUnicodeInfo]::GetUnicodeCategory($Value,$index)
            $scalars++; $inspected=$index+1
            if ([char]::IsHighSurrogate($unit) -and $index+1 -lt $length -and [char]::IsLowSurrogate($Value[$index+1])) {
                $index++; $inspected=$index+1
                continue
            }
            if ([char]::IsSurrogate($unit)) {$valid=$false}
            if ($category -in @([Globalization.UnicodeCategory]::Control,[Globalization.UnicodeCategory]::Format,[Globalization.UnicodeCategory]::Surrogate)) {
                $nonprinting++
                if ($positions.Count -lt 32) {
                    $positions.Add([ordered]@{utf16_index=$index;category=$category.ToString();codepoint=('U+{0:X4}' -f [int]$unit)})
                } else {$truncated=$true}
            }
        }
        if ($length -gt $inspected) {$truncated=$true; $scalars=$null}
        if (-not $valid) {$scalars=$null}
    }
    $script:textFailure=[ordered]@{
        field=$Field;dotnet_type=$type;utf16_length=$length;utf16_limit=$Limit;violation=$Violation
        scalar_length=$scalars;inspected_utf16_units=$inspected;nonprinting_in_scanned=$nonprinting
        nonprinting_positions=$positions.ToArray();diagnostic_truncated=$truncated
    }
    Reject-Details 'TEXT_CONTRACT'
}
function Assert-SourceText {
    param([string]$Field,[object]$Value,[int]$Limit)
    if ($Value -isnot [string]) {Reject-SourceText $Field $Value $Limit 'TYPE'}
    if ($Value.Length -gt $Limit) {Reject-SourceText $Field $Value $Limit 'LENGTH'}
    for ($index=0;$index -lt $Value.Length;$index++) {
        if ([char]::IsHighSurrogate($Value[$index])) {
            if ($index+1 -ge $Value.Length -or -not [char]::IsLowSurrogate($Value[$index+1])) {
                Reject-SourceText $Field $Value $Limit 'INVALID_SURROGATE'
            }
            $index++
        } elseif ([char]::IsLowSurrogate($Value[$index])) {
            Reject-SourceText $Field $Value $Limit 'INVALID_SURROGATE'
        }
    }
    # Literal, well-formed Unicode is source evidence, not approved semantics.
    # Controls, format/private-use characters and NUL remain unchanged in the
    # private JSON. Persistence must encode NUL reversibly before PostgreSQL JSONB.
}
function Read-Details {
    param([string]$Query,[string[]]$Fields,[int]$Limit,[object[]]$Values=@('A'),[object]$Sink=$null)
    Check-Deadline
    $command=$connection.CreateCommand(); $reader=$null
    $textLimits=@{account_name_raw=150;classification_raw=20;account_type_raw=1;account_status_raw=1;selection_raw=1;agency_raw=10;account_identifier_raw=30;bank_name_raw=100;comp_pad_raw=1;branch_parameter_raw=1;nature_raw=1;group_raw=1}
    $nullable=@('parameter_company_code','codi_pad_raw','comp_pad_raw','i_planocontas_raw','cash_account_parameter_raw','branch_parameter_raw','catalogue_account_code','account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw','selection_raw','cash_type_raw','bank_id_raw','bank_catalogue_id','bank_code_raw','bank_name_raw','integration_started_on_raw')
    try {
        $command.CommandText=$Query; $command.CommandTimeout=120
        foreach ($value in $Values) {
            if ($value -is [DateTime]) {$type=[System.Data.Odbc.OdbcType]::Date}
            elseif ($value -is [string]) {$type=[System.Data.Odbc.OdbcType]::VarChar}
            else {$type=[System.Data.Odbc.OdbcType]::Int}
            $parameter=$command.Parameters.Add('p',$type); $parameter.Value=$value
        }
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) {Reject-Details 'COLUMN_COUNT'}
        $rows=New-Object 'System.Collections.Generic.List[object]'; $count=0
        while ($reader.Read()) {
            Check-Deadline
            if ($count -ge $Limit) {Reject-Details 'ROW_LIMIT'}
            $row=[ordered]@{}
            for ($i=0;$i -lt $Fields.Count;$i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin $nullable) {Reject-Details 'NULL_FIELD'}
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($textLimits.ContainsKey($field)) {
                    Assert-SourceText $field $value $textLimits[$field]
                    # Do not trim/pad strings or parse banking identifiers as numbers.
                    $row[$field]=$value
                } elseif ($field -in @('inactive_on_raw','integration_started_on_raw')) {
                    if ($value -isnot [DateTime] -or $value.TimeOfDay -ne [TimeSpan]::Zero) {Reject-Details 'DATE_CONTRACT'}
                    $row[$field]=$value.ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
                } else {
                    if ($value -is [string] -or $value -is [bool]) {Reject-Details 'NUMBER_TYPE'}
                    $number=[long]$value
                    if ($number -lt 0 -or $number -gt 2147483647 -or [decimal]$value -ne $number) {Reject-Details 'NUMBER_RANGE'}
                    $row[$field]=$number
                }
            }
            $count++
            if ($null -eq $Sink) {$rows.Add($row)} else {Write-CatalogueRow $Sink $row}
        }
        Check-Deadline
        if ($null -eq $Sink) {return ,$rows.ToArray()}
    } finally {if ($null -ne $reader) {$reader.Dispose()}; $command.Dispose()}
}
function Read-CatalogRows {
    param([string]$Query, [object[]]$Values, [string[]]$Fields, [int]$Limit)
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandTimeout=120; $command.CommandText=$Query
        foreach ($value in $Values) {
            $parameter=$command.Parameters.Add('p',[System.Data.Odbc.OdbcType]::VarChar,128)
            $parameter.Value=[string]$value
        }
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) { throw 'Contrato de catálogo incompatível.' }
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            Check-Deadline
            if ($rows.Count -ge $Limit) { throw 'Limite do complemento excedido.' }
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

function Read-DiscoveryMetadata {
    $targets=@('CTPARMTO','CTPLANOCONTAS','CTNATUREZA_CONTA','CTCONTACAIXA','CTCONTACAIXA_CONTA_BANCARIA','CTPARMTO_CONTAS_ICEBERG','CTCONTAS_EQUIVALENTES')
    $script:stage='reading_target_tables'
    $tables=Read-CatalogRows -Limit 7 -Fields @('table_id','table_name','table_type') -Values (@('bethadba')+$targets) -Query @'
SELECT TOP 8 t.table_id, t.table_name, t.table_type
FROM SYS.SYSTAB t JOIN SYS.SYSUSER u ON u.user_id=t.creator
WHERE u.user_name=? AND UPPER(t.table_name) IN (?,?,?,?,?,?,?)
ORDER BY t.table_id
'@
    if ($tables.Count -ne $targets.Count -or @($tables | ForEach-Object {$_.table_name.ToUpperInvariant()} | Sort-Object -Unique).Count -ne $targets.Count) { throw 'Objetos esperados não identificados de modo único.' }
    foreach ($target in $targets) {
        if (@($tables | Where-Object {$_.table_name -ieq $target -and $_.table_type -eq 1}).Count -ne 1) { throw 'Tabela base esperada ausente.' }
    }
    $script:stage='reading_declared_keys'
    $keys=Read-CatalogRows -Limit 1024 -Fields @('table_id','index_id','index_category','unique_code','not_enforced','index_name','sequence','column_id','column_name','primary_column_id') -Values (@('bethadba')+$targets) -Query @'
SELECT TOP 1025 i.table_id, i.index_id, i.index_category, i."unique", i.not_enforced,
 i.index_name, ic.sequence, ic.column_id, c.column_name, ic.primary_column_id
FROM SYS.SYSIDX i
JOIN SYS.SYSTAB t ON t.table_id=i.table_id
JOIN SYS.SYSUSER u ON u.user_id=t.creator
JOIN SYS.SYSIDXCOL ic ON ic.table_id=i.table_id AND ic.index_id=i.index_id
JOIN SYS.SYSTABCOL c ON c.table_id=ic.table_id AND c.column_id=ic.column_id
WHERE u.user_name=? AND UPPER(t.table_name) IN (?,?,?,?,?,?,?)
 AND (i.index_category IN (1,2) OR i."unique" IN (1,2,5))
ORDER BY i.table_id, i.index_id, ic.sequence
'@
    $script:stage='reading_declared_relations'
    $relations=Read-CatalogRows -Limit 4096 -Fields @('foreign_table_id','foreign_index_id','primary_table_id','primary_index_id','foreign_schema','foreign_table','primary_schema','primary_table','match_type','check_on_commit','nulls','sequence','foreign_column_id','foreign_column','primary_column_id','primary_column') -Values (@('bethadba')+$targets+@('bethadba')+$targets) -Query @'
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
WHERE (fu.user_name=? AND UPPER(ft.table_name) IN (?,?,?,?,?,?,?))
 OR (pu.user_name=? AND UPPER(pt.table_name) IN (?,?,?,?,?,?,?))
ORDER BY f.foreign_table_id, f.foreign_index_id, ic.sequence
'@
    return [ordered]@{targets=$targets;tables=$tables;key_columns=$keys;relation_columns=$relations}
}

function New-CatalogueSink {
    param([string]$Kind,[string]$Directory,[object]$Owners,[object]$Requested)
    $names=@{chart_accounts='chart-accounts.jsonl';plan_template_accounts='plan-template-accounts.jsonl';nature_rules='nature-rules.jsonl'}
    $path=Join-Path $Directory $names[$Kind]
    $rowLimit=1000000; $byteLimit=536870912
    if ($Kind -eq 'nature_rules') {$rowLimit=100000; $byteLimit=33554432}
    return @{kind=$Kind;file=$names[$Kind];path=$path;rows=[long]0;bytes=[long]0;row_limit=$rowLimit;byte_limit=$byteLimit;previous=$null;owners=$Owners;requested=$Requested;matched=@{};stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)}
}
function Write-CatalogueRow {
    param([object]$Sink,[object]$Row)
    if ($Sink.rows -ge $Sink.row_limit) {Reject-Details 'ROW_LIMIT'}
    if (-not $Sink.owners.Contains($Row.chart_company_code)) {Reject-Details 'CATALOGUE_SCOPE'}
    if ($Sink.kind -eq 'nature_rules') {
        if ($Row.rule_order -gt 255) {Reject-Details 'NATURE_SCOPE'}
        if ($null -eq $Row.classification_raw) {Reject-Details 'CATALOGUE_NULL'}
        $key=@([long]$Row.chart_company_code,[long]$Row.rule_order)
    } else {
        if ($Row.account_code -lt 1) {Reject-Details 'CATALOGUE_SCOPE'}
        foreach ($field in @('account_name_raw','classification_raw','account_type_raw','account_status_raw')) {if ($null -eq $Row[$field]) {Reject-Details 'CATALOGUE_NULL'}}
        $key=@([long]$Row.chart_company_code,[long]$Row.account_code)
        if ($Sink.kind -eq 'plan_template_accounts') {
            Assert-SourceText 'account_name_raw' $Row.account_name_raw 60
            $key=@([long]$Row.chart_company_code,[long]$Row.plan_id_raw,[long]$Row.account_code)
        }
    }
    # Queries order by the complete numeric key. Strict monotonicity proves
    # uniqueness without keeping a million keys or catalogue objects in memory.
    if ($null -ne $Sink.previous) {
        $comparison=0
        for ($i=0;$i -lt $key.Count;$i++) {
            if ($key[$i] -lt $Sink.previous[$i]) {$comparison=-1;break}
            if ($key[$i] -gt $Sink.previous[$i]) {$comparison=1;break}
        }
        if ($comparison -le 0) {Reject-Details 'CATALOGUE_CARDINALITY'}
    }
    $Sink.previous=$key
    if ($Sink.kind -eq 'chart_accounts') {
        $lookup='{0}:{1}' -f $Row.chart_company_code,$Row.account_code
        if ($Sink.requested.ContainsKey($lookup)) {$Sink.matched[$lookup]=$Row}
    }
    $line=[Text.Encoding]::UTF8.GetBytes(($Row | ConvertTo-Json -Depth 3 -Compress)+"`n")
    if ($Sink.bytes+$line.Length -gt $Sink.byte_limit) {Reject-Details 'OUTPUT_LIMIT'}
    $Sink.stream.Write($line,0,$line.Length); $Sink.bytes+=$line.Length; $Sink.rows++
}
function Close-CatalogueSink {
    param([object]$Sink)
    if ($null -ne $Sink.stream) {$Sink.stream.Dispose();$Sink.stream=$null}
    return [ordered]@{file=$Sink.file;rows=$Sink.rows;bytes=$Sink.bytes;sha256=(Get-FileHash -LiteralPath $Sink.path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Read-Snapshot {
    param([string]$Directory)
    $script:stage='reading_active_company_codes'
    $companies=Read-Details -Limit 500 -Fields @('company_code','parameter_company_code','codi_pad_raw','comp_pad_raw','i_planocontas_raw','cash_account_parameter_raw','branch_parameter_raw') -Query @'
SELECT TOP 501 g.codi_emp,p.codi_emp,p.codi_pad,p.comp_pad,p.I_PLANOCONTAS,p.ccxa_par,p.fili_par
FROM bethadba.geempre g LEFT JOIN bethadba.ctparmto p ON p.codi_emp=g.codi_emp
WHERE g.stat_emp=?
ORDER BY g.codi_emp
'@
    $companyIds=New-Object 'System.Collections.Generic.HashSet[long]'
    foreach ($company in $companies) {
        $company['configuration_rows']=0
        if ($null -ne $company.parameter_company_code) {
            if ($company.parameter_company_code -ne $company.company_code -or $null -eq $company.i_planocontas_raw) {Reject-Details 'COMPANY_CONFIGURATION'}
            $company['configuration_rows']=1
        } elseif (@('codi_pad_raw','comp_pad_raw','i_planocontas_raw','cash_account_parameter_raw','branch_parameter_raw') | Where-Object {$null -ne $company[$_]}) {Reject-Details 'COMPANY_CONFIGURATION'}
        $company.Remove('parameter_company_code')
        if ($company.company_code -lt 1 -or -not $companyIds.Add($company.company_code)) {Reject-Details 'COMPANY_COVERAGE'}
    }
    if ($companies.Count -ne $expectedCompanyCount) {Reject-Details 'COMPANY_COUNT_CHANGED'}
    # Sort primitive Int64 codes: Sort-Object -Property does not consistently
    # resolve OrderedDictionary keys and can scramble otherwise identical sets.
    $codeText=(@($companies | ForEach-Object {[long]$_.company_code} | Sort-Object | ForEach-Object {$_.ToString([Globalization.CultureInfo]::InvariantCulture)}) -join ',')
    $hasher=[Security.Cryptography.SHA256]::Create()
    try {$codeSha=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::ASCII.GetBytes($codeText)))).Replace('-','').ToLowerInvariant()}
    finally {$hasher.Dispose()}
    if ($codeSha -cne $expectedCompanyCodeSha256) {Reject-Details 'COMPANY_CODES_CHANGED'}
    $script:stage='reading_configured_account_details'
    $configured=Read-Details -Limit 5000 -Fields @('company_code','chart_company_code','account_code','catalogue_account_code','account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw') -Query @'
SELECT TOP 5001 q.CODI_EMP,q.CODI_EMP_PLANO,q.CODI_CTA,c.codi_cta,
 c.nome_cta,c.clas_cta,c.tipo_cta,c.SITUACAO_CTA,c.DATAINATIVA_CTA
FROM bethadba.CTCONCILIACAO_CONTA q
JOIN bethadba.geempre g ON g.codi_emp=q.CODI_EMP
LEFT JOIN bethadba.ctcontas c ON c.codi_emp=q.CODI_EMP_PLANO AND c.codi_cta=q.CODI_CTA
WHERE g.stat_emp=?
ORDER BY q.CODI_EMP,q.CODI_EMP_PLANO,q.CODI_CTA
'@
    $keys=New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($account in $configured) {
        $key='{0}:{1}:{2}' -f $account.company_code,$account.chart_company_code,$account.account_code
        if (-not $companyIds.Contains($account.company_code) -or $account.chart_company_code -lt 1 -or $account.account_code -lt 1) {Reject-Details 'ACCOUNT_SCOPE'}
        if (-not $keys.Add($key)) {Reject-Details 'ACCOUNT_CARDINALITY'}
        $account['catalogue_matches']=0
        if ($null -ne $account.catalogue_account_code) {
            if ($account.catalogue_account_code -ne $account.account_code) {Reject-Details 'ACCOUNT_LOOKUP'}
            foreach ($field in @('account_name_raw','classification_raw','account_type_raw','account_status_raw')) {
                if ($null -eq $account[$field]) {Reject-Details 'ACCOUNT_LOOKUP'}
            }
            $account['catalogue_matches']=1
        } elseif (@('account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw') | Where-Object {$null -ne $account[$_]}) {Reject-Details 'ACCOUNT_LOOKUP'}
    }
    $script:stage='reading_cash_accounts'
    $cash=Read-Details -Limit 5000 -Fields @('company_code','cash_account_code','selection_raw','cash_type_raw') -Query @'
SELECT TOP 5001 c.codi_emp,c.codi_cta,c.sele_cta,c.TIPO_CONTA_CAIXA
FROM bethadba.ctcontacaixa c
JOIN bethadba.geempre g ON g.codi_emp=c.codi_emp
WHERE g.stat_emp=?
ORDER BY c.codi_emp,c.codi_cta
'@
    $cashByKey=@{}
    foreach ($account in $cash) {
        $key='{0}:{1}' -f $account.company_code,$account.cash_account_code
        if (-not $companyIds.Contains($account.company_code)) {Reject-Details 'CASH_SCOPE'}
        if ($cashByKey.ContainsKey($key)) {Reject-Details 'CASH_CARDINALITY'}
        $account['bank_reference_count']=0
        $cashByKey[$key]=$account
    }
    $script:stage='reading_bank_references'
    $banks=Read-Details -Limit 20000 -Fields @('company_code','cash_account_code','bank_reference_sequence','agency_raw','account_identifier_raw','bank_id_raw','bank_catalogue_id','bank_code_raw','bank_name_raw') -Query @'
SELECT TOP 20001 b.CODI_EMP,b.I_CONTA_CAIXA,b.I_SEQUENCIAL_CONTA_BANCARIA,
 b.AGENCIA,b.IDENTIFICADOR_CONTA,b.I_BANCO,k.I_BANCO,k.CODIGO_BANCO,k.DESCRICAO_BANCO
FROM bethadba.CTCONTACAIXA_CONTA_BANCARIA b
JOIN bethadba.geempre g ON g.codi_emp=b.CODI_EMP
LEFT JOIN bethadba.CTLISTA_BANCOS_BANCO_CENTRAL k ON k.I_BANCO=b.I_BANCO
WHERE g.stat_emp=?
ORDER BY b.CODI_EMP,b.I_CONTA_CAIXA,b.I_SEQUENCIAL_CONTA_BANCARIA
'@
    $keys.Clear()
    foreach ($bank in $banks) {
        $key='{0}:{1}:{2}' -f $bank.company_code,$bank.cash_account_code,$bank.bank_reference_sequence
        if (-not $companyIds.Contains($bank.company_code)) {Reject-Details 'BANK_SCOPE'}
        if (-not $keys.Add($key)) {Reject-Details 'BANK_CARDINALITY'}
        $cashKey='{0}:{1}' -f $bank.company_code,$bank.cash_account_code
        $bank['cash_key_present']=$cashByKey.ContainsKey($cashKey)
        if ($bank.cash_key_present) {$cashByKey[$cashKey]['bank_reference_count']++}
        $bank['bank_catalogue_matches']=0
        if ($null -ne $bank.bank_catalogue_id) {
            if ($null -eq $bank.bank_id_raw -or $bank.bank_catalogue_id -ne $bank.bank_id_raw -or $null -eq $bank.bank_code_raw -or $null -eq $bank.bank_name_raw) {Reject-Details 'BANK_LOOKUP'}
            $bank['bank_catalogue_matches']=1
        } elseif ($null -ne $bank.bank_code_raw -or $null -ne $bank.bank_name_raw) {Reject-Details 'BANK_LOOKUP'}
    }
    $script:stage='reading_integration_account_configurations'
    $integrations=Read-Details -Limit 5000 -Fields @('company_code','integration_account_code_raw','integration_branch_code_raw','integration_bank_id_raw','integration_started_on_raw') -Query @'
SELECT TOP 5001 i.CODI_EMP,i.CODI_CTA,i.CODI_FIL,i.I_BANCO,i.DATA_INICIO_INTEGRACAO
FROM bethadba.CTPARMTO_CONTAS_ICEBERG i
JOIN bethadba.geempre g ON g.codi_emp=i.CODI_EMP
WHERE g.stat_emp=?
ORDER BY i.CODI_EMP,i.CODI_CTA,i.CODI_FIL,i.I_BANCO
'@
    $keys.Clear()
    foreach ($configuration in $integrations) {
        if (-not $companyIds.Contains($configuration.company_code)) {Reject-Details 'INTEGRATION_SCOPE'}
        # Comparison key only: no retained foreign key proves an account owner,
        # branch meaning or association of this I_BANCO with the bank catalog.
        $key='{0}:{1}:{2}:{3}' -f $configuration.company_code,$configuration.integration_account_code_raw,$configuration.integration_branch_code_raw,$configuration.integration_bank_id_raw
        if (-not $keys.Add($key)) {Reject-Details 'INTEGRATION_CARDINALITY'}
    }
    $script:stage='reading_equivalent_account_references'
    $equivalents=Read-Details -Limit 20000 -Fields @('company_code','chart_company_code','account_code') -Query @'
SELECT TOP 20001 e.CODI_EMP,e.CODI_EMP_PLANO,e.CODI_CTA
FROM bethadba.CTCONTAS_EQUIVALENTES e
JOIN bethadba.geempre g ON g.codi_emp=e.CODI_EMP
WHERE g.stat_emp=?
ORDER BY e.CODI_EMP,e.CODI_EMP_PLANO,e.CODI_CTA
'@
    $keys.Clear()
    foreach ($item in $equivalents) {
        if (-not $companyIds.Contains($item.company_code) -or $item.chart_company_code -lt 1 -or $item.account_code -lt 1) {Reject-Details 'EQUIVALENT_SCOPE'}
        if (-not $keys.Add(('{0}:{1}:{2}' -f $item.company_code,$item.chart_company_code,$item.account_code))) {Reject-Details 'EQUIVALENT_CARDINALITY'}
    }
    $script:stage='reading_observed_chart_usage'
    $usage=Read-Details -Limit 10000 -Values @('A',$periodStart,$periodEnd) -Fields @('company_code','chart_company_code','branch_code','year','month','entry_count') -Query @'
SELECT TOP 10001 l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan),COUNT(*)
FROM bethadba.ctlancto l JOIN bethadba.geempre g ON g.codi_emp=l.codi_emp
WHERE g.stat_emp=? AND l.data_lan>=? AND l.data_lan<?
GROUP BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan)
ORDER BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan)
'@
    $keys.Clear(); $total=[long]0
    foreach ($item in $usage) {
        if (-not $companyIds.Contains($item.company_code) -or $item.chart_company_code -lt 1 -or $item.year -ne 2026 -or $item.month -lt 9 -or $item.month -gt 11 -or $item.entry_count -lt 1) {Reject-Details 'USAGE_SCOPE'}
        if (-not $keys.Add(('{0}:{1}:{2}:{3}:{4}' -f $item.company_code,$item.chart_company_code,$item.branch_code,$item.year,$item.month))) {Reject-Details 'USAGE_CARDINALITY'}
        $total+=$item.entry_count
        if ($total -gt 5000000) {Reject-Details 'USAGE_TOTAL_LIMIT'}
    }
    # Candidate owners are a union of independently labelled references. This is
    # a catalogue selection, never an assertion that CODI_PAD/COMP_PAD is active.
    $ownerSet=New-Object 'System.Collections.Generic.HashSet[long]'
    foreach ($company in $companies) {
        [void]$ownerSet.Add($company.company_code)
        if ($null -ne $company.codi_pad_raw -and $company.codi_pad_raw -gt 0) {[void]$ownerSet.Add($company.codi_pad_raw)}
    }
    foreach ($item in @($configured)+@($equivalents)+@($usage)) {[void]$ownerSet.Add($item.chart_company_code)}
    $owners=@($ownerSet | Sort-Object)
    if ($owners.Count -gt 600) {Reject-Details 'OWNER_LIMIT'}
    $requested=@{}
    foreach ($item in $configured) {$requested[('{0}:{1}' -f $item.chart_company_code,$item.account_code)]=$true}
    $charts=$null; $templates=$null; $natures=$null
    try {
        $charts=New-CatalogueSink 'chart_accounts' $Directory $ownerSet $requested
        $templates=New-CatalogueSink 'plan_template_accounts' $Directory $ownerSet $requested
        $natures=New-CatalogueSink 'nature_rules' $Directory $ownerSet $requested
    for ($offset=0;$offset -lt $owners.Count;$offset+=100) {
        $last=[Math]::Min($offset+99,$owners.Count-1)
        $batch=@($owners[$offset..$last]); $placeholders=(@($batch | ForEach-Object {'?'}) -join ',')
        $script:stage='reading_complete_chart_accounts'
        $query=@'
SELECT TOP 1000001 c.codi_emp,c.codi_cta,c.nome_cta,c.clas_cta,c.tipo_cta,c.SITUACAO_CTA,c.DATAINATIVA_CTA
FROM bethadba.ctcontas c WHERE c.codi_emp IN (__OWNERS__)
ORDER BY c.codi_emp,c.codi_cta
'@
        Read-Details -Limit 1000000 -Sink $charts -Values $batch -Fields @('chart_company_code','account_code','account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw') -Query $query.Replace('__OWNERS__',$placeholders)
        $script:stage='reading_plan_template_accounts'
        $query=@'
SELECT TOP 1000001 c.CODI_EMP,c.I_PLANOCONTAS,c.CODI_CTA,c.NOME_CTA,c.CLAS_CTA,c.TIPO_CTA,c.SITUACAO_CTA,c.DATAINATIVA_CTA
FROM bethadba.CTPLANOCONTAS c WHERE c.CODI_EMP IN (__OWNERS__)
ORDER BY c.CODI_EMP,c.I_PLANOCONTAS,c.CODI_CTA
'@
        Read-Details -Limit 1000000 -Sink $templates -Values $batch -Fields @('chart_company_code','plan_id_raw','account_code','account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw') -Query $query.Replace('__OWNERS__',$placeholders)
        $script:stage='reading_literal_nature_rules'
        $query=@'
SELECT TOP 100001 n.codi_emp,n.ordem,n.clas_cta,n.natureza,n.grupo
FROM bethadba.ctnatureza_conta n WHERE n.codi_emp IN (__OWNERS__)
ORDER BY n.codi_emp,n.ordem
'@
        Read-Details -Limit 100000 -Sink $natures -Values $batch -Fields @('chart_company_code','rule_order','classification_raw','nature_raw','group_raw') -Query $query.Replace('__OWNERS__',$placeholders)
    }
        foreach ($item in $configured) {
            $key='{0}:{1}' -f $item.chart_company_code,$item.account_code
            if ($charts.matched.ContainsKey($key) -ne ($item.catalogue_matches -eq 1)) {Reject-Details 'CATALOGUE_INCONSISTENT'}
            if ($item.catalogue_matches -eq 1) {
                foreach ($field in @('account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw')) {
                    if (-not [object]::Equals($item[$field],$charts.matched[$key][$field])) {Reject-Details 'CATALOGUE_INCONSISTENT'}
                }
            }
        }
        $chartDescriptor=Close-CatalogueSink $charts
        $templateDescriptor=Close-CatalogueSink $templates
        $natureDescriptor=Close-CatalogueSink $natures
    } finally {
        foreach ($sink in @($charts,$templates,$natures)) {if ($null -ne $sink -and $null -ne $sink.stream) {$sink.stream.Dispose();$sink.stream=$null}}
    }
    $metadata=Read-DiscoveryMetadata
    return [ordered]@{companies=$companies;observed_chart_usage=$usage;chart_owners=@($owners | ForEach-Object {[ordered]@{chart_company_code=$_}});chart_accounts=$chartDescriptor;plan_template_accounts=$templateDescriptor;nature_rules=$natureDescriptor;configured_accounts=$configured;equivalent_accounts=$equivalents;cash_accounts=$cash;bank_references=$banks;integration_account_configurations=$integrations;metadata=$metadata}
}
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Descoberta cadastral CONTAD: informe a credencial local do Dominio. Nao envie senha ao chat.'
    if ($null -eq $credential) {Reject-Details 'CANCELLED'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open()
    $builder.Clear(); $credential=$null; $timer=[Diagnostics.Stopwatch]::StartNew()
    $stage='validating_proven_columns'
    $required=@{
        geempre=@('CODI_EMP','STAT_EMP')
        ctparmto=@('CODI_EMP','CODI_PAD','COMP_PAD','I_PLANOCONTAS','CCXA_PAR','FILI_PAR')
        ctlancto=@('CODI_EMP','CODI_EMP_PLANO','FILI_LAN','DATA_LAN')
        ctplanocontas=@('CODI_EMP','CODI_CTA','I_PLANOCONTAS','NOME_CTA','CLAS_CTA','TIPO_CTA','SITUACAO_CTA','DATAINATIVA_CTA')
        ctnatureza_conta=@('CODI_EMP','ORDEM','CLAS_CTA','NATUREZA','GRUPO')
        ctcontas_equivalentes=@('CODI_EMP','CODI_EMP_PLANO','CODI_CTA')
        ctconciliacao_conta=@('CODI_EMP','CODI_EMP_PLANO','CODI_CTA')
        ctcontas=@('CODI_EMP','CODI_CTA','NOME_CTA','CLAS_CTA','TIPO_CTA','SITUACAO_CTA','DATAINATIVA_CTA')
        ctcontacaixa=@('CODI_EMP','CODI_CTA','SELE_CTA','TIPO_CONTA_CAIXA')
        ctcontacaixa_conta_bancaria=@('CODI_EMP','I_CONTA_CAIXA','I_SEQUENCIAL_CONTA_BANCARIA','AGENCIA','IDENTIFICADOR_CONTA','I_BANCO')
        ctlista_bancos_banco_central=@('I_BANCO','CODIGO_BANCO','DESCRICAO_BANCO')
        ctparmto_contas_iceberg=@('CODI_EMP','CODI_CTA','CODI_FIL','I_BANCO','DATA_INICIO_INTEGRACAO')
    }
    foreach ($table in $required.Keys) {
        Check-Deadline
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {Reject-Details 'MISSING_COLUMN'}}
    }
    $outputDirectory=Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Planos-Contas-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($outputDirectory)
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @([Security.Principal.WindowsIdentity]::GetCurrent().User,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
    }
    Set-Acl -LiteralPath $outputDirectory -AclObject $acl
    if (-not (Get-Acl -LiteralPath $outputDirectory).AreAccessRulesProtected) {Reject-Details 'PRIVATE_ACL'}
    $firstDirectory=Join-Path $outputDirectory 'read-one'; $secondDirectory=Join-Path $outputDirectory 'read-two'
    $readDirectories=@($firstDirectory,$secondDirectory)
    foreach ($directory in $readDirectories) {[void][IO.Directory]::CreateDirectory($directory)}
    $first=Read-Snapshot $firstDirectory
    $firstJson=$first | ConvertTo-Json -Depth 8 -Compress
    if ([Text.Encoding]::UTF8.GetByteCount($firstJson) -gt 8388608) {Reject-Details 'OUTPUT_LIMIT'}
    $second=Read-Snapshot $secondDirectory
    if (-not [string]::Equals($firstJson,($second | ConvertTo-Json -Depth 8 -Compress),[StringComparison]::Ordinal)) {Reject-Details 'SOURCE_CHANGED'}
    Check-Deadline
    $connection.Close()
    $stage='writing_private_report'
    $result=[ordered]@{
        version='contad-chart-discovery-v2';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o')
        decision='D-373';period_start=$periodStart.ToString('yyyy-MM-dd');period_end_exclusive=$periodEnd.ToString('yyyy-MM-dd');company_selector='A';expected_company_count=$expectedCompanyCount;two_reads_identical=$true
        company_codes_sha256=$expectedCompanyCodeSha256
        retained_portfolio_sha256='21136b2aaab37d28a85ac833001a039f6f100abde565101dbd3f8219099e1231'
        script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
        provenance=[ordered]@{
            observed_chart_usage='CTLANCTO.(codi_emp,CODI_EMP_PLANO,fili_lan,YEAR(data_lan),MONTH(data_lan)); grouped codes and counts within declared period only'
            chart_accounts='Complete CTCONTAS per union of own/CODI_PAD/observed/configured/equivalent chart owners; no name/type/status filtering'
            company_parameters='CTPARMTO literal CODI_PAD,COMP_PAD,I_PLANOCONTAS,CCXA_PAR,FILI_PAR; no active-plan or cash mapping inferred'
            plan_template_accounts='CTPLANOCONTAS literal accounts per owner/I_PLANOCONTAS; not substituted for CTCONTAS'
            nature_rules='CTNATUREZA_CONTA literal codi_emp,ordem,clas_cta,natureza,grupo; no prefix, precedence or debit/credit interpretation'
            equivalent_accounts='CTCONTAS_EQUIVALENTES.(CODI_EMP_PLANO,CODI_CTA) -> CTCONTAS.(codi_emp,codi_cta); company reference only'

            configured_accounts='CTCONCILIACAO_CONTA.(CODI_EMP_PLANO,CODI_CTA) -> CTCONTAS.(codi_emp,codi_cta)'
            bank_references='CTCONTACAIXA_CONTA_BANCARIA.(CODI_EMP,I_CONTA_CAIXA) -> CTCONTACAIXA.(codi_emp,codi_cta)'
            bank_catalogue='CTCONTACAIXA_CONTA_BANCARIA.I_BANCO -> CTLISTA_BANCOS_BANCO_CENTRAL.I_BANCO'
            bank_code_storage='CODIGO_BANCO is an integer in the retained catalog; no padding inferred.'
            integration_account_configurations=[ordered]@{
                source='CTPARMTO_CONTAS_ICEBERG'
                selected_columns=@('CODI_EMP','CODI_CTA','CODI_FIL','I_BANCO','DATA_INICIO_INTEGRACAO')
                comparison_key_columns=@('CODI_EMP','CODI_CTA','CODI_FIL','I_BANCO')
                declared_foreign_keys_verified=$false;chart_owner_mapping_inferred=$false;bank_catalogue_link_inferred=$false
                interpretation='Literal cadastral codes and date only; comparison key does not assert a database primary key.'
            }
        }
        snapshot=$first;nature_interpreted=$false;chart_owner_mapping_inferred=$false;cash_to_ledger_mapping_inferred=$false;bank_association_approved=$false;account_meanings_approved=$false
        human_reviewed=$false;financial_collection_enabled=$false;financial_values_selected=$false
        cadastral_names_and_bank_references_selected=$true;agent_configuration_read=$false;erp_write_performed=$false;uploaded=$false
    }
    $bytes=[Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Depth 10 -Compress))
    if ($bytes.Length -gt 8388608) {Reject-Details 'OUTPUT_LIMIT'}
    $uncompressed=[long]$bytes.Length+$first.chart_accounts.bytes+$first.plan_template_accounts.bytes+$first.nature_rules.bytes
    if ($uncompressed -gt 1073741824) {Reject-Details 'OUTPUT_LIMIT'}
    [IO.File]::WriteAllBytes((Join-Path $firstDirectory 'manifest.json'),$bytes)
    $path=Join-Path $outputDirectory 'planos-contas.zip'; $temporary=$path+'.partial'
    $archive=$null; $zipStream=$null
    try {
        $zipStream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        $archive=[IO.Compression.ZipArchive]::new($zipStream,[IO.Compression.ZipArchiveMode]::Create,$true)
        # Fixed root names only; no recursive directory ingestion or arbitrary paths.
        foreach ($name in @('manifest.json','chart-accounts.jsonl','plan-template-accounts.jsonl','nature-rules.jsonl')) {
            Check-Deadline
            $entry=$archive.CreateEntry($name,[IO.Compression.CompressionLevel]::Optimal)
            $inputStream=$null; $entryStream=$null
            try {
                $inputStream=[IO.File]::OpenRead((Join-Path $firstDirectory $name)); $entryStream=$entry.Open()
                $buffer=New-Object byte[] 65536
                while (($count=$inputStream.Read($buffer,0,$buffer.Length)) -gt 0) {
                    Check-Deadline; $entryStream.Write($buffer,0,$count)
                    if ($zipStream.Length -gt 134217728) {Reject-Details 'PACKAGE_LIMIT'}
                }
            } finally {if ($null -ne $inputStream) {$inputStream.Dispose()};if ($null -ne $entryStream) {$entryStream.Dispose()}}
        }
        $archive.Dispose();$archive=$null
        if ($zipStream.Length -gt 134217728) {Reject-Details 'PACKAGE_LIMIT'}
        $zipStream.Dispose();$zipStream=$null
        [IO.File]::Move($temporary,$path)
    } finally {
        if ($null -ne $archive) {$archive.Dispose()}; if ($null -ne $zipStream) {$zipStream.Dispose()}
        if ([IO.File]::Exists($temporary)) {[IO.File]::Delete($temporary)}
    }
    $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $packageBytes=(Get-Item -LiteralPath $path).Length
    # Delete both raw passes before reporting success; only the private ZIP remains.
    foreach ($directory in $readDirectories) {Remove-Item -LiteralPath $directory -Recurse -Force}
    $completed=$true
    [ordered]@{
        version='contad-chart-discovery-receipt-v2';completed=$true;companies=$first.companies.Count
        chart_owners=$first.chart_owners.Count;chart_accounts=$first.chart_accounts.rows;plan_template_accounts=$first.plan_template_accounts.rows;nature_rules=$first.nature_rules.rows;observed_chart_usage=$first.observed_chart_usage.Count;equivalent_accounts=$first.equivalent_accounts.Count
        configured_accounts=$first.configured_accounts.Count;cash_accounts=$first.cash_accounts.Count;bank_references=$first.bank_references.Count
        integration_account_configurations=$first.integration_account_configurations.Count
        missing_chart_accounts=@($first.configured_accounts | Where-Object {$_.catalogue_matches -eq 0}).Count
        missing_bank_catalogue=@($first.bank_references | Where-Object {$_.bank_catalogue_matches -eq 0}).Count
        missing_cash_keys=@($first.bank_references | Where-Object {-not $_.cash_key_present}).Count
        sha256=$sha;bytes=$packageBytes;uncompressed_bytes=$uncompressed;report_file=$path;two_reads_identical=$true;financial_values_selected=$false
        uploaded=$false;human_reviewed=$false
    } | ConvertTo-Json -Depth 3 -Compress | Write-Output
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]'; $states=New-Object 'System.Collections.Generic.List[string]'
    $exception=$_.Exception
    for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {
            foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)}}
        }
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-chart-discovery-receipt-v2';completed=$false;stage=$stage;reason_code=$reason;text_contract_failure=$textFailure;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);uploaded=$false} | ConvertTo-Json -Depth 6 -Compress | Write-Output
    Write-Error 'Descoberta nao concluido. Retorne somente este diagnostico seguro; preserve credencial e agente.' -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $connection) {$connection.Dispose()}
    if ($null -ne $builder) {$builder.Clear()}
    $credential=$null
    if (-not $completed -and $null -ne $outputDirectory -and [IO.Directory]::Exists($outputDirectory)) {Remove-Item -LiteralPath $outputDirectory -Recurse -Force}
}
