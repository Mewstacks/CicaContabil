#requires -Version 5.1
<# CI ONLY: execute the real cadastral reader against synthetic ODBC and private local files. #>
[CmdletBinding()]
param([string]$Scenario='')
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') {throw 'Ensaio exclusivo de CI Windows descartavel; nao executar no SVAPL02.'}
$source=Join-Path $PSScriptRoot 'inspect-contad-chart-discovery.ps1'
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
public sealed class ChartDiscoveryFixtureConnection:IDisposable {
 public static string Scenario;
 public int ConnectionTimeout {get;set;}
 public void Open(){if(ConnectionTimeout!=20)throw new Exception("Timeout");if(Scenario=="driver_failure")throw new Exception("synthetic-private-password must never leak");}
 public void Close(){}
 public void Dispose(){}
 public ChartDiscoveryFixtureCommand CreateCommand(){return new ChartDiscoveryFixtureCommand();}
 public DataTable GetSchema(string kind,string[] r){
  if(kind!="Columns"||r.Length!=4||r[1]!="bethadba")throw new Exception("Metadata scope");
  string[] cols;
  switch(r[2]){
   case "geempre":cols=new[]{"CODI_EMP","STAT_EMP"};break;
   case "ctparmto":cols=new[]{"CODI_EMP","CODI_PAD","COMP_PAD","I_PLANOCONTAS","CCXA_PAR","FILI_PAR"};break;
   case "ctlancto":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","FILI_LAN","DATA_LAN"};break;
   case "ctplanocontas":cols=new[]{"CODI_EMP","CODI_CTA","I_PLANOCONTAS","NOME_CTA","CLAS_CTA","TIPO_CTA","SITUACAO_CTA","DATAINATIVA_CTA"};break;
   case "ctnatureza_conta":cols=new[]{"CODI_EMP","ORDEM","CLAS_CTA","NATUREZA","GRUPO"};break;
   case "ctcontas_equivalentes":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","CODI_CTA"};break;
   case "ctconciliacao_conta":cols=new[]{"CODI_EMP","CODI_EMP_PLANO","CODI_CTA"};break;
   case "ctcontas":cols=new[]{"CODI_EMP","CODI_CTA","NOME_CTA","CLAS_CTA","TIPO_CTA","SITUACAO_CTA","DATAINATIVA_CTA"};break;
   case "ctcontacaixa":cols=new[]{"CODI_EMP","CODI_CTA","SELE_CTA","TIPO_CONTA_CAIXA"};break;
   case "ctcontacaixa_conta_bancaria":cols=new[]{"CODI_EMP","I_CONTA_CAIXA","I_SEQUENCIAL_CONTA_BANCARIA","AGENCIA","IDENTIFICADOR_CONTA","I_BANCO"};break;
   case "ctlista_bancos_banco_central":cols=new[]{"I_BANCO","CODIGO_BANCO","DESCRICAO_BANCO"};break;
   case "ctparmto_contas_iceberg":cols=new[]{"CODI_EMP","CODI_CTA","CODI_FIL","I_BANCO","DATA_INICIO_INTEGRACAO"};break;
   default:throw new Exception("Unexpected table");
  }
  var t=new DataTable();foreach(string key in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME"})t.Columns.Add(key,typeof(string));
  foreach(string col in cols){if(Scenario=="missing_column"&&col=="AGENCIA")continue;t.Rows.Add("bethadba",r[2],col);}return t;
 }
}
public sealed class ChartDiscoveryFixtureCommand:IDisposable {
 public string CommandText {get;set;}
 public int CommandTimeout {get;set;}
 public static int Reads; public static int CompanyReads;
 private OdbcCommand holder=new OdbcCommand();
 public OdbcParameterCollection Parameters {get{return holder.Parameters;}}
 private DataTable Table(params Type[] types){var t=new DataTable();for(int i=0;i<types.Length;i++)t.Columns.Add("c"+i,types[i]);return t;}
 public IDataReader ExecuteReader(){
  string q=CommandText.Replace("\r","").Trim(),s=ChartDiscoveryFixtureConnection.Scenario;
  bool companies=q.StartsWith("SELECT TOP 501 "),configured=q.Contains("FROM bethadba.CTCONCILIACAO_CONTA q"),cash=q.Contains("FROM bethadba.ctcontacaixa c"),banks=q.Contains("FROM bethadba.CTCONTACAIXA_CONTA_BANCARIA b"),integrations=q.Contains("FROM bethadba.CTPARMTO_CONTAS_ICEBERG i");
  bool equivalents=q.Contains("FROM bethadba.CTCONTAS_EQUIVALENTES e"),usage=q.Contains("FROM bethadba.ctlancto l"),chart=q.Contains("FROM bethadba.ctcontas c WHERE"),templates=q.Contains("FROM bethadba.CTPLANOCONTAS c WHERE"),nature=q.Contains("FROM bethadba.ctnatureza_conta n WHERE"),metadata=q.Contains("FROM SYS.");
  bool ownerQuery=chart||templates||nature;
  if(CommandTimeout!=40||(!companies&&!configured&&!cash&&!banks&&!integrations&&!equivalents&&!usage&&!ownerQuery&&!metadata))throw new Exception("Query scope");
  if(Regex.IsMatch(q,@"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|CTEXTRATO|VLOR_LAN|CHIS_LAN|NDOC_LAN|VALOR|SALDO(?:_INICIAL)?|CGCE_EMP|PASSWORD)\b")||q.Contains("SELECT *"))throw new Exception("Forbidden values/write");
  if(metadata) return Metadata(q,s);
  if(ownerQuery){
   if(Parameters.Count<1||Parameters.Count>100||Regex.Matches(q,@"\?").Count!=Parameters.Count||!q.Contains("codi_emp IN (" )&&!q.Contains("CODI_EMP IN ("))throw new Exception("Owner scope");
   foreach(OdbcParameter p in Parameters)if(p.OdbcType!=OdbcType.Int||(long)p.Value<1||(long)p.Value>902)throw new Exception("Owner binding");
   if(q.Contains("CTCONCILIACAO")||q.Contains("tipo_cta=")||q.Contains("nome_cta LIKE"))throw new Exception("Filtered catalogue");
  }else{
   if(Parameters.Count!=(usage?3:1)||Parameters[0].OdbcType!=OdbcType.VarChar||(string)Parameters[0].Value!="A"||!q.Contains("WHERE g.stat_emp=?"))throw new Exception("Active scope");
   if(usage&&(Parameters[1].OdbcType!=OdbcType.Date||(DateTime)Parameters[1].Value!=new DateTime(2026,9,1)||Parameters[2].OdbcType!=OdbcType.Date||(DateTime)Parameters[2].Value!=new DateTime(2026,12,1)||!q.Contains("l.data_lan>=? AND l.data_lan<?")||!q.Contains("YEAR(l.data_lan),MONTH(l.data_lan),COUNT(*)")))throw new Exception("Usage window");
  }
  if(configured&&!q.Contains("c.codi_emp=q.CODI_EMP_PLANO AND c.codi_cta=q.CODI_CTA"))throw new Exception("Chart composite key");
  if(banks&&!q.Contains("k.I_BANCO=b.I_BANCO"))throw new Exception("Bank catalog key");
  if((cash||banks)&&q.Contains("bethadba.ctcontas"))throw new Exception("Inferred cash-to-ledger mapping");
  if(integrations&&(!q.StartsWith("SELECT TOP 5001 i.CODI_EMP,i.CODI_CTA,i.CODI_FIL,i.I_BANCO,i.DATA_INICIO_INTEGRACAO\n")||Regex.Matches(q,@"(?i)\bJOIN\b").Count!=1))throw new Exception("Inferred integration mapping or extra values");
  Reads++;DataTable t;
  if(companies){
   CompanyReads++;t=Table(s=="number_type"?typeof(string):typeof(long),typeof(long),typeof(long),typeof(string),typeof(long),typeof(long),typeof(string));int count=s=="company_limit"?501:s=="company_count_changed"?147:146;
   for(int i=1;i<=count;i++){
    long c=s=="company_codes_changed"&&i==146?999:s=="company_order_reversed"?147-i:i;bool absent=c==146||s=="missing_parameters";
    t.Rows.Add(s=="number_type"?(object)c.ToString():(object)c,absent?(object)DBNull.Value:c,absent?(object)DBNull.Value:c==1?(object)900L:DBNull.Value,absent?(object)DBNull.Value:c==2?"S":"N",absent?(object)DBNull.Value:1L,absent?(object)DBNull.Value:c==2?(object)0L:DBNull.Value,absent?(object)DBNull.Value:"N");
   }
   if(s=="duplicate_company")t.ImportRow(t.Rows[0]);
   if(s=="parameter_changed"&&CompanyReads>1)t.Rows[0][3]="S";
   if(s=="missing_plan_id")t.Rows[0][4]=DBNull.Value;
   return t.CreateDataReader();
  }
  if(equivalents){
   t=Table(typeof(long),typeof(long),typeof(long));if(s=="empty_details")return t.CreateDataReader();
   int count=s=="equivalent_limit"?20001:1;for(int i=0;i<count;i++)t.Rows.Add(s=="equivalent_outside"?999L:1L,902L,(long)i+11);
   if(s=="equivalent_duplicate")t.ImportRow(t.Rows[0]);if(s=="equivalent_changed"&&CompanyReads>1)t.Rows[0][2]=12L;return t.CreateDataReader();
  }
  if(usage){
   t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(long),typeof(long));if(s=="empty_details")return t.CreateDataReader();
   int count=s=="usage_limit"?10001:2;for(int i=0;i<count;i++)t.Rows.Add(s=="usage_outside"?999L:1L,901L,(long)i,2026L,s=="usage_outside_month"?12L:(long)9+i%2,s=="usage_total_limit"?5000001L:1L);
   if(s=="usage_duplicate")t.ImportRow(t.Rows[0]);if(s=="usage_changed"&&CompanyReads>1)t.Rows[0][5]=2L;return t.CreateDataReader();
  }
  if(ownerQuery){
   if(nature){
    t=Table(typeof(long),typeof(long),typeof(string),typeof(string),typeof(string));
    if(s=="empty_details"||s=="empty_nature")return t.CreateDataReader();
    if(HasOwner(1)){int count=s=="nature_limit"?10001:1;for(int i=0;i<count;i++)t.Rows.Add(s=="nature_outside"?999L:1L,(long)i,"001 ","X","Z");
     if(s=="nature_duplicate")t.ImportRow(t.Rows[0]);if(s=="nature_changed"&&CompanyReads>1)t.Rows[0][3]="Y";}
    return t.CreateDataReader();
   }
   t=templates?Table(typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime)):Table(typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime));
   if(s=="empty_details"||s=="empty_catalogues")return t.CreateDataReader();
   foreach(long owner in new long[]{1,100,900,901,902}){
    if(!HasOwner(owner)||s=="missing_chart"&&owner==100)continue;
    int count=owner==1&&(s=="catalogue_limit"&&!templates||s=="template_limit"&&templates)?100001:1;
    for(int i=0;i<count;i++){
     long account=owner==900?9:owner==901?10:owner==902?11:8;
     long selectedOwner=s=="catalogue_outside"&&!templates||s=="template_outside"&&templates?999:owner;
     object name=s=="catalogue_null"&&!templates?(object)DBNull.Value:s=="template_name_limit"&&templates?new string('x',61):s=="catalogue_changed"&&!templates&&CompanyReads>1?"changed-private-name":"synthetic-private-name";
     if(templates)t.Rows.Add(selectedOwner,1L,account+i,name,"001.0008 ","A","A",DBNull.Value);
     else t.Rows.Add(selectedOwner,account+i,name,"001.0008 ","A","A",s=="inactive_date"?(object)new DateTime(2026,10,1):DBNull.Value);
    }
   }
   if(t.Rows.Count>0){
    if(s=="catalogue_duplicate"&&!templates||s=="template_duplicate"&&templates)t.ImportRow(t.Rows[0]);
    if(templates&&s=="multiple_templates"&&HasOwner(1)){var row=t.NewRow();row.ItemArray=(object[])t.Rows[0].ItemArray.Clone();row[1]=2L;t.Rows.Add(row);}
   }
   return t.CreateDataReader();
  }
  if(configured){
   t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime));
   if(s=="empty_details")return t.CreateDataReader();int count=s=="account_limit"?5001:1;
   for(int i=0;i<count;i++){
    bool missing=s=="missing_chart"||s=="empty_catalogues";
    t.Rows.Add(s=="account_outside"?999L:1L,100L,(long)i+8,missing?(object)DBNull.Value:(object)((long)i+8),missing?(object)DBNull.Value:s=="invalid_text"?"synthetic-private-name\n":"synthetic-private-name",missing?(object)DBNull.Value:"001.0008 ",missing?(object)DBNull.Value:"A",missing?(object)DBNull.Value:"A",s=="inactive_date"?(object)new DateTime(2026,10,1):DBNull.Value);
   }
   if(s=="account_fanout")t.ImportRow(t.Rows[0]);
   if(s=="source_changed"&&CompanyReads>1)t.Rows[0][4]="changed-private-name";
   return t.CreateDataReader();
  }
  if(cash){
   t=Table(typeof(long),typeof(long),typeof(string),typeof(long));
   if(s=="empty_details")return t.CreateDataReader();int count=s=="cash_limit"?5001:1;
   for(int i=0;i<count;i++)t.Rows.Add(s=="cash_outside"?999L:1L,(long)i+8,s=="null_cash_codes"?(object)DBNull.Value:"S",s=="null_cash_codes"?(object)DBNull.Value:0L);
   if(s=="cash_duplicate")t.ImportRow(t.Rows[0]);return t.CreateDataReader();
  }
  if(integrations){
   t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(DateTime));
   if(s=="empty_details"||s=="no_integrations")return t.CreateDataReader();int count=s=="integration_limit"?5001:2;
   for(int i=0;i<count;i++)t.Rows.Add(s=="integration_outside"?999L:2L,s=="integration_zero_codes"?0L:8L,(long)i,s=="integration_zero_codes"?0L:7L,s=="integration_null_start"?(object)DBNull.Value:s=="integration_invalid_date"?(object)new DateTime(2026,9,1,12,0,0):(object)new DateTime(2026,9,1));
   if(s=="integration_duplicate")t.ImportRow(t.Rows[0]);
   if(s=="integration_null_code")t.Rows[0][3]=DBNull.Value;
   if(s=="integration_changed"&&CompanyReads>1)t.Rows[0][4]=new DateTime(2026,9,2);
   return t.CreateDataReader();
  }
  t=Table(typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(long),typeof(long),typeof(long),typeof(string));
  if(s=="empty_details"||s=="no_bank_references")return t.CreateDataReader();int bankCount=s=="bank_limit"?20001:2;
  for(int i=0;i<bankCount;i++){
   bool missing=s=="missing_bank",none=s=="null_bank_id";
   t.Rows.Add(s=="bank_outside"?999L:1L,s=="orphan_cash"?99L:8L,(long)i,"0001","0000123-0",none?(object)DBNull.Value:7L,missing||none?(object)DBNull.Value:7L,missing||none?(object)DBNull.Value:0L,missing||none?(object)DBNull.Value:"synthetic-private-bank");
  }
  if(s=="bank_fanout")t.ImportRow(t.Rows[0]);return t.CreateDataReader();
 }
 private bool HasOwner(long id){foreach(OdbcParameter p in Parameters)if((long)p.Value==id)return true;return false;}
 private IDataReader Metadata(string q,string s){
  string[] targets={"CTPARMTO","CTPLANOCONTAS","CTNATUREZA_CONTA","CTCONTACAIXA","CTCONTACAIXA_CONTA_BANCARIA","CTPARMTO_CONTAS_ICEBERG","CTCONTAS_EQUIVALENTES"};
  bool tables=q.Contains("FROM SYS.SYSTAB t"),keys=q.Contains("FROM SYS.SYSIDX i"),relations=q.Contains("FROM SYS.SYSFKEY f");
  if(!tables&&!keys&&!relations||Parameters.Count!=(relations?16:8))throw new Exception("Metadata scope");
  for(int i=0;i<Parameters.Count;i++){string expected=i%8==0?"bethadba":targets[i%8-1];if(Parameters[i].OdbcType!=OdbcType.VarChar||(string)Parameters[i].Value!=expected)throw new Exception("Metadata parameters");}
  DataTable t;
  if(tables){t=Table(typeof(long),typeof(string),typeof(long));for(int i=0;i<7;i++)t.Rows.Add((long)i+1,s=="metadata_missing_target"&&i==6?"OTHER":targets[i],1L);return t.CreateDataReader();}
  if(keys){t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(long),typeof(long),typeof(string),typeof(long));
   t.Rows.Add(1L,0L,1L,2L,"N","ctparmto",0L,1L,"codi_emp",DBNull.Value);return t.CreateDataReader();}
  t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(long),typeof(string),typeof(string),typeof(long),typeof(long),typeof(string),typeof(long),typeof(string));
  int count=s=="metadata_limit"?4097:2;for(int i=0;i<count;i++)t.Rows.Add(7L,1L,99L,0L,"bethadba","CTCONTAS_EQUIVALENTES","bethadba","ctcontas",0L,"N","N",(long)i,(long)i+1,i==0?"CODI_EMP_PLANO":"CODI_CTA",(long)i+1,s=="metadata_changed"&&CompanyReads>1?"changed_column":i==0?"codi_emp":"codi_cta");
  return t.CreateDataReader();
 }
 public void Dispose(){holder.Dispose();}
}
'@
    [ChartDiscoveryFixtureConnection]::Scenario=$Scenario
    function global:Get-Credential {param($UserName,$Message);return [Management.Automation.PSCredential]::new('EXTERNO',(ConvertTo-SecureString 'synthetic-private-password' -AsPlainText -Force))}
    function global:New-Object {
        [CmdletBinding()]param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection') {return [ChartDiscoveryFixtureConnection]::new()}
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $fixtureFolder=Join-Path $env:RUNNER_TEMP ('cica-chart-discovery-fixture-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($fixtureFolder)
    $fixtureSource=Join-Path $fixtureFolder 'inspect-contad-chart-discovery.ps1'
    [IO.File]::WriteAllText($fixtureSource,(Get-FixtureSourceText),[Text.UTF8Encoding]::new($false))
    try {$global:LASTEXITCODE=0; & $fixtureSource; $resultCode=$LASTEXITCODE}
    finally {Remove-Item -LiteralPath $fixtureFolder -Recurse -Force}
    exit $resultCode
}
$tokens=$null; $errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw ($errors | Out-String)}
$success=@('missing_parameters','empty_catalogues','empty_nature','multiple_templates','success','company_order_reversed','empty_details','no_bank_references','missing_chart','missing_bank','null_bank_id','null_cash_codes','orphan_cash','inactive_date','integration_null_start','integration_zero_codes','no_integrations')
$cases=$success+@('parameter_changed','missing_plan_id','equivalent_limit','equivalent_outside','equivalent_duplicate','equivalent_changed','usage_limit','usage_outside','usage_outside_month','usage_total_limit','usage_duplicate','usage_changed','catalogue_limit','catalogue_outside','catalogue_null','catalogue_changed','catalogue_duplicate','template_limit','template_outside','template_name_limit','template_duplicate','nature_limit','nature_outside','nature_duplicate','nature_changed','metadata_missing_target','metadata_limit','metadata_changed','missing_column','driver_failure','company_limit','company_count_changed','company_codes_changed','duplicate_company','number_type','account_limit','account_outside','account_fanout','invalid_text','source_changed','cash_limit','cash_outside','cash_duplicate','bank_limit','bank_outside','bank_fanout','integration_limit','integration_outside','integration_duplicate','integration_null_code','integration_invalid_date','integration_changed')
$integrationFailures=@{integration_limit='ROW_LIMIT';integration_outside='INTEGRATION_SCOPE';integration_duplicate='INTEGRATION_CARDINALITY';integration_null_code='NULL_FIELD';integration_invalid_date='DATE_CONTRACT';integration_changed='SOURCE_CHANGED'}
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
        if ((Split-Path $folder) -ne $expectedRoot -or (Split-Path $folder -Leaf) -notmatch '^CICA-CONTAD-Planos-Contas-[a-f0-9]{32}$') {throw 'Unexpected fixture report path.'}
        try {
            if ((Get-FileHash -LiteralPath $report -Algorithm SHA256).Hash.ToLowerInvariant() -cne $receipt.sha256 -or (Get-Item -LiteralPath $report).Length -ne $receipt.bytes) {throw 'Private report integrity failed.'}
            $acl=Get-Acl -LiteralPath $folder
            if (-not $acl.AreAccessRulesProtected) {throw 'Private ACL inheritance remains active.'}
            $allowed=@([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
            foreach ($rule in $acl.Access) {if ($rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $allowed) {throw 'Unexpected report access.'}}
            $data=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
            foreach ($flag in @('nature_interpreted','chart_owner_mapping_inferred','cash_to_ledger_mapping_inferred','bank_association_approved','account_meanings_approved','human_reviewed','financial_collection_enabled','financial_values_selected','agent_configuration_read','erp_write_performed','uploaded')) {if ($data.$flag -ne $false) {throw ('Unsafe flag: '+$flag)}}
            $hasher=[Security.Cryptography.SHA256]::Create()
            try {$fixtureHash=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes((Get-FixtureSourceText))))).Replace('-','').ToLowerInvariant()}
            finally {$hasher.Dispose()}
            if ($data.script_sha256 -ne $fixtureHash -or $data.company_codes_sha256 -ne '794ea11f50892913aa01dd78f0835597272e0b1dcdb39169ca982253ec04e44b') {throw 'Script/scope provenance mismatch.'}
            $integrationProvenance=$data.provenance.integration_account_configurations
            if ($integrationProvenance.source -cne 'CTPARMTO_CONTAS_ICEBERG' -or $integrationProvenance.declared_foreign_keys_verified -ne $false -or $integrationProvenance.chart_owner_mapping_inferred -ne $false -or $integrationProvenance.bank_catalogue_link_inferred -ne $false) {throw 'Integration semantics inferred.'}
            if (@($data.snapshot.integration_account_configurations).Count -ne $receipt.integration_account_configurations) {throw 'Integration count mismatch.'}
            if ($data.period_start -cne '2026-09-01' -or $data.period_end_exclusive -cne '2026-12-01') {throw 'Usage period changed.'}
            if ($case -eq 'success') {
                if ($data.snapshot.chart_owners.Count -ne 149 -or $data.snapshot.chart_accounts.Count -ne 5 -or $data.snapshot.plan_template_accounts.Count -ne 5) {throw 'Full shared-owner catalogue incomplete or multiplied.'}
                if ($data.snapshot.observed_chart_usage.Count -ne 2 -or $data.snapshot.observed_chart_usage[1].month -ne 10 -or $data.snapshot.observed_chart_usage[1].branch_code -ne 1) {throw 'Observed month/branch multiplicity lost.'}
                if ($data.snapshot.companies[0].codi_pad_raw -ne 900 -or $data.snapshot.companies[0].comp_pad_raw -cne 'N' -or $data.snapshot.companies[1].cash_account_parameter_raw -ne 0 -or $data.snapshot.companies[145].configuration_rows -ne 0) {throw 'Parameter raw codes/missing state lost.'}
                if ($data.snapshot.nature_rules[0].nature_raw -cne 'X' -or $data.snapshot.nature_rules[0].group_raw -cne 'Z' -or $data.snapshot.equivalent_accounts[0].chart_company_code -ne 902) {throw 'Literal nature/equivalent reference lost.'}
                if ($data.snapshot.metadata.targets.Count -ne 7 -or $data.snapshot.metadata.relation_columns.Count -ne 2) {throw 'Metadata absent.'}
                if ($data.snapshot.bank_references.Count -ne 2 -or $data.snapshot.cash_accounts[0].bank_reference_count -ne 2 -or $data.snapshot.bank_references[0].agency_raw -cne '0001' -or $data.snapshot.bank_references[0].account_identifier_raw -cne '0000123-0' -or $data.snapshot.bank_references[0].bank_code_raw -ne 0 -or $data.snapshot.configured_accounts[0].classification_raw -cne '001.0008 ') {throw 'Multiplicity, raw strings or numeric zero lost.'}
                if ($data.snapshot.integration_account_configurations.Count -ne 2 -or $data.snapshot.integration_account_configurations[0].integration_started_on_raw -cne '2026-09-01' -or $data.snapshot.integration_account_configurations[0].integration_account_code_raw -ne 8 -or $data.snapshot.integration_account_configurations[0].integration_bank_id_raw -ne 7 -or $data.snapshot.integration_account_configurations[1].integration_branch_code_raw -ne 1) {throw 'Integration multiplicity, literal codes or date lost.'}
            }
            if ($case -eq 'missing_parameters' -and @($data.snapshot.companies | Where-Object {$_.configuration_rows -ne 0}).Count) {throw 'Parameters invented.'}
            if ($case -eq 'empty_catalogues' -and ($receipt.chart_accounts -ne 0 -or $receipt.plan_template_accounts -ne 0 -or $receipt.chart_owners -ne 149)) {throw 'Empty chart owners lost.'}
            if ($case -eq 'multiple_templates' -and @($data.snapshot.plan_template_accounts | Where-Object {$_.plan_id_raw -eq 2}).Count -ne 1) {throw 'Template id collapsed.'}
            if ($case -eq 'empty_details' -and ($data.snapshot.configured_accounts.Count -ne 0 -or $data.snapshot.cash_accounts.Count -ne 0 -or $data.snapshot.bank_references.Count -ne 0 -or $data.snapshot.integration_account_configurations.Count -ne 0)) {throw 'Invented source records.'}
            if ($case -eq 'no_integrations' -and $receipt.integration_account_configurations -ne 0) {throw 'Invented integration configurations.'}
            if ($case -eq 'integration_null_start' -and $null -ne $data.snapshot.integration_account_configurations[0].integration_started_on_raw) {throw 'Null integration date changed.'}
            if ($case -eq 'integration_zero_codes' -and ($data.snapshot.integration_account_configurations[0].integration_account_code_raw -ne 0 -or $data.snapshot.integration_account_configurations[0].integration_branch_code_raw -ne 0 -or $data.snapshot.integration_account_configurations[0].integration_bank_id_raw -ne 0)) {throw 'Integration numeric zero lost.'}
            if ($case -eq 'no_bank_references' -and $data.snapshot.cash_accounts[0].bank_reference_count -ne 0) {throw 'Zero references changed.'}
            if ($case -eq 'missing_chart' -and $receipt.missing_chart_accounts -ne 1) {throw 'Missing chart hidden.'}
            if ($case -in @('missing_bank','null_bank_id') -and $receipt.missing_bank_catalogue -ne 2) {throw 'Missing bank hidden.'}
            if ($case -eq 'orphan_cash' -and $receipt.missing_cash_keys -ne 2) {throw 'Orphan cash hidden.'}
            if ($case -eq 'inactive_date' -and $data.snapshot.configured_accounts[0].inactive_on_raw -cne '2026-10-01') {throw 'Source date changed.'}
        } finally {Remove-Item -LiteralPath $folder -Recurse -Force}
    } elseif ($code -eq 0 -or $receipt.completed -or -not $receipt.reason_code -or $receipt.report_file) {throw ('Failure accepted: '+$case)}
    if ($integrationFailures.ContainsKey($case) -and $receipt.reason_code -cne $integrationFailures[$case]) {throw ('Unexpected integration rejection: '+$case+'; '+$receipt.reason_code)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation'; [void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false;private_fixtures_removed=$true;fixture_company_scope_hash_replaced=$true;production_source_unchanged=$true} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-chart-discovery.json') -Encoding UTF8
Write-Host 'Chart discovery: fixed SELECTs, scope, cardinality, two reads, private ACL, zero preservation and safe diagnostics passed.'
# The final negative subprocess must not determine the successful harness exit.
$global:LASTEXITCODE=0
exit 0
