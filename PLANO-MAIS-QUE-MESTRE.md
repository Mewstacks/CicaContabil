
# CICA — plano completo de evolução do produto

## 1. Visão do produto e avaliação da ideia

O CICA será a **central de operação do escritório contábil**: reúne empresas, pessoas, documentos, obrigações, fechamentos, conferências e análises financeiras, mostrando o que precisa ser feito, por quem, até quando e com qual comprovação.

O produto funcionará em três modalidades:

- **Com Domínio conectado:** aproveita os dados disponíveis nas integrações homologadas.
- **Com Siescon conectado:** utiliza um adaptador próprio, respeitando as capacidades efetivamente verificadas.
- **Sem ERP conectado:** opera com cadastros, atividades, documentos, lançamentos gerenciais e importações no próprio CICA.

A arquitetura permitirá adicionar outros ERPs futuramente. Não haverá dependência operacional de bancos, adquirentes, agregadores financeiros ou outros ERPs nesta evolução. Permanecem os serviços já escolhidos: Serpro, IA por API, e-mail e Asaas para cobrança do CICA.

**Minha avaliação:** a ideia tem potencial comercial forte, sobretudo ao combinar gestão operacional com comprovação e análise. Entretanto, painéis, listas de tarefas e chat com IA já são comuns. A diferenciação precisa aparecer em resultados concretos:

1. Identificar pendências reais, incluindo divergências entre sistemas.
2. Explicar a origem de cada pendência.
3. Permitir resolvê-la no mesmo contexto.
4. Confirmar o resultado com evidência.
5. Transformar os dados do escritório em entregas úteis ao cliente.

Exemplo da experiência desejada:

> “A folha da empresa foi processada, mas há divergência entre o valor apurado e a obrigação consultada. Veja a diferença, os registros envolvidos, a última atualização e a atividade responsável pela regularização.”

A promessa comercial será baseada nessas capacidades demonstráveis. “Disruptivo” será um objetivo de produto, medido pela redução de trabalho e pela qualidade das entregas.

## 2. Decisões consolidadas

| Tema | Regra do novo CICA |
|---|---|
| Venda | Suíte completa, com pacotes de capacidade. |
| Capacidade | Usuários internos ativos e empresas ativas por **raiz de CNPJ**. |
| Matriz e filiais | Compartilham a unidade comercial, mas permanecem separadas nas operações e evidências. |
| Funcionário | Acesso operacional completo às empresas atribuídas, inclusive transmissões e ciência oficial, mediante confirmação humana. |
| Administrador | Visão total do escritório; gestão de pessoas, atribuições, configuração, contratação e limites financeiros. |
| Auditoria | Registrar ações, aprovações, resultados, falhas, alterações e atividades esperadas que venceram sem conclusão. |
| Fechamento | Processamento/fechamento comprovado e obrigações aplicáveis aceitas. Revisão interna final não é obrigatória. |
| Pagamento de guias | Atividade separada do fechamento. |
| Sem ERP | Evidência documental e confirmação humana, identificadas como tais. |
| Prazos | Modelos aprovados pelo administrador, com exceções por empresa e área. |
| Relatórios | Modelos configuráveis; exportação livre para usuários autorizados, com indicação de pendências e atualização. |
| Entrega ao cliente | Relatórios e arquivos; sem portal do cliente neste escopo. |
| Integra Contador | Repasse do custo efetivo, sem margem, com descontos e ajustes distribuídos de forma auditável. |
| IA | Franquia em reais de uso CICA, adicional pela tabela comercial e teto mensal autorizado pelo administrador. |
| Dados enviados à IA | Minimização e mascaramento por padrão; conteúdo identificável depende de política específica e base contratual validada. |
| E-mail | Evoluir para aplicativos centrais da Mewstack com consentimento do escritório; aplicativo próprio permanece como alternativa. |
| Relatórios e gráficos | Bibliotecas JavaScript. |
| Conexões financeiras externas | Fora do plano. Caixa alimentado por CICA, arquivos e dados disponíveis nos ERPs autorizados. |

As regras anteriores de cobrança que não conflitam permanecem: Asaas e contratos manuais separados, teste de 14 dias, fechamento mensal no dia 1, vencimento no dia 10, proporcionalidade inicial e tratamento de inadimplência já definido.

Os preços e as quantidades de cada pacote serão configuráveis e aprovados antes da venda. Este plano não inventa valores comerciais.

## 3. Experiência funcional

### 3.1. Tela inicial do funcionário

A tela inicial será a área de trabalho diária, organizada por prioridade e prazo.

Deverá apresentar:

- Atividades vencidas, de hoje e próximas.
- Fechamentos das próprias empresas, separados em contábil, fiscal e folha.
- Pendências aguardando documento, processamento, transmissão ou retorno.
- Divergências que precisam de análise.
- Operações preparadas que aguardam confirmação.
- Problemas de integração que impedem verificar uma situação.
- Calendário pessoal e filtros por empresa, área, competência e situação.

Cada atividade terá contexto suficiente para agir:

**Empresa → competência → obrigação ou processo → situação → evidência → próxima ação.**

O funcionário poderá abrir os documentos, consultar a origem da divergência, executar uma operação permitida, registrar impedimento e acompanhar o resultado sem procurar a mesma empresa em várias telas.

A prioridade inicial será determinística: vencimento, bloqueio de dependências e relevância definida no modelo. A IA poderá explicar e sugerir, mas não esconder atividades nem decidir sozinha o que deixou de ser obrigatório.

### 3.2. Visão do administrador

A administração terá duas perspectivas:

| Perspectiva | Conteúdo |
|---|---|
| Operação | Fechamentos, atrasos, empresas sem responsável, pendências, dependências e redistribuição de atividades. |
| Gestão | Capacidade da equipe, volume por carteira, retrabalho, tempo de resolução, consumo, integração e qualidade dos dados. |

O administrador poderá investigar um indicador até chegar à atividade e à evidência correspondente.

A avaliação de funcionários usará fatos contextualizados: atribuição, prazo, alteração de responsabilidade, impedimento e disponibilidade das fontes. Contagem de cliques ou quantidade bruta de tarefas não será tratada como medida suficiente de produtividade.

A visão total do administrador se limita ao seu escritório. Administração técnica da Mewstack será separada, com acessos excepcionais identificados e auditados.

### 3.3. Ficha única da empresa

Cada empresa terá uma ficha operacional contendo:

- Cadastro, raiz de CNPJ e estabelecimentos.
- Responsáveis e atribuições por área.
- Fontes conectadas e última sincronização.
- Competências e fechamentos.
- Obrigações e respectivos comprovantes.
- Documentos e pendências.
- Situação fiscal, guias e parcelamentos.
- Conferências de folha.
- DRE, indicadores e caixa gerencial.
- Histórico completo de atividades e operações.

O acesso à empresa será concedido explicitamente. A cobrança por raiz de CNPJ não concederá automaticamente acesso a todas as filiais.

### 3.4. Configuração inicial simplificada

O assistente seguirá esta sequência:

1. **Escolher como começar:** Domínio, Siescon ou sem ERP.
2. **Cadastrar ou importar empresas:** mostrar prévia, duplicidades e agrupamento por raiz.
3. **Adicionar equipe e atribuir empresas:** inclusive em lote.
4. **Aplicar modelos de atividades:** por área e perfil, com revisão das exceções.
5. **Conectar os serviços desejados:** e-mail, agente, certificados e procurações quando necessários.
6. **Definir limites:** franquia, adicional de IA e orçamento de consultas.
7. **Executar um diagnóstico:** apresentar o que está pronto e o que ainda não pode funcionar.

O administrador poderá salvar e retomar. Uma integração pendente não bloqueará as funções independentes dela.

Microsoft e Google suportam os mecanismos necessários para esse modelo de consentimento, mas políticas do tenant, verificação e possíveis avaliações de segurança precisam ser homologadas. O produto deverá explicar essas exigências dentro do assistente. [Microsoft](https://learn.microsoft.com/en-us/entra/identity-platform/single-and-multi-tenant-apps), [Google](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).

## 4. Motor central de atividades e fechamentos

### 4.1. Um modelo operacional único

A central será alimentada por quatro origens:

- Dados observados no ERP.
- Retornos oficiais das integrações.
- Documentos e informações importados.
- Atividades e registros próprios do CICA.

Os modelos de atividades definirão aplicabilidade, periodicidade, responsável, prazo, dependências e evidência necessária.

As ocorrências serão criadas por empresa, estabelecimento quando aplicável, área e competência. Reprocessar uma fonte não poderá duplicar tarefas.

Alterar um modelo não modificará silenciosamente o histórico. Mudanças relevantes serão versionadas e terão efeito identificado nas competências afetadas.

### 4.2. Situações independentes

O sistema distinguirá:

| Dimensão | Exemplos |
|---|---|
| Trabalho | Pendente, em andamento, impedido, concluído. |
| Processamento | Aberto, processado, fechado, reaberto, não verificado. |
| Obrigação | Não preparada, preparada, transmitida, aceita, rejeitada, resultado incerto. |
| Pagamento | Não aplicável, previsto, guia disponível, pagamento informado, pagamento comprovado. |
| Atualização | Atualizado, desatualizado, fonte indisponível, integração não configurada. |

“Transmitido” não será sinônimo de “aceito”; “guia emitida” não será sinônimo de “pago”; falha de consulta não significará ausência de pendência.

Para cada fonte, será exibida a última observação bem-sucedida. O estado anterior ficará disponível quando a fonte falhar, acompanhado da indicação de desatualização.

### 4.3. Fechamento concluído

A conclusão dependerá das evidências aplicáveis ao processo:

- Processamento/fechamento confirmado na fonte, quando conectado.
- Documentação e confirmação humana no modo sem ERP.
- Obrigações aplicáveis aceitas, quando exigidas pelo modelo.
- Ausência de impedimentos obrigatórios daquele fechamento.

Prazos legais e internos serão campos diferentes. Dispensas terão motivo, responsável e evidência.

Se o ERP reabrir uma competência ou surgir uma retificação relevante, o CICA reavaliará o fechamento e preservará a conclusão anterior no histórico.

### 4.4. Auditoria utilizável

Cada evento relevante registrará autor, momento, empresa, competência, ação, resultado, origem e vínculo com evidências.

Para demonstrar omissões, o sistema registrará também:

- Qual atividade era esperada.
- Quem estava responsável durante o período.
- Qual prazo estava vigente.
- Quais avisos e impedimentos foram registrados.
- Quando houve redistribuição ou alteração de prazo.

Correções serão novos eventos, sem apagar a versão anterior. Senhas, tokens e conteúdo pessoal desnecessário não entrarão nos logs.

## 5. Domínio, Siescon e funcionamento independente

O CICA terá um modelo de dados próprio. As integrações preencherão esse modelo por adaptadores, sem espalhar nomes de tabelas dos fornecedores por toda a aplicação.

Cada adaptador declarará suas capacidades: empresas, lançamentos, saldos, folha, obrigações, fechamentos e outras entidades efetivamente suportadas.

### Domínio

- Preservar o agente Windows .NET e o acesso somente leitura.
- Usar consultas permitidas, incrementais e paginadas.
- Homologar separadamente os dados contábeis, fiscais e de folha.
- Preferir APIs oficiais quando cobrirem o dado necessário.
- Manter explícitas as limitações do Domínio Web e da atualização por backup.

As estruturas já observadas no projeto não comprovam, por si só, a existência de um contrato completo para DRE ou fechamento. Cada leitura nova precisará de validação semântica.

### Siescon

A integração permanece dependente do contrato técnico de Q-33: versão, mecanismo autorizado, identificação de empresas e layouts. Nenhuma tabela ou capacidade será presumida.

O próprio Siescon apresenta um gerenciador de tarefas; a descoberta deverá verificar se existe um meio autorizado de obter estados úteis, sem prometer uma API pública não demonstrada. [Siescon](https://www.siescon.com.br/portal/modulo?modulo=21-gerenciadordetarefas).

### Sem ERP

O escritório poderá cadastrar empresas, atividades, saldos gerenciais, recebimentos e pagamentos, além de importar dados e documentos.

Relatórios contábeis dependerão de dados contábeis suficientes. Uma movimentação bancária isolada não será convertida automaticamente em DRE contábil.

Conectar um ERP posteriormente exigirá uma conciliação inicial entre registros existentes e importados. A conexão não sobrescreverá cadastros nem duplicará movimentos automaticamente.

## 6. Ferramentas de folha que ajudam de verdade

O foco será conferir, organizar e explicar o trabalho de departamento pessoal. O cálculo da folha continuará no ERP quando utilizado.

| Ferramenta | Entrega prática |
|---|---|
| Fechamento da folha | Situação por empresa e competência, com documentos, processamento, obrigações e impedimentos. |
| Conferência de encargos | Comparar valores do ERP com documentos e retornos oficiais disponíveis. |
| Análise de variações | Apontar mudanças relevantes em salários, rubricas, bases, descontos, encargos e líquido. |
| Crédito do Trabalhador | Conferir contratos e descontos registrados, diferenças e casos parciais, ligados à atividade responsável. |
| Férias e contratos | Calendário de eventos, períodos e providências, conforme dados disponíveis e regras revisadas. |
| Convenções coletivas | Repositório de instrumentos, vigência, enquadramento validado e obrigações decorrentes. |
| Conferência anual | Comparação das informações mensais e anuais, respeitando competência e pagamento. |
| Custo de pessoal | Relatório gerencial por empresa, estabelecimento e centro de custo disponível. |

Cada divergência deve mostrar a regra aplicada e os valores comparados. Alertas precisam permitir justificativa e tratamento de exceção para evitar uma fila permanente de falsos positivos.

O Domínio já oferece rotinas de Crédito do Trabalhador, incluindo importação e automações. O CICA deve aproveitar os resultados e conferir exceções, evitando reconstruir a mesma rotina. [Documentação Domínio](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=11666).

Para eSocial e FGTS, a primeira entrega usará dados do ERP e documentos importados. Uma conferência não dependerá de um novo fornecedor contratado nem alegará consulta oficial quando só houver arquivo informado pelo usuário.

## 7. Serpro e ferramentas inspiradas na pesquisa da GOB

### 7.1. Central Integra Contador

Organizar a expansão em três grupos:

| Grupo | Capacidades previstas |
|---|---|
| Acompanhamento | Situação fiscal, caixas oficiais, procurações, obrigações e atualizações disponibilizadas pelo serviço. |
| Regularização | Guias, pagamentos consultáveis, parcelamentos e acompanhamento de resultados. |
| Transmissão | DCTFWeb, PGDAS-D, DEFIS e fechamento MIT, conforme contrato de cada operação e homologação. |

O catálogo técnico deverá registrar serviço, versão, procuração, custo, efeito legal, possibilidade de repetição e evidência de conclusão. A referência é o [catálogo oficial do Integra Contador](https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/); a disponibilidade efetiva precisa ser confirmada no contrato e na homologação.

Fluxo das operações com efeito legal:

1. Preparar.
2. Validar empresa, competência e dados.
3. Mostrar conteúdo, consequências e custo aplicável.
4. Receber confirmação humana.
5. Executar exatamente a versão aprovada.
6. Consultar ou receber o resultado.
7. Guardar protocolo e atualizar a atividade.

O funcionário poderá preparar e confirmar nas próprias empresas. Não será exigido um segundo aprovador.

Mudança de conteúdo após a confirmação invalidará a aprovação. Uma resposta incerta não autorizará repetir cegamente a transmissão.

A ciência oficial será uma ação explícita. Abrir a tela inicial ou executar uma atualização de monitoramento não poderá provocar ciência silenciosamente.

### 7.2. O que aproveitar da GOB

A pesquisa mostra três frentes úteis: acompanhamento de obrigações e situação fiscal, gestão de PER/DCOMP e notificações trabalhistas. [GOB](https://gobsolucoes.com.br/gob/), [PER/DCOMP](https://gobsolucoes.com.br/perdcomp/), [DET](https://gobsolucoes.com.br/det/).

Recomendo incorporar ao CICA:

- Carteira de obrigações e pendências.
- Controle de certidões e vencimentos.
- Histórico de regime tributário.
- Acompanhamento de parcelamentos.
- Registro e acompanhamento de créditos e pedidos.
- Caixa de notificações vinculada a tarefas e prazos.

Isso será desenvolvido no CICA, sem integração ou dependência da GOB.

Quando não houver um acesso oficial homologado dentro dos serviços permitidos, o funcionamento será por cadastro/importação de documento e atualização humana. A tela deverá distinguir claramente esse modo do monitoramento automático.

DET e DTE permanecerão separados: são contextos e efeitos distintos. A cobertura divulgada por outro produto não será copiada como se estivesse disponível no CICA.

## 8. BI, DRE e relatórios em JavaScript

### 8.1. Bibliotecas escolhidas

| Finalidade | Escolha |
|---|---|
| Gráficos interativos e gráficos dos relatórios | **Apache ECharts** |
| PDF profissional | **Puppeteer + Chromium**, usando HTML/CSS |
| Planilhas XLSX | **ExcelJS** |
| Cálculos decimais no componente JS | **Decimal.js** |
| Tabelas analíticas interativas | **Tabulator**, onde a complexidade justificar |
| Código do serviço de relatórios | **Node.js + TypeScript** |

O ECharts permite reutilizar os gráficos na interface e gerar SVG no servidor. Puppeteer renderiza PDF com estilos de impressão; ExcelJS atende à geração de planilhas formatadas; Decimal.js evita usar ponto flutuante binário como base dos cálculos monetários. [ECharts](https://echarts.apache.org/handbook/en/how-to/cross-platform/server/), [Puppeteer](https://pptr.dev/api/puppeteer.page.pdf), [ExcelJS](https://github.com/exceljs/exceljs), [Decimal.js](https://github.com/MikeMcl/decimal.js), [Tabulator](https://www.tabulator.info/docs/6.x/).

A geração atual de relatórios do Copiloto com ReportLab e OpenPyXL será migrada. Bibliotecas Python ainda necessárias para leitura ou importação de arquivos não serão removidas indiscriminadamente.

### 8.2. Motor de relatórios

Um serviço Node interno receberá uma fotografia versionada dos dados autorizados e produzirá PDF ou XLSX.

Regras:

- O mesmo conjunto de dados alimenta números, tabelas e gráficos.
- Valores monetários trafegam com precisão decimal explícita.
- Fórmulas são versionadas e restritas às operações permitidas.
- Relatórios não executam JavaScript, SQL ou HTML arbitrário informado por usuários.
- Arquivos gerados preservam filtros, período, fonte, versão do modelo e atualização dos dados.
- Uma falha de geração não interfere no fechamento ou na transmissão.
- A permissão será verificada tanto ao solicitar quanto ao baixar.

Não haverá uma segunda fila de negócios independente: Django/Celery continuarão orquestrando as solicitações, com o serviço Node responsável pela renderização e pelos cálculos de apresentação definidos.

### 8.3. DRE confiável

A DRE terá:

- Mapeamento versionado do plano de contas.
- Grupos e fórmulas configuráveis.
- Comparação mensal, acumulada e entre períodos.
- Análises horizontal e vertical.
- Detalhamento do total até as contas e lançamentos disponíveis.
- Identificação de contas sem mapeamento.
- Separação entre ajustes gerenciais e dados de origem.
- Conferência com os relatórios do ERP na homologação.

O relatório não será marcado como completo quando faltarem dados ou mapeamentos relevantes.

A IA poderá redigir uma análise dos números já calculados, indicando as evidências utilizadas. Não será o motor responsável por somar saldos ou determinar o resultado.

### 8.4. Modelos configuráveis

Entregas iniciais:

- DRE gerencial.
- Evolução de receitas, despesas e resultado.
- Fluxo de caixa projetado e realizado.
- Custo de pessoal.
- Situação fiscal e obrigações.
- Fechamento mensal e pendências.
- Diagnóstico de preparação para a reforma.

O escritório poderá ajustar marca, seções, indicadores, gráficos, comparações e mapeamentos permitidos.

A exportação será livre para usuários autorizados. Um relatório incompleto sairá identificado como preliminar, com pendências e data de atualização, sem exigir uma etapa adicional de liberação.

## 9. Reforma tributária e caixa líquido

### 9.1. Avaliação da proposta

O painel de caixa líquido é uma boa oportunidade porque liga mudança tributária a uma decisão concreta: quanto a empresa terá disponível para pagar suas obrigações.

A limitação é a qualidade dos dados. Sem integração com os meios de pagamento, o CICA não poderá conhecer automaticamente toda retenção efetiva. O produto deve entregar uma projeção explicável e permitir conciliá-la com os valores informados/importados.

A regulamentação e os padrões do split payment estão evoluindo. A implementação usará regras versionadas e fontes oficiais, sem uma alíquota universal aplicada indistintamente a todos os recebimentos. [Atos técnicos RFB/CGIBS](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/reforma-tributaria-do-consumo/legislacao/atos-tecnicos-conjuntos/).

### 9.2. Três visões distintas

| Visão | Significado |
|---|---|
| Simulação | Resultado de hipóteses escolhidas pelo usuário. |
| Projeção | Estimativa baseada nos recebíveis, pagamentos e regras conhecidos. |
| Realizado | Valores registrados e conciliados com a evidência disponível. |

Recebimentos informados manualmente serão identificados como informados. A comprovação documental acrescentará outro nível de evidência, sem transformar uma confirmação humana em consulta bancária.

### 9.3. Dados e funcionamento

Entradas:

- Saldo inicial com data de referência.
- Contas a receber e a pagar.
- Datas previstas e efetivas.
- Parcelamentos dos recebimentos.
- Tarifas, antecipações, devoluções e estornos.
- Retenções tributárias estimadas ou comprovadas.
- Folha e outras provisões.
- Documentos fiscais disponíveis.

As entradas serão por cadastro, importação e fontes ERP homologadas. Toda importação terá prévia, conferência de empresa, validação e prevenção de duplicidade.

Recomendo um horizonte inicial configurável de **13 semanas**, com detalhamento diário e visão semanal.

O sistema mostrará:

- Recebimento bruto.
- Retenções e descontos.
- Entrada líquida.
- Compromissos previstos.
- Saldo projetado.
- Menor saldo no horizonte.
- Necessidade estimada de capital de giro.
- Diferenças entre projetado e realizado.

Crédito tributário não será tratado como dinheiro disponível antes de um evento que efetivamente altere o caixa. Tributo retido não poderá ser descontado novamente como uma provisão da mesma obrigação.

### 9.4. Outras ferramentas da reforma

- Diagnóstico de preparação por empresa.
- Conferência dos campos tributários nos documentos suportados.
- Cenários de margem, preço e prazo de recebimento.
- Registro de créditos e de seu tratamento.
- Acompanhamento de diferenças entre documentos, apuração e pagamentos.
- Radar normativo com fonte, vigência e atividade de adequação.

A calculadora oficial poderá ser avaliada como componente local de apoio, conforme cobertura e licença verificadas. Ela não substitui a projeção financeira nem será tratada como uma API pública de produção presumida. [Manual oficial da plataforma CBS](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/manuais/reforma-tributaria-do-consumo/manual-plataforma-cbs-21-maio-2026-07h40.pdf).

## 10. IA, Triagem e módulos existentes

O plano preservará e concluirá Triagem, NFS-e, certificados, Conciliação, Radar, Copiloto e Integra Contador. A central passará a apresentar o trabalho desses módulos de maneira integrada.

### IA

O Copiloto poderá:

- Explicar uma divergência com base nos registros.
- Localizar documentos autorizados.
- Resumir o estado da empresa.
- Sugerir ações e preparar minutas.
- Elaborar comentários gerenciais para relatórios.
- Apoiar classificação e identificação de documentos.

As respostas deverão indicar fonte e atualização. Ausência de dados será apresentada como ausência de dados.

Confirmações legais, regras de acesso, cálculos oficiais e limites financeiros serão controlados por código determinístico.

Mantêm-se a IA por API inicialmente, a preparação do processamento local e o isolamento dos dados e aprendizados por escritório. A migração para IA local continuará dependente de hardware e homologação.

### Triagem

A entrada inicial permanece por e-mail, conforme decisão anterior. Importações do caixa e da Conciliação não mudam essa regra.

Fluxo:

**Recebimento → verificação do arquivo → identificação → classificação → revisão quando necessária → arquivamento confirmado → atualização da atividade.**

Receber um anexo não comprova que ele foi corretamente arquivado. Falhas de identificação ou destino permanecerão visíveis.

### Conciliação e NFS-e

A Conciliação manterá a entrada única de arquivos e a prevenção de duplicidade já desenvolvidas. As exportações continuarão vinculadas ao adaptador de destino homologado.

NFS-e manterá revisão fiscal e validação dos acumuladores da empresa. Nenhuma expansão da central autorizará lançamento direto no ERP.

## 11. Comercial e controle de consumo

### Suíte completa

Todos os pacotes terão o mesmo conjunto de funcionalidades liberadas para venda. A diferença estará na capacidade contratada e na franquia de IA.

- Usuários ativos, inclusive administradores, ocupam capacidade.
- Uma raiz de CNPJ ativa ocupa uma empresa.
- Filiais permanecem individualizadas operacionalmente.
- Arquivados ficam disponíveis para consulta e histórico.
- Arquivar não apaga consumo nem altera retroativamente faturamento.
- Ultrapassar capacidade exige mudança explícita de contrato; não gera cobrança surpresa.

### Integra Contador

O livro de consumo registrará serviço, quantidade, escritório, empresa, operação, tarifa aplicável, estimativa, custo apurado e ajustes.

O acerto mensal deverá reconciliar o total atribuído aos escritórios com o custo correspondente do fornecedor. Diferenças de arredondamento serão compensadas de forma determinística, sem gerar margem.

Falhas ou repetições serão tratadas conforme a cobrança efetiva do fornecedor. O CICA não presumirá que uma chamada sem resposta foi gratuita.

### IA

A interface mostrará:

- Franquia disponível em reais de uso CICA.
- Consumo acumulado.
- Adicional autorizado.
- Valor reservado para operações em andamento.
- Teto mensal.
- Histórico detalhado.

O saldo representa a tabela comercial do CICA, não uma promessa de repasse do custo do provedor.

O administrador controlará o teto. Operações concorrentes reservarão saldo antes da execução para não ultrapassá-lo.

## 12. Arquitetura, interfaces e segurança

### Estrutura técnica

Preservar:

- Django e APIs existentes.
- PostgreSQL.
- Celery e Redis.
- Templates e JavaScript, com evolução gradual da interface.
- Agente Windows .NET.
- Separação por escritório.

Adicionar:

- Motor de atividades e evidências.
- Modelo normalizado de fontes e capacidades.
- Conferências de folha.
- Serviço Node/TypeScript de relatórios.
- Modelo de dados analíticos e mapeamento de DRE.
- Caixa gerencial e cenários da reforma.
- Nova medição comercial de capacidade, IA e Serpro.

### Contratos principais

| Contrato | Responsabilidade |
|---|---|
| Capacidades da fonte | Informar quais dados e ações um adaptador suporta. |
| Observação da fonte | Guardar origem, identificador, competência, versão e momento da leitura. |
| Atividade | Registrar obrigação esperada, responsável, prazo, dependências e situação. |
| Evidência | Associar documento, retorno ou confirmação à conclusão observada. |
| Aprovação | Vincular usuário à versão exata de uma operação. |
| Execução | Controlar tentativas, protocolo, resultado e situação incerta. |
| Fotografia do relatório | Fixar dados, filtros, regras e versões usados na geração. |
| Consumo | Controlar reserva, custo, liquidação, ajuste e faturamento. |

Novas APIs serão versionadas e protegidas pelo mesmo isolamento de escritório e empresa. O serviço Node será interno; não receberá credenciais de ERP ou Serpro.

### Segurança e continuidade

- Revalidar permissões em tarefas assíncronas e downloads.
- Invalidar acesso quando uma atribuição for revogada.
- Separar segredos de logs e documentos.
- Restringir arquivos, templates e acesso de rede do renderizador de PDF.
- Proteger planilhas contra interpretação indevida de conteúdo como fórmula.
- Manter políticas de retenção por categoria e bloqueio de descarte quando necessário.
- Exigir política de dados aprovada antes de ativar processamento real de conteúdo pessoal.
- Preservar cópias e evidências necessárias à recuperação.

Prazos legais de retenção, infraestrutura e termos não serão inventados pelo implementador. Serão artefatos obrigatórios da preparação para produção; sem aprovação, a função dependente não será ativada.

## 13. Plano de ação, validação e entrega

O plano será incorporado ao **plano mestre existente**, preservando o histórico das etapas 00–13. As novas frentes entrarão como extensões com dependências explícitas; não haverá um plano concorrente.

| Ordem | Frente | Entrega | Critério de aceite |
|---|---|---|---|
| 1 | Consolidar decisões | Atualizar regras comerciais, acesso, fechamento, relatórios e integrações permitidas. | Nenhuma contradição ativa entre plano, decisões e etapas. |
| 2 | Base independente de ERP | Cadastros, capacidades de fontes e proveniência. | Mesma empresa operável sem ERP e com fonte simulada, sem duplicação. |
| 3 | Acesso e auditoria | Carteiras por funcionário, administração e trilha de eventos. | Bloqueio de acesso indevido em telas, APIs, tarefas e arquivos. |
| 4 | Motor de atividades | Modelos, prazos, dependências, evidências e fechamento. | Reprocessamento idempotente; reabertura e indisponibilidade tratadas corretamente. |
| 5 | Interface operacional | Minha área, visão administrativa e ficha da empresa. | Usuário consegue identificar e resolver uma pendência de ponta a ponta. |
| 6 | Integrações ERP | Contratos ampliados Domínio e adaptador Siescon. | Correspondência comprovada com os dados da fonte; capacidade ausente não simulada. |
| 7 | Comercial e consumo | Pacotes, raiz de CNPJ, franquia IA e custo efetivo Serpro. | Fatura reconciliada; reservas concorrentes respeitam limites. |
| 8 | Central Serpro | Consultas, monitoramento e transmissões aprovadas. | Aprovação vinculada ao conteúdo e protocolos recuperáveis; sem repetição indevida. |
| 9 | Folha | Conferências, eventos e relatórios de pessoal. | Diferenças explicáveis e verificadas em amostras reais autorizadas. |
| 10 | Relatórios JS | DRE, gráficos, PDF, XLSX e modelos configuráveis. | Números iguais entre formatos e conferidos com as fontes. |
| 11 | Reforma e caixa | Cadastro, importação, projeções e cenários. | Simulado, projetado e realizado separados; sem dupla dedução. |
| 12 | Integração dos módulos atuais | Triagem, NFS-e, Conciliação, Radar e Copiloto alimentando a central. | A atividade acompanha corretamente o resultado de cada módulo. |
| 13 | Configuração e documentação | Assistente, diagnóstico, ajuda contextual e procedimentos de suporte. | Escritório configura o fluxo homologado seguindo o próprio produto. |
| 14 | Homologação integrada | Piloto, desempenho, recuperação e validação comercial. | Evidências reais aprovadas pelo proprietário, conforme D-73. |
| 15 | Liberação | Oferta coerente com capacidades homologadas, suporte e operação preparados. | Nenhuma função anunciada depende de fluxo não comprovado. |

Toda execução que exija ambiente publicado, credenciais de produção, chamadas reais ou piloto continuará vinculada à etapa 12 existente, conforme D-87. A IA local definitiva permanece na etapa 13 e não bloqueia a venda inicial com API.

A ordem representa dependências, não uma estimativa de semanas. O calendário será estabelecido após dimensionar equipe, capacidade e contratos técnicos.

### Entrega obrigatória de cada frente

- Comportamento implementado.
- Testes pertinentes e resultados.
- Evidências visuais quando houver interface.
- Limitações e dependências externas identificadas.
- Procedimento de recuperação.
- Documentação de operação e suporte.
- Atualização do checklist e do registro de execução.
- Prompt da etapa seguinte com pré-requisitos e aceite.

## 14. Validação e critérios de liberação

### Testes essenciais

| Área | Cenários obrigatórios |
|---|---|
| Isolamento | Tentativas de acesso cruzado entre escritórios e empresas, inclusive downloads e tarefas assíncronas. |
| Fechamento | ERP fechado com obrigação pendente; obrigação aceita com ERP aberto; reabertura; dispensa; fonte indisponível. |
| Sem ERP | Cadastro, importação, confirmação documental e posterior conexão sem sobrescrita ou duplicação. |
| Transmissões | Conteúdo alterado após aprovação, clique duplicado, expiração de permissão, timeout e retorno tardio. |
| Ciência oficial | Monitoramento sem ciência; confirmação explícita; registro do efeito e do resultado. |
| Auditoria | Redistribuição, mudança de prazo, impedimento e atividade vencida com histórico preservado. |
| Cobrança | Matriz/filiais, arquivamento, usuários ativos, reservas simultâneas e ajustes de custo. |
| DRE | Conta não mapeada, estorno, sinal, competência, ajuste gerencial e igualdade entre formatos. |
| Caixa | Recebimento parcial, antecipação, tarifa, devolução, atraso, retenção e importação repetida. |
| IA | Falta de fonte, tentativa de acesso indevido, conteúdo pessoal bloqueado e esgotamento de saldo. |
| Recuperação | Queda de worker, agente, fonte e serviço de relatórios, sem perda ou execução duplicada. |

As métricas já aprovadas em D-73 permanecem: amostras revisadas, precisão medida para classificação, zero associação indevida entre empresas, recuperação em até 15 minutos, restauração conferida em até 4 horas e tempos por empresa dentro do limite aprovado, ressalvadas dependências externas documentadas.

Esses critérios não serão substituídos por quantidade de testes passando.

### Interface e relatórios

Aplicar o fluxo obrigatório do projeto:

- UI/UX Pro Max e referências reais.
- Watermelon para inspiração pertinente.
- Auditoria pelas Web Interface Guidelines.
- Playwright em desktop e celular.
- Teclado, foco, estados vazios, carregamento, falha e permissões.
- Inspeção dos PDFs e planilhas gerados.
- Encerramento das sessões de navegador abertas para validação.

A identidade atual do CICA será preservada. Referências como a organização do trabalho do [Karbon](https://karbonhq.com/solution/project-management) servirão para hierarquia e fluxo. Refero, SaaSFrame e Watermelon serão referências de composição, sem copiar interfaces nem alegar inspeção de fluxos restritos que não estiverem acessíveis.

### Medidas de valor do produto

O piloto deverá comparar o processo anterior e o CICA:

- Tempo para identificar o que falta fechar.
- Tempo gasto consultando fontes.
- Quantidade de pendências detectadas antes do prazo.
- Retrabalho provocado por informação divergente.
- Tempo para produzir uma entrega gerencial.
- Quantidade de alertas úteis versus descartados.
- Facilidade de configuração e necessidade de suporte.

As metas de melhoria serão fixadas a partir dessa linha de base, sem percentuais comerciais inventados.

## 15. Migração, documentação e liberação comercial

A implementação começará atualizando os registros canônicos:

- [PLANO-MESTRE.md](C:/Users/gege/Documents/DjangoSys/HubContador/PLANO-MESTRE.md)
- [DECISOES.md](C:/Users/gege/Documents/DjangoSys/HubContador/DECISOES.md)
- [VALIDACOES.md](C:/Users/gege/Documents/DjangoSys/HubContador/VALIDACOES.md)

As novas decisões substituirão explicitamente as partes incompatíveis de D-23, D-39, D-42, D-44 e da precificação antiga do Serpro, preservando o histórico.

A migração será aditiva:

- Manter dados e evidências existentes.
- Não reaproveitar automaticamente o antigo módulo Jornadas como motor da nova central.
- Ativar capacidades por escritório após validação.
- Comparar resultados novos e antigos antes da substituição.
- Preservar a leitura dos relatórios e consumos históricos.
- Permitir desativar uma integração com problema sem indisponibilizar o restante do produto.

A liberação comercial dependerá de preços aprovados, políticas de dados, homologações, documentação e capacidade operacional demonstrada. Não haverá contratação, publicação ou chamada cobrada implícita neste plano.

**Estado desta entrega:** plano de produto e execução, apoiado na inspeção do projeto e na pesquisa realizada. Nenhum arquivo foi alterado e nenhuma nova funcionalidade foi implementada ou homologada nesta etapa de planejamento.

