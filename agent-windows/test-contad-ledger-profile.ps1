#requires -Version 5.1
<# Disposable Windows CI, synthetic counts only; never query the customer's ERP. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-ledger-profile.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class LedgerProfileFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-ledger-secret must not leak");}
 public void Dispose(){}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba")throw new Exception("Metadata restriction contract");
  string[] cols;
  switch(r[2]){
   case "geempre":cols=new[]{"CODI_EMP","STAT_EMP"};break;
   case "ctparmto":cols=new[]{"CODI_EMP","CODI_PAD","COMP_PAD","I_PLANOCONTAS"};break;
   case "ctlancto":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","DATA_LAN","CDEB_LAN","CCRE_LAN"};break;
   case "ctcontas":cols=new[]{"CODI_EMP","CODI_CTA","TIPO_CTA","SITUACAO_CTA"};break;
   default:throw new Exception("Unexpected source table");
  }
  var t=new DataTable();foreach(string s in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(s,typeof(string));
  foreach(string c in cols){if(Scenario=="missing_column"&&c=="CODI_EMP_PLANO")continue;t.Rows.Add("bethadba",r[2],c);}return t;
 }
 public LedgerProfileFixtureCommand CreateCommand(){return new LedgerProfileFixtureCommand();}
}
public sealed class LedgerProfileFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r", "").Trim(),s=LedgerProfileFixtureConnection.Scenario;
  bool config=q.StartsWith("SELECT TOP 2 "),baseline=q.StartsWith("SELECT TOP 11 ")&&!q.Contains("LEFT JOIN"),joined=q.Contains("LEFT JOIN"),shape=q.StartsWith("SELECT TOP 129 ");
  if((!config&&!baseline&&!joined&&!shape)||CommandTimeout!=40)throw new Exception("Query contract");
  if(System.Text.RegularExpressions.Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|VLOR_LAN|CHIS_LAN|NDOC_LAN|CGCE_EMP|NOME_EMP|NOME_CTA)\b")||q.Contains("SELECT *"))throw new Exception("Prohibited values or write");
  foreach(System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)")) {
   if(Array.IndexOf(new[]{"bethadba.geempre","bethadba.ctparmto","bethadba.ctlancto","bethadba.ctcontas"},m.Groups[1].Value)<0)throw new Exception("Unexpected source");
  }
  if(!shape){
   if(Parameters.Count!=(config?2:3)||Parameters[0].OdbcType!=OdbcType.Int||(int)Parameters[0].Value!=212)throw new Exception("Company scope");
   if(config){if(Parameters[1].OdbcType!=OdbcType.VarChar||(string)Parameters[1].Value!="A"||!q.Contains("WHERE p.codi_emp=? AND g.stat_emp=?"))throw new Exception("Active pilot scope");}
   else {
    if(Parameters[1].OdbcType!=OdbcType.Date||Parameters[2].OdbcType!=OdbcType.Date||(DateTime)Parameters[1].Value!=new DateTime(2026,9,1)||(DateTime)Parameters[2].Value!=new DateTime(2026,10,1)||!q.Contains("WHERE l.codi_emp=? AND l.data_lan>=? AND l.data_lan<?"))throw new Exception("Period scope");
    if(joined){foreach(string key in new[]{"dp.codi_emp=l.CODI_EMP_PLANO AND dp.codi_cta=l.cdeb_lan","cp.codi_emp=l.CODI_EMP_PLANO AND cp.codi_cta=l.ccre_lan","dc.codi_emp=l.codi_emp AND dc.codi_cta=l.cdeb_lan","cc.codi_emp=l.codi_emp AND cc.codi_cta=l.ccre_lan"})if(!q.Contains(key))throw new Exception("Candidate composite key");}
   }
  }else{
   foreach(OdbcParameter p in Parameters)if(p.OdbcType!=OdbcType.Int||((int)p.Value!=100&&(int)p.Value!=212))throw new Exception("Candidate scope");
   if(!q.Contains("WHERE codi_emp IN ("))throw new Exception("Unbounded accounts");
  }
  var t=new DataTable();
  if(config){
   t.Columns.Add("company",typeof(long));t.Columns.Add("pad",typeof(long));t.Columns.Add("comp",typeof(string));t.Columns.Add("plan",typeof(long));
   if(s!="missing_config")t.Rows.Add(212L,s=="null_codes"?(object)DBNull.Value:100L,s=="null_codes"?(object)DBNull.Value:"N",s=="null_codes"?(object)DBNull.Value:1L);
   if(s=="duplicate_config")t.Rows.Add(212L,100L,"N",1L);
  }else if(baseline){
   for(int i=0;i<7;i++)t.Columns.Add("c"+i,typeof(long));
   if(s!="empty_ledger"){
    if(s=="plan_limit"){for(int i=0;i<11;i++)t.Rows.Add((long)i,1L,1L,0L,0L,0L,0L);}
    else if(s=="count_limit")t.Rows.Add(100L,1000001L,1000001L,0L,0L,0L,0L);
    else t.Rows.Add(100L,s=="invalid_number"?-1L:200L,197L,1L,1L,1L,163L);
   }
  }else if(joined){
   for(int i=0;i<(s=="wrong_columns"?7:8);i++)t.Columns.Add("c"+i,typeof(long));
   if(s=="wrong_columns")t.Rows.Add(100L,200L,198L,198L,198L,198L,0L);
   else if(s!="empty_ledger")t.Rows.Add(100L,s=="join_multiplication"?201L:200L,s=="inconsistent_sides"?199L:198L,198L,s=="impossible_match"?199L:198L,198L,0L,0L);
  }else {
   t.Columns.Add("owner",typeof(long));t.Columns.Add("type",typeof(string));t.Columns.Add("status",typeof(string));t.Columns.Add("count",typeof(long));
   int count=s=="shape_limit"?129:(s=="large_output"?128:1);
   for(int i=0;i<count;i++)t.Rows.Add(s=="null_codes"||s=="empty_ledger"?212L:100L,s=="null_codes"?(object)DBNull.Value:"A",s=="null_codes"?(object)DBNull.Value:"A",50L);
  }
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [LedgerProfileFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-ledger-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [LedgerProfileFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0; & $source; exit $LASTEXITCODE
}
$evidence=@()
foreach ($case in @('success','empty_ledger','null_codes','missing_column','missing_config','duplicate_config','plan_limit','join_multiplication','inconsistent_sides','impossible_match','invalid_number','count_limit','shape_limit','large_output','wrong_columns','driver_failure')) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if ($output.Contains('synthetic-ledger-secret')) {throw 'Credential or driver message leaked.'}
    $match=[regex]::Match($output,'(?ms)^\{.*?^\}')
    if (-not $match.Success) {throw ('Missing safe JSON: '+$case)}
    $result=$match.Value | ConvertFrom-Json
    if ($case -in @('success','empty_ledger','null_codes')) {
        if ($code -ne 0 -or -not $result.completed -or $result.company_code -ne 212 -or $result.pilot_account_code -ne 8 -or $result.period_start -ne '2026-09-01' -or $result.period_end_exclusive -ne '2026-10-01' -or $result.financial_values_selected -or $result.names_or_documents_selected -or $result.erp_write_performed -or $result.chart_owner_mapping_approved -or $result.account_type_meanings_approved -or $result.financial_collection_enabled) {throw ('Unsafe/wrong success: '+$case)}
        if ($case -eq 'success' -and ($result.entry_count -ne 200 -or $result.entry_shapes[0].pilot_account_rows -ne 163 -or $result.candidate_links[0].debit_plan_matches -ne 198 -or $result.candidate_links[0].debit_own_matches -ne 0)) {throw 'Coverage lost.'}
        if ($case -eq 'empty_ledger' -and ($result.entry_count -ne 0 -or $result.entry_shapes.Count -ne 0)) {throw 'Empty source fabricated counts.'}
        if ([Text.Encoding]::UTF8.GetByteCount($match.Value) -gt 16384) {throw 'Large profile accepted.'}
    } elseif ($code -eq 0 -or $result.completed) {throw ('Failure fixture accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;stage=$result.stage;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-ledger-profile.json') -Encoding UTF8
Write-Host 'Ledger profile: fixed pilot/period, aggregate-only queries, candidate keys, fanout refusals, bounds and redaction passed.'
exit 0
