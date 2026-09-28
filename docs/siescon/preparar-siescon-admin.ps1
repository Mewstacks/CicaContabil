# Preparacao do acesso relacional ao Siescon. RODAR EM SHELL COMO ADMINISTRADOR.
#
# O que faz, nesta ordem:
#   1. Remove do compartilhamento de producao os DDFs que a investigacao criou.
#      Guarda dupla: so remove arquivo cujo nome esta na lista fixa de DDFs do
#      Pervasive E que foi criado hoje. Nenhum arquivo de dados do Siescon e
#      tocado - o Siescon acessa por Btrieve e nunca leu esses arquivos.
#   2. Remove os bancos de teste registrados no Pervasive (tst4, loc11..loc13,
#      siescon, siescon2). Isso mexe no DBNAMES.CFG, que e config compartilhada,
#      por isso exige elevacao.
#   3. Cria o banco 'siescon' limpo, com dicionario em disco local e dados
#      apontando para o share por caminho UNC (o motor nao resolve letra de
#      unidade mapeada, que so existe na sessao de quem mapeou).
#   4. Cria o DSN de Sistema de 32 bits que o conector vai usar.
#
# O driver ODBC do Pervasive instalado e de 32 bits, entao as partes de banco
# rodam num PowerShell de 32 bits chamado a partir daqui.

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Continue'

$share = '\\servidor\siescon\Dados'
$ddf = 'C:\ProgramData\ARD\siescon-ddf'
$ps32 = "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"

Write-Host "`n=== 1. limpando DDFs do compartilhamento de producao ===" -ForegroundColor Cyan
$nomesDdf = @('ATTRIB.DDF', 'FIELD.DDF', 'FILE.DDF', 'INDEX.DDF', 'OCCURS.DDF',
              'PROC.DDF', 'RELATE.DDF', 'TRIGGER.DDF', 'VARIANT.DDF', 'VIEW.DDF')
$hoje = (Get-Date).Date
foreach ($nome in $nomesDdf) {
    $f = Join-Path $share $nome
    if (-not (Test-Path $f)) { continue }
    $item = Get-Item $f -Force
    if ($item.CreationTime.Date -ne $hoje) {
        Write-Host "   PULADO  $nome (criado em $($item.CreationTime); nao foi este trabalho)"
        continue
    }
    try { Remove-Item $f -Force -ErrorAction Stop; Write-Host "   removido $nome" }
    catch { Write-Host "   FALHOU  $nome : $($_.Exception.Message)" -ForegroundColor Red }
}
$resto = @(Get-ChildItem $share -Filter '*.DDF' -Force -ErrorAction SilentlyContinue)
if ($resto.Count -eq 0) { Write-Host "   share limpo." -ForegroundColor Green }
else { Write-Host "   ainda ha DDF no share: $($resto.Name -join ', ')" -ForegroundColor Yellow }

Write-Host "`n=== 2 e 3. bancos Pervasive (via PowerShell 32 bits) ===" -ForegroundColor Cyan
$scriptBanco = @'
$ErrorActionPreference = 'Continue'
$share = '\\servidor\siescon\Dados'
$ddf = 'C:\ProgramData\ARD\siescon-ddf'
New-Item -ItemType Directory -Force -Path $ddf | Out-Null

$cn = New-Object System.Data.Odbc.OdbcConnection("DSN=demodata;")
$cn.Open()
function Roda($sql) {
    $c = $cn.CreateCommand(); $c.CommandText = $sql; $c.CommandTimeout = 120
    try { [void]$c.ExecuteNonQuery(); "   OK    $sql" }
    catch { "   falha $sql  ->  $(($_.Exception.Message -split '\]')[-1].Trim())" }
}
foreach ($db in 'tst4','loc11','loc12','loc13','siescon','siescon2') { Roda "DROP DATABASE $db" }
Roda "CREATE DATABASE siescon DICTIONARY_PATH '$ddf' DATA_PATH '$share'"
$cn.Close()
'@
$tmp = "$env:TEMP\ard-banco.ps1"
Set-Content -Path $tmp -Value $scriptBanco -Encoding ASCII
& $ps32 -NoProfile -ExecutionPolicy Bypass -File $tmp

Write-Host "`n=== 4. DSN de Sistema (32 bits) para o conector ===" -ForegroundColor Cyan
$chave = 'HKLM:\SOFTWARE\WOW6432Node\ODBC\ODBC.INI'
try {
    New-Item -Path "$chave\SiesconARD" -Force | Out-Null
    Set-ItemProperty "$chave\SiesconARD" -Name 'Driver' -Value 'C:\Program Files (x86)\Pervasive Software\PSQL\bin\w3odbcci.dll'
    Set-ItemProperty "$chave\SiesconARD" -Name 'Description' -Value 'Siescon (ARD)'
    Set-ItemProperty "$chave\SiesconARD" -Name 'ServerName' -Value 'localhost'
    Set-ItemProperty "$chave\SiesconARD" -Name 'DBQ' -Value 'siescon'
    Set-ItemProperty "$chave\ODBC Data Sources" -Name 'SiesconARD' -Value 'Pervasive ODBC Client Interface'
    Write-Host "   DSN 'SiesconARD' criado." -ForegroundColor Green
} catch { Write-Host "   falhou: $($_.Exception.Message)" -ForegroundColor Red }

Write-Host "`n=== FIM. Me avise que eu continuo daqui. ===" -ForegroundColor Cyan
