#requires -Version 5.1
<# Synthetic ODBC contract on disposable Windows. Never use a real ERP or agent configuration. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'inspect-contad-branch-accounts.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
public sealed class BranchFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-branch-secret must not leak");}
 public void Dispose(){}
 public BranchFixtureCommand CreateCommand(){return new BranchFixtureCommand();}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba"||r[2]!="ctlancto")throw new Exception("Metadata scope");
  var t=new DataTable();foreach(string s in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(s,typeof(string));
  foreach(string c in new[]{"CODI_EMP","CODI_EMP_PLANO","FILI_LAN","DATA_LAN","CDEB_LAN","CCRE_LAN"}){if(Scenario=="missing_column"&&c=="FILI_LAN")continue;t.Rows.Add("bethadba","ctlancto",c);}
  return t;
 }
}
public sealed class BranchFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 public static int Reads;
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r","").Trim(),s=BranchFixtureConnection.Scenario;
  bool debit=q.Contains("l.cdeb_lan<>0"),credit=q.Contains("l.ccre_lan<>0");
  if(debit==credit||!q.StartsWith("SELECT TOP 20001 ")||CommandTimeout!=60||Parameters.Count!=8)throw new Exception("Query contract");
  long[] expected={25,42,129,147,280,293};
  for(int i=0;i<6;i++)if(Parameters[i].OdbcType!=OdbcType.Int||Convert.ToInt64(Parameters[i].Value)!=expected[i])throw new Exception("Company scope");
  if(Parameters[6].OdbcType!=OdbcType.Date||Parameters[7].OdbcType!=OdbcType.Date||(DateTime)Parameters[6].Value!=new DateTime(2026,9,1)||(DateTime)Parameters[7].Value!=new DateTime(2026,11,1))throw new Exception("Period scope");
  if(!q.Contains("l.codi_emp IN (?,?,?,?,?,?) AND l.data_lan>=? AND l.data_lan<?"))throw new Exception("Where scope");
  if(System.Text.RegularExpressions.Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|PASSWORD|VLOR_LAN|CHIS_LAN|NDOC_LAN|CGCE_EMP|NOME_EMP|NOME_CTA|AGENCIA|IDENTIFICADOR_CONTA)\b")||q.Contains("SELECT *"))throw new Exception("Forbidden values/write");
  foreach(System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)"))
   if(m.Groups[1].Value!="bethadba.ctlancto")throw new Exception("Source scope");
  Reads++;
  var t=new DataTable();
  for(int i=0;i<7;i++)t.Columns.Add("c"+i,typeof(long));
  if(s=="empty")return t.CreateDataReader();
  if(s=="row_limit"){for(int i=0;i<20001;i++)t.Rows.Add(25L,25L,25L,(long)i+1,2026L,9L,1L);return t.CreateDataReader();}
  if(s=="large_output"){for(int i=0;i<3000;i++)t.Rows.Add(280L,280L,(long)(i%5)+191,(long)i+1,2026L,9L,3L);return t.CreateDataReader();}
  t.Rows.Add(25L,25L,25L,debit?8L:9L,2026L,9L,12L);
  t.Rows.Add(25L,25L,1002L,debit?8L:9L,2026L,9L,s=="source_changed"&&Reads>2?5L:4L);
  if(s=="outside_company")t.Rows.Add(999L,999L,999L,8L,2026L,9L,1L);
  if(s=="outside_period")t.Rows.Add(25L,25L,25L,8L,2026L,11L,1L);
  if(s=="duplicate")t.Rows.Add(25L,25L,25L,debit?8L:9L,2026L,9L,1L);
  if(s=="zero_count")t.Rows.Add(42L,42L,42L,8L,2026L,9L,0L);
  if(s=="null_field")t.Rows.Add(42L,42L,DBNull.Value,8L,2026L,9L,1L);
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [BranchFixtureConnection]::Scenario=$Scenario
    function Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-branch-secret' -AsPlainText -Force))}
    function New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [BranchFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE=0
    & $source
    exit $LASTEXITCODE
}
$evidence=@()
$cases=@('success','empty','large_output','missing_column','outside_company','outside_period','duplicate','zero_count','null_field','row_limit','source_changed','driver_failure')
foreach ($case in $cases) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1);$code=$LASTEXITCODE} finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    if ($output.Contains('synthetic-branch-secret')) {throw 'Credential or raw diagnostic leaked.'}
    $matches=@($output -split '\r?\n' | Where-Object {$_.StartsWith('{')})
    if ($matches.Count -ne 1) {throw ('Missing safe JSON: '+$case)}
    $result=$matches[0] | ConvertFrom-Json
    if ($case -in @('success','empty','large_output')) {
        if ($code -ne 0 -or $result.version -ne 'contad-branch-accounts-transfer-v1') {throw ('Wrong success: '+$case)}
        $buffer=[IO.MemoryStream]::new([Convert]::FromBase64String($result.data),$false)
        $gzip=[IO.Compression.GZipStream]::new($buffer,[IO.Compression.CompressionMode]::Decompress)
        $reader=[IO.StreamReader]::new($gzip,[Text.Encoding]::UTF8)
        try {$raw=$reader.ReadToEnd()} finally {$reader.Dispose();$gzip.Dispose();$buffer.Dispose()}
        $bytes=[Text.Encoding]::UTF8.GetBytes($raw);$hasher=[Security.Cryptography.SHA256]::Create()
        try {$sha=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()} finally {$hasher.Dispose()}
        if ($result.bytes -ne $bytes.Length -or $result.sha256 -cne $sha) {throw 'Transfer integrity failed.'}
        $profile=$raw | ConvertFrom-Json
        if (-not $profile.completed -or -not $profile.two_reads_identical -or $profile.period_start -ne '2026-09-01' -or $profile.period_end_exclusive -ne '2026-11-01' -or $profile.company_codes.Count -ne 6) {throw ('Wrong profile: '+$case)}
        foreach ($flag in @('bank_association_approved','financial_values_selected','names_or_documents_selected','agent_configuration_read','erp_write_performed','uploaded')) {if ($profile.$flag -ne $false) {throw ('Unsafe flag: '+$case)}}
        $saved=Join-Path ([Environment]::GetFolderPath('Desktop')) 'CICA-CONTAD-Filiais\filiais-contas.txt'
        if ((Get-Content -LiteralPath $saved -Raw).Trim() -cne $matches[0].Trim()) {throw 'Saved transfer differs from output.'}
        if ($case -eq 'success') {
            if ($profile.snapshot.debit_counts.Count -ne 2 -or $profile.snapshot.credit_counts.Count -ne 2) {throw 'Coverage lost.'}
            $branches=@($profile.snapshot.debit_counts | ForEach-Object {$_.branch_code} | Sort-Object)
            if (($branches -join ',') -ne '25,1002' -or $profile.snapshot.debit_counts[0].account_code -ne 8 -or $profile.snapshot.credit_counts[0].account_code -ne 9) {throw 'Branch/account mapping lost.'}
        }
        if ($case -eq 'empty' -and ($profile.snapshot.debit_counts.Count -ne 0 -or $profile.snapshot.credit_counts.Count -ne 0)) {throw 'Empty source fabricated counts.'}
        if ($case -eq 'large_output' -and $profile.snapshot.debit_counts.Count -ne 3000) {throw 'Large output truncated.'}
    } elseif ($code -eq 0 -or $result.completed -or -not $result.reason_code) {throw ('Failure accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-branch-accounts.json') -Encoding UTF8
Write-Host 'Branch accounts: fixed scope, both sides, bounds, two reads, transfer integrity and redaction passed.'
exit 0
