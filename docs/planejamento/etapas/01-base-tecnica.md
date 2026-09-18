# Etapa 01 — Estabilizar a base técnica

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Concluída em 18/09/2026 como estabilização técnica local. Todos os itens do checklist foram executados, incluindo runtime de treinamento (V-006); Fedrizzi já tem o conector Domínio ODBC pronto (D-74) e D-73 define as métricas de aceite. A conclusão não homologa Domínio, Siescon, Serpro, NFS-e, Asaas ou e-mail: cada um será provado em sua própria etapa com o critério aplicável.

**Dependências:** 00.

**Decisões relacionadas:** D-03, D-56, D-57, D-61.

## Escopo e checklist

- [x] Resolver as 66 violações atuais do Ruff e demais falhas verificadas.
- [x] Consolidar migrações e revisar compatibilidade com dados existentes.
- [x] Executar testes com PostgreSQL, Redis e workers reais em ambiente isolado.
- [x] Verificar concorrência em consumo, faturamento, filas e publicação de modelos — teste concorrente de idempotência de consumo em PostgreSQL; suíte de risco no mesmo banco cobre faturamento, filas e publicação.
- [x] Validar builds da aplicação, runtime multimodal, treinamento e agente — trainer construído com imagem oficial fixada por digest; binário e ambiente validados sem GPU, modelo ou treino.
- [x] Revisar dependências, configuração de produção e tratamento de segredos.

## Bloqueios e responsabilidade

Atualização de 18/09, D-70/D-71: retomada autorizada e LlamaFactory mantido para o treinamento local. A imagem oficial foi fixada por digest e validada; o Dockerfile rejeita tag mutável. Docker Desktop 4.91.0 e WSL 2.7.1 estão operacionais; PostgreSQL 17 e Redis 7.4 locais foram iniciados por Compose. D-73 resolve as metas de aceite e D-74 confirma o conector Domínio já configurado. Demais integrações externas são dependências de suas próprias etapas, não pendência desta estabilização.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Ruff, Django check, migrations dry-run, suíte, concorrência PostgreSQL, workers/Redis e builds; registrar separadamente qualquer ambiente indisponível.

**Critério de aceite:** CI aprovado e instalação reproduzível; testes com SQLite não substituem testes concorrentes em PostgreSQL.

## Evidências e próximo passo

Retomada de 18/09: Ruff aprovado; 12 testes do runner e da configuração de deploy aprovados. `cica-trainer:stage01` foi construído a partir da imagem oficial fixa e `llamafactory-cli version/env` iniciou no contêiner. `runtime/trainer/image.env` e o CI usam o mesmo digest; o rebuild local por esse arquivo passou. A imagem ocupa 26.4 GB localmente e detectou CPU neste computador. Nenhum modelo nem treino foram baixados/executados. Após D-73, a suíte completa fechou com 742 aprovados, 2 ignorados e 8 subtestes em 85,31 s; check, migrations dry-run e Ruff passaram. A inspeção segura do banco confirmou um conector Fedrizzi `direct_odbc` e fonte Domínio local `ready`, sem ler DSN ou dados. Aceite técnico local atendido; próximo passo é etapa 02.

V-004 registra comandos e resultados: Ruff, Django check, migrations dry-run, 740 testes, 2 ignorados e 8 subtestes, 95 testes críticos em PostgreSQL, worker Celery via Redis, auditoria de dependências limpa, imagens Docker e MSI do agente com checksum. Não houve homologação externa. Após receber Q-37, construir o runtime de treinamento e registrar seu resultado antes de encerrar a etapa.

## Prompt de execução

> Execute a etapa 01. Estabilize o estado atual preservando alterações existentes, faça o CI passar e valide banco, filas, migrações e builds em ambiente isolado. Registre resultados e limitações reais; não considere testes simulados prova de produção.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
