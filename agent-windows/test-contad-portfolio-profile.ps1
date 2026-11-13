#requires -Version 5.1
<# Synthetic ODBC contract on disposable Windows. Never use a real ERP or agent configuration. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-portfolio-profile.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class PortfolioFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-portfolio-secret must not leak");}
 public void Dispose(){}
 public PortfolioFixtureCommand CreateCommand(){return new PortfolioFixtureCommand();}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba")throw new Exception("Metadata scope");
  string[] cols;
  switch(r[2]){
   case "geempre":cols=new[]{"CODI_EMP","STAT_EMP"};break;
   case "ctparmto":cols=new[]{"CODI_EMP","CODI_PAD","COMP_PAD","I_PLANOCONTAS"};break;
   case "ctcontacaixa":cols=new[]{"CODI_EMP","CODI_CTA","SELE_CTA","TIPO_CONTA_CAIXA"};break;
   case "ctcontacaixa_conta_bancaria":cols=new[]{"CODI_EMP","I_CONTA_CAIXA","I_SEQUENCIAL_CONTA_BANCARIA"};break;
   case "ctlancto":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","FILI_LAN","DATA_LAN","CDEB_LAN","CCRE_LAN","CODI_LOTE"};break;
   case "ctconciliacao_conta":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","CODI_CTA"};break;
   case "ctcontas":cols=new[]{"CODI_EMP","CODI_CTA","TIPO_CTA","SITUACAO_CTA"};break;
   default:throw new Exception("Unexpected source");
  }
  var t=new DataTable();foreach(string s in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(s,typeof(string));
  foreach(string c in cols){if(Scenario=="missing_column"&&c=="STAT_EMP")continue;t.Rows.Add("bethadba",r[2],c);}return t;
 }
}
public sealed class PortfolioFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 public static int Reads;
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r", "").Trim(),s=PortfolioFixtureConnection.Scenario;
  bool configured=q.Contains("FROM bethadba.CTCONCILIACAO_CONTA q"),companies=q.StartsWith("SELECT TOP 501 "),cash=q.StartsWith("SELECT TOP 5001 ")&&!configured,ledger=q.StartsWith("SELECT TOP 10001 ");
  if((!companies&&!cash&&!ledger&&!configured)||CommandTimeout!=40||Parameters.Count!=(ledger?3:1))throw new Exception("Query contract");
  if(Parameters[0].OdbcType!=OdbcType.VarChar||(string)Parameters[0].Value!="A"||!q.Contains("WHERE g.stat_emp=?"))throw new Exception("Active scope");
  if(System.Text.RegularExpressions.Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|VLOR_LAN|CHIS_LAN|NDOC_LAN|CGCE_EMP|NOME_EMP|NOME_CTA|AGENCIA|IDENTIFICADOR_CONTA)\b")||q.Contains("SELECT *"))throw new Exception("Forbidden values/write");
  foreach(System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)"))
   if(Array.IndexOf(new[]{"bethadba.geempre","bethadba.ctparmto","bethadba.ctcontacaixa","bethadba.CTCONTACAIXA_CONTA_BANCARIA","bethadba.ctlancto","bethadba.CTCONCILIACAO_CONTA","bethadba.ctcontas"},m.Groups[1].Value)<0)throw new Exception("Source scope");
  if(configured&&!q.Contains("c.codi_emp=q.CODI_EMP_PLANO AND c.codi_cta=q.CODI_CTA"))throw new Exception("Composite chart key");
  if(companies&&!q.Contains("LEFT JOIN bethadba.ctparmto p ON p.codi_emp=g.codi_emp"))throw new Exception("Missing company coverage");
  if(cash&&!q.Contains("b.CODI_EMP=c.codi_emp AND b.I_CONTA_CAIXA=c.codi_cta"))throw new Exception("Composite bank reference key");
  if(ledger&&(Parameters[1].OdbcType!=OdbcType.Date||Parameters[2].OdbcType!=OdbcType.Date||(DateTime)Parameters[1].Value!=new DateTime(2026,9,1)||(DateTime)Parameters[2].Value!=new DateTime(DateTime.Today.Year,DateTime.Today.Month,1)||!q.Contains("AND l.data_lan>=? AND l.data_lan<?")))throw new Exception("Period scope");
  Reads++;
  var t=new DataTable();
  if(companies){
   t.Columns.Add("company",typeof(long));t.Columns.Add("configs",typeof(long));t.Columns.Add("pad",typeof(long));t.Columns.Add("comp",typeof(string));t.Columns.Add("plan",typeof(long));
   if(s=="empty")return t.CreateDataReader();
   if(s=="company_limit"){for(int i=0;i<501;i++)t.Rows.Add((long)i+1,1L,100L,"N",1L);return t.CreateDataReader();}
   if(s=="missing_configuration")t.Rows.Add(212L,0L,DBNull.Value,DBNull.Value,DBNull.Value);
   else t.Rows.Add(212L,s=="duplicate_configuration"?2L:1L,100L,s=="invalid_raw"?"SECRET":"N",1L);
   if(s=="duplicate_company")t.Rows.Add(212L,1L,100L,"N",1L);
   else t.Rows.Add(213L,1L,100L,"N",1L);
  }else if(configured){
   t.Columns.Add("company",typeof(long));t.Columns.Add("chart",typeof(long));t.Columns.Add("code",typeof(long));t.Columns.Add("type",typeof(string));t.Columns.Add("status",typeof(string));t.Columns.Add("matches",typeof(long));
   if(s=="configured_empty")return t.CreateDataReader();
   int count=s=="configured_limit"?5001:1;
   for(int i=0;i<count;i++)t.Rows.Add(s=="configured_outside"?999L:212L,100L,(long)i+8,s=="configured_missing"?(object)DBNull.Value:"A",s=="configured_missing"?(object)DBNull.Value:"A",s=="configured_missing"?0L:(s=="configured_fanout"?2L:1L));
   if(s=="configured_duplicate")t.Rows.Add(212L,100L,8L,"A","A",1L);
   if(s=="configured_changed"&&Reads>2)t.Rows.Add(212L,100L,999L,"A","A",1L);
  }else if(cash){
   t.Columns.Add("company",typeof(long));t.Columns.Add("cash",typeof(long));t.Columns.Add("selection",typeof(string));t.Columns.Add("type",typeof(long));t.Columns.Add("refs",typeof(long));
   if(s=="empty"||s=="no_cash")return t.CreateDataReader();
   int count=s=="cash_limit"?5001:(s=="large_output"?300:1);
   for(int i=0;i<count;i++)t.Rows.Add(s=="outside_company"?999L:212L,(long)i+8,s=="null_codes"?(object)DBNull.Value:"S",s=="null_codes"?(object)DBNull.Value:1L,s=="source_changed"&&Reads>3?2L:1L);
   if(s=="duplicate_cash")t.Rows.Add(212L,8L,"N",2L,1L);
  }else{
   for(int i=0;i<9;i++)t.Columns.Add("c"+i,typeof(long));
   if(s=="empty"||s=="empty_ledger")return t.CreateDataReader();
   int count=s=="ledger_limit"?10001:1;
   for(int i=0;i<count;i++)t.Rows.Add(212L,100L,(long)i,s=="outside_period"?2025L:2026L,9L,s=="invalid_count"?-1L:200L,s=="count_coverage"?201L:20L,10L,0L);
   if(s=="duplicate_ledger")t.Rows.Add(212L,100L,0L,2026L,9L,200L,20L,10L,0L);
  }
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [PortfolioFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-portfolio-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [PortfolioFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0
    if ($Scenario -like 'configured_*') {& $source -ReconciliationAccountsOnly} else {& $source}
    exit $LASTEXITCODE
}
$evidence=@()
$cases=@('success','empty','no_cash','empty_ledger','null_codes','missing_configuration','large_output','missing_column','duplicate_configuration','duplicate_company','outside_company','duplicate_cash','duplicate_ledger','outside_period','invalid_count','count_coverage','company_limit','cash_limit','ledger_limit','invalid_raw','source_changed','driver_failure')
$cases+=@('configured_success','configured_empty','configured_missing','configured_outside','configured_duplicate','configured_fanout','configured_limit','configured_changed')
foreach ($case in $cases) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if ($output.Contains('synthetic-portfolio-secret') -or $output.Contains('SECRET')) {throw 'Credential or raw diagnostic leaked.'}
    $matches=@($output -split '\r?\n' | Where-Object {$_.StartsWith('{')})
    if ($matches.Count -ne 1) {throw ('Missing safe JSON: '+$case)}
    $result=$matches[0] | ConvertFrom-Json
    $compressed=$result.version -eq 'contad-portfolio-profile-transfer-v1'
    if ($compressed) {
        $buffer=[IO.MemoryStream]::new([Convert]::FromBase64String($result.data),$false)
        $gzip=[IO.Compression.GZipStream]::new($buffer,[IO.Compression.CompressionMode]::Decompress)
        $reader=[IO.StreamReader]::new($gzip,[Text.Encoding]::UTF8)
        try {$raw=$reader.ReadToEnd()} finally {$reader.Dispose();$gzip.Dispose();$buffer.Dispose()}
        $bytes=[Text.Encoding]::UTF8.GetBytes($raw);$hasher=[Security.Cryptography.SHA256]::Create()
        try {$sha=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()} finally {$hasher.Dispose()}
        if ($result.bytes -ne $bytes.Length -or $result.sha256 -cne $sha -or $bytes.Length -gt 4194304) {throw 'Transfer integrity failed.'}
        $result=$raw | ConvertFrom-Json
    }
    if ($case -in @('success','empty','no_cash','empty_ledger','null_codes','missing_configuration','large_output','configured_success','configured_empty','configured_missing')) {
        if ($code -ne 0 -or -not $result.completed -or -not $result.two_reads_identical -or $result.company_selector -ne 'A' -or $result.period_start -ne '2026-09-01') {throw ('Wrong success: '+$case)}
        foreach ($flag in @('account_meanings_approved','chart_owner_mapping_approved','bank_association_approved','financial_values_selected','names_or_documents_selected','agent_configuration_read','erp_write_performed','financial_collection_enabled','uploaded')) {if ($result.$flag -ne $false) {throw ('Unsafe flag: '+$case)}}
        if ($case -eq 'success' -and ($result.snapshot.companies.Count -ne 2 -or $result.snapshot.monthly_ledger.Count -ne 1 -or $result.snapshot.cash_candidates[0].bank_reference_count -ne 1)) {throw 'Coverage lost.'}
        if ($case -eq 'empty' -and ($result.snapshot.companies.Count -ne 0 -or $result.snapshot.cash_candidates.Count -ne 0 -or $result.snapshot.monthly_ledger.Count -ne 0)) {throw 'Empty source fabricated coverage.'}
        if ($case -eq 'large_output' -and -not $compressed) {throw 'Compressed transport not exercised.'}
        if ($case -like 'configured_*' -and $result.version -ne 'contad-reconciliation-account-profile-v1') {throw 'Wrong configured profile.'}
        if ($case -eq 'configured_success' -and ($result.snapshot.configured_accounts.Count -ne 1 -or $result.snapshot.configured_accounts[0].chart_company_code -ne 100)) {throw 'Configured coverage lost.'}
        if ($case -eq 'configured_empty' -and $result.snapshot.configured_accounts.Count -ne 0) {throw 'Empty configured source fabricated accounts.'}
        if ($case -eq 'configured_missing' -and $result.snapshot.configured_accounts[0].catalogue_matches -ne 0) {throw 'Missing chart match hidden.'}
    } elseif ($code -eq 0 -or $result.completed -or -not $result.reason_code) {throw ('Failure accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-portfolio-profile.json') -Encoding UTF8
Write-Host 'Portfolio profile: active scope, full-month counts, composite references, bounds, two reads and redaction passed.'
exit 0
