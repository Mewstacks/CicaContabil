#requires -Version 5.1
<# D-372/Q-28. Fixed cadastral SELECTs only. Never reads agent.config, writes ERP,
   queries transactions or infers a cash-to-ledger mapping. Private JSON stays local. #>
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {throw 'Use Windows PowerShell de 64 bits.'}
Add-Type -AssemblyName System.Data
$connection=$null; $builder=$null; $credential=$null; $timer=$null
$stage='credential_prompt'; $reason='UNCLASSIFIED'; $outputDirectory=$null
$expectedCompanyCount=146
$expectedCompanyCodeSha256='4ab91c9e80c1b20275c5878b3ec3f844deec7f6b155d94fdb90b79fbf6626f55'
function Reject-Details {param([string]$Code); $script:reason=$Code; throw 'Complemento cadastral recusado.'}
function Check-Deadline {
    if ($null -ne $timer -and $timer.Elapsed.TotalSeconds -gt 300) {Reject-Details 'TIME_LIMIT'}
}
function Read-Details {
    param([string]$Query,[string[]]$Fields,[int]$Limit)
    Check-Deadline
    $command=$connection.CreateCommand(); $reader=$null
    $textLimits=@{account_name_raw=150;classification_raw=20;account_type_raw=1;account_status_raw=1;selection_raw=1;agency_raw=10;account_identifier_raw=30;bank_name_raw=100}
    $nullable=@('catalogue_account_code','account_name_raw','classification_raw','account_type_raw','account_status_raw','inactive_on_raw','selection_raw','cash_type_raw','bank_id_raw','bank_catalogue_id','bank_code_raw','bank_name_raw')
    try {
        $command.CommandText=$Query; $command.CommandTimeout=40
        $parameter=$command.Parameters.Add('p',[System.Data.Odbc.OdbcType]::VarChar,1)
        $parameter.Value='A'
        $reader=$command.ExecuteReader()
        if ($reader.FieldCount -ne $Fields.Count) {Reject-Details 'COLUMN_COUNT'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        while ($reader.Read()) {
            Check-Deadline
            if ($rows.Count -ge $Limit) {Reject-Details 'ROW_LIMIT'}
            $row=[ordered]@{}
            for ($i=0;$i -lt $Fields.Count;$i++) {
                $field=$Fields[$i]
                if ($reader.IsDBNull($i)) {
                    if ($field -notin $nullable) {Reject-Details 'NULL_FIELD'}
                    $row[$field]=$null; continue
                }
                $value=$reader.GetValue($i)
                if ($textLimits.ContainsKey($field)) {
                    if ($value -isnot [string] -or $value.Length -gt $textLimits[$field] -or $value -match '\p{C}') {Reject-Details 'TEXT_CONTRACT'}
                    # Do not trim/pad strings or parse banking identifiers as numbers.
                    $row[$field]=$value
                } elseif ($field -eq 'inactive_on_raw') {
                    if ($value -isnot [DateTime] -or $value.TimeOfDay -ne [TimeSpan]::Zero) {Reject-Details 'DATE_CONTRACT'}
                    $row[$field]=$value.ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
                } else {
                    if ($value -is [string] -or $value -is [bool]) {Reject-Details 'NUMBER_TYPE'}
                    $number=[long]$value
                    if ($number -lt 0 -or $number -gt 2147483647 -or [decimal]$value -ne $number) {Reject-Details 'NUMBER_RANGE'}
                    $row[$field]=$number
                }
            }
            $rows.Add($row)
        }
        Check-Deadline
        return ,$rows.ToArray()
    } finally {if ($null -ne $reader) {$reader.Dispose()}; $command.Dispose()}
}
function Read-Snapshot {
    $script:stage='reading_active_company_codes'
    $companies=Read-Details -Limit 500 -Fields @('company_code') -Query @'
SELECT TOP 501 g.codi_emp
FROM bethadba.geempre g
WHERE g.stat_emp=?
ORDER BY g.codi_emp
'@
    $companyIds=New-Object 'System.Collections.Generic.HashSet[long]'
    foreach ($company in $companies) {
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
    return [ordered]@{companies=$companies;configured_accounts=$configured;cash_accounts=$cash;bank_references=$banks}
}
try {
    $credential=Get-Credential -UserName 'EXTERNO' -Message 'Complemento cadastral CONTAD: informe a credencial local do Dominio. Nao envie senha ao chat.'
    if ($null -eq $credential) {Reject-Details 'CANCELLED'}
    $builder=New-Object System.Data.Odbc.OdbcConnectionStringBuilder
    $builder['DSN']='CICA_CONTAD'; $builder['UID']=$credential.UserName; $builder['PWD']=$credential.GetNetworkCredential().Password
    $connection=New-Object System.Data.Odbc.OdbcConnection -ArgumentList $builder.ConnectionString
    $connection.ConnectionTimeout=20; $stage='opening_connection'; $connection.Open()
    $builder.Clear(); $credential=$null; $timer=[Diagnostics.Stopwatch]::StartNew()
    $stage='validating_proven_columns'
    $required=@{
        geempre=@('CODI_EMP','STAT_EMP')
        ctconciliacao_conta=@('CODI_EMP','CODI_EMP_PLANO','CODI_CTA')
        ctcontas=@('CODI_EMP','CODI_CTA','NOME_CTA','CLAS_CTA','TIPO_CTA','SITUACAO_CTA','DATAINATIVA_CTA')
        ctcontacaixa=@('CODI_EMP','CODI_CTA','SELE_CTA','TIPO_CONTA_CAIXA')
        ctcontacaixa_conta_bancaria=@('CODI_EMP','I_CONTA_CAIXA','I_SEQUENCIAL_CONTA_BANCARIA','AGENCIA','IDENTIFICADOR_CONTA','I_BANCO')
        ctlista_bancos_banco_central=@('I_BANCO','CODIGO_BANCO','DESCRICAO_BANCO')
    }
    foreach ($table in $required.Keys) {
        Check-Deadline
        $columns=$connection.GetSchema('Columns',[string[]]@($null,'bethadba',$table,$null))
        $names=@($columns.Rows | Where-Object {$_.TABLE_SCHEM -ieq 'bethadba' -and $_.TABLE_NAME -ieq $table} | ForEach-Object {([string]$_.COLUMN_NAME).ToUpperInvariant()})
        foreach ($name in $required[$table]) {if ($names -notcontains $name) {Reject-Details 'MISSING_COLUMN'}}
    }
    $first=Read-Snapshot; $second=Read-Snapshot
    $firstJson=$first | ConvertTo-Json -Depth 8 -Compress
    if ($firstJson -cne ($second | ConvertTo-Json -Depth 8 -Compress)) {Reject-Details 'SOURCE_CHANGED'}
    Check-Deadline
    $connection.Close()
    $stage='writing_private_report'
    $result=[ordered]@{
        version='contad-account-details-v1';completed=$true;observed_at_utc=[DateTime]::UtcNow.ToString('o')
        decision='D-372';company_selector='A';expected_company_count=$expectedCompanyCount;two_reads_identical=$true
        company_codes_sha256=$expectedCompanyCodeSha256
        retained_portfolio_sha256='21136b2aaab37d28a85ac833001a039f6f100abde565101dbd3f8219099e1231'
        script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
        provenance=[ordered]@{
            configured_accounts='CTCONCILIACAO_CONTA.(CODI_EMP_PLANO,CODI_CTA) -> CTCONTAS.(codi_emp,codi_cta)'
            bank_references='CTCONTACAIXA_CONTA_BANCARIA.(CODI_EMP,I_CONTA_CAIXA) -> CTCONTACAIXA.(codi_emp,codi_cta)'
            bank_catalogue='CTCONTACAIXA_CONTA_BANCARIA.I_BANCO -> CTLISTA_BANCOS_BANCO_CENTRAL.I_BANCO'
            bank_code_storage='CODIGO_BANCO is an integer in the retained catalog; no padding inferred.'
        }
        snapshot=$first;cash_to_ledger_mapping_inferred=$false;bank_association_approved=$false;account_meanings_approved=$false
        human_reviewed=$false;financial_collection_enabled=$false;financial_values_selected=$false
        cadastral_names_and_bank_references_selected=$true;agent_configuration_read=$false;erp_write_performed=$false;uploaded=$false
    }
    $bytes=[Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Depth 10 -Compress))
    if ($bytes.Length -gt 4194304) {Reject-Details 'OUTPUT_LIMIT'}
    $outputDirectory=Join-Path ([Environment]::GetFolderPath('UserProfile')) ('Downloads\CICA-CONTAD-Contas-Detalhes-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($outputDirectory)
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @([Security.Principal.WindowsIdentity]::GetCurrent().User,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
    }
    Set-Acl -LiteralPath $outputDirectory -AclObject $acl
    if (-not (Get-Acl -LiteralPath $outputDirectory).AreAccessRulesProtected) {Reject-Details 'PRIVATE_ACL'}
    $path=Join-Path $outputDirectory 'contas-detalhes.json'
    $temporary=$path+'.partial'
    try {[IO.File]::WriteAllBytes($temporary,$bytes); [IO.File]::Move($temporary,$path)}
    finally {if ([IO.File]::Exists($temporary)) {[IO.File]::Delete($temporary)}}
    $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    [ordered]@{
        version='contad-account-details-receipt-v1';completed=$true;companies=$first.companies.Count
        configured_accounts=$first.configured_accounts.Count;cash_accounts=$first.cash_accounts.Count;bank_references=$first.bank_references.Count
        missing_chart_accounts=@($first.configured_accounts | Where-Object {$_.catalogue_matches -eq 0}).Count
        missing_bank_catalogue=@($first.bank_references | Where-Object {$_.bank_catalogue_matches -eq 0}).Count
        missing_cash_keys=@($first.bank_references | Where-Object {-not $_.cash_key_present}).Count
        sha256=$sha;bytes=$bytes.Length;report_file=$path;two_reads_identical=$true;financial_values_selected=$false
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
    [ordered]@{version='contad-account-details-receipt-v1';completed=$false;stage=$stage;reason_code=$reason;exception_types=@($types.ToArray());sql_states=@($states.ToArray() | Select-Object -Unique);uploaded=$false} | ConvertTo-Json -Depth 4 -Compress | Write-Output
    Write-Error 'Complemento nao concluido. Retorne somente este diagnostico seguro; preserve credencial e agente.' -ErrorAction Continue
    exit 1
} finally {
    if ($null -ne $connection) {$connection.Dispose()}
    if ($null -ne $builder) {$builder.Clear()}
    $credential=$null
}
