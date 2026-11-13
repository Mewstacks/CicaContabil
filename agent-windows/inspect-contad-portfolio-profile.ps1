#requires -Version 5.1
<# D-356/Q-28: active-company technical codes and counts only; no financial values. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $stage='credential_prompt'; $reason='UNCLASSIFIED'
$periodStart=[DateTime]::new(2026,9,1)
$today=[DateTime]::Today; $periodEnd=[DateTime]::new($today.Year,$today.Month,1)
function Reject-Profile {param([string]$Code); $script:reason=$Code; throw 'Perfil recusado.'}
function Read-Profile {
    param([string]$Query,[object[]]$Parameters,[string[]]$Fields,[int]$Limit)
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandText=$Query; $command.CommandTimeout=40
        foreach ($item in $Parameters) {$p=$command.Parameters.Add('p',$item.type);$p.Value=$item.value}
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) {Reject-Profile 'COLUMN_COUNT'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            if ($rows.Count -ge $Limit) {Reject-Profile 'ROW_LIMIT'}
            if ($timer.Elapsed.TotalSeconds -gt 300) {Reject-Profile 'TIME_LIMIT'}
            $row=[ordered]@{}
            for ($i=0;$i -lt $Fields.Count;$i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin @('codi_pad_raw','comp_pad_raw','i_planocontas_raw','selection_raw','cash_type_raw')) {Reject-Profile 'NULL_FIELD'}
                    $row[$field]=$null;continue
                }
                $value=$reader.GetValue($i)
                if ($field -in @('comp_pad_raw','selection_raw')) {
                    $text=([string]$value).TrimEnd([char[]]@(' '))
                    if ($text -notmatch '^[\x20-\x7E]?$') {Reject-Profile 'RAW_CODE'}
                    $row[$field]=$text
                } else {
                    if ($value -is [string] -or $value -is [bool]) {Reject-Profile 'NUMBER_TYPE'}
                    $number=[long]$value
                    if ($number -lt 0 -or $number -gt 2147483647 -or [decimal]$value -ne $number) {Reject-Profile 'NUMBER_RANGE'}
                    $row[$field]=$number
                }
            }
            $rows.Add($row)
        }
        return ,$rows.ToArray()
    } finally {if ($null -ne $reader) {$reader.Dispose()};$command.Dispose()}
}
function Read-Snapshot {
    $active=@(@{type=[System.Data.Odbc.OdbcType]::VarChar;value='A'})
    $script:stage='reading_company_configuration'
    $companies=Read-Profile -Limit 500 -Parameters $active -Fields @('company_code','configuration_rows','codi_pad_raw','comp_pad_raw','i_planocontas_raw') -Query @'
SELECT TOP 501 g.codi_emp, COUNT(p.codi_emp), MIN(p.codi_pad), MIN(p.comp_pad), MIN(p.I_PLANOCONTAS)
FROM bethadba.geempre g LEFT JOIN bethadba.ctparmto p ON p.codi_emp=g.codi_emp
WHERE g.stat_emp=?
GROUP BY g.codi_emp ORDER BY g.codi_emp
'@
    $ids=New-Object 'System.Collections.Generic.HashSet[long]'
    foreach ($c in $companies) {
        if ($c.company_code -lt 1 -or -not $ids.Add($c.company_code) -or $c.configuration_rows -gt 1) {Reject-Profile 'COMPANY_CONFIGURATION'}
        if ($c.configuration_rows -eq 0 -and ($null -ne $c.codi_pad_raw -or $null -ne $c.comp_pad_raw -or $null -ne $c.i_planocontas_raw)) {Reject-Profile 'MISSING_CONFIGURATION'}
    }
    $script:stage='reading_cash_candidates'
    $cash=Read-Profile -Limit 5000 -Parameters $active -Fields @('company_code','cash_account_code','selection_raw','cash_type_raw','bank_reference_count') -Query @'
SELECT TOP 5001 c.codi_emp, c.codi_cta, c.sele_cta, c.TIPO_CONTA_CAIXA, COUNT(b.I_SEQUENCIAL_CONTA_BANCARIA)
FROM bethadba.ctcontacaixa c JOIN bethadba.geempre g ON g.codi_emp=c.codi_emp
LEFT JOIN bethadba.CTCONTACAIXA_CONTA_BANCARIA b ON b.CODI_EMP=c.codi_emp AND b.I_CONTA_CAIXA=c.codi_cta
WHERE g.stat_emp=?
GROUP BY c.codi_emp,c.codi_cta,c.sele_cta,c.TIPO_CONTA_CAIXA ORDER BY c.codi_emp,c.codi_cta
'@
    $seen=New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($c in $cash) {
        if (-not $ids.Contains($c.company_code) -or -not $seen.Add(('{0}:{1}' -f $c.company_code,$c.cash_account_code)) -or $c.bank_reference_count -gt 10000) {Reject-Profile 'CASH_COVERAGE'}
    }
    $script:stage='reading_monthly_ledger_counts'
    $parameters=@($active)+@(@{type=[System.Data.Odbc.OdbcType]::Date;value=$periodStart},@{type=[System.Data.Odbc.OdbcType]::Date;value=$periodEnd})
    $ledger=Read-Profile -Limit 10000 -Parameters $parameters -Fields @('company_code','source_plan_company_code','branch_code','year','month','entry_count','zero_debit_rows','zero_credit_rows','rows_without_lot') -Query @'
SELECT TOP 10001 l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan),COUNT(*),
 SUM(CASE WHEN l.cdeb_lan=0 THEN 1 ELSE 0 END),SUM(CASE WHEN l.ccre_lan=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.codi_lote IS NULL THEN 1 ELSE 0 END)
FROM bethadba.ctlancto l JOIN bethadba.geempre g ON g.codi_emp=l.codi_emp
WHERE g.stat_emp=? AND l.data_lan>=? AND l.data_lan<?
GROUP BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan)
ORDER BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,YEAR(l.data_lan),MONTH(l.data_lan)
'@
    $seen.Clear();$total=[long]0
    foreach ($l in $ledger) {
        if (-not $ids.Contains($l.company_code) -or $l.source_plan_company_code -lt 1 -or $l.year -lt 2026 -or $l.year -gt 2100 -or $l.month -lt 1 -or $l.month -gt 12) {Reject-Profile 'LEDGER_SCOPE'}
        $month=[DateTime]::new($l.year,$l.month,1)
        $key='{0}:{1}:{2}:{3}:{4}' -f $l.company_code,$l.source_plan_company_code,$l.branch_code,$l.year,$l.month
        if ($month -lt $periodStart -or $month -ge $periodEnd -or -not $seen.Add($key) -or $l.entry_count -lt 1 -or $l.entry_count -gt 1000000) {Reject-Profile 'LEDGER_COVERAGE'}
        foreach ($f in @('zero_debit_rows','zero_credit_rows','rows_without_lot')) {if ($l[$f] -gt $l.entry_count) {Reject-Profile 'LEDGER_COUNT'}}
        $total+=$l.entry_count
    }
    if ($total -gt 5000000) {Reject-Profile 'TOTAL_LIMIT'}
    return [ordered]@{companies=$companies;cash_candidates=$cash;monthly_ledger=$ledger}
}
try {
    if ($periodEnd -le $periodStart -or $periodEnd -gt $periodStart.AddMonths(24)) {Reject-Profile 'PERIOD_LIMIT'}
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Cobertura financeira: informe a credencial local do Domínio. Não envie senha ao chat.'
    if ($null -eq $credential) {Reject-Profile 'CANCELLED'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD';$builder['UID']=$credential.UserName;$builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20;$stage='opening_connection';$connection.Open();$builder.Clear();$credential=$null
    $timer=[Diagnostics.Stopwatch]::StartNew();$stage='validating_columns'
    $required=@{geempre=@('CODI_EMP','STAT_EMP');ctparmto=@('CODI_EMP','CODI_PAD','COMP_PAD','I_PLANOCONTAS');ctcontacaixa=@('CODI_EMP','CODI_CTA','SELE_CTA','TIPO_CONTA_CAIXA');ctcontacaixa_conta_bancaria=@('CODI_EMP','I_CONTA_CAIXA','I_SEQUENCIAL_CONTA_BANCARIA');ctlancto=@('CODI_EMP','CODI_EMP_PLANO','FILI_LAN','DATA_LAN','CDEB_LAN','CCRE_LAN','CODI_LOTE')}
    foreach ($table in $required.Keys) {
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {Reject-Profile 'MISSING_COLUMN'}}
    }
    $first=Read-Snapshot;$second=Read-Snapshot
    if (($first | ConvertTo-Json -Depth 7 -Compress) -cne ($second | ConvertTo-Json -Depth 7 -Compress)) {Reject-Profile 'SOURCE_CHANGED'}
    if ($timer.Elapsed.TotalSeconds -gt 300) {Reject-Profile 'TIME_LIMIT'}
    $stage='serializing_profile'
    $result=[ordered]@{version='contad-portfolio-profile-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');period_start=$periodStart.ToString('yyyy-MM-dd');period_end_exclusive=$periodEnd.ToString('yyyy-MM-dd');company_selector='A';snapshot=$first;two_reads_identical=$true;account_meanings_approved=$false;chart_owner_mapping_approved=$false;bank_association_approved=$false;financial_values_selected=$false;names_or_documents_selected=$false;agent_configuration_read=$false;erp_write_performed=$false;financial_collection_enabled=$false;uploaded=$false}
    $json=$result | ConvertTo-Json -Depth 8 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($json)
    if ($bytes.Length -gt 4194304) {Reject-Profile 'OUTPUT_LIMIT'}
    if ($bytes.Length -le 16384) {$json | Write-Output} else {
        $hasher=[Security.Cryptography.SHA256]::Create()
        try {$sha=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()} finally {$hasher.Dispose()}
        $buffer=New-Object IO.MemoryStream
        try {
            $gzip=New-Object IO.Compression.GZipStream($buffer,[IO.Compression.CompressionMode]::Compress,$true)
            try {$gzip.Write($bytes,0,$bytes.Length)} finally {$gzip.Dispose()}
            $packed=[Convert]::ToBase64String($buffer.ToArray())
        } finally {$buffer.Dispose()}
        [ordered]@{version='contad-portfolio-profile-transfer-v1';sha256=$sha;bytes=$bytes.Length;encoding='gzip-base64';data=$packed} | ConvertTo-Json -Compress | Write-Output
    }
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]';$states=New-Object 'System.Collections.Generic.List[string]';$native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)};$native.Add([int]$item.NativeError)}}
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-portfolio-profile-v1';completed=$false;stage=$stage;reason_code=$reason;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 -Compress | Write-Output
    Write-Error 'Conferência não concluída. Retorne somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()};if ($null -ne $builder) {$builder.Clear()};$credential=$null}
