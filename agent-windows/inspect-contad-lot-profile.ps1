#requires -Version 5.1
<# D-337: scoped lot structure; only counts leave the database, no monetary amounts. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $stage='credential_prompt'

function Read-Profile {
    param([string]$Query,[object[]]$Parameters,[string[]]$Fields,[int]$Limit)
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandText=$Query; $command.CommandTimeout=40
        foreach ($item in $Parameters) {
            $parameter=$command.Parameters.Add('p',$item.type)
            $parameter.Value=$item.value
        }
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) {throw 'Contrato de retorno incompatível.'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            if ($rows.Count -ge $Limit -or $timer.Elapsed.TotalSeconds -gt 180) {throw 'Limite da conferência excedido.'}
            $row=[ordered]@{}
            for ($i=0; $i -lt $Fields.Count; $i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin @('codi_pad_raw','comp_pad_raw','i_planocontas_raw','type_raw','status_raw','lot_type_raw')) {throw 'Agregado obrigatório ausente.'}
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($field -in @('comp_pad_raw','type_raw','status_raw','lot_type_raw')) {
                    $text=([string]$value).TrimEnd([char[]]@(' '))
                    if ($text.Length -gt 1 -or $text -match '\p{C}') {throw 'Código bruto incompatível.'}
                    $row[$field]=$text
                } else {
                    if ($value -is [string]) {throw 'Tipo de agregado incompatível.'}
                    $number=[long]$value
                    if ($number -lt 0 -or $number -gt 2147483647 -or [decimal]$value -ne $number) {throw 'Agregado fora do limite.'}
                    $row[$field]=$number
                }
            }
            $rows.Add($row)
        }
        return ,$rows.ToArray()
    } finally {if ($null -ne $reader) {$reader.Dispose()}; $command.Dispose()}
}
function Integer-Parameter {param([int]$Value); return @{type=[System.Data.Odbc.OdbcType]::Int;value=$Value}}
function Pilot-Parameters {
    return @((Integer-Parameter 212),@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})
}
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Contagens dos lotes da conta8: informe a credencial local do Domínio. Não envie a senha ao chat.'
    if ($null -eq $credential) {throw 'Consulta cancelada.'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open(); $builder.Clear(); $credential=$null
    $timer=[Diagnostics.Stopwatch]::StartNew(); $stage='validating_columns'
    $required=@{ctlancto=@('CODI_EMP','CODI_LOTE','DATA_LAN','CODI_EMP_PLANO','FILI_LAN','CDEB_LAN','CCRE_LAN','VLOR_LAN');ctlanctolote=@('CODI_EMP','CODI_LOTE','TIPO')}
    foreach ($table in $required.Keys) {
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {throw 'Coluna esperada ausente.'}}
    }
    $stage='reading_bank_lot_baseline'
    $baseline=Read-Profile -Limit 1 -Fields @('bank_rows','distinct_nonnull_lots','null_lot_rows','bank_effects') -Parameters (Pilot-Parameters) -Query @'
SELECT COUNT(*), COUNT(DISTINCT codi_lote),
 COALESCE(SUM(CASE WHEN codi_lote IS NULL THEN 1 ELSE 0 END),0),
 COALESCE(SUM(CASE WHEN cdeb_lan=8 THEN 1 ELSE 0 END)+SUM(CASE WHEN ccre_lan=8 THEN 1 ELSE 0 END),0)
FROM bethadba.ctlancto
WHERE codi_emp=? AND data_lan>=? AND data_lan<? AND (cdeb_lan=8 OR ccre_lan=8)
'@
    if ($baseline.Count -ne 1 -or $baseline[0].bank_rows -gt 1000000) {throw 'Base do piloto fora do limite.'}
    $dates=@(@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})
    $parameters=@(Pilot-Parameters)+$dates+$dates+@((Integer-Parameter 212),(Integer-Parameter 212))
    $stage='reading_complete_lot_shapes'
    $groups=Read-Profile -Limit 16 -Fields @('lot_type_raw','lot_count','all_rows','period_rows','bank_rows','bank_effects','cross_period_lots','multiple_dates_lots','multiple_plans_lots','multiple_branches_lots','unbalanced_period_lots','missing_header_lots','multiple_bank_effects_lots','nonpositive_amount_rows') -Parameters $parameters -Query @'
WITH selected_lots AS (
 SELECT DISTINCT codi_lote FROM bethadba.ctlancto
 WHERE codi_emp=? AND data_lan>=? AND data_lan<? AND (cdeb_lan=8 OR ccre_lan=8)
), lot_rows AS (
 SELECT l.codi_lote, l.data_lan, l.CODI_EMP_PLANO, l.fili_lan, l.cdeb_lan, l.ccre_lan,
  CASE WHEN l.data_lan>=? AND l.data_lan<? THEN 1 ELSE 0 END AS in_period,
  CASE WHEN l.data_lan>=? AND l.data_lan<? THEN l.vlor_lan ELSE 0 END AS period_amount
 FROM bethadba.ctlancto l JOIN selected_lots s
  ON (s.codi_lote=l.codi_lote OR (s.codi_lote IS NULL AND l.codi_lote IS NULL))
 WHERE l.codi_emp=?
), grouped_lots AS (
 SELECT codi_lote, COUNT(*) AS all_rows, SUM(in_period) AS period_rows,
  SUM(CASE WHEN in_period=1 AND (cdeb_lan=8 OR ccre_lan=8) THEN 1 ELSE 0 END) AS bank_rows,
  SUM(CASE WHEN in_period=1 AND cdeb_lan=8 THEN 1 ELSE 0 END)+SUM(CASE WHEN in_period=1 AND ccre_lan=8 THEN 1 ELSE 0 END) AS bank_effects,
  COUNT(DISTINCT data_lan) AS dates_count, COUNT(DISTINCT CODI_EMP_PLANO) AS plans_count,
  COUNT(DISTINCT fili_lan) AS branches_count,
  SUM(CASE WHEN in_period=1 AND cdeb_lan<>0 THEN period_amount ELSE 0 END) AS debit_total,
  SUM(CASE WHEN in_period=1 AND ccre_lan<>0 THEN period_amount ELSE 0 END) AS credit_total,
  SUM(CASE WHEN in_period=1 AND period_amount<=0 THEN 1 ELSE 0 END) AS nonpositive_rows
 FROM lot_rows GROUP BY codi_lote
)
SELECT TOP 17 h.tipo, COUNT(*), SUM(g.all_rows), SUM(g.period_rows), SUM(g.bank_rows), SUM(g.bank_effects),
 SUM(CASE WHEN g.all_rows<>g.period_rows THEN 1 ELSE 0 END),
 SUM(CASE WHEN g.dates_count<>1 THEN 1 ELSE 0 END), SUM(CASE WHEN g.plans_count<>1 THEN 1 ELSE 0 END),
 SUM(CASE WHEN g.branches_count<>1 THEN 1 ELSE 0 END), SUM(CASE WHEN g.debit_total<>g.credit_total THEN 1 ELSE 0 END),
 SUM(CASE WHEN h.codi_lote IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN g.bank_effects<>1 THEN 1 ELSE 0 END), SUM(g.nonpositive_rows)
FROM grouped_lots g LEFT JOIN bethadba.ctlanctolote h ON h.codi_emp=? AND h.codi_lote=g.codi_lote
GROUP BY h.tipo ORDER BY h.tipo
'@
    $stage='reading_bank_branch_shapes'
    $branches=Read-Profile -Limit 16 -Fields @('branch_code_raw','bank_rows') -Parameters (Pilot-Parameters) -Query @'
SELECT TOP 17 fili_lan, COUNT(*) FROM bethadba.ctlancto
WHERE codi_emp=? AND data_lan>=? AND data_lan<? AND (cdeb_lan=8 OR ccre_lan=8)
GROUP BY fili_lan ORDER BY fili_lan
'@
    $branchTotal=[long]0
    foreach ($branch in $branches) {if ($branch.bank_rows -lt 1) {throw 'Contagem de filial incompatível.'}; $branchTotal+=$branch.bank_rows}
    $bank=[long]0; $effects=[long]0; $lots=[long]0; $allRows=[long]0; $compatible=($baseline[0].bank_rows -gt 0)
    foreach ($group in $groups) {
        $bank+=$group.bank_rows; $effects+=$group.bank_effects; $lots+=$group.lot_count; $allRows+=$group.all_rows
        if ($group.period_rows -gt $group.all_rows -or $group.bank_rows -gt $group.period_rows -or $group.lot_count -lt 1 -or $group.nonpositive_amount_rows -gt $group.period_rows) {throw 'Contagens de lote inconsistentes.'}
        foreach ($field in @('cross_period_lots','multiple_dates_lots','multiple_plans_lots','multiple_branches_lots','unbalanced_period_lots','missing_header_lots','multiple_bank_effects_lots')) {
            if ($group[$field] -gt $group.lot_count) {throw 'Contagem de grupos fora da cobertura.'}
            if ($group[$field] -gt 0) {$compatible=$false}
        }
        if ($group.nonpositive_amount_rows -gt 0) {$compatible=$false}
    }
    $expectedLots=$baseline[0].distinct_nonnull_lots+$(if ($baseline[0].null_lot_rows -gt 0) {1} else {0})
    if ($bank -ne $baseline[0].bank_rows -or $effects -ne $baseline[0].bank_effects -or $lots -ne $expectedLots -or $branchTotal -ne $bank -or $allRows -gt 1000000) {throw 'Cobertura de lotes divergente; nenhuma interpretação aprovada.'}
    if ($baseline[0].null_lot_rows -gt 0) {$compatible=$false}
    if ($timer.Elapsed.TotalSeconds -gt 180) {throw 'Tempo da conferência excedido.'}
    $stage='serializing_profile'
    $result=[ordered]@{version='contad-lot-profile-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');company_code=212;pilot_account_code=8;period_start='2026-09-01';period_end_exclusive='2026-10-01';baseline=$baseline[0];groups=$groups;bank_branch_shapes=$branches;structural_candidate_compatible=$compatible;grouping_meaning_approved=$false;amounts_used_for_internal_checks=$true;monetary_values_returned=$false;names_or_documents_returned=$false;agent_configuration_read=$false;erp_write_performed=$false;financial_collection_enabled=$false}
    $json=$result | ConvertTo-Json -Depth 7
    if ([Text.Encoding]::UTF8.GetByteCount($json) -gt 16384) {throw 'Perfil excedeu dezesseis KiB.'}
    $json | Write-Output

} catch {
    $types=New-Object 'System.Collections.Generic.List[string]'; $states=New-Object 'System.Collections.Generic.List[string]'; $native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for ($depth=0; $null -ne $exception -and $depth -lt 8; $depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)}; $native.Add([int]$item.NativeError)}}
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-lot-profile-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 | Write-Output
    Write-Error 'Conferência não concluída. Envie somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()}; if ($null -ne $builder) {$builder.Clear()}; $credential=$null}
