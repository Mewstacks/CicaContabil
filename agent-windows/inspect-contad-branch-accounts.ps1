#requires -Version 5.1
<# D-381/Q-28: entry counts per company/plan/branch/account/side for six fixed head offices; codes and counts only, no financial values. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $stage='credential_prompt'; $reason='UNCLASSIFIED'
$profileVersion='contad-branch-accounts-v1'
$periodStart=[DateTime]::new(2026,9,1)
$periodEnd=[DateTime]::new(2026,11,1)
$companyCodes=[long[]]@(25,42,129,147,280,293)
function Reject-Profile {param([string]$Code); $script:reason=$Code; throw 'Perfil recusado.'}
function Read-Counts {
    param([string]$Query)
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandText=$Query; $command.CommandTimeout=60
        foreach ($code in $companyCodes) {$p=$command.Parameters.Add('p',[System.Data.Odbc.OdbcType]::Int);$p.Value=[int]$code}
        foreach ($date in @($periodStart,$periodEnd)) {$p=$command.Parameters.Add('p',[System.Data.Odbc.OdbcType]::Date);$p.Value=$date}
        $fields=@('company_code','chart_company_code','branch_code','account_code','year','month','entry_count')
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $fields.Count) {Reject-Profile 'COLUMN_COUNT'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            if ($rows.Count -ge 20000) {Reject-Profile 'ROW_LIMIT'}
            if ($timer.Elapsed.TotalSeconds -gt 300) {Reject-Profile 'TIME_LIMIT'}
            $row=[ordered]@{}
            for ($i=0;$i -lt $fields.Count;$i++) {
                if ($reader.IsDBNull($i)) {Reject-Profile 'NULL_FIELD'}
                $value=$reader.GetValue($i)
                if ($value -is [string] -or $value -is [bool]) {Reject-Profile 'NUMBER_TYPE'}
                $number=[long]$value
                if ($number -lt 0 -or $number -gt 2147483647 -or [decimal]$value -ne $number) {Reject-Profile 'NUMBER_RANGE'}
                $row[$fields[$i]]=$number
            }
            $rows.Add($row)
        }
        return ,$rows.ToArray()
    } finally {if ($null -ne $reader) {$reader.Dispose()};$command.Dispose()}
}
function Test-Counts {
    param([object[]]$Rows)
    $seen=New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($r in $Rows) {
        if ($companyCodes -notcontains $r.company_code -or $r.chart_company_code -lt 1 -or $r.account_code -lt 1) {Reject-Profile 'SCOPE'}
        if ($r.year -lt 2026 -or $r.year -gt 2100 -or $r.month -lt 1 -or $r.month -gt 12) {Reject-Profile 'PERIOD'}
        $month=[DateTime]::new([int]$r.year,[int]$r.month,1)
        if ($month -lt $periodStart -or $month -ge $periodEnd) {Reject-Profile 'PERIOD'}
        if ($r.entry_count -lt 1 -or $r.entry_count -gt 1000000) {Reject-Profile 'COUNT'}
        $key='{0}:{1}:{2}:{3}:{4}:{5}' -f $r.company_code,$r.chart_company_code,$r.branch_code,$r.account_code,$r.year,$r.month
        if (-not $seen.Add($key)) {Reject-Profile 'DUPLICATE'}
    }
}
function Read-Snapshot {
    $scope='l.codi_emp IN (?,?,?,?,?,?) AND l.data_lan>=? AND l.data_lan<?'
    $script:stage='reading_debit_counts'
    $debit=Read-Counts -Query @"
SELECT TOP 20001 l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.cdeb_lan,YEAR(l.data_lan),MONTH(l.data_lan),COUNT(*)
FROM bethadba.ctlancto l
WHERE $scope AND l.cdeb_lan<>0
GROUP BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.cdeb_lan,YEAR(l.data_lan),MONTH(l.data_lan)
ORDER BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.cdeb_lan,YEAR(l.data_lan),MONTH(l.data_lan)
"@
    Test-Counts -Rows $debit
    $script:stage='reading_credit_counts'
    $credit=Read-Counts -Query @"
SELECT TOP 20001 l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.ccre_lan,YEAR(l.data_lan),MONTH(l.data_lan),COUNT(*)
FROM bethadba.ctlancto l
WHERE $scope AND l.ccre_lan<>0
GROUP BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.ccre_lan,YEAR(l.data_lan),MONTH(l.data_lan)
ORDER BY l.codi_emp,l.CODI_EMP_PLANO,l.fili_lan,l.ccre_lan,YEAR(l.data_lan),MONTH(l.data_lan)
"@
    Test-Counts -Rows $credit
    if (($debit.Count+$credit.Count) -gt 30000) {Reject-Profile 'TOTAL_LIMIT'}
    return [ordered]@{debit_counts=$debit;credit_counts=$credit}
}
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Filial das contas: informe a credencial local do Domínio. Não envie senha ao chat.'
    if ($null -eq $credential) {Reject-Profile 'CANCELLED'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD';$builder['UID']=$credential.UserName;$builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20;$stage='opening_connection';$connection.Open();$builder.Clear();$credential=$null
    $timer=[Diagnostics.Stopwatch]::StartNew();$stage='validating_columns'
    $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba','ctlancto',$null))
    $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq 'ctlancto'} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
    foreach ($name in @('CODI_EMP','CODI_EMP_PLANO','FILI_LAN','DATA_LAN','CDEB_LAN','CCRE_LAN')) {if ($names -notcontains $name) {Reject-Profile 'MISSING_COLUMN'}}
    $first=Read-Snapshot;$second=Read-Snapshot
    if (($first | ConvertTo-Json -Depth 6 -Compress) -cne ($second | ConvertTo-Json -Depth 6 -Compress)) {Reject-Profile 'SOURCE_CHANGED'}
    if ($timer.Elapsed.TotalSeconds -gt 300) {Reject-Profile 'TIME_LIMIT'}
    $stage='serializing_profile'
    $result=[ordered]@{version=$profileVersion;completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');period_start=$periodStart.ToString('yyyy-MM-dd');period_end_exclusive=$periodEnd.ToString('yyyy-MM-dd');company_codes=$companyCodes;snapshot=$first;two_reads_identical=$true;bank_association_approved=$false;financial_values_selected=$false;names_or_documents_selected=$false;agent_configuration_read=$false;erp_write_performed=$false;uploaded=$false}
    $json=$result | ConvertTo-Json -Depth 7 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($json)
    if ($bytes.Length -gt 4194304) {Reject-Profile 'OUTPUT_LIMIT'}
    $hasher=[Security.Cryptography.SHA256]::Create()
    try {$sha=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()} finally {$hasher.Dispose()}
    $buffer=New-Object IO.MemoryStream
    try {
        $gzip=New-Object IO.Compression.GZipStream($buffer,[IO.Compression.CompressionMode]::Compress,$true)
        try {$gzip.Write($bytes,0,$bytes.Length)} finally {$gzip.Dispose()}
        $packed=[Convert]::ToBase64String($buffer.ToArray())
    } finally {$buffer.Dispose()}
    $transfer=[ordered]@{version='contad-branch-accounts-transfer-v1';sha256=$sha;bytes=$bytes.Length;debit_rows=$first.debit_counts.Count;credit_rows=$first.credit_counts.Count;encoding='gzip-base64';data=$packed} | ConvertTo-Json -Compress
    $folder=Join-Path ([Environment]::GetFolderPath('Desktop')) 'CICA-CONTAD-Filiais'
    [void][IO.Directory]::CreateDirectory($folder)
    $path=Join-Path $folder 'filiais-contas.txt'
    [IO.File]::WriteAllText($path,$transfer,(New-Object Text.UTF8Encoding($false)))
    $transfer | Write-Output
    Write-Host ('Arquivo salvo em: '+$path)
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]';$states=New-Object 'System.Collections.Generic.List[string]';$native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)};$native.Add([int]$item.NativeError)}}
        $exception=$exception.InnerException
    }
    [ordered]@{version=$profileVersion;completed=$false;stage=$stage;reason_code=$reason;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 -Compress | Write-Output
    Write-Error 'Consulta não concluída. Retorne somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()};if ($null -ne $builder) {$builder.Clear()};$credential=$null}
