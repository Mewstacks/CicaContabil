#requires -Version 5.1
<# Disposable Windows harness: no ERP, no network and synthetic credentials only. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-title-profile.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class TitleProfileConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){
  if(ConnectionTimeout!=20)throw new Exception("Timeout");
  if(Scenario=="driver_failure")throw new Exception("synthetic-title-profile-secret must not leak");
 }
 public void Dispose(){}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns" || r.Length!=4 || r[1]!="bethadba")throw new Exception("Unexpected metadata scope");
  var t=new DataTable();foreach(var c in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(c,typeof(string));
  string table=r[2]; string names;
  if(table=="ctlancto")names="CODI_EMP NUME_LAN CODI_EMP_PLANO DATA_LAN CDEB_LAN CCRE_LAN";
  else {
   string n=table.StartsWith("efentradas")?"ent":table.StartsWith("efsaidas")?"sai":table.StartsWith("efservicos")?"ser":null;
   if(n==null)throw new Exception("Unexpected table");
   string s=n+"p";
   names="CODI_EMP codi_"+n;
   if(table.EndsWith("par"))names+=" origem_reg parc_"+s+" vcto_"+s+" tipo_"+s+" vlor_"+s;
   else if(table.EndsWith("pag"))names+=" origem_reg parc_"+s+" pgto_"+s+" tipo_"+s+" nropag_"+s+" vpag_"+s+" origempg_"+s;
   else if(table.EndsWith("pag_lancto"))names+=" NUME_LAN FILI_LAN parc_"+s+" pgto_"+s+" tipo_"+s+" nropag_"+s;
  }
  foreach(string c in names.Split(' ')) {
   if(Scenario=="missing_column" && c=="NUME_LAN")continue;
   t.Rows.Add("bethadba",table,c);
  }
  return t;
 }
 public TitleProfileCommand CreateCommand(){return new TitleProfileCommand();}
}
public sealed class TitleProfileCommand:IDisposable {
 public static int Executions;
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  Executions++;
  string q=CommandText.Replace("\r","").Trim();
  bool payment=q.Contains("pag p\n");
  if(!q.StartsWith("SELECT TOP 257 ") || CommandTimeout!=20 || q.Contains("{") || Parameters.Count!=(payment?8:3))throw new Exception("Query contract");
  int first=payment?2:0;
  if(payment) {
   CheckDate(0,9,1);CheckDate(1,10,1);
   if(!q.Contains("k.fili_lan=p.codi_emp") || !q.Contains("l.codi_emp=x.codi_emp") || !q.Contains("l.nume_lan=x.nume_lan"))throw new Exception("Company identity lost");
  }
  for(int i=first;i<Parameters.Count;i+=3) {
   if(Parameters[i].OdbcType!=OdbcType.Int || Convert.ToInt32(Parameters[i].Value)!=212)throw new Exception("Scope escaped");
   CheckDate(i+1,9,1);CheckDate(i+2,10,1);
  }
  var t=new DataTable();
  for(int i=0;i<(payment?18:8);i++)t.Columns.Add("c"+i,(payment && i==1)?typeof(string):typeof(long));
  string scenario=TitleProfileConnection.Scenario;
  if(scenario=="empty")return t.CreateDataReader();
  object[] row=payment?new object[]{4L,"M",0L,2L,0L,1L,1L,0L,0L,0L,1L,1L,0L,1L,1L,0L,0L,0L}:new object[]{0L,0L,2L,0L,2L,0L,0L,0L};
  int count=payment?3:2;
  if(scenario=="changed" && Executions>6){row[count]=3L;row[count+2]=payment?2L:3L;}
  if(scenario=="negative_count")row[count]=-1L;
  if(scenario=="bad_partition")row[count+1]=1L;
  if(scenario=="bad_links" && payment)row[13]=0L;
  if(scenario=="raw_code_limit")row[0]=256L;
  if(scenario=="row_limit"){row[count]=1000001L;row[count+2]=1000001L;}
  if(scenario=="raw_origin" && payment)row[1]="unexpected-identifier";
  int loops=scenario=="group_limit"?257:1;
  for(int i=0;i<loops;i++)t.Rows.Add((object[])row.Clone());
  return t.CreateDataReader();
 }
 private void CheckDate(int i,int month,int day){
  if(Parameters[i].OdbcType!=OdbcType.Date || (DateTime)Parameters[i].Value!=new DateTime(2026,month,day))throw new Exception("Date scope escaped");
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [TitleProfileConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-title-profile-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [TitleProfileConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0; & $source; exit $LASTEXITCODE
}
$evidence=@()
foreach ($case in @('success','empty','changed','missing_column','group_limit','negative_count','bad_partition','bad_links','raw_code_limit','row_limit','raw_origin','driver_failure')) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue'; $lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1); $code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if ($output.Contains('synthetic-title-profile-secret')) {throw 'Credential or driver message leaked.'}
    $json=@($lines | ForEach-Object {[string]$_} | Where-Object {$_.TrimStart().StartsWith('{')})
    if ($json.Count -ne 1) {throw ('Missing safe JSON for '+$case+': '+$output)}
    $result=$json[0] | ConvertFrom-Json
    if ($case -in @('success','empty')) {
        if ($code -ne 0 -or -not $result.completed -or $result.version -ne 'contad-title-profile-v1' -or $result.company_code -ne 212 -or $result.identical_read_count -ne 2 -or $result.families.Count -ne 3 -or $result.financial_values_selected -or $result.names_or_documents_selected -or $result.erp_write_performed -or $result.payment_semantics_approved -or $result.financial_collection_enabled) {throw ('Incorrect success: '+$case+'; exit='+$code+'; safe output='+$output)}
        foreach ($family in $result.families) {
            if ($case -eq 'empty') {if ($family.due_installments.Count -ne 0 -or $family.payments.Count -ne 0) {throw 'Empty source invented rows.'}}
            elseif ($family.due_installments.Count -ne 1 -or $family.payments.Count -ne 1 -or $family.payments[0].row_count -ne 2 -or $family.payments[0].pilot_bank_linked -ne 1) {throw 'Wrong profile shape.'}
        }
    } elseif ($code -eq 0 -or $result.completed) {throw ('Failure fixture accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation'; [void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-title-profile.json') -Encoding UTF8
Write-Host 'Title profile: twelve bounded synthetic scenarios passed; no ERP access.'
$global:LASTEXITCODE=0
exit 0
