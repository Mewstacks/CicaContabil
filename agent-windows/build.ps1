param(
  [ValidatePattern('^\d+\.\d+\.\d+(\.\d+)?$')]
  [string]$Version = '1.0.0'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$artifacts = Join-Path $root 'artifacts'
$service = Join-Path $artifacts 'service'
$configurator = Join-Path $artifacts 'configurator'
$diagnosticScript = Join-Path $root 'diagnosticar.ps1'
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
dotnet publish (Join-Path $root 'src\Cica.Agent.Service\Cica.Agent.Service.csproj') -c Release -o $service `
  -p:Version=$Version
dotnet publish (Join-Path $root 'src\Cica.Agent.Configurator\Cica.Agent.Configurator.csproj') -c Release -o $configurator `
  -p:Version=$Version
dotnet build (Join-Path $root 'installer\Cica.Agent.Installer.wixproj') -c Release `
  -p:ServiceDir=$service -p:ConfiguratorDir=$configurator -p:DiagnosticScript=$diagnosticScript `
  -p:InstallerVersion=$Version
$msi = Get-ChildItem -LiteralPath (Join-Path $root 'installer\bin') -Filter '*.msi' -Recurse |
  Sort-Object LastWriteTimeUtc -Descending |
  Select-Object -First 1
if (-not $msi) { throw 'O MSI não foi gerado.' }
Copy-Item -LiteralPath $msi.FullName -Destination (Join-Path $artifacts 'CicaAgent.msi') -Force
$finalMsi = Join-Path $artifacts 'CicaAgent.msi'
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $finalMsi
$hash.Hash.ToLowerInvariant() + '  CicaAgent.msi' |
  Set-Content -LiteralPath (Join-Path $artifacts 'CicaAgent.msi.sha256') -Encoding ascii
@{ version = $Version; sha256 = $hash.Hash.ToLowerInvariant(); filename = 'CicaAgent.msi' } |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifacts 'release.json') -Encoding utf8
dotnet list (Join-Path $root 'src\Cica.Agent.Service\Cica.Agent.Service.csproj') package `
  --include-transitive --format json |
  Set-Content -LiteralPath (Join-Path $artifacts 'dependency-inventory.json') -Encoding utf8
$hash | Select-Object Algorithm, Hash, Path | Format-List
