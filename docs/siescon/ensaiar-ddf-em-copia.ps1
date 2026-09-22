# Ensaio dos DDFs do Siescon numa COPIA. Nao escreve nada em S:\Dados.
#
# Existe porque criar o dicionario relacional (FILE.DDF/FIELD.DDF/INDEX.DDF) e o
# unico jeito de o Pervasive aceitar SELECT, e isso e escrita no share de
# producao do escritorio. Aqui a escrita acontece numa pasta local, sobre copias
# dos arquivos, e o que se prova e exatamente o mesmo: que o layout esta certo e
# que as consultas do contrato rodam e devolvem as colunas esperadas.
#
# O ensaio tem duas partes:
#
#   1. Conferencia estatica (automatica, nao precisa de banco nem de engine).
#      Compara o tamanho de registro declarado em layout-v0.sql com o real, lido
#      por `butil -stat`. Se a soma das colunas nao bater byte a byte com o
#      registro, o Pervasive desloca todos os offsets seguintes e o SELECT volta
#      com o conteudo trocado -- foi assim que uma empresa chamada JUSSARA
#      apareceu como SARA. Este e o erro mais provavel num layout derivado a mao,
#      e o mais barato de pegar antes de mexer em producao.
#
#   2. Ensaio no Pervasive (precisa de um banco nomeado apontando para a copia).
#      Roda o DDL e depois as consultas dos contratos, comparando as colunas
#      devolvidas com o manifest.json.
#
# O banco nomeado tem de ser criado a mao, no Pervasive Control Center
# (pcc.exe), apontando Data path e DDF path para a pasta da copia. Nao ha
# caminho de linha de comando nesta instalacao: dbmaint nao existe, e a
# automacao por DTO falha ao conectar (DtoSession.Connect devolve 7025) porque o
# motor e Workgroup e roda na sessao de outro usuario.
#
# Uso tipico, em duas passadas:
#
#   .\ensaiar-ddf-em-copia.ps1                          # copia + conferencia estatica
#   (criar o banco no pcc.exe apontando para a pasta que o script imprimir)
#   .\ensaiar-ddf-em-copia.ps1 -Banco SIESCONENSAIO     # DDL + consultas
#   .\ensaiar-ddf-em-copia.ps1 -Limpar                  # apaga a copia
#
# ATENCAO: a copia contem dados de clientes do escritorio. Ela fica em disco ate
# voce rodar com -Limpar. Nao deixe para depois.

param(
    # Pasta da empresa de onde sai SAEC_COL. A folha do Siescon mora em
    # S:\Dados\<NNNN>\, uma pasta por empresa, entao esta e a escolha de "de quem
    # e a folha" -- no uso real, a pasta do proprio escritorio.
    [string]$Empresa = '0577',

    [string]$Origem = 'S:\Dados',
    [string]$Destino = (Join-Path $env:TEMP 'siescon-ensaio'),

    # Nome do banco Pervasive ja criado apontando para $Destino. Sem ele, o
    # script para depois da conferencia estatica.
    [string]$Banco,

    # DSN ODBC para rodar as consultas. Por padrao usa o nome do banco.
    [string]$Dsn,

    [string]$Repositorio = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\..')),

    [switch]$Limpar
)

$ErrorActionPreference = 'Stop'

# O Pervasive aqui e de 32 bits, entao o Engine DSN que o Control Center cria fica
# no hive de 32 bits do ODBC. Um processo de 64 bits simplesmente nao o enxerga --
# a conexao falharia com "data source name not found", que nao ajuda ninguem a
# entender que o problema e arquitetura. Se a fase do banco foi pedida e estamos
# em 64 bits, o script se relanca no PowerShell de 32 bits.
if ($Banco -and [Environment]::Is64BitProcess) {
    $ps32 = Join-Path $env:windir 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path $ps32)) { throw "nao encontrei o PowerShell de 32 bits em $ps32" }
    Write-Host "  [INFO]  relancando em 32 bits para enxergar o DSN do Pervasive" -ForegroundColor Yellow
    $argumentos = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $MyInvocation.MyCommand.Path,
        '-Empresa', $Empresa, '-Origem', $Origem, '-Destino', $Destino,
        '-Banco', $Banco, '-Repositorio', $Repositorio
    )
    if ($Dsn) { $argumentos += @('-Dsn', $Dsn) }
    & $ps32 @argumentos
    exit $LASTEXITCODE
}

$bin = 'C:\Program Files (x86)\Pervasive Software\PSQL\bin'
$butil = Join-Path $bin 'butil.exe'
$pvddl = Join-Path $bin 'pvddl.exe'
$layout = Join-Path $Repositorio 'docs\siescon\layout-v0.sql'
$contratos = Join-Path $Repositorio 'contracts\datasets'

function Titulo($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($m) { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Ruim($m) { Write-Host "  [FALHA] $m" -ForegroundColor Red }
function Nota($m) { Write-Host "  [INFO]  $m" -ForegroundColor Yellow }

if ($Limpar) {
    Titulo 'limpando a copia'
    if (Test-Path $Destino) {
        Remove-Item $Destino -Recurse -Force
        Ok "removido $Destino"
    } else {
        Nota 'nada a remover'
    }
    exit 0
}

# ---------------------------------------------------------------- 1. copia --
Titulo 'copiando os arquivos'
foreach ($ferramenta in $butil, $pvddl) {
    if (-not (Test-Path $ferramenta)) { Ruim "nao encontrei $ferramenta"; exit 1 }
}
if (-not (Test-Path $layout)) { Ruim "nao encontrei $layout"; exit 1 }

New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$globais = 'GER_EMPRESA.DAT', 'ADM_USUARIO.DAT', 'SAEC_ENQ.DAT'
foreach ($arquivo in $globais) {
    $de = Join-Path $Origem $arquivo
    if (-not (Test-Path $de)) { Ruim "nao encontrei $de"; exit 1 }
    Copy-Item $de $Destino -Force
    Ok $arquivo
}
$folha = Join-Path (Join-Path $Origem $Empresa) 'SAEC_COL.DAT'
if (Test-Path $folha) {
    Copy-Item $folha $Destino -Force
    Ok "SAEC_COL.DAT (empresa $Empresa)"
} else {
    Nota "sem SAEC_COL.DAT na empresa $Empresa; a folha fica fora do ensaio"
}
Nota "copia em $Destino"

# ------------------------------------------------- 2. conferencia estatica --
Titulo 'conferencia estatica: layout declarado x registro real'

# Tamanho de cada tipo do DDL. Os CHAR(n) trazem o proprio n; os demais sao fixos.
$tamanhoFixo = @{ 'INTEGER' = 4; 'SMALLINT' = 2; 'DOUBLE' = 8 }
$ddl = Get-Content $layout -Raw
$declarado = @{}
foreach ($m in [regex]::Matches($ddl, '(?s)CREATE TABLE (\w+)[^(]*\((.*?)\);')) {
    $tabela = $m.Groups[1].Value
    $soma = 0
    foreach ($linha in ($m.Groups[2].Value -split "`n")) {
        $limpa = ($linha -split '--')[0].Trim()
        if (-not $limpa) { continue }
        $tipo = [regex]::Match($limpa, '\bCHAR\s*\((\d+)\)|\b(INTEGER|SMALLINT|DOUBLE)\b')
        if (-not $tipo.Success) { continue }
        if ($tipo.Groups[1].Success) { $soma += [int]$tipo.Groups[1].Value }
        else { $soma += $tamanhoFixo[$tipo.Groups[2].Value] }
    }
    $declarado[$tabela] = $soma
}

$divergencias = 0
foreach ($tabela in $declarado.Keys | Sort-Object) {
    $arquivo = Join-Path $Destino "$tabela.DAT"
    if (-not (Test-Path $arquivo)) { Nota "$tabela fora do ensaio"; continue }
    $saida = & $butil -stat $arquivo 2>&1
    $real = [regex]::Match(($saida -join ' '), 'Record Length\s*=\s*(\d+)')
    $linhas = [regex]::Match(($saida -join ' '), 'Total Number of Records\s*=\s*(\d+)')
    if (-not $real.Success) { Ruim "$tabela : nao consegui ler o tamanho do registro"; $divergencias++; continue }
    $r = [int]$real.Groups[1].Value
    $d = $declarado[$tabela]
    $n = if ($linhas.Success) { $linhas.Groups[1].Value } else { '?' }
    if ($r -eq $d) {
        Ok ("{0,-14} declarado {1,5} = real {1,5}   ({2} registros)" -f $tabela, $d, $n)
    } else {
        Ruim ("{0,-14} declarado {1,5} != real {2,5}   -- os offsets seguintes sairao deslocados" -f $tabela, $d, $r)
        $divergencias++
    }
    if ($n -eq '0') { Nota "$tabela esta VAZIA: a consulta vai rodar e devolver zero linhas" }
}

if ($divergencias -gt 0) {
    Ruim "$divergencias tabela(s) com layout divergente. Corrija layout-v0.sql antes de seguir."
    exit 1
}
Ok 'todas as tabelas conferem byte a byte'

# ------------------------------------------------------ 3. ensaio no banco --
if (-not $Banco) {
    Titulo 'proximo passo (manual)'
    Write-Host @"
  Crie um banco nomeado no Pervasive Control Center apontando para a copia:

    pcc.exe  ->  Databases  ->  New Database
      Database Name:  SIESCONENSAIO
      Location:       $Destino

      [ ] Bound                          <- DESMARCADO. Vincular grava a ligacao
                                            nos proprios arquivos de dados; em
                                            producao isso deixaria de ser "so
                                            cria o dicionario".
      [x] Create dictionary files        <- e o que cria os DDFs
      [ ] Relational integrity enforced  <- desmarcado: o layout nao tem chave
                                            estrangeira, e a RI trabalha junto
                                            com banco vinculado
      [ ] Long metadata (V2)
      [x] Create Engine DSN              <- o DSN que este script usa

  Depois rode de novo:

    .\ensaiar-ddf-em-copia.ps1 -Banco SIESCONENSAIO

  E, ao terminar, apague a copia:

    .\ensaiar-ddf-em-copia.ps1 -Limpar
"@ -ForegroundColor Gray
    exit 0
}

Titulo "criando os DDFs no banco $Banco"
& $pvddl $Banco $layout -stopOnFail
if ($LASTEXITCODE -ne 0) { Ruim "pvddl retornou $LASTEXITCODE"; exit 1 }
Ok 'DDFs criados'

Titulo 'rodando as consultas dos contratos'
if (-not $Dsn) { $Dsn = $Banco }
Add-Type -AssemblyName System.Data
$manifesto = Get-Content (Join-Path $contratos 'manifest.json') -Raw | ConvertFrom-Json
$doSiescon = $manifesto.datasets | Where-Object { $_.sourceSystem -eq 'siescon' }

$conn = New-Object System.Data.Odbc.OdbcConnection("DSN=$Dsn")
try { $conn.Open(); Ok "conectado em DSN=$Dsn" }
catch { Ruim "nao conectei: $($_.Exception.Message)"; exit 1 }

$falhas = 0
foreach ($dataset in $doSiescon) {
    $sql = Get-Content (Join-Path $contratos $dataset.sqlFile) -Raw
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = 60
    try {
        # SchemaOnly prepara a consulta e devolve as colunas sem ler uma linha:
        # prova que o SELECT compila contra os DDFs, sem trafegar dado.
        $r = $cmd.ExecuteReader([System.Data.CommandBehavior]::SchemaOnly)
        $colunas = @()
        for ($i = 0; $i -lt $r.FieldCount; $i++) { $colunas += $r.GetName($i) }
        $r.Close()

        # `contextColumns` sao preenchidas pelo backend, nao vem do SELECT.
        $contexto = @($dataset.contextColumns)
        $esperadas = @($dataset.columns | ForEach-Object { $_.name } |
            Where-Object { $contexto -notcontains $_ })
        $faltando = @($esperadas | Where-Object { $colunas -notcontains $_ })
        $sobrando = @($colunas | Where-Object { $esperadas -notcontains $_ })

        if ($faltando.Count -eq 0 -and $sobrando.Count -eq 0) {
            Ok ("{0,-10} {1}" -f $dataset.code, ($colunas -join ', '))
        } else {
            Ruim ("{0,-10} faltando: [{1}]  sobrando: [{2}]" -f $dataset.code,
                ($faltando -join ', '), ($sobrando -join ', '))
            $falhas++
        }
    } catch {
        Ruim ("{0,-10} {1}" -f $dataset.code, (($_.Exception.Message -split "`n")[0]))
        $falhas++
    }
}
$conn.Close()

Titulo 'resultado'
if ($falhas -gt 0) {
    Ruim "$falhas contrato(s) com problema. Nao aplique o DDL em S:\Dados ainda."
    exit 1
}
Ok 'todos os contratos do Siescon compilam e devolvem as colunas esperadas'
Nota 'agora sim da para aplicar o mesmo layout-v0.sql em S:\Dados, com janela e backup'
Nota "e nao esqueca: .\ensaiar-ddf-em-copia.ps1 -Limpar"
