# Etapa 14 — Incorporar Rentabilidade por Cliente (Lucrums)

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** Em andamento desde 22/09/2026 na branch dedicada `codex/lucrums` (D-120). O corte de origem continua `Mewstacks/ProjetoARD@main` em `d9d4ebb`; os pulls de 28/09/2026 não trouxeram commits novos (V-112). As fases 1, 2 e 3 estão concluídas no nível local (V-105 a V-108 e V-110). A fase 4 tem catálogo fixado por hash, ponte de 32 bits, configurador único para os dois ERPs e WiX revisado (V-109/V-111); falta executar o novo job de pacote no CI Windows. V-112 corrigiu a herança visual e verificou seis telas. V-113 corrigiu a identidade de matriz/filial com documento repetido; o portão de cobertura global está em 80,09% ante 85% exigidos. Q-33, Q-42 e Q-43 foram resolvidas por D-116 e D-117; seguem abertas Q-39, Q-40 e Q-41.

**Dependências:** 01–03. A ingestão usa o agente da etapa 03; a operação do perfil Siescon depende do adaptador e da homologação da etapa 04.

**Decisões relacionadas:** D-80, D-86, D-108, D-109, D-110, D-111, D-112, D-113, D-114, D-115, D-116, D-117, D-118, D-120.

## O que é o módulo

O Lucrums responde quanto cada cliente dá de lucro ao escritório: `resultado = honorários − (horas lançadas × custo/hora do colaborador)`, com margem, faixa e mensalidade sugerida por competência. Ele lê o ERP no servidor do próprio escritório — Domínio Sistemas por SQL Anywhere e Siescon por Btrieve — e materializa métricas por cliente e por colaborador.

O custo/hora tem uma única conta, fixada após a auditoria de setembro de 2026 que removeu uma segunda fórmula divergente em 28,9%: custo anual do colaborador dividido pelas horas produtivas do ano, onde as horas produtivas descontam feriados, férias, folgas e ausências e aplicam o índice de produtividade do escritório. Os vetores dessa conta vivem em `contracts/calculations/v1.json` e são lidos pelo teste; não se altera um valor ao portar.

## Escopo e checklist

- [x] Sincronizar os dois repositórios localmente e fixar o commit de origem (22/09/2026).
- [x] Registrar D-108 a D-112 e abrir Q-39 a Q-43 no registro único de dúvidas.
- [x] Criar `src/apps/profitability` e portar o domínio: competência, colaborador, usuário do ERP, salário, registro de horas, serviço faturado, evento de faturamento, mensalidade, segmento e configuração do módulo (V-105).
- [x] Substituir a entidade `Empresa` do Lucrums por `CompanyErpProfile` ligado a `hub.ClientCompany`, conforme D-109, com a resolução de identidade contra a carteira por documento, código Domínio e gêmea do outro ERP (V-105, V-106).
- [x] Portar o motor de cálculo e os serviços de recomputação sem alterar os vetores do contrato (V-105).
- [x] Declarar o módulo: código no `ProductModule.Code`, migração de choices, entrada no catálogo, grupo "Gestão" na navegação e azulejo no painel (V-107). Por D-115 ele fica fora dos módulos padrão do cadastro enquanto Q-39 e Q-41 estiverem abertas.
- [x] Portar as telas para templates por D-110, com o gráfico de D-113 como SVG próprio (V-107, V-108). Lista de clientes e tela de conectores não foram portadas: a CICA já as tem. Inspeção visual em navegador, responsividade e leitor de tela pertencem à etapa 11.
- [x] Completar a ficha analítica do cliente dentro do módulo, ligada à carteira única: evolução, horas automáticas × F9, atividades, equipe, unidades do grupo, referências e histórico, sempre recortados por `CompanyAccessGrant` (V-110).
- [x] Trazer o catálogo de consultas fixado por SHA-256 e o processamento por conjunto de dados para o protocolo de agente vigente, atrás de sinalizador desligado por padrão (V-106). O preflight por escritório não veio: o indicador de contrato validado segue vindo do manifesto.
- [-] Unificar o conector Windows por D-111, com o alvo resolvido em D-116 (V-109/V-111). Entraram catálogo fixado por hash, processador, ponte ODBC de 32 bits, seleção/teste do Siescon no configurador, atalho persistente e revisão do WiX. O job Windows agora gera e confere o MSI único; falta observar sua primeira execução no CI. O atualizador automático da origem foi deliberadamente excluído por D-118.
- [x] Portar e ampliar os testes do Lucrums (V-105 a V-110): cálculo contra o contrato, domínio, serviços, casador, ingestão, protocolo de agente, telas, ficha analítica e catálogo do conector. A recusa por módulo desligado, o escopo do colaborador e da empresa, o isolamento entre inquilinos e a sessão somente-leitura estão cobertos.
- [-] Revalidar a etapa após a atualização local (V-112/V-113): 971 testes Python e 20 .NET passaram; seis telas foram abertas em navegador em desktop e celular, a herança dos estilos foi corrigida e documento repetido entre matriz/filial não funde mais cadastros. Faltam cobertura global de 85%, build do MSI no CI Windows, validação acessível integral e homologação operacional.

## Plano de análise e inserção

Este é o plano vigente da incorporação; ele continua as fases já executadas e não cria uma segunda trilha concorrente.

| Fase | Análise / inserção | Estado e prova |
|---|---|---|
| A — congelar a origem | Localizar o ProjetoARD/Lucrums, fixar commit, inventariar código, contratos e diferenças de base | Concluída; origem `d9d4ebb`, inventário e decisões D-108 a D-112 |
| B — definir fronteiras | Preservar conta, organização, segurança, auditoria e carteira da CICA; importar só o produto | Concluída; `ClientCompany` é a entidade única por D-109 |
| C — portar domínio e cálculo | Migrar modelos, serviços, casamento ERP/folha e vetores sem mudar fórmulas | Concluída localmente; V-105 e V-106 |
| D — inserir no hub | Declarar catálogo, acesso, navegação e estados ligado/desligado sem ativar oferta | Concluída localmente; V-107 e D-115 |
| E — migrar experiência | Reescrever a SPA como templates CICA, reaproveitar carteira/conectores e completar a ficha do cliente | Concluída por requisição; V-108 e V-110. V-112 corrigiu estilos herdados e inspecionou seis telas em dois tamanhos; leitor de tela e jornada integral seguem na etapa 11 |
| F — consolidar integração | Usar um agente, catálogo por hash e ponte x86; revisar o MSI único | Parcial; V-109/V-111. Código e WiX revisados, job Windows preparado; falta a prova da execução no CI. Autoatualizador excluído por D-118 |
| G — validar e liberar | Rodar portões locais, validar Windows/ERP real, piloto e regras comerciais | V-113: testes funcionais limpos, cobertura global 80,09% abaixo do piso de 85%; Windows/ERP/piloto ficam na etapa 12 e Q-39 a Q-41 bloqueiam oferta |

## Bloqueios e responsabilidade

Q-39 a Q-41. Q-39 é o bloqueio de produto mais sério: o levantamento do próprio Lucrums registra que não há fonte de receita em nenhum dos dois ERPs — `efservicos` está vazio no escritório e os campos `PFT_*` do Siescon estão zerados desde 2018. Sem honorário não existe margem, e o módulo entrega custo e horas, não rentabilidade. Q-40 define o que a tela pode afirmar enquanto a cobertura de horas for baixa: em 21/09/2026 eram 11%, com 30 de 47 pessoas sem nenhuma hora lançada, o que faz a margem ler alto demais. Isso é limite de dado, não de fórmula, e pela regra de D-98 a D-106 não pode aparecer silenciosamente incompleto. Q-41 mantém o módulo sem preço. Q-33, Q-42 e Q-43 estão encerradas por D-116 e D-117.

Instalação real, assinatura de pacote e piloto permanecem na etapa 12 por D-86.

Regras, autorização externa e valores comerciais: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Portão vigente da CICA por fase: `ruff check`, `ruff format --check`, `mypy src`, `pytest -q`, `manage.py check` e `makemigrations --check --dry-run`, com piso de cobertura de 85%.

Provas específicas desta etapa:

- O motor de cálculo passa contra `contracts/calculations/v1.json` sem alterar um vetor. É o sinal de que o cálculo atravessou intacto.
- Módulo desligado no escritório devolve recusa; colaborador sem o código no escopo devolve recusa; cliente de outro inquilino não enxerga nada; sessão de suporte somente-leitura não grava.
- O grupo "Gestão" só aparece na navegação com o módulo ligado.
- A ingestão é simulada de ponta a ponta sem Windows, do pareamento ao lote cifrado.
- O conector unificado é construído pela integração contínua em `windows-latest`.

**Critério de encerramento local:** módulo declarado, cálculo portado e aprovado contra o contrato, telas no padrão da CICA, ingestão preparada atrás de sinalizador desligado e conector único construído. O aceite operacional — instalar em servidor de escritório, sincronizar ERP real e conferir margem contra a contabilidade — é obrigatório na etapa 12.

## Evidências e próximo passo

Verificação local de 22/09/2026, base das decisões D-108 a D-112: os dois backends são forks do mesmo boilerplate `Mewstacks/_DjangoSetup`, com Django 6.0, Python 3.12, Celery 5.6.3 e cryptography 50.0.0 nas duas árvores; `OrganizationScopedModel`, `EncryptedTextField` e `blind_index` são equivalentes, com a CICA como superset endurecido, o que permite descartar as camadas de base do Lucrums e mover só o produto — cerca de 10.300 linhas de Python, 10.100 de TypeScript a portar para templates e 2.591 de C# a consolidar no agente.

Próximo passo: observar o primeiro build do MSI único no CI Windows e escrever o adaptador Siescon da etapa 04, que D-117 destravou. O autoatualizador da origem não faz parte do corte por D-118. A ficha analítica precisa da inspeção visual da etapa 11; Q-40 continua necessária antes de publicar margem como afirmação da carteira inteira, e Q-39 antes de o módulo poder ser oferecido.

## Prompt de execução

> Execute a etapa 14 conforme D-108 a D-112. Porte o produto do Lucrums, não a sua base: os apps de conta, organização, auditoria e privacidade da CICA prevalecem. Não crie segunda carteira de empresas. Não reintroduza a fórmula antiga de custo/hora removida pela auditoria de setembro de 2026. Não invente fonte de receita, limiar de cobertura, preço ou aceite do material Siescon — esses são Q-39 a Q-42.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.
