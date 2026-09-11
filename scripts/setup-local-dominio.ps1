[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9 _.-]{1,128}$')]
    [string]$SystemDsn = 'contabil',
    [string]$PythonPath,
    [switch]$SkipSync
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $PythonPath) {
    $PythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
}
$python = (Resolve-Path $PythonPath).Path

if (-not (Get-Command Get-OdbcDsn -ErrorAction SilentlyContinue)) {
    throw 'Get-OdbcDsn não está disponível nesta instalação do Windows.'
}

$matchingDsn = Get-OdbcDsn | Where-Object { $_.Name -ceq $SystemDsn -and $_.DsnType -eq 'System' }
if (-not $matchingDsn) {
    throw "DSN de sistema '$SystemDsn' não encontrado. Crie-o com uma credencial Domínio somente leitura."
}

Push-Location $projectRoot
try {
    & $python manage.py migrate --noinput
    if ($SkipSync) {
        & $python manage.py setup_fedrizzi_dominio
    }
    else {
        & $python manage.py setup_fedrizzi_dominio --dsn $SystemDsn --sync
    }
}
finally {
    Pop-Location
}
