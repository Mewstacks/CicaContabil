# CICA — plano mestre de conclusão e preparação para venda

Atualizado em 17/09/2026. Plano aprovado pelo responsável nesta conversa; localização na raiz conforme D-59.

**Execução autorizada agora: somente etapa 00 — documentação e consolidação.** As etapas 01–13 não foram iniciadas por esta entrega. O estado final da etapa 00 está em [VALIDACOES.md](VALIDACOES.md).

## 1. Objetivo e ponto de partida

Concluir todos os módulos atuais, integrar Domínio e Siescon, entregar o instalador do escritório e operar inicialmente com IA por API, deixando o fluxo de IA local preparado e testado.

**Pronto para venda:** o escritório consegue configurar, executar, conferir o resultado e recuperar falhas; permissões, cobrança, documentação e suporte correspondem ao comportamento real.

Verificações da análise de 17/09/2026, anteriores à edição documental: 740 testes aprovados, 1 ignorado e 8 subtestes aprovados; Django check sem problemas; nenhuma migração faltante no dry-run; 66 violações Ruff. Há alterações locais anteriores não consolidadas. Estes resultados não homologam integrações externas, treinamento em GPU ou instalação no cliente. Evidências e limites em [VALIDACOES.md](VALIDACOES.md).

## 2. Memória única

- [DECISOES.md](DECISOES.md): decisões confirmadas e registros históricos, preservando seu grau de confirmação.
- [VALIDACOES.md](VALIDACOES.md): verificações efetivamente executadas, resultados, limites e estado desta entrega.
- [Etapas e prompts](docs/planejamento/etapas/README.md): execução detalhada das etapas 00–13.
- [Inventário de código, rotas, tarefas e APIs](docs/planejamento/inventario-conclusao.md): mapa estático, não prova de funcionamento.
- [Dúvidas abertas](docs/planejamento/duvidas-abertas.md): registro único de perguntas, com etapa e dono.
- [Estado operacional](docs/planejamento/estado-operacional.md) e [histórico de execução](docs/planejamento/registro-de-execucao.md): evidências anteriores, com data e ressalvas.

Os caminhos antigos de plano e decisões são ponteiros, não planos concorrentes. Documentos históricos não viram especificação por serem mais antigos ou mais extensos. Decisões confirmadas só voltam a ser perguntadas diante de conflito concreto ou mudança solicitada, indicando o ID e o motivo.

Cada item distingue: **implementado → testado localmente → homologado no ambiente real → liberado para venda**. Um bloqueio documentado não transforma uma etapa incompleta em concluída.

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

> Execute a etapa 03. Complete o serviço instalável e o conector Domínio local/Web. Apresente a decisão técnica pendente sobre Python e serviço nativo com evidências antes de alterar essa arquitetura. Homologue instalação, leitura, recuperação, atualização e pastas Windows, sem SQL arbitrário nem escrita no banco Domínio.

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
- Testar o contrato do runtime local e impedir fallback externo sem autorização.

**Pendências / limites:** Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no código não são aprovação comercial.

**Aceite:** Respostas com fontes verificáveis; isolamento entre escritórios; pipeline reproduzível; etapas que exigem a GPU definitiva explicitamente identificadas.

**Prompt**

> Execute a etapa 05. Complete a IA por API e o pipeline local para contábil, fiscal e folha, mantendo dados e ajustes isolados por escritório. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliação, artefato e inferência. Não declare treinamento real ou desempenho local sem execução comprovada.

[Checklist, testes e continuidade da etapa 05](docs/planejamento/etapas/05-ia-api-pipeline-local.md).

### Etapa 06 — Concluir Triagem de Arquivos

**Depende de:** 03 e 05.

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

**Entregas**

- Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidências.
- Permitir corrigir mapeamento, classificar, revisar, conciliar e tratar ausência de correspondência.
- Validar contas, direção, competência, saldos e lançamentos equilibrados.
- Homologar exportações Domínio e Siescon sem apresentar exportação como importação concluída.
- Validar volume com PostgreSQL e corpus representativo.
- No Radar, comprovar coleta, atualização, origem e falhas, preservando a proposta de acompanhamento de publicações.

**Pendências / limites:** Q-28 e Q-30; layouts reais e amostra independente.

**Aceite:** Processamento auditável, nenhuma conciliação sem evidência independente e exportações conferidas nos sistemas de destino.

**Prompt**

> Execute a etapa 09. Complete conciliação, lançamentos revisados e exportações homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete também a operação do Radar, sem ampliar sua promessa para cálculo tributário individual não decidido.

[Checklist, testes e continuidade da etapa 09](docs/planejamento/etapas/09-conciliacao-radar.md).

### Etapa 10 — Concluir contratação, tokens e cobrança

**Depende de:** 02; pode avançar antes das homologações fiscais.

**Entregas**

- Fechar com o responsável preços, franquias, pesos, tetos, carência e regras de mudança de contrato.
- Concluir cliente Asaas; o webhook existente não cobre criação e operação integral da cobrança.
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

**Entregas**

- Revisar site comercial, cadastro, aplicação do escritório, central de aprendizado e console Mewstack.
- Corrigir ações sem saída, tabelas incompletas, estados confusos e ausência de evidência.
- Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- Aplicar ui-ux-pro-max, Watermelon, referências reais de produto e web-design-guidelines.
- Inspecionar as jornadas com Playwright MCP; registrar exatamente os estados alcançados e fechar as sessões.
- Conferir que oferta comercial e demonstração refletem capacidades homologadas.

**Pendências / limites:** Q-30; estados inacessíveis devem ser registrados, nunca presumidos validados.

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

Somente após nova solicitação, executar [01 — estabilizar a base técnica](docs/planejamento/etapas/01-base-tecnica.md). Nesta entrega, limitar alterações a documentação e instruções de continuidade. As 66 violações Ruff permanecem como achado, sem correção nesta etapa.
