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
por tabela. Toda linha fica guardada como veio (`LegacyImportRecord`); empresas e usuários viram
registros nativos do CICA.
