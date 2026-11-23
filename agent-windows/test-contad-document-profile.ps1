#requires -Version 5.1
<# Disposable Windows CI only; no ERP or actual credentials. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-document-profile.ps1'
if($Scenario){
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class ProfileFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-profile-secret must not leak");}
 public void Dispose(){}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns" || r.Length!=4 || r[1]!="bethadba" || r[2]!="geempre")throw new Exception("Metadata contract");
  var t=new DataTable();foreach(var s in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(s,typeof(string));
  foreach(var s in new[]{"STAT_EMP","CGCE_EMP","TIPOI_EMP"}){if(Scenario=="missing_column" && s=="TIPOI_EMP")continue;t.Rows.Add("bethadba","geempre",s);}return t;
 }
 public ProfileFixtureCommand CreateCommand(){return new ProfileFixtureCommand();}
}
public sealed class ProfileFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r","").Trim();
  string expected="SELECT TOP 41 tipoi_emp, LENGTH(TRIM(cgce_emp)),\n LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', '')), COUNT(*)\nFROM bethadba.geempre WHERE stat_emp = ?\nGROUP BY tipoi_emp, LENGTH(TRIM(cgce_emp)),\n LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', ''))\nORDER BY tipoi_emp, LENGTH(TRIM(cgce_emp)),\n LENGTH(REPLACE(REPLACE(REPLACE(TRIM(cgce_emp), '.', ''), '/', ''), '-', ''))";
  if(q!=expected || CommandTimeout!=60 || Parameters.Count!=1 || (string)Parameters[0].Value!="A" || Parameters[0].OdbcType!=OdbcType.VarChar)throw new Exception("Unexpected query");
  var t=new DataTable();foreach(var s in new[]{"kind","length","normalized","count"})t.Columns.Add(s,typeof(long));
  if(ProfileFixtureConnection.Scenario=="group_limit"){for(int i=0;i<41;i++)t.Rows.Add(1L,14L,14L,1L);}
  else if(ProfileFixtureConnection.Scenario=="count_limit")t.Rows.Add(1L,14L,14L,10001L);
  else if(ProfileFixtureConnection.Scenario=="invalid_shape")t.Rows.Add(2L,11L,14L,1L);
  else {t.Rows.Add(1L,14L,14L,143L);t.Rows.Add(2L,11L,11L,1L);t.Rows.Add(3L,12L,12L,1L);t.Rows.Add(DBNull.Value,DBNull.Value,DBNull.Value,1L);}
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [ProfileFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-profile-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if($TypeName -eq 'System.Data.Odbc.OdbcConnection'){return [ProfileFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0;& $source;exit $LASTEXITCODE
}
$evidence=@()
foreach($case in @('success','missing_column','group_limit','count_limit','invalid_shape','driver_failure')){
    $saved=$ErrorActionPreference
    try{$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE}finally{$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if($output.Contains('synthetic-profile-secret')){throw 'Credential or driver message leaked.'}
    $match=[regex]::Match($output,'(?s)\{\s*"version":\s*"contad-document-profile-v1".*?\n\}')
    if(-not $match.Success){throw ('Missing JSON: '+$output)}
    $result=$match.Value | ConvertFrom-Json
    if($case -eq 'success'){
        if($code -ne 0 -or -not $result.completed -or $result.company_count -ne 146 -or $result.groups.Count -ne 4 -or $result.document_values_selected -or $result.financial_values_selected -or $result.erp_write_performed -or $result.registration_type_meanings_approved){throw 'Wrong coverage or false approval.'}
    }elseif($code -eq 0 -or $result.completed){throw ('Failure fixture accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-document-profile.json') -Encoding UTF8
Write-Host 'Document profile: bounded aggregate shapes, parameterized selection, nulls, refusals and redaction passed.'
exit 0
