# Etapa 15 — Incorporar Contraprova (sucessor do Tax Envel)

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento desde 21/10/2026 na branch dedicada `codex/contraprova` (D-300). A origem é o projeto `Site_Integracao\Django\apps\Tax_Envel`, lido em modo somente leitura no commit `ea066e8`; nada é copiado dele. Implementado e validado localmente em 22/10/2026: motor, módulo Django, telas, retenção e o lado servidor e o agente Windows da consulta de UF ao Domínio. Nada foi publicado nem homologado; o aceite fiscal (Q-46) e o ensaio na base real (Q-47) seguem abertos.

**Dependências:** 01–03. O caminho por arquivo não depende de nada além da base; a consulta de UF ao Domínio pelo agente depende do agente da etapa 03 e do ensaio real da etapa 12.

**Decisões relacionadas:** D-18, D-54, D-80, D-86, D-165, D-276, D-284, D-288, D-291, D-300, D-301, D-302.

## O que é o módulo

O Contraprova confere arquivos fiscais entre si e lista só o que diverge, por empresa e competência da carteira. Quatro ferramentas, que mantêm as funções do Tax Envel:

| Ferramenta | Confere | Entradas | Resultado |
|---|---|---|---|
| SPED x XML | C100/D100 da EFD ICMS/IPI contra NF-e/CT-e: valor do documento, ICMS e IPI (CT-e: prestação e ICMS) | EFD `.txt` e XML (ZIP ou soltos) | divergências, só no SPED, só no XML, ignoradas por regra |
| SPED x SPED | duas EFD entre si: documentos, totais e analítico (C190/D190) | SPED 1 e SPED 2 | só no 1, só no 2, divergência de documento e de analítico |
| ICMS 51 | compras de ativo e consumo (CFOP 1551/1556) cujo XML traz ICMS 51 (diferimento) | EFD e XML | chaves com os valores do grupo e a aritmética conferida |
| UF x Domínio | UF da contraparte no XML contra a UF cadastrada no Domínio | XML e UF do Domínio (agente ou CSV/XLSX) | UF divergente, ausente no Domínio, sem UF |

Mapa do legado: "Compara Sped x XML ICMS/IPI" e "ICMS" são a mesma ferramenta (SPED x XML) com seleção de campos; "Cruzamento Speds" é SPED x SPED; "Relação Chaves ICMS51" é ICMS 51; "Compara UFs" é UF x Domínio. As variantes "banco" (MongoDB `fiscaldrive`) e as cópias `*_v2` e `apps/tax` não foram portadas.

## Defeitos do legado e tratamento

Auditoria de leitura do código (nenhuma execução). Cada linha vira teste de regressão.

| Achado | Tratamento |
|---|---|
| Quebra sem bloco D, sem C190 ou sem C100; formulário inválido devolve 500 | leitor tolerante a bloco ausente; toda entrada inválida volta com motivo por arquivo |
| Rótulos de coluna trocados (C100 campo 10 é DT_DOC; C190 campos 3/6/7/11 são CFOP/BC/ICMS/IPI; D100 campos 19/20/12 são BC/ICMS/DT_A_P; ICMS 51 lia VL_IPI como COD_OBS) | leiaute conferido no Guia Prático e fixado por registro, com teste campo a campo |
| `CFOP_IGNORAR` copiado em cinco lugares e suprimindo tudo, até o valor do documento | regra única e visível (D-301): só ICMS/IPI, o achado fica em "Ignoradas" |
| Dinheiro em `float` com tolerância 0,01 (100,03 x 100,02 acusa, 10,02 x 10,01 passa) | `Decimal` e centavos inteiros, tolerância inclusiva |
| SPED lido como UTF-8 com `errors='replace'` | decodificação estrita (UTF-8 e, se falhar, Latin-1), codificação registrada |
| Sem cabeçalho 0000, versão, CNPJ, período, situação, totais 9900/9999 | validação do cabeçalho e da integridade; arquivo truncado é recusado; CNPJ e competência conferidos contra a empresa |
| Saídas (`\|C100\|1\|`) descartadas por engano | seleção explícita de operação |
| Crédito do Simples Nacional só em ICMSSN101 (quatro cópias) | ICMSSN101/201/900 em um ponto |
| Compara UF: SQL por interpolação, UF do destinatário contra a do fornecedor na entrada, empresa fixa 3359, chave ausente tratada como UF diferente | parâmetros, contraparte correta, empresa da conferência, categoria própria |
| XSS por `innerHTML`, sem autenticação, `DEBUG=True`, upload de 500 MB em memória, N+1 no MongoDB | escape no servidor, acesso do CICA, teto de arquivo e processamento em streaming |

## Escopo e checklist

- [x] Auditar o Tax Envel (nove sub-apps, seis rotas vivas, defeitos catalogados) e fixar o que vira teste.
- [x] Registrar D-300 a D-302 e abrir Q-46 e Q-47.
- [ ] Motor de conferência em `src/apps/crosscheck/engine`: chave, dinheiro, leitor EFD, XML fiscal, ZIP, preparo em SQLite, regras, quatro comparadores e relatório.
- [ ] Geradores sintéticos de EFD/XML e testes: unidade, regressão do legado e desempenho.
- [ ] Modelos, migrações (hub e crosscheck, com linha desabilitada do módulo nos escritórios existentes), serviço, tarefa e retenção.
- [ ] Declarar o módulo: código no `ProductModule.Code`, catálogo (fora do cadastro, D-288), grupo Fiscal da navegação e azulejo do painel.
- [ ] Telas no padrão CICA: lista, nova conferência, envio com recibo e verificações cruzadas, andamento, resultado com filtros na URL e downloads.
- [ ] Dataset `fiscal_counterparts.v1`, processador .NET e fila no servidor, atrás de `CONTRAPROVA_AGENT_ENABLED` desligado.
- [ ] Inspeção em navegador (375, 768 e 1440 px; claro e escuro; teclado) com duas rodadas de correção.
- [ ] Fechar a documentação: V-300, registro de execução, `CICA-QA.md`, `docs/cica-module-truth.md` e README.

## Protocolo do agente (fila do Contraprova)

Autenticação igual à dos demais endpoints `/api/agent/v2/` (cabeçalhos `X-Hub-Agent-ID`, `X-Hub-Agent-Timestamp` e `X-Hub-Agent-Signature`, HMAC). O agente só consulta com o catálogo embutido: o SQL nunca vem da nuvem.

- `POST /api/agent/v2/contraprova/jobs/next` com `{"source_system":"dominio"}` devolve `{"job": null}` quando não há trabalho, ou `{"job": {"id", "dataset_code": "fiscal_counterparts", "schema_version": 1, "query_sha256", "parameters": [{"name", "value", "odbc_type"}], "max_rows": 200000, "page_size": 500}}`. Os parâmetros seguem a ordem do manifesto: `codi_emp_sai`, `start_sai`, `end_sai`, `codi_emp_ent`, `start_ent`, `end_ent`. `404` (recurso desligado) vale como "sem trabalho".
- `POST .../jobs/<id>/batches` com `{"sequence": 0, "rows": [{"chave_nfe", "direcao", "uf"}]}` devolve `{"status": "accepted"}` ou `"duplicate"`.
- `POST .../jobs/<id>/complete` com `{"row_count", "pages"}`.
- `POST .../jobs/<id>/failure` com `{"error_code", "detail"}`, em que `error_code` é `dataset_mismatch`, `dataset_not_validated`, `row_limit`, `odbc_error` ou `agent_error`, e `detail` tem até 200 caracteres sem dados.

`direcao` é `S` ou `E`; `uf` vazio vira `""`. O trabalho reivindicado volta à fila se o agente ficar 15 minutos sem enviar.

## Bloqueios e responsabilidade

Q-46 (regras fiscais) e Q-47 (contrato do dataset e chave em claro). Sem Q-46 as regras de D-301 valem como padrão e aparecem em cada relatório; sem Q-47 o dataset fica `validated: false` e só o caminho por arquivo funciona. O ensaio na base real do Domínio, a instalação de um MSI novo no servidor do escritório (D-291) e a homologação pertencem à etapa 12 (D-86). Não há amostra real de SPED/XML: a validação desta etapa é feita com arquivos sintéticos e declara esse limite.

Regras, autorização externa e valores comerciais: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Portão vigente da CICA por fase: `ruff check`, `ruff format --check`, `mypy src`, `pytest -q`, `manage.py check` e `makemigrations --check --dry-run`, com piso de cobertura de 85%.

Provas específicas desta etapa:

- Cada achado da tabela acima tem um teste que falha no comportamento antigo.
- Módulo desligado devolve recusa; colaborador sem o código no escopo devolve recusa; empresa de outro escritório não aparece; sessão de suporte somente-leitura não cria nem baixa derivado.
- Entrada inválida (extensão, tamanho, conteúdo falso, ZIP malicioso, DTD/entidade) volta com motivo e não derruba a requisição.
- Um escritório que hoje é só NFS-e continua sendo tratado como só NFS-e depois da migração do novo código.
- EFD de 200 mil linhas e 10 mil XML processados dentro do orçamento de memória do worker e do limite de tarefa.
- A fila do agente reivindica sem duplicar, devolve trabalho abandonado, é idempotente e nunca lista o dataset em `profitability/datasets`.

**Critério de encerramento local:** módulo declarado e fora do cadastro, quatro ferramentas funcionando por arquivo, telas no padrão da CICA, retenção aplicada e consulta ao Domínio implementada atrás de sinalizador desligado. O aceite operacional — instalar o agente novo, ensaiar a consulta na base real e conferir a UF contra o Domínio — é obrigatório na etapa 12.

## Evidências e próximo passo

Auditoria de 21/10/2026: leitura integral dos views, formulários, templates e scripts do Tax Envel, conferência dos leiautes 0000, C100, C190, D100 e D190 no Guia Prático da EFD ICMS/IPI e do desenho de módulo, de upload, de fila e de agente do CICA. Não houve execução do legado, dado real, chamada externa nem custo.

Próximo passo: responder Q-46 (regras) e Q-47 (contrato do Domínio); instalar o agente novo e ensaiar `fiscal_counterparts` na base real autorizada (etapa 12); só então `validated: true`, `CONTRAPROVA_AGENT_ENABLED` ligado e habilitação caso a caso no console. Antes disso, o caminho por arquivo cobre as quatro ferramentas.

## Prompt de execução

> Execute a etapa 15 conforme D-300 a D-302. Porte o produto do Tax Envel, não a sua base: autenticação, escritório, carteira, auditoria e privacidade da CICA prevalecem. Não reintroduza `CFOP_IGNORAR` como supressão silenciosa, `float` para dinheiro, SQL por interpolação, leitura em UTF-8 com substituição nem banco interno hard-coded. Não invente regra fiscal além de D-301: o que faltar vira pergunta em Q-46. Não marque como homologado o que foi apenas simulado.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
