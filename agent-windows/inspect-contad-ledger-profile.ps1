#requires -Version 5.1
<# D-336: fixed September pilot, raw configuration and counts only; no amounts or narratives. #>
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
                    if ($field -notin @('codi_pad_raw','comp_pad_raw','i_planocontas_raw','type_raw','status_raw')) {throw 'Agregado obrigatório ausente.'}
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($field -in @('comp_pad_raw','type_raw','status_raw')) {
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
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Conferência de contagens do piloto: informe a credencial local do Domínio. Não envie a senha ao chat.'
    if ($null -eq $credential) {throw 'Consulta cancelada.'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open(); $builder.Clear(); $credential=$null
    $timer=[Diagnostics.Stopwatch]::StartNew(); $stage='validating_columns'
    $required=@{
        geempre=@('CODI_EMP','STAT_EMP')
        ctparmto=@('CODI_EMP','CODI_PAD','COMP_PAD','I_PLANOCONTAS')
        ctlancto=@('CODI_EMP','CODI_EMP_PLANO','DATA_LAN','CDEB_LAN','CCRE_LAN')
        ctcontas=@('CODI_EMP','CODI_CTA','TIPO_CTA','SITUACAO_CTA')
    }
    foreach ($table in $required.Keys) {
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {throw 'Coluna esperada ausente.'}}
    }
    $stage='reading_pilot_configuration'
    $configuration=Read-Profile -Limit 1 -Fields @('company_code','codi_pad_raw','comp_pad_raw','i_planocontas_raw') -Parameters @((Integer-Parameter 212),@{type=[System.Data.Odbc.OdbcType]::VarChar;value='A'}) -Query @'
SELECT TOP 2 p.codi_emp, p.codi_pad, p.comp_pad, p.I_PLANOCONTAS
FROM bethadba.ctparmto p JOIN bethadba.geempre g ON g.codi_emp=p.codi_emp
WHERE p.codi_emp=? AND g.stat_emp=?
'@
    if ($configuration.Count -ne 1 -or $configuration[0].company_code -ne 212) {throw 'Configuração única do piloto ativo ausente.'}
    $stage='reading_baseline_counts'
    $baseline=Read-Profile -Limit 10 -Fields @('source_plan_company_code','entry_count','both_sides','debit_only','credit_only','neither_side','pilot_account_rows') -Parameters (Pilot-Parameters) -Query @'
SELECT TOP 11 l.CODI_EMP_PLANO, COUNT(*),
 SUM(CASE WHEN l.cdeb_lan<>0 AND l.ccre_lan<>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan<>0 AND l.ccre_lan=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan=0 AND l.ccre_lan<>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan=0 AND l.ccre_lan=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan=8 OR l.ccre_lan=8 THEN 1 ELSE 0 END)
FROM bethadba.ctlancto l
WHERE l.codi_emp=? AND l.data_lan>=? AND l.data_lan<?
GROUP BY l.CODI_EMP_PLANO ORDER BY l.CODI_EMP_PLANO
'@
    $stage='checking_candidate_account_links'
    $joined=Read-Profile -Limit 10 -Fields @('source_plan_company_code','joined_count','debit_rows','credit_rows','debit_plan_matches','credit_plan_matches','debit_own_matches','credit_own_matches') -Parameters (Pilot-Parameters) -Query @'
SELECT TOP 11 l.CODI_EMP_PLANO, COUNT(*),
 SUM(CASE WHEN l.cdeb_lan<>0 THEN 1 ELSE 0 END), SUM(CASE WHEN l.ccre_lan<>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan<>0 AND dp.codi_cta IS NOT NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.ccre_lan<>0 AND cp.codi_cta IS NOT NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.cdeb_lan<>0 AND dc.codi_cta IS NOT NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN l.ccre_lan<>0 AND cc.codi_cta IS NOT NULL THEN 1 ELSE 0 END)
FROM bethadba.ctlancto l
LEFT JOIN bethadba.ctcontas dp ON dp.codi_emp=l.CODI_EMP_PLANO AND dp.codi_cta=l.cdeb_lan
LEFT JOIN bethadba.ctcontas cp ON cp.codi_emp=l.CODI_EMP_PLANO AND cp.codi_cta=l.ccre_lan
LEFT JOIN bethadba.ctcontas dc ON dc.codi_emp=l.codi_emp AND dc.codi_cta=l.cdeb_lan
LEFT JOIN bethadba.ctcontas cc ON cc.codi_emp=l.codi_emp AND cc.codi_cta=l.ccre_lan
WHERE l.codi_emp=? AND l.data_lan>=? AND l.data_lan<?
GROUP BY l.CODI_EMP_PLANO ORDER BY l.CODI_EMP_PLANO
'@
    if ($baseline.Count -ne $joined.Count) {throw 'Fontes mudaram entre leituras.'}
    $total=[long]0
    for ($i=0; $i -lt $baseline.Count; $i++) {
        $base=$baseline[$i]; $link=$joined[$i]; $count=$base.entry_count
        if ($count -lt 1 -or $count -gt 1000000 -or $base.source_plan_company_code -ne $link.source_plan_company_code -or $count -ne $link.joined_count) {throw 'Multiplicação de linhas ou mudança entre leituras.'}
        if (($base.both_sides+$base.debit_only+$base.credit_only+$base.neither_side) -ne $count -or $base.pilot_account_rows -gt $count) {throw 'Perfil de partidas inconsistente.'}
        if ($link.debit_rows -ne ($base.both_sides+$base.debit_only) -or $link.credit_rows -ne ($base.both_sides+$base.credit_only)) {throw 'Perfil de lados divergente.'}
        foreach ($side in @('debit','credit')) {foreach ($candidate in @('plan','own')) {if ($link[($side+'_'+$candidate+'_matches')] -gt $link[($side+'_rows')]) {throw 'Correspondência fora da cobertura.'}}}
        $total+=$count
    }
    if ($total -gt 1000000) {throw 'Piloto excedeu um milhão de linhas.'}
    $owners=@(@(212)+@($configuration[0].codi_pad_raw)+@($baseline | ForEach-Object {$_.source_plan_company_code}) | Where-Object {$null -ne $_ -and $_ -gt 0} | Sort-Object -Unique)
    if ($owners.Count -gt 12) {throw 'Mais de doze candidatos ao plano.'}
    $stage='reading_raw_account_shapes'
    $placeholders=(@($owners | ForEach-Object {'?'}) -join ',')
    $shapeQuery='SELECT TOP 129 codi_emp, tipo_cta, SITUACAO_CTA, COUNT(*) FROM bethadba.ctcontas WHERE codi_emp IN ('+$placeholders+') GROUP BY codi_emp, tipo_cta, SITUACAO_CTA ORDER BY codi_emp, tipo_cta, SITUACAO_CTA'
    $shapes=Read-Profile -Limit 128 -Fields @('chart_company_code','type_raw','status_raw','account_count') -Parameters @($owners | ForEach-Object {Integer-Parameter $_}) -Query $shapeQuery
    foreach ($shape in $shapes) {if ($owners -notcontains $shape.chart_company_code -or $shape.account_count -lt 1 -or $shape.account_count -gt 1000000) {throw 'Perfil de contas fora da cobertura.'}}
    if ($timer.Elapsed.TotalSeconds -gt 180) {throw 'Tempo da conferência excedido.'}
    $stage='serializing_profile'
    $result=[ordered]@{version='contad-ledger-profile-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');company_code=212;pilot_account_code=8;period_start='2026-09-01';period_end_exclusive='2026-10-01';configuration_raw=$configuration[0];entry_count=$total;entry_shapes=$baseline;candidate_links=$joined;account_shapes=$shapes;account_type_meanings_approved=$false;chart_owner_mapping_approved=$false;financial_values_selected=$false;names_or_documents_selected=$false;agent_configuration_read=$false;erp_write_performed=$false;financial_collection_enabled=$false}
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
    [ordered]@{version='contad-ledger-profile-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 | Write-Output
    Write-Error 'Conferência não concluída. Envie somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()}; if ($null -ne $builder) {$builder.Clear()}; $credential=$null}
