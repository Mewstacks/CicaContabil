# Fontes e histórico de planos

Levantamento em 15/09/2026. Foram inspecionados `docs/`, os planos em `C:\Users\gege\.claude\plans`, os arquivos de sessão em `C:\Users\gege\.codex\sessions` e o `PLAN.md` citado no histórico em `Downloads`. Não foi indicado outro acervo. A busca de nomes e conteúdo mostrou muitos planos de CRMew, IdeaLead, Spreading, Conta200 e outros sistemas; a presença incidental de “HubContador”, “CICA” ou “Mewstack” nesses planos não os transforma em especificação desta aplicação.

## Planos Claude diretamente relacionados

| ID | Fonte local | Papel e limite |
| --- | --- | --- |
| CL-01 | `quero-uma-revis-o-valida-o-serene-thompson.md` | Plano inicial de tornar HubContador SaaS vendável por módulos: segurança, Integra, Domínio, entitlement, Banco Inter/Asaas, onboarding e telas. Retrata um código anterior; problemas apontados ali podem já ter sido corrigidos. |
| CL-02 | `preciso-que-todas-as-mighty-sloth.md` | Matriz de rotas/personas, becos sem saída, teste de fluxo e revisão crítica de telas. É plano de execução e diagnóstico de 11/09, não certificado de conclusão atual. |
| CL-03 | `faz-um-plano-do-breezy-flame.md` | Plano de go-live CICA/HubContador de 14/09: Serpro real, NFS-e ADN, cobrança Asaas, Fly e instalação Windows. Contém decisões atribuídas ao responsável e achados técnicos; diverge da documentação CICA posterior em cobrança e acesso. |
| CL-04 | `reuni-o-de-11-09-16-10-luminous-barto.md` | Plano Claude da Triagem de Arquivos feito após reunião de 11/09. Define fluxo por e-mail, biblioteca/Windows, catálogo, quarentena, classificação e revisão; inclui hipóteses explícitas e perguntas ainda abertas. O plano inicial no repositório continua sendo fonte da transcrição e da justificativa de segurança. |

## Contexto antecedente, sem adoção automática

O desenho técnico de CL-03 para Asaas propõe **uma cobrança por fatura variável**, em task separada do fechamento local; idempotência por referência da fatura; evento de atraso que entra em carência e suspensão posterior por varredura; reconciliação diária para eventos perdidos; e migração que mantém contratos existentes fora do Asaas até escolha explícita. Essas medidas tratam risco real de cobrança dupla e de suspensão errada, mas são **propostas de implementação**, ainda sem adaptador ou prova em sandbox. A confirmação recente adotou Asaas como padrão, com exceção manual, e deixou duração da carência aberta. CL-03 também propõe separar o cliente ADN do Serpro, usando certificado por empresa e checkpoint de NSU; rotas e semântica do cursor precisam de homologação oficial, logo não são fatos da integração atual.

CL-04 propõe destino exclusivo por escritório e não migrar automaticamente arquivos já arquivados quando o modo muda; esse comportamento ainda precisa de confirmação. Propõe 12 frentes de execução e verificação, de módulo/schema até caixa de e-mail, extração, revisão, biblioteca, agente Windows e checklist. A implementação atual entregou apenas parte do domínio e um fluxo manual em andamento, enquanto a confirmação posterior definiu **e-mail como entrada vendável** e **Claude API provisório**. Os títulos de commits do plano são sugestões históricas, não commits, cards ou versões criados por esta memória.

| ID | Fonte | Relação com a CICA |
| --- | --- | --- |
| AN-01 | `preciso-que-tu-fa-a-structured-reddy.md` | Documenta o HubCobalchini derivado do HubFedrizzi e mostra que a tela NFS-e antiga consumia MongoDB alimentado por robôs externos. As decisões de marca, banco e deploy são daquele projeto, não da CICA. |
| AN-02 | `preciso-que-tu-olhe-shimmying-whisper.md` | Port de robô NFS-e para HubFedrizzi; informa riscos e dependência externa. Não comprova que o novo SaaS tenha coleta ADN. |
| AN-03 | `c-users-gege-downloads-reuni-o-iniciada-clever-kazoo.md` | Plano de reuniões e pipeline CRMew. A sessão Codex de 12/09 o citou; a crítica posterior do responsável levou ao plano específico de triagem, sem transferir o restante do CRMew para esta aplicação. |
| AN-04 | `integrar-caixa-de-e-mail-snoopy-quiche.md` | Caixa Gmail para outro Hub, por usuário e em tempo real. Não representa a triagem por caixa de escritório e armazenamento documental da CICA. |
| AN-05 | `para-a-ia-vamos-snuggly-pumpkin.md` | Ideia de servidor local Ollama/LiteLLM para outros sistemas; serve como contexto de infraestrutura futura, sem impor modelo ou implantação à CICA. |
| AN-06 | `C:\Users\gege\Downloads\PLAN.md` | Plano de marca/landing “Regaro” de 12/09. Nome anterior substituído pela confirmação expressa de CICA em 13/09. |

## Histórico Codex relevante

O Codex não mantém nesta máquina uma pasta única de `.md` para este projeto. Seus planos, pedidos e respostas estão nas sessões JSONL. Os IDs abaixo são o sufixo do nome `rollout-*.jsonl`; o caminho começa em `C:\Users\gege\.codex\sessions\2026\09\<dia>\`. A sessão permite distinguir texto do usuário de proposta do assistente; usar apenas texto do usuário como confirmação direta.

| ID | Dia / sessão | Registro relevante |
| --- | --- | --- |
| CX-01 | 09/09 `01a08665-ac49-7c73-b684-af0b26d980e6` | Produto centralizado e modular a partir de HubFedrizzi/HubCobalchini e base `_DjangoSetup`; SEO retirado do escopo deste produto. |
| CX-02 | 09/09 `01a0870e-ef6e-7251-95ed-3d1ff56c54f3` | Domínio via ODBC local ou serviço no escritório, leitura controlada; IA local planejada com fallback Claude e curadoria. |
| CX-03 | 10/09 `01a08c15-d4c5-7450-a7a8-d181948eb020` | DTE/Integra sem planilhas e cadastro de empresas Domínio. |
| CX-04 | 10/09 `01a08ce0-7c85-7893-87bf-7a6d6082ff5c` | ODBC local somente leitura para testes, ingestão de cadastro e revisão da navegação entre empresas. |
| CX-05 | 12/09 `01a095ad-a3fc-7aa2-9d3a-f1fd7db3a67b` | Central Integra Mewstack: franquia por escritório, excedente, fatura única; plano integral enviado pelo usuário especificou fechamento dia 1, vencimento dia 10 e Inter/Asaas como meios à época. |
| CX-06 | 12/09 `01a096d1-f275-7573-a061-f8be34c1d385` | Configuração simples pelo escritório; Domínio Web por importação de backup com atualização manual; nome “Regaro” adotado temporariamente. |
| CX-07 | 13/09 `01a09dbd-cb92-7ec3-860d-498203d4ec3f` | Exigência de auditar todas as funções sem assumir requisitos; confirmação direta de que o nome oficial passou a CICA. |
| CX-08 | 14/09 `01a0a0c2-7493-7c01-871d-a3d67365855e` | Reunião de triagem tratada como conversa ambígua; pedido de plano para aprovação e conexão a caixas populares, incluindo Microsoft e Google. |
| CX-09 | 15/09 `01a0a538-458d-7182-96a8-be18eb933465` | Meta de módulos vendáveis e IA funcional por API até o PC local; respostas do responsável confirmam e-mail como única entrada v1, destino selecionado pelo escritório, Microsoft 365/Google/IMAP, Serpro central Mewstack, chave Claude no `.env`, Sonnet, configuração da conexão pelo próprio escritório e pasta de empresa com código Domínio obrigatório. |
| CX-10 | 15/09 `01a0a540-ef6a-7ba2-9539-82e946a512ef` | Solicitação de consolidar planos Claude/Codex em `.md`; confirmação nesta conversa de Asaas como padrão e contratos manuais com preços diferenciados. |

Outras sessões do projeto tratam correções locais, marca, landing, configuração e perguntas específicas. Elas não substituem os documentos e confirmações listados. Os planos de Codex em outras pastas de trabalho pertencem aos respectivos produtos, conforme o `cwd` registrado na sessão.

## Documentos versionados consultados

- [Implementação CICA](../cica-implementation.md), [inventário de auditoria](../cica-code-audit-inventory.md) e [verdade dos módulos](../cica-module-truth.md): fotografia declarada do produto, com limites e pendências.
- [Plano inicial de triagem](../plano-triagem-documental.md) e [auditoria de triagem](../cica-triage-audit.md): taxonomia da foto, perguntas e avaliação de uma versão anterior do módulo. A auditoria precisa de atualização porque há trabalho local posterior não commitado.
- [Revisão de contrato/MFA](../cica-mfa-contract-review.md), [acesso operacional](../cica-operation-access-review.md), [catálogo](../cica-catalog-safety.md), [IA](../cica-ai-scope-review.md) e [Siescon](../cica-siescon-discovery.md): correções verificadas e seus limites.
- [Direção pública](../cica-landing-direction.md), [motion](../cica-motion-review.md) e [revisão Claude original](../pt-BR/revisao-claude.md): visual e segurança, sem aprovação de lançamento.

## Regras de precedência comprovável

“Mais recente” sozinho não valida uma proposta. Uma confirmação expressa do responsável altera apenas o assunto respondido. O código pode revelar a regra atual da aplicação, mas não decide por si só a regra comercial desejada. Por isso a decisão Asaas com exceção manual substitui a declaração anterior de cobrança exclusivamente externa, enquanto meio de pagamento, ciclo, suspensão e detalhes da exceção continuam em confirmação.
