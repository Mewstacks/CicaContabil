#requires -Version 5.1
<# Windows fixture only. No ERP connection, network access or actual credential. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-title-links.ps1'
if ($Scenario) {
 Add-Type -AssemblyName System.Data
 Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class TitleLinksConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){
  if(ConnectionTimeout!=20)throw new Exception("Timeout");
  if(Scenario=="driver_failure")throw new Exception("synthetic-title-links-secret must not leak");
 }
 public void Dispose(){}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns" || r.Length!=4 || r[1]!="bethadba")throw new Exception("Unexpected metadata scope");
  var t=new DataTable();foreach(string c in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(c,typeof(string));
  string table=r[2];string names;
  if(table=="ctlancto")names="CODI_EMP NUME_LAN CODI_LOTE CODI_EMP_PLANO DATA_LAN CDEB_LAN CCRE_LAN";
  else if(table=="ctlanctolote")names="CODI_EMP CODI_LOTE";
  else {
   string n=table.StartsWith("efentradas")?"ent":table.StartsWith("efsaidas")?"sai":table.StartsWith("efservicos")?"ser":null;
   if(n==null || !(table.EndsWith("pag") || table.EndsWith("pag_lancto")))throw new Exception("Unexpected table");
   string s=n+"p";names="CODI_EMP codi_"+n+" parc_"+s+" pgto_"+s+" tipo_"+s+" nropag_"+s;
   names+=table.EndsWith("pag_lancto")?" NUME_LAN FILI_LAN":" origem_reg origempg_"+s;
  }
  foreach(string c in names.Split(' ')) {
   if(Scenario=="missing_column" && c=="CODI_LOTE")continue;
   t.Rows.Add("bethadba",table,c);
  }
  return t;
 }
 public TitleLinksCommand CreateCommand(){return new TitleLinksCommand();}
}
public sealed class TitleLinksCommand:IDisposable {
 public static int Executions;
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  Executions++;
  string q=CommandText.Replace("\r","").Trim();bool coverage=q.StartsWith("WITH scoped_payments AS (");
  if(CommandTimeout!=20 || q.Contains("{") || Parameters.Count!=(coverage?5:3))throw new Exception("Query contract");
  if(q.Contains("vpag_") || q.Contains("vlor_") || q.ToLowerInvariant().Contains("historico"))throw new Exception("Monetary or narrative column selected");
  if(!q.Contains("x.fili_lan=p.codi_emp") || !q.Contains("l.codi_emp=x.codi_emp") || !q.Contains("l.nume_lan=x.nume_lan"))throw new Exception("Source identity lost");
  if(coverage && (!q.Contains("b.codi_emp=212 AND b.CODI_EMP_PLANO=212") || !q.Contains("b.codi_emp=r.ledger_company AND b.codi_lote=r.codi_lote")))throw new Exception("Lot identity lost");
  if(Parameters[0].OdbcType!=OdbcType.Int || Convert.ToInt32(Parameters[0].Value)!=212)throw new Exception("Company scope escaped");
  CheckDate(1,9,1);CheckDate(2,10,1);if(coverage){CheckDate(3,9,1);CheckDate(4,10,1);}
  string scenario=TitleLinksConnection.Scenario;
  var t=new DataTable();int columns=coverage?16:7;if(scenario=="wrong_fields")columns++;
  for(int i=0;i<columns;i++)t.Columns.Add("c"+i,(coverage && i==1)?typeof(string):typeof(long));
  if(scenario=="empty" || scenario=="wrong_fields")return t.CreateDataReader();
  object[] row=coverage?new object[]{1L,"B",0L,2L,0L,0L,2L,1L,1L,1L,0L,0L,0L,0L,0L,0L}:new object[]{1L,212L,212L,501L,0L,3L,2L};
  if(scenario=="changed" && Executions>6 && coverage){row[3]=3L;}
  if(scenario=="negative_count")row[coverage?3:5]=-1L;
  if(scenario=="bad_coverage" && coverage)row[6]=3L;
  if(scenario=="bad_lot_coverage" && coverage){row[6]=0L;}
  if(scenario=="bad_account_coverage" && !coverage)row[6]=4L;
  if(scenario=="raw_code_limit")row[0]=256L;
  if(scenario=="raw_origin" && coverage)row[1]="unexpected-identifier";
  if(!coverage && !q.StartsWith("SELECT TOP 1025 "))throw new Exception("Account group sentinel missing");
  int loops=(scenario=="group_limit" && coverage)?257:(scenario=="account_group_limit" && !coverage)?1025:(scenario=="expanded_accounts" && !coverage)?129:1;
  if(scenario=="total_limit"){loops=2;row[coverage?3:5]=750000L;}
  for(int i=0;i<loops;i++){
   object[] current=(object[])row.Clone();if(!coverage && loops>2)current[3]=501L+i;
   t.Rows.Add(current);
  }
  return t.CreateDataReader();
 }
 private void CheckDate(int i,int month,int day){if(Parameters[i].OdbcType!=OdbcType.Date || (DateTime)Parameters[i].Value!=new DateTime(2026,month,day))throw new Exception("Date scope escaped");}
 public void Dispose(){holder.Dispose();}
}
'@
 [TitleLinksConnection]::Scenario=$Scenario
 function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-title-links-secret' -AsPlainText -Force))}
 function New-Object {
  [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
  if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [TitleLinksConnection]::new()}
  Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
 }
 $global:LASTEXITCODE=0
 if ($Scenario -eq 'compact') {& $source -Compact} else {& $source}
 exit $LASTEXITCODE
}
$evidence=@()
foreach ($case in @('success','empty','compact','expanded_accounts','changed','missing_column','group_limit','account_group_limit','negative_count','bad_coverage','bad_lot_coverage','bad_account_coverage','raw_code_limit','raw_origin','wrong_fields','total_limit','driver_failure')) {
 $saved=$ErrorActionPreference
 try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
 $output=$lines | Out-String
 if ($output.Contains('synthetic-title-links-secret')) {throw 'Credential or driver message leaked.'}
 $json=@($lines | ForEach-Object {[string]$_} | Where-Object {$_.TrimStart().StartsWith('{')})
 if ($json.Count -ne 1) {throw ('Missing safe JSON for '+$case+': '+$output)}
 $r=$json[0] | ConvertFrom-Json
 if ($case -eq 'compact') {
  if ($r.version -ne 'contad-title-links-transfer-v1' -or $r.encoding -ne 'gzip-base64' -or $r.bytes -lt 1 -or $r.bytes -gt 4194304) {throw 'Incorrect transfer envelope.'}
  $packed=[Convert]::FromBase64String($r.data)
  $inputStream=New-Object IO.MemoryStream(,$packed)
  $gzip=New-Object IO.Compression.GZipStream($inputStream,[IO.Compression.CompressionMode]::Decompress)
  $decoded=New-Object IO.MemoryStream
  try {$gzip.CopyTo($decoded);$bytes=$decoded.ToArray()} finally {$gzip.Dispose();$inputStream.Dispose();$decoded.Dispose()}
  $crypto=[Security.Cryptography.SHA256]::Create()
  try {$sha=[BitConverter]::ToString($crypto.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()} finally {$crypto.Dispose()}
  if ($bytes.Length -ne $r.bytes -or $sha -cne $r.sha256) {throw 'Transfer hash or byte count differs.'}
  $r=[Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json
 }
 if ($case -in @('success','empty','compact','expanded_accounts')) {
  if ($code -ne 0 -or -not $r.completed -or $r.version -ne 'contad-title-links-v1' -or $r.company_code -ne 212 -or $r.identical_read_count -ne 2 -or $r.families.Count -ne 3 -or $r.monetary_columns_selected -or $r.names_or_documents_selected -or $r.lot_membership_proves_bank_allocation -or $r.payment_semantics_approved -or $r.financial_collection_enabled -or $r.erp_write_performed -or $r.agent_configuration_read) {throw ('Wrong success: '+$case+'; exit='+$code+'; safe output='+$output)}
  foreach ($family in $r.families) {
   if ($case -eq 'empty') {if ($family.payment_coverage.Count -ne 0 -or $family.linked_account_shapes.Count -ne 0) {throw 'Empty source invented rows.'}}
   else {
    $expectedAccounts=$(if ($case -eq 'expanded_accounts') {129} else {1})
    if ($family.payment_coverage.Count -ne 1 -or $family.payment_coverage[0].row_count -ne 2 -or $family.payment_coverage[0].same_lot_bank -ne 2 -or $family.linked_account_shapes.Count -ne $expectedAccounts -or $family.linked_account_shapes[0].link_row_count -ne 3) {throw 'Wrong counts.'}
   }
  }
 } else {
  if ($code -eq 0 -or $r.completed) {throw ('Failure accepted: '+$case)}
  $expectedReasons=@{changed='SOURCE_CHANGED';missing_column='MISSING_COLUMN';group_limit='COVERAGE_GROUP_LIMIT';account_group_limit='ACCOUNT_GROUP_LIMIT';negative_count='NUMERIC_RANGE';bad_coverage='COVERAGE_COUNT';bad_lot_coverage='LOT_COVERAGE';bad_account_coverage='ACCOUNT_SHAPE';raw_code_limit='NUMERIC_RANGE';raw_origin='RAW_CODE_FORMAT';wrong_fields='FIELD_COUNT';total_limit='ROW_LIMIT';driver_failure='UNCLASSIFIED'}
  if ($r.reason_code -cne $expectedReasons[$case]) {throw ('Incorrect static diagnostic for '+$case+': '+$r.reason_code)}
 }
 $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-title-links.json') -Encoding UTF8
Write-Host 'Title links: seventeen bounded synthetic Windows scenarios passed; no ERP access.'
$global:LASTEXITCODE=0
exit 0
