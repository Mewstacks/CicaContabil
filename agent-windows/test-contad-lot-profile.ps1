#requires -Version 5.1
<# Disposable Windows CI; synthetic aggregates only, not financial acceptance. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-lot-profile.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class LotFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-lot-secret must not leak");}
 public void Dispose(){}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba")throw new Exception("Metadata restrictions");
  string[] cols;
  if(r[2]=="ctlancto")cols=new[]{"CODI_EMP","CODI_LOTE","DATA_LAN","CODI_EMP_PLANO","FILI_LAN","CDEB_LAN","CCRE_LAN","VLOR_LAN"};
  else if(r[2]=="ctlanctolote")cols=new[]{"CODI_EMP","CODI_LOTE","TIPO"};
  else throw new Exception("Unexpected object");
  var t=new DataTable();foreach(string n in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(n,typeof(string));
  foreach(string c in cols){if(Scenario=="missing_column"&&c=="CODI_LOTE")continue;t.Rows.Add("bethadba",r[2],c);}return t;
 }
 public LotFixtureCommand CreateCommand(){return new LotFixtureCommand();}
}
public sealed class LotFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r", "").Trim(),s=LotFixtureConnection.Scenario;
  bool baseline=q.StartsWith("SELECT COUNT(*)"),groups=q.StartsWith("WITH selected_lots"),branches=q.StartsWith("SELECT TOP 17 fili_lan");
  if((!baseline&&!groups&&!branches)||CommandTimeout!=40||Parameters.Count!=(groups?9:3))throw new Exception("Query contract");
  if(System.Text.RegularExpressions.Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|CHIS_LAN|NDOC_LAN|CGCE_EMP|NOME_EMP|NOME_CTA)\b")||q.Contains("SELECT *"))throw new Exception("Unsafe values/write");
  for(int i=0;i<Parameters.Count;i++) {
   bool number=i==0||i==7||i==8;
   if(number){if(Parameters[i].OdbcType!=OdbcType.Int||(int)Parameters[i].Value!=212)throw new Exception("Company scope");}
   else {DateTime expected=i==1||i==3||i==5?new DateTime(2026,9,1):new DateTime(2026,10,1);if(Parameters[i].OdbcType!=OdbcType.Date||(DateTime)Parameters[i].Value!=expected)throw new Exception("Period scope");}
  }
  if(!q.Contains("(cdeb_lan=8 OR ccre_lan=8)"))throw new Exception("Missing bank scope");
  if(groups){
   foreach(string fragment in new[]{"CASE WHEN l.data_lan>=? AND l.data_lan<? THEN l.vlor_lan ELSE 0 END","s.codi_lote IS NULL AND l.codi_lote IS NULL","h.codi_emp=? AND h.codi_lote=g.codi_lote","g.debit_total<>g.credit_total","g.all_rows<>g.period_rows"})if(!q.Contains(fragment))throw new Exception("Incomplete candidate check");
   string projection=q.Substring(q.IndexOf("SELECT TOP 17 h.tipo"));
   if(projection.Contains("SUM(g.debit_total)")||projection.Contains("SUM(g.credit_total)"))throw new Exception("Monetary amount returned");
  } else if(q.Contains("vlor_lan"))throw new Exception("Unnecessary monetary source");
  var t=new DataTable();
  bool empty=s=="empty";
  if(baseline){
   for(int i=0;i<4;i++)t.Columns.Add("c"+i,typeof(long));
   t.Rows.Add(empty?0L:163L,empty?0L:(s=="multiple_effects"?162L:163L),0L,empty?0L:163L);
  }else if(groups){
   t.Columns.Add("type",typeof(string));for(int i=1;i<14;i++)t.Columns.Add("c"+i,typeof(long));
   if(!empty){
    int rows=s=="group_limit"?17:1;
    for(int i=0;i<rows;i++)t.Rows.Add("M",s=="multiple_effects"?162L:(s=="fanout"?164L:163L),s=="outside_period"?301L:300L,300L,s=="lost_bank_row"?162L:163L,163L,s=="outside_period"?1L:0L,s=="multiple_dates"?1L:0L,s=="multiple_plans"?1L:0L,s=="multiple_branches"?1L:0L,s=="unbalanced"?1L:0L,s=="missing_header"?1L:0L,s=="multiple_effects"?1L:0L,s=="nonpositive"?1L:0L);
   }
  }else{
   t.Columns.Add("branch",typeof(long));t.Columns.Add("rows",typeof(long));
   if(!empty){if(s=="branch_limit"){for(int i=0;i<17;i++)t.Rows.Add((long)i,1L);}else t.Rows.Add(0L,163L);}
  }
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [LotFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-lot-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [LotFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0; & $source; exit $LASTEXITCODE
}
$evidence=@()
$incompatible=@('empty','multiple_effects','outside_period','multiple_dates','multiple_plans','multiple_branches','unbalanced','missing_header','nonpositive')
foreach ($case in @('success')+$incompatible+@('missing_column','group_limit','branch_limit','fanout','lost_bank_row','driver_failure')) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if ($output.Contains('synthetic-lot-secret')) {throw 'Secret or driver message leaked.'}
    $match=[regex]::Match($output,'(?ms)^\{.*?^\}')
    if (-not $match.Success) {throw ('Missing safe JSON: '+$case)}
    $result=$match.Value | ConvertFrom-Json
    if ($case -eq 'success' -or $case -in $incompatible) {
        if ($code -ne 0 -or -not $result.completed -or $result.company_code -ne 212 -or $result.pilot_account_code -ne 8 -or $result.monetary_values_returned -or $result.names_or_documents_returned -or $result.erp_write_performed -or $result.grouping_meaning_approved -or $result.financial_collection_enabled) {throw ('Unsafe/wrong success: '+$case)}
        if ($result.structural_candidate_compatible -ne ($case -eq 'success')) {throw ('False structural compatibility: '+$case)}
    } elseif ($code -eq 0 -or $result.completed) {throw ('Failure accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-lot-profile.json') -Encoding UTF8
Write-Host 'Lot profile: bounded counts, internal balance checks, complete period, bank cardinality, refusal and redaction passed.'
exit 0
