# CICA — validações e evidências

Atualizado em 17/09/2026. Registro na raiz conforme D-59. Leia com [PLANO-MESTRE.md](PLANO-MESTRE.md) e [DECISOES.md](DECISOES.md).

**Escopo desta entrega: somente etapa 00.** As etapas 01–13 não foram executadas. Decisões do responsável ficam em DECISOES.md; este arquivo registra verificações técnicas, sem confundir decisão, teste e homologação.

## V-001 — Base técnica observada antes da edição documental

Data: 17/09/2026, nesta conversa. Ambiente: checkout Windows local, Python da `.venv`, configurações Django de teste; `TEST_USE_EXTERNAL_SERVICES=false` e `TEST_SQLITE_PATH` vazio. Banco de teste SQLite em memória. Sem homologação externa nesta análise.

| Verificação | Resultado observado | Limite |
|---|---|---|
| `python -m pytest -q` | 740 aprovados, 1 ignorado, 8 subtestes aprovados; 74,48 s | Não demonstra concorrência PostgreSQL nem operação real de serviços externos |
| Teste ignorado | `tests/test_regaro_auth_flow.py:155`: Python Playwright opcional | Não equivale a navegação validada; não houve inspeção Playwright nesta etapa |
| `python manage.py check` | Sem problemas (0 silenciados) | Configurações de teste, não certificação de produção |
| `python manage.py makemigrations --check --dry-run` | No changes detected | Nenhuma migration aplicada por esta etapa; não prova migração de base produtiva |
| `python -m ruff check . --output-format concise` | 66 violações: comprimento de linha e ordenação de imports | CI ainda bloqueado; não corrigidas por restrição à etapa 00 |
| Inventário inicial Git | 291 entradas em `git status --short` antes da documentação | Trabalho local anterior preservado; não é uma release consolidada |

Os comandos acima foram executados na análise anterior à materialização dos documentos. A leitura de Ruff foi repetida em JSON antes da restrição final de escopo e manteve 66 achados. Não foram refeitos testes funcionais após mudanças exclusivamente documentais.

## V-002 — Evidência estática por área

| Área | Implementado / observado no código | Testado localmente nesta análise | Homologação real / venda |
|---|---|---|---|
| Cadastro, acesso, organizações, auditoria e privacidade | Modelos, rotas, serviços e testes no checkout | Suíte V-001; não atribuir cobertura integral a cada fluxo | Jornadas externas/produção não homologadas por esta análise |
| Domínio | Consultas fixas e limites 1.000/10.000/5.000; agente Python, fila, sync e descoberta | Suíte V-001 e leitura do código | Há registros históricos de sondagens ODBC; não comprovam cobertura completa ou instalação vendável |
| Agente Windows nativo | Heartbeat, backup e arquivamento; sincronização local ainda depende de Python | Leitura de `Worker.cs` e README; build não executado nesta etapa | Instalação limpa, atualização e destino real ainda pendentes |
| Siescon | Referência no modelo/UI; adaptador não encontrado | Busca estática; não há teste de conector real | Banco disponível confirmado pelo responsável; acesso e layout ainda não inspecionados |
| IA | API, roteamento local, corpus, runner QLoRA, avaliação e publicação; busca lexical | Suíte V-001; sem chamada de IA nesta etapa | Pipeline completo e hardware definitivo não homologados; geração histórica isolada não é aceite de produto |
| Triagem | OAuth/IMAP, leitores, quarentena, revisão/arquivo e trabalho Windows | Suíte V-001 | Caixas, scanner, análise e arquivamento reais ainda requerem piloto |
| NFS-e | Cliente ADN, mTLS, checkpoints e área operacional | Suíte V-001, respostas simuladas | Não houve consulta ADN nesta análise |
| Integra | DTE, DCTFWeb, PARCSN, filas e consumo | Suíte V-001, transporte simulado | Não houve consulta/ciência/emissão Serpro nesta análise |
| Conciliação | Fontes preservadas, layouts, movimentos, lançamentos e exportação | Suíte V-001, fixtures | Layouts reais, importação nos ERPs, OCR e volume ainda exigem prova |
| Radar | Coleta e tarefas existentes | Suíte V-001 | Agenda e relevância operacional não homologadas nesta análise |
| Cobrança | Medidores/faturas e receptor Asaas | Suíte V-001 | Cliente de cobrança e ciclo completo Asaas ainda pendentes |
| Infraestrutura | Compose, workflows, imagens e runbooks | Inspeção estática | Não houve build/deploy, PostgreSQL/Redis reais ou restauração nesta etapa |

## V-003 — Etapa 00: documentação e continuidade

Estado: materializada; conferência documental em andamento.

Entregas: plano e decisões na raiz, registro de validações, 14 arquivos de etapa com prompts, inventário estático, dúvidas com responsáveis/dependências, ponteiros dos endereços anteriores e instrução de continuidade em AGENTS.md.

Não houve edição de código da aplicação, migração, instalação de dependências, conexão a banco de cliente, execução de treino, chamada paga, deploy ou publicação nesta etapa. Não foram alterados arquivos `.env`, credenciais ou dados de clientes.

## Como acrescentar evidência

Use ID V único, data, etapa, ambiente, comando/procedimento, resultado, caminho da evidência e limites. Diferencie resultado observado nesta execução de relato histórico. Registre falhas e skips. Só avance de teste local para homologação após prova no ambiente correspondente e de homologação para liberação com o aceite aplicável.

Histórico detalhado anterior: [registro de execução](docs/planejamento/registro-de-execucao.md). [Próxima etapa preparada](docs/planejamento/etapas/01-base-tecnica.md), ainda não autorizada pela última instrução de escopo.
