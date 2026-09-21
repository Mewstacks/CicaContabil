# CICA — análise integral do projeto em 21/09/2026

Esta análise atualiza a fotografia técnica e documental sem substituir decisões
confirmadas, evidências anteriores ou os critérios de homologação. As escolhas
canônicas estão em [DECISOES.md](../../DECISOES.md) e a execução observada em
[VALIDACOES.md](../../VALIDACOES.md).

## Objetivo final

A CICA é o SaaS da Mewstack para escritórios contábeis. Ela reúne operação
multiempresa, permissões e auditoria por escritório, serviços centrais e um
agente instalável no Windows do escritório. A oferta prevista cobre acesso e
administração, Domínio, Siescon, IA, Triagem, NFS-e, Central Integra Contador,
Conciliação, Radar e cobrança.

O produto só está pronto para venda quando o escritório consegue configurar,
executar, conferir evidência e recuperar uma falha, com permissões, cobrança,
suporte e documentação coerentes. Implementado, testado localmente, homologado
no ambiente real e liberado para venda são estados distintos. A IA começa por
API central e a futura IA local só pode se tornar padrão após a etapa 13; dados
e ajustes privados ficam isolados por escritório (D-46–D-51).

## Arquitetura e maturidade verificadas

O checkout é um Django 6/DRF com Celery, Redis, PostgreSQL, banco operacional
e banco de conhecimento separados, OpenAPI, auditoria, criptografia e controles
LGPD. As aplicações principais são `accounts`, `audit`, `common`, `hub`,
`integra`, `intelligence`, `knowledge`, `organizations`, `platform`, `privacy`
e `triage`. Também há agente Python de apoio, serviço/configurador/MSI .NET
para Windows, runtime multimodal e runtime QLoRA, Compose e CI. O inventário
detalhado permanece em [inventario-conclusao.md](inventario-conclusao.md).

| Área | Maior nível demonstrado | Limite atual |
| --- | --- | --- |
| Base, acesso e agente/Domínio | Implementação e validação local concluídas nas etapas 01–03 | Produção, SMTP/DNS, mTLS, backup `.dom`, rede e destino Windows real pertencem à etapa 12. |
| Siescon | Preparação comum local | Falta o contrato Q-33; não existe adaptador específico. |
| IA | Preparação local parcial, com isolamento, proveniência, manifesto que recusa identificadores pessoais/reescrita de artefato e contrato privado com prioridade local | Curadoria, egressão, limites, corpus, runtime/modelo e artefato reais ainda não foram homologados. |
| Triagem, NFS-e, Integra, Conciliação e Radar | Fluxos e controles locais/simulados; NFS-e expõe fatos normalizados e pagina a carteira | Dependem de provedores, certificados, layouts, amostras e prova de recuperação autorizados. |
| Cobrança | Regras, tokens, webhook e cliente Asaas validados localmente | Falta orquestração comercial e homologação Asaas sem custo não autorizado. |
| Jornadas e interfaces | Inspeção local parcial | Faltam todos os perfis, estados e a aderência integral entre oferta e capacidade homologada. |

## Continuidade do plano mestre

As etapas 00–03 estão concluídas apenas no patamar local. A etapa 04 é a
próxima habilitada. D-53 confirma que existe servidor/banco Siescon disponível;
D-54 permite somente leitura e exportação revisada, jamais escrita direta.

A preparação existente é deliberadamente conservadora: `AccountingExport`
reconhece o destino `siescon`, mas a tabela de adaptadores contém somente
Domínio. A solicitação de Siescon falha explicitamente antes de consultar
lançamentos ou produzir arquivo. Esse bloqueio impede que um layout ou uma
integração sejam fingidos como funcionais.

Para desbloquear Q-33, o técnico Siescon deve encaminhar por canal seguro:

1. versão instalada, banco/driver e meio de leitura somente leitura;
2. ambiente de homologação, revogação e contato técnico;
3. schema e campos autorizados de empresas, contas e lançamentos, incluindo
   identificador da empresa e cursor incremental;
4. layout versionado de exportação/importação, amostra sintética e critério de
   conferência da importação.

Com esse contrato, o incremento autorizado é um adaptador versionado com
leitura idempotente, diagnóstico seguro e exportação revisada. A importação e
conferência no destino continuam necessárias para o aceite de D-73 e da etapa
04; a homologação comercial continua concentrada na etapa 12 por D-87.

## Revalidação desta execução

Em ambiente macOS local, sem credenciais, dados de clientes, conexão Siescon,
arquivo de ERP, chamada a provedor, custo ou deploy, passaram Ruff, Django,
migrações sem drift, 35 testes focados de conciliação (um skip de OCR local) e
a suíte integral com 759 aprovados, três skips e oito subtestes. A evidência
completa está em V-041.

Na continuidade local da etapa 05, V-042 passou a recusar CPF, CNPJ e e-mail
reconhecíveis antes da geração dos manifestos de treino/avaliação e impede a
sobrescrita de um JSONL existente. Essa proteção preserva o registro de origem
para revisão humana; não é anonimização de dados reais, treinamento ou
autorização de egressão. A revalidação correspondente fechou com 762 testes,
três skips e onze subtestes.

V-043 eliminou os 21 erros MyPy inicialmente observados nos módulos tocados,
sem alterar comportamento de negócio. Na sequência, V-044–V-068 levaram a
dívida global de 535 ocorrências a zero nos 190 arquivos verificados; V-068
também registrou Django, migrações, Ruff e a suíte integral com 762 testes,
três skips e 11 subtestes aprovados.

V-072 fechou o único checklist técnico restante da etapa 05 que independia de
serviços externos: em 73 testes e três subtestes, um runtime privado simulado
recebeu o contrato OpenAI-compatível e, mesmo com fallback configurado e
aprovado, a resposta local não chamou o provedor nem criou egressão. A prova
complementar sem opt-in mantém a negação auditada. Isso é uma verificação de
contrato, não execução de modelo, GPU, rede ou Claude reais.

Foi executado `git fetch origin --prune`; `HEAD...origin/main` tem zero commits
de cada lado. Portanto não havia mudança no GitHub a trazer nesta análise.
Após a documentação, o estado do projeto deve ser revisado normalmente antes de
qualquer integração futura.

## Conclusão objetiva

O projeto tem uma base ampla e controles locais relevantes, mas não está pronto
para venda: integrações e homologações reais críticas permanecem pendentes. O
primeiro bloqueio sequencial é Q-33/Siescon. A ação segura é obter o contrato
técnico listado acima; não é criar uma implementação por suposição.
