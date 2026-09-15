# MCP de IA para Domínio — execução testável

## Estado atual

O Hub expõe um MCP interno em `POST /api/v1/intelligence/mcp/`. Ele não é um endpoint para Claude Desktop, ChatGPT ou a internet. O usuário autenticado e o escritório ativo determinam o escopo; `organization_id`, papel, SQL, DSN e credenciais nunca são aceitos como argumento de ferramenta.

O protocolo é JSON-RPC 2.0, revisão MCP `2025-06-18`, com `initialize`, `tools/list` e `tools/call`. A resposta de ferramenta usa `structuredContent` e cartões compactos. A interface registra somente metadados de auditoria: ferramenta, chaves de resultado, finalidade e hashes. Ela não registra dados fiscais brutos, prompts ou credenciais.

Ferramentas da primeira versão:

| Ferramenta | Retorno permitido | Limites |
| --- | --- | --- |
| `search_data_catalog` | Fontes de negócio autorizadas | Consulta até 300 caracteres; no máximo 4 cartões |
| `retrieve_knowledge` | Mesmo catálogo, para RAG | Sem documentos brutos |
| `get_company_context` | Empresa, identificador e status de sync | Empresa do escritório ativo apenas |
| `get_risk_snapshot` | Contagem e cartões de revisão aberta | Empresa do escritório ativo apenas |
| `explain_classification` | Código sugerido + regra ou histórico | Nunca aplica no Domínio |
| `get_answer_evidence` | Evidências de uma resposta do escritório | Nunca lê outra organização |

`run_sql`, conexão ODBC, nomes de tabela, DDL, escrita no Domínio e egressão de segredo não existem no contrato.

Em instalação governada pelo CRMew, o grant de cada empresa também precisa declarar a capacidade: `read` para consulta e `draft` para criar rascunho; `*` é a única capacidade ampla. Grant sem capacidade não ganha permissão implícita. Sem vínculo CRMew, o piloto interno conserva o comportamento local até o enrollment.

## Modos Domínio

O contrato de dados é igual nos dois modos:

1. **Direto interno:** serviço privado do Hub usa DSN ODBC de sistema e usuário Domínio `Externo` somente leitura.
2. **Agente de borda:** serviço Windows junto ao Domínio abre apenas HTTPS autenticado de saída para o Hub. Ele usa a mesma lista de consultas permitidas e uma fila cifrada local.

`apps.intelligence.connectors.ReadOnlyDominoOdbc` é propositalmente mínimo: aceita apenas o nome de uma consulta registrada em código, com timeout e limite de linhas. A instalação do driver `pyodbc` e o DSN ocorrem somente na máquina autorizada; o Hub não armazena senha, PFX ou configuração ODBC.

O agente de borda já possui o protocolo de piloto: código de enrollment de uso único e expiração curta, segredo de dispositivo cifrado no Hub, HMAC de `timestamp.body`, janela anti-replay de cinco minutos, fila local AES-GCM e revogação. Os endpoints de agente aceitam apenas enrollment e snapshots de empresas com no máximo 500 linhas; a organização é derivada do dispositivo, nunca do payload. Consulte [agent/README.md](../agent/README.md) para a instalação assistida.

Para iniciar a descoberta do servidor `10.10.10.122`, usar uma janela controlada com usuário Externo, DSN 64-bit e acesso somente leitura. Validar catálogo e uma consulta de baixo risco primeiro. Não enviar a senha pelo chat ou commitá-la em `.env`.

Após configurar o DSN no próprio servidor Windows, o primeiro comando é um probe sem espelhamento:

```powershell
python manage.py probe_dominio_odbc --organization escritorio-piloto --dsn Dominio64
```

Somente depois de conferir a contagem, repetir com `--apply`; o comando não imprime linhas, CNPJ ou senha.

## Descoberta do schema Domínio

Antes de liberar um pacote semântico, o operador executa uma descoberta ODBC limitada. Ela usa os metadados do driver, não recebe SQL e não copia registros fiscais. O catálogo privado guarda somente esquema, nomes de colunas, tipos, classificação e hash de estrutura. Todo objeto começa bloqueado para pacote; uma alteração de estrutura remove a aprovação automaticamente.

```powershell
venv\Scripts\python.exe manage.py discover_dominio_schema --organization escritorio-piloto --dsn Dominio64 --limit 50
venv\Scripts\python.exe manage.py discover_dominio_schema --organization escritorio-piloto --dsn Dominio64 --limit 50 --apply
```

O primeiro comando somente informa quantidades. O segundo persiste o catálogo para revisão do desenvolvedor/contador, sem listar nomes ou valores no terminal. A descoberta utiliza a interface de metadados ODBC, compatível com o catálogo do SQL Anywhere; as visões `SYSTABCOL` documentam uma linha por coluna, mas não são expostas ao MCP nem aceitam texto SQL do usuário. [Referência SAP SQL Anywhere](https://help.sap.com/docs/SAP_SQL_Anywhere/61ecb3d4d8be4baaa07cc4db0ddb5d0a/3beaa3956c5f1014883cb0c3e3559cc9.html)

## Governança de pacote semântico

Um pacote só pode escrever no espelho ou aparecer no chat quando declara as tabelas/visões e colunas das quais depende. O Hub confere cada dependência contra o catálogo Domínio do mesmo escritório: objeto aprovado, colunas existentes, dados não excluídos, chave de empresa, chave primária, campos de evidência e limites de período/linhas/staleness. Alteração de schema remove a aprovação e bloqueia o pacote até nova revisão. Esse gate é revalidado no sync e na leitura do chat; criar um registro com `enabled=true` não o contorna.

Depois de revisar o catálogo e preencher o contrato do pacote, a ativação local auditada é:

```powershell
venv\Scripts\python.exe manage.py activate_semantic_package --organization escritorio-piloto --package UUID_DO_PACOTE
```

## Treinamento inicial e melhoria contínua

O treinamento é uma linha de produção, não conversa solta:

1. Curador ingere manual Domínio, procedimento, dicionário de dados ou caso histórico em `KnowledgeSource`.
2. Contador aprova a fonte e o desenvolvedor cria cenários atômicos em `TrainingExample` com ao menos uma referência de origem.
3. Fontes RAG exigem origem verificável, versão e conteúdo sanitizado já na gravação; CPF, CNPJ e e-mail são recusados tanto no corpus do escritório quanto no corpus global. Somente exemplos `validated` exportam para JSONL. Cada exportação é de um escritório; não há mistura de dados entre tenants.
4. O job isolado de GPU prepara e treina um adaptador QLoRA no modelo local. Ele recebe somente o JSONL validado, a especificação com hash e uma imagem de runtime aprovada; não recebe acesso ao banco Domínio, Hub, ODBC, API ou rede.
5. Um avaliador executa o conjunto congelado, casos ambíguos, regressão de segurança, isolamento, mascaramento e política de ferramentas.
6. `record_intelligence_evaluation` grava as métricas e bloqueia publicação se a qualidade não atingir o gate.
7. Owner/admin aprova uma versão; publicar é reversível para o adaptador anterior.

Comandos locais:

```powershell
venv\Scripts\python.exe manage.py migrate --settings=config.settings.local
venv\Scripts\python.exe manage.py export_training_manifest --organization acme --output .\artifacts\acme-train.jsonl
venv\Scripts\python.exe manage.py prepare_lora_job --organization acme --base-model qwen3-14b --template qwen3 --adapter acme-2026-09 --output .\artifacts\acme-qlora-job.json
venv\Scripts\python.exe manage.py record_intelligence_evaluation --organization acme --report .\artifacts\evaluation.json
```

O runner em `runtime/trainer` valida novamente o hash do corpus, rejeita CPF/CNPJ/e-mail, gera o dataset Alpaca e o YAML do LlamaFactory. Sem `--execute`, ele só prepara arquivos e é o modo obrigatório de teste local. Para a execução aprovada, montar corpus e modelos apenas para leitura, saída vazia para escrita e desabilitar a rede do contêiner:

```powershell
docker build --build-arg LLAMAFACTORY_IMAGE=imagem-aprovada@sha256:SEU_DIGEST --file runtime/trainer/Dockerfile --tag hubcontador-trainer:aprovado .
docker run --rm --network none --gpus all --read-only --tmpfs /tmp:rw,noexec,nosuid,size=2g -e HUB_TRAINING_EXECUTION_APPROVED=1 -v ${PWD}\artifacts:/input:ro -v D:\Modelos\qwen3-14b:/models/qwen3-14b:ro -v ${PWD}\artifacts\qlora-output:/work hubcontador-trainer:aprovado --job /input/acme-qlora-job.json --manifest /input/acme-train.jsonl --workspace /work --models-root /models --execute
```

O digest da imagem e o diretório local do modelo são uma aprovação operacional explícita; o Hub não baixa modelo, não inicia GPU nem executa este comando automaticamente. O formato Alpaca (`instruction`, `input`, `output`, `system`) e o registro em `dataset_info.json` seguem a [documentação de dados do LlamaFactory](https://llamafactory.readthedocs.io/en/latest/getting_started/data_preparation.html).

Formato mínimo do relatório, sem prompts nem saídas brutas:

```json
{
  "suite_name": "pilot-2026-09",
  "model_name": "modelo-local+adaptador",
  "corpus_version": "acme-2026-09-01",
  "total_cases": 100,
  "correct_cases": 96,
  "sourced_cases": 100,
  "safety_regressions": 0,
  "tenant_isolation_passed": true,
  "masking_passed": true,
  "tool_policy_passed": true
}
```

O gate exige: 100% de respostas com fonte, pelo menos 95% de acerto em risco/classificação e zero regressão de segurança, isolamento, mascaramento ou ferramentas. O comando retorna erro quando o gate falha; uma versão reprovada não pode ser publicada.

Feedback “Não resolveu” cria somente um `LearningCandidate` pendente. Não altera pesos, regra ou RAG automaticamente. A central técnica permite curadoria, teste, aprovação e rollback.

## Modelo local e Claude

Enquanto o PC local não estiver disponível, o chat pode usar Claude Sonnet pela chave central da Mewstack; quando o runtime local estiver configurado e saudável, ele tem precedência. Nenhuma chamada paga ocorre por padrão: Claude exige ativação global, política por escritório e limite positivo. Para habilitar a rota Claude, cada escritório precisa de:

- opt-in explícito do owner;
- perfis permitidos; neste produto, owner, admin, manager e operator;
- política de dado completo ou mascarado;
- modelo Claude permitido, teto por requisição e diário/mensal em centavos, aprovação de custo vigente e revogável;
- auditoria de usuário, papel, finalidade, horário, modelo e hash do pacote enviado.

Claude pode ser a rota temporária enquanto o runtime local ainda não estiver configurado ou o fallback técnico quando ele não devolver resposta utilizável. Ele nunca pode ser usado apenas por uma pergunta “difícil”. A chave é central da Mewstack, e cada escritório continua sujeito a consentimento, papel e cotas. Claude serve como professor/avaliador offline e não como fine-tuning: o adaptador é treinado no modelo local. O cliente envia apenas pergunta mascarada, resumo estruturado, turnos relevantes e cartões de evidência; nunca schema inteiro, histórico completo, anexo bruto ou dump de tabela. CPF/CNPJ e e-mail são mascarados antes do envio. O prefixo estável de política recebe cache efêmero de cinco minutos, sem colocar conteúdo do escritório no prefixo cacheado.

O código falha fechado se a aprovação não existir, estiver revogada/expirada, tiver teto diário/mensal zero, não tiver modelo permitido, teto por requisição ou chave central. Antes de uma chamada autorizada, registra somente usuário, perfil, modelo, estimativa e hash do payload. O custo reservado é conservador: o teto por requisição conta contra o limite aprovado antes da chamada.

### Política assinada pelo CRMew e chave local

O CRMew entrega no estado assinado de cada instalação somente a política abaixo. O Hub valida tipos, papéis, modelo e limites antes de gravar; política ausente, inválida ou `enabled: false` revoga o fallback. Isso vale no próximo sync e, de todo modo, o cache de autorização expira em quinze minutos.

```json
{
  "configuration": {
    "intelligence": {
      "claude": {
        "enabled": true,
        "allow_full_data": false,
        "allowed_roles": ["owner", "admin", "manager", "operator"],
        "model": "claude-sonnet-4-20250514",
        "max_request_cents": 35,
        "offline_curation_enabled": true,
        "curation_max_batch_requests": 100,
        "approval": {
          "status": "approved",
          "daily_limit_cents": 500,
          "monthly_limit_cents": 4000,
          "valid_until": "2026-10-01T00:00:00-03:00"
        }
      }
    }
  }
}
```

`claude_api_key` não pertence ao contrato e o CRMew nunca a recebe. O operador a provisiona apenas no terminal seguro da própria instalação, sem passá-la como argumento nem gravá-la no histórico do shell:

```powershell
venv\Scripts\python.exe manage.py configure_claude_local_key --organization escritorio-piloto
```

Esse comando apenas cifra a chave local; não habilita o fallback e não faz chamada à Anthropic. A liberação continua dependendo da próxima política assinada do CRMew e dos tetos definidos nela.

Para o uso de Claude como professor offline, o Hub apenas gera um JSONL local de exemplos já validados e anonimizados. Ele não submete lote, não lê anexos nem dados vivos do Domínio e interrompe a preparação ao detectar CPF, CNPJ ou e-mail. Cada retorno da Anthropic continua sendo candidato de curadoria — nunca altera RAG, regras ou pesos sem revisão humana.

```powershell
venv\Scripts\python.exe manage.py prepare_claude_curation_batch --organization escritorio-piloto --output .\artifacts\claude-curation.jsonl
```

Enviar esse arquivo à Batch API é uma ação externa paga e exige confirmação de custo específica antes de ser feita.

## Plano de teste por fase

### Fase 0 — descoberta local controlada

- [ ] DSN, driver SQL Anywhere e usuário Externo confirmados no servidor autorizado.
- [ ] Catálogo de módulos e matriz de sensibilidade aprovados.
- [ ] Consulta allowlisted executada com limite, timeout e sem dado fiscal em log.
- [ ] Snapshot/hash ou watermark comprovado em cópia autorizada.
- [ ] Benchmark local registra qualidade, latência, VRAM e modelo candidato.

### Fase 1 — piloto interno local

- [x] Migrações, endpoint MCP, isolamento de empresa/escritório e auditoria metadata-only.
- [x] Chat com evidência, feedback e rascunho que não escreve no Domínio.
- [ ] Sincronizador Domínio com dados de piloto e dados mascarados de teste.
- [ ] Suite de classificação/risco com mínimo de 100 casos validados.
- [ ] Testes de erro ODBC, timeout, dado desatualizado, página vazia e permissão.

### Fase 2 — aprendizagem e modelo local

- [x] Manifesto JSONL e gate de avaliação persistente.
- [x] Runner QLoRA isolado e reproduzível em modo seco: imagem-base por digest, checksum do corpus, validação de PII, modelo local montado e saída vazia.
- [ ] Execução homologada em GPU privada com imagem/digest e modelo aprovados pelo operador.
- [x] RAG diário versionado por fonte/hash; ingestão rejeita fonte sem origem, versão ou dado identificável indevido.
- [x] Avaliador bloqueia publicação com regressão contra a suíte congelada; contador ainda aprova a amostra em produção.
- [x] Fallback Claude opt-in, orçamento por solicitação/dia/mês e testes de bloqueio de egressão.

### Fase 3 — agente multi-escritório

- [x] Enrollment de dispositivo com código único, certificado e revogação.
- [x] mTLS, HMAC, fila local cifrada e retomada após queda.
- [x] Testes locais de replay antes de ODBC, DSN inseguro, documento de configuração inválido e agente revogado.
- [x] Instalador assistido para serviço Windows: DPAPI, ACL restrita e host nativo SCM.
- [ ] Assinar o pacote Windows com certificado de code-signing e homologar no piloto; o certificado não está neste repositório.

## Teste local obrigatório

```powershell
.venv\Scripts\python.exe manage.py check --settings=config.settings.test
.venv\Scripts\python.exe manage.py test tests.test_intelligence_mcp_django --settings=config.settings.test --verbosity 2
```

O segundo comando cria banco efêmero, executa migrações e verifica JSON-RPC, ferramentas sem SQL livre e bloqueio de evidência cross-tenant. Para a bateria completa, instalar todos os extras locais com `uv sync --all-extras --dev` e incluir:

```powershell
uv run pytest
uv run ruff check src tests
uv run mypy src
```

## Publicação controlada no Fly

1. Executar todos os testes locais e congelar a versão do corpus/modelo/adaptador.
2. Definir segredos exclusivamente com `fly secrets set`; nunca em `fly.toml`, log ou histórico de shell.
3. Criar staging separado, sem DSN de produção e sem fallback Claude.
4. Executar `fly deploy --strategy canary` somente após aprovar a mudança e o custo de qualquer recurso novo.
5. O `release_command` já executa `python manage.py migrate --noinput`; o health check é `/api/v1/health/ready/`.
6. Validar smoke tests autenticados, isolamento, CSP/CSRF, migração, health check, logs sem conteúdo sensível e rollback.
7. Só então promover produção. GPU/modelo local e Domínio nunca são expostos pelo Fly: o Hub fala com serviços privados/agent de saída autenticado.

O canário precisa falhar fechado: se o MCP, catálogo ou modelo local não estiver saudável, exibir incerteza e não tentar Claude sem o opt-in e teto aprovados.

## Retenção

O agendamento diário deve executar `python manage.py purge_intelligence_retention` primeiro em modo de simulação. A remoção exige `--apply` e respeita os dias definidos por escritório (90 por padrão). Conversas ligadas a rascunho ou candidato de aprendizado permanecem até a curadoria terminar, para não apagar evidência de uma decisão pendente.

## Fontes técnicas verificadas

- [Autorização MCP 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization): validação de audiência e proibição de token passthrough.
- [Ferramentas MCP](https://modelcontextprotocol.io/specification/2025-06-18/server/tools): ferramentas devem ser inspecionáveis e ter controle humano.
- [Prompt caching Claude](https://platform.claude.com/docs/en/build-with-claude/prompt-caching): prefixos estáveis, cache de 5 min/1 h e isolamento por workspace.
- [Deploy no Fly](https://fly.io/docs/launch/deploy/): canário e release command.
