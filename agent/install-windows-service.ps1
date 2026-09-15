[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_. -]{1,128}$')]
    [string]$SystemDsn,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$HubUrl,
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Label,
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$CaFile,
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$CertificateFile,
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$PrivateKeyFile,
    [string]$PythonExecutable = 'python',
    [ValidateRange(10, 86400)]
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$principal = [Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute este instalador em PowerShell elevado.'
}

$enrollmentSecure = Read-Host -Prompt 'Código de enrollment (uso único)' -AsSecureString
$enrollmentBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($enrollmentSecure)
try {
    $enrollmentCode = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($enrollmentBstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($enrollmentBstr)
}
if ([string]::IsNullOrWhiteSpace($enrollmentCode)) { throw 'O código de enrollment é obrigatório.' }

$programData = Join-Path $env:ProgramData 'HubContador'
$configPath = Join-Path $programData 'agent-config.dpapi'
New-Item -ItemType Directory -Path $programData -Force | Out-Null

$fingerprintInput = "$env:COMPUTERNAME|$SystemDsn|$CertificateFile"
$fingerprintBytes = [Text.Encoding]::UTF8.GetBytes($fingerprintInput)
$fingerprint = ([Security.Cryptography.SHA256]::HashData($fingerprintBytes) | ForEach-Object { $_.ToString('x2') }) -join ''

$env:HUB_AGENT_ENROLLMENT_CODE = $enrollmentCode
try {
    $enrollmentJson = @"
import json
import os
from agent.sync_client import EdgeAgentConfig, enroll_agent

config = EdgeAgentConfig(
    hub_url=$(ConvertTo-Json $HubUrl -Compress),
    agent_id='',
    shared_secret='',
    client_ca_file=$(ConvertTo-Json ([IO.Path]::GetFullPath($CaFile)) -Compress),
    client_certificate_file=$(ConvertTo-Json ([IO.Path]::GetFullPath($CertificateFile)) -Compress),
    client_private_key_file=$(ConvertTo-Json ([IO.Path]::GetFullPath($PrivateKeyFile)) -Compress),
)
agent_id, shared_secret = enroll_agent(
    config,
    code=os.environ['HUB_AGENT_ENROLLMENT_CODE'],
    label=$(ConvertTo-Json $Label -Compress),
    fingerprint=$(ConvertTo-Json $fingerprint -Compress),
)
print(json.dumps({'agent_id': agent_id, 'shared_secret': shared_secret}))
"@ | & $PythonExecutable -
    if ($LASTEXITCODE -ne 0) { throw 'Ativação recusada pela CICA.' }
} finally {
    Remove-Item Env:HUB_AGENT_ENROLLMENT_CODE -ErrorAction SilentlyContinue
    Remove-Variable enrollmentCode -ErrorAction SilentlyContinue
}

$credentials = $enrollmentJson | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($credentials.agent_id) -or [string]::IsNullOrWhiteSpace($credentials.shared_secret)) {
    throw 'Resposta de enrollment inválida.'
}
$configuration = @{
    HUB_AGENT_DSN = $SystemDsn
    HUB_AGENT_HUB_URL = $HubUrl.TrimEnd('/')
    HUB_AGENT_ID = [string]$credentials.agent_id
    HUB_AGENT_SHARED_SECRET = [string]$credentials.shared_secret
    HUB_AGENT_CA_FILE = [IO.Path]::GetFullPath($CaFile)
    HUB_AGENT_CERTIFICATE_FILE = [IO.Path]::GetFullPath($CertificateFile)
    HUB_AGENT_PRIVATE_KEY_FILE = [IO.Path]::GetFullPath($PrivateKeyFile)
    HUB_AGENT_QUEUE_PATH = (Join-Path $programData 'agent-queue.bin')
    HUB_AGENT_INTERVAL_SECONDS = [string]$IntervalSeconds
}
$plain = [Text.Encoding]::UTF8.GetBytes(($configuration | ConvertTo-Json -Compress))
$protected = [Security.Cryptography.ProtectedData]::Protect(
    $plain, $null, [Security.Cryptography.DataProtectionScope]::LocalMachine
)
[IO.File]::WriteAllBytes($configPath, [Text.Encoding]::ASCII.GetBytes([Convert]::ToBase64String($protected)))

$protectedFiles = @($configPath, $CaFile, $CertificateFile, $PrivateKeyFile)
foreach ($path in $protectedFiles) {
    & icacls $path /inheritance:r /grant:r 'SYSTEM:(F)' 'BUILTIN\Administrators:(F)' 'NT AUTHORITY\LOCAL SERVICE:(R)' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível aplicar ACL no arquivo protegido: $path" }
}

& $PythonExecutable -m agent.windows_service --startup delayed install
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível registrar o serviço Windows.' }
& $PythonExecutable -m agent.windows_service start
if ($LASTEXITCODE -ne 0) { throw 'O serviço foi registrado, mas não iniciou. Consulte o Event Viewer.' }

Write-Information 'Agente CICA instalado. O segredo não foi exibido nem salvo em argumentos de processo.' -InformationAction Continue
