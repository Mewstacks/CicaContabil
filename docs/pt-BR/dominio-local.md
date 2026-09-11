# Domínio local: Fedrizzi Contabilidade

Este fluxo cria o escritório local de teste **Fedrizzi Contabilidade** (`fedrizzi-contabilidade`) e espelha apenas cadastros ativos do Domínio. A conexão aceita exclusivamente o nome de um DSN de sistema Windows; senha, `UID`, host e SQL livre não entram no Hub nem no repositório.

O espelho mantém código Domínio, nome e CNPJ mascarado. A consulta direta é um `SELECT` fixo e limitado a 1.000 cadastros; ela não grava no Domínio e não desativa empresas ausentes, pois esta primeira consulta é propositalmente limitada. Neste banco ela usa o schema `bethadba` e a tabela `geempre`. O agente de borda para servidor conserva o limite de 500 por envio e também não desativa ausências.

## Executar neste computador

O DSN `contabil` já foi identificado como DSN de sistema SQL Anywhere. Confirme que ele usa a credencial Domínio somente leitura e execute no PowerShell, a partir da raiz do projeto:

```powershell
.\scripts\setup-local-dominio.ps1 -SystemDsn contabil
```

O script aplica as migrações locais, cria o escritório de forma idempotente e roda a consulta allowlisted de empresas. A saída mostra apenas contagens, nunca registros ou CNPJ bruto.

Para preparar o escritório sem consultar o Domínio:

```powershell
.\scripts\setup-local-dominio.ps1 -SkipSync
```

Para fazer o mesmo manualmente:

```powershell
.\.venv\Scripts\python.exe manage.py setup_fedrizzi_dominio --dsn contabil --sync
```

## Comunicados e outras fontes

Além dos cadastros, a rotina espelha os comunicados de atendimento da fonte identificada neste banco: `bethadba.GENOTIFICACOES_USUARIO_ATENDIMENTO`. A projeção fixa inclui somente identificador, código da empresa, assunto, tipo, situação e visualização. CPF, usuário, responsável, departamento e nome de empregado são excluídos da consulta; o assunto é cifrado no banco local.

Para outras fontes, faça primeiro apenas o inventário de metadados (não imprime nem persiste conteúdo sem `--apply`):

```powershell
.\.venv\Scripts\python.exe manage.py discover_dominio_schema --organization fedrizzi-contabilidade --dsn contabil --limit 50 --include-views
```

Depois de identificar uma nova fonte com o contador, a próxima implementação deve adicionar uma consulta fixa e limitada ao registro de consultas, com campos mínimos, classificação LGPD e teste. Isso mantém a integração estritamente somente leitura e impede SQL arbitrário.
