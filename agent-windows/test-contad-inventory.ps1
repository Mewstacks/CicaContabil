#requires -Version 5.1
<# Disposable Windows CI only. Successful metadata is synthetic; missing DSN uses real ODBC. #>
[CmdletBinding()]
param([string]$Scenario = '')
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'inspect-contad-schema.ps1'
if ($Scenario) {
    Add-Type -AssemblyName System.Data
    Add-Type -ReferencedAssemblies System.Data,System.Xml -TypeDefinition @'
using System;
using System.Data;
public sealed class InventoryFixtureConnection : IDisposable {
    public static string Scenario;
    public int ConnectionTimeout { get; set; }
    public void Open() { if(ConnectionTimeout != 20) throw new Exception("Timeout not configured"); }
    public void Close() { }
    public void Dispose() { }
    public DataTable GetSchema(string kind, string[] restrictions) {
        var t = new DataTable();
        if(kind == "Tables") {
            foreach(var s in new[]{"TABLE_SCHEM","TABLE_NAME","TABLE_TYPE"}) t.Columns.Add(s,typeof(string));
            t.Rows.Add("bethadba","GEEMPRE","TABLE");
            t.Rows.Add("bethadba","CTCONTAS","TABLE");
            t.Rows.Add("bethadba","EFRECEBER","VIEW");
            t.Rows.Add("other","CTPRIVATE","TABLE");
            t.Rows.Add("bethadba","UNRELATED","TABLE");
            if(Scenario == "object_limit") for(int i=0;i<1500;i++) t.Rows.Add("bethadba","CT"+i,"TABLE");
        } else if(kind == "Columns") {
            foreach(var s in new[]{"TABLE_SCHEM","TABLE_NAME","COLUMN_NAME","TYPE_NAME","ORDINAL_POSITION","NULLABLE","COLUMN_SIZE","DECIMAL_DIGITS"}) t.Columns.Add(s,typeof(string));
            var names=restrictions[2] == "GEEMPRE" ? new[]{"CODI_EMP","NOME_EMP","CGCE_EMP","STAT_EMP"} : new[]{"CODI_EMP"};
            int i=0;
            foreach(var name in names) {
                if(Scenario == "missing_column" && name == "STAT_EMP") continue;
                t.Rows.Add("bethadba",restrictions[2],name,"varchar",++i,"1","180","0");
            }
        } else throw new Exception("Unexpected metadata collection");
        return t;
    }
    public InventoryFixtureCommand CreateCommand() { return new InventoryFixtureCommand(); }
}
public sealed class InventoryFixtureCommand : IDisposable {
    public string CommandText { get; set; }
    public int CommandTimeout { get; set; }
    public IDataReader ExecuteReader() {
        if(CommandText != "SELECT TOP 21 stat_emp, COUNT(*) FROM bethadba.geempre GROUP BY stat_emp ORDER BY stat_emp" || CommandTimeout != 60) throw new Exception("Unexpected query");
        var t=new DataTable(); t.Columns.Add("stat_emp",typeof(string)); t.Columns.Add("count",typeof(long));
        if(InventoryFixtureConnection.Scenario == "status_limit") { for(int i=0;i<21;i++) t.Rows.Add("S"+i,1L); }
        else { t.Rows.Add("A",501L); t.Rows.Add("I",2L); }
        return t.CreateDataReader();
    }
    public void Dispose() { }
}
'@
    [InventoryFixtureConnection]::Scenario=$Scenario
    function Get-Credential {
        param($UserName,$Message)
        return New-Object System.Management.Automation.PSCredential('EXTERNO', (ConvertTo-SecureString 'synthetic-only-no-real-password' -AsPlainText -Force))
    }
    function New-Object {
        [CmdletBinding()]
        param([Parameter(Position=0)][string]$TypeName,[Parameter(Position=1)][object[]]$ArgumentList)
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection' -and $Scenario -ne 'missing_dsn') {
            return [InventoryFixtureConnection]::new()
        }
        if ($TypeName -eq 'System.Data.Odbc.OdbcConnection' -and $Scenario -eq 'missing_dsn') {
            $ArgumentList=@('DSN=CicaMissingInventoryCi;UID=synthetic;PWD=synthetic-only-no-real-password')
            $PSBoundParameters['ArgumentList']=$ArgumentList
        }
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
    $global:LASTEXITCODE = 0
    & $source
    exit $LASTEXITCODE
}
$evidence=@()
$scriptPath=$MyInvocation.MyCommand.Path
foreach ($case in @('success','missing_column','object_limit','status_limit','missing_dsn')) {
    $savedPreference=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        $lines=@(& "$PSHOME\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $scriptPath -Scenario $case 2>&1)
        $exitCode=$LASTEXITCODE
    } finally { $ErrorActionPreference=$savedPreference }
    $output=$lines | Out-String
    if($output.Contains('synthetic-only-no-real-password')) { throw 'Credential leaked in diagnostic output.' }
    $match=[regex]::Match($output,'Arquivo local restrito: ([^\r\n]+)')
    if ($case -eq 'success') {
        if($exitCode -ne 0 -or -not $match.Success) { throw ('Success fixture failed: '+$output) }
        $path=$match.Groups[1].Value.Trim()
        try {
            $raw=[IO.File]::ReadAllText($path)
            $result=$raw | ConvertFrom-Json
            if($result.company_count -ne 503 -or $result.object_count -ne 3 -or $result.column_count -ne 6) { throw 'Unexpected metadata coverage.' }
            if($result.status_mapping_approved -or $result.keys_relations_and_financial_semantics_verified) { throw 'Synthetic fixture falsely approved semantics.' }
            if($raw.Contains('synthetic-only-no-real-password') -or $raw.Contains('CTPRIVATE') -or $raw.Contains('UNRELATED')) { throw 'Private/unselected content leaked.' }
            $acl=Get-Acl -LiteralPath $path
            $allowed=@('S-1-5-18','S-1-5-32-544',[Security.Principal.WindowsIdentity]::GetCurrent().User.Value)
            foreach($rule in $acl.Access) {
                $sid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
                if($sid -notin $allowed) { throw 'Unexpected reader of inventory file.' }
            }
            if(-not (Get-Acl -LiteralPath (Split-Path $path)).AreAccessRulesProtected) { throw 'Output directory inherits public ACLs.' }
        } finally { Remove-Item -LiteralPath (Split-Path $path) -Recurse -Force }
    } elseif($exitCode -eq 0 -or $match.Success) { throw ('Failure fixture accepted: '+$case) }
    $evidence+=@{ scenario=$case; passed=$true; exit_code=$exitCode; real_erp=$false }
}
$folder=Join-Path $PSScriptRoot 'artifacts\validation'
[void][IO.Directory]::CreateDirectory($folder)
@{ windows=$PSVersionTable.PSVersion.ToString(); process_x64=[Environment]::Is64BitProcess; source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant(); scenarios=$evidence; real_erp=$false } |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'contad-inventory.json') -Encoding UTF8
Write-Host 'Inventory: synthetic success/limits/schema, real missing DSN, redaction and private ACLs passed.'
