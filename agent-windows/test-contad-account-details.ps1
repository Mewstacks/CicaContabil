#requires -Version 5.1
<# CI ONLY: execute the real cadastral reader against synthetic ODBC and private local files. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') {throw 'Ensaio exclusivo de CI Windows descartavel; nao executar no SVAPL02.'}
$source=Join-Path $PSScriptRoot 'inspect-contad-account-details.ps1'
function Get-FixtureSourceText {
    $text=[IO.File]::ReadAllText($source)
    $expected="`$expectedCompanyCodeSha256='4ab91c9e80c1b20275c5878b3ec3f844deec7f6b155d94fdb90b79fbf6626f55'"
    if ([regex]::Matches($text,[regex]::Escape($expected)).Count -ne 1) {throw 'Unexpected production scope literal.'}
    # Replace only the approved selector hash in a disposable copy, never publish
    # real company codes or weaken the production script's fixed scope.
    return $text.Replace($expected,"`$expectedCompanyCodeSha256='794ea11f50892913aa01dd78f0835597272e0b1dcdb39169ca982253ec04e44b'")
}
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
using System.Data.Odbc;
using System.Text.RegularExpressions;
public sealed class AccountDetailsFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-private-password must never leak");}
 public void Close(){}
 public void Dispose(){}
 public AccountDetailsFixtureCommand CreateCommand(){return new AccountDetailsFixtureCommand();}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba")throw new Exception("Metadata scope");
  string[] cols;
  switch(r[2]){
   case "geempre":cols=new[]{"CODI_EMP","STAT_EMP"};break;
   case "ctconciliacao_conta":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","CODI_CTA"};break;
   case "ctcontas":cols=new[]{"CODI_EMP","CODI_CTA","NOME_CTA","CLAS_CTA","TIPO_CTA","SITUACAO_CTA","DATAINATIVA_CTA"};break;
   case "ctcontacaixa":cols=new[]{"CODI_EMP","CODI_CTA","SELE_CTA","TIPO_CONTA_CAIXA"};break;
   case "ctcontacaixa_conta_bancaria":cols=new[]{"CODI_EMP","I_CONTA_CAIXA","I_SEQUENCIAL_CONTA_BANCARIA","AGENCIA","IDENTIFICADOR_CONTA","I_BANCO"};break;
   case "ctlista_bancos_banco_central":cols=new[]{"I_BANCO","CODIGO_BANCO","DESCRICAO_BANCO"};break;
   default:throw new Exception("Unexpected table");
  }
  var t=new DataTable();foreach(string key in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(key,typeof(string));
  foreach(string col in cols){if(Scenario=="missing_column"&&col=="AGENCIA")continue;t.Rows.Add("bethadba",r[2],col);}return t;
 }
}
public sealed class AccountDetailsFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 public static int Reads;
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 private DataTable Table(params Type[] types){var t=new DataTable();for(int i=0;i<types.Length;i++)t.Columns.Add("c"+i,types[i]);return t;}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r","").Trim(),s=AccountDetailsFixtureConnection.Scenario;
  bool companies=q.StartsWith("SELECT TOP 501 "),configured=q.Contains("FROM bethadba.CTCONCILIACAO_CONTA q"),cash=q.Contains("FROM bethadba.ctcontacaixa c"),banks=q.Contains("FROM bethadba.CTCONTACAIXA_CONTA_BANCARIA b");
  if((!companies&&!configured&&!cash&&!banks)||CommandTimeout!=40||Parameters.Count!=1||Parameters[0].OdbcType!=OdbcType.VarChar||(string)Parameters[0].Value!="A"||!q.Contains("WHERE g.stat_emp=?"))throw new Exception("Query scope");
  if(Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|CTLANCTO|CTEXTRATO|VLOR_LAN|VALOR|SALDO|CGCE_EMP|PASSWORD)\b")||q.Contains("SELECT *"))throw new Exception("Forbidden values/write");
  foreach(Match m in Regex.Matches(q,@"(?i)\b(?:FROM|JOIN)\s+(\S+)"))if(Array.IndexOf(new[]{"bethadba.geempre","bethadba.CTCONCILIACAO_CONTA","bethadba.ctcontas","bethadba.ctcontacaixa","bethadba.CTCONTACAIXA_CONTA_BANCARIA","bethadba.CTLISTA_BANCOS_BANCO_CENTRAL"},m.Groups[1].Value)<0)throw new Exception("Unexpected source");
  if(configured&&!q.Contains("c.codi_emp=q.CODI_EMP_PLANO AND c.codi_cta=q.CODI_CTA"))throw new Exception("Chart composite key");
  if(banks&&!q.Contains("k.I_BANCO=b.I_BANCO"))throw new Exception("Bank catalog key");
  if((cash||banks)&&q.Contains("bethadba.ctcontas"))throw new Exception("Inferred cash-to-ledger mapping");
  Reads++;DataTable t;
  if(companies){
   t=Table(s=="number_type"?typeof(string):typeof(long));int count=s=="company_limit"?501:s=="company_count_changed"?147:146;
   for(int i=1;i<=count;i++)t.Rows.Add(s=="number_type"?(object)i.ToString():(object)(long)(s=="company_codes_changed"&&i==146?999:i));
   if(s=="duplicate_company")t.Rows.Add(1L);return t.CreateDataReader();
  }
  if(configured){
   t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime));
   if(s=="empty_details")return t.CreateDataReader();int count=s=="account_limit"?5001:1;
   for(int i=0;i<count;i++){
    bool missing=s=="missing_chart";
    t.Rows.Add(s=="account_outside"?999L:1L,100L,(long)i+8,missing?(object)DBNull.Value:(object)((long)i+8),missing?(object)DBNull.Value:s=="invalid_text"?"synthetic-private-name\n":"synthetic-private-name",missing?(object)DBNull.Value:"001.0008 ",missing?(object)DBNull.Value:"A",missing?(object)DBNull.Value:"A",s=="inactive_date"?(object)new DateTime(2026,10,1):DBNull.Value);
   }
   if(s=="account_fanout")t.ImportRow(t.Rows[0]);
   if(s=="source_changed"&&Reads>4)t.Rows[0][4]="changed-private-name";
   return t.CreateDataReader();
  }
  if(cash){
   t=Table(typeof(long),typeof(long),typeof(string),typeof(long));
   if(s=="empty_details")return t.CreateDataReader();int count=s=="cash_limit"?5001:1;
   for(int i=0;i<count;i++)t.Rows.Add(s=="cash_outside"?999L:1L,(long)i+8,s=="null_cash_codes"?(object)DBNull.Value:"S",s=="null_cash_codes"?(object)DBNull.Value:0L);
   if(s=="cash_duplicate")t.ImportRow(t.Rows[0]);return t.CreateDataReader();
  }
  t=Table(typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(long),typeof(long),typeof(long),typeof(string));
  if(s=="empty_details"||s=="no_bank_references")return t.CreateDataReader();int bankCount=s=="bank_limit"?20001:2;
  for(int i=0;i<bankCount;i++){
   bool missing=s=="missing_bank",none=s=="null_bank_id";
   t.Rows.Add(s=="bank_outside"?999L:1L,s=="orphan_cash"?99L:8L,(long)i,"0001","0000123-0",none?(object)DBNull.Value:7L,missing||none?(object)DBNull.Value:7L,missing||none?(object)DBNull.Value:0L,missing||none?(object)DBNull.Value:"synthetic-private-bank");
  }
  if(s=="bank_fanout")t.ImportRow(t.Rows[0]);return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [AccountDetailsFixtureConnection]::Scenario=$Scenario
    function global:Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-private-password' -AsPlainText -Force))}
    function global:New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [AccountDetailsFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $fixtureFolder=Join-Path $env:RUNNER_TEMP ('cica-account-details-fixture-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($fixtureFolder)
    $fixtureSource=Join-Path $fixtureFolder 'inspect-contad-account-details.ps1'
    [IO.File]::WriteAllText($fixtureSource,(Get-FixtureSourceText),[Text.UTF8Encoding]::new($false))
    try {$global:LASTEXITCODE=0; & $fixtureSource; $resultCode=$LASTEXITCODE}
    finally {Remove-Item -LiteralPath $fixtureFolder -Recurse -Force}
    exit $resultCode
}
$tokens=$null; $errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw ($errors | Out-String)}
$success=@('success','empty_details','no_bank_references','missing_chart','missing_bank','null_bank_id','null_cash_codes','orphan_cash','inactive_date')
$cases=$success+@('missing_column','driver_failure','company_limit','company_count_changed','company_codes_changed','duplicate_company','number_type','account_limit','account_outside','account_fanout','invalid_text','source_changed','cash_limit','cash_outside','cash_duplicate','bank_limit','bank_outside','bank_fanout')
$evidence=@()
foreach ($case in $cases) {
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue'; $lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1); $code=$LASTEXITCODE}
    finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    foreach ($secret in @('synthetic-private-password','synthetic-private-name','synthetic-private-bank','0000123-0')) {if ($output.Contains($secret)) {throw ('Private content leaked: '+$case)}}
    $json=@($output -split '\r?\n' | Where-Object {$_.StartsWith('{')})
    if ($json.Count -ne 1) {throw ('Missing safe receipt: '+$case)}
    $receipt=$json[0] | ConvertFrom-Json
    if ($case -in $success) {
        if ($code -ne 0 -or -not $receipt.completed -or -not $receipt.two_reads_identical -or $receipt.companies -ne 146) {
            throw ('Expected success: {0}; exit={1}; completed={2}; stage={3}; reason={4}; types={5}' -f $case,$code,$receipt.completed,$receipt.stage,$receipt.reason_code,($receipt.exception_types -join ','))
        }
        $report=$receipt.report_file; $folder=Split-Path $report
        $expectedRoot=Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
        if ((Split-Path $folder) -ne $expectedRoot -or (Split-Path $folder -Leaf) -notmatch '^CICA-CONTAD-Contas-Detalhes-[a-f0-9]{32}$') {throw 'Unexpected fixture report path.'}
        try {
            if ((Get-FileHash -LiteralPath $report -Algorithm SHA256).Hash.ToLowerInvariant() -cne $receipt.sha256 -or (Get-Item -LiteralPath $report).Length -ne $receipt.bytes) {throw 'Private report integrity failed.'}
            $acl=Get-Acl -LiteralPath $folder
            if (-not $acl.AreAccessRulesProtected) {throw 'Private ACL inheritance remains active.'}
            $allowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
            foreach ($rule in $acl.Access) {if ($rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $allowed) {throw 'Unexpected report access.'}}
            $data=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
            foreach ($flag in @('cash_to_ledger_mapping_inferred','bank_association_approved','account_meanings_approved','human_reviewed','financial_collection_enabled','financial_values_selected','agent_configuration_read','erp_write_performed','uploaded')) {if ($data.$flag -ne $false) {throw ('Unsafe flag: '+$flag)}}
            $hasher=[Security.Cryptography.SHA256]::Create()
            try {$fixtureHash=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes((Get-FixtureSourceText))))).Replace('-','').ToLowerInvariant()}
            finally {$hasher.Dispose()}
            if ($data.script_sha256 -ne $fixtureHash -or $data.company_codes_sha256 -ne '794ea11f50892913aa01dd78f0835597272e0b1dcdb39169ca982253ec04e44b') {throw 'Script/scope provenance mismatch.'}
            if ($case -eq 'success') {
                if ($data.snapshot.bank_references.Count -ne 2 -or $data.snapshot.cash_accounts[0].bank_reference_count -ne 2 -or $data.snapshot.bank_references[0].agency_raw -cne '0001' -or $data.snapshot.bank_references[0].account_identifier_raw -cne '0000123-0' -or $data.snapshot.bank_references[0].bank_code_raw -ne 0 -or $data.snapshot.configured_accounts[0].classification_raw -cne '001.0008 ') {throw 'Multiplicity, raw strings or numeric zero lost.'}
            }
            if ($case -eq 'empty_details' -and ($data.snapshot.configured_accounts.Count -ne 0 -or $data.snapshot.cash_accounts.Count -ne 0 -or $data.snapshot.bank_references.Count -ne 0)) {throw 'Invented source records.'}
            if ($case -eq 'no_bank_references' -and $data.snapshot.cash_accounts[0].bank_reference_count -ne 0) {throw 'Zero references changed.'}
            if ($case -eq 'missing_chart' -and $receipt.missing_chart_accounts -ne 1) {throw 'Missing chart hidden.'}
            if ($case -in @('missing_bank','null_bank_id') -and $receipt.missing_bank_catalogue -ne 2) {throw 'Missing bank hidden.'}
            if ($case -eq 'orphan_cash' -and $receipt.missing_cash_keys -ne 2) {throw 'Orphan cash hidden.'}
            if ($case -eq 'inactive_date' -and $data.snapshot.configured_accounts[0].inactive_on_raw -cne '2026-10-01') {throw 'Source date changed.'}
        } finally {Remove-Item -LiteralPath $folder -Recurse -Force}
    } elseif ($code -eq 0 -or $receipt.completed -or -not $receipt.reason_code -or $receipt.report_file) {throw ('Failure accepted: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation'; [void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false;private_fixtures_removed=$true;fixture_company_scope_hash_replaced=$true;production_source_unchanged=$true} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-account-details.json') -Encoding UTF8
Write-Host 'Account details: fixed SELECTs, scope, cardinality, two reads, private ACL, zero preservation and safe diagnostics passed.'
