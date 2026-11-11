#requires -Version 5.1
<# Disposable Windows CI only: synthetic catalog, no actual ERP or credentials. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-relations.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class RelationsFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-relations-secret must not leak");}
 public void Close(){}
 public void Dispose(){}
 public RelationsFixtureCommand CreateCommand(){return new RelationsFixtureCommand();}
}
public sealed class RelationsFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r", "").Trim();
  string[] names={"GEEMPRE","CTCONTAS","CTCONTACAIXA","CTCONTACAIXA_CONTA_BANCARIA","CTLANCTO","CTCLANCTO","CTCCUSTO","EFCLIENTES","EFFORNECE"};
  bool tables=q.StartsWith("SELECT TOP 10 "), keys=q.StartsWith("SELECT TOP 1025 "), relations=q.StartsWith("SELECT TOP 2049 ");
  if((!tables&&!keys&&!relations)||CommandTimeout!=40||Parameters.Count!=(relations?20:10))throw new Exception("Query contract");
  for(int i=0;i<Parameters.Count;i++) {
   string expected=i%10==0?"bethadba":names[i%10-1];
   if(Parameters[i].OdbcType!=OdbcType.VarChar||Parameters[i].Size!=128||(string)Parameters[i].Value!=expected)throw new Exception("Parameter scope");
  }
  if(System.Text.RegularExpressions.Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|SYSUSERPASSWORD)\b")||q.Contains("SELECT *")||q.Contains("FROM bethadba"))throw new Exception("Unsafe projection");
  foreach(System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)")){
   if(Array.IndexOf(new[]{"SYS.SYSTAB","SYS.SYSUSER","SYS.SYSIDX","SYS.SYSIDXCOL","SYS.SYSTABCOL","SYS.SYSFKEY"},m.Groups[1].Value)<0)throw new Exception("Unexpected catalog");
  }
  if(keys&&(!q.Contains("ic.index_id=i.index_id")||!q.Contains("ic.table_id=i.table_id")||!q.Contains("c.column_id=ic.column_id")))throw new Exception("Composite index join");
  if(relations&&(!q.Contains("pc.column_id=ic.primary_column_id")||!q.Contains("pc.table_id=f.primary_table_id")||!q.Contains("ic.index_id=f.foreign_index_id")))throw new Exception("Foreign column mapping");
  string scenario=RelationsFixtureConnection.Scenario;
  var t=new DataTable();
  if(tables){
   t.Columns.Add("id",typeof(long));t.Columns.Add("name",typeof(string));t.Columns.Add("type",typeof(long));
   for(int i=0;i<names.Length;i++){
    if(scenario=="missing_table"&&i==8)continue;
    t.Rows.Add(100L+i,scenario=="duplicate_table"&&i==8?names[0]:names[i]+"  ",scenario=="wrong_table_type"&&i==0?21L:1L);
   }
  }else if(keys){
   foreach(string s in new[]{"table_id","index_id","category","unique","not_enforced","index_name","sequence","column_id","column_name","primary_column_id"})t.Columns.Add(s,s=="not_enforced"||s=="index_name"||s=="column_name"?typeof(string):typeof(long));
   if(scenario!="empty_catalog"){
    int count=scenario=="key_limit"?1025:2;
    for(int i=0;i<count;i++)t.Rows.Add(101L,0L,1L,1L,"N","PRIMARY",(long)i,(long)i+1,"column_"+i,DBNull.Value);
    if(scenario=="null_required")t.Rows[0][8]=DBNull.Value;
    if(scenario=="invalid_name")t.Rows[0][8]="unsafe\nname";
    if(scenario=="invalid_number")t.Rows[0][6]=-1L;
   }
  }else{
   foreach(string s in new[]{"foreign_table_id","foreign_index_id","primary_table_id","primary_index_id","foreign_schema","foreign_table","primary_schema","primary_table","match_type","check_on_commit","nulls","sequence","foreign_column_id","foreign_column","primary_column_id","primary_column"})t.Columns.Add(s,s.EndsWith("schema")||s.EndsWith("table")||s=="check_on_commit"||s=="nulls"||s=="foreign_column"||s=="primary_column"?typeof(string):typeof(long));
   if(scenario!="empty_catalog"){
    int count=scenario=="relation_limit"?2049:2;
    for(int i=0;i<count;i++)t.Rows.Add(104L,2L,101L,0L,"bethadba","CTLANCTO","bethadba","CTCONTAS",0L,"N","N",(long)i,(long)i+1,"source_"+i,2L-i,"target_"+i);
   }
  }
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [RelationsFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-relations-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [RelationsFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0
    if ($Scenario -eq 'summary') {& $source} else {& $source -AsJson}
    exit $LASTEXITCODE
}
$evidence=@()
$download=Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
[void][IO.Directory]::CreateDirectory($download)
foreach ($case in @('success','summary','empty_catalog','missing_table','duplicate_table','wrong_table_type','key_limit','relation_limit','null_required','invalid_name','invalid_number','driver_failure')) {
    $before=@(Get-ChildItem -LiteralPath $download -Directory -Filter 'CICA-CONTAD-Relacoes-*' | ForEach-Object {$_.FullName})
    try {
        $saved=$ErrorActionPreference
        try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
        $output=$lines | Out-String
        if ($output.Contains('synthetic-relations-secret')) {throw 'Secret or driver message leaked.'}
        $match=[regex]::Match($output,'(?s)\{.*?\}(?=\s*(?:$|\r?\n))')
        if (-not $match.Success) {throw ('Missing safe JSON: '+$case)}
        $result=$match.Value | ConvertFrom-Json
        $created=@(Get-ChildItem -LiteralPath $download -Directory -Filter 'CICA-CONTAD-Relacoes-*' | Where-Object {$before -notcontains $_.FullName})
        if ($case -in @('success','summary','empty_catalog')) {
            if ($code -ne 0 -or -not $result.completed -or $result.financial_semantics_approved -or $result.uploaded -or $created.Count -ne 1) {throw ('Wrong success: '+$case)}
            $reportPath=Join-Path $created[0].FullName 'relacoes.json'
            $report=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
            if ($report.tables.Count -ne 9 -or $report.business_values_selected -or $report.erp_write_performed -or $report.agent_configuration_read) {throw 'Unsafe report.'}
            if ($case -eq 'success' -and ($report.key_columns.Count -ne 2 -or $report.relation_columns.Count -ne 2 -or $report.relation_columns[0].primary_column_id -ne 2)) {throw 'Composite ordering or mapping lost.'}
            if ($case -eq 'empty_catalog' -and ($report.key_columns.Count -ne 0 -or $report.relation_columns.Count -ne 0)) {throw 'Empty catalog fabricated keys.'}
            if ($case -eq 'summary' -and $result.sha256 -ne (Get-FileHash -LiteralPath $reportPath -Algorithm SHA256).Hash.ToLowerInvariant()) {throw 'Wrong report hash.'}
            $acl=Get-Acl -LiteralPath $created[0].FullName
            if (-not $acl.AreAccessRulesProtected) {throw 'Inherited report ACL.'}
            $allowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
            foreach ($rule in $acl.Access) {if ($allowed -notcontains $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value) {throw 'Unexpected report reader.'}}
        } elseif ($code -eq 0 -or $result.completed -or $created.Count -ne 0) {throw ('Partial/failing fixture accepted: '+$case)}
        $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
    } finally {
        Get-ChildItem -LiteralPath $download -Directory -Filter 'CICA-CONTAD-Relacoes-*' | Where-Object {$before -notcontains $_.FullName} | Remove-Item -Recurse -Force
    }
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-relations.json') -Encoding UTF8
Write-Host 'Relations catalog: fixed metadata scope, composite columns, bounds, refusals, private ACL and redaction passed.'
exit 0
