# Registra no dicionario do Siescon a tabela da folha DO ESCRITORIO.
#
# O que isso faz, e o que NAO faz:
#
#   FAZ    grava uma definicao de tabela nos DDFs em C:\ProgramData\ARD\siescon-ddf,
#          dizendo "a tabela SAEC_COL_ESCRITORIO le o arquivo 0042\SAEC_COL.DAT".
#   NAO    escreve coisa alguma em \\servidor\siescon\Dados. O .DAT e apenas lido.
#
# Por que e preciso: a tabela SAEC_COL_ARD que existe hoje aponta para
# SAEC_COL.DAT na RAIZ do share, que nao e a folha de nenhuma empresa -- por isso
# o contrato `salaries` do Siescon volta com zero linhas. No Siescon a folha mora
# em S:\Dados\<NNNN>\SAEC_COL.DAT, uma pasta por empresa, e a do escritorio
# (FEDRIZZI CONTABILIDADE, empresa 42) esta em 0042, com 49 colaboradores.
#
# Por que criar em vez de corrigir a existente: corrigir exigiria DROP TABLE, e no
# Pervasive o DROP pode remover o proprio .DAT. Sobre dado de cliente isso nao se
# faz. Criar ao lado e aditivo e reversivel.
#
# O driver ODBC do Pervasive e de 32 bits, entao o script se relanca sozinho no
# PowerShell de 32 bits -- um processo de 64 nem enxerga o DSN.

param(
    # Pasta da empresa cuja folha sera lida. 0042 = FEDRIZZI CONTABILIDADE.
    [string]$Pasta = '0042',
    [string]$Tabela = 'SAEC_COL_ESCRITORIO',
    [string]$Dsn = 'SiesconARD',
    [string]$Share = '\\servidor\siescon\Dados'
)

$ErrorActionPreference = 'Stop'

if ([Environment]::Is64BitProcess) {
    $ps32 = Join-Path $env:windir 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path $ps32)) { throw "nao encontrei o PowerShell de 32 bits em $ps32" }
    Write-Host "  [INFO]  relancando em 32 bits para enxergar o DSN do Pervasive" -ForegroundColor Yellow
    & $ps32 -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path `
        -Pasta $Pasta -Tabela $Tabela -Dsn $Dsn -Share $Share
    exit $LASTEXITCODE
}

function Ok($m) { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Ruim($m) { Write-Host "  [FALHA] $m" -ForegroundColor Red }
function Nota($m) { Write-Host "  [INFO]  $m" -ForegroundColor Yellow }

Write-Host "`n=== conferindo o arquivo de origem ===" -ForegroundColor Cyan
$arquivo = Join-Path (Join-Path $Share $Pasta) 'SAEC_COL.DAT'
if (-not (Test-Path $arquivo)) { Ruim "nao existe $arquivo"; exit 1 }
$butil = 'C:\Program Files (x86)\Pervasive Software\PSQL\bin\butil.exe'
$stat = & $butil -stat $arquivo 2>&1
$registros = [regex]::Match(($stat -join ' '), 'Total Number of Records\s*=\s*(\d+)')
$tamanho = [regex]::Match(($stat -join ' '), 'Record Length\s*=\s*(\d+)')
if (-not $tamanho.Success) { Ruim 'nao consegui ler o cabecalho do arquivo'; exit 1 }
if ([int]$tamanho.Groups[1].Value -ne 1176) {
    Ruim "registro de $($tamanho.Groups[1].Value) bytes; o layout da folha espera 1176"
    exit 1
}
Ok "$arquivo : $($registros.Groups[1].Value) registros, 1176 bytes por registro"

Add-Type -AssemblyName System.Data
$cn = New-Object System.Data.Odbc.OdbcConnection("DSN=$Dsn")
try { $cn.Open(); Ok "conectado em DSN=$Dsn" }
catch { Ruim "nao conectei: $(($_.Exception.Message -split '\]')[-1].Trim())"; exit 1 }

Write-Host "`n=== a tabela ja existe? ===" -ForegroundColor Cyan
$existe = $cn.CreateCommand()
$existe.CommandText = "SELECT COUNT(*) FROM X`$File WHERE Xf`$Name = '$Tabela'"
if ([int]$existe.ExecuteScalar() -gt 0) {
    Nota "$Tabela ja esta no dicionario; nada a fazer"
    Nota 'para repontar seria preciso DROP, que este script nao faz de proposito'
    $cn.Close()
    exit 0
}
Ok "$Tabela ainda nao existe"

Write-Host "`n=== criando a definicao ===" -ForegroundColor Cyan
# Mesmas colunas de layout-v0.sql. Todas NOT NULL: sem isso o Pervasive insere um
# byte indicador de nulo antes de cada coluna e desloca todos os offsets
# seguintes -- foi o que quebrou as tabelas sem sufixo do dicionario.
$ddl = @"
CREATE TABLE $Tabela USING '$Pasta\SAEC_COL.DAT' (
    codi_colaborador INTEGER NOT NULL,
    filler_5         CHAR(26) NOT NULL,
    nome             CHAR(50) NOT NULL,
    filler_81        CHAR(563) NOT NULL,
    salario          DOUBLE NOT NULL,
    salario_hora     DOUBLE NOT NULL,
    filler_660       CHAR(517) NOT NULL
)
"@
$cmd = $cn.CreateCommand(); $cmd.CommandText = $ddl; $cmd.CommandTimeout = 60
try { [void]$cmd.ExecuteNonQuery(); Ok "$Tabela criada apontando para $Pasta\SAEC_COL.DAT" }
catch { Ruim (($_.Exception.Message -split '\]')[-1].Trim()); $cn.Close(); exit 1 }

Write-Host "`n=== conferindo o que a tabela le ===" -ForegroundColor Cyan
# O teste e auto-validante: salario / salario_hora tem de dar perto de 220, que e
# a jornada mensal padrao. Dois campos numericos quaisquer nao caem nessa razao
# por acaso -- se der outra coisa, o offset esta errado.
$check = $cn.CreateCommand()
$check.CommandText = "SELECT codi_colaborador, salario, salario_hora FROM $Tabela WHERE salario_hora > 0"
$r = $check.ExecuteReader()
$n = 0; $dentro = 0
while ($r.Read()) {
    $n++
    $razao = [double]$r[1] / [double]$r[2]
    if ($razao -gt 200 -and $razao -lt 230) { $dentro++ }
}
$r.Close()
$cn.Close()

if ($n -eq 0) { Ruim 'nenhuma linha com salario-hora; confira a pasta informada'; exit 1 }
Ok "$n colaboradores lidos; $dentro com salario/salario_hora entre 200 e 230"
if ($dentro -lt [math]::Floor($n * 0.8)) {
    Ruim 'a razao nao bate com a jornada de 220h: o layout pode estar deslocado'
    exit 1
}
Ok 'layout confere'
Nota "agora avise para trocar o FROM do contrato salaries.siescon.v1.sql para $Tabela"
