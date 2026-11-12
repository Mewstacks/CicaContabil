#requires -Version 5.1
<# Disposable Windows only: fixed-query contract, synthetic schema, no ERP. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-title-catalog.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
using System.Text.RegularExpressions;
public sealed class TitleCatalogFixtureConnection:IDisposable {
 public static string Scenario;
 public static string[] Names={"efentradas","efentradaspag","efentradaspag_lancto","efentradaspar"};
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-title-secret must not leak");}
 public void Close(){}
 public void Dispose(){}
 public TitleCatalogFixtureCommand CreateCommand(){return new TitleCatalogFixtureCommand();}
 public DataTable GetSchema(string name,string[] restrictions){
  DataTable t=new DataTable();
  if(name=="Tables"){
   foreach(string c in new[]{"TABLE_SCHEM","TABLE_NAME","TABLE_TYPE"})t.Columns.Add(c,typeof(string));
   if(Scenario!="empty_family")foreach(string n in Names)t.Rows.Add("bethadba",n,"TABLE");
   t.Rows.Add("bethadba","efentradas_sensitive_other","TABLE");
   t.Rows.Add("other_schema","efsaidas","TABLE");
   return t;
  }
  if(name!="Columns"||restrictions.Length!=4||restrictions[1]!="bethadba"||Array.IndexOf(Names,restrictions[2])<0)throw new Exception("Column scope");
  foreach(string c in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME","TYPE_NAME"})t.Columns.Add(c,typeof(string));
  foreach(string c in new[]{"COLUMN_SIZE","NULLABLE","ORDINAL_POSITION","DECIMAL_DIGITS"})t.Columns.Add(c,typeof(int));
  if(Scenario!="empty_columns")for(int i=0;i<(Scenario=="column_limit"?1001:2);i++)
   t.Rows.Add("bethadba",restrictions[2],i==0?"codi_emp":"synthetic_key_"+i,"integer",10,0,i+1,0);
  return t;
 }
}
public sealed class TitleCatalogFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r", "").Trim();
  bool tables=q.StartsWith("SELECT TOP 16 "), keys=q.StartsWith("SELECT TOP 2049 "), relations=q.StartsWith("SELECT TOP 4097 ");
  if((!tables&&!keys&&!relations)||CommandTimeout!=40||Parameters.Count!=(relations?10:5)||q.Split('?').Length-1!=Parameters.Count)throw new Exception("Query contract");
  for(int i=0;i<Parameters.Count;i++){
   string expected=i%5==0?"bethadba":TitleCatalogFixtureConnection.Names[i%5-1];
   if(Parameters[i].OdbcType!=OdbcType.VarChar||Parameters[i].Size!=128||(string)Parameters[i].Value!=expected)throw new Exception("Parameter scope");
  }
  if(Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|SYSUSERPASSWORD)\b")||q.Contains("SELECT *")||q.Contains("FROM bethadba"))throw new Exception("Unsafe query");
  foreach(Match m in Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)"))
   if(Array.IndexOf(new[]{"SYS.SYSTAB","SYS.SYSUSER","SYS.SYSIDX","SYS.SYSIDXCOL","SYS.SYSTABCOL","SYS.SYSFKEY"},m.Groups[1].Value)<0)throw new Exception("Noncatalog source");
  DataTable t=new DataTable();
  string[] numeric;
  if(tables){
   numeric=new[]{"table_id","table_type"};
   foreach(string c in new[]{"table_id","table_name","table_type"})t.Columns.Add(c,Array.IndexOf(numeric,c)>=0?typeof(long):typeof(string));
   int count=TitleCatalogFixtureConnection.Scenario=="missing_table"?3:4;
   for(int i=0;i<count;i++)t.Rows.Add((long)i+1,TitleCatalogFixtureConnection.Names[i],TitleCatalogFixtureConnection.Scenario=="wrong_table_type"?2L:1L);
  }else if(keys){
   numeric=new[]{"table_id","index_id","index_category","unique_code","sequence","column_id","primary_column_id"};
   foreach(string c in new[]{"table_id","index_id","index_category","unique_code","not_enforced","index_name","sequence","column_id","column_name","primary_column_id"})t.Columns.Add(c,Array.IndexOf(numeric,c)>=0?typeof(long):typeof(string));
   int count=TitleCatalogFixtureConnection.Scenario=="key_limit"?2049:4;
   for(int i=0;i<count;i++)t.Rows.Add((long)i%4+1,0L,1L,1L,"N","synthetic_pk",0L,1L,"codi_emp",DBNull.Value);
  }else{
   numeric=new[]{"foreign_table_id","foreign_index_id","primary_table_id","primary_index_id","match_type","sequence","foreign_column_id","primary_column_id"};
   foreach(string c in new[]{"foreign_table_id","foreign_index_id","primary_table_id","primary_index_id","foreign_schema","foreign_table","primary_schema","primary_table","match_type","check_on_commit","nulls","sequence","foreign_column_id","foreign_column","primary_column_id","primary_column"})t.Columns.Add(c,Array.IndexOf(numeric,c)>=0?typeof(long):typeof(string));
   int count=TitleCatalogFixtureConnection.Scenario=="relation_limit"?4097:1;
   for(int i=0;i<count;i++)t.Rows.Add(4L,1L,1L,0L,"bethadba","efentradaspar","bethadba","efentradas",0L,"N","N",0L,1L,"codi_emp",1L,"codi_emp");
  }
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [TitleCatalogFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-title-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [TitleCatalogFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0
    if ($Scenario -eq 'compact') {& $source -Compact} else {& $source}
    exit $LASTEXITCODE
}
$parseErrors=$null;$parseTokens=$null
[void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$parseTokens,[ref]$parseErrors)
if (@($parseErrors).Count -ne 0) { throw 'PowerShell syntax errors.' }
$download=Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
[void][IO.Directory]::CreateDirectory($download)
$evidence=@()
foreach ($case in @('success','compact','empty_family','empty_columns','column_limit','missing_table','wrong_table_type','key_limit','relation_limit','driver_failure')) {
    $before=@(Get-ChildItem -LiteralPath $download -Directory -Filter 'CICA-CONTAD-Titulos-Estrutura-*' | ForEach-Object {$_.FullName})
    try {
        $saved=$ErrorActionPreference
        try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
        $output=($lines | ForEach-Object {$_ | Out-String}) -join "`n"
        if ($output -match 'synthetic-title-secret|PWD=|Password=') { throw 'Secret exposed.' }
        $success=$case -in @('success','compact')
        if (($code -eq 0) -ne $success) {throw ('Unexpected result: '+$case+': '+$output)}
        $stdout=@($lines | Where-Object {$_ -is [string]})
        $result=($stdout -join "`n") | ConvertFrom-Json
        if ($success) {
            if ($case -eq 'compact') {
                $buffer=New-Object IO.MemoryStream
                $packedBytes=[Convert]::FromBase64String($result.data)
                $buffer.Write($packedBytes,0,$packedBytes.Length);$buffer.Position=0
                $gzip=New-Object IO.Compression.GZipStream($buffer,[IO.Compression.CompressionMode]::Decompress)
                $reader=New-Object IO.StreamReader($gzip,[Text.Encoding]::UTF8)
                try {$raw=$reader.ReadToEnd()} finally {$reader.Dispose();$gzip.Dispose();$buffer.Dispose()}
                $sha=[Security.Cryptography.SHA256]::Create()
                try {$hash=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($raw)))).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
                if ($hash -ne $result.sha256) {throw 'Transport hash mismatch.'}
                $report=$raw | ConvertFrom-Json
                if ($report.business_values_selected -ne $false -or $report.objects.Count -ne 4 -or $report.objects[0].columns.Count -ne 2) {throw 'Unexpected metadata report.'}
            } elseif ($result.tables.Count -ne 4 -or $result.columns -ne 8 -or $result.keys -ne 4 -or $result.relations -ne 1) {throw 'Unexpected catalog counts.'}
        } elseif ($result.completed -ne $false) {throw 'Failure reported complete.'}
        $evidence += [ordered]@{scenario=$case;passed=$true}
    } finally {
        @(Get-ChildItem -LiteralPath $download -Directory -Filter 'CICA-CONTAD-Titulos-Estrutura-*' | Where-Object {$_.FullName -notin $before}) | Remove-Item -Recurse -Force
    }
}
[ordered]@{version='contad-title-catalog-tests-v1';passed=$true;scenarios=$evidence} | ConvertTo-Json -Depth 4
