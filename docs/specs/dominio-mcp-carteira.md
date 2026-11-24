# MCP do Domínio — o produto é a carteira (pesquisa e escopo, 24/11/2026)

Pergunta do dono: o MCP é útil de verdade? O que o mercado já tem? Este documento junta a pesquisa de dores reais de escritórios que usam o Domínio, ranqueia as perguntas e diz o que foi entregue. Decisões da frente: `DC-1` a `DC-4` (mais abaixo; os números D-/V- do repositório ficam para a reintegração com a produção).

## O que o mercado já tem

- **Domínio IA** (Thomson Reuters, lançado em 30/09/2026): conversa com o balancete e as demonstrações, BIS customizado por linguagem natural, conferência de eSocial e DCTFWeb, mais de 80% do Plano Referencial mapeado. Roda dentro do sistema, no contexto de uma empresa por vez, com o conteúdo fiscal da TR. Fontes: [Portal ERP](https://portalerp.com/br/noticia/thomson-reuters-lanca-dominio-ia-para-automatizar-rotinas-e-analisar-dados-contabeis), [Inforchannel](https://inforchannel.com.br/2026/10/01/dominio-ia-une-inteligencia-artificial-e-conhecimento-tributario-da-thomson-reuters/). Não há avaliação independente de precisão.
- **Adoção:** 79% de 644 escritórios usam IA generativa e 67% não medem produtividade ([RDD/Connectabil](https://www.robertodiasduarte.com.br/ia-no-mercado-contabil-medir-antes-de-automatizar/)); 78% de 393 profissionais usam IA toda semana, e os órgãos pedem conferência, validação e rastreabilidade ([CFC/Fenacon/IOB](https://cfc.org.br/noticias/pesquisa-mostra-avanco-da-inteligencia-artificial-na-rotina-dos-profissionais-da-contabilidade/)). Chat sozinho virou commodity.
- **Fora do Brasil:** Xero e QuickBooks têm MCP oficial, centrado em ler e escrever o livro-razão de uma empresa ([levantamento](https://dev.to/grove_chatforest/accounting-bookkeeping-mcp-servers-quickbooks-xero-zoho-books-beancount-and-more-2kgg)); a Pilot vende fechamento mensal autônomo ([CPA Practice Advisor](https://www.cpapracticeadvisor.com/2026/06/23/pilot-says-new-ai-accounting-platform-meridian-runs-monthly-close-from-start-to-finish/185541/)), números do próprio fornecedor.

Conclusão de produto: "perguntar ao banco do Domínio" não diferencia. O que nenhum deles faz é olhar **a carteira inteira de uma vez**, com número rastreável, usando a IA que o escritório já paga.

## A prova de que a lacuna é real

O próprio Domínio entrega, na Central de Soluções, **239 relatórios personalizados `.bgr`** (178 de Folha, 43 de Escrita, 10 de Contabilidade, 7 gerais) que o contador baixa e importa à mão no Gerador de Relatórios: [índice oficial](https://suporte.dominioatendimento.com/central/faces/relatorios-personalizados.html). São, na prática, a lista de pedidos que o sistema não atende nativamente. Exemplos: [Como identificar notas sem contabilização?](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=10058), [Regime de Apuração dos Clientes](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=11646), [relatório de empresas](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=1301). Em um fórum do setor, a resposta a "falta um relatório de diferenças" foi que o suporte pode construir um ([Contábeis](https://www.contabeis.com.br/forum/tecnologia-contabil/181498/dominio-sistemas-diferencas-sped-fiscal/), 2015).

Limites desta pesquisa, ditos de frente: não achei pesquisa que ranqueie tarefas por horas gastas nem threads recentes sobre o Domínio no Reddit; os tópicos de fórum são de 2014 a 2017; as demais fontes são blogs e conteúdo de fornecedores. O ranking abaixo mede **evidência de que a pergunta existe** (relatório que o Domínio precisou distribuir, ou prática recorrente em guias do setor), não horas. Quem valida o ranking é a contadora.

## As 10 perguntas, ranqueadas

Evidência: **A** = o Domínio distribui relatório `.bgr` para isso; **B** = guias e artigos do setor apontam como rotina ou gargalo; **H** = hipótese nossa, sem fonte.

| # | Pergunta do contador | Evidência | Estado |
|---|---|---|---|
| 1 | Quais clientes têm nota lançada sem lançamento contábil? | A (Central 10058; "notas sem contabilização"; "parcelas baixadas sem contabilização") | **feita**: `notas_sem_contabilizacao` |
| 2 | Quanto cada cliente faturou, qual o acumulado de 12 meses e quão perto está do limite do Simples? | A ("Demonstrativo de Faturamento com a Receita Bruta Acumulada", "Faturamento de Todas Empresas") e B (acompanhar o acumulado todo mês é a recomendação comum: [Agilize](https://agilize.com.br/artigos/?p=431), [Contabilizei](https://www.contabilizei.com.br/contabilidade-online/limite-simples-nacional/)) | **feita**: `faturamento_e_limite` |
| 3 | Quem não mandou documento este mês? | A ("Quantidade de notas fiscais por Tipo e Empresa") e B (documento atrasado transforma o fechamento em emergência: [Jettax](https://www.jettax.com.br/blog/como-organizar-os-processos-contabeis-e-reduzir-riscos-no-escritorio/)) | **feita**: `sem_movimento` |
| 4 | Qual o regime, o CNAE e o que falta parametrizar em cada empresa? | A (4 relatórios: regimes, relação de empresas, CNAEs, empresas sem parâmetros na Escrita e na Contabilidade; Central 11646) | **feita**: `cadastro` |
| 5 | Quais empresas com contabilidade estão sem lançamento no mês? | A ("totais de lançamentos contábeis", "empresas com Zeramento") e B (fechamento mensal é o maior gargalo: [Ledware](https://www.ledware.com.br/2026/01/18/rotinas-contabeis-como-organizar-padronizar-e-escalar-um-escritorio-de-contabilidade/)) | **feita**: `lancamentos_contabeis` |
| 6 | Quais clientes têm buraco ou repetição na numeração das notas emitidas? | B (conferência de numeração é rotina de fechamento; o Domínio só confere empresa a empresa) | **feita**: `numeracao` |
| 7 | Quais clientes cancelam muita nota? | A ("notas canceladas, denegadas ou devoluções"; "Notas Canceladas com Estoque") | **feita**: `notas_canceladas` |
| 8 | Quem teve queda ou salto de faturamento fora do normal? | H | **feita**: `variacao_faturamento` (marcada como sinal, não conclusão) |
| 9 | Quais notas têm erro que a EFD Contribuições vai recusar (sem PIS/COFINS, CST incoerente)? | A ("Relatório de erros na EFD Contribuições", comparativos de PIS/COFINS por produto) | **pendente**: exige validar a semântica de CST e natureza da receita com a contadora |
| 10 | Quais balancetes não fecham ou têm conta sem vínculo referencial? | A ("contas contábeis com contas referenciais", "contas não vinculadas ao DFC"; mensagem "Ativo diferente do Passivo no Balanço Referencial", Central 7133) | **pendente**: exige regra de saldo por natureza de conta, conferida contra o balancete oficial |

Candidatos fora do ranking: certificados digitais a vencer (relatório A "Lista de Certificados Digitais"; a tabela é de credencial e a política a bloqueia, e o Hub já acompanha certificado e procuração), períodos fechados por módulo (relatório A; a tabela não foi localizada) e conferência de eSocial (o Domínio IA já cobre).

## O que foi entregue

- Uma ferramenta, `analise_da_carteira`, com oito análises fixas (`DC-2`): o cliente escolhe a análise e os valores, nunca o SQL. Cada uma é uma consulta verificada com aviso, colunas declaradas e classe de dados (nome da empresa é `texto_livre`; nenhum dado pessoal ou segredo sai).
- Paginação por `deslocamento`: o teto de 12 KB da resposta corta antes das 500 linhas, e a varredura de 630 empresas segue o campo `truncado` sem repetir nem pular empresa.
- Um roteiro `briefing_da_carteira(mes)`: o escritório roda no Claude ou no ChatGPT dele e recebe o resumo por gravidade, com o número que sustenta cada item.
- Orçamento de custo por consulta (`DC-3`): o servidor estima custo pessimista para junções largas (33 milhões de linhas estimadas para uma consulta de 1 s) e o limite global provisório (10) recusaria todas. Cada consulta declara o que mediu, dentro de um teto duro (50 mil), o cliente nunca escolhe, e o timeout de 30 s com cancelamento continua valendo. Bônus: `conferir_numeracao` recusava as empresas grandes (custo 19,5) e passou a ter orçamento próprio.

## Decisões da frente

- **DC-1** Escopo: a carteira é o produto; o MCP é o motor. Ferramentas novas só entram com pergunta de evidência A ou B e com conferência cruzada no banco real.
- **DC-2** Uma ferramenta com lista fechada de oito análises, em vez de oito ferramentas: mantém o esquema pequeno no contexto da IA e o conjunto de ferramentas do repasse (`relay-job`) fechado. Sem SQL do cliente em nenhum campo.
- **DC-3** Orçamento por consulta, medido e com teto duro, até o ensaio de carga T4.9 calibrar o custo estimado contra o tempo real (continua pendente da janela autorizada pelo dono). Medido hoje: as nove consultas da carteira inteira levam 8 s no total, com paginação.
- **DC-5** Cancelada = marca `cancelada_*` ou situação do documento 2, 7 ou 8 (legenda do leiaute de importação, Central 672); a marca sozinha deixava a taxa em zero. A unidade de contagem é a nota (espécie, série e número; na entrada, também o fornecedor), não a linha de segmento.
- **DC-6** Simples = `simplesn_optante_par = 'S'` (flag real do cadastro), não o código inferido de `rfed_par`; MEI com R$ 81 mil; limite proporcional no ano de início. Todos a conferir com a contadora.
- **DC-4** A ligação nota → lançamento contábil é `ctlancto.orig_lan` (5 saída, 6 entrada, 7 serviço) mais `ctlancto.ndoc_lan` = código interno da nota (`codi_sai`, `codi_ent`, `codi_ser`). A primeira hipótese, `ndoc_lan` = número da nota, casava por coincidência (datas e valores diferentes) e foi descartada na conferência por valor e data; o Domínio indexa a relação em `IDX_DOCTO`.

## O que ainda não é verdade

- Nada foi conferido contra um relatório oficial do Domínio (a contadora): as consultas batem entre si e com SQL escrito de outro jeito no banco real, e uma revisão independente já derrubou três premissas minhas (cancelamento, unidade da nota, regime); não batem com o relatório da tela.
- Os limites do Simples (R$ 4,8 milhões, sublimite de R$ 3,6 milhões, MEI de R$ 81 mil, proporcional no ano de início) e a regra "acumulado de 12 meses para a faixa, ano-calendário para a exclusão" vêm de guias do setor e da LC 123/2006 lida de segunda mão. O regime vem da flag `simplesn_optante_par`; a legenda do código `rfed_par` (2 = "Microempresa") é inferida e não serve de limite. A saída leva os dois acumulados e o aviso.
- O banco real está em migração: poucas empresas têm 12 meses de histórico (só uma com 12 meses completos na data da medição) e a maioria nunca integrou escrita fiscal com contabilidade. Os números de hoje provam que as consultas funcionam, não o estado do escritório.
- O `.mcpb` precisa ser reinstalado no Claude Desktop para enxergar a ferramenta nova; nenhum cliente real (Claude ou ChatGPT) foi conectado.
- Perguntas 9 e 10 seguem abertas; `build-pack --aceitar` (L2 livre) segue com o dono.
