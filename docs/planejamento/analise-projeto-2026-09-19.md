# CICA — análise consolidada do projeto em 19/09/2026

Esta análise atualiza a fotografia técnica e documental da CICA sem substituir
decisões confirmadas, evidências anteriores ou critérios de homologação. A fonte
canônica para escolhas é [DECISOES.md](../../DECISOES.md); a evidência executada
fica em [VALIDACOES.md](../../VALIDACOES.md).

## Objetivo final confirmado

A CICA é um SaaS da Mewstack para escritórios contábeis, com operação
multiempresa, permissões e auditoria por escritório, serviços centrais e agente
instalável no ambiente Windows do escritório. O produto reúne acesso e
administração, Domínio, Siescon, IA, Triagem, NFS-e, Central Integra Contador,
Conciliação, Radar e cobrança.

O critério de produto não é a mera existência de uma rota, tela, modelo ou teste
isolado. O módulo só fica pronto para venda quando o escritório consegue
configurá-lo, executar a tarefa, conferir a evidência e recuperar uma falha, com
permissões, cobrança, documentação e suporte coerentes com o comportamento
real. A IA inicia pela API central autorizada e poderá migrar para a IA local
após a prova da etapa 13; dados e ajustes privados continuam isolados por
escritório (D-46 a D-51).

## Arquitetura encontrada no checkout

O núcleo é Django 6 com DRF, Celery, Redis, PostgreSQL, dois bancos lógicos
(operacional e conhecimento), OpenAPI, auditoria, criptografia e controles LGPD.
Há onze aplicações Python: `accounts`, `audit`, `common`, `hub`, `integra`,
`intelligence`, `knowledge`, `organizations`, `platform`, `privacy` e `triage`.
O checkout também contém:

- agente Python e agente nativo .NET/Windows, configurador e MSI;
- runtime multimodal e runtime de treinamento QLoRA com LlamaFactory fixado por
  digest;
- Compose para PostgreSQL/Redis/web/worker, CI que executa lint, Django,
  migrações, testes e os três builds Docker;
- rotas web, APIs REST, API v2 do agente e tarefas Celery para ciclos de
  contrato, conhecimento, IA, triagem, NFS-e, conciliação, DTE/DCTFWeb,
  parcelamentos e Radar.

O [inventário de conclusão](inventario-conclusao.md) permanece o mapa detalhado
de modelos, rotas, APIs, tarefas e artefatos operacionais.

## Leitura por capacidade

| Capacidade | Estado confirmado | Limite que ainda impede venda/homologação |
| --- | --- | --- |
| Base, acesso e plataforma | Etapas 01 e 02 concluídas no nível local; há cadastro, MFA, organizações, isolamento, contratos e console. | SMTP/DNS, ambiente publicado e jornadas externas pertencem à etapa 12. |
| Domínio e agente Windows | Etapa 03 concluída localmente; leitura controlada, backup preparado, arquivamento e diagnóstico constam no código. | Piloto com site publicado, mTLS, arquivo `.dom`, rede e raiz Windows real na etapa 12. |
| Siescon | Fonte e destino de exportação são modelados; a exportação é recusada sem adaptador revisado. | Não há versão, mecanismo autorizado, schema, identificador empresarial ou layout em Q-33. |
| IA | API Claude, isolamento, corpus, avaliação e runner local existem como preparação; fontes e exemplos têm escopo de empresa, período e área, com recuperação que não cruza empresas. | Tetos, egressão, governança da chave, curadoria e piloto autorizado continuam abertos. |
| Triagem | Conectores de e-mail, quarentena, revisão, biblioteca e destino Windows são preparados/testados localmente. | Regras documentais, caixas/scanner reais, retenção e arquivamento no destino real. |
| NFS-e, Integra, Conciliação e Radar | Há fluxos, filas e testes locais/simulados. | Certificados, contratos, amostras, chamadas autorizadas e provas de recuperação reais. |
| Cobrança | Medição e fundamentos de contrato existem; Asaas/manual foram decididos. | Cliente Asaas, preços operacionais, ciclo completo e homologação. |

## Plano mestre e próximo trabalho

As etapas 00, 01, 02 e 03 estão concluídas somente como implementação e
validação local. A etapa 04 é a próxima habilitada, está em andamento e não pode
ser concluída ou implementada por suposição. D-53 confirma que há
servidor/banco Siescon disponível; D-54 limita a operação a leitura e exportação
revisada, sem escrita direta.

Para avançar a etapa 04, o responsável técnico do Siescon deve encaminhar por
canal seguro, sem segredos no chat:

1. versão instalada, banco/driver e mecanismo de leitura somente leitura;
2. ambiente de homologação, procedimento de revogação e contato técnico;
3. schema e campos autorizados para empresas, contas e lançamentos, incluindo o
   identificador de empresa e o cursor de atualização;
4. layout de exportação/importação, versão, amostra sintética e critério para
   conferir a importação.

Com esse contrato, o próximo incremento é um adaptador versionado, leitura
idempotente, diagnóstico seguro e exportação revisada. Sem ele, gerar SQL,
endpoints, credenciais ou arquivos Siescon seria especulativo e contrariaria
D-54, D-56 e Q-33.

## Achados desta análise

- O checkout estava limpo antes desta execução; não havia alterações locais de
  outra pessoa a preservar.
- A estação atual é macOS e não possuía o ambiente virtual da validação Windows.
  `uv sync --locked --all-extras` recriou somente `.venv/`, que é ignorado pelo
  Git, usando CPython 3.12.13 e o lock versionado.
- A primeira execução de `uv run ruff check .` encontrou 16 E501 em três
  arquivos do agente/Triagem. As correções foram apenas quebras de linha. A
  primeira suíte completa também revelou que, ao escolher a biblioteca interna,
  o formulário apagava indevidamente o padrão de pastas Windows. O padrão agora
  é preservado, como a regressão existente exige. A reexecução passou com Ruff,
  Django, migrações e **747 testes aprovados, 3 ignorados e 8 subtestes**. Ver
  V-031.
- Foram atualizados os ponteiros de escopo em README, planejamento e plano
  mestre. Os textos datados sobre a limitação original à etapa 00 permanecem no
  histórico, identificados como tal; eles não são mais apresentados como o
  estado vigente.

## Limites desta execução

Não houve deploy, chamada externa, acesso a dados de cliente, conexão Siescon,
uso de credenciais, cobrança, geração de custo, treinamento de modelo ou piloto.
A prova completa em SQLite não substitui PostgreSQL/Redis ou fornecedor real;
as evidências anteriores que usam esses ambientes continuam datadas e
referenciadas em `VALIDACOES.md`.
