#requires -Version 5.1
<# D-348/Q-46: fixed pilot aggregates; codes and counts only, never amounts. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $stage='credential_prompt'
$families=@(
    @{name='entradas';note='ent';suffix='entp'},
    @{name='saidas';note='sai';suffix='saip'},
    @{name='servicos';note='ser';suffix='serp'}
)

# Tokens below are replaced only by the three fixed families above; no user SQL.
$parcelQuery=@'
SELECT TOP 257 p.tipo_{suffix}, p.origem_reg, COUNT(*),
 SUM(CASE WHEN p.vlor_{suffix} IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vlor_{suffix}>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vlor_{suffix}=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vlor_{suffix}<0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN h.codi_emp IS NULL THEN 1 ELSE 0 END)
FROM bethadba.ef{family}par p
LEFT JOIN bethadba.ef{family} h ON h.codi_emp=p.codi_emp AND h.codi_{note}=p.codi_{note}
WHERE p.codi_emp=? AND p.vcto_{suffix}>=? AND p.vcto_{suffix}<?
GROUP BY p.tipo_{suffix}, p.origem_reg
ORDER BY p.tipo_{suffix}, p.origem_reg
'@
$paymentQuery=@'
SELECT TOP 257 p.tipo_{suffix}, p.origempg_{suffix}, p.origem_reg, COUNT(*),
 SUM(CASE WHEN p.vpag_{suffix} IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vpag_{suffix}>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vpag_{suffix}=0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN p.vpag_{suffix}<0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN i.codi_emp IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN h.codi_emp IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.link_count IS NULL THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.link_count=1 THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.link_count>1 THEN 1 ELSE 0 END),
 SUM(COALESCE(k.link_count,0)),
 SUM(CASE WHEN k.bank_links>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.foreign_company_links>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.missing_ledger_links>0 THEN 1 ELSE 0 END),
 SUM(CASE WHEN k.outside_period_links>0 THEN 1 ELSE 0 END)
FROM bethadba.ef{family}pag p
LEFT JOIN bethadba.ef{family}par i ON i.codi_emp=p.codi_emp AND i.codi_{note}=p.codi_{note} AND i.parc_{suffix}=p.parc_{suffix}
LEFT JOIN bethadba.ef{family} h ON h.codi_emp=p.codi_emp AND h.codi_{note}=p.codi_{note}
LEFT JOIN (
 SELECT x.fili_lan, x.codi_{note}, x.pgto_{suffix}, x.tipo_{suffix}, x.parc_{suffix}, x.nropag_{suffix},
  COUNT(*) AS link_count,
  SUM(CASE WHEN l.codi_emp=212 AND l.CODI_EMP_PLANO=212 AND (l.cdeb_lan=8 OR l.ccre_lan=8) THEN 1 ELSE 0 END) AS bank_links,
  SUM(CASE WHEN x.codi_emp<>x.fili_lan THEN 1 ELSE 0 END) AS foreign_company_links,
  SUM(CASE WHEN l.nume_lan IS NULL THEN 1 ELSE 0 END) AS missing_ledger_links,
  SUM(CASE WHEN l.data_lan<? OR l.data_lan>=? THEN 1 ELSE 0 END) AS outside_period_links
 FROM bethadba.ef{family}pag_lancto x
 LEFT JOIN bethadba.ctlancto l ON l.codi_emp=x.codi_emp AND l.nume_lan=x.nume_lan
 WHERE x.fili_lan=? AND x.pgto_{suffix}>=? AND x.pgto_{suffix}<?
 GROUP BY x.fili_lan, x.codi_{note}, x.pgto_{suffix}, x.tipo_{suffix}, x.parc_{suffix}, x.nropag_{suffix}
) k ON k.fili_lan=p.codi_emp AND k.codi_{note}=p.codi_{note} AND k.pgto_{suffix}=p.pgto_{suffix} AND k.tipo_{suffix}=p.tipo_{suffix} AND k.parc_{suffix}=p.parc_{suffix} AND k.nropag_{suffix}=p.nropag_{suffix}
WHERE p.codi_emp=? AND p.pgto_{suffix}>=? AND p.pgto_{suffix}<?
GROUP BY p.tipo_{suffix}, p.origempg_{suffix}, p.origem_reg
ORDER BY p.tipo_{suffix}, p.origempg_{suffix}, p.origem_reg
'@
$parcelFields=@('type_raw','origin_reg_raw','row_count','value_null','value_positive','value_zero','value_negative','missing_header')
$paymentFields=@('type_raw','origin_raw','origin_reg_raw','row_count','value_null','value_positive','value_zero','value_negative','missing_installment','missing_header','unlinked','single_link','multiple_links','accounting_link_count','pilot_bank_linked','foreign_accounting_company_linked','missing_ledger_linked','outside_period_ledger_linked')

function Expand-Family {param([string]$Query,$Family);return $Query.Replace('{family}',$Family.name).Replace('{note}',$Family.note).Replace('{suffix}',$Family.suffix)}
function Scope-Parameters {
    return @(@{type=[System.Data.Odbc.OdbcType]::Int;value=212},
        @{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},
        @{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})
}
function Read-Aggregates {
    param([string]$Query,[object[]]$Parameters,[string[]]$Fields)
    if ($timer.Elapsed.TotalSeconds -gt 180) {throw 'Tempo de conferência excedido.'}
    $command=$connection.CreateCommand(); $reader=$null
    try {
        $command.CommandText=$Query; $command.CommandTimeout=20
        foreach ($item in $Parameters) {$p=$command.Parameters.Add('p',$item.type); $p.Value=$item.value}
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) {throw 'Contrato de retorno incompatível.'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            if ($rows.Count -ge 256 -or $timer.Elapsed.TotalSeconds -gt 180) {throw 'Perfil incompleto por limite.'}
            $row=[ordered]@{}
            for ($i=0;$i -lt $Fields.Count;$i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin @('type_raw','origin_raw','origin_reg_raw')) {throw 'Contagem ausente.'}
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($field -eq 'origin_raw') {
                    $text=([string]$value).TrimEnd([char[]]@(' '))
                    if ($text.Length -gt 1 -or $text -match '\p{C}') {throw 'Código bruto inválido.'}
                    $row[$field]=$text
                } else {
                    if ($value -is [string]) {throw 'Tipo de contagem inválido.'}
                    $number=[long]$value
                    $maximum=$(if ($field -in @('type_raw','origin_reg_raw')) {255} else {1000000})
                    if ($number -lt 0 -or $number -gt $maximum -or [decimal]$value -ne $number) {throw 'Contagem fora do limite.'}
                    $row[$field]=$number
                }
            }
            $count=$row.row_count
            if ($count -lt 1 -or ($row.value_null+$row.value_positive+$row.value_zero+$row.value_negative) -ne $count) {throw 'Partição monetária inconsistente.'}
            foreach ($field in $Fields) {
                if ($field -notin @('type_raw','origin_raw','origin_reg_raw','row_count','accounting_link_count') -and $row[$field] -gt $count) {throw 'Cobertura inconsistente.'}
            }
            if ($row.Contains('unlinked')) {
                if (($row.unlinked+$row.single_link+$row.multiple_links) -ne $count -or $row.accounting_link_count -lt ($row.single_link+2*$row.multiple_links)) {throw 'Contabilização inconsistente.'}
                foreach ($field in @('pilot_bank_linked','foreign_accounting_company_linked','missing_ledger_linked','outside_period_ledger_linked')) {
                    if ($row[$field] -gt ($count-$row.unlinked)) {throw 'Vínculo fora da cobertura.'}
                }
            }
            $rows.Add($row)
        }
        if (($rows | Measure-Object -Property row_count -Sum).Sum -gt 1000000) {throw 'Cobertura excedeu um milhão de linhas.'}
        return ,$rows.ToArray()
    } finally {if ($null -ne $reader) {$reader.Dispose()}; $command.Dispose()}
}
function Read-Profile {
    $result=New-Object 'System.Collections.Generic.List[object]'
    foreach ($family in $families) {
        $script:stage='reading_'+$family.name
        $parcels=Read-Aggregates -Query (Expand-Family $parcelQuery $family) -Parameters (Scope-Parameters) -Fields $parcelFields
        $parameters=@(@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,9,1)},@{type=[System.Data.Odbc.OdbcType]::Date;value=[DateTime]::new(2026,10,1)})+@(Scope-Parameters)+@(Scope-Parameters)
        $payments=Read-Aggregates -Query (Expand-Family $paymentQuery $family) -Parameters $parameters -Fields $paymentFields
        $result.Add([ordered]@{family=$family.name;due_installments=$parcels;payments=$payments})
    }
    return ,$result.ToArray()
}
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Contagens fiscais do piloto: informe a credencial local do Domínio. Não envie a senha ao chat.'
    if ($null -eq $credential) {throw 'Consulta cancelada.'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open(); $builder.Clear(); $credential=$null
    $timer=[Diagnostics.Stopwatch]::StartNew(); $stage='validating_columns'
    $required=@{ctlancto=@('CODI_EMP','NUME_LAN','CODI_EMP_PLANO','DATA_LAN','CDEB_LAN','CCRE_LAN')}
    foreach ($family in $families) {
        $required[('ef'+$family.name)]=@('CODI_EMP',('CODI_'+$family.note).ToUpperInvariant())
        $required[('ef'+$family.name+'par')]=@('CODI_EMP','ORIGEM_REG')+@(@(('codi_'+$family.note),('parc_'+$family.suffix),('vcto_'+$family.suffix),('tipo_'+$family.suffix),('vlor_'+$family.suffix)) | ForEach-Object {$_.ToUpperInvariant()})
        $required[('ef'+$family.name+'pag')]=@('CODI_EMP','ORIGEM_REG')+@(@(('codi_'+$family.note),('parc_'+$family.suffix),('pgto_'+$family.suffix),('tipo_'+$family.suffix),('nropag_'+$family.suffix),('vpag_'+$family.suffix),('origempg_'+$family.suffix)) | ForEach-Object {$_.ToUpperInvariant()})
        $required[('ef'+$family.name+'pag_lancto')]=@('CODI_EMP','NUME_LAN','FILI_LAN')+@(@(('codi_'+$family.note),('parc_'+$family.suffix),('pgto_'+$family.suffix),('tipo_'+$family.suffix),('nropag_'+$family.suffix)) | ForEach-Object {$_.ToUpperInvariant()})
    }
    foreach ($table in $required.Keys) {
        if ($timer.Elapsed.TotalSeconds -gt 180) {throw 'Tempo de metadados excedido.'}
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {throw 'Coluna esperada ausente.'}}
    }
    $stage='first_profile'; $first=Read-Profile
    $stage='second_profile'; $second=Read-Profile
    if (($first | ConvertTo-Json -Depth 8 -Compress) -cne ($second | ConvertTo-Json -Depth 8 -Compress)) {throw 'Fonte mudou entre leituras.'}
    if ($timer.Elapsed.TotalSeconds -gt 180) {throw 'Tempo de conferência excedido.'}
    $stage='serializing_profile'
    $result=[ordered]@{version='contad-title-profile-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');company_code=212;pilot_account_code=8;chart_company_code=212;period_start='2026-09-01';period_end_exclusive='2026-10-01';identical_read_count=2;families=$first;financial_values_selected=$false;monetary_signs_counted=$true;names_or_documents_selected=$false;payment_semantics_approved=$false;agent_configuration_read=$false;erp_write_performed=$false;financial_collection_enabled=$false}
    $json=$result | ConvertTo-Json -Depth 8 -Compress
    if ([Text.Encoding]::UTF8.GetByteCount($json) -gt 32768) {throw 'Perfil excedeu trinta e dois KiB.'}
    Write-Output $json
} catch {
    $types=New-Object 'System.Collections.Generic.List[string]'; $states=New-Object 'System.Collections.Generic.List[string]'; $native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for ($depth=0;$null -ne $exception -and $depth -lt 8;$depth++) {
        $types.Add($exception.GetType().Name)
        if ($exception -is [System.Data.Odbc.OdbcException]) {foreach ($item in @($exception.Errors | Select-Object -First 20)) {if ($item.SQLState -match '^[A-Z0-9]{5}$') {$states.Add($item.SQLState)}; $native.Add([int]$item.NativeError)}}
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-title-profile-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 5 -Compress | Write-Output
    Write-Error 'Perfil não concluído. Envie somente o JSON seguro; preserve DSN e agente.' -ErrorAction Continue
    exit 1
} finally {if ($null -ne $connection) {$connection.Dispose()}; if ($null -ne $builder) {$builder.Clear()}; $credential=$null}
