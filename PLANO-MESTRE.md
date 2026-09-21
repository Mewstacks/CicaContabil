# CICA — plano mestre de conclusão e preparação para venda

Atualizado em 21/09/2026. Plano aprovado pelo responsável nesta conversa; localização na raiz conforme D-59.

**Situação em 21/09/2026:** etapas 00, 01, 02 e 03 concluídas no nível de implementação e validação local. A etapa 04 está em andamento e bloqueada pelo contrato técnico Siescon de Q-33; a base de exportação comum já recusa Siescon até existir adaptador/layout revisados. V-041 revalidou o checkout, o bloqueio explícito e a documentação, sem criar conexão ou arquivo Siescon; também confirmou que `main` e `origin/main` estavam no mesmo commit antes desta entrega. V-042 avançou localmente a etapa 05: o manifesto de treino/avaliação agora recusa identificadores pessoais antes de gravar artefato e não sobrescreve artefato existente, preservando revisão humana. V-043 eliminou a dívida de tipagem encontrada nos módulos envolvidos; V-044–V-068 reduziram a dívida global de 535 ocorrências para **zero nos 190 arquivos verificados por MyPy**, incluindo Triagem, Hub, contratação, PARCSN, transporte local, livros de consumo, coletores, configuração, gateway de IA, relatórios, sincronização bancária, segurança, acesso DTE, operações, NFS-e e IA, sem mudar regra de negócio. V-063 reexecutou a regressão integral local com 762 testes aprovados; V-073 a repetiu com 763 testes aprovados após completar a revisão e a carteira NFS-e; V-074 a atualizou para 764 após paginar a carteira de Guias/DCTFWeb; V-075 a atualizou para 765 após paginar a carteira de Parcelamentos por lote autorizado; V-076 a atualizou para 766 após paginar a fila OFX × Domínio; V-077 a atualizou para 767 após paginar o histórico operacional de Parcelamentos; V-078 a atualizou para 768 após paginar a cobertura de certificados. V-072 comprovou por teste o contrato do runtime OpenAI-compatível privado e que uma resposta local impede egressão, mesmo com fallback configurado; sem opt-in, o fallback permanece negado e auditado. V-073 completou o detalhe de revisão NFS-e, a demonstração fictícia e a paginação da carteira sem corte silencioso. V-074 estendeu essa proteção à carteira de Guias/DCTFWeb, V-075 à carteira de Parcelamentos, cuja página de 30 registros coincide com seu limite de consulta em lote, V-076 à fila de Conciliação, V-077 ao histórico de operações e V-078 à cobertura de empresas sem A1 válido. As etapas 05–10 confirmaram controles locais próprios; na 10, V-040 acrescentou o contrato de requisição do cliente Asaas sem conexão ou chave. V-069–V-071 ampliaram a inspeção visual local da etapa 11 para home, cadastro, demonstração isolada, Triagem, revisão NFS-e, módulos operacionais e Copiloto fictícios, sem homologar jornada real. As homologações de caixas/antimalware/destino, ADN, Serpro, arquivos/ERPs/fontes do Radar e Asaas permanecem pendentes. Por D-87, toda dependência de site em produção fica concentrada na etapa 12; isso inclui SMTP/DNS, pareamento HTTPS/mTLS, rede, atualização distribuída, backup Domínio Web e escrita Windows definitiva. A demonstração NFS-e foi ajustada separadamente e não conclui a etapa 07. Evidências em [VALIDACOES.md](VALIDACOES.md).

**Atualização V-079:** a ficha da empresa passou a paginar seus históricos NFS-e, revisões e DTE em seções independentes, e a regressão integral local alcançou 769 testes aprovados. A evidência permanece exclusivamente sintética; não há homologação ADN ou Serpro.

**Atualização V-080:** a auditoria de conciliação passou a paginar seus eventos sem limite silencioso, mantendo a ação filtrada entre páginas; a regressão integral local alcançou 770 testes aprovados. A evidência permanece exclusivamente sintética; não há homologação de ERP, OFX ou exportação.

**Atualização V-081:** o Radar da Reforma passou a paginar alertas sem limite silencioso, mantendo termo, fonte e tema; a regressão integral local alcançou 771 testes aprovados. A evidência permanece exclusivamente sintética; não há homologação de fontes ou coleta.

**Atualização V-082:** o console da plataforma passou a paginar o histórico manual de faturas sem limite silencioso; a regressão integral local alcançou 772 testes aprovados. A evidência permanece exclusivamente sintética; não há homologação de cobrança ou Asaas.

**Atualização V-083:** a Caixa DTE passou a paginar seu histórico de resultados sem interferir na fila de mensagens; a regressão integral local alcançou 773 testes aprovados. A evidência permanece exclusivamente sintética; não há consulta, consumo ou homologação Serpro.

**Atualização V-084:** o onboarding passou a paginar seu histórico de importações sem ocultar lotes antigos e sem interferir na fonte ou prévia selecionadas; a regressão integral local alcançou 774 testes aprovados. A evidência permanece exclusivamente sintética; não há upload, backup ou homologação Domínio.

**Atualização V-085:** a Conciliação passou a paginar separadamente os históricos de processamentos e exportações, sem ocultar registros antigos; a regressão integral local alcançou 775 testes aprovados. A evidência permanece exclusivamente sintética; não há arquivo real, ERP ou homologação de exportação.

**Atualização V-086:** o Copiloto passou a paginar o histórico de conversas abertas sem ocultar as antigas, preservando a conversa selecionada; a regressão integral local alcançou 776 testes aprovados. A evidência permanece exclusivamente sintética; não há chamada de IA, curadoria ou homologação operacional.

**Atualização V-087:** o console da plataforma passou a paginar os fechamentos ainda adiados sem ocultar ocorrências antigas; a regressão integral local alcançou 777 testes aprovados. A evidência permanece exclusivamente sintética; não há fechamento, cobrança ou homologação Asaas.

**Atualização V-088:** o console da plataforma passou a paginar as tentativas Claude incertas sem ocultar protocolos antigos; a regressão integral local alcançou 778 testes aprovados. A evidência permanece exclusivamente sintética; não há chamada de IA, custo ou homologação operacional.

**Atualização V-089:** a revisão NFS-e passou a recusar acumulador ausente do catálogo da empresa; a regressão integral local alcançou 779 testes aprovados. A evidência permanece sintética; não há ADN ou homologação fiscal.

**Atualização V-090:** o detalhe de conciliação passou a paginar todos os candidatos no recorte já existente, sem ocultar os posteriores ao quinquagésimo; a regressão integral local alcançou 780 testes aprovados. A evidência permanece sintética; não há ERP, arquivo ou exportação homologados.

**Atualização V-091:** o detalhe da Triagem passou a paginar a trilha persistida de eventos sem ocultar evidência antiga; a regressão integral local alcançou 781 testes aprovados. A evidência permanece sintética; não há caixa, arquivo, agente ou destino homologados.

**Atualização V-092:** a carteira de movimentos da Conciliação passou a preservar as páginas de Processamentos e Exportações ao navegar, mantendo as três trilhas independentes; a regressão integral local manteve 781 testes aprovados. A evidência permanece sintética; não há arquivo, ERP ou exportação homologados.

**Atualização V-093:** a fila OFX × Domínio passou a preservar também o contexto das páginas de Processamentos, Movimentos e Exportações; a regressão integral local manteve 781 testes aprovados. A evidência permanece sintética; não há arquivo, ERP ou exportação homologados.

**Atualização V-094:** a Caixa DTE passou a preservar simultaneamente a página das mensagens e a página do histórico de consultas; a regressão integral local manteve 781 testes aprovados. A evidência permanece sintética; não há consulta Serpro, consumo ou homologação.

**Atualização V-095:** Jornadas foi removida do catálogo efetivo do produto conforme D-43, preservando apenas enum, schema e migrações históricos; a regressão integral local manteve 781 testes aprovados. A evidência é local; não há migração de produção ou homologação comercial.

**Atualização V-096:** formulários, views e template operacionais órfãos de Jornadas foram removidos conforme D-43, preservando enum, modelos, tabelas e migrações históricas; a regressão integral local manteve 781 testes aprovados. A evidência é local; não há migração de produção ou homologação comercial.

**Atualização V-097:** a Conciliação passou a rejeitar XLSX corrompido antes de persistir uma fonte, sem transformar falha de leitura em processamento incompleto; a prévia CSV também deixou de materializar todo o arquivo para exibir 50 linhas. A regressão integral local alcançou 783 testes aprovados; a evidência é local, sem arquivo, ERP ou OCR homologados.

## 1. Objetivo e ponto de partida

Concluir todos os módulos atuais, integrar Domínio e Siescon, entregar o instalador do escritório e operar inicialmente com IA por API, deixando o fluxo de IA local preparado e testado.

**Pronto para venda:** o escritório consegue configurar, executar, conferir o resultado e recuperar falhas; permissões, cobrança, documentação e suporte correspondem ao comportamento real.

As evidências são sempre datadas: V-041 registra a revalidação local de 21/09/2026 (lint, Django, migrações, testes e comparação com GitHub); as provas anteriores de PostgreSQL, Redis, Windows e builds seguem registradas com seus limites. Nenhuma delas homologa integração externa, treinamento em GPU ou instalação no cliente. A análise consolidada mais recente está em [docs/planejamento/analise-projeto-2026-09-21.md](docs/planejamento/analise-projeto-2026-09-21.md).

## 2. Memória única

- [DECISOES.md](DECISOES.md): decisões confirmadas e registros históricos, preservando seu grau de confirmação.
- [VALIDACOES.md](VALIDACOES.md): verificações efetivamente executadas, resultados, limites e estado desta entrega.
- [Etapas e prompts](docs/planejamento/etapas/README.md): execução detalhada das etapas 00–13.
- [Inventário de código, rotas, tarefas e APIs](docs/planejamento/inventario-conclusao.md): mapa estático, não prova de funcionamento.
- [Matriz de evidências de conclusão](docs/planejamento/matriz-evidencias-2026-09-19.md): nível máximo provado, evidências e bloqueios de cada etapa.
- [Limitações comerciais Domínio Web](docs/dominio-web-limitacoes-comerciais.md): linguagem de venda, capacidades verificadas e limites da API/backup.
- [Dúvidas abertas](docs/planejamento/duvidas-abertas.md): registro único de perguntas, com etapa e dono.
- [Estado operacional](docs/planejamento/estado-operacional.md) e [histórico de execução](docs/planejamento/registro-de-execucao.md): evidências anteriores, com data e ressalvas.

Os caminhos antigos de plano e decisões são ponteiros, não planos concorrentes. Documentos históricos não viram especificação por serem mais antigos ou mais extensos. Decisões confirmadas só voltam a ser perguntadas diante de conflito concreto ou mudança solicitada, indicando o ID e o motivo.

Cada item distingue: **implementado → testado localmente → homologado no ambiente real → liberado para venda**. Um bloqueio documentado não transforma uma etapa incompleta em concluída.

Por D-87, as etapas 01–11 encerram o respectivo escopo de implementação e validação local. A etapa 12 reúne toda execução que exija site publicado, ambiente hospedado, credencial externa de produção, chamada real, piloto ou homologação comercial. Essa organização não antecipa deploy nem autoriza custos.

### Decisões encerradas nesta conversa

| Assunto | Decisão | Registro |
|---|---|---|
| Arquitetura | SaaS e IA centralizados na Mewstack; agente instalado no escritório. | D-46 |
| IA inicial | Uso por API KEY agora; preservar Claude conforme D-16. | D-47 |
| IA local | Consulta aos dados + ajuste do modelo com exemplos revisados. | D-48 |
| Isolamento do aprendizado | Conhecimento, exemplos, correções e ajustes derivados dos clientes ficam restritos ao respectivo escritório; conhecimento geral pode ser compartilhado. | D-49 |
| API após migração | IA local como padrão após homologação; API como reserva autorizada, sujeita à política de dados e orçamento. | D-50 |
| Aceite local para venda inicial | Pipeline local preparado e testado; treinamento e desempenho na máquina definitiva ficam para etapa posterior explícita. | D-51 |
| Áreas do Domínio | Contábil, fiscal e folha na preparação da IA. | D-52 |
| Disponibilidade Siescon | Responsável confirmou servidor/banco disponível para viabilizar descoberta autorizada. | D-53 |
| Operações Siescon | Leitura + exportação revisada; gravação direta não aprovada. | D-54 |
| Autonomia | Automação por regras aprovadas e qualidade medida; exceções seguem para revisão. | D-55 |
| Sem presunções | “nunca assume nada, o que for preciso tu me pergunta aqui”. | D-56 |
| Memória e execução | Documentar tudo que for decidido; criar etapas para terminar o projeto e um prompt por etapa. | D-57 |
| Plano aprovado | Plano de conclusão composto pelas etapas 00–13, com dependências e aceites registrados em PLANO-MESTRE.md. | D-58 |
| Localização da memória | Plano mestre e tudo que for validado devem ficar na raiz do repositório. | D-59 |
| Escopo desta execução | “quero que tu faça apenas a primeira etapa agora”. | D-60 |

Preservar também as decisões anteriormente confirmadas: marca CICA; credenciais Serpro centrais; Asaas e cobrança manual separados; tokens por módulo; Triagem por e-mail; Triagem substitui Jornadas. Valores propostos, regras apenas registradas e homologações pendentes não foram aprovados por este plano.

## 3. Etapas, dependências e prompts

Os números identificam etapas; a ordem de execução deve respeitar dependências. A etapa 10 fornece controles necessários à 08. A 13 fica após a disponibilidade do equipamento e não bloqueia a venda inicial por API.

### Etapa 00 — Consolidar decisões, inventário e pendências

**Depende de:** Nenhuma.

**Entregas**

- Gravar integralmente o plano e as decisões confirmadas.
- Inventariar módulos, rotas, tarefas, APIs, serviços Windows e integrações.
- Confrontar documentação antiga com o código e decisões posteriores.
- Registrar cada pendência uma única vez, com etapa afetada e responsável pela resposta.
- Preservar o trabalho local existente; não descartar nem sobrescrever alterações.
- Agrupar as perguntas restantes por condições comerciais, regras documentais, dados autorizados para IA, ambientes de homologação e metas operacionais; perguntar somente o ainda não decidido.

**Pendências / limites:** Nenhum bloqueio para documentar; as decisões abertas não impedem esta etapa.

**Aceite:** Outra pessoa consegue identificar o próximo trabalho, suas decisões e seus bloqueios sem reconstruir conversas antigas.

**Prompt**

> Execute a etapa 00 do plano mestre da CICA. Materialize os documentos e prompts deste plano, consolide as decisões já confirmadas e elimine contradições documentais sem apagar o histórico. Confira o código atual. Não pergunte novamente decisões registradas; apresente somente lacunas ou conflitos concretos.

[Checklist, testes e continuidade da etapa 00](docs/planejamento/etapas/00-documentacao.md).

### Etapa 01 — Estabilizar a base técnica

**Depende de:** 00.

**Entregas**

- Resolver as 66 violações atuais do Ruff e demais falhas verificadas.
- Consolidar migrações e revisar compatibilidade com dados existentes.
- Executar testes com PostgreSQL, Redis e workers reais em ambiente isolado.
- Verificar concorrência em consumo, faturamento, filas e publicação de modelos.
- Validar builds da aplicação, runtime multimodal, treinamento e agente.
- Revisar dependências, configuração de produção e tratamento de segredos.

**Pendências / limites:** Q-28 e Q-30 para ambientes e aceite; disponibilidades técnicas devem ser inspecionadas, sem instalar ou contratar infraestrutura por inferência.

**Aceite:** CI aprovado e instalação reproduzível; testes com SQLite não substituem testes concorrentes em PostgreSQL.

**Prompt**

> Execute a etapa 01. Estabilize o estado atual preservando alterações existentes, faça o CI passar e valide banco, filas, migrações e builds em ambiente isolado. Registre resultados e limitações reais; não considere testes simulados prova de produção.

[Checklist, testes e continuidade da etapa 01](docs/planejamento/etapas/01-base-tecnica.md).

### Etapa 02 — Fechar cadastro, acesso e administração

**Depende de:** 01.

**Entregas**

- Completar cadastro, confirmação de e-mail, recuperação, convites, MFA e fim do teste.
- Conferir permissões por escritório, empresa, módulo e operação.
- Validar empresas, certificados, equipe e primeiros passos.
- Completar o console Mewstack para suporte, contratos, integrações e falhas.
- Garantir que demonstrações não acessem dados ou serviços reais.
- Homologar e-mail transacional e seus estados de falha.

**Pendências / limites:** Q-01 a Q-06 e Q-29: não inventar regras de acesso comercial nem SMTP.

**Aceite:** Proprietário, administrador, operador, financeiro, auditor e suporte só realizam ações autorizadas, inclusive por acesso direto às APIs.

**Prompt**

> Execute a etapa 02. Complete o ciclo de entrada e administração da CICA, incluindo permissões, MFA, empresas, certificados e suporte. Valide as jornadas por perfil e o isolamento entre escritórios. Consulte decisões existentes antes de perguntar regras comerciais ou de acesso.

[Checklist, testes e continuidade da etapa 02](docs/planejamento/etapas/02-acesso-administracao.md).

### Etapa 03 — Concluir agente Windows e integração Domínio

**Depende de:** 01–02.

**Entregas**

- Resolver a divisão atual: o agente Python sincroniza Domínio local; o nativo processa backups e arquivamento.
- Entregar um fluxo de instalação que identifique claramente os componentes necessários.
- Homologar DSNs e drivers nas arquiteturas suportadas.
- Completar pareamento, atualização, revogação, reinício, diagnóstico e recuperação de rede.
- Validar Domínio local e importação manual de backup Domínio Web.
- Substituir limites que truncam dados por leitura paginada/incremental verificável.
- Mapear os dados necessários de contabilidade, fiscal e folha, com leitura autorizada e rastreabilidade.
- Homologar escrita documental nas pastas Windows permitidas.

**Pendências / limites:** Q-22, Q-28, Q-31 e Q-32. Registrar a arquitetura definitiva antes de unificar Python e serviço nativo.

**Aceite:** Instalar em máquina limpa, sincronizar, interromper a rede, reiniciar e retomar sem perder ou duplicar dados.

**Prompt**

> Execute a etapa 03. Complete localmente o serviço instalável e o conector Domínio local/Web. Registre a arquitetura definitiva antes de alterá-la. Prepare instalação, leitura, recuperação, atualização e pastas Windows sem SQL arbitrário nem escrita no banco Domínio; a homologação contra o site publicado e o piloto real pertencem à etapa 12.

[Checklist, testes e continuidade da etapa 03](docs/planejamento/etapas/03-agente-dominio.md).

### Etapa 04 — Implementar e homologar Siescon

**Depende de:** 02–03.

**Entregas**

- Identificar versão, banco, mecanismo permitido de acesso e ambiente disponibilizado.
- Obter schema e arquivos de referência por acesso autorizado.
- Implementar leitura, sincronização e diagnóstico.
- Mapear empresas, contas, lançamentos e demais dados necessários aos fluxos contratados.
- Preparar exportação revisada no layout efetivamente suportado.
- Generalizar vínculos hoje dependentes exclusivamente do código Domínio.
- Registrar matriz de capacidades: o que funciona com Domínio, Siescon ou ambos.

**Pendências / limites:** Q-28 e Q-33. Banco disponível foi confirmado; versão, meio de acesso e layout não foram fornecidos.

**Aceite:** Dados sincronizados conferem com o Siescon; arquivo exportado é importado e conferido no ambiente de homologação. Gerar arquivo não basta.

**Prompt**

> Execute a etapa 04 usando o servidor/banco Siescon disponibilizado pelo responsável. Descubra e documente o contrato técnico antes de programar o adaptador. Entregue leitura e exportação revisada, valide identificação das empresas e homologue a importação. Não invente endpoints, layouts ou permissões.

[Checklist, testes e continuidade da etapa 04](docs/planejamento/etapas/04-siescon.md).

### Etapa 05 — Concluir IA por API e preparação da IA local

**Depende de:** 02–03; incorporar Siescon após 04.

**Entregas**

- Completar Copiloto e análise documental por API com limites, custos e falhas recuperáveis.
- Ampliar a consulta de conhecimento: a busca atual por palavras não comprova cobertura das três áreas solicitadas.
- Estruturar dados e fontes por escritório, empresa, período e área.
- Separar dados operacionais atualizados dos exemplos usados para ajuste do modelo.
- Completar seleção de exemplos, revisão, anonimização, versionamento e exportação QLoRA.
- Separar conjuntos de treino e avaliação para evitar avaliação contaminada.
- Vincular avaliação ao artefato exato do modelo/adaptador, corpus e versão.
- Preparar publicação, seleção do adaptador por escritório e retorno à versão anterior.
- [x] Testar o contrato do runtime local e impedir fallback externo sem autorização (V-072).

**Pendências / limites:** Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no código não são aprovação comercial.

**Aceite:** Respostas com fontes verificáveis; isolamento entre escritórios; pipeline reproduzível; etapas que exigem a GPU definitiva explicitamente identificadas.

**Prompt**

> Execute a etapa 05. Complete a IA por API e o pipeline local para contábil, fiscal e folha, mantendo dados e ajustes isolados por escritório. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliação, artefato e inferência. Não declare treinamento real ou desempenho local sem execução comprovada.

[Checklist, testes e continuidade da etapa 05](docs/planejamento/etapas/05-ia-api-pipeline-local.md).

### Etapa 06 — Concluir Triagem de Arquivos

**Depende de:** 03 e 05.

**Estado local:** V-038 revalidou quarentena, leitura incremental simulada,
scan/formato, revisão, cópia íntegra e protocolo de agente Windows. Isso não
homologa OAuth, caixa, antimalware, catálogo, retenção ou destino Windows real.

**Entregas**

- Homologar Microsoft 365, Google Workspace, Gmail pessoal e IMAP conforme decisões registradas.
- Completar leitura incremental, quarentena, antimalware, extração e classificação.
- Permitir visualizar documentos liberados, corrigir empresa, tipo, competência e destino.
- Aplicar automação somente às regras aprovadas e medidas.
- Completar biblioteca interna e arquivamento Windows com confirmação de integridade.
- Atualizar checklist somente após arquivamento confirmado.
- Resolver duplicatas, colisões, múltiplos documentos e indisponibilidade do agente.

**Pendências / limites:** Q-12 a Q-25 e Q-31: catálogo, nomenclatura, retenção, formatos, limites e checklist ainda precisam de decisões específicas.

**Aceite:** E-mail → anexo seguro → classificação/revisão → arquivo localizado no destino → checklist atualizado, com recuperação de falhas.

**Prompt**

> Execute a etapa 06. Complete a Triagem exclusivamente pelas entradas de e-mail aprovadas e pelos dois destinos definidos. Consulte o registro antes de perguntar taxonomia ou nomenclatura. Homologue todo o caminho até o arquivo final, incluindo correção humana, duplicatas, quarentena e agente indisponível.

[Checklist, testes e continuidade da etapa 06](docs/planejamento/etapas/06-triagem.md).

### Etapa 07 — Concluir NFS-e, certificados e revisão fiscal

**Depende de:** 03 e 05.

**Entregas**

- Homologar coleta ADN, certificados, NSU, retomada e deduplicação.
- Apresentar nota legível, valores, participantes, competência e descrição dos serviços.
- Validar acumuladores contra o catálogo da empresa.
- Exibir evidência da sugestão e permitir correção.
- Garantir acesso a toda a carteira, sem cortes silenciosos nas filas.
- Documentar cobertura e limitações efetivas da fonte de coleta.

**Pendências / limites:** Q-28 e Q-30: certificado/ambiente autorizado, corpus e métricas de aceite.

**Aceite:** Nota real autorizada é coletada, conferida, classificada e rastreada sem duplicação ou associação à empresa errada.

**Prompt**

> Execute a etapa 07. Complete e homologue NFS-e e revisão fiscal, da validade do certificado à decisão do contador. Valide o catálogo de acumuladores e a continuidade da coleta. Não confunda dados calculados, documento fiscal oficial e sugestão da IA.

[Checklist, testes e continuidade da etapa 07](docs/planejamento/etapas/07-nfse.md).

### Etapa 08 — Concluir Central Integra Contador

**Depende de:** 02 e controles de consumo da 10.

**Entregas**

- DTE: consulta, paginação, teor, autorização específica de ciência e recuperação de retorno incerto.
- DCTFWeb: declaração, recibo e guia; preservar o escopo registrado sem transmissão.
- Parcelamentos: concluir PARCSN e consultar o responsável antes de ampliar modalidades.
- Homologar credenciais centrais, certificados, representação e serviços.
- Validar estimativa, autorização, reserva, liquidação e persistência de documentos.
- Impedir repetição automática de operações com resultado incerto.

**Pendências / limites:** Q-05, Q-28, Q-30 e Q-36; chamadas cobradas exigem autorização específica.

**Aceite:** Cada operação prometida completa a jornada real, com documentos, protocolo, consumo e falhas rastreáveis.

**Prompt**

> Execute a etapa 08. Homologue DTE, DCTFWeb e Parcelamentos com credenciais centrais Mewstack e escopo já aprovado. Preserve autorização de ciência e controles de consumo. Antes de qualquer chamada cobrada, solicite aprovação específica de custo; não repita chamadas de resultado incerto.

[Checklist, testes e continuidade da etapa 08](docs/planejamento/etapas/08-integra-contador.md).

### Etapa 09 — Concluir Conciliação e Radar

**Depende de:** 03–05; exportação Siescon depende de 04.

**Estado local:** V-037 revalidou ingestão limitada, mapeamento/revisão,
conciliação com evidência, retomada, exportação auditável e coleta Radar
simulada. Isso não homologa OCR, layout, volume, fontes oficiais ou importação
em Domínio/Siescon.

**Entregas**

- Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidências.
- Permitir corrigir mapeamento, classificar, revisar, conciliar e tratar ausência de correspondência.
- Validar contas, direção, competência, saldos e lançamentos equilibrados.
- Homologar exportações Domínio e Siescon sem apresentar exportação como importação concluída.
- Validar volume com PostgreSQL e corpus representativo.
- No Radar, comprovar coleta, atualização, origem e falhas, preservando a proposta de acompanhamento de publicações.

**Pendências / limites:** Q-28; layouts reais e amostra independente. Aplicar as
métricas já decididas em D-73 antes de qualquer aceite.

**Aceite:** Processamento auditável, nenhuma conciliação sem evidência independente e exportações conferidas nos sistemas de destino.

**Prompt**

> Execute a etapa 09. Complete conciliação, lançamentos revisados e exportações homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete também a operação do Radar, sem ampliar sua promessa para cálculo tributário individual não decidido.

[Checklist, testes e continuidade da etapa 09](docs/planejamento/etapas/09-conciliacao-radar.md).

### Etapa 10 — Concluir contratação, tokens e cobrança

**Depende de:** 02; pode avançar antes das homologações fiscais.

**Entregas**

- Fechar com o responsável preços, franquias, pesos, tetos, carência e regras de mudança de contrato.
- Concluir a orquestração Asaas entre dados comerciais autorizados, cliente, cobrança e `PaymentAttempt`; V-040 já cobre somente o contrato local do cliente.
- Homologar Pix, boleto, cartão, atrasos, estornos e eventos fora de ordem.
- Garantir fatura única, consumo auditável e proteção contra duplicidade.
- Separar integralmente contratos manuais da automação Asaas.
- Implementar somente leitura e reativação conforme regras expressamente aprovadas.

**Pendências / limites:** Q-01 a Q-06 e Q-08; sandbox/contrato em Q-28.

**Aceite:** Contrato, acesso, consumo e fatura concordam, inclusive em concorrência e falhas.

**Prompt**

> Execute a etapa 10. Use o modelo comercial confirmado e pergunte apenas valores e regras ainda pendentes. Complete e homologue Asaas e cobrança manual, com tokens inteiros, franquias por módulo e teto aceito. Não publique preços nem crie cobranças reais sem aprovação correspondente.

[Checklist, testes e continuidade da etapa 10](docs/planejamento/etapas/10-contratacao-cobranca.md).

### Etapa 11 — Validar todas as jornadas e interfaces

**Depende de:** Módulos implementados.

**Estado local:** V-039 verificou parcialmente 14 caminhos e uma jornada
fictícia de Triagem em servidor isolado. A auditoria completa de perfis, estados
e oferta segue pendente.

**Entregas**

- Revisar site comercial, cadastro, aplicação do escritório, central de aprendizado e console Mewstack.
- Corrigir ações sem saída, tabelas incompletas, estados confusos e ausência de evidência.
- Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- Aplicar ui-ux-pro-max, Watermelon, referências reais de produto e web-design-guidelines.
- Inspecionar as jornadas com Playwright MCP; registrar exatamente os estados alcançados e fechar as sessões.
- Conferir que oferta comercial e demonstração refletem capacidades homologadas.

**Pendências / limites:** Aplicar D-73; estados inacessíveis devem ser
registrados, nunca presumidos validados.

**Aceite:** O usuário conclui tarefas representativas sem intervenção interna não prevista.

**Prompt**

> Execute a etapa 11 em todas as áreas da CICA, preservando o design existente. Siga integralmente o fluxo de UI do AGENTS.md, registre referências e valide tarefas completas com Playwright em desktop e celular. Corrija bloqueios funcionais e de acessibilidade e feche as sessões abertas.

[Checklist, testes e continuidade da etapa 11](docs/planejamento/etapas/11-jornadas-interfaces.md).

### Etapa 12 — Homologação integrada e liberação comercial

**Depende de:** 01–11.

**Entregas**

- Identificar ambiente de produção e capacidade necessária, sem presumir provedor ou contratar recursos.
- Validar deploy, migrações, workers, agendador, storage e conectividade dos agentes.
- Executar restauração de banco e documentos, recuperação de falhas e retorno de versão.
- Homologar retenção, exportação, exclusão, termos e contatos de suporte.
- Executar piloto por módulo, com critérios e amostra aprovados.
- Entregar manuais de instalação, operação e suporte, matriz de compatibilidade e limitações.
- Produzir relatório final de liberação por módulo.

**Pendências / limites:** Q-24, Q-28 a Q-30 e Q-35. Recursos pagos exigem aprovação específica.

**Aceite:** Todos os módulos da oferta possuem evidência de funcionamento e operação sustentável; nenhuma pendência crítica é escondida como concluída.

**Prompt**

> Execute a etapa 12. Faça a homologação integrada da CICA e reúna evidências por módulo, incluindo restauração, filas, integrações, instalação e suporte. Confirme com o responsável ambiente, metas e critérios ainda pendentes. Não libere venda nem contrate infraestrutura por inferência.

[Checklist, testes e continuidade da etapa 12](docs/planejamento/etapas/12-homologacao-venda.md).

### Etapa 13 — Ativar IA local na máquina definitiva

**Depende de:** 05 e disponibilidade do equipamento; não bloqueia a venda inicial por API.

**Entregas**

- Inspecionar hardware e selecionar modelo compatível mediante decisão registrada.
- Executar treinamento real e avaliação independente por escritório.
- Medir qualidade, latência, concorrência e consumo de recursos.
- Homologar isolamento de adaptadores e operação sem API.
- Migrar o padrão para local somente após aprovação dos resultados.
- Manter API como reserva autorizada e permitir retorno à versão anterior.

**Pendências / limites:** Q-30, Q-34 e Q-35. Hardware/modelo e resultados ainda não homologados.

**Aceite:** Treino real, qualidade e capacidade comprovados na máquina definitiva; mudança de rota aprovada e retorno de versão demonstrado.

**Prompt**

> Execute a etapa 13 quando a máquina definitiva estiver disponível. Consulte as decisões de IA já registradas, valide hardware e modelo, execute treinamento e avaliação reais e apresente as evidências para a mudança de rota. Preserve isolamento por escritório e fallback externo somente autorizado.

[Checklist, testes e continuidade da etapa 13](docs/planejamento/etapas/13-ia-local-definitiva.md).

## 4. Regras de conclusão e continuidade

Todo prompt de etapa deve ser executado com as instruções comuns abaixo:

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.

Cada entrega deve registrar critérios atendidos e bloqueios, testes proporcionais ao risco, documentação atualizada, ações do responsável e o próximo prompt. Uma etapa só é concluída quando o aceite foi atendido; caso contrário permanece parcial ou bloqueada, com motivo. A mera documentação do bloqueio não constitui conclusão funcional.

**Nenhum prazo, preço, regra comercial, arquitetura pendente ou autorização de dados será inventado para preencher o plano.** As pendências têm dono e impedem apenas o trabalho dependente. A autorização de execução de uma etapa não autoriza custo, publicação, homologação presumida ou execução da próxima etapa quando o responsável limitou o escopo.

## 5. Próximo trabalho

[04 — implementar e homologar Siescon](docs/planejamento/etapas/04-siescon.md) é a próxima etapa habilitada. A preparação estrutural local e a análise estão registradas em V-029 a V-031 e V-041; o contrato técnico Q-33 continua indispensável para escrever o adaptador, pois não se pode inventar versão, mecanismo de acesso, schema, identificador de empresa ou layout. As frentes locais independentes de IA, Triagem, NFS-e, Central Integra Contador, Conciliação/Radar e cobrança também avançaram e foram evidenciadas em V-032 a V-035, V-037–V-040, sem antecipar integrações externas. A [análise de 21/09](docs/planejamento/analise-projeto-2026-09-21.md) lista o material mínimo a receber por canal seguro. Sem esse material, a etapa permanece bloqueada, não concluída.
