#requires -Version 5.1
<# Q-28/D-332: aggregate shapes only; never query or print document values. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if(-not [Environment]::Is64BitProcess){throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null;$builder=$null;$credential=$null;$command=$null;$reader=$null
$stage='credential_prompt'
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Diagnóstico somente leitura: informe a credencial local do Domínio. Não envie a senha ao chat.'
    if($null -eq $credential){throw 'Consulta cancelada.'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD';$builder['UID']=$credential.UserName;$builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20
    $stage='opening_connection';$connection.Open();$builder.Clear();$credential=$null
    $stage='validating_columns'
    $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba','geempre',$null))
    $names=@($columns.Rows | Where-Object { $_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq 'geempre' } | ForEach-Object { ([string]$_.COLUMN_NAME).ToUpperInvariant() })
    foreach($required in @('STAT_EMP','CGCE_EMP','TIPOI_EMP')){if($names -notcontains $required){throw 'Coluna necessária ausente.'}}
    $stage='reading_aggregate_shapes'
    $command=$connection.CreateCommand();$command.CommandTimeout=60
    $command.CommandText=@'
SELECT TOP 41 tipoi_emp, LENGTH(TRIM(cgce_emp)),
 LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', '')), COUNT(*)
FROM bethadba.geempre WHERE stat_emp = ?
GROUP BY tipoi_emp, LENGTH(TRIM(cgce_emp)),
 LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', ''))
ORDER BY tipoi_emp, LENGTH(TRIM(cgce_emp)),
 LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', ''))
'@
    [void]$command.Parameters.Add('@status',[System.Data.Odbc.OdbcType]::VarChar,16)
    $command.Parameters[0].Value='A'
    $reader=$command.ExecuteReader();$groups=New-Object 'System.Collections.Generic.List[object]';$total=[long]0
    while($reader.Read()){
        if($groups.Count -ge 40){throw 'Mais de quarenta grupos; diagnóstico incompleto.'}
        $type=$(if($reader.IsDBNull(0)){$null}else{[int]$reader.GetValue(0)})
        $original=$(if($reader.IsDBNull(1)){$null}else{[int]$reader.GetValue(1)})
        $normalized=$(if($reader.IsDBNull(2)){$null}else{[int]$reader.GetValue(2)})
        $count=[long]$reader.GetValue(3)
        if(($null -ne $type -and ($type -lt 0 -or $type -gt 255)) -or ($null -ne $original -and ($original -lt 0 -or $original -gt 14)) -or ($null -ne $normalized -and ($normalized -lt 0 -or $normalized -gt 14)) -or (($null -eq $original) -ne ($null -eq $normalized)) -or ($null -ne $normalized -and $normalized -gt $original) -or $count -lt 1 -or $count -gt 10000){throw 'Agregado fora do limite.'}
        $total+=$count;if($total -gt 10000){throw 'Mais de dez mil cadastros; diagnóstico incompleto.'}
        $groups.Add([ordered]@{source_registration_type_code=$type;trimmed_length=$original;length_without_common_separators=$normalized;count=$count})
    }
    [ordered]@{version='contad-document-profile-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o');source_status='A';company_count=$total;groups=@($groups.ToArray());registration_type_meanings_approved=$false;document_values_selected=$false;financial_values_selected=$false;agent_configuration_read=$false;erp_write_performed=$false} | ConvertTo-Json -Depth 6 | Write-Output
} catch {
    # Never emit driver messages, values, exception ToString or connection strings.
    $types=New-Object 'System.Collections.Generic.List[string]';$states=New-Object 'System.Collections.Generic.List[string]';$native=New-Object 'System.Collections.Generic.List[int]'
    $exception=$_.Exception
    for($depth=0;$null -ne $exception -and $depth -lt 8;$depth++){
        $types.Add($exception.GetType().Name)
        if($exception -is [System.Data.Odbc.OdbcException]){foreach($item in @($exception.Errors | Select-Object -First 20)){if($item.SQLState -match '^[A-Z0-9]{5}$'){$states.Add($item.SQLState)};$native.Add([int]$item.NativeError)}}
        $exception=$exception.InnerException
    }
    [ordered]@{version='contad-document-profile-v1';completed=$false;stage=$stage;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);native_error_codes=@($native.ToArray() | Select-Object -Unique)} | ConvertTo-Json -Depth 6 | Write-Output
    Write-Error 'Diagnóstico não concluído. Envie somente o JSON seguro; preserve DSN e configuração do agente.' -ErrorAction Continue
    exit 1
} finally {
    if($null -ne $reader){$reader.Dispose()};if($null -ne $command){$command.Dispose()};if($null -ne $connection){$connection.Dispose()};if($null -ne $builder){$builder.Clear()};$credential=$null
}
