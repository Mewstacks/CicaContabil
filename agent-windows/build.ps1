$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$artifacts = Join-Path $root 'artifacts'
$service = Join-Path $artifacts 'service'
$configurator = Join-Path $artifacts 'configurator'
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
dotnet publish (Join-Path $root 'src\Regaro.Agent.Service\Regaro.Agent.Service.csproj') -c Release -o $service
dotnet publish (Join-Path $root 'src\Regaro.Agent.Configurator\Regaro.Agent.Configurator.csproj') -c Release -o $configurator
dotnet build (Join-Path $root 'installer\Regaro.Agent.Installer.wixproj') -c Release `
  -p:ServiceDir=$service -p:ConfiguratorDir=$configurator
$msi = Get-ChildItem -LiteralPath (Join-Path $root 'installer\bin') -Filter '*.msi' -Recurse |
  Sort-Object LastWriteTimeUtc -Descending |
  Select-Object -First 1
if (-not $msi) { throw 'O MSI não foi gerado.' }
Copy-Item -LiteralPath $msi.FullName -Destination (Join-Path $artifacts 'RegaroAgent.msi') -Force
$finalMsi = Join-Path $artifacts 'RegaroAgent.msi'
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $finalMsi
$hash.Hash.ToLowerInvariant() + '  RegaroAgent.msi' |
  Set-Content -LiteralPath (Join-Path $artifacts 'RegaroAgent.msi.sha256') -Encoding ascii
dotnet list (Join-Path $root 'src\Regaro.Agent.Service\Regaro.Agent.Service.csproj') package `
  --include-transitive --format json |
  Set-Content -LiteralPath (Join-Path $artifacts 'dependency-inventory.json') -Encoding utf8
$hash | Select-Object Algorithm, Hash, Path | Format-List
