# CICA — plano de conclusão revisado em 05/10/2026

**Ponto de entrada vigente:** esta revisão organiza a conclusão do sistema a partir da auditoria
solicitada em D-275. Preserva as etapas 00–13 e decisões anteriores aplicáveis. O conteúdo histórico
abaixo continua como memória, mas seus estados datados não substituem este resumo reconciliado.
Esta entrega é planejamento: não implementa as propostas nem autoriza nova publicação ou consumo.

**Diagnóstico e fontes:** [auditoria completa de produto, telas e mercado](docs/planejamento/auditoria-produto-2026-10-05.md).
**Evidência desta análise:** V-275 em [VALIDACOES.md](VALIDACOES.md).
**Decisões/regras:** [DECISOES.md](DECISOES.md).
**Perguntas únicas:** [duvidas-abertas.md](docs/planejamento/duvidas-abertas.md).

## Resultado que se pretende entregar

Um escritório deve conseguir cadastrar sua carteira, preparar as fontes necessárias, distribuir
o trabalho, receber/coletar dados, conferir exceções, concluir com evidência, entregar o resultado
e recuperar falhas. Dono, gestor, operador, auditor, financeiro e suporte precisam compreender seu
próximo passo e seus limites sem depender de intervenção do desenvolvedor.

O CICA já tem boa parte da base e várias jornadas refinadas. O esforço agora se concentra em
completar encadeamentos, corrigir inconsistências de uso, homologar integrações e operar com prova.
Não há justificativa para refazer todas as telas nem para trocar a identidade visual do produto.

**Duas liberações distintas, sem reduzir o objetivo final:**

1. **Produto NFS-e completo**, conforme prioridade já decidida em D-189: coleta, classificação,
   revisão, pacote, importação conferida no Domínio, acesso, suporte e recuperação.
2. **Suíte CICA completa:** todas as capacidades assumidas nas etapas 00–12 e na evolução D-109,
   com integrações e percursos reais homologados. IA local definitiva continua na etapa 13 e não
   bloqueia a venda inicial por API, conforme D-50/51.

Portal do cliente, novos canais, novos ERPs, Open Finance, app móvel, CRM amplo e outras expansões
não viram exigência retroativa para o produto NFS-e. As oportunidades novas têm prioridade e
decisão próprias, explicitadas abaixo.

## Definição objetiva de “100% concluído”

Uma capacidade só estará concluída quando todos os itens aplicáveis tiverem evidência:

- [ ] Regra e escopo aprovados, sem conflito D/Q pendente que altere o comportamento.
- [ ] Implementação cobre o percurso inteiro, incluindo retorno e evidência final.
- [ ] Usuário autorizado encontra, entende e termina a tarefa; perfil consultivo não altera.
- [ ] Estados inicial, vazio, carregando, parcial, erro, incerto, indisponível e concluído são honestos.
- [ ] Testes locais e concorrência pertinente passam na versão exata da entrega.
- [ ] Desktop, celular, teclado, foco, temas e recuperação foram inspecionados na jornada afetada.
- [ ] A capacidade foi publicada com manifesto, migrações, rollback e compatibilidade verificados.
- [ ] Integração e dado real autorizados foram homologados, quando necessários.
- [ ] Desempenho, retomada, restauração, custo e consumo cumprem seus critérios aplicáveis.
- [ ] Ajuda, contrato, suporte e oferta correspondem ao comportamento liberado.
- [ ] O proprietário registrou o aceite; nenhum impedimento crítico foi convertido em “concluído”.

Usar uma matriz por capacidade com colunas **implementado / validado localmente / publicado /
homologado / liberado**, cada uma com data, release e V correspondente. Não calcular conclusão
pela quantidade de telas ou testes. Uma etapa bloqueada continua aberta; documentar o bloqueio
não atende seu aceite.

Critérios já aprovados D-73: 200 itens por fluxo automatizado, precisão mínima de 95% onde
aplicável, zero duplicidade/associação errada/vazamento, retomada sem perda até 15 minutos,
restauração de banco e documentos até quatro horas e processamento por empresa até cinco minutos
salvo dependência externa registrada. Exportação exige importação e conferência no destino.
Definir RPO e janela de medição sem presumir novos números. Cobertura e precisão são métricas distintas.

## Estado atual das etapas, reconciliado

| Etapa | Situação em 05/10/2026 | Condição restante principal |
|---|---|---|
| 00 | Base documental existente; revisão integral de planejamento entregue em V-275 | Manter matriz corrente e corrigir contradições de checklists nas entregas dependentes |
| 01 | Base local sólida; V-274 registra 1.106 testes/145 subtestes, seis skips | Release atual, CI remoto, carga, concorrência pertinente, recuperação e dependências |
| 02 | Acesso, equipe, MFA e administração implementados | E-mail/recuperação reais, escala da carteira, clareza de papéis e aceite por perfil |
| 03 | Agente .NET e Domínio local/backup implementados; leituras reais documentadas | Instalação/upgrade/revogação/rede/pastas e piloto integral |
| 04 | Estrutura e recusa segura existentes; Siescon sem adaptador homologado | Contrato Q-33, implementação, leitura e importação conferidas |
| 05 | Copiloto e pipeline de IA presentes | Curadoria utilizável, dados/custos/governança, avaliação real e relatórios publicados |
| 06 | Componentes da Triagem presentes | Encadear processamento, corrigir revisão, checklist e homologar caixas/destinos |
| 07 | NFS-e opera em produção; V-274 registra 29.042 notas avaliadas | Indicadores/contexto, qualidade do piloto, Q-39 e operação recuperável |
| 08 | DTE/DCTFWeb/PARCSN e controles locais implementados | Serviço Serpro real, custo/retorno, D-149/Q-40 e aceite por operação |
| 09 | Conciliação/Radar implementados em grande parte | Corpus/layouts/OCR, destino ERP, fontes/cobertura e carga |
| 10 | Contratos/livros/faturas presentes | Modelo D-109, Asaas completo, pagamento→acesso e casos comerciais |
| 11 | Muitas telas e pontes já revisadas; auditoria abrangente atual entregue | Correções localizadas, calendário/modelos reais e testes com usuários |
| 12 | Produção Fly+Neon e NFS-e real já iniciados | Homologação por módulo, restore medido, alarmes, suporte, privacidade e liberação |
| 13 | Pipeline/runtime preparados, sem conclusão de IA definitiva | Equipamento/modelo, treino/avaliação/capacidade e virada aprovados |

V-274 é evidência histórica, não teste repetido nesta análise. Publicação de uma release maior
não demonstra que todas as modificações locais foram incluídas. A matriz deve conferir artefatos
por capacidade, principalmente as revisões V-254–273 que registram entregas locais.

## Ordem de execução e entregas verificáveis

Os pacotes PC abaixo desdobram as etapas existentes. São unidades de acompanhamento, não novas
etapas concorrentes. **Crítico** bloqueia a liberação indicada; **alto** afeta a operação diária;
**médio** melhora fluidez. Novas capacidades permanecem propostas. Não há estimativa de calendário
sem dimensionar equipe, acesso e disponibilidade do piloto.

| Pacote | Prioridade / etapas | Entrega concreta | Dependência e responsável | Aceite específico |
|---|---|---|---|---|
| PC-01 | Alto · 00/11/12 | Matriz única por capacidade/release; reconciliar D-109, oferta, Q atuais e checklists | Desenvolvimento + proprietário; base V-275 | Nenhum falso “pronto”/“não iniciado”; cada bloqueio tem próximo passo e dono |
| PC-02 | Alto · 07/11 | Corrigir indicadores NFS-e e links para usar o mesmo recorte de empresa/pesquisa/período da lista | Desenvolvimento; A-14 | Dois meses/empresas, filtros, paginação, relatório e classificação demo concordam; clique preserva contexto |
| PC-03 | Crítico NFS-e · 07/12 | Homologar pacote/importador/retorno Domínio, incluindo `infNFSe/valores/acum` | Q-39; proprietário + contador piloto + técnico Domínio | Amostra importada e conferida no ERP; protocolo/quantidades/rejeições vinculados ao pacote |
| PC-04 | Crítico NFS-e · 07/12 | Piloto fiscal independente; medir precisão, cobertura e esforço da revisão | PC-02/03; D-73/D-189; contador + proprietário | 200 itens revisados, integridade e precisão aprovadas; ambiguidades com tratamento e decisão humana preservada |
| PC-05 | Crítico NFS-e · 07/12 | Provar ciclo A1/coleta/paginação/NSU/pausa/renovação/rede/worker | Ambiente autorizado existente; desenvolvimento + operações | Sem perda/duplicidade/empresa errada; cobertura declarada e retomada D-73 medida |
| PC-06 | Crítico comercial · 02/12 | E-mail de cadastro/convite/recuperação e recuperação administrativa MFA | Brevo já decidido; Q-29 remanescente; operações | Entrega real autorizada, expiração/reuso/falha, recuperação segura; preservar D-183/192 |
| PC-07 | Crítico comercial · 10 | Contrato/medidor/fatura/telas conforme capacidade e custos de D-109 | Proprietário define somente valores ausentes; desenvolvimento reconcilia | Snapshot explicável, usuários/raízes/IA/Integra corretos; manual e automático separados |
| PC-08 | Crítico comercial · 10/12 | Orquestração Asaas e ponte de pagamento para acesso | PC-07, sandbox/acesso seguro; regras D-79 aplicáveis | Emissão única, prorata, carência, reativação, estorno, disputa, eventos repetidos/fora de ordem sem regressão |
| PC-09 | Crítico operacional · 01/12 | Runbook atual e exercício de restauração/rollback completo | Neon, objetos, chaves e bancos default/knowledge; operações | Restore conferido até 4h, RPO registrado, rollback ensaiado, procedimentos por operador/substituto |
| PC-10 | Alto · 01/12 | Saúde de fontes/filas/worker/Beat, alarmes e ensaio de volume | Desenvolvimento + operações; orçamento antes de escalar | Backlog e falha detectados, alerta acionável, tempo D-73; testar cold start e consumo sem wake-up artificial |
| PC-11 | Alto · 02/11 | Onboarding por contratação/papel até primeiro resultado, com predicados verdadeiros | A-05; desenvolvimento + responsável operacional | Vazio/independente/NFS-e/local/Web alcançam resultado sem falso passo concluído ou link proibido |
| PC-12 | Alto · 11 | Biblioteca real de modelos e cobertura empresa/área/competência | Proprietário/contador define rotina, prazo e prova; código já existe | Toda rotina do piloto tem dono, aplicabilidade e requisito; ausência de configuração nunca parece fechamento |
| PC-13 | Alto · 11 | Ampliar recorrência: competência×vencimento, calendário, exceção e prazo auditável | Proposta a fechar com rotinas de PC-12; desenvolvimento | Mensal/sob demanda preservados; casos reais fora de 1–28/mesmo mês cobertos; mudança mantém trilha |
| PC-14 | Alto · 11 | Handoffs, revisão/devolução e ausência do responsável onde necessários | Proposta; gestor define casos e poderes | Trabalho mantém responsável atual, histórico e condições de conclusão; sem ampliação de carteira |
| PC-15 | Crítico Triagem · 06/05 | Encadear e-mail→scan→extração/classificação→revisão→arquivo→checklist | A-02; Q-12–25/31 remanescentes; desenvolvimento + contador | E-mail chega ao resultado sem manipulação técnica; falhas, ambiguidades e duplicatas recuperáveis |
| PC-16 | Crítico Triagem · 06/11 | Prévia segura, correção de empresa/tipo/período/nome e destino verificável | A-01; desenvolvimento | Operador confere e corrige antes de aprovar; sem empresa tem saída; quarentena continua protegida |
| PC-17 | Crítico integração · 03/12 | Piloto de instalação .NET/Domínio/backup/arquivo em máquina limpa | Recursos existentes e escopo de máquina/dados confirmado em Q-28/Q-31; técnico + desenvolvimento | Instala, pareia, lê, atualiza, revoga e retoma; arquivo final e hash conferidos; sem escrita no ERP |
| PC-18 | Crítico Integra · 08/10/12 | Inventariar operações/transmissões já assumidas na etapa 08, implementar lacunas autorizadas e homologar DTE/DCTFWeb/PARCSN | Contrato/documentação por operação, aprovação ligada ao conteúdo, Serpro/representação/consumo; D-149/Q-40; não ampliar Q-36 | Protocolo/documento/custo coerentes; ciência e transmissão separadas; consulta não prova transmissão; incerto não repete cegamente |
| PC-19 | Crítico Contábil · 09/12 | Conciliação com corpus/layouts/OCR reais e exportação conferida | Q-39 ou Q-33; contador + desenvolvimento | Importar→mapear→revisar→conciliar→exportar→conferir destino; erro e reversão preservam prova |
| PC-20 | Alto · 09/11/12 | Folha/DRE/caixa: importação guiada, mapas, fotografia e resultado real | Amostras ERP/arquivos autorizadas; contador | Totais reconciliados; diferença explicável; cenário separado do realizado; fonte/período visíveis |
| PC-21 | Crítico relatórios · 05/09/12 | Renderer Node em operação, fila/download/retry e histórico recuperável | PC-20 conforme relatório; ambiente/segredo/rotação | PDF/XLSX publicados, íntegros, vinculados à fotografia; revogação e job interrompido seguros |
| PC-22 | Crítico IA · 05/12 | Corpus/egressão/custo, avaliação independente, fontes e resposta insuficiente | Q-08/09/11/34; proprietário + curador + desenvolvimento | Amostra/qualidade aprovadas; custo/isolamento; sem fonte não inventa; anexo não instrui execução indevida |
| PC-23 | Crítico aprendizado · 05/11 | Curadoria com correção, fonte, revisão, fila/histórico e entrada visível | A-03; curador definido em Q-34 | Feedback chega a exemplo editável; incompleto não aprova; exemplo/treino/avaliação/publicação separados |
| PC-24 | Alto · 09/12 | Radar com cobertura declarada, coleta/frescor/alteração de fonte e análise humana | Fonte oficial + contador; sem cálculo novo | Publicações esperadas detectadas; falha não parece ausência de mudança; empresa/motivo vinculados |
| PC-25 | Crítico Siescon · 04/12 | Contrato, adaptador e capacidades reais de leitura/exportação | Q-33; técnico do fornecedor + desenvolvimento | Empresas/contas/dados conferem; exportação importada; matriz Domínio/Siescon explícita |
| PC-26 | Alto · 02/11 | Equipe em carteira extensa, papéis explicados, console e erros recuperáveis | A-07/A-09; desenvolvimento | Atribuir/revogar sem seleção ambígua; contexto preservado no erro; busca/paginação e suporte auditado |
| PC-27 | Alto · 11 | Linguagem, ajuda contextual e descoberta de relatórios/aprendizado | A-08/A-10; produto + desenvolvimento | Ajuda ensina ação real; termos explicados no ponto; tarefa concluída sem orientação externa |
| PC-28 | Crítico privacidade · 02/12 | Política e execução de retenção/portabilidade/exclusão por artefato | Q-24/29; proprietário + profissional responsável + desenvolvimento | Pedido chega à execução rastreável; objetos/backups/chaves tratados sem apagar obrigação de guarda por inferência |
| PC-29 | Alto · 11/12 | Rodadas de usabilidade com contadores e regressão por papel/estado | Cenários da auditoria, amostra autorizada | Sucesso/tempo/dúvida/erro registrados; corrigir bloqueios e repetir só percursos afetados |
| PC-30 | Crítico liberação · 12 | Dossiê por módulo, oferta coerente, manual/suporte e aceite | Todos os pacotes aplicáveis à liberação | Nenhuma promessa sem prova; proprietário assina matriz de capacidades e limitações |
| PC-31 | Posterior · 13 | Treino/avaliação/capacidade da IA na máquina definitiva | Hardware/modelo/curadoria; D-50/51 | Qualidade e isolamento medidos; migração aprovada com rollback; API só como reserva autorizada |

### Ondas e caminho crítico

**Onda 1 — verdade do produto e correções imediatas:** PC-01/02; especificar PC-11/16/23/26.
Saída: lista de capacidades confiável e defeitos delimitados. Pesquisa atual A-14 já justifica
corrigir métricas NFS-e; não esperar outro redesenho para fazê-lo.

**Onda 2 — primeira liberação NFS-e:** PC-03/04/05, com PC-06/09/10 e condições contratuais
aplicáveis de PC-07/08/28/30. Caminho crítico: contrato de importação Q-39 → pacote de prova →
importação/retorno no Domínio → amostra independente → aceite. Correções locais e preparação
operacional podem seguir em paralelo ao recebimento do material.

**Onda 3 — central e experiência diária:** PC-11/12/13/14/26/27/29. Começar pela operação
independente com provas humanas, depois ligar fontes homologadas. Calendário e handoffs novos
precisam ser especificados a partir das rotinas reais, não de regras fiscais supostas.

**Onda 4 — completar módulos:** Triagem PC-15/16/17; Contábil PC-19/20/21; Integra PC-18;
IA PC-22/23; Radar PC-24. Trilhas independentes podem ser paralelas. PC-25 avança quando Q-33
for atendida, sem bloquear correções de outros módulos.

**Onda 5 — homologação integrada e suíte:** repetir PC-09/10/28/29 nos módulos efetivamente
incluídos, concluir PC-30 para a suíte. Executar competência representativa de ponta a ponta,
inclusive novos documentos após conclusão, revogação e fonte indisponível. Não fechar etapas
com pendências nem substituir amostra real por demonstração.

**Onda 6 — IA definitiva e expansões aprovadas:** PC-31 e oportunidades escolhidas abaixo.
Não colocar treinamento local como bloqueio da liberação por API já decidida.

## Evoluções propostas, separadas da dívida de conclusão

| Proposta | Valor para o usuário | Prioridade recomendada / decisão necessária |
|---|---|---|
| Notificações internas de prazo, atribuição e falha | Perceber trabalho novo sem percorrer módulos | **Aprovada em D-277** (só no produto, deduplicada); canal externo continua separado |
| Documento esperado e pendência com responsável | Saber exatamente o que falta e quem acompanha | Parte do fechamento/Triagem; concluir checklist existente antes de abrir novo canal |
| Visões salvas e busca global | Reencontrar empresa, tarefa, nota e protocolo | Busca global **aprovada em D-277**, limitada à carteira/módulos; visões salvas continuam proposta |
| Portal de solicitação/entrega do cliente | Reduzir troca dispersa e confirmar recebimento | Validar demanda/canal/identidade/retenção; nova proposta, sem reativar Jornadas automaticamente |
| Colaboração com comentário/menção | Passar contexto e devolver trabalho | Implementar somente o mínimo comprovado por PC-14/29; comentário não substitui evidência |
| Indicadores de operação do escritório | Medir atraso, tempo de ciclo e gargalos | Medir processo e qualidade; não transformar tarefas atribuídas em ranking de pessoas |

Decisões de expansão serão registradas em DECISOES.md antes de comportamento dependente. Nenhum
envio de e-mail/WhatsApp ou ação oficial é autorizado pela existência destas propostas.

## Dependências do responsável: pedir somente o que destrava a próxima entrega

| ID existente | O que ainda é necessário | Recomendação e como fornecer | Trabalho que pode seguir |
|---|---|---|---|
| Q-39 / D-274 | Importador/versão e retorno de importação efetiva; o contrato `acum` já tem evidência | Técnico/contador executa amostra descartável em ambiente autorizado e fornece retorno pelo canal seguro | PC-02, preparo do pacote, critérios de conferência e recuperação |
| Q-33 | Versão/schema/mecanismo Siescon, identificadores e layout suportado | Sessão técnica e amostras autorizadas; nunca credenciais no chat | Outras integrações e recusa segura atual |
| D-109 / Q-08 / D-149 | Valores ausentes do modelo vigente, limites IA e adicional de reemissão | Apresentar tabela concreta de operação/preço/limite, com custo auditável; registrar escolha antes de cobrar | Orquestração local/sandbox e testes das regras já decididas |
| Q-40 | Efeito de PDF válido na atividade de emissão | Recomenda-se emissão, conferência e pagamento separados; solicitar resposta antes da transição dependente | Consulta/armazenamento/trilha sem conclusão automática presumida |
| Q-12–25 / Q-31 | Somente políticas documentais ainda sem definição após D-76/D-109 e amostras/destinos reais | Levar catálogo e cenários concretos para conferência; não repetir perguntas já aprovadas genericamente | Encadeamento local, prévia/editor e diagnóstico com dados sintéticos |
| Q-09/11/34 | Política de dados externos, governança de chave e curador | Matriz de dados/mascaramento/retenção e papel de aprovação; canal protegido | Curadoria local e avaliação sem egressão |
| Q-28/29 | Acessos específicos, remetente/entrega, termos/privacidade aplicáveis | Reusar ambientes existentes; pedir apenas acesso/amostra do conector em execução | Templates, runbooks e testes locais |
| Q-35 | Equipamento/modelo da IA definitiva | Inspecionar equipamento quando disponível; SaaS Fly+Neon não deve ser perguntado de novo | Operação por API e pipeline já aprovado |
| D-169 + D-03 + Q-33 | Reconciliação de promessa Siescon com ausência de homologação | Homologar ou delimitar disponibilidade na oferta/contrato por decisão explícita | Auditoria de capacidades; não alterar copy comercial por inferência |

Custos incrementais seguem a autorização global vigente: abaixo de US$ 1,00 estão preautorizados
no escopo; a partir do limite ou sem estimativa razoável, confirmação específica imediatamente
antes. Pesquisa, documentação e testes locais não precisam dessa confirmação. Autorizações
anteriores de dados/custo/publicação não são ampliadas pelo novo plano.

## Matriz de validação da conclusão

Cada pacote deve anexar casos de tarefa, estado, permissão, resultado e recuperação. Para UI,
seguir ui-ux-pro-max, Watermelon, referências reais, Web Interface Guidelines atuais e Playwright
MCP; fechar todas as sessões abertas. Reaproveitar evidência válida sem presumir que uma alteração
posterior mantém todos os aceites. Testes de implementação não substituem observação do usuário.

| Dimensão | Cobertura obrigatória na liberação afetada |
|---|---|
| Papéis | Dono/admin, gestor, operador, auditor, financeiro, suporte leitura/escrita autorizada |
| Carteira | Vazia, pequena, extensa, homônimos, matriz/filial, pausada, vínculo revogado e outro escritório |
| Ciclo | Primeiro uso, operação normal, competência seguinte, reabertura, alteração de fonte e saída do cliente |
| Falhas | Entrada inválida, lote parcial, rede/worker/agente indisponível, timeout, resultado incerto, duplicata e retry |
| Interface | Desktop/mobile/paisagem, teclado, foco, zoom, temas, movimento reduzido, loading/erro/vazio e console |
| Segurança | Autorização revalidada em job/download, arquivo inseguro bloqueado, segredos protegidos, IA isolada |
| Operação | Banco e objetos restaurados, readiness monitorada, backlog/certificado/fonte alertados, rollback e suporte |
| Comercial | Contrato/consumo/fatura/acesso coerentes, manual separado, mudanças no ciclo correto e custo transparente |

Proposta de teste de usabilidade: rodada exploratória de 5–8 participantes cobrindo papéis, com
cenários objetivos e sem instrução de clique. Medir sucesso, tempo, erro e pedido de ajuda.
Metas iniciais propostas, a calibrar: 90% das tarefas prioritárias sem ajuda, próxima ação em até
um minuto, zero confusão observada entre download/importação, emissão/pagamento e resumo/ciência.
Não são resultados já obtidos nem substituem D-73. Roteiro completo na auditoria vinculada.

## Próxima execução preparada

**Recomendação:** executar PC-01/02 primeiro, concluir especificação do ciclo Q-39 em paralelo
e manter a primeira liberação NFS-e como prioridade. Não iniciar implementação nesta entrega
de planejamento. O prompt abaixo fica preparado para a próxima autorização:

> Leia a revisão vigente de PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e a auditoria de
> 05/10/2026. Execute PC-01 e PC-02 nas etapas 00/07/11: reconcilie a matriz de capacidades e
> corrija o escopo dos indicadores/links NFS-e para concordar com a lista e seus filtros,
> preservando decisões da sessão demo. Não altere regras fiscais ou comerciais. Teste dois
> meses, duas empresas, classificação, relatórios, links e paginação; aplique o fluxo UI obrigatório,
> registre evidências e bloqueios, feche o navegador e preserve as alterações locais existentes.
> Prepare o material mínimo para Q-39 sem presumir importação homologada ou autorização de deploy.

## Histórico do plano e das entregas anteriores

Os registros a seguir preservam datas, decisões e evidências anteriores. Para prioridade e estado
atual, usar a revisão acima e as decisões posteriores aplicáveis, não um cabeçalho histórico isolado.

﻿
**Atualizacao V-205:** `cicacontabil.com.br` e `www.cicacontabil.com.br` foram registrados como hostnames definitivos em D-179. O A legado da HostGator foi removido; os nameservers autoritativos e os resolvedores 1.1.1.1/8.8.8.8 passaram a retornar somente o Fly. Certificados RSA/ECDSA foram emitidos para os dois hostnames, Django recebeu `ALLOWED_HOSTS` e origens CSRF explicitos, e o health permaneceu passing. O Windows ainda conservava o IP antigo pelo TTL anterior; apos limpar o cache DNS, apex e `www` responderam 200 pelo IP correto, com TLS valido, em todas as tentativas.
**Atualização V-245:** o 403 técnico ao trocar aparência foi confirmado nos logs como token CSRF antigo após renovação de login, não falha de domínio. O seletor atualiza o token antes do POST sem relaxar cookie `HttpOnly` ou middleware; rejeições residuais recebem recuperação CICA com retorno seguro e APIs preservam JSON. Release Fly 34 publicada e validada no domínio real com token adulterado: refresh 200, POST 302, tema aplicado; fallback 403 responsivo, liveness/readiness 200 e banco/cache `ok`.

**Atualização V-247:** a página inicial foi recomposta como superfície de decisão: contexto e próxima ação no topo, escopos explicados, filtros de prioridade acionáveis, agenda de dez itens com prazo relativo/exato e somente exceções úteis. Responsável deixa de se repetir em Meu trabalho; fechamentos ficam recolhidos e preservam estado na URL. Pesquisa em padrões de Linear, Asana, Karbon e Process Street, auditoria integral das Web Interface Guidelines e Playwright desktop/mobile/escuro cobriram os estados principais. Regressão integral: 1.047 testes e 139 subtestes aprovados, seis skips explícitos. Release Fly 37 publicada por overlay de quatro arquivos; web/worker/health saudáveis e demo real confirmou a nova estrutura. Detalhes e limites em V-247.

**Atualização V-248:** a reauditoria da NFS-e confirmou em produção a descoberta, seleção e os downloads em lote e corrigiu o defeito real do pacote: pastas agora incluem código e nome seguro da empresa, refletidos também no manifesto. A legibilidade mobile foi elevada sem mudar regras fiscais. Playwright local/publicado cobriu seleção, filtros, vazio, loading, erro de rede, temas, responsividade e ZIPs emitidas/tomadas. Regressão integral: 1.048 testes e 139 subtestes aprovados, seis skips. Release Fly 38 publicada por overlay de quatro arquivos; web/worker/health e readiness saudáveis. Q-39 e a homologação Domínio permanecem abertos. Detalhes em V-248.

**Atualização V-254:** a Central NFS-e agora gera PDF e XLSX do recorte filtrado com entrada/saída, dados de conferência e ISS, PIS, COFINS, CSLL, IRRF e INSS separados. O total usa somente retenções explícitas, o Excel neutraliza fórmula injetada e ambos respeitam carteira/permissão com limite de 5.000 notas. PDF, XLSX, filtros e interface desktop/mobile foram validados localmente. A publicação, amostra fiscal real e homologação Domínio Q-39 continuam pendentes.

**Atualização V-265:** a entrega de retenções foi revalidada ponta a ponta contra o HubCobalchini: impostos ficam visíveis por nota, PDF e Excel `.xlsx` usam o filtro atual e os seis tributos permanecem separados. O detalhamento ganhou alvo de 44 px e texto maior. Downloads reais, três páginas do PDF, estrutura/fórmulas da planilha, desktop/mobile, vazio, teclado, tema escuro, movimento reduzido, overflow e console foram conferidos localmente. A suíte integral aprovou 568 testes, com um skip explícito. Restam somente amostra fiscal real autorizada e Q-39; não houve publicação.

**Atualização V-266:** Guias e DCTFWeb foram reorganizadas como uma fila contábil orientada ao próximo passo. Apurações locais levam à consulta individual ou em lote, guias oficiais mostram uma ação principal por estado e documentos exibem progresso por nome, sem chaves de serviço. Erros brutos do Domínio/Serpro ficam nos logs; a interface oferece orientação segura e referência recolhida para suporte. Resultado incerto continua sem repetição. Desktop/mobile, lote, vazio, falha, incerteza, teclado, modal, PDF fictício, tema, overflow e console foram validados localmente; não houve Serpro, custo ou publicação. D-149/Q-40 e homologação real permanecem abertos.

**Atualização V-255:** a empresa pausada preserva o histórico NFS-e para proprietários/administradores sem carteira restrita, mas permanece fora da carteira operacional e sem coleta ou classificação. A tela agora identifica o modo de consulta, mantém downloads/relatórios, remove a falsa promessa “Classificar” e não conta revisão aberta legada como pendência quando a nota já possui acumulador. Perfis com carteira explícita continuam sem acesso; validação local desktop/mobile e permissões concluída, sem publicação ou fonte fiscal.

**Atualizacao V-204:** apos uma captura com `ERR_CONNECTION_RESET`, a producao Fly.io foi revalidada sem mutacao. Web e worker permaneciam iniciados; o health check estava passing; pagina inicial e prontidao responderam 200; banco e cache estavam ok; DNS, TCP/443, TLS e redirecionamento HTTP para HTTPS passaram. Vinte requisicoes consecutivas a pagina inicial retornaram 200 em 62–196 ms, sem reinicio, OOM ou erro da aplicacao nos logs disponiveis. A falha observada foi transitoria e nao foi reproduzida; nenhum restart ou redeploy foi executado. A inspecao visual por navegador ficou indisponivel porque a sessao nao ofereceu browser.

**Atualizacao V-140:** proprietario e administrador agora veem a distribuicao de atividades abertas por membro ativo, com atrasadas e impedidas separadas e link para cada carteira individual. Tambem podem abrir diretamente o recorte sem responsavel. Essa superficie descreve atribuicao e excecoes atuais, sem pontuacao de produtividade. Foram aprovados 81 testes focados, Ruff, MyPy, Django, migracoes e regressao integral com 863 testes, 2 ignorados e 11 subtestes em 79,33 s. A inspecao visual permanece pendente porque o Playwright MCP retornou `Transport closed` antes de abrir uma aba.

**Atualizacao V-139:** a area de trabalho agora resume todas as atividades abertas do escopo autorizado por atraso, hoje, proximos sete dias, impedimento e fonte indisponivel. Cada indicador abre o recorte correspondente na central e os estados continuam independentes. O resumo de atraso deixou de contar somente as seis linhas exibidas. A ficha de atividades ganhou filtro de atualizacao da fonte; filtros e paginacao preservam o contexto. Foram aprovados 80 testes focados, Ruff, MyPy, Django, migracoes e regressao integral com 862 testes, 2 ignorados e 11 subtestes em 81,47 s. A inspecao visual permanece pendente porque o Playwright MCP retornou `Transport closed` antes de abrir uma aba.

**Atualizacao V-138:** uma divergencia de folha agora leva para a fila de atividades da mesma empresa, competencia e area, por URL verificavel. A fila ganhou filtro mensal que preserva todos os filtros na paginacao e recusa competencia invalida sem modificar o recorte. Nenhuma atividade e encerrada ou atribuida automaticamente. Foram aprovados 79 testes focados, Ruff, MyPy, Django, migracoes e regressao integral com 861 testes, 2 ignorados e 11 subtestes em 92,53 s. A inspecao visual permanece pendente porque o Playwright MCP retornou `Transport closed` antes de abrir uma aba.

**Atualizacao V-137:** a ficha da empresa agora compara duas fotografias agregadas da folha para a mesma competencia, expondo fonte, valores ausentes e diferencas acima da tolerancia escolhida. A comparacao nao calcula folha, nao mostra trabalhador individual e nao consulta fonte externa. A tabela se adapta ao celular e o envio informa `Comparando...` durante a navegacao. Foram aprovados 72 testes focados, Ruff, MyPy, Django, migracoes e regressao integral com 861 testes, 2 ignorados e 11 subtestes em 80,06 s. A auditoria pelas Web Interface Guidelines nao encontrou violacao material apos o ajuste de responsividade. A inspecao visual permanece pendente porque o Playwright MCP retornou `Transport closed` antes de abrir uma aba.

**Atualizacao V-136:** a exportacao PDF/XLSX do Copiloto passou a usar exclusivamente o servico Node/TypeScript de relatorios. A fotografia, a permissao, o hash e a auditoria persistida continuam no Django; URL ou segredo ausente agora retornam indisponibilidade explicita, sem fallback ReportLab/OpenPyXL. Foram aprovados 21 testes focados, 8 testes Node, Ruff, MyPy, Django e migracoes; a regressao integral aprovou 860 testes, ignorou 2 e executou 11 subtestes em 82,24 s. A configuracao e homologacao do renderizador interno em ambiente publicado permanecem na etapa 12.

**Atualizacao V-135:** o editor visual do mapa DRE permite que proprietario ou administrador configure conta, grupo e sinal. O salvamento valida o conjunto inteiro, cria uma versao completa e imutavel, desativa apenas a versao anterior e registra auditoria. Os registros anteriores continuam disponiveis. Foram aprovados 70 testes focados, Ruff, MyPy, Django, migracoes e a regressao integral com 860 testes, 2 ignorados e 11 subtestes em 82,86 s. A revisao pelas Web Interface Guidelines nao encontrou violacao material. A inspecao visual desktop/mobile permanece pendente por `Transport closed` no Playwright MCP.

**Atualizacao V-134:** exportacoes financeiras DRE/caixa agora entram em fila Celery duravel com fotografia criptografada, hash, lease, recuperacao e arquivo privado. O worker e o download revalidam o acesso atual a empresa. Cinco testes focados, Ruff, MyPy, Django e migracoes passaram; a regressao integral aprovou 858 testes, ignorou 2 e executou 11 subtestes em 86,79 s. A inspe??o Playwright permanece pendente por `Transport closed`.

**Atualizacao V-133:** o renderizador Node aceita durante rotacao o segredo ativo e o anterior, enquanto Django transmite exclusivamente o ativo. A sequencia de revogacao foi documentada; TypeScript, 8 testes Node, 6 testes Django, Ruff e MyPy passaram; a regressao integral aprovou 855 testes e ignorou 2 em 82,28 s. A fila Celery de relatorios permanece pendente.

**Atualizacao V-132:** uma assinatura explicitamente limitada ao NFS-e passa a abrir sua central, sem navegacao ou URLs de atividades e modelos operacionais. Empresas, certificados, equipe e configuracao inicial permanecem como apoio do proprio fluxo. Ruff, MyPy e 80 testes de workspace/navegacao passaram; a regressao integral aprovou 854 testes e ignorou 2 em 79,79 s; a inspecao visual desktop/mobile continua pendente porque o Playwright MCP retorna `Transport closed`.

**Atualizacao V-131:** acumulador incluido manualmente sem criterio explicito deixou de atuar como classificador curinga: permanece no catalogo e no historico, enquanto NFS-e sem correspondencia segue para revisao humana. A validacao focal aprovou 94 testes, Ruff e MyPy; a regressao integral aprovou 852 testes e ignorou 2 em 76,03 s. A inspecao visual permanece pendente pelo transporte Playwright MCP indisponivel.

**Atualizacao V-130:** a carteira de pacotes NFS-e agora pagina todos os registros em vez de limitar silenciosamente aos 100 mais recentes; a prova local usou 101 pacotes. Foram aprovados 69 testes focados, Ruff e MyPy. A inspecao visual permanece pendente pelo transporte Playwright MCP indisponivel.

**Atualizacao V-128:** a pesquisa oficial do DomÃ­nio confirmou rotinas automaticas, mas nao publicou schema `.dom` ou contrato de XML NFS-e/acumuladores. Por D-112 e Q-39, o ZIP NFS-e passou a ser explicitamente pacote privado de conferencia; a interface e a rota bloqueiam confirmacao de importacao ate o layout e retorno serem homologados. Foram aprovados 68 testes focados, Ruff e MyPy. Nenhuma fonte ou rotina real foi acionada.

**Atualizacao V-127:** o historico NFS-e de acumuladores tornou-se um livro imutavel unico para fotografia DomÃ­nio Web, cadastro manual e decisao humana, com empresa, codigo, origem e instante preservados e exibicao paginada. Os 70 testes focados passaram, com Ruff, MyPy e migracoes limpas. A auditoria manual de interface nao encontrou violacao material; a repeticao visual desktop/mobile continua pendente pela indisponibilidade do transporte Playwright MCP. Nenhuma fonte ou rotina real foi acionada.

**Atualizacao V-126:** NFS-e passou a registrar o catalogo da fotografia unica do backup Dom?nio Web por empresa e lote, permitir acumuladores cadastrados pela interface e preservar a decisao humana no historico. A baixa gera ZIP privado com manifesto, hash e estados auditaveis distintos para geracao, download e confirmacao humana de importacao. Arquivo privado ausente nao avanca estado nem gera erro interno. Foram aprovados 68 testes focados, regressao integral com 851 aprovados e 2 ignorados, Ruff, MyPy e verificacao de migracoes. A interface desktop de Exportacoes foi inspecionada por Playwright; a repeticao do fluxo de download e da visao mobile ficou pendente porque o transporte MCP foi encerrado durante a validacao. Nao houve backup real, leitura de banco Dom?nio, rotina Windows, chamada externa ou homologacao de importacao.
# CICA â€” plano mestre de conclusÃ£o e preparaÃ§Ã£o para venda

Atualizado em 21/09/2026. Plano aprovado pelo responsÃ¡vel nesta conversa; localizaÃ§Ã£o na raiz conforme D-59.

**Atualização V-256:** o CICA agora tem recuperação global própria para 400, 403, 404 e 500,
com status HTTP real, próximo passo, resposta neutra que não enumera recursos protegidos e JSON
preservado em `/api/`. Erros não ficam em cache nem expõem detalhes internos; o 500 possui fallback
independente de template, banco e reversão de URL. Playwright validou desktop/mobile, temas,
teclado, foco e retorno ao início; a regressão integral aprovou 1.075 testes e 139 subtestes, com
seis skips explícitos. Implementação local, sem publicação.

**Atualização V-257:** a Conciliação não-demo agora coloca importações interrompidas antes das
métricas, explica o próximo passo sem refletir exceções e oferece somente ações aplicáveis ao
estado. Salvar layout sem execução elegível deixou de prometer processamento iniciado. Mapeamento e
processamentos ganharam alvos de 44 px e cartões legíveis no celular. Playwright validou falha,
mapeamento, erro, desktop/mobile, temas, teclado, foco e console; a regressão integral aprovou 1.077
testes e 139 subtestes, com seis skips. Exportação Domínio continua bloqueada por Q-39.

**Atualização V-258:** a revisão individual da Conciliação agora informa o próximo passo pelo estado,
preserva a data no campo nativo, foca e vincula erros e só oferece gerar lançamento quando os dados
estão completos. Exportações prontas podem ser baixadas com integridade revalidada e, após Q-39 ser
habilitada, confirmadas explicitamente por hash, pessoa e instante; confirmação repetida é idempotente
e arquivo adulterado é recusado. O histórico ficou legível no celular e protege envios duplicados.
Playwright validou desktop/mobile, escuro, movimento reduzido, erro, foco, confirmação e console; a
regressão integral aprovou 1.080 testes e 145 subtestes, com seis skips. Sem deploy; Q-39 continua
bloqueando geração e confirmação reais no Domínio.

**Atualização V-259:** a configuração da Conciliação deixou de afirmar que uma empresa sem contas
estava pronta e passou a separar conta contábil essencial, conta financeira para extratos, proteção
opcional de períodos e automação opcional. Há uma próxima ação única, formulários sob demanda,
deep-link, proteção contra perda de edição, retorno à seção afetada e seis listas paginadas. Erros
permanecem abertos e focados; auditor com carteira autorizada consulta sem controles de escrita.
Playwright validou desktop/mobile, escuro, movimento reduzido, teclado, foco, erro, URL, alvos e
console. Regressão integral: 1.082 testes e 145 subtestes aprovados, seis skips. Implementação local,
sem publicação e sem alterar Q-39.

**Atualização V-260:** a auditoria da Conciliação deixou de expor códigos como conteúdo principal e
passou a apresentar atividade, contexto, responsável, instante, registro afetado e resultado em uma
linha do tempo investigável. Busca, atividade, resultado e período são combináveis e persistidos na
URL; filtro inválido não amplia a consulta. Metadados usam lista segura, referências técnicas ficam
recolhidas e a paginação caiu para 50 eventos. Playwright validou desktop/mobile escuro, movimento
reduzido, teclado, foco de erro, detalhe, filtros, alvos, overflow e console. Regressão integral:
1.083 testes e 145 subtestes aprovados, seis skips. Implementação local, sem ampliar permissão,
retenção, exportação ou Q-39.

**Atualização V-215:** a central de certificados agora aceita arrastar ou selecionar um ou vários arquivos `.pfx`/`.p12`, identifica o CNPJ pela extensão oficial ICP-Brasil do certificado e correlaciona exatamente a empresa acessível. A importação em lote admite senha comum ou convenções explícitas no nome do arquivo, sem IA nem envio externo; falhas e ambiguidades ficam como não reconhecidas e não são persistidas. A entrega foi validada localmente e não ativa coleta ADN nem constitui homologação fiscal.

**SituaÃ§Ã£o em 21/09/2026:** etapas 00, 01, 02 e 03 concluÃ­das no nÃ­vel de implementaÃ§Ã£o e validaÃ§Ã£o local. A etapa 04 estÃ¡ em andamento e bloqueada pelo contrato tÃ©cnico Siescon de Q-33; a base de exportaÃ§Ã£o comum jÃ¡ recusa Siescon atÃ© existir adaptador/layout revisados. V-041 revalidou o checkout, o bloqueio explÃ­cito e a documentaÃ§Ã£o, sem criar conexÃ£o ou arquivo Siescon; tambÃ©m confirmou que `main` e `origin/main` estavam no mesmo commit antes desta entrega. V-042 avanÃ§ou localmente a etapa 05: o manifesto de treino/avaliaÃ§Ã£o agora recusa identificadores pessoais antes de gravar artefato e nÃ£o sobrescreve artefato existente, preservando revisÃ£o humana. V-043 eliminou a dÃ­vida de tipagem encontrada nos mÃ³dulos envolvidos; V-044â€“V-068 reduziram a dÃ­vida global de 535 ocorrÃªncias para **zero nos 190 arquivos verificados por MyPy**, incluindo Triagem, Hub, contrataÃ§Ã£o, PARCSN, transporte local, livros de consumo, coletores, configuraÃ§Ã£o, gateway de IA, relatÃ³rios, sincronizaÃ§Ã£o bancÃ¡ria, seguranÃ§a, acesso DTE, operaÃ§Ãµes, NFS-e e IA, sem mudar regra de negÃ³cio. V-063 reexecutou a regressÃ£o integral local com 762 testes aprovados; V-073 a repetiu com 763 testes aprovados apÃ³s completar a revisÃ£o e a carteira NFS-e; V-074 a atualizou para 764 apÃ³s paginar a carteira de Guias/DCTFWeb; V-075 a atualizou para 765 apÃ³s paginar a carteira de Parcelamentos por lote autorizado; V-076 a atualizou para 766 apÃ³s paginar a fila OFX Ã— DomÃ­nio; V-077 a atualizou para 767 apÃ³s paginar o histÃ³rico operacional de Parcelamentos; V-078 a atualizou para 768 apÃ³s paginar a cobertura de certificados. V-072 comprovou por teste o contrato do runtime OpenAI-compatÃ­vel privado e que uma resposta local impede egressÃ£o, mesmo com fallback configurado; sem opt-in, o fallback permanece negado e auditado. V-073 completou o detalhe de revisÃ£o NFS-e, a demonstraÃ§Ã£o fictÃ­cia e a paginaÃ§Ã£o da carteira sem corte silencioso. V-074 estendeu essa proteÃ§Ã£o Ã  carteira de Guias/DCTFWeb, V-075 Ã  carteira de Parcelamentos, cuja pÃ¡gina de 30 registros coincide com seu limite de consulta em lote, V-076 Ã  fila de ConciliaÃ§Ã£o, V-077 ao histÃ³rico de operaÃ§Ãµes e V-078 Ã  cobertura de empresas sem A1 vÃ¡lido. As etapas 05â€“10 confirmaram controles locais prÃ³prios; na 10, V-040 acrescentou o contrato de requisiÃ§Ã£o do cliente Asaas sem conexÃ£o ou chave. V-069â€“V-071 ampliaram a inspeÃ§Ã£o visual local da etapa 11 para home, cadastro, demonstraÃ§Ã£o isolada, Triagem, revisÃ£o NFS-e, mÃ³dulos operacionais e Copiloto fictÃ­cios, sem homologar jornada real. As homologaÃ§Ãµes de caixas/antimalware/destino, ADN, Serpro, arquivos/ERPs/fontes do Radar e Asaas permanecem pendentes. Por D-87, toda dependÃªncia de site em produÃ§Ã£o fica concentrada na etapa 12; isso inclui SMTP/DNS, pareamento HTTPS/mTLS, rede, atualizaÃ§Ã£o distribuÃ­da, backup DomÃ­nio Web e escrita Windows definitiva. A demonstraÃ§Ã£o NFS-e foi ajustada separadamente e nÃ£o conclui a etapa 07. EvidÃªncias em [VALIDACOES.md](VALIDACOES.md).

**AtualizaÃ§Ã£o V-079:** a ficha da empresa passou a paginar seus histÃ³ricos NFS-e, revisÃµes e DTE em seÃ§Ãµes independentes, e a regressÃ£o integral local alcanÃ§ou 769 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ homologaÃ§Ã£o ADN ou Serpro.

**AtualizaÃ§Ã£o V-080:** a auditoria de conciliaÃ§Ã£o passou a paginar seus eventos sem limite silencioso, mantendo a aÃ§Ã£o filtrada entre pÃ¡ginas; a regressÃ£o integral local alcanÃ§ou 770 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ homologaÃ§Ã£o de ERP, OFX ou exportaÃ§Ã£o.

**AtualizaÃ§Ã£o V-081:** o Radar da Reforma passou a paginar alertas sem limite silencioso, mantendo termo, fonte e tema; a regressÃ£o integral local alcanÃ§ou 771 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ homologaÃ§Ã£o de fontes ou coleta.

**AtualizaÃ§Ã£o V-082:** o console da plataforma passou a paginar o histÃ³rico manual de faturas sem limite silencioso; a regressÃ£o integral local alcanÃ§ou 772 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ homologaÃ§Ã£o de cobranÃ§a ou Asaas.

**AtualizaÃ§Ã£o V-083:** a Caixa DTE passou a paginar seu histÃ³rico de resultados sem interferir na fila de mensagens; a regressÃ£o integral local alcanÃ§ou 773 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ consulta, consumo ou homologaÃ§Ã£o Serpro.

**AtualizaÃ§Ã£o V-084:** o onboarding passou a paginar seu histÃ³rico de importaÃ§Ãµes sem ocultar lotes antigos e sem interferir na fonte ou prÃ©via selecionadas; a regressÃ£o integral local alcanÃ§ou 774 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ upload, backup ou homologaÃ§Ã£o DomÃ­nio.

**AtualizaÃ§Ã£o V-085:** a ConciliaÃ§Ã£o passou a paginar separadamente os histÃ³ricos de processamentos e exportaÃ§Ãµes, sem ocultar registros antigos; a regressÃ£o integral local alcanÃ§ou 775 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ arquivo real, ERP ou homologaÃ§Ã£o de exportaÃ§Ã£o.

**AtualizaÃ§Ã£o V-086:** o Copiloto passou a paginar o histÃ³rico de conversas abertas sem ocultar as antigas, preservando a conversa selecionada; a regressÃ£o integral local alcanÃ§ou 776 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ chamada de IA, curadoria ou homologaÃ§Ã£o operacional.

**AtualizaÃ§Ã£o V-087:** o console da plataforma passou a paginar os fechamentos ainda adiados sem ocultar ocorrÃªncias antigas; a regressÃ£o integral local alcanÃ§ou 777 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ fechamento, cobranÃ§a ou homologaÃ§Ã£o Asaas.

**AtualizaÃ§Ã£o V-088:** o console da plataforma passou a paginar as tentativas Claude incertas sem ocultar protocolos antigos; a regressÃ£o integral local alcanÃ§ou 778 testes aprovados. A evidÃªncia permanece exclusivamente sintÃ©tica; nÃ£o hÃ¡ chamada de IA, custo ou homologaÃ§Ã£o operacional.

**AtualizaÃ§Ã£o V-089:** a revisÃ£o NFS-e passou a recusar acumulador ausente do catÃ¡logo da empresa; a regressÃ£o integral local alcanÃ§ou 779 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ ADN ou homologaÃ§Ã£o fiscal.

**AtualizaÃ§Ã£o V-090:** o detalhe de conciliaÃ§Ã£o passou a paginar todos os candidatos no recorte jÃ¡ existente, sem ocultar os posteriores ao quinquagÃ©simo; a regressÃ£o integral local alcanÃ§ou 780 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ ERP, arquivo ou exportaÃ§Ã£o homologados.

**AtualizaÃ§Ã£o V-091:** o detalhe da Triagem passou a paginar a trilha persistida de eventos sem ocultar evidÃªncia antiga; a regressÃ£o integral local alcanÃ§ou 781 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ caixa, arquivo, agente ou destino homologados.

**AtualizaÃ§Ã£o V-092:** a carteira de movimentos da ConciliaÃ§Ã£o passou a preservar as pÃ¡ginas de Processamentos e ExportaÃ§Ãµes ao navegar, mantendo as trÃªs trilhas independentes; a regressÃ£o integral local manteve 781 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ arquivo, ERP ou exportaÃ§Ã£o homologados.

**AtualizaÃ§Ã£o V-093:** a fila OFX Ã— DomÃ­nio passou a preservar tambÃ©m o contexto das pÃ¡ginas de Processamentos, Movimentos e ExportaÃ§Ãµes; a regressÃ£o integral local manteve 781 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ arquivo, ERP ou exportaÃ§Ã£o homologados.

**AtualizaÃ§Ã£o V-094:** a Caixa DTE passou a preservar simultaneamente a pÃ¡gina das mensagens e a pÃ¡gina do histÃ³rico de consultas; a regressÃ£o integral local manteve 781 testes aprovados. A evidÃªncia permanece sintÃ©tica; nÃ£o hÃ¡ consulta Serpro, consumo ou homologaÃ§Ã£o.

**AtualizaÃ§Ã£o V-095:** Jornadas foi removida do catÃ¡logo efetivo do produto conforme D-43, preservando apenas enum, schema e migraÃ§Ãµes histÃ³ricos; a regressÃ£o integral local manteve 781 testes aprovados. A evidÃªncia Ã© local; nÃ£o hÃ¡ migraÃ§Ã£o de produÃ§Ã£o ou homologaÃ§Ã£o comercial.

**AtualizaÃ§Ã£o V-096:** formulÃ¡rios, views e template operacionais Ã³rfÃ£os de Jornadas foram removidos conforme D-43, preservando enum, modelos, tabelas e migraÃ§Ãµes histÃ³ricas; a regressÃ£o integral local manteve 781 testes aprovados. A evidÃªncia Ã© local; nÃ£o hÃ¡ migraÃ§Ã£o de produÃ§Ã£o ou homologaÃ§Ã£o comercial.

**AtualizaÃ§Ã£o V-097:** a ConciliaÃ§Ã£o passou a rejeitar XLSX corrompido antes de persistir uma fonte, sem transformar falha de leitura em processamento incompleto; a prÃ©via CSV tambÃ©m deixou de materializar todo o arquivo para exibir 50 linhas. A regressÃ£o integral local alcanÃ§ou 783 testes aprovados; a evidÃªncia Ã© local, sem arquivo, ERP ou OCR homologados.

**AtualizaÃ§Ã£o V-098:** a ConciliaÃ§Ã£o passou a rejeitar PDF malformado antes de persistir fonte, lote ou processamento, preservando o caminho de OCR local para PDF digitalizado vÃ¡lido. A regressÃ£o integral local alcanÃ§ou 784 testes aprovados; a evidÃªncia Ã© local, sem OCR, arquivo, ERP ou exportaÃ§Ã£o homologados.

**AtualizaÃ§Ã£o V-099:** a demonstraÃ§Ã£o isolada da ConciliaÃ§Ã£o foi revisada em navegador com base SQLite temporÃ¡ria e dados fictÃ­cios; desktop e celular nÃ£o apresentaram overflow horizontal nem erros de console. NÃ£o houve upload, integraÃ§Ã£o, cobranÃ§a ou homologaÃ§Ã£o.

**AtualizaÃ§Ã£o V-114/V-115:** o renderizador Node/TypeScript passou a gerar e validar localmente SVG, PDF e XLSX com fotografia versionada, pendÃªncias, filtros e hash de saÃ­da. Django usa canal autenticado por segredo compartilhado quando a URL interna Ã© configurada e recusa hash, MIME ou serviÃ§o invÃ¡lido sem fallback. PDF/XLSX continuam fora de produÃ§Ã£o: a auditoria persistida chegou em V-117 e a cadeia ExcelJS foi atualizada em V-119; faltam Celery e rotaÃ§Ã£o do segredo.

**AtualizaÃ§Ã£o V-120:** DRE e caixa ganharam fotografias financeiras persistentes, mapeamento DRE versionado e cenÃ¡rios separados. As pendÃªncias entÃ£o registradas de tela, importaÃ§Ã£o e relatÃ³rios JS foram concluÃ­das em V-121 a V-124; o adaptador DomÃ­nio e sua homologaÃ§Ã£o continuam pendentes.

**AtualizaÃ§Ã£o V-121 a V-124:** a ficha da empresa agora expÃµe DRE e caixa, com exportaÃ§Ã£o PDF/XLSX por `POST`, fotografia e auditoria persistidas. O onboarding importa saldos para DRE, cenÃ¡rios de caixa e mapas DRE versionados; cada arquivo tem prÃ©via, validaÃ§Ã£o integral, proveniÃªncia e proteÃ§Ã£o contra duplicidade ou saldo inicial divergente. A geraÃ§Ã£o local e os fluxos de tela foram verificados; faltam adaptadores DomÃ­nio homologados, fila Celery, rotaÃ§Ã£o do segredo, editor visual do mapa DRE e evidÃªncia de dados reais autorizados.

**AtualizaÃ§Ã£o V-125:** o backup Ãºnico do DomÃ­nio Web passou a aceitar catÃ¡logo de acumuladores por uma capacidade explicitamente permitida do agente. Cada acumulador normalizado preserva fonte, lote, empresa e data da fotografia e pode ser usado somente na revisÃ£o NFS-e da empresa correspondente. O leitor real do backup, o layout de saÃ­da para rotina automÃ¡tica e a confirmaÃ§Ã£o da importaÃ§Ã£o ainda dependem de arquivo autorizado, layout e homologaÃ§Ã£o DomÃ­nio.

**AtualizaÃ§Ã£o V-116:** a central passou a suportar fotografias agregadas de folha por empresa, competÃªncia e origem, com comparaÃ§Ã£o determinÃ­stica de quadro e totais sem guardar PII de trabalhador. ImportaÃ§Ã£o, interface, conexÃ£o DomÃ­nio e consultas oficiais continuam dependentes dos contratos e homologaÃ§Ãµes aplicÃ¡veis.

**AtualizaÃ§Ã£o V-117:** cada exportaÃ§Ã£o de relatÃ³rio do Copiloto preserva uma fotografia criptografada e imutÃ¡vel, vinculada Ã  resposta, empresa, solicitante, modelo e hashes do insumo/arquivo. A geraÃ§Ã£o ainda nÃ£o estÃ¡ pronta para produÃ§Ã£o: faltam fila Celery, rotaÃ§Ã£o de segredo e atualizaÃ§Ã£o compatÃ­vel da cadeia vulnerÃ¡vel do ExcelJS.

**AtualizaÃ§Ã£o V-118:** a exportaÃ§Ã£o do Copiloto exige `POST` com CSRF; `GET` nÃ£o gera download, fotografia ou auditoria. A inspeÃ§Ã£o visual dos controles no perfil nÃ£o-demo permanece obrigatÃ³ria antes de liberaÃ§Ã£o.

**AtualizaÃ§Ã£o V-119:** o lockfile do renderizador fixa uuid 11.1.1 compatÃ­vel com ExcelJS 4.4.0; `npm audit --omit=dev` passou sem vulnerabilidades. Para produÃ§Ã£o, restam Celery e rotaÃ§Ã£o/revogaÃ§Ã£o do segredo.

## Reauditoria de facilidade de uso — D-211 / V-223

V-227: atalhos Empresas → NFS-e usam empresa exata e preservam o recorte até o lote, com teste de homônimos e isolamento. Revalidar histórico de empresas pausadas no escopo operacional; publicação continua pendente.

V-226: Empresas reauditada; busca CNPJ tolerante, contagem filtrada, estado pausado e recuperação do modal corrigidos. Vinte e dois testes e dois subtestes aprovados, Playwright desktop/celular e checks estáticos. Publicação ainda pendente.

V-224: fluxo comum NFS-e percorrido com 165 notas sintéticas, seleção por empresa/página/filtro e ZIP iniciado na segunda página. Corrigida recusa de filtros inválidos e seleções parcialmente indisponíveis; publicação, rede interrompida e carteira real continuam pendentes.

V-225: histórico de downloads simplificado e falhas de abertura tratadas antes de registrar solicitação. A regressão ampla também corrigiu emissão fictícia do proprietário demo para progresso por sessão. A barreira de publicação está sendo reexecutada; versão de produção consultada continua 31.

Objetivo ativo reforçado: revisar novamente todas as telas, inclusive as já validadas, pesquisar padrões e ideias de layout antes de cada decisão e priorizar encontrar, entender e concluir tarefas. Primeira correção local: descoberta do download NFS-e em lote, orientação contextual, navegação e seleção coerentes; 29 testes aprovados e Playwright desktop/celular. Publicação e demais jornadas permanecem pendentes.

## 1. Objetivo e ponto de partida

Concluir todos os mÃ³dulos atuais, integrar DomÃ­nio e Siescon, entregar o instalador do escritÃ³rio e operar inicialmente com IA por API, deixando o fluxo de IA local preparado e testado.

**Pronto para venda:** o escritÃ³rio consegue configurar, executar, conferir o resultado e recuperar falhas; permissÃµes, cobranÃ§a, documentaÃ§Ã£o e suporte correspondem ao comportamento real.

As evidÃªncias sÃ£o sempre datadas: V-041 registra a revalidaÃ§Ã£o local de 21/09/2026 (lint, Django, migraÃ§Ãµes, testes e comparaÃ§Ã£o com GitHub); as provas anteriores de PostgreSQL, Redis, Windows e builds seguem registradas com seus limites. Nenhuma delas homologa integraÃ§Ã£o externa, treinamento em GPU ou instalaÃ§Ã£o no cliente. A anÃ¡lise consolidada mais recente estÃ¡ em [docs/planejamento/analise-projeto-2026-09-21.md](docs/planejamento/analise-projeto-2026-09-21.md).

## 2. MemÃ³ria Ãºnica

- [DECISOES.md](DECISOES.md): decisÃµes confirmadas e registros histÃ³ricos, preservando seu grau de confirmaÃ§Ã£o.
- [VALIDACOES.md](VALIDACOES.md): verificaÃ§Ãµes efetivamente executadas, resultados, limites e estado desta entrega.
- [Etapas e prompts](docs/planejamento/etapas/README.md): execuÃ§Ã£o detalhada das etapas 00â€“13.
- [InventÃ¡rio de cÃ³digo, rotas, tarefas e APIs](docs/planejamento/inventario-conclusao.md): mapa estÃ¡tico, nÃ£o prova de funcionamento.
- [Matriz de evidÃªncias de conclusÃ£o](docs/planejamento/matriz-evidencias-2026-09-19.md): nÃ­vel mÃ¡ximo provado, evidÃªncias e bloqueios de cada etapa.
- [LimitaÃ§Ãµes comerciais DomÃ­nio Web](docs/dominio-web-limitacoes-comerciais.md): linguagem de venda, capacidades verificadas e limites da API/backup.
- [DÃºvidas abertas](docs/planejamento/duvidas-abertas.md): registro Ãºnico de perguntas, com etapa e dono.
- [Estado operacional](docs/planejamento/estado-operacional.md) e [histÃ³rico de execuÃ§Ã£o](docs/planejamento/registro-de-execucao.md): evidÃªncias anteriores, com data e ressalvas.

Os caminhos antigos de plano e decisÃµes sÃ£o ponteiros, nÃ£o planos concorrentes. Documentos histÃ³ricos nÃ£o viram especificaÃ§Ã£o por serem mais antigos ou mais extensos. DecisÃµes confirmadas sÃ³ voltam a ser perguntadas diante de conflito concreto ou mudanÃ§a solicitada, indicando o ID e o motivo.

Cada item distingue: **implementado â†’ testado localmente â†’ homologado no ambiente real â†’ liberado para venda**. Um bloqueio documentado nÃ£o transforma uma etapa incompleta em concluÃ­da.

Por D-87, as etapas 01â€“11 encerram o respectivo escopo de implementaÃ§Ã£o e validaÃ§Ã£o local. A etapa 12 reÃºne toda execuÃ§Ã£o que exija site publicado, ambiente hospedado, credencial externa de produÃ§Ã£o, chamada real, piloto ou homologaÃ§Ã£o comercial. Essa organizaÃ§Ã£o nÃ£o antecipa deploy nem autoriza custos.

### DecisÃµes encerradas nesta conversa

| Assunto | DecisÃ£o | Registro |
|---|---|---|
| Arquitetura | SaaS e IA centralizados na Mewstack; agente instalado no escritÃ³rio. | D-46 |
| IA inicial | Uso por API KEY agora; preservar Claude conforme D-16. | D-47 |
| IA local | Consulta aos dados + ajuste do modelo com exemplos revisados. | D-48 |
| Isolamento do aprendizado | Conhecimento, exemplos, correÃ§Ãµes e ajustes derivados dos clientes ficam restritos ao respectivo escritÃ³rio; conhecimento geral pode ser compartilhado. | D-49 |
| API apÃ³s migraÃ§Ã£o | IA local como padrÃ£o apÃ³s homologaÃ§Ã£o; API como reserva autorizada, sujeita Ã  polÃ­tica de dados e orÃ§amento. | D-50 |
| Aceite local para venda inicial | Pipeline local preparado e testado; treinamento e desempenho na mÃ¡quina definitiva ficam para etapa posterior explÃ­cita. | D-51 |
| Ãreas do DomÃ­nio | ContÃ¡bil, fiscal e folha na preparaÃ§Ã£o da IA. | D-52 |
| Disponibilidade Siescon | ResponsÃ¡vel confirmou servidor/banco disponÃ­vel para viabilizar descoberta autorizada. | D-53 |
| OperaÃ§Ãµes Siescon | Leitura + exportaÃ§Ã£o revisada; gravaÃ§Ã£o direta nÃ£o aprovada. | D-54 |
| Autonomia | AutomaÃ§Ã£o por regras aprovadas e qualidade medida; exceÃ§Ãµes seguem para revisÃ£o. | D-55 |
| Sem presunÃ§Ãµes | â€œnunca assume nada, o que for preciso tu me pergunta aquiâ€. | D-56 |
| MemÃ³ria e execuÃ§Ã£o | Documentar tudo que for decidido; criar etapas para terminar o projeto e um prompt por etapa. | D-57 |
| Plano aprovado | Plano de conclusÃ£o composto pelas etapas 00â€“13, com dependÃªncias e aceites registrados em PLANO-MESTRE.md. | D-58 |
| LocalizaÃ§Ã£o da memÃ³ria | Plano mestre e tudo que for validado devem ficar na raiz do repositÃ³rio. | D-59 |
| Escopo desta execuÃ§Ã£o | â€œquero que tu faÃ§a apenas a primeira etapa agoraâ€. | D-60 |

Preservar tambÃ©m as decisÃµes anteriormente confirmadas: marca CICA; credenciais Serpro centrais; Asaas e cobranÃ§a manual separados; tokens por mÃ³dulo; Triagem por e-mail; Triagem substitui Jornadas. Valores propostos, regras apenas registradas e homologaÃ§Ãµes pendentes nÃ£o foram aprovados por este plano.

## 3. Etapas, dependÃªncias e prompts

Os nÃºmeros identificam etapas; a ordem de execuÃ§Ã£o deve respeitar dependÃªncias. A etapa 10 fornece controles necessÃ¡rios Ã  08. A 13 fica apÃ³s a disponibilidade do equipamento e nÃ£o bloqueia a venda inicial por API.

### Etapa 00 â€” Consolidar decisÃµes, inventÃ¡rio e pendÃªncias

**Depende de:** Nenhuma.

**Entregas**

- Gravar integralmente o plano e as decisÃµes confirmadas.
- Inventariar mÃ³dulos, rotas, tarefas, APIs, serviÃ§os Windows e integraÃ§Ãµes.
- Confrontar documentaÃ§Ã£o antiga com o cÃ³digo e decisÃµes posteriores.
- Registrar cada pendÃªncia uma Ãºnica vez, com etapa afetada e responsÃ¡vel pela resposta.
- Preservar o trabalho local existente; nÃ£o descartar nem sobrescrever alteraÃ§Ãµes.
- Agrupar as perguntas restantes por condiÃ§Ãµes comerciais, regras documentais, dados autorizados para IA, ambientes de homologaÃ§Ã£o e metas operacionais; perguntar somente o ainda nÃ£o decidido.

**PendÃªncias / limites:** Nenhum bloqueio para documentar; as decisÃµes abertas nÃ£o impedem esta etapa.

**Aceite:** Outra pessoa consegue identificar o prÃ³ximo trabalho, suas decisÃµes e seus bloqueios sem reconstruir conversas antigas.

**Prompt**

> Execute a etapa 00 do plano mestre da CICA. Materialize os documentos e prompts deste plano, consolide as decisÃµes jÃ¡ confirmadas e elimine contradiÃ§Ãµes documentais sem apagar o histÃ³rico. Confira o cÃ³digo atual. NÃ£o pergunte novamente decisÃµes registradas; apresente somente lacunas ou conflitos concretos.

[Checklist, testes e continuidade da etapa 00](docs/planejamento/etapas/00-documentacao.md).

### Etapa 01 â€” Estabilizar a base tÃ©cnica

**Depende de:** 00.

**Entregas**

- Resolver as 66 violaÃ§Ãµes atuais do Ruff e demais falhas verificadas.
- Consolidar migraÃ§Ãµes e revisar compatibilidade com dados existentes.
- Executar testes com PostgreSQL, Redis e workers reais em ambiente isolado.
- Verificar concorrÃªncia em consumo, faturamento, filas e publicaÃ§Ã£o de modelos.
- Validar builds da aplicaÃ§Ã£o, runtime multimodal, treinamento e agente.
- Revisar dependÃªncias, configuraÃ§Ã£o de produÃ§Ã£o e tratamento de segredos.

**PendÃªncias / limites:** Q-28 e Q-30 para ambientes e aceite; disponibilidades tÃ©cnicas devem ser inspecionadas, sem instalar ou contratar infraestrutura por inferÃªncia.

**Aceite:** CI aprovado e instalaÃ§Ã£o reproduzÃ­vel; testes com SQLite nÃ£o substituem testes concorrentes em PostgreSQL.

**Prompt**

> Execute a etapa 01. Estabilize o estado atual preservando alteraÃ§Ãµes existentes, faÃ§a o CI passar e valide banco, filas, migraÃ§Ãµes e builds em ambiente isolado. Registre resultados e limitaÃ§Ãµes reais; nÃ£o considere testes simulados prova de produÃ§Ã£o.

[Checklist, testes e continuidade da etapa 01](docs/planejamento/etapas/01-base-tecnica.md).

### Etapa 02 â€” Fechar cadastro, acesso e administraÃ§Ã£o

**Depende de:** 01.

**Entregas**

- Completar cadastro, confirmaÃ§Ã£o de e-mail, recuperaÃ§Ã£o, convites, MFA e fim do teste.
- Conferir permissÃµes por escritÃ³rio, empresa, mÃ³dulo e operaÃ§Ã£o.
- Validar empresas, certificados, equipe e primeiros passos.
- Completar o console Mewstack para suporte, contratos, integraÃ§Ãµes e falhas.
- Garantir que demonstraÃ§Ãµes nÃ£o acessem dados ou serviÃ§os reais.
- Homologar e-mail transacional e seus estados de falha.

**PendÃªncias / limites:** Q-01 a Q-06 e Q-29: nÃ£o inventar regras de acesso comercial nem SMTP.

**Aceite:** ProprietÃ¡rio, administrador, operador, financeiro, auditor e suporte sÃ³ realizam aÃ§Ãµes autorizadas, inclusive por acesso direto Ã s APIs.

**Prompt**

> Execute a etapa 02. Complete o ciclo de entrada e administraÃ§Ã£o da CICA, incluindo permissÃµes, MFA, empresas, certificados e suporte. Valide as jornadas por perfil e o isolamento entre escritÃ³rios. Consulte decisÃµes existentes antes de perguntar regras comerciais ou de acesso.

[Checklist, testes e continuidade da etapa 02](docs/planejamento/etapas/02-acesso-administracao.md).

### Etapa 03 â€” Concluir agente Windows e integraÃ§Ã£o DomÃ­nio

**Depende de:** 01â€“02.

**Entregas**

- Resolver a divisÃ£o atual: o agente Python sincroniza DomÃ­nio local; o nativo processa backups e arquivamento.
- Entregar um fluxo de instalaÃ§Ã£o que identifique claramente os componentes necessÃ¡rios.
- Homologar DSNs e drivers nas arquiteturas suportadas.
- Completar pareamento, atualizaÃ§Ã£o, revogaÃ§Ã£o, reinÃ­cio, diagnÃ³stico e recuperaÃ§Ã£o de rede.
- Validar DomÃ­nio local e importaÃ§Ã£o manual de backup DomÃ­nio Web.
- Substituir limites que truncam dados por leitura paginada/incremental verificÃ¡vel.
- Mapear os dados necessÃ¡rios de contabilidade, fiscal e folha, com leitura autorizada e rastreabilidade.
- Homologar escrita documental nas pastas Windows permitidas.

**PendÃªncias / limites:** Q-22, Q-28, Q-31 e Q-32. Registrar a arquitetura definitiva antes de unificar Python e serviÃ§o nativo.

**Aceite:** Instalar em mÃ¡quina limpa, sincronizar, interromper a rede, reiniciar e retomar sem perder ou duplicar dados.

**Prompt**

> Execute a etapa 03. Complete localmente o serviÃ§o instalÃ¡vel e o conector DomÃ­nio local/Web. Registre a arquitetura definitiva antes de alterÃ¡-la. Prepare instalaÃ§Ã£o, leitura, recuperaÃ§Ã£o, atualizaÃ§Ã£o e pastas Windows sem SQL arbitrÃ¡rio nem escrita no banco DomÃ­nio; a homologaÃ§Ã£o contra o site publicado e o piloto real pertencem Ã  etapa 12.

[Checklist, testes e continuidade da etapa 03](docs/planejamento/etapas/03-agente-dominio.md).

### Etapa 04 â€” Implementar e homologar Siescon

**Depende de:** 02â€“03.

**Entregas**

- Identificar versÃ£o, banco, mecanismo permitido de acesso e ambiente disponibilizado.
- Obter schema e arquivos de referÃªncia por acesso autorizado.
- Implementar leitura, sincronizaÃ§Ã£o e diagnÃ³stico.
- Mapear empresas, contas, lanÃ§amentos e demais dados necessÃ¡rios aos fluxos contratados.
- Preparar exportaÃ§Ã£o revisada no layout efetivamente suportado.
- Generalizar vÃ­nculos hoje dependentes exclusivamente do cÃ³digo DomÃ­nio.
- Registrar matriz de capacidades: o que funciona com DomÃ­nio, Siescon ou ambos.

**PendÃªncias / limites:** Q-28 e Q-33. Banco disponÃ­vel foi confirmado; versÃ£o, meio de acesso e layout nÃ£o foram fornecidos.

**Aceite:** Dados sincronizados conferem com o Siescon; arquivo exportado Ã© importado e conferido no ambiente de homologaÃ§Ã£o. Gerar arquivo nÃ£o basta.

**Prompt**

> Execute a etapa 04 usando o servidor/banco Siescon disponibilizado pelo responsÃ¡vel. Descubra e documente o contrato tÃ©cnico antes de programar o adaptador. Entregue leitura e exportaÃ§Ã£o revisada, valide identificaÃ§Ã£o das empresas e homologue a importaÃ§Ã£o. NÃ£o invente endpoints, layouts ou permissÃµes.

[Checklist, testes e continuidade da etapa 04](docs/planejamento/etapas/04-siescon.md).

### Etapa 05 â€” Concluir IA por API e preparaÃ§Ã£o da IA local

**Depende de:** 02â€“03; incorporar Siescon apÃ³s 04.

**Entregas**

- Completar Copiloto e anÃ¡lise documental por API com limites, custos e falhas recuperÃ¡veis.
- Ampliar a consulta de conhecimento: a busca atual por palavras nÃ£o comprova cobertura das trÃªs Ã¡reas solicitadas.
- Estruturar dados e fontes por escritÃ³rio, empresa, perÃ­odo e Ã¡rea.
- Separar dados operacionais atualizados dos exemplos usados para ajuste do modelo.
- Completar seleÃ§Ã£o de exemplos, revisÃ£o, anonimizaÃ§Ã£o, versionamento e exportaÃ§Ã£o QLoRA.
- Separar conjuntos de treino e avaliaÃ§Ã£o para evitar avaliaÃ§Ã£o contaminada.
- Vincular avaliaÃ§Ã£o ao artefato exato do modelo/adaptador, corpus e versÃ£o.
- Preparar publicaÃ§Ã£o, seleÃ§Ã£o do adaptador por escritÃ³rio e retorno Ã  versÃ£o anterior.
- [x] Testar o contrato do runtime local e impedir fallback externo sem autorizaÃ§Ã£o (V-072).

**PendÃªncias / limites:** Q-08, Q-09, Q-11, Q-30 e Q-34. Percentuais existentes no cÃ³digo nÃ£o sÃ£o aprovaÃ§Ã£o comercial.

**Aceite:** Respostas com fontes verificÃ¡veis; isolamento entre escritÃ³rios; pipeline reproduzÃ­vel; etapas que exigem a GPU definitiva explicitamente identificadas.

**Prompt**

> Execute a etapa 05. Complete a IA por API e o pipeline local para contÃ¡bil, fiscal e folha, mantendo dados e ajustes isolados por escritÃ³rio. Reaproveite o runner QLoRA e os controles existentes, corrigindo lacunas entre corpus, avaliaÃ§Ã£o, artefato e inferÃªncia. NÃ£o declare treinamento real ou desempenho local sem execuÃ§Ã£o comprovada.

[Checklist, testes e continuidade da etapa 05](docs/planejamento/etapas/05-ia-api-pipeline-local.md).

### Etapa 06 â€” Concluir Triagem de Arquivos

**Depende de:** 03 e 05.

**Estado local:** V-038 revalidou quarentena, leitura incremental simulada,
scan/formato, revisÃ£o, cÃ³pia Ã­ntegra e protocolo de agente Windows. Isso nÃ£o
homologa OAuth, caixa, antimalware, catÃ¡logo, retenÃ§Ã£o ou destino Windows real.

**Entregas**

- Homologar Microsoft 365, Google Workspace, Gmail pessoal e IMAP conforme decisÃµes registradas.
- Completar leitura incremental, quarentena, antimalware, extraÃ§Ã£o e classificaÃ§Ã£o.
- Permitir visualizar documentos liberados, corrigir empresa, tipo, competÃªncia e destino.
- Aplicar automaÃ§Ã£o somente Ã s regras aprovadas e medidas.
- Completar biblioteca interna e arquivamento Windows com confirmaÃ§Ã£o de integridade.
- Atualizar checklist somente apÃ³s arquivamento confirmado.
- Resolver duplicatas, colisÃµes, mÃºltiplos documentos e indisponibilidade do agente.

**PendÃªncias / limites:** Q-12 a Q-25 e Q-31: catÃ¡logo, nomenclatura, retenÃ§Ã£o, formatos, limites e checklist ainda precisam de decisÃµes especÃ­ficas.

**Aceite:** E-mail â†’ anexo seguro â†’ classificaÃ§Ã£o/revisÃ£o â†’ arquivo localizado no destino â†’ checklist atualizado, com recuperaÃ§Ã£o de falhas.

**Prompt**

> Execute a etapa 06. Complete a Triagem exclusivamente pelas entradas de e-mail aprovadas e pelos dois destinos definidos. Consulte o registro antes de perguntar taxonomia ou nomenclatura. Homologue todo o caminho atÃ© o arquivo final, incluindo correÃ§Ã£o humana, duplicatas, quarentena e agente indisponÃ­vel.

[Checklist, testes e continuidade da etapa 06](docs/planejamento/etapas/06-triagem.md).

### Etapa 07 â€” Concluir NFS-e, certificados e revisÃ£o fiscal

**Depende de:** 03 e 05.

**Entregas**

- Homologar coleta ADN, certificados, NSU, retomada e deduplicaÃ§Ã£o.
- Apresentar nota legÃ­vel, valores, participantes, competÃªncia e descriÃ§Ã£o dos serviÃ§os.
- Validar acumuladores contra o catÃ¡logo da empresa.
- Exibir evidÃªncia da sugestÃ£o e permitir correÃ§Ã£o.
- Garantir acesso a toda a carteira, sem cortes silenciosos nas filas.
- Documentar cobertura e limitaÃ§Ãµes efetivas da fonte de coleta.

**PendÃªncias / limites:** Q-28 e Q-30: certificado/ambiente autorizado, corpus e mÃ©tricas de aceite.

**Aceite:** Nota real autorizada Ã© coletada, conferida, classificada e rastreada sem duplicaÃ§Ã£o ou associaÃ§Ã£o Ã  empresa errada.

**Prompt**

> Execute a etapa 07. Complete e homologue NFS-e e revisÃ£o fiscal, da validade do certificado Ã  decisÃ£o do contador. Valide o catÃ¡logo de acumuladores e a continuidade da coleta. NÃ£o confunda dados calculados, documento fiscal oficial e sugestÃ£o da IA.

[Checklist, testes e continuidade da etapa 07](docs/planejamento/etapas/07-nfse.md).

### Etapa 08 â€” Concluir Central Integra Contador

**Depende de:** 02 e controles de consumo da 10.

**Entregas**

- DTE: consulta, paginaÃ§Ã£o, teor, autorizaÃ§Ã£o especÃ­fica de ciÃªncia e recuperaÃ§Ã£o de retorno incerto.
- DCTFWeb: declaraÃ§Ã£o, recibo e guia; preservar o escopo registrado sem transmissÃ£o.
- Parcelamentos: concluir PARCSN e consultar o responsÃ¡vel antes de ampliar modalidades.
- Homologar credenciais centrais, certificados, representaÃ§Ã£o e serviÃ§os.
- Validar estimativa, autorizaÃ§Ã£o, reserva, liquidaÃ§Ã£o e persistÃªncia de documentos.
- Impedir repetiÃ§Ã£o automÃ¡tica de operaÃ§Ãµes com resultado incerto.

**PendÃªncias / limites:** Q-05, Q-28, Q-30 e Q-36; chamadas cobradas exigem autorizaÃ§Ã£o especÃ­fica.

**Aceite:** Cada operaÃ§Ã£o prometida completa a jornada real, com documentos, protocolo, consumo e falhas rastreÃ¡veis.

**Prompt**

> Execute a etapa 08. Homologue DTE, DCTFWeb e Parcelamentos com credenciais centrais Mewstack e escopo jÃ¡ aprovado. Preserve autorizaÃ§Ã£o de ciÃªncia e controles de consumo. Antes de qualquer chamada cobrada, solicite aprovaÃ§Ã£o especÃ­fica de custo; nÃ£o repita chamadas de resultado incerto.

[Checklist, testes e continuidade da etapa 08](docs/planejamento/etapas/08-integra-contador.md).

### Etapa 09 â€” Concluir ConciliaÃ§Ã£o e Radar

**Depende de:** 03â€“05; exportaÃ§Ã£o Siescon depende de 04.

**Estado local:** V-037 revalidou ingestÃ£o limitada, mapeamento/revisÃ£o,
conciliaÃ§Ã£o com evidÃªncia, retomada, exportaÃ§Ã£o auditÃ¡vel e coleta Radar
simulada. Isso nÃ£o homologa OCR, layout, volume, fontes oficiais ou importaÃ§Ã£o
em DomÃ­nio/Siescon.

**Entregas**

- Concluir OFX, CSV, XLSX e PDF/OCR com layouts e evidÃªncias.
- Permitir corrigir mapeamento, classificar, revisar, conciliar e tratar ausÃªncia de correspondÃªncia.
- Validar contas, direÃ§Ã£o, competÃªncia, saldos e lanÃ§amentos equilibrados.
- Homologar exportaÃ§Ãµes DomÃ­nio e Siescon sem apresentar exportaÃ§Ã£o como importaÃ§Ã£o concluÃ­da.
- Validar volume com PostgreSQL e corpus representativo.
- No Radar, comprovar coleta, atualizaÃ§Ã£o, origem e falhas, preservando a proposta de acompanhamento de publicaÃ§Ãµes.

**PendÃªncias / limites:** Q-28; layouts reais e amostra independente. Aplicar as
mÃ©tricas jÃ¡ decididas em D-73 antes de qualquer aceite.

**Aceite:** Processamento auditÃ¡vel, nenhuma conciliaÃ§Ã£o sem evidÃªncia independente e exportaÃ§Ãµes conferidas nos sistemas de destino.

**Prompt**

> Execute a etapa 09. Complete conciliaÃ§Ã£o, lanÃ§amentos revisados e exportaÃ§Ãµes homologadas para os conectores aprovados. Valide documentos reais autorizados e volume. Complete tambÃ©m a operaÃ§Ã£o do Radar, sem ampliar sua promessa para cÃ¡lculo tributÃ¡rio individual nÃ£o decidido.

[Checklist, testes e continuidade da etapa 09](docs/planejamento/etapas/09-conciliacao-radar.md).

### Etapa 10 â€” Concluir contrataÃ§Ã£o, tokens e cobranÃ§a

**Depende de:** 02; pode avanÃ§ar antes das homologaÃ§Ãµes fiscais.

**Entregas**

- Fechar com o responsÃ¡vel preÃ§os, franquias, pesos, tetos, carÃªncia e regras de mudanÃ§a de contrato.
- Concluir a orquestraÃ§Ã£o Asaas entre dados comerciais autorizados, cliente, cobranÃ§a e `PaymentAttempt`; V-040 jÃ¡ cobre somente o contrato local do cliente.
- Homologar Pix, boleto, cartÃ£o, atrasos, estornos e eventos fora de ordem.
- Garantir fatura Ãºnica, consumo auditÃ¡vel e proteÃ§Ã£o contra duplicidade.
- Separar integralmente contratos manuais da automaÃ§Ã£o Asaas.
- Implementar somente leitura e reativaÃ§Ã£o conforme regras expressamente aprovadas.

**PendÃªncias / limites:** Q-01 a Q-06 e Q-08; sandbox/contrato em Q-28.

**Aceite:** Contrato, acesso, consumo e fatura concordam, inclusive em concorrÃªncia e falhas.

**Prompt**

> Execute a etapa 10. Use o modelo comercial confirmado e pergunte apenas valores e regras ainda pendentes. Complete e homologue Asaas e cobranÃ§a manual, com tokens inteiros, franquias por mÃ³dulo e teto aceito. NÃ£o publique preÃ§os nem crie cobranÃ§as reais sem aprovaÃ§Ã£o correspondente.

[Checklist, testes e continuidade da etapa 10](docs/planejamento/etapas/10-contratacao-cobranca.md).

### Etapa 11 â€” Validar todas as jornadas e interfaces

**Depende de:** MÃ³dulos implementados.

**Estado local:** V-039 verificou parcialmente 14 caminhos e uma jornada
fictÃ­cia de Triagem em servidor isolado. A auditoria completa de perfis, estados
e oferta segue pendente.

**Entregas**

- Revisar site comercial, cadastro, aplicaÃ§Ã£o do escritÃ³rio, central de aprendizado e console Mewstack.
- Corrigir aÃ§Ãµes sem saÃ­da, tabelas incompletas, estados confusos e ausÃªncia de evidÃªncia.
- Validar desktop, celular, teclado, foco, erros, carregamento e estados vazios.
- Aplicar ui-ux-pro-max, Watermelon, referÃªncias reais de produto e web-design-guidelines.
- Inspecionar as jornadas com Playwright MCP; registrar exatamente os estados alcanÃ§ados e fechar as sessÃµes.
- Conferir que oferta comercial e demonstraÃ§Ã£o refletem capacidades homologadas.

**PendÃªncias / limites:** Aplicar D-73; estados inacessÃ­veis devem ser
registrados, nunca presumidos validados.

**Aceite:** O usuÃ¡rio conclui tarefas representativas sem intervenÃ§Ã£o interna nÃ£o prevista.

**Prompt**

> Execute a etapa 11 em todas as Ã¡reas da CICA, preservando o design existente. Siga integralmente o fluxo de UI do AGENTS.md, registre referÃªncias e valide tarefas completas com Playwright em desktop e celular. Corrija bloqueios funcionais e de acessibilidade e feche as sessÃµes abertas.

[Checklist, testes e continuidade da etapa 11](docs/planejamento/etapas/11-jornadas-interfaces.md).

### Etapa 12 â€” HomologaÃ§Ã£o integrada e liberaÃ§Ã£o comercial

**Depende de:** 01â€“11.

**Entregas**

- Identificar ambiente de produÃ§Ã£o e capacidade necessÃ¡ria, sem presumir provedor ou contratar recursos.
- Validar deploy, migraÃ§Ãµes, workers, agendador, storage e conectividade dos agentes.
- Executar restauraÃ§Ã£o de banco e documentos, recuperaÃ§Ã£o de falhas e retorno de versÃ£o.
- Homologar retenÃ§Ã£o, exportaÃ§Ã£o, exclusÃ£o, termos e contatos de suporte.
- Executar piloto por mÃ³dulo, com critÃ©rios e amostra aprovados.
- Entregar manuais de instalaÃ§Ã£o, operaÃ§Ã£o e suporte, matriz de compatibilidade e limitaÃ§Ãµes.
- Produzir relatÃ³rio final de liberaÃ§Ã£o por mÃ³dulo.

**PendÃªncias / limites:** Q-24, Q-28 a Q-30 e Q-35. Recursos pagos exigem aprovaÃ§Ã£o especÃ­fica.

**Aceite:** Todos os mÃ³dulos da oferta possuem evidÃªncia de funcionamento e operaÃ§Ã£o sustentÃ¡vel; nenhuma pendÃªncia crÃ­tica Ã© escondida como concluÃ­da.

**Prompt**

> Execute a etapa 12. FaÃ§a a homologaÃ§Ã£o integrada da CICA e reÃºna evidÃªncias por mÃ³dulo, incluindo restauraÃ§Ã£o, filas, integraÃ§Ãµes, instalaÃ§Ã£o e suporte. Confirme com o responsÃ¡vel ambiente, metas e critÃ©rios ainda pendentes. NÃ£o libere venda nem contrate infraestrutura por inferÃªncia.

[Checklist, testes e continuidade da etapa 12](docs/planejamento/etapas/12-homologacao-venda.md).

### Etapa 13 â€” Ativar IA local na mÃ¡quina definitiva

**Depende de:** 05 e disponibilidade do equipamento; nÃ£o bloqueia a venda inicial por API.

**Entregas**

- Inspecionar hardware e selecionar modelo compatÃ­vel mediante decisÃ£o registrada.
- Executar treinamento real e avaliaÃ§Ã£o independente por escritÃ³rio.
- Medir qualidade, latÃªncia, concorrÃªncia e consumo de recursos.
- Homologar isolamento de adaptadores e operaÃ§Ã£o sem API.
- Migrar o padrÃ£o para local somente apÃ³s aprovaÃ§Ã£o dos resultados.
- Manter API como reserva autorizada e permitir retorno Ã  versÃ£o anterior.

**PendÃªncias / limites:** Q-30, Q-34 e Q-35. Hardware/modelo e resultados ainda nÃ£o homologados.

**Aceite:** Treino real, qualidade e capacidade comprovados na mÃ¡quina definitiva; mudanÃ§a de rota aprovada e retorno de versÃ£o demonstrado.

**Prompt**

> Execute a etapa 13 quando a mÃ¡quina definitiva estiver disponÃ­vel. Consulte as decisÃµes de IA jÃ¡ registradas, valide hardware e modelo, execute treinamento e avaliaÃ§Ã£o reais e apresente as evidÃªncias para a mudanÃ§a de rota. Preserve isolamento por escritÃ³rio e fallback externo somente autorizado.

[Checklist, testes e continuidade da etapa 13](docs/planejamento/etapas/13-ia-local-definitiva.md).

## 4. Regras de conclusÃ£o e continuidade

Todo prompt de etapa deve ser executado com as instruÃ§Ãµes comuns abaixo:

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. NÃ£o refaÃ§a decisÃµes confirmadas. Pergunte ao responsÃ¡vel somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alteraÃ§Ãµes existentes. NÃ£o incorra em custos sem aprovaÃ§Ã£o especÃ­fica imediatamente anterior. Ao terminar, atualize os .md com mudanÃ§as, testes executados, evidÃªncias, limitaÃ§Ãµes, bloqueios e prÃ³ximo passo. NÃ£o marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitaÃ§Ã£o atual; a existÃªncia do prÃ³ximo prompt nÃ£o autoriza iniciar outra etapa.

Cada entrega deve registrar critÃ©rios atendidos e bloqueios, testes proporcionais ao risco, documentaÃ§Ã£o atualizada, aÃ§Ãµes do responsÃ¡vel e o prÃ³ximo prompt. Uma etapa sÃ³ Ã© concluÃ­da quando o aceite foi atendido; caso contrÃ¡rio permanece parcial ou bloqueada, com motivo. A mera documentaÃ§Ã£o do bloqueio nÃ£o constitui conclusÃ£o funcional.

**Nenhum prazo, preÃ§o, regra comercial, arquitetura pendente ou autorizaÃ§Ã£o de dados serÃ¡ inventado para preencher o plano.** As pendÃªncias tÃªm dono e impedem apenas o trabalho dependente. A autorizaÃ§Ã£o de execuÃ§Ã£o de uma etapa nÃ£o autoriza custo, publicaÃ§Ã£o, homologaÃ§Ã£o presumida ou execuÃ§Ã£o da prÃ³xima etapa quando o responsÃ¡vel limitou o escopo.

## 5. PrÃ³ximo trabalho

**AtualizaÃ§Ã£o de continuidade em 23/09/2026:** D-110 define uma meta ativa de
completude verificÃ¡vel: revisar lacunas, implementar o que independe de decisÃµes
externas, validar cada fluxo e registrar os bloqueios reais antes de considerar o
produto pronto. A revisÃ£o nÃ£o reduz os critÃ©rios de D-73 nem antecipa a etapa 12.

**AtualizaÃ§Ã£o V-113 em 23/09/2026:** a ficha Ãºnica de empresa passou a concentrar
as atividades locais e, quando autorizado, a Triagem daquela empresa. O vÃ­nculo
nÃ£o conclui trabalho automaticamente e nÃ£o altera o fluxo dos mÃ³dulos de origem;
NFS-e, ConciliaÃ§Ã£o, Radar, Copiloto, folha, DRE e caixa permanecem extensÃµes
explÃ­citas a completar e validar.

**AtualizaÃ§Ã£o de escopo em 23/09/2026:** o responsÃ¡vel autorizou implementar a
evoluÃ§Ã£o integral descrita em D-109. O trabalho preserva as etapas 00â€“13 e seus
limites de homologaÃ§Ã£o, mas introduz a frente transversal "Central operacional":
modelo de atividades, evidÃªncias, fechamentos, permissÃµes por empresa, dados
independentes de ERP, relatÃ³rios JavaScript, DRE, caixa gerencial e preparaÃ§Ã£o
para reforma tributÃ¡ria. A entrega serÃ¡ incremental, com migraÃ§Ãµes aditivas,
testes locais e registros em VALIDACOES.md; integraÃ§Ãµes externas, credenciais,
custos, piloto e publicaÃ§Ã£o seguem exclusivamente para a etapa 12.

[04 â€” implementar e homologar Siescon](docs/planejamento/etapas/04-siescon.md) Ã© a prÃ³xima etapa habilitada. A preparaÃ§Ã£o estrutural local e a anÃ¡lise estÃ£o registradas em V-029 a V-031 e V-041; o contrato tÃ©cnico Q-33 continua indispensÃ¡vel para escrever o adaptador, pois nÃ£o se pode inventar versÃ£o, mecanismo de acesso, schema, identificador de empresa ou layout. As frentes locais independentes de IA, Triagem, NFS-e, Central Integra Contador, ConciliaÃ§Ã£o/Radar e cobranÃ§a tambÃ©m avanÃ§aram e foram evidenciadas em V-032 a V-035, V-037â€“V-040, sem antecipar integraÃ§Ãµes externas. A [anÃ¡lise de 21/09](docs/planejamento/analise-projeto-2026-09-21.md) lista o material mÃ­nimo a receber por canal seguro. Sem esse material, a etapa permanece bloqueada, nÃ£o concluÃ­da.

- V-141 (23/09/2026): a configuracao inicial passou a ser retomavel com proxima acao concreta para cada etapa persistida; nao cria configuracoes ou consumo automaticamente.

- V-142 (23/09/2026): o roteiro do responsavel passou a consolidar, por integracao e frente de produto, o material a providenciar, decisoes, dono, aceite e ordem de desbloqueio. Ele nao substitui Q/D nem declara homologacao externa.

**AtualizaÃ§Ã£o V-143 (24/09/2026):** corrigida a ampliaÃ§Ã£o indevida de carteira quando um colaborador nÃ£o possui atribuiÃ§Ãµes ativas, inclusive apÃ³s revogaÃ§Ã£o da Ãºltima; mantida visÃ£o total administrativa local e validade do controle externo. PrÃ©via/fila usam prazo efetivo para ordenaÃ§Ã£o. SuÃ­te integral: 869 aprovados, 2 ignorados, 15 subtestes; Ruff, MyPy, Django e migraÃ§Ãµes passaram. A meta da agenda pessoal permanece ativa: fechamentos na pÃ¡gina, recorrÃªncia automÃ¡tica e integraÃ§Ã£o dos mÃ³dulos ainda precisam de implementaÃ§Ã£o, alÃ©m da validaÃ§Ã£o visual bloqueada pelo transporte Playwright. Checklist atualizado na etapa 11.

**AtualizaÃ§Ã£o V-144 (24/09/2026):** VisÃ£o geral agora comeÃ§a em Meu trabalho, com tarefas atribuÃ­das Ã  pessoa, paginaÃ§Ã£o e agrupamento por prazo. Carteira e GestÃ£o sÃ£o recortes separados; colaboradores nÃ£o abrem GestÃ£o. Indicadores preservam o recorte. 871 testes aprovados, 2 ignorados e 15 subtestes; checagens tÃ©cnicas passaram. ValidaÃ§Ã£o visual segue pendente pelo transporte Playwright. Fechamentos agregados, geraÃ§Ã£o recorrente e conexÃ£o dos mÃ³dulos continuam abertos no checklist da etapa 11; esta entrega nÃ£o encerra a meta.

**AtualizaÃ§Ã£o V-145 (24/09/2026):** recorrÃªncia mensal local implementada com cursor transacional por atribuiÃ§Ã£o, recuperaÃ§Ã£o de competÃªncias, pausa/retomada, geraÃ§Ã£o sem responsÃ¡vel apÃ³s revogaÃ§Ã£o e exclusÃµes de escopo. Tarefa Celery/Beat preparada; migration 0054 verificada no banco de testes. RegressÃ£o: 878 aprovados, 2 ignorados e 19 subtestes. Fechamentos agregados, integraÃ§Ã£o dos mÃ³dulos, concorrÃªncia PostgreSQL e validaÃ§Ã£o visual continuam pendentes; nÃ£o houve ativaÃ§Ã£o em produÃ§Ã£o.

**AtualizaÃ§Ã£o V-146 (24/09/2026):** regra de fechamento revalida comprovaÃ§Ãµes e estados exigidos, compartilhada com a conclusÃ£o manual; tarefas marcadas concluÃ­das sem requisitos nÃ£o bastam. 881 testes aprovados, 2 ignorados e 21 subtestes; checagens tÃ©cnicas passaram. ExposiÃ§Ã£o agregada na agenda, integraÃ§Ã£o dos mÃ³dulos e validaÃ§Ã£o visual seguem pendentes, sem homologaÃ§Ã£o externa presumida.

**AtualizaÃ§Ã£o V-147 (24/09/2026):** a agenda exibe requisitos de fechamento por empresa/competÃªncia/Ã¡rea, causas e acesso Ã s evidÃªncias, com carteira protegida e paginaÃ§Ã£o. 884 testes aprovados, 2 ignorados e 21 subtestes. Estados ainda precisam ser alimentados pelos mÃ³dulos e fontes homologadas; cobertura dos modelos e validaÃ§Ã£o visual permanecem pendentes. NÃ£o hÃ¡ declaraÃ§Ã£o de produto concluÃ­do.

**AtualizaÃ§Ã£o V-148 (24/09/2026):** captura e revisÃ£o humana de NFS-e passaram a alimentar atividades com vÃ­nculo Ãºnico e evidÃªncia local, transaÃ§Ã£o conjunta e recuperaÃ§Ã£o explÃ­cita. 889 testes aprovados, 2 ignorados, 21 subtestes. NÃ£o confirma importaÃ§Ã£o DomÃ­nio. Restam navegaÃ§Ã£o/validaÃ§Ã£o visual, demais mÃ³dulos e homologaÃ§Ãµes externas; migration 0055 aplicada apenas em testes.

**AtualizaÃ§Ã£o V-149 (24/09/2026):** Triagem passou a projetar aprovaÃ§Ã£o, falha/rejeiÃ§Ã£o e confirmaÃ§Ã£o de arquivamento em atividades vinculadas, incluindo retorno do agente. ConclusÃ£o depende de destino/data/hash persistidos e nÃ£o fecha ERP. Migration 0056 aplicada apenas em testes; comando local de recuperaÃ§Ã£o documentado. Demais mÃ³dulos, navegaÃ§Ã£o contextual e homologaÃ§Ãµes continuam abertos.

**AtualizaÃ§Ã£o V-150 (24/09/2026):** atividades vinculadas tÃªm aÃ§Ã£o contextual para NFS-e/Triagem; serviÃ§os recusam escrita de auditor/financeiro e revalidam carteira. 893 testes aprovados, 2 ignorados, 23 subtestes. PrÃ³xima lacuna operacional: atribuir tarefas avulsas/de mÃ³dulo explicitamente para alimentar a agenda pessoal; demais mÃ³dulos e homologaÃ§Ãµes permanecem abertos.

**AtualizaÃ§Ã£o V-151 (24/09/2026):** administrador pode atribuir/redistribuir tarefas abertas para pessoas com carteira vigente, com motivo, histÃ³rico e detecÃ§Ã£o de envio desatualizado. Trabalho passa a entrar/sair da agenda pessoal explicitamente. RegressÃ£o: 895 aprovados, 2 ignorados, 23 subtestes. Demais mÃ³dulos, fonte-observaÃ§Ã£o e validaÃ§Ã£o visual/externa permanecem em execuÃ§Ã£o.

**AtualizaÃ§Ã£o V-152 (24/09/2026):** observaÃ§Ãµes da fonte passaram a respeitar ordem temporal por dimensÃ£o, repetiÃ§Ã£o exata, conflito de instante e preservaÃ§Ã£o da Ãºltima fotografia. EvidÃªncia fica vinculada ao retorno aplicado, sem conclusÃ£o automÃ¡tica. Trata-se da base do contrato; ligaÃ§Ã£o e homologaÃ§Ã£o dos adaptadores permanecem pendentes, assim como demais mÃ³dulos e validaÃ§Ã£o visual.

**AtualizaÃ§Ã£o V-153 (24/09/2026):** ConciliaÃ§Ã£o projeta tratamento local em atividade Ãºnica por arquivo, com prova e reabertura apÃ³s desfazimento/revisÃ£o. 898 testes aprovados, 2 ignorados, 23 subtestes; checagens tÃ©cnicas passaram. NavegaÃ§Ã£o contextual, reconfirmaÃ§Ã£o apÃ³s desfazimento, demais pontes e validaÃ§Ã£o visual/externa permanecem pendentes. Migration 0057 aplicada apenas em testes; meta ativa.

**AtualizaÃ§Ã£o V-154 (24/09/2026):** corrigida reconfirmaÃ§Ã£o apÃ³s desfazimento, com histÃ³rico prÃ³prio protegido, tratamento de legado e revalidaÃ§Ã£o de capacidade. 899 testes aprovados, 2 ignorados, 23 subtestes; checagens tÃ©cnicas passaram. Migration 0058 apenas em testes. ExposiÃ§Ã£o do histÃ³rico, navegaÃ§Ã£o contextual, demais pontes e homologaÃ§Ã£o continuam abertas; objetivo ativo.

**AtualizaÃ§Ã£o V-155 (24/09/2026):** atividade abre ConciliaÃ§Ã£o filtrada pelo arquivo autorizado, com busca/paginaÃ§Ã£o persistentes e retorno ao contexto. 57 testes focados e 9 apÃ³s ampliar o cenÃ¡rio passaram; checagens tÃ©cnicas passaram. ApresentaÃ§Ã£o das decisÃµes, validaÃ§Ã£o visual indisponÃ­vel via Playwright e demais pontes/homologaÃ§Ãµes permanecem pendentes.

**AtualizaÃ§Ã£o V-156 (24/09/2026):** histÃ³rico de decisÃµes exposto no movimento, com evidÃªncia escapada, paginaÃ§Ã£o e indicaÃ§Ã£o de legado. Perfil consultivo nÃ£o recebe formulÃ¡rios de escrita. 57 testes focados passaram; checagens tÃ©cnicas passaram. ValidaÃ§Ã£o visual, concorrÃªncia/volume, demais pontes e homologaÃ§Ãµes continuam abertas.

**AtualizaÃ§Ã£o V-157 (24/09/2026):** importaÃ§Ã£o de totais da folha passou a alimentar a comparaÃ§Ã£o existente, com confirmaÃ§Ã£o, documento informado, campos ausentes e referÃªncia preservada. 902 testes aprovados, 2 ignorados, 23 subtestes. Migration 0059 sÃ³ em testes. LigaÃ§Ã£o com atividades, prÃ©via detalhada e homologaÃ§Ãµes permanecem pendentes; meta ativa.

**AtualizaÃ§Ã£o V-158 (24/09/2026):** fotografias da folha geram atividade por empresa/competÃªncia, com reabertura e confirmaÃ§Ã£o humana vigente; replay nÃ£o duplica. 903 testes aprovados, 2 ignorados, 23 subtestes. Migration 0060 sÃ³ em testes. NavegaÃ§Ã£o contextual, prÃ©via detalhada, demais pontes e validaÃ§Ãµes externas continuam pendentes.

**AtualizaÃ§Ã£o V-159 (24/09/2026):** atividade da folha abre ficha/seletores restritos Ã  competÃªncia, com retorno para evidÃªncia e conclusÃ£o humana. 106 testes focados e 8 subtestes passaram. PrÃ©via detalhada, demais pontes e validaÃ§Ã£o visual/externa continuam pendentes; objetivo ativo.

**AtualizaÃ§Ã£o V-160 (24/09/2026):** prÃ©via da folha mostra linhas paginadas e valores originais antes de confirmar, restrita Ã  administraÃ§Ã£o. 80 testes focados passaram. Outras pontes, fontes reais e validaÃ§Ã£o visual/externa continuam pendentes.

**AtualizaÃ§Ã£o V-161 (24/09/2026):** mensagens DTE persistidas geram anÃ¡lise humana na central, com evidÃªncia de consulta, bloqueio por resultado incerto, carteira vigente e recuperaÃ§Ã£o sem chamada externa. Migration 0061 somente em testes. RegressÃ£o: 907 aprovados e 2 ignorados; checagens tÃ©cnicas passaram. NavegaÃ§Ã£o contextual DTE, demais pontes e validaÃ§Ãµes visuais/externas continuam pendentes; objetivo ativo.

**AtualizaÃ§Ã£o V-162 (24/09/2026):** confirmaÃ§Ã£o humana anterior Ã  abertura DTE nÃ£o satisfaz conclusÃ£o; novo recibo reabre anÃ¡lise antiga, e recuperaÃ§Ã£o preserva confirmaÃ§Ã£o posterior vÃ¡lida. 48 testes/8 subtestes e checagens tÃ©cnicas passaram. Sem nova migration. Demais pendÃªncias de V-161 continuam abertas.

**AtualizaÃ§Ã£o V-163 (24/09/2026):** atividade DTE e resumo da mensagem conectados com retorno e permissÃµes; navegar nÃ£o abre teor ou gera consumo. Testes DTE finais 11 aprovados; workspace aprovado na rodada conjunta e checagens tÃ©cnicas passaram. InspeÃ§Ã£o visual sem transporte Playwright; demais pontes e homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-164 (24/09/2026):** Radar vincula publicaÃ§Ã£o a empresa por escolha humana, com atividade, versÃ£o/prova, reabertura, recuperaÃ§Ã£o local e percurso de tela. Falha atual da coleta nÃ£o Ã© ocultada por sucesso anterior. Migration 0062 sÃ³ em testes. RegressÃ£o 915/2/23; 9 testes apÃ³s correÃ§Ã£o visual de estado passaram. ValidaÃ§Ã£o visual indisponÃ­vel, PostgreSQL/volume e demais pontes/homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-165 (24/09/2026):** serviÃ§o e worker DCTFWeb revalidam solicitante/carteira/mÃ³dulo, recusando acesso revogado antes da chamada e liberando reserva nÃ£o executada. 29 testes e checagens tÃ©cnicas passaram. Sem migration/UI. Guias/parcelamentos, integraÃ§Ã£o com fechamento e demais homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-166 (24/09/2026):** guias e PARCSN tambÃ©m revalidam autorizaÃ§Ã£o antes de reservar/executar. RegressÃ£o 929 aprovados, 2 ignorados, 23 subtestes; checagens tÃ©cnicas passaram. Identificada e registrada lacuna no retorno incerto de emissÃ£o de guias, ainda reemitÃ­vel e com reserva liberada. Prioridade seguinte: corrigir esse fluxo antes de homologaÃ§Ã£o, seguido das pontes com fechamentos e validaÃ§Ãµes restantes.

**CorreÃ§Ã£o D-149 / V-167 (24/09/2026):** proprietÃ¡rio permite reemissÃ£o com custo adicional por guia e exige consulta antes de novas regras de fluxo/cobranÃ§a. Bloqueio provisÃ³rio de D-148 nÃ£o Ã© soluÃ§Ã£o aprovada. Confirmar modalidade do adicional e substituir o bloqueio pelo fluxo de reemissÃ£o cobrada com histÃ³rico preservado. Testes tÃ©cnicos do estÃ¡gio provisÃ³rio nÃ£o comprovam atendimento dessa regra; implementaÃ§Ã£o permanece aberta.

**AtualizaÃ§Ã£o V-168 (24/09/2026):** preservaÃ§Ã£o tÃ©cnica das tentativas implementada, com histÃ³rico imutÃ¡vel e retorno criptografado; protocolo antigo nÃ£o Ã© reutilizado na nova tentativa. Migration 0064 somente em testes. RegressÃ£o 935 aprovados, 2 ignorados, 23 subtestes. ApresentaÃ§Ã£o do histÃ³rico, reemissÃ£o/cobranÃ§a de D-149, recuperaÃ§Ã£o e demais pontes/validaÃ§Ãµes continuam pendentes; meta ativa.

**AtualizaÃ§Ã£o V-169 (24/09/2026):** histÃ³rico de tentativas exposto na ficha, com paginaÃ§Ã£o e download de PDF anterior sem nova chamada. 28 testes finais de guias passaram; checagens tÃ©cnicas passaram. InspeÃ§Ã£o visual sem transporte Playwright. ReemissÃ£o/cobranÃ§a D-149, recuperaÃ§Ã£o, demais pontes e homologaÃ§Ãµes continuam abertas; meta ativa.

**AtualizaÃ§Ã£o V-170 (24/09/2026):** consulta de Guias/Integra passou a exigir mÃ³dulo e empresa na mesma concessÃ£o, corrigindo acesso cruzado entre mÃ³dulos da carteira; contador DTE pendente tambÃ©m restrito. RegressÃ£o 939/2/25 e checagens tÃ©cnicas passaram. Sem migration/UI nova. Resultados ainda precisam ser ligados Ã  central e observaÃ§Ãµes aos adaptadores; D-149, recuperaÃ§Ã£o e validaÃ§Ãµes visuais/externas continuam pendentes.

**AtualizaÃ§Ã£o V-171 (24/09/2026):** matriz consolidada do objetivo na etapa 11, com evidÃªncia e lacuna por requisito. Corrigida preservaÃ§Ã£o de evidÃªncia e histÃ³rico de acumuladores apÃ³s nova resoluÃ§Ã£o NFS-e (D-153); 85 testes focados e checagens tÃ©cnicas passaram. Sem migration/UI nova. Guias/DCTFWeb/PARCSN â†’ atividades e adaptadores â†’ observaÃ§Ãµes ainda nÃ£o implementados; D-149 e homologaÃ§Ãµes continuam pendentes.

**AtualizaÃ§Ã£o V-172 (24/09/2026):** superada a ausÃªncia de validaÃ§Ã£o PostgreSQL local: suÃ­te final 942 aprovados, 1 ignorado, 25 subtestes, com reserva e recorrÃªncia concorrentes. Corrigidas falhas de locks em DCTFWeb/PARCSN/Triagem e ciclo de respostas nos testes. ContÃªiner isolado encerrado. Isso nÃ£o homologa provedores, produÃ§Ã£o, volume ou recuperaÃ§Ã£o real. Q-40 aguarda decisÃ£o sobre conclusÃ£o da atividade de emissÃ£o; D-149 e demais ligaÃ§Ãµes continuam pendentes.


**AtualizaÃ§Ã£o V-173 (24/09/2026):** Playwright local com Edge disponÃ­vel, apesar do MCP sem transporte. Central validada em 52 combinaÃ§Ãµes de pÃ¡gina/perfil/tema/viewport, 17 verificaÃ§Ãµes, sem overflow ou erro de console. Capturas desktop/mobile inspecionadas; carteira e leitura do auditor verificadas. NÃ£o foram validados todos os fluxos de alteraÃ§Ã£o, carregamento ou fontes reais. Scripts repetÃ­veis: qa_ui_server.py (QA_REVIEW_SUITE=central), qa_central_fixture.py e qa_central_browser.cjs. Contextos/navegador e servidor encerrados. D-149/Q-40 seguem pendentes; meta ativa.

**AtualizaÃ§Ã£o V-174 (24/09/2026):** D-155 concluiu a ponte local de resultados Serpro para a central: guias, documentos DCTFWeb e operaÃ§Ãµes PARCSN tÃªm atividade, evidÃªncia, estado e recuperaÃ§Ã£o local prÃ³prios. EmissÃ£o nÃ£o significa aceite, pagamento ou fechamento; a regra comercial de reemissÃ£o permanece em D-149 e a conclusÃ£o de emissÃ£o em Q-40. A migration 0065 Ã© aditiva; `sync_serpro_activities` recompÃµe apenas dados persistidos, sem chamada externa. RegressÃ£o final 944/3/25 e validaÃ§Ã£o visual sintÃ©tica 64 telas/21 verificaÃ§Ãµes. Fontes reais, recuperaÃ§Ã£o cronometrada, volume, transmissÃ£o aprovada e piloto continuam nas etapas de homologaÃ§Ã£o.

**AtualizaÃ§Ã£o V-175 (24/09/2026):** revisÃ£o do agente e de documentaÃ§Ã£o oficial confirmou que a central nÃ£o recebe estado DomÃ­nio de fechamento/reabertura ou aceite: agente atual envia empresas e guias calculadas; `FOVGUIAINSS.SITUACAO` nÃ£o possui mapeamento semÃ¢ntico homologado. Foi registrado o contrato tÃ©cnico mÃ­nimo antes de ampliar leitura, sem criar consulta ou integraÃ§Ã£o fictÃ­cia. Separar fechamento de competÃªncia, S-1299 e DCTFWeb continua obrigatÃ³rio. PrÃ³ximo bloqueio objetivo: validar esse contrato no ambiente DomÃ­nio autorizado; Siescon segue dependente de Q-33.

**AtualizaÃ§Ã£o V-176 (24/09/2026):** recuperaÃ§Ã£o unificada local da central implementada por `recover_operational_center --organization`, para NFS-e, Triagem, ConciliaÃ§Ã£o, folha, DTE, Radar e resultados Serpro jÃ¡ persistidos. NÃ£o chama fonte, nÃ£o emite/transmite, nÃ£o provoca ciÃªncia nem consome saldo; falhas de uma ponte sÃ£o reportadas sem impedir as demais. Teste focado: 15 aprovados. RecuperaÃ§Ã£o cronometrada com dados reais, fontes e piloto continuam pendentes.

**AtualizaÃ§Ã£o V-177 (24/09/2026):** a atividade concluÃ­da agora mantÃ©m o formulÃ¡rio de evidÃªncia para correÃ§Ãµes auditÃ¡veis, mas nÃ£o mostra controles de impedimento ou uma segunda conclusÃ£o, que o serviÃ§o jÃ¡ recusa. A jornada sintÃ©tica percorreu registrar evidÃªncia, concluir, conferir a trilha e retornar Ã  agenda em 390 px, sem overflow ou erro de console. Testes focados: 45 aprovados e 8 subtestes; Django check, migraÃ§Ãµes, Ruff e sintaxe do navegador passaram. A validaÃ§Ã£o usa Edge/Playwright local porque o MCP Playwright e a consulta direta ao Watermelon continuam indisponÃ­veis nesta sessÃ£o; nÃ£o substitui piloto, fontes reais, falhas de rede ou a regra comercial pendente D-149.

**Atualizacao V-178 (24/09/2026):** regressao local integral passou com 948 testes, 3 ignorados e 25 subtestes em 81,08 s. Ela inclui a central, seus modulos e os testes novos de estado concluido/dispensado, mas nao substitui a homologacao de fontes, o piloto, volume, recuperacao cronometrada ou as decisoes D-149/Q-40. Nenhuma chamada externa, custo ou publicacao ocorreu.

**Atualizacao V-179 (24/09/2026):** D-157 fecha uma brecha na base de observacoes: a fonte so altera processamento ou obrigacao se declarar a capacidade tecnica especifica e esta declaracao e relida sob lock. Falha sem estado continua registravel como indisponibilidade. Os testes cobrem recusa sem capacidade, remocao concorrente da capacidade e fonte desativada, preservando atividade e historico vazios; adaptadores reais e mapeamentos semanticos continuam pendentes. Regressao integral apos a mudanca: 949 aprovados, 3 ignorados e 25 subtestes em 80,61 s.

**Atualizacao V-180 (24/09/2026):** a prova da recuperacao unificada passou de um unico caso NFS-e para NFS-e, guia, documento DCTFWeb e operacao PARCSN persistidos no mesmo escritorio. Um unico comando cria/recompoe as quatro atividades, informa cada contagem e a repeticao nao duplica registros. Teste focado: 17 aprovados. Continua sem consultar fornecedor, emitir, transmitir, consumir saldo ou provar os demais modulos e fontes reais.

**Atualizacao V-181 (24/09/2026):** D-158 consolida a instrucao do proprietario: qualquer custo, tarifa, repasse ou lancamento exige definicao expressa antes de codigo, inclusive a reemissao de guia autorizada em D-149. A validacao da recuperacao unificada agora semeia NFS-e, Triagem, Conciliacao, folha, DTE, guia, documento DCTFWeb e operacao PARCSN, parte desses fatos sem projecao e confirma que um comando recompoe exatamente uma atividade por fato sem provedor e sem duplicacao no replay. Teste focado: 17 aprovados; Django check, migrations e Ruff passaram. Ainda nao prova Radar, fontes reais, tempo de recuperacao, carga, piloto ou a regra comercial da reemissao.

**Atualizacao V-182 (24/09/2026):** a recuperacao local tambem tem prova especifica para Radar: somente uma publicacao previamente escolhida por pessoa cria atividade; o comando reprojeta esse vinculo, informa `radar=1`, nao duplica atividade nem gera novo evento quando a versao nao mudou. Teste focado do conjunto de pontes: 18 aprovados; Ruff, Django check, migrations e diff-check passaram. Isto nao coleta publicacoes, nao cria vinculo por inferencia e nao homologa fontes, carga, recuperacao D-73 ou piloto.

**Atualizacao V-183 (24/09/2026):** D-159 corrige a semantica de fonte desativada: retorno tardio bem-sucedido pode ficar no historico, mas nao atualiza fotografia, situacao da fonte, frescor da atividade, processamento ou obrigacao. Falha tardia ainda registra indisponibilidade sem substituir `disabled`. A reativacao exige acao administrativa explicita. Testes de central e pontes: 51 aprovados e 8 subtestes; Ruff, MyPy da operacao, Django check, migrations e diff-check passaram. Isto continua sem adaptador ERP homologado nem chamada externa.

**Atualizacao V-184 (24/09/2026):** D-160 entrega a reativacao administrativa explicita na configuracao de fontes. Somente owner/admin fora de suporte pode confirmar a acao; ela preserva capacidades e fotografia, muda para `not_configured`, limpa erro operacional e registra os estados antes/depois. Nao consulta fonte nem torna dados atuais. Testes isolados de owner e perfil sem permissao passaram. UI auditada com UI/UX Pro Max, Watermelon (Agndex), Refero Basedash, SaaSFrame Prelude e referencias Karbon; Web Interface Guidelines revisadas. Playwright local/Edge: 66 telas e 24 verificacoes, desktop/mobile, foco de teclado, overflow e console sem erro; navegador e servidor QA encerrados. Adaptadores ERP e reemissao D-149 continuam pendentes.

**Atualizacao V-185 (24/09/2026):** D-161 fecha a atribuicao recorrente fora da carteira. Antes de materializar, o motor verifica que modelo, atribuicao e empresa pertencem ao mesmo escritorio e que o responsavel tem perfil operacional, vinculo ativo e carteira atual. Atribuicao antiga invalida gera atividade sem responsavel e evento explicavel, preservando o registro original; formulario administrativo recusa nova selecao incompativel. Testes de central: 36 aprovados e 8 subtestes; recorrencia: 7 aprovados, 1 ignorado por exigir locks PostgreSQL e 4 subtestes. Ruff, MyPy, Django check, migrations e diff-check passaram. Playwright/Edge: 70 telas e 28 verificacoes, inclusive modelos em desktop/celular, sem erro de console ou overflow; servidor/navegador QA encerrados.

**Atualizacao V-186 (24/09/2026):** a ficha da empresa passou a aplicar a mesma ordenacao de prazo efetivo da agenda e da fila (D-124): prazo interno quando existir, prazo legal quando nao existir e itens sem prazo ao final, com desempate estavel. O teste de view cobre prazo legal vencido antes de prazo interno futuro. A revisao visual sintetica incluiu a ficha em 1440/390 px para owner, operador e auditor; nenhuma chamada externa, regra comercial ou alteracao de contrato foi feita.

**Atualizacao V-187 (24/09/2026):** D-162 reforca a escrita de atividades: evidencia, impedimento, conclusao e distribuicao relêem o vinculo atual, o usuario ativo, o perfil e a carteira antes de persistir. Revogacao ou troca de papel entre exibicao e POST nao permite usar o objeto antigo; distribuicao exige owner/admin atual. Teste do centro: 38 aprovados e 12 subtestes. Sem interface, fonte externa, custo ou regra comercial nova.

**Complemento V-187 (24/09/2026):** regressão HTTP da área do escritório: `tests/test_hub_workspace_views_django.py` aprovou 76 testes em 59,27 s, cobrindo carteira, detalhes e POSTs das atividades após a revalidação de vínculo.

**Regressao integral V-187 (24/09/2026):** `pytest -q` passou com 962 aprovados, 3 skips conhecidos e 29 subtestes em 91,62 s. Os skips permanecem Playwright Python opcional e cenarios de locks PostgreSQL cobertos no ambiente proprio; o resultado nao homologa fontes externas, recuperacao cronometrada, volume, piloto ou D-149.

**AtualizaÃ§Ã£o V-188 (24/09/2026):** landing pÃºblica revisada conforme D-163: proposta sobre pendÃªncias e responsÃ¡veis, pauta ilustrativa, recursos compactos, integraÃ§Ãµes contextualizadas e FAQ antes do CTA. Pesquisa/Watermelon/guidelines concluÃ­dos; Playwright MCP disponÃ­vel e usado em 12 combinaÃ§Ãµes de tamanho/tema, com teclado, navegaÃ§Ã£o e sem JS; 27 testes aprovados. Browser e QA encerrados. [Resumo e referÃªncias](docs/cica-landing-review-2026-09-24.md). NÃ£o altera preÃ§os nem declara conversÃ£o, publicaÃ§Ã£o ou homologaÃ§Ã£o comercial; etapa 11 conserva pendÃªncias fora da landing.

**AtualizaÃ§Ã£o V-189 (24/09/2026):** corrigido o agente DomÃ­nio Local para concluir a paginaÃ§Ã£o de empresas e entÃ£o sincronizar os extratos bancÃ¡rios jÃ¡ permitidos, em vez de retornar antes dessa segunda etapa. TambÃ©m foi corrigida a chamada autenticada de download que impedia a compilaÃ§Ã£o do serviÃ§o Windows. A build .NET Release passou sem avisos; 43 testes Python focados do agente/central, Ruff, MyPy, Django check e migraÃ§Ãµes passaram. NÃ£o houve execuÃ§Ã£o ODBC, envio de dados, publicaÃ§Ã£o de MSI ou homologaÃ§Ã£o de DomÃ­nio.


**Atualização V-190 (24/09/2026):** reconciliado o checklist ativo da central com as entregas verificadas. Agenda pessoal/carteira/gestão, fechamentos agregados, recorrência idempotente, pontes persistidas dos módulos, recuperação unificada, prazo efetivo e revalidação de escrita estão implementados. Permanecem abertas somente as evidências que não podem ser fabricadas localmente: contratos de estados ERP, fontes e transmissões reais, Siescon, carga/concorrência, recuperação cronometrada, piloto e a regra comercial D-149.

**Atualização V-191 a V-193 (24/09/2026):** repetida a verificação da recorrência e da recomposição unificada local: 63 testes e 16 subtestes passaram, com um único skip que exige locks PostgreSQL. A inspeção da central em Edge/Playwright percorreu 82 telas e 40 verificações em três perfis e dois temas, mais cenário móvel em paisagem com movimento reduzido; navegador e servidor isolado foram encerrados. A pesquisa documental confirmou que Domínio separa fechamento interno, reabertura S-1298 e fechamento S-1299, e que o Siescon público não expõe contrato de leitura das tarefas. Manual externo atualizado com os artefatos exigidos para um adaptador. Essas evidências não habilitam estados ERP, fonte real, transmissão, recuperação cronometrada, carga, piloto nem reemissão D-149.

**Atualização V-194 (24/09/2026):** regressão integral do estado atual passou com 962 testes, 3 skips conhecidos e 29 subtestes em 101,79 s. A auditoria adicional do modelo de observações não encontrou nova falha local de replay, conflito, indisponibilidade, retorno tardio ou reabertura. A suíte não prova fonte real, contrato Domínio/Siescon, recuperação medida, volume, piloto ou D-149.

**Atualização V-195 (24/09/2026):** corrigida a landing efetivamente servida em 8000 após detectar dois runservers concorrentes; a instância antiga foi encerrada e a atual preservada. Aplicadas design e ai-design-skills/landing-page-design com Manrope local, sem itálicos/flechas, botões consistentes e FAQ ampliada. Uso da nova skill registrado como obrigatório no AGENTS global. Playwright MCP conferiu desktop/mobile, temas, teclado, foco, links e sem JS; 4 testes focados passaram. V-188 tinha limite de QA isolado; V-195 documenta a verificação da instância real e o encerramento das abas. Não houve publicação nem alteração comercial.

**Atualização V-196 (24/09/2026):** por correção explícita do proprietário, a landing foi reconstruída do zero conforme D-168, sem reutilizar a composição antiga. A nova linguagem usa papel quente, grafite e terracota, com verde restrito a estado positivo; a prova principal é uma central de fechamento inédita em HTML/CSS. Pesquisa de produto, Watermelon e skills de landing/conversão/marca/UI foram aplicadas, e a auditoria atual das guidelines corrigiu contraste e cor do navegador. Playwright MCP validou 6 larguras, dois temas, teclado, FAQ, links, sem JS, console e rede; 27 testes passaram. Abas encerradas e servidor local preservado. Conversão, publicação e homologações externas continuam fora da evidência.

**Atualização V-197 (24/09/2026):** removidos os três benefícios numerados e os três cards de disponibilidade rejeitados pelo proprietário. A rotina agora demonstra uma atividade concreta com contexto completo; Domínio, Integra Contador, e-mail e Siescon aparecem em uma faixa única como partes prontas do produto, com copy e FAQ consistentes. Auditoria atual corrigiu um contraste residual; Playwright MCP aprovou 12 combinações, sem overflow, roadmap ou console error, e 4 testes focados passaram. Abas fechadas e servidor 8000 preservado.

**Atualização V-198 (25/09/2026):** iniciada a homologação sobre os dados reais autorizados da Fedrizzi. Leituras ODBC allowlisted trouxeram 576 empresas, 10.000 registros normalizados e 3.335 cálculos de guia sem vencimento no contrato atual; não houve escrita no Domínio. O Console habilitou os sete módulos, sem ativar provedor de IA ou consumo. A área operacional permanece bloqueada, de modo correto, por ausência de contrato vigente. Agenda e fluxos autenticados dependem de contrato de homologação sem cobrança ou contrato real definido pelo responsável; não foi inventado preço, prazo ou cobrança.

**Atualização V-199 (25/09/2026):** D-170 transforma Fedrizzi em parceiro interno de homologação: Developer/Admin marca a condição no Console, o escritório opera sem contrato comercial e sem cobrança, e desligar exige confirmação e volta à ativação pendente quando não há contrato. A condição não é demo, não desbloqueia IA/Serpro/transmissões e foi aplicada à Fedrizzi: 576 empresas, sete módulos, zero contrato comercial. O Console, Integrações e agenda foram revisados em navegador real; a copy errada de teste de 14 dias foi corrigida. A pauta permanece vazia até que modelos e prazos sejam definidos sem inferir vencimentos ausentes.

## V-200 — Prévia navegável das áreas da landing

25/09/2026. D-171 tornou a prova de produto da landing uma demonstração navegável. `home.html` agora apresenta tabs nativas para Central, Meu trabalho, Empresas, Documentos, Fiscal e Conciliação; cada uma exibe um recorte de trabalho consistente, inteiramente fictício. `cica-product-demo.js` controla o estado acessível, as setas Home/End/esquerda/direita, a âncora compartilhável `#demonstracao-*` e o retorno pelo histórico do navegador. Sem JavaScript, Meu trabalho continua renderizado como a tela inicial. A demonstração não autentica, não consulta a Fedrizzi nem qualquer outra fonte, e não tem ações que escrevem ou geram consumo.

UI/UX Pro Max foi aplicado para estado ativo, URL refletindo a tela e foco de teclado. Watermelon MCP não estava exposto nesta sessão. A pesquisa de referências usou [Karbon](https://karbonhq.com/solution/project-management) para a pauta por responsável, cliente e prazo, [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para a hierarquia de navegação lateral, e [Asana](https://help.asana.com/s/article/reporting-with-dashboards) para a leitura de tarefas e estados. Foram adaptados somente hierarquia, densidade e feedback; nenhuma interface, texto proprietário ou dado externo foi copiado.

A fonte atual das Web Interface Guidelines foi relida e a auditoria de `home.html`, `cica-landing.css` e `cica-product-demo.js` não encontrou violação material: buttons nativos, `tablist`/`tabpanel`, foco visível de 3 px, hover, movimento reduzido, texto com quebra e URL do estado. O MCP Playwright não estava disponível; a validação equivalente local em Edge percorreu as seis telas em 1440 e 390 px, clique, teclado, deep-link, retorno do histórico, contexto sem JavaScript e console. Não houve overflow horizontal nem erro de console. Capturas inspecionadas: `.playwright-mcp/landing-review/demo-desktop.png` e `demo-mobile.png`; contextos e browser foram fechados.

`pytest tests/test_cica_landing_django.py -q`: 4 aprovados em 65,30 s. `manage.py check --settings=config.settings.local`, sintaxe Node e `git diff --check` dos arquivos de escopo passaram. Limites: isto valida uma apresentação fictícia, não permissões, dados, operações ou resultados dos módulos autenticados.

## V-201 — Camada visual autenticada alinhada à landing

25/09/2026. D-172 substituiu a linguagem visual compartilhada das telas autenticadas sem tocar seus comportamentos. `cica-auth.css` e `cica-brand.css` agora aplicam Manrope local, papel quente, grafite, terracota, campos, botões, foco e feedback coerentes em login, cadastro, convites, recuperação e MFA. `workspace.css` aplica os mesmos tokens a todo o shell autenticado: cabeçalho, navegação, formulários, painéis, tabs, mensagens, setup e módulos que herdavam o tema anterior. Verde segue restrito a estados positivos. As URLs, forms, permissões, dados, integrações e gates operacionais foram preservados.

UI/UX Pro Max orientou hierarquia de onboarding, foco e configuração responsiva. Watermelon MCP não estava disponível. Referências: [Karbon](https://karbonhq.com/resources/videos/karbon-practice-management-best-practices-how-other-firms-are-using-karbon/) para setup de prática, [Asana](https://asana.com/resources/collections/getting-started-with-asana) para onboarding guiado e [SaaSFrame](https://www.saasframe.io/examples/latitude-project-dashboard) para hierarquia de workspace. Foram adaptados apenas padrões de densidade, orientação e estados, dentro da identidade CICA.

A validação local em Edge abriu login, cadastro, visão geral e configuração da Fedrizzi em 1440 e 390 px. Em todas as oito combinações: sem overflow horizontal, foco visível de 3 px e console sem erros. A configuração e a área de trabalho usaram o escritório parceiro interno Fedrizzi e não chamaram fonte, IA, Serpro ou cobrança. Capturas: `.playwright-mcp/d172-login-final.png`, `d172-final-signup-desktop.png`, `d172-final-workspace-desktop.png` e `d172-final-setup-mobile.png`. A fonte atual das Web Interface Guidelines foi aplicada: controles nativos, foco, responsividade, texto longo, movimento reduzido e estado de navegação na URL permanecem cobertos. O MCP Playwright não estava exposto; os contextos equivalentes locais foram fechados.

Validação automatizada em andamento nesta entrada: `test_cica_auth_flow.py`, `test_cica_signup_flow.py` e `test_hub_workspace_views_django.py`; `manage.py check --settings=config.settings.local` e `git diff --check` passaram. Limite: a camada compartilhada transforma a aparência de todas as telas que a consomem; refinamentos de estrutura específica continuam necessários se uma tela especializada revelar um problema em uso real.
**Atualização V-218 (29/09/2026):** release 21 publicou fila NFS-e de uma empresa por vez, checkpoints NSU por página e classificação diretamente na lista agrupada por empresa. A Bianchi chegou a 1.746 documentos; a retomada verificada terminou em NSU 50/50 sem erro/retry. A tela usa competência anterior e apenas Classificadas/Não classificadas. O ZIP continua como conferência até o layout Domínio de Q-39 ser homologado.

**Atualização V-219 (29/09/2026):** a lista NFS-e passou a mostrar o número fiscal, corrigir acumulador com salvamento automático e preservar cada decisão em cadeia imutável. O lote seleciona nota, empresa, página ou todos os classificados do filtro e informa a abrangência antes do download. A validação focal teve 19 testes aprovados e Playwright cobriu desktop/celular, teclado, foco, movimento reduzido, overflow e console. Q-39 permanece aberta: o ZIP é pacote de conferência, não importação Domínio homologada.

**Atualização V-220 (30/09/2026):** produção está na release Fly 27 usando Neon para os bancos principal e knowledge, com Fly responsável por web, worker e Valkey e o banco antigo preservado para rollback. A Bianchi tem 14.452 NFS-e persistidas e as 56 sincronizações já registraram sucesso. A tag `ACU` em qualquer profundidade foi validada com XML real sem alterar o original; o detalhe de empresa pausada também foi corrigido. Q-39 continua bloqueando somente a declaração de importação Domínio homologada.

**Atualização V-221 (30/09/2026):** a máquina do PostgreSQL legado do Fly foi parada. Produção usa somente Neon para os bancos principal e knowledge; health, web, worker e consultas pelos dois aliases permaneceram saudáveis após o desligamento. A máquina e o volume antigos não foram destruídos e continuam como rollback recuperável.

**Atualização V-222 (30/09/2026):** D-210 removeu wake-ups artificiais do Neon sem alterar processamento normal. O Fly usa liveness no balanceador, readiness continua disponível para dependências, recuperações ficam alinhadas a cada 15 minutos e integrações desativadas não recebem agenda. O endpoint Neon suspende após 300 segundos ociosos e preserva autoscaling 0,25–1 CU. A release 31 terminou com web, worker, Celery, banco principal, knowledge e cache saudáveis.

**Atualização V-246 (01/10/2026):** D-213 publicou a release 33 e povoou somente a demo com 84 atividades, seis modelos, três personas, 60 evidências e 168 eventos fictícios. Meu trabalho mostra nove tarefas; Carteira/Gestão mostram 33 abertas. Replay criou zero duplicatas. Regressão local: 1.046 aprovados e 139 subtestes, cinco skips PostgreSQL; Playwright conferiu produção desktop/mobile, teclado, estados e console. Não constitui homologação fiscal nem conclusão das demais pendências. [Detalhes](docs/cica-demo-population-2026-10-01.md).

**Atualização V-249 (01/10/2026):** D-217 simplificou a coleta NFS-e para situação, próximo passo e fila por empresa, com demo declaradamente simulada e ações isoladas por sessão. Empresa sem A1 válido não ativa; configuração virou detalhe secundário. Onze testes focados e verificações estáticas passaram; Playwright local cobriu desktop/mobile e estados. A release 43 foi publicada saudável após rollback seguro de uma tentativa com manifesto incompleto. A sessão demo publicada confirmou dashboard com nove abertas, assets novos e fila 200. Q-39, fonte real, carga e piloto seguem abertos.

**Atualização V-272 (03/10/2026):** D-271 transformou os fechamentos por competência em uma fila de conferência: resumo da página, exceções antes de pendências comuns, próximo passo e ação direta por empresa/área, concluídos separados e lacunas de cobertura sem falso positivo. Competência inválida agora retorna recorte vazio e foco no erro, sem trocar silenciosamente de mês. Playwright MCP validou desktop/mobile, tema escuro, movimento reduzido, teclado, detalhe, navegação, erro, overflow e console; 1.095 testes e 145 subtestes passaram, com seis skips explícitos. Fontes e critérios reais do escritório piloto continuam pendentes.

**Atualização V-261 (03/10/2026):** D-231 transformou a importação manual e a prévia da folha em uma jornada explícita de escolha, envio e confirmação. O lote inteiro é pré-validado sem escrita, linhas problemáticas recebem diagnóstico acionável e não oferecem confirmação, duplicatas concluídas voltam ao histórico e somente o formulário efetivamente enviado é validado. A homologação de layouts reais CSV/XLSX continua sendo dependência externa e não foi presumida.

**Atualização V-262 (03/10/2026):** D-232 transformou a conferência agregada da folha em uma jornada iniciada pela competência. A ficha mostra pessoas, bruto, descontos, encargos e líquido de cada fonte, oferece uma única ação por mês comparável, limita os seletores à competência aberta e expressa cada divergência como valor a mais ou a menos. A comparação permanece somente leitura, sem cálculo, dados de trabalhador ou conclusão automática da atividade. Layouts reais e critérios operacionais do escritório piloto continuam dependendo de homologação externa.

**Atualização V-263 (03/10/2026):** D-233 reaudita a Caixa Postal DTE como uma caixa de trabalho contábil: assunto sem ação duplicada, um único “Abrir resumo”, filtros e ações legíveis, histórico em cartões no celular e separação explícita entre resumo local e abertura que pode produzir ciência. A demo continua isolada por sessão e não consulta o Serpro. Credenciais, contrato e fluxo DTE real autorizado permanecem dependências externas antes de qualquer homologação.

**Atualização V-264 (03/10/2026):** D-234 transforma o Radar de uma tabela horizontal em uma fila de triagem. Fonte, tema, data, resumo e limite fiscal ficam juntos; “Analisar impacto” conduz à escolha humana de empresa e motivo, enquanto perfis consultivos recebem “Ver análises”. A carteira extensa ganhou filtro local sem perder o `select` nativo e a tela preserva o retorno aos filtros. Coleta real, completude das fontes e validação de aplicabilidade continuam dependências externas.
## Atualização V-267 — Parcelamentos orientados ao trabalho contábil (03/10/2026)

D-267 reorganiza Parcelamentos pela tarefa empresa → acordo → parcela → DAS. A empresa em foco e o próximo passo vêm antes da carteira; consultas, emissões e lotes têm revisão explícita de escopo/consumo; estados do fornecedor recebem orientação segura; resultado incerto exige conferência humana no e-CAC; e a demo gera PDF inequivocamente fictício, privado à sessão. Desktop, mobile, landscape, tema escuro, movimento reduzido, lote, vazio, teclado, foco, overflow e console foram validados localmente. Homologação Serpro real, contrato, credenciais e regras fiscais/comerciais continuam externas.

## Atualização V-269 — Ficha de atividade orientada à decisão (03/10/2026)

D-268 reorganiza o detalhe da atividade por contexto, próximo passo, condições de conclusão,
responsável, evidências e trilha. Ações concorrentes foram separadas, entradas inválidas permanecem
na tela e a conclusão exige revisão. No estado impedido, a revisão explica que concluir com as
condições atendidas resolve o impedimento e preserva a trilha. Perfis consultivos não recebem
controles de escrita. A homologação de fluxos originados por integrações reais permanece externa.

## Atualização V-270 — Central de atividades como fila de decisão (03/10/2026)

D-269 transforma a lista em fila de trabalho em aberto: prioridades visíveis, um único refinamento,
filtros removíveis e URL canônica. Cada item apresenta próximo passo, prazo relativo/exato,
responsável e situação; encerradas exigem filtro explícito. Filtro inválido retorna recorte vazio e
orientação, nunca amplia a consulta. Desktop, mobile, landscape, temas, teclado, foco, erro, vazio,
Owner/Auditor, histórico do navegador, overflow e console foram validados localmente. Fontes reais
e critérios do escritório piloto continuam dependências externas, não pendências desta interface.
**Atualização V-271 (03/10/2026):** Modelos de atividades passaram a funcionar como biblioteca operacional com cobertura agregada, configuração progressiva, paginação e erro recuperável para atribuição repetida. Pausa/retomada preserva histórico; geração manual usa apenas rotinas mensais ativas. Validação focada aprovou 144 testes e 23 subtestes; regressão integral aprovou 1.095 testes e 145 subtestes, com seis skips explícitos. Playwright MCP percorreu o fluxo completo em desktop/mobile/paisagem, tema escuro e movimento reduzido, após corrigir compressão desktop e altura mobile. A definição dos modelos, prazos, responsáveis e critérios reais continua dependente de homologação do escritório; nenhuma publicação foi feita.

**Atualização V-273 (03/10/2026):** D-272 transforma o cadastro de empresas em carteira de ação:
prioridades visíveis, filtros progressivos, próximo passo e destino direto por empresa. Ausência de
código Domínio pode ser isolada e qualquer filtro inválido retorna zero resultados com erro focado,
sem ampliar a carteira. Cadastro inválido preserva os campos. Playwright MCP validou
desktop/mobile/paisagem, temas, movimento reduzido, teclado, modal, erro, vazio, alvos, overflow e
console final limpo. Regressão integral: 1.097 testes e 145 subtestes aprovados, com seis skips
explícitos. Edição/sincronização do cadastro com Domínio real permanece dependência de homologação;
nenhum deploy foi feito.

**Atualização V-274 (05/10/2026):** D-274 publicou a rotina idempotente que reavalia todas as NFS-e
pela fotografia real do backup e escreve somente evidência derivada. Em produção, 29.042 notas foram
percorridas: 4.656 possuem correspondência segura, 16 receberam nova classificação, 4.640 já estavam
corretas e 24.386 permaneceram explicitamente em revisão. Foram criadas 39 revisões, atualizadas 666
sugestões e resolvidas 16 com origem `backup`; nenhuma decisão humana foi substituída. Os 16 XMLs
derivados respeitam `infNFSe/valores/acum`, sem `ACU`, e a segunda passagem criou zero registros.
Release 45 e dependências terminaram saudáveis. Q-39 e os casos ambíguos continuam externos.
