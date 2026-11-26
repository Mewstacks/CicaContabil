# Exportar o HubFedrizzi para o CICA (servidor da Fedrizzi)

O exportador só lê. Não altera banco, arquivo, configuração nem tarefa agendada do HubFedrizzi.

## O que precisa estar no servidor

Nada novo para exportar. Usa o Python e o `.env` que o HubFedrizzi já tem (Postgres, MongoDB, `pymongo`).
O agente Windows do CICA (serviço .NET, MSI) é instalado à parte, depois da importação.

## Passo a passo

1. Copie `export_hubfedrizzi.py` para uma pasta fora do HubFedrizzi (ex.: `C:\temp\cica`).
2. PowerShell **como a mesma conta que roda o HubFedrizzi**, na pasta do projeto:

```powershell
cd C:\actions-runner\_work\HubFedrizzi\HubFedrizzi
$env:DJANGO_ENV = "production"
.\.venv\Scripts\python.exe C:\temp\cica\export_hubfedrizzi.py --out C:\temp\fedrizzi-export
```

3. A saída mostra tabelas, linhas, Mongo, arquivos e o SHA-256 do pacote:
   `C:\temp\fedrizzi-export.zip`. Mande o zip por canal privado e passe o SHA-256 por outro canal.
4. Apague a pasta e o zip do servidor depois de conferido.

Opções: `--no-files` (sem copiar PDFs/XMLs do MEDIA_ROOT), `--no-mongo`.

## O que NÃO sai

Senha de usuário, `senha_cifrada` e qualquer campo com senha/token/chave/cifrado vira vazio;
o arquivo `.pfx` e a senha do certificado ficam no servidor.

## No CICA (quem importa)

```powershell
python manage.py import_legacy_bundle --org fedrizzi-contabilidade --bundle fedrizzi-export.zip --dry-run
python manage.py import_legacy_bundle --org fedrizzi-contabilidade --bundle fedrizzi-export.zip --with-users
```

O comando confere os checksums, é repetível (rodar duas vezes não duplica) e mostra a contagem
por tabela. Toda linha fica guardada como veio (`LegacyImportRecord`) e depois é convertida em
modelo nativo, só dentro do escritório alvo. O relatório termina com uma linha de paridade por
tabela (`origem=N nativo=M`, com o motivo de cada linha sem nativo), medida no banco.

| HubFedrizzi | CICA |
|---|---|
| `core_empresa` (+ dia de liberação de e-mail, responsável) | `hub.ClientCompany`, `CompanyAreaResponsible` |
| `core_obrigacao` + `core_regimeobrigacao` | `hub.ActivityTemplate` (esfera, categoria, periodicidade, destino, regimes) |
| `core_empresaobrigacao` | `hub.ActivityTemplateAssignment` |
| `workflow_envio` | `hub.ObligationDelivery` (só linhas com algo registrado) |
| `core_empresainscricaoestadual`, `triagem_socioempresa` | `ClientCompany.state_registration`, `hub.CompanyPartner` |
| `core_feriado` | `fiscal_calendar.NonBusinessDay` (rascunho global, inerte até aprovação) |
| `triagem_documenttype/senderrule/sendercompany/extractionrule/rulealias/checklist*` | `triage.*` |
| `nfse_sincronizacaonfse` | `hub.NfseSync` (NSU preservado, desligada) |
| `robo_nfse_notanfse`, `mongo_nfse` | `hub.NfseDocument`, estágio próprio abaixo |

Opções da conversão: `--no-convert` (só guarda cru), `--hold-generation` (vínculos entram
inativos, o motor não gera atividade), `--enable-nfse-sync` (liga a sincronização das empresas
ativas; só na virada, para não haver dois sistemas consultando o mesmo NSU).

### Notas fiscais (estágio separado, em lotes)

O XML não é guardado cru: a linha de `robo_nfse_notanfse` perde o campo `xml` e o Mongo não vira
`LegacyImportRecord`. As notas vão direto para `NfseDocument` (XML criptografado, uma vez), em
lotes de 200 com commit por lote; rodar de novo pula o que já entrou.

```powershell
python manage.py import_legacy_bundle --org fedrizzi-contabilidade --bundle fedrizzi-export.zip --docs-only --nfse-documents all --measure-only
python manage.py import_legacy_bundle --org fedrizzi-contabilidade --bundle fedrizzi-export.zip --docs-only --nfse-documents all
python manage.py backfill_nfse_sides --organization fedrizzi-contabilidade
```

`--measure-only` lê o pacote e imprime quantas notas são novas e quanto ocupam; só depois de ver
o tamanho no Neon rode sem ele. Precisa do pacote completo (com o Mongo). `--limit N` corta cada
fonte para um teste.
