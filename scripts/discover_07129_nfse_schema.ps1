param([string]$Dsn = 'CICA07129')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $root '.tmp\07129-extract\nfse-schema.json'
$credential = Get-Credential -UserName 'CICA_NFSE' -Message 'CICA: leitura de metadados NFS-e do Domínio. A senha não será salva.'
if ($null -eq $credential) { throw 'Credencial não informada.' }

$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($credential.Password)
$password = ''
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $connection = [Data.Odbc.OdbcConnection]::new(
        "DSN=$Dsn;UID=$($credential.UserName);PWD=$password;ASTART=NO;CON=Cica07129SchemaReadOnly"
    )
    $connection.Open()
    try {
        $tables = @(
            [pscustomobject]@{ TABLE_NAME = 'EFACUMULADOR' }
            [pscustomobject]@{ TABLE_NAME = 'FONOTA_FISCAL_SERVICOS_PRESTADOS' }
            [pscustomobject]@{ TABLE_NAME = 'FONOTA_FISCAL_SERVICOS_TOMADOS' }
        )
        $result = [Collections.Generic.List[object]]::new()
        foreach ($table in ($tables | Sort-Object TABLE_NAME -Unique)) {
            $restrictions = [string[]]@($null, 'bethadba', [string]$table.TABLE_NAME, $null)
            $columns = $connection.GetSchema('Columns', $restrictions) | Sort-Object ORDINAL_POSITION
            $result.Add([ordered]@{
                owner = 'bethadba'
                table = [string]$table.TABLE_NAME
                columns = @($columns | ForEach-Object {
                    [ordered]@{
                        name = [string]$_.COLUMN_NAME
                        type = [string]$_.TYPE_NAME
                        size = [int]$_.COLUMN_SIZE
                        nullable = [bool]$_.NULLABLE
                        ordinal = [int]$_.ORDINAL_POSITION
                    }
                })
            })
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $outputPath) -Force | Out-Null
        [IO.File]::WriteAllText(
            $outputPath,
            ($result | ConvertTo-Json -Depth 8),
            [Text.UTF8Encoding]::new($false)
        )
        Write-Host "Metadados lidos: $($result.Count) tabelas candidatas."
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
