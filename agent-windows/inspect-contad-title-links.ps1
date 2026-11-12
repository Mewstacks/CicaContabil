#requires -Version 5.1
<# D-350/Q-46: payment/ledger/lot structural counts only; no monetary columns. #>
[CmdletBinding()]
param([switch]$Compact)
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $stage='credential_prompt'; $diagnosticCode='UNCLASSIFIED'
$families=@(@{name='entradas';note='ent';suffix='entp'},@{name='saidas';note='sai';suffix='saip'},@{name='servicos';note='ser';suffix='serp'})

$coverageQuery=@'
WITH scoped_payments AS (
 SELECT p.codi_emp, p.codi_{note}, p.parc_{suffix}, p.pgto_{suffix}, p.tipo_{suffix}, p.nropag_{suffix}, p.origempg_{suffix}, p.origem_reg
 FROM bethadba.ef{family}pag p
 WHERE p.codi_emp=? AND p.pgto_{suffix}>=? AND p.pgto_{suffix}<?
), linked_rows AS (
 SELECT p.*, x.codi_emp AS ledger_company, x.nume_lan AS linked_entry,
  l.nume_lan AS found_entry, l.codi_lote, l.CODI_EMP_PLANO, l.cdeb_lan, l.ccre_lan
 FROM scoped_payments p
 LEFT JOIN bethadba.ef{family}pag_lancto x ON x.fili_lan=p.codi_emp AND x.codi_{note}=p.codi_{note} AND x.parc_{suffix}=p.parc_{suffix} AND x.pgto_{suffix}=p.pgto_{suffix} AND x.tipo_{suffix}=p.tipo_{suffix} AND x.nropag_{suffix}=p.nropag_{suffix}
 LEFT JOIN bethadba.ctlancto l ON l.codi_emp=x.codi_emp AND l.nume_lan=x.nume_lan
), selected_lots AS (
 SELECT DISTINCT ledger_company, codi_lote FROM linked_rows WHERE found_entry IS NOT NULL AND codi_lote IS NOT NULL
), bank_rows AS (
 SELECT b.codi_emp, b.codi_lote, b.cdeb_lan, b.ccre_lan,
  CASE WHEN b.data_lan>=? AND b.data_lan<? THEN 1 ELSE 0 END AS in_period
 FROM bethadba.ctlancto b JOIN selected_lots s ON s.ledger_company=b.codi_emp AND s.codi_lote=b.codi_lote
 WHERE b.codi_emp=212 AND b.CODI_EMP_PLANO=212 AND (b.cdeb_lan=8 OR b.ccre_lan=8)
), bank_lots AS (
 SELECT codi_emp, codi_lote, SUM(in_period) AS period_rows, SUM(1-in_period) AS outside_rows,
  SUM(CASE WHEN in_period=1 AND cdeb_lan=8 THEN 1 ELSE 0 END)+SUM(CASE WHEN in_period=1 AND ccre_lan=8 THEN 1 ELSE 0 END) AS period_effects
 FROM bank_rows GROUP BY codi_emp, codi_lote
), flagged_payments AS (
 SELECT r.codi_emp, r.codi_{note}, r.parc_{suffix}, r.pgto_{suffix}, r.tipo_{suffix}, r.nropag_{suffix}, r.origempg_{suffix}, r.origem_reg,
  COUNT(r.linked_entry) AS link_count,
  SUM(CASE WHEN r.ledger_company=212 AND r.CODI_EMP_PLANO=212 AND (r.cdeb_lan=8 OR r.ccre_lan=8) THEN 1 ELSE 0 END) AS direct_bank,
  SUM(CASE WHEN b.period_rows>0 THEN 1 ELSE 0 END) AS same_lot_bank,
  COUNT(DISTINCT CASE WHEN b.period_rows>0 THEN r.codi_lote ELSE NULL END) AS bank_lot_count,
  SUM(CASE WHEN b.period_rows>1 THEN 1 ELSE 0 END) AS multiple_bank_rows,
  SUM(CASE WHEN b.period_effects>1 THEN 1 ELSE 0 END) AS multiple_bank_effects,
  SUM(CASE WHEN b.period_rows>0 AND b.outside_rows>0 THEN 1 ELSE 0 END) AS cross_period_bank,
  SUM(CASE WHEN b.period_rows=0 AND b.outside_rows>0 THEN 1 ELSE 0 END) AS outside_only_bank,
  SUM(CASE WHEN r.linked_entry IS NOT NULL AND r.found_entry IS NULL THEN 1 ELSE 0 END) AS missing_ledger,
  SUM(CASE WHEN r.found_entry IS NOT NULL AND r.codi_lote IS NULL THEN 1 ELSE 0 END) AS null_lot,
  SUM(CASE WHEN r.found_entry IS NOT NULL AND r.codi_lote IS NOT NULL AND h.codi_lote IS NULL THEN 1 ELSE 0 END) AS missing_header,
  SUM(CASE WHEN r.ledger_company<>r.codi_emp THEN 1 ELSE 0 END) AS foreign_company
 FROM linked_rows r
 LEFT JOIN bank_lots b ON b.codi_emp=r.ledger_company AND b.codi_lote=r.codi_lote
 LEFT JOIN bethadba.ctlanctolote h ON h.codi_emp=r.ledger_company AND h.codi_lote=r.codi_lote
 GROUP BY r.codi_emp, r.codi_{note}, r.parc_{suffix}, r.pgto_{suffix}, r.tipo_{suffix}, r.nropag_{suffix}, r.origempg_{suffix}, r.origem_reg
)
SELECT TOP 257 tipo_{suffix}, origempg_{suffix}, origem_reg, COUNT(*),
 SUM(CASE WHEN link_count=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN direct_bank>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN same_lot_bank>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN bank_lot_count>1 THEN 1 ELSE 0 END),
 SUM(CASE WHEN multiple_bank_rows>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN multiple_bank_effects>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN cross_period_bank>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN outside_only_bank>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN missing_ledger>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN null_lot>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN missing_header>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN foreign_company>0 THEN 1 ELSE 0 END)
FROM flagged_payments
GROUP BY tipo_{suffix}, origempg_{suffix}, origem_reg
ORDER BY tipo_{suffix}, origempg_{suffix}, origem_reg
'@
$accountQuery=@'
SELECT TOP 1025 p.tipo_{suffix}, x.codi_emp, l.CODI_EMP_PLANO, l.cdeb_lan, l.ccre_lan,
 COUNT(*), COUNT(DISTINCT l.nume_lan)
FROM bethadba.ef{family}pag p
JOIN bethadba.ef{family}pag_lancto x ON x.fili_lan=p.codi_emp AND x.codi_{note}=p.codi_{note} AND x.parc_{suffix}=p.parc_{suffix} AND x.pgto_{suffix}=p.pgto_{suffix} AND x.tipo_{suffix}=p.tipo_{suffix} AND x.nropag_{suffix}=p.nropag_{suffix}
LEFT JOIN bethadba.ctlancto l ON l.codi_emp=x.codi_emp AND l.nume_lan=x.nume_lan
WHERE p.codi_emp=? AND p.pgto_{suffix}>=? AND p.pgto_{suffix}<?
GROUP BY p.tipo_{suffix}, x.codi_emp, l.CODI_EMP_PLANO, l.cdeb_lan, l.ccre_lan
ORDER BY p.tipo_{suffix}, x.codi_emp, l.CODI_EMP_PLANO, l.cdeb_lan, l.ccre_lan
'@
$coverageFields=@('type_raw','origin_raw','origin_reg_raw','row_count','unlinked','direct_bank','same_lot_bank','multiple_bank_lots','multiple_bank_rows','multiple_bank_effects','cross_period_bank_lot','outside_only_bank_lot','missing_ledger','null_lot','missing_lot_header','foreign_accounting_company')
$accountFields=@('type_raw','ledger_company_raw','chart_company_raw','debit_account_raw','credit_account_raw','link_row_count','distinct_entry_count')

function Reject-Profile {param([string]$Code);$script:diagnosticCode=$Code;throw 'Perfil recusado por regra fixa.'}
function Scope-Parameters {
 return @(@{type=[System.Data.Odbc.OdbcType]::Int;value=212},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})
}
function Expand-Family {param([string]$Query,$Family);return $Query.Replace('{family}',$Family.name).Replace('{note}',$Family.note).Replace('{suffix}',$Family.suffix)}
function Read-SafeRows {
 param([string]$Query,[object[]]$Parameters,[string[]]$Fields,[int]$Limit,[bool]$Coverage)
 if ($timer.Elapsed.TotalSeconds -gt 180) {Reject-Profile 'TIME_LIMIT'}
 $command=$connection.CreateCommand(); $reader=$null
 try {
  $command.CommandText=$Query; $command.CommandTimeout=20
  foreach ($item in $Parameters) {$p=$command.Parameters.Add('p',$item.type); $p.Value=$item.value}
  $reader=$command.ExecuteReader()
  if ($reader.FieldCount -ne $Fields.Count) {Reject-Profile 'FIELD_COUNT'}
  $rows=New-Object 'System.Collections.Generic.List[object]'; $total=[long]0
  while ($reader.Read()) {
   if ($rows.Count -ge $Limit) {
    if ($Coverage) {Reject-Profile 'COVERAGE_GROUP_LIMIT'} else {Reject-Profile 'ACCOUNT_GROUP_LIMIT'}
   }
   if ($timer.Elapsed.TotalSeconds -gt 180) {Reject-Profile 'TIME_LIMIT'}
   $row=[ordered]@{}
   for ($i=0;$i -lt $Fields.Count;$i++) {
    $field=$Fields[$i]
    if ($reader.IsDBNull($i)) {
     if ($field -notin @('type_raw','origin_raw','origin_reg_raw','chart_company_raw','debit_account_raw','credit_account_raw')) {Reject-Profile 'REQUIRED_COUNT_NULL'}
     $row[$field]=$null; continue
    }
    $value=$reader.GetValue($i)
    if ($field -eq 'origin_raw') {
     $text=([string]$value).TrimEnd([char[]]@(' '))
     if ($text.Length -gt 1 -or $text -match '\p{C}') {Reject-Profile 'RAW_CODE_FORMAT'}
     $row[$field]=$text
    } else {
     if ($value -is [string]) {Reject-Profile 'NUMERIC_TYPE'}
     $number=[long]$value
     $max=$(if ($field -in @('type_raw','origin_reg_raw')) {255} elseif ($field.EndsWith('_raw')) {2147483647} else {1000000})
     if ($number -lt 0 -or $number -gt $max -or [decimal]$value -ne $number) {Reject-Profile 'NUMERIC_RANGE'}
     $row[$field]=$number
    }
   }
   if ($Coverage) {
    $count=$row.row_count
    if ($count -lt 1) {Reject-Profile 'EMPTY_GROUP'}
    foreach ($field in $Fields) {if ($field -notin @('type_raw','origin_raw','origin_reg_raw','row_count') -and $row[$field] -gt $count) {Reject-Profile 'COVERAGE_COUNT'}}
    foreach ($field in @('direct_bank','same_lot_bank','outside_only_bank_lot','missing_ledger','null_lot','missing_lot_header','foreign_accounting_company')) {if ($row[$field] -gt ($count-$row.unlinked)) {Reject-Profile 'LINK_COVERAGE'}}
    foreach ($field in @('multiple_bank_lots','multiple_bank_rows','multiple_bank_effects','cross_period_bank_lot')) {if ($row[$field] -gt $row.same_lot_bank) {Reject-Profile 'LOT_COVERAGE'}}
   } else {
    $count=$row.link_row_count
    if ($count -lt 1 -or $row.distinct_entry_count -gt $count -or $row.ledger_company_raw -lt 1) {Reject-Profile 'ACCOUNT_SHAPE'}
   }
   $total+=$count
   if ($total -gt 1000000) {Reject-Profile 'ROW_LIMIT'}
   $rows.Add($row)
  }
  return ,$rows.ToArray()
 } finally {if ($null -ne $reader) {$reader.Dispose()}; $command.Dispose()}
}
function Read-Snapshot {
 $result=New-Object 'System.Collections.Generic.List[object]'
 foreach ($family in $families) {
  $script:stage='reading_'+$family.name+'_coverage'
  $parameters=@(Scope-Parameters)+@(@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})
  $coverage=Read-SafeRows -Query (Expand-Family $coverageQuery $family) -Parameters $parameters -Fields $coverageFields -Limit 256 -Coverage $true
  $script:stage='reading_'+$family.name+'_account_shapes'
  $accounts=Read-SafeRows -Query (Expand-Family $accountQuery $family) -Parameters (Scope-Parameters) -Fields $accountFields -Limit 1024 -Coverage $false
  $result.Add([ordered]@{family=$family.name;payment_coverage=$coverage;linked_account_shapes=$accounts})
 }
 return ,$result.ToArray()
}
try {
 $credential=Get-Credential -UserName 'EXTERNO' -Message 'Vínculos estruturais do piloto: informe a credencial local do Domínio. Não envie a senha ao chat.'
 if ($null -eq $credential) {Reject-Profile 'CANCELLED'}
 $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
 $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
 $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
 $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open(); $builder.Clear(); $credential=$null
 $timer=[Diagnostics.Stopwatch]::StartNew(); $stage='validating_columns'
 $required=@{ctlancto=@('CODI_EMP','NUME_LAN','CODI_LOTE','CODI_EMP_PLANO','DATA_LAN','CDEB_LAN','CCRE_LAN');ctlanctolote=@('CODI_EMP','CODI_LOTE')}
 foreach ($family in $families) {
  $keys=@('CODI_EMP')+@(@(('codi_'+$family.note),('parc_'+$family.suffix),('pgto_'+$family.suffix),('tipo_'+$family.suffix),('nropag_'+$family.suffix)) | ForEach-Object {$_.ToUpperInvariant()})
  $required[('ef'+$family.name+'pag')]=$keys+@('ORIGEM_REG',('ORIGEMPG_'+$family.suffix).ToUpperInvariant())
  $required[('ef'+$family.name+'pag_lancto')]=$keys+@('NUME_LAN','FILI_LAN')
 }
 foreach ($table in $required.Keys) {
  if ($timer.Elapsed.TotalSeconds -gt 180) {Reject-Profile 'METADATA_TIME_LIMIT'}
  $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
  $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
  foreach ($name in $required[$table]) {if ($names -notcontains $name) {Reject-Profile 'MISSING_COLUMN'}}
 }
 $stage='first_snapshot'; $first=Read-Snapshot
 $stage='second_snapshot'; $second=Read-Snapshot
 if (($first | ConvertTo-Json -Depth 8 -Compress) -cne ($second | ConvertTo-Json -Depth 8 -Compress)) {Reject-Profile 'SOURCE_CHANGED'}
 if ($timer.Elapsed.TotalSeconds -gt 180) {Reject-Profile 'TIME_LIMIT'}
 $stage='serializing_snapshot'
 $result=[ordered]@{version='contad-title-links-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');company_code=212;pilot_account_code=8;chart_company_code=212;period_start='2026-09-01';period_end_exclusive='2026-10-01';identical_read_count=2;families=$first;monetary_columns_selected=$false;names_or_documents_selected=$false;lot_membership_proves_bank_allocation=$false;payment_semantics_approved=$false;agent_configuration_read=$false;erp_write_performed=$false;financial_collection_enabled=$false}
 $json=$result | ConvertTo-Json -Depth 8 -Compress
 $bytes=[Text.Encoding]::UTF8.GetBytes($json)
 if ($bytes.Length -gt 4194304) {Reject-Profile 'BYTE_LIMIT'}
 if ($Compact) {
  $crypto=[Security.Cryptography.SHA256]::Create()
  try {$sha=[BitConverter]::ToString($crypto.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()} finally {$crypto.Dispose()}
  $buffer=New-Object IO.MemoryStream
  $gzip=New-Object IO.Compression.GZipStream($buffer,[IO.Compression.CompressionMode]::Compress,$true)
  try {$gzip.Write($bytes,0,$bytes.Length)} finally {$gzip.Dispose()}
  try {$packed=[Convert]::ToBase64String($buffer.ToArray())} finally {$buffer.Dispose()}
  [ordered]@{version='contad-title-links-transfer-v1';sha256=$sha;bytes=$bytes.Length;encoding='gzip-base64';data=$packed} | ConvertTo-Json -Compress | Write-Output
 } else {Write-Output $json}
} catch {
 $types=New-Object 'System.Collections.Generic.List[string]'; $states=New-Object 'System.Collections.Generic.List[string]'; $native=New-Object 'System.Collections.Generic.List[int]'
 $exception=$_.Exception
 for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
  $types.Add($exception.GetType().Name)
  if ($exception -is [System.Data.Odbc.OdbcException]) {foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)}; $native.Add([int]$item.NativeError)}}
  $exception=$exception.InnerException
 }
 [ordered]@{version='contad-title-links-v1';completed=$false;stage=$stage;reason_code=$diagnosticCode;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 -Compress | Write-Output
 Write-Error 'Vínculos não conferidos. Envie somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
 exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()}; if ($null -ne $builder) {$builder.Clear()}; $credential=$null}
