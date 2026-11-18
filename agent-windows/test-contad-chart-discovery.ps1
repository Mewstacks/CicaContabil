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
    $text=$text.Replace($expected,"`$expectedCompanyCodeSha256='794ea11f50892913aa01dd78f0835597272e0b1dcdb39169ca982253ec04e44b'")
    # Bounded negative fixtures exercise the exact production guards without
    # manufacturing million-row failures; the large success uses real limits.
    if ($Scenario -in @('catalogue_limit','template_limit','nature_limit')) {
        $text=$text.Replace('$rowLimit=1000000;', '$rowLimit=100;').Replace('$rowLimit=100000;', '$rowLimit=100;')
    }
    if ($Scenario -eq 'catalogue_bytes_limit') {$text=$text.Replace('$byteLimit=536870912','$byteLimit=128')}
    if ($Scenario -eq 'template_bytes_limit') {$text=$text.Replace('$path=Join-Path $Directory $names[$Kind]', '$path=Join-Path $Directory $names[$Kind]').Replace('return @{kind=$Kind;', "if (`$Kind -eq 'plan_template_accounts') {`$byteLimit=128}; return @{kind=`$Kind;")}
    if ($Scenario -eq 'nature_bytes_limit') {$text=$text.Replace('$byteLimit=33554432','$byteLimit=8')}
    if ($Scenario -eq 'manifest_limit') {$text=$text.Replace('8388608','1')}
    if ($Scenario -eq 'uncompressed_limit') {$text=$text.Replace('1073741824','1')}
    if ($Scenario -eq 'package_limit') {$text=$text.Replace('134217728','1')}
    if ($Scenario -eq 'stream_failure') {$text=$text.Replace('$Sink.stream.Write($line,0,$line.Length);', '$Sink.stream.Write($line,0,$line.Length); Reject-Details ''SYNTHETIC_IO_FAILURE'';')}
    if ($Scenario -eq 'chronology_reversed') {$text=$text.Replace('$secondReadStarted=[DateTime]::UtcNow','$secondReadStarted=$firstReadStarted.AddTicks(-1)')}
    if ($Scenario -eq 'observed_time_reversed') {$text=$text.Replace('$observed=[DateTime]::UtcNow','$observed=$secondReadCompleted.AddTicks(-1)')}
    if ($Scenario -eq 'descriptor_hash_changed') {$text=$text.Replace('$second=Read-Snapshot $secondDirectory', '$second=Read-Snapshot $secondDirectory; $second.chart_accounts.sha256=(''0''*64)')}
    return $text

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
  if(CommandTimeout!=120||(!companies&&!configured&&!cash&&!banks&&!integrations&&!equivalents&&!usage&&!ownerQuery&&!metadata))throw new Exception("Query scope");
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
   t=Table(typeof(long),typeof(long),typeof(long),typeof(long),typeof(long),s=="usage_bool"?typeof(object):typeof(long));if(s=="empty_details")return t.CreateDataReader();
   int count=s=="usage_limit"?10001:2;for(int i=0;i<count;i++)t.Rows.Add(s=="usage_outside"?999L:1L,901L,(long)i,2026L,s=="usage_outside_month"?12L:(long)9+i%2,s=="usage_total_limit"?5000001L:1L);
   if(s=="usage_duplicate")t.ImportRow(t.Rows[0]);
   if((s=="usage_changed"||s=="usage_and_catalogue_changed")&&CompanyReads>1)t.Rows[0][5]=2L;
   if(s=="usage_decreased")t.Rows[0][5]=CompanyReads>1?1L:3L;
   if(CompanyReads>1){
    if(s=="usage_reordered"){var row=t.Rows[0].ItemArray;t.Rows[0].ItemArray=t.Rows[1].ItemArray;t.Rows[1].ItemArray=row;}
    if(s=="usage_key_changed")t.Rows[0][2]=2L;
    if(s=="usage_key_removed")t.Rows.RemoveAt(0);
    if(s=="usage_zero")t.Rows[0][5]=0L;
    if(s=="usage_negative")t.Rows[0][5]=-1L;
    if(s=="usage_bool")t.Rows[0][5]=true;
   }
   return t.CreateDataReader();
  }
  if(ownerQuery){
   if(nature){
    t=Table(typeof(long),typeof(long),typeof(string),typeof(string),typeof(string));
    if(s=="empty_details"||s=="empty_nature")return t.CreateDataReader();
    if(HasOwner(1)){int count=s=="nature_limit"?101:1;for(int i=0;i<count;i++)t.Rows.Add(s=="nature_outside"?999L:1L,(long)i,"001 ","X","Z");
     if(s=="nature_duplicate")t.ImportRow(t.Rows[0]);if(s=="nature_changed"&&CompanyReads>1)t.Rows[0][3]="Y";}
    return t.CreateDataReader();
   }
   t=templates?Table(typeof(long),typeof(long),typeof(long),typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime)):Table(typeof(long),typeof(long),s=="text_type"?typeof(object):typeof(string),typeof(string),typeof(string),typeof(string),typeof(DateTime));
   if(s=="empty_details"||s=="empty_catalogues")return t.CreateDataReader();
   foreach(long owner in new long[]{1,100,900,901,902}){
    if(!HasOwner(owner)||s=="missing_chart"&&owner==100)continue;
    int count=owner==1&&(s=="catalogue_limit"&&!templates||s=="template_limit"&&templates)?101:1;
    for(int i=0;i<count;i++){
     long account=owner==900?9:owner==901?10:owner==902?11:8;
     long selectedOwner=s=="catalogue_outside"&&!templates||s=="template_outside"&&templates?999:owner;
     object name=s=="catalogue_null"&&!templates?(object)DBNull.Value:s=="template_name_limit"&&templates?new string('x',61):s=="catalogue_changed"&&!templates&&CompanyReads>1?"changed-private-name":SourceName(s,templates,owner);
     if(templates)t.Rows.Add(selectedOwner,1L,account+i,name,"001.0008 ","A","A",DBNull.Value);
     else t.Rows.Add(selectedOwner,account+i,name,s=="text_classification_limit"&&owner==1?new string('0',21):"001.0008 ",s=="text_flag_limit"&&owner==1?"AA":"A","A",s=="inactive_date"?(object)new DateTime(2026,10,1):DBNull.Value);
    }
   }
   if(t.Rows.Count>0){
    if(s=="catalogue_duplicate"&&!templates||s=="template_duplicate"&&templates)t.ImportRow(t.Rows[0]);
    if(templates&&s=="multiple_templates"&&HasOwner(1)){var row=t.NewRow();row.ItemArray=(object[])t.Rows[0].ItemArray.Clone();row[1]=2L;t.Rows.Add(row);}
   }
   if((s=="large_catalogue"||s=="large_source_changed")&&chart&&HasOwner(1))return new RepeatedChartReader(t.CreateDataReader(),100005,s=="large_source_changed"&&CompanyReads>1);
   if(s=="catalogue_out_of_order"&&chart&&t.Rows.Count>1){var first=t.Rows[0].ItemArray;t.Rows[0].ItemArray=t.Rows[1].ItemArray;t.Rows[1].ItemArray=first;}
   // The real database sorts owner/plan/account. Preserve that order in fixture.
   if(templates){var view=t.DefaultView;view.Sort="c0 ASC, c1 ASC, c2 ASC";return view.ToTable().CreateDataReader();}
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
 private object SourceName(string s,bool template,long owner){
  if(s=="invalid_text")return "synthetic-private-name\n";
  if(template||owner!=1)return "synthetic-private-name";
  switch(s){
   case "unicode_whitespace":return " \tsynthetic-private-name\r\n ";
   case "unicode_format":return "A\u200BB\u202EC";
   case "unicode_private":return "A\uE000B";
   case "unicode_unassigned":return "A\u0378B";
   case "unicode_supplementary":return "A"+Char.ConvertFromUtf32(0x1F600)+"B";
   case "unicode_combining":return "e\u0301";
   case "unicode_nul":return "A\0B";
   case "unicode_utf16_limit":return new string('x',148)+Char.ConvertFromUtf32(0x1F600);
   case "text_utf16_overflow":return new string('x',149)+Char.ConvertFromUtf32(0x1F600);
   case "text_length":return new string('x',151);
   case "text_diagnostic_limit":return new string('\n',600);
   case "text_type":return 123;
   case "text_high_surrogate":return "A\uD800B";
   case "text_low_surrogate":return "A\uDC00B";
   case "usage_and_catalogue_changed":return CompanyReads>1?"changed-private-name":"synthetic-private-name";
   case "unicode_changed":return CompanyReads>1?"AB":"A\u200BB";
   default:return "synthetic-private-name";
  }
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
public sealed class RepeatedChartReader:IDataReader {
 private readonly IDataReader inner;private readonly int total;private readonly bool changed;private int repeated;private bool repeat;
 public RepeatedChartReader(IDataReader source,int count,bool change){inner=source;total=count;changed=change;}
 public bool Read(){if(repeat&&repeated<total){repeated++;return true;}bool next=inner.Read();repeat=next&&Convert.ToInt64(inner.GetValue(0))==1;repeated=repeat?1:0;return next;}
 public object GetValue(int i){if(repeat&&i==1)return Convert.ToInt64(inner.GetValue(i))+repeated-1;if(repeat&&i==2&&changed&&repeated==total)return "changed-private-name";return inner.GetValue(i);}
 public bool IsDBNull(int i){return GetValue(i)==DBNull.Value;}
 public int FieldCount{get{return inner.FieldCount;}}public int Depth{get{return inner.Depth;}}public bool IsClosed{get{return inner.IsClosed;}}public int RecordsAffected{get{return inner.RecordsAffected;}}
 public object this[int i]{get{return GetValue(i);}}public object this[string n]{get{return GetValue(GetOrdinal(n));}}
 public void Close(){inner.Close();}public void Dispose(){inner.Dispose();}public DataTable GetSchemaTable(){return inner.GetSchemaTable();}public bool NextResult(){return inner.NextResult();}
 public string GetName(int i){return inner.GetName(i);}public string GetDataTypeName(int i){return inner.GetDataTypeName(i);}public Type GetFieldType(int i){return inner.GetFieldType(i);}public int GetOrdinal(string n){return inner.GetOrdinal(n);}
 public int GetValues(object[] values){for(int i=0;i<Math.Min(values.Length,FieldCount);i++)values[i]=GetValue(i);return Math.Min(values.Length,FieldCount);}
 public bool GetBoolean(int i){return Convert.ToBoolean(GetValue(i));}public byte GetByte(int i){return Convert.ToByte(GetValue(i));}public char GetChar(int i){return Convert.ToChar(GetValue(i));}public DateTime GetDateTime(int i){return Convert.ToDateTime(GetValue(i));}public decimal GetDecimal(int i){return Convert.ToDecimal(GetValue(i));}public double GetDouble(int i){return Convert.ToDouble(GetValue(i));}public float GetFloat(int i){return Convert.ToSingle(GetValue(i));}public Guid GetGuid(int i){return (Guid)GetValue(i);}public short GetInt16(int i){return Convert.ToInt16(GetValue(i));}public int GetInt32(int i){return Convert.ToInt32(GetValue(i));}public long GetInt64(int i){return Convert.ToInt64(GetValue(i));}public string GetString(int i){return Convert.ToString(GetValue(i));}
 public long GetBytes(int i,long a,byte[] b,int c,int d){throw new NotSupportedException();}public long GetChars(int i,long a,char[] b,int c,int d){throw new NotSupportedException();}public IDataReader GetData(int i){throw new NotSupportedException();}
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
$success=@('usage_changed','usage_decreased','usage_reordered','large_catalogue','invalid_text','unicode_whitespace','unicode_format','unicode_private','unicode_unassigned','unicode_supplementary','unicode_combining','unicode_nul','unicode_utf16_limit','missing_parameters','empty_catalogues','empty_nature','multiple_templates','success','company_order_reversed','empty_details','no_bank_references','missing_chart','missing_bank','null_bank_id','null_cash_codes','orphan_cash','inactive_date','integration_null_start','integration_zero_codes','no_integrations')
$cases=$success+@('usage_key_changed','usage_key_removed','usage_zero','usage_negative','usage_bool','usage_and_catalogue_changed','chronology_reversed','observed_time_reversed','descriptor_hash_changed','large_source_changed','catalogue_out_of_order','catalogue_bytes_limit','template_bytes_limit','nature_bytes_limit','manifest_limit','uncompressed_limit','package_limit','stream_failure','text_utf16_overflow','text_length','text_diagnostic_limit','text_type','text_high_surrogate','text_low_surrogate','text_classification_limit','text_flag_limit','unicode_changed','parameter_changed','missing_plan_id','equivalent_limit','equivalent_outside','equivalent_duplicate','equivalent_changed','usage_limit','usage_outside','usage_outside_month','usage_total_limit','usage_duplicate','catalogue_limit','catalogue_outside','catalogue_null','catalogue_changed','catalogue_duplicate','template_limit','template_outside','template_name_limit','template_duplicate','nature_limit','nature_outside','nature_duplicate','nature_changed','metadata_missing_target','metadata_limit','metadata_changed','missing_column','driver_failure','company_limit','company_count_changed','company_codes_changed','duplicate_company','number_type','account_limit','account_outside','account_fanout','source_changed','cash_limit','cash_outside','cash_duplicate','bank_limit','bank_outside','bank_fanout','integration_limit','integration_outside','integration_duplicate','integration_null_code','integration_invalid_date','integration_changed')
$unicodeNames=@{
    invalid_text="synthetic-private-name`n"
    unicode_whitespace=" `tsynthetic-private-name`r`n "
    unicode_format=('A'+[char]0x200B+'B'+[char]0x202E+'C')
    unicode_private=('A'+[char]0xE000+'B')
    unicode_unassigned=('A'+[char]0x0378+'B')
    unicode_supplementary=('A'+[char]::ConvertFromUtf32(0x1F600)+'B')
    unicode_combining=('e'+[char]0x0301)
    unicode_nul=('A'+[char]0+'B')
    unicode_utf16_limit=(('x'*148)+[char]::ConvertFromUtf32(0x1F600))
}
$textFailures=@{
    text_utf16_overflow=@{field='account_name_raw';kind='LENGTH';length=151;limit=150;type='System.String'}
    text_length=@{field='account_name_raw';kind='LENGTH';length=151;limit=150;type='System.String'}
    text_diagnostic_limit=@{field='account_name_raw';kind='LENGTH';length=600;limit=150;type='System.String'}
    text_type=@{field='account_name_raw';kind='TYPE';length=$null;limit=150;type='System.Int32'}
    text_high_surrogate=@{field='account_name_raw';kind='INVALID_SURROGATE';length=3;limit=150;type='System.String'}
    text_low_surrogate=@{field='account_name_raw';kind='INVALID_SURROGATE';length=3;limit=150;type='System.String'}
    text_classification_limit=@{field='classification_raw';kind='LENGTH';length=21;limit=20;type='System.String'}
    text_flag_limit=@{field='account_type_raw';kind='LENGTH';length=2;limit=1;type='System.String'}
    template_name_limit=@{field='account_name_raw';kind='LENGTH';length=61;limit=60;type='System.String'}
}
$integrationFailures=@{integration_limit='ROW_LIMIT';integration_outside='INTEGRATION_SCOPE';integration_duplicate='INTEGRATION_CARDINALITY';integration_null_code='NULL_FIELD';integration_invalid_date='DATE_CONTRACT';integration_changed='SOURCE_CHANGED'}
$evidence=@()
Add-Type -AssemblyName System.IO.Compression
foreach ($case in $cases) {
    $downloads=Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
    $foldersBefore=@(Get-ChildItem -LiteralPath $downloads -Directory -Filter 'CICA-CONTAD-Planos-Contas-*' -ErrorAction SilentlyContinue | ForEach-Object FullName)
    $saved=$ErrorActionPreference
    try {$ErrorActionPreference='Continue'; $lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path -Scenario $case 2>&1); $code=$LASTEXITCODE}
    finally {$ErrorActionPreference=$saved}
    $output=$lines | Out-String
    foreach ($secret in @('synthetic-private-password','synthetic-private-name','synthetic-private-bank','0000123-0')) {if ($output.Contains($secret)) {throw ('Private content leaked: '+$case)}}
    $json=@($output -split '\r?\n' | Where-Object {$_.StartsWith('{')})
    if ($json.Count -ne 1) {throw ('Missing safe receipt: '+$case)}
    $receipt=$json[0] | ConvertFrom-Json
    if ($case -in $success) {
        if ($code -ne 0 -or -not $receipt.completed -or $receipt.companies -ne 146) {
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
            if ([IO.Path]::GetExtension($report) -cne '.zip') {throw 'Expected ZIP report.'}
            if (@(Get-ChildItem -LiteralPath $folder -Force).Count -ne 1) {throw 'Raw snapshot or partial file remained.'}
            $zipStream=[IO.File]::OpenRead($report);$zip=[IO.Compression.ZipArchive]::new($zipStream,[IO.Compression.ZipArchiveMode]::Read)
            try {
                $expectedFiles=@('manifest.json','chart-accounts.jsonl','plan-template-accounts.jsonl','nature-rules.jsonl')
                if ($zip.Entries.Count -ne 4 -or @($zip.Entries | Where-Object {$_.FullName -cnotin $expectedFiles -or $_.Name -cne $_.FullName}).Count -or @($zip.Entries.FullName | Sort-Object -Unique).Count -ne 4) {throw 'Unsafe ZIP entry layout.'}
                $stream=$zip.GetEntry('manifest.json').Open();$reader=[IO.StreamReader]::new($stream,[Text.UTF8Encoding]::new($false,$true),$false)
                try {$data=$reader.ReadToEnd() | ConvertFrom-Json} finally {$reader.Dispose()}
                if ($data.version -cne 'contad-chart-discovery-v3') {throw 'Wrong discovery version.'}
                $uncompressed=[long]$zip.GetEntry('manifest.json').Length
                foreach ($kind in @('chart_accounts','plan_template_accounts','nature_rules')) {
                    $descriptor=$data.snapshot.$kind
                    if (@($descriptor.PSObject.Properties.Name | Sort-Object) -join ',' -cne 'bytes,file,rows,sha256') {throw 'Unexpected descriptor.'}
                    $entry=$zip.GetEntry($descriptor.file)
                    if ($null -eq $entry -or $entry.Length -ne $descriptor.bytes) {throw 'Stream byte count mismatch.'}
                    $stream=$entry.Open();$hasher=[Security.Cryptography.SHA256]::Create()
                    try {$digest=([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-','').ToLowerInvariant()} finally {$stream.Dispose();$hasher.Dispose()}
                    if ($digest -cne $descriptor.sha256) {throw 'Stream digest mismatch.'}
                    $stream=$entry.Open();$buffer=New-Object byte[] 65536;$seen=[long]0;$lf=[long]0;$last=-1
                    try {
                        while (($length=$stream.Read($buffer,0,$buffer.Length)) -gt 0) {
                            if ($seen -eq 0 -and $length -ge 3 -and $buffer[0] -eq 239 -and $buffer[1] -eq 187 -and $buffer[2] -eq 191) {throw 'UTF8 BOM emitted.'}
                            for ($i=0;$i -lt $length;$i++) {if ($buffer[$i] -eq 13 -or $buffer[$i] -eq 0) {throw 'Unescaped control in JSONL.'};if ($buffer[$i] -eq 10) {$lf++}}
                            $seen+=$length;$last=$buffer[$length-1]
                        }
                    } finally {$stream.Dispose()}
                    if ($seen -ne $descriptor.bytes -or $lf -ne $descriptor.rows -or ($seen -gt 0 -and $last -ne 10)) {throw 'JSONL framing mismatch.'}
                    $stream=$entry.Open();$reader=[IO.StreamReader]::new($stream,[Text.UTF8Encoding]::new($false,$true),$false)
                    $items=New-Object 'System.Collections.Generic.List[object]';$count=0
                    try {while ($null -ne ($line=$reader.ReadLine())) {$item=$line | ConvertFrom-Json;$count++;if ($case -ne 'large_catalogue' -or $count -le 5) {$items.Add($item)}}} finally {$reader.Dispose()}
                    if ($count -ne $descriptor.rows) {throw 'JSONL row count mismatch.'}
                    $uncompressed+=$descriptor.bytes
                    $data.snapshot.$kind=$items.ToArray()
                }
                if ($uncompressed -ne $receipt.uncompressed_bytes) {throw 'Package total mismatch.'}
            } finally {$zip.Dispose();$zipStream.Dispose()}
            foreach ($flag in @('nature_interpreted','chart_owner_mapping_inferred','cash_to_ledger_mapping_inferred','bank_association_approved','account_meanings_approved','human_reviewed','financial_collection_enabled','financial_values_selected','agent_configuration_read','erp_write_performed','uploaded')) {if ($data.$flag -ne $false) {throw ('Unsafe flag: '+$flag)}}
            $hasher=[Security.Cryptography.SHA256]::Create()
            try {$fixtureHash=([BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes((Get-FixtureSourceText))))).Replace('-','').ToLowerInvariant()}
            finally {$hasher.Dispose()}
            if ($data.script_sha256 -ne $fixtureHash -or $data.company_codes_sha256 -ne '794ea11f50892913aa01dd78f0835597272e0b1dcdb39169ca982253ec04e44b') {throw 'Script/scope provenance mismatch.'}
            $integrationProvenance=$data.provenance.integration_account_configurations
            if ($integrationProvenance.source -cne 'CTPARMTO_CONTAS_ICEBERG' -or $integrationProvenance.declared_foreign_keys_verified -ne $false -or $integrationProvenance.chart_owner_mapping_inferred -ne $false -or $integrationProvenance.bank_catalogue_link_inferred -ne $false) {throw 'Integration semantics inferred.'}
            if (@($data.snapshot.integration_account_configurations).Count -ne $receipt.integration_account_configurations) {throw 'Integration count mismatch.'}
            if ($data.period_start -cne '2026-09-01' -or $data.period_end_exclusive -cne '2026-12-01') {throw 'Usage period changed.'}
            $consistency=$data.read_consistency
            $expectedConsistencyKeys=@('cadastral_reads_identical','observed_usage_keys_identical','observed_usage_counts_identical','first_observed_chart_usage','first_read_started_at_utc','first_read_completed_at_utc','second_read_started_at_utc','second_read_completed_at_utc')
            if ((@($consistency.PSObject.Properties.Name | Sort-Object) -join ',') -cne (@($expectedConsistencyKeys | Sort-Object) -join ',')) {throw 'Consistency schema changed.'}
            if ($consistency.cadastral_reads_identical -ne $true -or $consistency.observed_usage_keys_identical -ne $true -or $receipt.cadastral_reads_identical -ne $true -or $receipt.observed_usage_keys_identical -ne $true) {throw 'Unsafe consistency flags.'}
            $firstUsage=@{};$secondUsage=@{}
            foreach ($pair in @(@{rows=$consistency.first_observed_chart_usage;map=$firstUsage},@{rows=$data.snapshot.observed_chart_usage;map=$secondUsage})) {
                foreach ($row in $pair.rows) {
                    $key='{0}:{1}:{2}:{3}:{4}' -f $row.company_code,$row.chart_company_code,$row.branch_code,$row.year,$row.month
                    if ($pair.map.ContainsKey($key) -or $row.entry_count -lt 1) {throw 'Invalid observed usage.'}
                    $pair.map[$key]=$row.entry_count
                }
            }
            if ((@($firstUsage.Keys | Sort-Object) -join ',') -cne (@($secondUsage.Keys | Sort-Object) -join ',')) {throw 'Changed usage keys accepted.'}
            $sameCounts=$true
            foreach ($key in $firstUsage.Keys) {if ($firstUsage[$key] -ne $secondUsage[$key]) {$sameCounts=$false}}
            if ($consistency.observed_usage_counts_identical -ne $sameCounts -or $data.two_reads_identical -ne $sameCounts -or $receipt.two_reads_identical -ne $sameCounts -or $receipt.observed_usage_counts_identical -ne $sameCounts) {throw 'Count variation misrepresented.'}
            $times=@($consistency.first_read_started_at_utc,$consistency.first_read_completed_at_utc,$consistency.second_read_started_at_utc,$consistency.second_read_completed_at_utc,$data.observed_at_utc)
            for ($i=0;$i -lt $times.Count;$i++) {
                if ($times[$i] -is [DateTime]) {if ($times[$i].Kind -ne [DateTimeKind]::Utc) {throw 'UTC interval lost.'}} elseif ($times[$i] -notmatch 'Z$') {throw 'UTC interval lost.'}
                if ($i -gt 0 -and ([DateTime]$times[$i-1]).Ticks -gt ([DateTime]$times[$i]).Ticks) {throw 'Invalid read chronology.'}
            }
            if ($case -in @('usage_changed','usage_decreased')) {
                if ($sameCounts -or $firstUsage['1:901:0:2026:9'] -ne $(if ($case -eq 'usage_changed') {1} else {3}) -or $secondUsage['1:901:0:2026:9'] -ne $(if ($case -eq 'usage_changed') {2} else {1})) {throw 'Both observed counts not retained exactly.'}
            }

            if ($unicodeNames.ContainsKey($case)) {
                $literal=@($data.snapshot.chart_accounts | Where-Object {$_.chart_company_code -eq 1})[0].account_name_raw
                if (-not [string]::Equals($literal,$unicodeNames[$case],[StringComparison]::Ordinal)) {throw ('Literal Unicode changed: '+$case)}
                if ($case -eq 'invalid_text' -and (-not [string]::Equals($data.snapshot.configured_accounts[0].account_name_raw,$unicodeNames[$case],[StringComparison]::Ordinal))) {throw 'Configured whitespace changed.'}
                # Framing scan rejects literal NUL; parsed value proves the escaped NUL round trip.
            }
            if ($case -eq 'large_catalogue' -and $receipt.chart_accounts -ne 100009) {throw 'Large catalogue truncated.'}
            if ($case -eq 'usage_changed') {
                $artifactFolder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($artifactFolder)
                Copy-Item -LiteralPath $report -Destination (Join-Path $artifactFolder 'contad-chart-discovery-counts-changed-synthetic.zip') -Force
            }
            if ($case -eq 'success') {
                if ($data.snapshot.chart_owners.Count -ne 149 -or $data.snapshot.chart_accounts.Count -ne 5 -or $data.snapshot.plan_template_accounts.Count -ne 5) {throw 'Full shared-owner catalogue incomplete or multiplied.'}
                if ($data.snapshot.observed_chart_usage.Count -ne 2 -or $data.snapshot.observed_chart_usage[1].month -ne 10 -or $data.snapshot.observed_chart_usage[1].branch_code -ne 1) {throw 'Observed month/branch multiplicity lost.'}
                if ($data.snapshot.companies[0].codi_pad_raw -ne 900 -or $data.snapshot.companies[0].comp_pad_raw -cne 'N' -or $data.snapshot.companies[1].cash_account_parameter_raw -ne 0 -or $data.snapshot.companies[145].configuration_rows -ne 0) {throw 'Parameter raw codes/missing state lost.'}
                if ($data.snapshot.nature_rules[0].nature_raw -cne 'X' -or $data.snapshot.nature_rules[0].group_raw -cne 'Z' -or $data.snapshot.equivalent_accounts[0].chart_company_code -ne 902) {throw 'Literal nature/equivalent reference lost.'}
                if ($data.snapshot.metadata.targets.Count -ne 7 -or $data.snapshot.metadata.relation_columns.Count -ne 2) {throw 'Metadata absent.'}
                if ($data.snapshot.bank_references.Count -ne 2 -or $data.snapshot.cash_accounts[0].bank_reference_count -ne 2 -or $data.snapshot.bank_references[0].agency_raw -cne '0001' -or $data.snapshot.bank_references[0].account_identifier_raw -cne '0000123-0' -or $data.snapshot.bank_references[0].bank_code_raw -ne 0 -or $data.snapshot.configured_accounts[0].classification_raw -cne '001.0008 ') {throw 'Multiplicity, raw strings or numeric zero lost.'}
                $artifactFolder=Join-Path $PSScriptRoot 'artifacts\validation';[void][IO.Directory]::CreateDirectory($artifactFolder)
                Copy-Item -LiteralPath $report -Destination (Join-Path $artifactFolder 'contad-chart-discovery-synthetic.zip') -Force
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
    if ($textFailures.ContainsKey($case)) {
        $expected=$textFailures[$case]; $diagnostic=$receipt.text_contract_failure
        if ($receipt.reason_code -cne 'TEXT_CONTRACT' -or $diagnostic.field -cne $expected.field -or $diagnostic.violation -cne $expected.kind -or $diagnostic.dotnet_type -cne $expected.type -or $diagnostic.utf16_length -ne $expected.length -or $diagnostic.utf16_limit -ne $expected.limit) {throw ('Text diagnostic mismatch: '+$case)}
        $allowedDiagnostic=@('field','dotnet_type','utf16_length','utf16_limit','violation','scalar_length','inspected_utf16_units','nonprinting_in_scanned','nonprinting_positions','diagnostic_truncated')
        if (@($diagnostic.PSObject.Properties.Name | Where-Object {$_ -notin $allowedDiagnostic}).Count -or @($diagnostic.nonprinting_positions).Count -gt 32) {throw 'Diagnostic exposed extra content.'}
        foreach ($position in $diagnostic.nonprinting_positions) {
            if ($position.category -notin @('Control','Format','Surrogate') -or $position.codepoint -notmatch '^U\+[0-9A-F]{4}$' -or @($position.PSObject.Properties.Name | Where-Object {$_ -notin @('utf16_index','category','codepoint')}).Count) {throw 'Printable text exposed in diagnostic.'}
        }
        if ($case -eq 'text_diagnostic_limit' -and (-not $diagnostic.diagnostic_truncated -or @($diagnostic.nonprinting_positions).Count -ne 32 -or $diagnostic.inspected_utf16_units -ne 512 -or $diagnostic.nonprinting_in_scanned -ne 512)) {throw 'Text diagnostic is not bounded.'}
        if ($case -in @('text_high_surrogate','text_low_surrogate') -and (@($diagnostic.nonprinting_positions).Count -ne 1 -or $diagnostic.nonprinting_positions[0].category -cne 'Surrogate' -or $diagnostic.nonprinting_positions[0].utf16_index -ne 1)) {throw 'Isolated surrogate diagnostic lost.'}
    }
    if ($case -in @('unicode_changed','large_source_changed') -and $receipt.reason_code -cne 'SOURCE_CHANGED') {throw 'Invisible source change accepted.'}
    if ($receipt.reason_code -eq 'SOURCE_CHANGED') {
        $diagnostic=$receipt.source_change
        if ($receipt.stage -cne 'comparing_read_consistency' -or $null -eq $diagnostic -or @($diagnostic.sections).Count -lt 1) {throw ('Missing fine source diagnostic: '+$case)}
        $allowedSections=@('companies','observed_chart_usage.keys','observed_chart_usage.entry_count','chart_owners','chart_accounts','plan_template_accounts','nature_rules','configured_accounts','equivalent_accounts','cash_accounts','bank_references','integration_account_configurations','metadata.targets','metadata.tables','metadata.key_columns','metadata.relation_columns')
        foreach ($section in $diagnostic.sections) {
            if ($section.section -notin $allowedSections -or (@($section.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'first,second,section') {throw 'Unsafe source diagnostic.'}
            foreach ($side in @($section.first,$section.second)) {
                if ((@($side.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bytes,rows,sha256' -or $side.sha256 -notmatch '^[0-9a-f]{64}$' -or $side.rows -lt 0 -or $side.bytes -lt 0) {throw 'Source diagnostic exposed data.'}
            }
        }
        if ($case -eq 'metadata_changed' -and @($diagnostic.sections | Where-Object {$_.section -eq 'metadata.relation_columns'}).Count -ne 1) {throw 'Exact metadata section missing.'}
        if ($case -in @('usage_key_changed','usage_key_removed') -and $diagnostic.observed_usage_keys_identical -ne $false) {throw 'Changed keys hidden.'}
        if ($case -eq 'usage_and_catalogue_changed' -and (@($diagnostic.sections).Count -ne 2 -or $diagnostic.cadastral_reads_identical -ne $false -or $diagnostic.observed_usage_keys_identical -ne $true -or $diagnostic.observed_usage_counts_identical -ne $false)) {throw 'Mixed changes hidden.'}
    }
    if ($case -in @('chronology_reversed','observed_time_reversed') -and $receipt.reason_code -cne 'READ_TIME_CONTRACT') {throw 'Clock regression accepted.'}
    $foldersAfter=@(Get-ChildItem -LiteralPath $downloads -Directory -Filter 'CICA-CONTAD-Planos-Contas-*' -ErrorAction SilentlyContinue | ForEach-Object FullName)
    if (@($foldersAfter | Where-Object {$_ -notin $foldersBefore}).Count) {throw ('Private temporary data remained: '+$case)}
    $evidence+=@{scenario=$case;passed=$true;exit_code=$code;real_erp=$false}
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation'; [void][IO.Directory]::CreateDirectory($folder)
@{passed=$true;windows=$PSVersionTable.PSVersion.ToString();source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();scenarios=$evidence;real_erp=$false;private_fixtures_removed=$true;fixture_company_scope_hash_replaced=$true;production_source_unchanged=$true;synthetic_package='contad-chart-discovery-synthetic.zip';synthetic_count_change_package='contad-chart-discovery-counts-changed-synthetic.zip';large_catalogue_rows=100009;format='contad-chart-discovery-v3'} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-chart-discovery.json') -Encoding UTF8
Write-Host 'Chart discovery: fixed SELECTs, scope, cardinality, two reads, private ACL, zero preservation, literal Unicode, bounded streaming ZIP, exact cadastral identity, both positive usage counts and safe section diagnostics passed.'
# The final negative subprocess must not determine the successful harness exit.
$global:LASTEXITCODE=0
exit 0
