param(
    [string]$Dsn = 'CICA07129',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
if (-not $OutputPath) {
    $root = Split-Path -Parent $PSScriptRoot
    $OutputPath = Join-Path $root '.tmp\07129-extract\normalized.json'
}

$credential = Get-Credential -UserName 'CICA_NFSE' -Message 'CICA: informe a senha do usuário Externo já cadastrado no Domínio. A senha não será salva.'
if ($null -eq $credential) { throw 'Credencial não informada.' }

$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($credential.Password)
$password = ''
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $connection = [Data.Odbc.OdbcConnection]::new(
        "DSN=$Dsn;UID=$($credential.UserName);PWD=$password;ASTART=NO;CON=Cica07129ReadOnly"
    )
    $connection.Open()
    try {
        $companies = [Collections.Generic.List[object]]::new()
        $command = $connection.CreateCommand()
        $command.CommandTimeout = 120
        $command.CommandText = @'
SELECT codi_emp, nome_emp, cgce_emp, stat_emp
FROM bethadba.geempre
ORDER BY codi_emp
'@
        $reader = $command.ExecuteReader()
        try {
            while ($reader.Read()) {
                $companies.Add([ordered]@{
                    external_key = [string]$reader.GetValue(0)
                    name = [string]$reader.GetValue(1)
                    cnpj = [string]$reader.GetValue(2)
                    active = ([string]$reader.GetValue(3)) -eq 'A'
                })
            }
        } finally { $reader.Dispose() }

        $accumulators = [Collections.Generic.List[object]]::new()
        $command.CommandText = @'
SELECT CODI_EMP, CODI_ACU, NOME_ACU,
       CASE WHEN DATA_INATIVACAO_ACU IS NULL THEN 1 ELSE 0 END
FROM bethadba.EFACUMULADOR
ORDER BY CODI_EMP, CODI_ACU
'@
        $reader = $command.ExecuteReader()
        try {
            while ($reader.Read()) {
                $companyKey = [string]$reader.GetValue(0)
                $code = [string]$reader.GetValue(1)
                $accumulators.Add([ordered]@{
                    company_key = $companyKey
                    accumulator_code = $code
                    name = [string]$reader.GetValue(2)
                    active = [int]$reader.GetValue(3) -eq 1
                    source_identifier = "$companyKey|$code"
                })
            }
        } finally { $reader.Dispose() }

        $payload = [ordered]@{
            schema_version = 1
            source = 'dominio-backup-07129'
            tenant = 'bianchi-rizzotto'
            captured_at_utc = [DateTime]::UtcNow.ToString('o')
            companies = $companies
            accumulator_catalog = $accumulators
        }
        $directory = Split-Path -Parent $OutputPath
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
        $json = $payload | ConvertTo-Json -Depth 6 -Compress
        [IO.File]::WriteAllText($OutputPath, $json, [Text.UTF8Encoding]::new($false))
        & icacls $directory /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F" | Out-Null
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $OutputPath).Hash.ToLowerInvariant()
        Write-Host "Leitura concluída: $($companies.Count) empresas e $($accumulators.Count) acumuladores."
        Write-Host "Arquivo normalizado protegido. SHA-256: $hash"
        Read-Host 'Pressione Enter para fechar'
    } finally {
        $connection.Dispose()
    }
} finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    $password = $null
    $credential = $null
}
