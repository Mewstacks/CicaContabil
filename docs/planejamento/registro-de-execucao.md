# Registro de execução da meta operacional

## 21/09/2026 — PDF corrompido recusado antes da conciliação (V-098)

- A validação passou a abrir PDF e a verificar o limite de 500 páginas antes de
  persistir a fonte. Arquivo malformado retorna mensagem clara sem criar lote ou
  processamento inválido; o caminho de OCR local continua disponível quando o
  parser opcional não está instalado.
- Foram aprovados 42 testes focados (um skip de OCR), Ruff e MyPy do serviço; a
  suíte integral fechou com 784 testes, três skips e 11 subtestes. Não houve
  OCR, arquivo real, ERP, integração ou serviço externo.

## 21/09/2026 — XLSX corrompido recusado antes da conciliação (V-097)

- A validação de entrada passou a abrir XLSX antes de criar a fonte. Arquivo com
  extensão e assinatura compatíveis, mas corrompido, é rejeitado com mensagem
  clara, sem fonte, lote ou processamento persistido.
- A prévia CSV passou a ler apenas as 51 linhas que exibe, sem materializar todo
  o conteúdo somente para cortar a amostra visual.
- Foram aprovados 41 testes focados (um skip de OCR), Ruff e MyPy do serviço; a
  suíte integral fechou com 783 testes, três skips e 11 subtestes. Não houve
  arquivo real, OCR, ERP, integração ou serviço externo.

## 21/09/2026 — código operacional de Jornadas removido (V-096)

- Em complemento à V-095 e conforme D-43, formulários, views e template
  operacionais órfãos de Jornadas foram removidos. Enum, modelos, tabelas e
  migrações históricos permaneceram intactos; não houve migração destrutiva.
- A busca de referências confirmou que não há rota, vínculo de navegação,
  formulário, view ou template ativo. O teste mantém as cinco rotas legadas
  como 404 em GET e POST e confirma a ausência do módulo no catálogo.
- Foram aprovados 73 testes focados, Ruff, MyPy global, Django e migrações; a
  suíte integral fechou com 781 testes, três skips e 11 subtestes. Não houve
  cobrança, integração ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 102 alterações locais existentes foram preservadas.

## 21/09/2026 — Jornadas removida do catálogo do produto (V-095)

- A definição de Jornadas foi removida do catálogo efetivo da CICA em
  conformidade com D-43. Enum, tabelas e migrações ficaram preservados para
  histórico, sem rota, navegação ou oferta acessível.
- Os testes confirmaram as cinco rotas legadas como 404 para GET e POST, a
  ausência na navegação e a ausência no catálogo, sem alterar contrato ou dado.
- Foram aprovados 73 testes focados, Ruff, MyPy global, Django e migrações; a
  suíte integral fechou com 781 testes, três skips e 11 subtestes. Não houve
  cobrança, integração ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 101 alterações locais existentes foram preservadas.

## 21/09/2026 — páginas independentes na Caixa DTE (V-094)

- A paginação de mensagens passou a preservar a página do histórico DTE,
  filtros e empresa; o histórico já preservava a página de mensagens. As duas
  listas não se reiniciam mais ao navegar.
- O teste com 31 resultados DTE e 26 mensagens sintéticas confirmou a segunda
  página e os vínculos de ida e volta de ambas, sem preparar, enviar ou cobrar
  consulta.
- Foram aprovados 10 testes focados, Ruff, MyPy global, Django e migrações; a
  suíte integral fechou com 781 testes, três skips e 11 subtestes. Não houve
  Serpro, arquivo, consumo, cobrança ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alterações locais existentes foram preservadas.

## 21/09/2026 — fila OFX preserva o contexto da Conciliação (V-093)

- A fila OFX × Domínio passou a conservar páginas de Processamentos, Movimentos
  e Exportações, além de seus próprios filtros; percorrê-la não reinicia as
  outras três áreas.
- O teste chegou à terceira página de 101 correspondências sintéticas com as
  demais páginas selecionadas e validou o retorno, sem importar, conciliar,
  reprocessar ou exportar arquivo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migrações; a suíte integral fechou com 781 testes, três skips e 11
  subtestes. Não houve ERP, arquivo, OCR real ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alterações locais existentes foram preservadas.

## 21/09/2026 — páginas independentes na Conciliação (V-092)

- A paginação dos movimentos normalizados agora preserva as páginas abertas de
  Processamentos e Exportações e o contexto da Conciliação, sem deslocar uma
  trilha quando a outra é percorrida.
- O teste com 21 processamentos, 21 exportações e 51 movimentos sintéticos
  confirmou a segunda página de cada área e o retorno do movimento, sem importar,
  confirmar, reprocessar ou exportar arquivo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migrações; a suíte integral fechou com 781 testes, três skips e 11
  subtestes. Não houve ERP, arquivo, OCR real ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alterações locais existentes foram preservadas.

## 21/09/2026 — histórico de Triagem recuperável por página (V-091)

- O detalhe de arquivo passou a paginar 20 eventos persistidos por vez, mostrar
  o total e manter ordem cronológica e parâmetros de retorno, sem ocultar
  evidência antiga nem carregar toda a trilha no detalhe.
- O teste com 21 eventos sintéticos confirmou as duas páginas, os vínculos de
  navegação e os eventos dos extremos sem decidir, arquivar ou gerar arquivo.
  A demonstração continua isolada por sessão e não foi usada como prova visual
  de volume; não houve autenticação inserida no navegador.
- Foram aprovados 57 testes focados, Ruff, MyPy global, Django e migrações; a
  suíte integral fechou com 781 testes, três skips e 11 subtestes. Não houve
  caixa, scanner, OCR, agente, serviço externo ou custo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 99 alterações locais existentes foram preservadas.

## 21/09/2026 — candidatos de conciliação recuperáveis por página (V-090)

- O detalhe de movimento não limita mais a 50 os candidatos de conciliação:
  percorre o recorte existente em páginas de 25 e informa o total avaliado,
  mantendo confirmação humana e evidência obrigatória.
- O teste com 51 candidatos sintéticos confirmou as três páginas; a sessão
  fictícia percorreu a segunda em 390 px, sem overflow horizontal ou erro de
  console. Não houve conciliação confirmada, arquivo, ERP ou serviço externo.
- Foram aprovados 39 testes focados (um skip de OCR), Ruff, MyPy global, Django
  e migrações; a suíte integral fechou com 780 testes, três skips e 11
  subtestes. O banco temporário foi movido à Lixeira de forma recuperável.
- O fetch final manteve `HEAD` e `origin/main` no mesmo commit (0/0), sem pull,
  commit ou push; as 98 alterações locais foram preservadas.

## 21/09/2026 — acumulador NFS-e validado por empresa (V-089)

- A decisão da revisão NFS-e agora aceita somente código já cadastrado em regra
  vigente ou histórico observado da mesma empresa; códigos inexistentes e de
  outras empresas são recusados, sem criar regra ou lançamento.
- Foram aprovados 95 testes focados, Ruff, MyPy global e a suíte integral com
  779 testes, três skips e 11 subtestes. Não houve ADN, certificado, custo ou
  serviço externo; o banco temporário foi movido à Lixeira de forma recuperável.
- A demonstração fictícia confirmou a lista local de acumuladores na decisão
  NFS-e em desktop e 390 px, sem overflow horizontal nem erro de console; ela
  não foi usada como prova de catálogo real. O fetch final manteve `HEAD` e
  `origin/main` no mesmo commit (0/0), sem pull, commit ou push.

## 21/09/2026 — atenção de egressão recuperável por página (V-088)

- O detalhe do escritório passou a paginar 20 tentativas Claude incertas e a
  exibir seu total, no lugar de ocultar protocolos antigos; os parâmetros da
  tela permanecem nos vínculos entre páginas.
- O teste com 21 auditorias fictícias confirmou a segunda página e o protocolo
  mais antigo sem chamar IA, liberar reserva ou alterar consumo. A inspeção
  visual autenticada não foi automatizada para não inserir credenciais.
- Foram aprovados 57 testes focados, Ruff, MyPy global e a suíte integral com
  778 testes, três skips e 11 subtestes. Não houve provedor, custo ou serviço
  externo; o banco temporário foi movido à Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 96 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — fechamentos adiados recuperáveis por página (V-087)

- A configuração da plataforma passou a paginar 30 fechamentos ainda adiados
  e a exibir seu total, no lugar de cortar a lista em 30 ocorrências; os
  parâmetros da tela permanecem nos vínculos entre páginas.
- O teste com 31 escritórios e ocorrências fictícias confirmou a segunda página
  sem executar fechamento, reserva, faturamento ou mudar contratos. A inspeção
  visual autenticada não foi automatizada para não inserir credenciais.
- Foram aprovados 65 testes focados, com um skip de concorrência PostgreSQL,
  Ruff, MyPy global e a suíte integral com 777 testes, três skips e 11
  subtestes. Não houve Asaas, custo ou serviço externo; o banco temporário foi
  movido à Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 96 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — histórico do Copiloto recuperável por página (V-086)

- O histórico aberto do Copiloto passou a paginar 12 conversas e a exibir seu
  total, no lugar de ocultar todas as conversas anteriores; a conversa em foco
  e a página continuam presentes nos vínculos entre as navegações.
- O teste com 13 conversas fictícias confirmou a segunda página e a seleção da
  conversa mais antiga sem enviar pergunta, criar mensagem ou chamar IA. A
  demonstração vazia confirmou a superfície móvel sem overflow ou erro de
  console, sem alegar volume visual.
- Foram aprovados 49 testes focados, Ruff, MyPy global e a suíte integral com
  776 testes, três skips e 11 subtestes. Não houve runtime, fallback, egressão,
  custo ou serviço externo; o ambiente temporário foi encerrado e movido à
  Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 94 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — trilhas de Conciliação recuperáveis (V-085)

- Processamentos e exportações passaram a paginar 20 registros de forma
  independente, em vez dos cortes de 12 e 8, preservando os parâmetros da tela
  e a outra trilha.
- O teste com 21 execuções e 21 exportações fictícias confirmou a segunda página
  de cada uma sem importar, reprocessar, exportar ou baixar arquivos. A
  demonstração confirmou apenas as áreas móveis, sem overflow ou erro de console.
- Foram aprovados 93 testes focados, com um skip de OCR local, Ruff, MyPy global
  e a suíte integral com 775 testes, três skips e 11 subtestes. Não houve ERP,
  arquivo real, custo ou serviço externo; o ambiente temporário foi encerrado e
  movido à Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 91 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — histórico de importações recuperável no onboarding (V-084)

- A área de onboarding passou a paginar 20 lotes de importação e a exibir o
  total, no lugar do corte nos oito mais recentes; a fonte e a prévia continuam
  presentes nos vínculos entre páginas.
- O teste com 21 lotes fictícios confirmou a segunda página sem enviar,
  confirmar ou alterar arquivo. A demonstração vazia confirmou a superfície
  móvel sem overflow ou erro de console, sem alegar volume visual.
- Foram aprovados 57 testes focados, Ruff, MyPy global e a suíte integral com
  774 testes, três skips e 11 subtestes. Não houve arquivo real, Domínio,
  agente, credencial, custo ou serviço externo; o ambiente temporário foi
  encerrado e movido à Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 90 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — histórico DTE recuperável por página própria (V-083)

- O histórico de resultados da Caixa DTE passou a paginar 30 itens, informar o
  total e preservar a página independente da fila de mensagens e os parâmetros
  correntes da tela.
- O teste com 31 itens DTE fictícios confirmou a segunda página sem preparar
  consulta, alterar resultado ou autorização. A demonstração vazia confirmou a
  superfície móvel sem overflow ou erro de console, sem alegar volume visual.
- Foram aprovados 75 testes focados, Ruff, MyPy global e a suíte integral com
  773 testes, três skips e 11 subtestes. Não houve Serpro, certificado,
  consumo, cobrança, custo ou serviço externo; o ambiente temporário foi
  encerrado e movido à Lixeira de forma recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 89 alterações locais existentes foram preservadas
  antes deste registro.

## 21/09/2026 — histórico de cobrança manual recuperável (V-082)

- O console da plataforma passou a paginar as faturas internas em páginas de
  12, expondo o total sem ocultar competências antigas.
- O teste com 25 faturas sintéticas confirmou a página 3 e o vínculo de retorno
  sem alterar valores, contratos ou status.
- Foram aprovados 41 testes focados, Ruff, MyPy global e a suíte integral com
  772 testes, três skips e 11 subtestes. Não houve cobrança, Asaas, cartão,
  Pix, boleto ou serviço externo. A inspeção visual autenticada permanece
  pendente por não inserir credenciais no navegador.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 87 alterações locais existentes foram preservadas.

## 21/09/2026 — Radar da Reforma recuperável por página (V-081)

- A lista de alertas do Radar passou a paginar 50 registros, no lugar do corte
  nos 80 primeiros, mantendo termo, fonte e tema em cada retorno.
- O teste com 101 alertas sintéticos confirmou a terceira página e os filtros.
  A demonstração, que contém somente três exemplos, confirmou o filtro IBS e a
  apresentação móvel, sem alegar visualização em volume.
- Foram aprovados 77 testes focados, Ruff, MyPy global e a suíte integral com
  771 testes, três skips e 11 subtestes. Não houve coleta, URL oficial, ERP ou
  serviço externo; o ambiente temporário foi encerrado e movido à Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 85 alterações locais existentes foram preservadas.

## 21/09/2026 — auditoria de conciliação recuperável por página (V-080)

- A trilha de auditoria deixou de ocultar eventos depois dos primeiros 200:
  agora apresenta 100 por página, total do filtro e navegação que conserva a
  ação selecionada.
- O teste com 201 eventos e a demonstração local temporária confirmaram a
  terceira página e o retorno à segunda; em 390 px não houve overflow
  horizontal ou erro de console.
- Foram aprovados 90 testes focados, Ruff, MyPy global e a suíte integral com
  770 testes, três skips e 11 subtestes. Não houve arquivo bancário, ERP,
  Domínio ou serviço externo; o ambiente temporário foi encerrado e movido à
  Lixeira de modo recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 84 alterações locais existentes foram preservadas.

## 21/09/2026 — ficha da empresa com históricos recuperáveis (V-079)

- A ficha passou a paginar documentos NFS-e, revisões abertas e mensagens DTE
  em seções independentes de 20 registros, preservando o retorno à carteira.
- O teste com 21 itens de cada tipo e a demonstração temporária confirmaram a
  página 2 das três seções; o retorno da DTE manteve as outras páginas. Em 390
  px não houve overflow horizontal nem erro de console.
- Foram aprovados 72 testes focados, Ruff, MyPy global e a suíte integral com
  769 testes, três skips e 11 subtestes. Não houve ADN, Serpro, A1 ou serviço
  externo; o ambiente temporário foi encerrado e movido à Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 83 alterações locais existentes foram preservadas.

## 21/09/2026 — cobertura de certificados recuperável (V-078)

- A lista de empresas sem certificado A1 válido passou a paginar 20 itens, sem
  interferir na paginação da carteira de certificados; a navegação preserva os
  parâmetros de busca e situação existentes.
- O teste com 21 empresas e a demonstração temporária com 25 pendências
  confirmaram a segunda página e o retorno à primeira. Em 390 px não houve
  overflow horizontal ou erro de console.
- Foram aprovados 70 testes focados, Ruff, MyPy global e a suíte integral com
  768 testes, três skips e 11 subtestes. Não houve A1, ADN ou serviço externo;
  o ambiente temporário foi encerrado e movido à Lixeira de modo recuperável.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 81 alterações locais existentes foram preservadas.

## 21/09/2026 — histórico de Parcelamentos recuperável (V-077)

- O histórico por empresa passou a paginar as operações, em vez de cortar após
  20 tentativas, preservando a empresa em foco na navegação.
- A demonstração temporária com 21 operações fictícias percorreu as duas
  páginas e preservou o aviso de recuperação para resultado incerto, sem erro
  de console. Foram aprovados 77 testes focados, Ruff, MyPy global e a suíte
  integral com 767 testes, três skips e 11 subtestes.
- Não houve chamada PARCSN/Serpro; o ambiente temporário foi encerrado.
- Após atualizar as referências remotas, `HEAD` permaneceu sincronizado com
  `origin/main` (0 à frente, 0 atrás); as 80 alterações locais foram
  preservadas.

## 21/09/2026 — fila de conciliação sem corte silencioso (V-076)

- A fila OFX × Domínio passou a paginar 50 resultados, mantendo busca e
  situação; a montagem de candidatos continua limitada à página apresentada.
- O teste autenticado criou 101 correspondências sem par, alcançou a página 3
  e manteve os filtros no retorno. A demonstração possui somente duas linhas,
  portanto não foi usada para alegar inspeção visual da paginação em volume.
- Foram aprovados 95 testes focados, Ruff, MyPy global e a suíte integral com
  766 testes, três skips e 11 subtestes, sem arquivo bancário ou serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 80 alterações locais existentes foram preservadas.

## 21/09/2026 — carteira de Parcelamentos por lote autorizado (V-075)

- A carteira deixou de ocultar empresas acima de 100 registros e agora pagina
  30 por página, preservando a pesquisa.
- O seletor em massa passou a declarar o escopo da página e cada página respeita
  o limite de 30 empresas já validado pelo backend. A jornada com 101 empresas
  fictícias alcançou a página 4, retornou à 3 e não apresentou erro de console.
- Foram aprovados 76 testes focados, Ruff, MyPy global e a suíte integral com
  765 testes, três skips e 11 subtestes. Não houve Serpro, PARCSN, Domínio ou
  outro serviço externo; o ambiente temporário foi encerrado.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 78 alterações locais existentes foram preservadas.

## 21/09/2026 — carteira de guias sem corte silencioso (V-074)

- Guias/DCTFWeb passou a paginar listas maiores que 100 resultados, mantendo
  busca, situação e vencimento ao navegar entre as páginas.
- A demonstração temporária com 101 guias fictícias confirmou página 2, retorno
  à página 1 e ausência de erros de console. Foram aprovados 88 testes focados,
  Ruff, MyPy global e a suíte integral com 764 testes, três skips e 11
  subtestes.
- O banco e servidor locais de QA foram encerrados; o diretório temporário foi
  movido de forma recuperável para a Lixeira. Não houve chamada Serpro,
  DCTFWeb, Domínio ou outro serviço externo.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push; as 76 alterações locais existentes foram preservadas.

## 21/09/2026 — revisão NFS-e e carteira sem corte silencioso (V-073)

- O detalhe local passou a mostrar os fatos normalizados necessários à decisão;
  a demonstração os preenche como fictícios e mantém a referência da contraparte
  pseudonimizada.
- A carteira agora pagina mais de 100 documentos sem perder o filtro. A página
  2 e o retorno à página 1 foram confirmados em celular no navegador interno,
  sem overflow ou erro de console. Foram aprovados 79 testes focados, Ruff,
  MyPy e a suíte integral com 763 testes, três skips e 11 subtestes.
- O banco e servidor locais de QA foram encerrados; o diretório temporário foi
  movido de forma recuperável para a Lixeira.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0), sem
  pull, commit ou push.

## 21/09/2026 — contrato do runtime de IA e guarda de fallback verificados (V-072)

- O runtime privado OpenAI-compatível respondeu em teste com evidência compacta;
  uma resposta local não acionou fallback nem criou egressão, mesmo com a rota
  externa configurada.
- A ausência de opt-in continuou bloqueando o provedor e registrando a negação.
  Foram aprovados 73 testes, 3 subtestes, Ruff e MyPy global; o ambiente foi
  totalmente simulado, sem modelo ou provedor real.
- O fetch final manteve `HEAD` e `origin/main` no mesmo commit (0/0), sem pull,
  commit ou push; as alterações locais foram preservadas.

## 21/09/2026 — módulos fictícios e Copiloto validados visualmente (V-071)

- Guias, DTE, Parcelamentos, Conciliação, Radar e Copiloto renderizaram na
  demonstração, com aviso explícito e sem erro de console.
- O Copiloto exigiu empresa e apresentou resposta simulada com fontes marcadas
  como sintéticas, sem egressão ou chamada externa.

## 21/09/2026 — revisão fiscal e isolamento de console verificados (V-070)

- A fila e o detalhe NFS-e fictícios apresentaram contexto, hash, evidência,
  confiança, XML e decisão explícita com retorno à fila.
- A sessão de demonstração recebeu acesso restrito ao abrir o console Mewstack;
  nenhum erro de console foi observado. A inspeção do console autenticado segue
  pendente por não inserir credenciais automaticamente.

## 21/09/2026 — auditoria visual pública e demonstração fictícia (V-069)

- A home, cadastro, abas/FAQ, viewport móvel e console foram verificados no
  navegador interno com base temporária; não houve overflow nem erro de console.
- A demonstração isolada alcançou dashboard e Triagem, onde o anexo em
  quarentena permaneceu explicitamente bloqueado para abertura e download.
- A auditoria é parcial: o Mac bloqueado impediu automação nativa e não houve
  acesso a console, integrações, dados reais ou ambiente publicado.

## 21/09/2026 — view Hub integralmente tipada e regressão focada (V-068)

- Os contratos locais de conciliação, Triagem, certificados, setup e tokens
  foram explicitados sem chamar serviços externos ou modificar fluxos.
- Ruff, MyPy da view e MyPy global passaram; 119 testes locais passaram, com
  um único skip esperado de OCR em português. A suíte integral repetiu 762
  testes aprovados, 3 skips conhecidos e 11 subtestes aprovados.
- O fetch final confirmou `HEAD` e `origin/main` no mesmo commit (0/0); as
  alterações locais da execução foram preservadas, sem commit ou push.

## 21/09/2026 — NFS-e e DCTFWeb da view Hub refinados (V-067)

- Coleções, contexto, números, UUID e cotações receberam contratos explícitos;
  20 testes NFS-e/DCTFWeb passaram sem integração externa.

## 21/09/2026 — primeira seção da view do Hub tipada (V-066)

- Demonstração, dashboard, convites, módulo, despacho NFS-e e filtros receberam
  contratos explícitos; 86 testes locais passaram sem alteração de integração.
- A dívida da view do Hub caiu a 114 erros; nenhuma homologação externa foi
  realizada.

## 21/09/2026 — serviços, agente e interface de IA tipados (V-065)

- Reserva do Copiloto, API do agente e estado transitório de entrega da
  interface receberam contratos explícitos, sem persistir novos campos nem
  acionar fallback externo.
- Ruff, MyPy e 68 testes passaram. A dívida global ficou em 131 erros de uma
  única view do Hub; curadoria e egressão real continuam pendentes.

## 21/09/2026 — operações Integra e NFS-e tipadas (V-064)

- Serviços, tarefas, reserva entre livros, despacho pós-commit e validação
  decimal NFS-e receberam contratos explícitos, mantendo as integrações sem
  execução real.
- Ruff, MyPy e 57 testes DTE/DCTFWeb/PARCSN/NFS-e passaram. A dívida global
  caiu a 143 erros em 4 arquivos; Serpro, ADN e Domínio seguem não homologados.

## 21/09/2026 — regressão integral atualizada (V-063)

- Django, migrações, diff e suíte integral foram reexecutados após V-060–V-062:
  762 testes, 3 skips conhecidos e 11 subtestes passaram em 27,52 s. O fetch
  final confirmou `HEAD` e `origin/main` no mesmo commit (0/0).
- Não houve integração externa. Os limites dos skips permanecem Playwright
  Python opcional, OCR local e concorrência PostgreSQL.

## 21/09/2026 — segurança, multipart e acesso DTE tipados (V-062)

- Scanner/política receberam fluxo binário explícito; multipart separou campos e
  bytes; e navegação/reserva DTE receberam contratos estáticos de requisição e
  consumo.
- Quarenta testes locais passaram com Ruff/MyPy; a dívida global caiu a 160
  erros em 7 arquivos. Nenhum scanner, Domínio, Serpro ou dado real foi usado.

## 21/09/2026 — plataforma administrativa tipada e retestada (V-061)

- Tarefa de competência, snapshot contratual, validação de conteúdo de webhook
  e contrato HTTP legal receberam tipos explícitos, preservando regras e dados
  comerciais existentes.
- Ruff, MyPy e 69 testes de plataforma passaram; a dívida global caiu a 168
  erros em 11 arquivos. Nenhuma cobrança, evento Asaas ou alteração comercial
  foi realizada.

## 21/09/2026 — coletores e fila de Triagem tipados (V-060)

- Cursor Graph, conteúdo IMAP, fábrica de conexão e consulta elegível da fila
  receberam contratos explícitos, preservando as leituras e checkpoints locais.
- Ruff, MyPy e 22 testes de Graph, IMAP, retentativa, ingestão e tarefas
  passaram. A dívida global caiu a 172 erros em 15 arquivos, sem OAuth, DNS,
  caixa, antimalware ou destino real.

## 21/09/2026 — regressão integral e relatórios/sincronização tipados (V-058/V-059)

- A verificação Django, migrações e suíte integral passaram: 762 testes, 3
  skips e 11 subtestes. Os skips continuam sendo limitações conhecidas de
  Playwright Python, OCR local e concorrência PostgreSQL.
- Relatórios XLSX/PDF e a normalização da sincronização bancária receberam
  contratos estáticos explícitos; 7 testes de sincronização passaram. Não há
  teste específico de exportação no repositório. A dívida MyPy caiu para 185
  erros em 18 arquivos, sem consulta Domínio ou geração com dados reais.

## 21/09/2026 — gateway e comandos de IA tipados (V-057)

- Payload do gateway e interfaces de comandos passaram a ter tipos explícitos.
  Trinta e dois testes de comandos, escopo e acesso de IA passaram sem chamada
  Anthropic; comandos de custo continuam bloqueados por aprovação específica.
- Ruff, MyPy e diff passaram; a dívida global caiu a 197 erros em 20 arquivos.
  Curadoria, egressão, treino e prova de artefato seguem pendentes.

## 21/09/2026 — configuração de plataforma tipada e retestada (V-056)

- Formulários, persistência, usuário de auditoria e seleção de plano passaram a
  ter contratos estáticos explícitos. Pagamentos, notificações e aprovação de
  fallback foram retestados sem chamar fornecedores.
- Ruff, MyPy e 55 testes passaram, com um skip PostgreSQL; a dívida global caiu
  para 205 erros em 24 arquivos. Nenhuma credencial, SMTP, Claude, Serpro ou
  Asaas real foi utilizado.

## 21/09/2026 — coletor Gmail e ingestão tipados (V-055)

- Cursor, checkpoint, data inicial, base64 e caminho de blob receberam
  pré-condições explícitas. Quatorze testes de ingestão/retentativa, Ruff e
  MyPy passaram; a dívida global reduziu a 291 erros em 28 arquivos.
- Nenhuma caixa Google, OAuth ou provedor foi acessado. A etapa 06 continua
  aguardando homologações externas.

## 21/09/2026 — cliente IMAP local tipado (V-054)

- Socket e respostas IMAP receberam contratos explícitos, preservando busca
  somente leitura sem charset. Doze testes de conexão/retentativa sintética,
  Ruff e MyPy passaram; a dívida global caiu a 296 erros em 30 arquivos.
- Nenhuma caixa, credencial ou provedor foi acessado. A homologação segue nas
  etapas 06 e 12.

## 21/09/2026 — livros de tokens e faturamento tipados (V-053)

- Medidores legado e de tokens foram separados explicitamente no fechamento;
  franquia/preço e usuário de aceite são materializados antes da persistência.
  Vinte e dois testes passaram, com concorrência PostgreSQL mantida como skip.
- Ruff, MyPy e diff passaram nos módulos; a dívida global reduziu a 300 erros em
  31 arquivos. Não houve cobrança, Asaas, preço novo ou pagamento real.

## 21/09/2026 — transporte de e-mail local tipado (V-052)

- O backend passou a declarar configuração, SMTP e sequência de mensagens sem
  alterar o carregamento tardio do modelo. Ruff, MyPy e 33 testes de
  configuração passaram; a dívida global reduziu para 311 erros em 33 arquivos.
- Não houve conexão SMTP/DNS/Brevo, segredo ou envio real. A homologação segue
  exclusivamente na etapa 12 conforme D-77/D-78.

## 21/09/2026 — PARCSN e tarefas agendadas tipados (V-051)

- O parser local passou a validar explicitamente o expoente decimal e os
  inteiros do payload; o decorador de tarefa tem contrato de retorno completo.
  Vinte testes de PARCSN/operações passaram sem transporte Serpro.
- Ruff, MyPy e diff passaram nos módulos; a dívida global chegou a 316 erros em
  34 arquivos. Credenciais, representação, custo e prova Serpro seguem abertas.

## 21/09/2026 — limites de entrada da importação explicitados (V-050)

- A prévia local exige nome de arquivo antes de persistir e usa esse valor
  validado nos fluxos tabular e de backup; o mapa de capacidades foi tipado.
  Não houve arquivo ou backup real.
- Ruff e 57 testes do Hub passaram; o MyPy global caiu a 328 ocorrências. A
  tentativa de isolação de imports expôs erro interno do MyPy/django-stubs, não
  mascarado como aprovação. A etapa 09 continua sem layout/ERP/OCR homologado.

## 21/09/2026 — serviço de conciliação tipado e retestado (V-049)

- Foram explicitados contratos locais de parser, checkpoint, armazenamento,
  relações opcionais e regra de faixa, preservando a recusa de dados inválidos.
  Bibliotecas de XLSX/PDF seguem sem stubs, com exceção limitada aos imports.
- Ruff e MyPy do serviço, 35 testes de conciliação (um skip de OCR), Django,
  migrações e diff passaram. MyPy global caiu para 334 erros em 38 arquivos.
- Não houve ERP, arquivo real, OCR disponível, fonte Radar ou exportação
  homologada; a etapa 09 continua aberta por esses requisitos.

## 21/09/2026 — formulários de contratação retestados (V-048)

- Ajustadas fronteiras de tipos de `LeadForm`, plano e proposta de tokens sem
  mudar preço, contrato, consumo ou cobrança. A suíte focada aprovou 26 testes,
  com um skip de concorrência reservado ao PostgreSQL.
- Ruff, MyPy e diff passaram; MyPy global passou a 348 erros em 39 arquivos.
  Não houve chamada CNPJ, Asaas, criação de cobrança ou qualquer custo.

## 21/09/2026 — formulários do Hub e cache CNPJ tipados (V-047)

- Formulários de escopo, importação e conciliação receberam tipos seguros para
  escolhas dinâmicas, modelos, widgets e validações. Referências genéricas de
  Django são adiadas para não tentar subscrever classes em execução.
- A suíte de conciliação aprovou 35 testes, com um skip esperado por OCR local;
  Ruff, MyPy, Django, migrações e diff passaram. O cache de CNPJ também só
  reutiliza dicionário de textos e não chamou a fonte externa.
- A dívida MyPy global reduziu para 356 ocorrências em 40 arquivos. OCR,
  layouts, ERP, Radar, fontes e homologações continuam fora desta evidência.

## 21/09/2026 — pré-condições de serviço da Triagem explicitadas (V-046)

- As verificações já esperadas pelo serviço foram tornadas explícitas para os
  tipos: relações de empresa/tipo, nome e tamanho do upload, caminho interno e
  stream binário. Não houve mudança de fluxo, regra de segurança, banco,
  provedor, arquivo real ou migração.
- Ruff e MyPy passaram no serviço; 35 testes de domínio, ingestão e agente
  Windows passaram em 7,47 s. Django, dry-run de migrações e diff passaram.
  A linha de base global reduziu para 399 erros em 42 arquivos.

## 21/09/2026 — formulários da Triagem tipados sem mudança funcional (V-045)

- Foram eliminadas 127 ocorrências MyPy dos seis formulários. As fronteiras
  dinâmicas do Django foram tipadas com precisão pragmática, os campos de
  empresa/documento ganharam tipos de modelo explícitos e o tratamento de data
  preserva a validação existente.
- Ruff e MyPy passaram nos módulos alterados; 51 testes de política, IMAP,
  domínio e ingestão sintética passaram em 14,77 s, e `git diff --check` ficou limpo. MyPy global
  reduziu de 535 erros em 46 arquivos para 408 em 43 arquivos.
- Não houve modificação de tela, fluxo, banco, provedor, caixa real, destino ou
  migração. A etapa 06 continua aberta pelas dependências Q-12 a Q-25/Q-31 e
  pela homologação externa.

## 21/09/2026 — diagnóstico global e primeiro lote de tipos da Triagem (V-044)

- A auditoria `uv run mypy .` achou 535 ocorrências em 46 arquivos. O número é
  uma linha de base de dívida técnica, não uma validação verde nem um bloqueio
  de funcionamento local.
- O primeiro lote eliminou a divergência entre enum e chave de texto no mapa de
  apresentação de caixas e tornou explícita a ausência de stubs de `defusedxml`.
  Não houve mudança de fluxo, banco, provedor, dado operacional ou migração.
- Ruff e MyPy passaram nos dois módulos; 44 testes de política, domínio e
  ingestão de e-mail passaram em 7,12 s, e o diff não tem espaço inválido.
  A retomada segura é reduzir a dívida em lotes revisáveis, preservando o
  diagnóstico global até que cada módulo tenha evidência própria.

## 21/09/2026 — qualidade de tipos local (V-043)

- Corrigidas as 21 ocorrências MyPy encontradas durante V-042 em armazenamento
  privado da Triagem, validação OAuth, caminho privado de conciliação e modelos
  de livros de tokens. As alterações preservam as assinaturas Django e não
  mudam regra de negócio, migração, provedor ou dado operacional.
- MyPy e Ruff passaram nos seis módulos envolvidos. Django, dry-run de
  migrações e diff também passaram; 125 testes focados (um skip de OCR) e três
  subtestes cobriram Triagem, conciliação, cobrança e IA.
- A suíte integral iniciada posteriormente excedeu a janela de captura da
  sessão, sem resumo recuperável; ela não é apresentada como aprovação. Não
  restou processo Pytest e `lastfailed` estava vazio. O ponto de retomada é
  repetir a suíte integral em terminal com captura persistente antes de usar
  esta alteração como revalidação global.

## 21/09/2026 — etapa 05: gate de identificadores pessoais no manifesto (V-042)

- D-94 formalizou o controle local: CPF, CNPJ ou e-mail reconhecível em
  pergunta, resposta ou referência bloqueia o manifesto de treino e avaliação
  antes de qualquer gravação. O registro não é mascarado automaticamente; a
  anonimização exige revisão humana para preservar seu sentido contábil.
- O comando de exportação transforma a recusa em erro controlado e não cria o
  JSONL. D-95 acrescentou criação exclusiva: ele também recusa sobrescrever um
  artefato existente. Testes cobrem os três locais possíveis do identificador,
  a ausência de artefato após a falha e a preservação do arquivo já existente.
- Ruff, Django, dry-run de migrações e 39 testes focados/3 subtestes passaram.
  A suíte integral fechou com 762 aprovados, 3 skips esperados e 11 subtestes.
  Não houve egressão, Claude, dado de cliente, modelo, treino, GPU, custo ou
  deploy. A etapa 05 segue em andamento por curadoria, corpus e aprovações
  Q-08/Q-09/Q-11/Q-34. MyPy não fechou: a execução a partir de `src/` reportou
  21 erros em quatro módulos não alterados (`triage`, `hub` e `platform`), que
  ficam registrados como dívida técnica separada.

## 21/09/2026 — análise integral, etapa 04 e comparação com GitHub (V-041)

- A documentação canônica, o inventário, a matriz de evidências e o código
  atual foram confrontados. O produto permanece um SaaS multiempresa da
  Mewstack com agente Windows e módulos operacionais; a condição de venda
  continua sendo operação verificável e recuperável, não a existência de tela
  ou teste isolado.
- A próxima etapa do plano continua sendo Siescon. A preparação correta já
  modela o destino, mas o registro de adaptadores contém apenas Domínio; pedir
  Siescon é recusado antes de ler lançamentos ou criar arquivo. Não foi criado
  SQL, endpoint, credencial ou layout especulativo. Q-33 continua exigindo
  versão/banco/método de leitura, schema, chave empresarial/cursor, ambiente e
  layout de importação por canal seguro.
- Ruff, Django, dry-run de migrações, 35 testes focados (1 skip de OCR) e a
  suíte completa (759 aprovados, 3 skips e 8 subtestes) passaram. Nenhuma
  integração externa foi executada. `git fetch origin --prune` e a comparação
  `HEAD...origin/main` retornaram 0 commits de cada lado; não havia mudança do
  GitHub a trazer.
- A etapa 04 fica em andamento e bloqueada, não concluída. Após receber o
  contrato Q-33, revisar o material antes de escrever adaptador, então validar
  leitura idempotente e exportação importada/conferida no ambiente autorizado.

## 20/09/2026 — etapa 11: pausa da auditoria local de interação

- A continuidade segura selecionada foi a auditoria local de teclado, foco e
  estados de erro/vazio, em servidor descartável com SQLite e egressão externa
  bloqueada. O servidor e a aba de demonstração foram encerrados ao parar.
- A regressão automatizada existente não pôde ser executada porque o pacote
  Node `playwright` não está instalado neste checkout. A inspeção com navegador
  nativo também não iniciou: o aplicativo Codex aguarda a concessão única de
  Acessibilidade e Gravação de Tela. Não foram inferidos resultados de UI.
- Ponto de retomada: após essa permissão, executar as jornadas sintéticas de
  teclado/foco/erro/vazio da etapa 11 e registrar apenas os estados de fato
  observados. Não há alteração de código, configuração, dados ou provedor neste
  registro.

## 20/09/2026 — etapa 10: contrato local do cliente Asaas (V-040)

- Implementado `apps.platform.asaas` com ambientes explícitos, chave e
  transporte injetados, consulta por `externalReference`, criação de cliente e
  cobrança avulsa sem dados de cartão. Falha ou retorno incerto não faz nova
  tentativa automática de `POST`.
- `uv run pytest tests/test_asaas_client.py tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q` fechou com 49 aprovados e um skip de concorrência exclusivo do PostgreSQL. Ruff, Django, dry-run de migrações e diff passaram.
- A revalidação integral fechou com 759 aprovados, 3 ignorados e 8 subtestes em
  28,99 s; os skips são Playwright Python opcional, OCR português ausente e a
  concorrência de locks já coberta em PostgreSQL histórico.
- O contrato foi conferido na documentação oficial Asaas e não fez conexão,
  usou chave real, alterou configuração ou criou objeto no provedor. Ainda falta
  orquestrar dados comerciais, cliente e `PaymentAttempt`, além da homologação
  autorizada de Pix, boleto, cartão e eventos na etapa 12.

## 19/09/2026 — etapa 11: inspeção local de jornadas e interfaces (V-039)

- Em servidor isolado com banco, mídia e massa sintéticos, 14 caminhos da área
  de trabalho foram verificados em desktop e 390 × 844: cada um exibiu um `h1`,
  não apresentou overflow horizontal nem campo visível sem rótulo na checagem
  DOM. A Triagem fictícia percorreu fila, revisão, preparo e arquivamento
  privado na sessão; o console não reportou erro.
- 77 testes de workspace, demonstração e autenticação passaram; um teste
  Playwright Python opcional foi ignorado porque o navegador interativo local
  foi usado nesta auditoria. Ruff, Django, migrações em dry-run e diff passaram.
- A inspeção não cobre todas as áreas públicas, console, perfis, teclado/foco,
  contraste, carga/erro/vazio nem tarefas externas. Etapa em andamento; não há
  alegação de aceite integrado ou aderência comercial final.

## 19/09/2026 — etapa 06: Triagem de Arquivos local (V-038)

- Revalidados quarentena privada, idempotência por entrega, cursor/leitura
  incremental simulados, bloqueio de binário não verificado, scan/formato,
  revisão, cópia interna com hash e protocolo de agente Windows com escopo,
  hash, falha recuperável e repetição. Nenhuma confirmação ocorre só pela
  intenção de arquivar.
- 72 testes de domínio e seis subtestes de protocolo Windows passaram; seis
  testes de interface/demo cobriram escopo de empresa, fila, bloqueio de arquivo
  não verificado, cópia privada e isolamento por sessão. Ruff, Django,
  migrações em dry-run e diff passaram.
- Nenhuma caixa, OAuth, ClamAV, agente Windows, arquivo de cliente ou pasta
  real foi usada. Q-12–Q-25/Q-31, regras de catálogo/retenção/checklist e o
  piloto com prova no destino seguem pendentes; a etapa fica em andamento.

## 19/09/2026 — etapa 09: Conciliação e Radar locais (V-037)

- Revalidado o processamento local de OFX/CSV/XLSX/PDF, hash e reimportação,
  mapeamento, contas, movimentos, lançamentos equilibrados, evidência de
  conciliação, exportação/reexportação auditável e retomada de execução. A
  ambiguidade não é confirmada só por data e valor.
- O Radar preserva fontes oficiais pré-definidas, origem, atualização
  idempotente e falha isolada por fonte; a interface não mostra o erro bruto.
  As fontes foram substituídas por respostas controladas nos testes, portanto
  não há alegação de disponibilidade operacional.
- 46 testes de domínio passaram; o cenário de OCR em português foi ignorado
  porque Tesseract/modelo local não existe. Quatro testes de interface/demo,
  Ruff, Django, dry-run de migrações e diff passaram. Sem dado de cliente,
  arquivo real, ERP, HTTP externo, custo ou deploy.
- Layouts aprovados, corpus/volume PostgreSQL, OCR, amostra de D-73, importação
  conferida no destino e fontes reais do Radar continuam necessários. A etapa
  fica em andamento.

## 19/09/2026 — análise auditável de conclusão (V-036)

- Criada a matriz de evidências que liga as 14 etapas ao maior nível provado, às validações e aos bloqueios concretos. O documento torna explícita a diferença entre implementação, validação local, homologação e venda.
- A matriz foi vinculada ao plano mestre e ao índice de planejamento. A checagem de diff, Django e migrações passou; não houve acesso externo, alteração de ambiente ou custo.
- A análise mantém Q-33 como primeiro bloqueio de sequência e não reclassifica nenhuma etapa incompleta como concluída.

## 19/09/2026 — etapa 07: demonstração NFS-e local (V-035)

- Reconciliado o checklist com o comportamento que já existia desde V-005: ZIP fictício por empresa, carteira inteira, manifesto de classificações, filtro exclusivo por competência/emissão e atualização visual de acumulador permanecem restritos à demonstração e não gravam decisão fiscal.
- Reexecutados 4 testes focados de NFS-e e a inspeção interativa da demonstração criada em SQLite temporário. Datas DD/MM/AAAA foram normalizadas, o intervalo de setembro retornou os 24 itens da carteira, o acumulador manual transitou para 100% e a limpeza restaurou Transitória a 0%; console sem erros.
- O banco e a conta temporários foram descartados após a inspeção. Nenhum certificado, ADN, XML real, dado de cliente, pasta Windows ou provedor externo foi utilizado. A coleta e a homologação fiscal seguem pendentes na etapa 07.

## 19/09/2026 — etapa 08: Central Integra Contador local (V-034)

- O checkout implementa DTE, DCTFWeb e PARCSN sob as decisões D-38–D-42, com seleção de empresas aptas, autorização específica de ciência, paginação, cotação/reserva/liquidação e documento persistido. O transporte incerto não é repetido automaticamente.
- `uv run pytest tests/test_dte.py tests/test_dte_access.py tests/test_dte_dispatch.py tests/test_integra_client.py tests/test_integra_dctfweb.py tests/test_integra_parcelamento.py tests/test_parcelamento_operations.py -q`: 63 aprovados em 13,98 s. Ruff dos módulos e testes envolvidos passou.
- Não houve configuração de segredo, credencial, certificado, representação, consulta, ciência DTE, declaração, guia ou DAS real. O piloto Serpro, contrato/ambiente Q-28 e autorização de custo continuam obrigatórios; Q-36 mantém PARCSN como recorte único.

## 19/09/2026 — etapa 10: controles locais de contratação e cobrança (V-033)

- Auditoria confirmou que D-76/D-79 resolveram as regras Q-01–Q-06. O checkout separa contrato manual e Asaas, mede tokens inteiros por módulo, reserva/liquida consumo de modo idempotente e fecha fatura por competência com preço congelado.
- `uv run pytest tests/test_platform_billing.py tests/test_platform_payments.py tests/test_token_billing.py tests/test_cica_contract_mfa.py tests/test_cica_operation_access.py -q`: 44 aprovados e 1 skip de concorrência PostgreSQL coberta em evidência histórica. Ruff dos arquivos de plataforma passou.
- Não houve conta, sandbox, credencial, cliente, cobrança, Pix, boleto, cartão ou webhook Asaas real. O cliente de criação/operação Asaas ainda não existe; Q-08 e o ambiente Q-28 continuam bloqueando a homologação.

## 19/09/2026 — etapa 05: escopo de conhecimento e treinamento (V-032)

- D-89 formalizou a estrutura técnica de área (`geral`, contábil, fiscal ou folha), empresa e período para fontes e exemplos. Registros existentes recebem o padrão geral; não houve reclassificação, exportação ou exposição de conteúdo.
- Fontes de uma empresa só podem pertencer ao mesmo escritório. A recuperação por empresa recebe apenas suas fontes e as globais do escritório, priorizando as específicas; o contexto sem empresa exclui fontes de qualquer empresa. O manifesto QLoRA guarda esses metadados para manter sua proveniência auditável, mas o runner continua treinando somente com pergunta, resposta e fontes aprovadas.
- D-90 acrescentou modelo base, versão e hashes de manifesto/artefato às avaliações e versões locais. Quando uma versão declara artefato, a publicação recusa qualquer avaliação com proveniência diferente; registros legados continuam legíveis sem alegar vínculo. Vinte testes focados passaram.
- D-91 separou exemplos validados entre treino e avaliação. O exportador seleciona um conjunto por vez, o hash da avaliação é registrado junto da avaliação do adaptador e o runner QLoRA recusa o conjunto de avaliação. Trinta e quatro testes focados passaram.
- D-92 adicionou retorno auditado de versão local: uma versão anterior só é reativada com avaliação aprovada e proveniência compatível, sem novo treino. Dezessete testes focados de publicação/retorno passaram.
- `ruff` focado, migrações em dry-run e 26 testes de recuperação, treinamento e runner passaram; a revalidação integral fechou em 754 aprovados, 3 ignorados e 8 subtestes. Não houve chamada Claude, curadoria externa, modelo baixado, treino, GPU, publicação ou custo. Governança de egressão e curadoria continuam em Q-08/Q-09/Q-11/Q-34.

## 19/09/2026 — análise integral e continuidade da etapa 04 (V-031)

- Revisados plano mestre, decisões, validações, inventário, documentação de produto/técnica, etapas e checkout. A análise consolidada registra objetivo, arquitetura, capacidades e limites em [analise-projeto-2026-09-19.md](analise-projeto-2026-09-19.md).
- A etapa 04 continua sendo o próximo trabalho habilitado, mas não pode receber adaptador Siescon sem o contrato Q-33. O material necessário é versão/banco/mecanismo de leitura, ambiente e revogação, schema/campos autorizados, identificador/cursor de empresa e layout de exportação/importação por canal seguro. Não houve conexão, solicitação de segredo, leitura de dados ou arquivo fictício Siescon.
- A estação macOS recriou `.venv/` ignorado pelo Git com `uv sync --locked --all-extras`. A revalidação encontrou 16 E501 e os corrigiu apenas com quebras de linha nos fluxos já existentes do agente e destino Windows. A primeira suíte integral expôs que o modo de biblioteca interna apagava o padrão de pastas Windows; o formulário passou a preservá-lo. Ruff, Django, dry-run de migrações e a suíte integral passaram com 747 aprovados, 3 ignorados e 8 subtestes. V-031 contém os comandos e limites.
- Corrigidos os ponteiros vigentes que ainda apresentavam o escopo histórico da etapa 00 ou a etapa 01 como próximo trabalho. Não foram alterados documentos históricos nem inferidas regras de produto.

## 18/09/2026 — etapa 02: auditoria inicial de acesso e administração

Etapa iniciada após a conclusão técnica da etapa 01. Auditoria local localizou cadastro, recuperação, convite, MFA, escopo, contrato/teste, isolamento e console já implementados. A suíte específica fechou com 83 aprovados em 54,47 s (V-007). Não houve envio de e-mail, alteração de cobrança nem integração externa. Q-01–Q-06/Q-29 continuam condicionando as regras comerciais e a homologação de e-mail; etapa segue aberta.

Cadastro inspecionado por Playwright em desktop e móvel: sem overflow, foco visível e console limpo; sessões fechadas. UI/UX Pro Max, Watermelon, referências SaaSFrame e Web Interface Guidelines aplicados conforme V-007. Sem mudança de UI nesta auditoria.

D-76 aprovou as regras documentadas para implementação e definiu `suporte@mewstack.com.br`. Implementados e-mails HTML de confirmação, convite e recuperação com texto de reserva; 62 testes e Ruff passaram (V-008). D-77 transferiu SMTP real, DNS e homologação de entrega para a etapa 12; nenhum envio foi feito nesta fase.

Brevo definido como provedor SMTP transacional (D-78). A decisão não configura conta, crédito, credenciais, domínio nem envio; tudo isso fica para a etapa 12.

## 18/09/2026 — retomada do plano (D-70)

Identificado o primeiro item pendente: build de treinamento na etapa 01. Corrigido o resumo desatualizado do plano mestre. D-71 manteve LlamaFactory como ferramenta interna e fixou a imagem oficial por digest. Corrigida a cópia inválida do executor no Dockerfile; `cica-trainer:stage01` foi construído e o CLI iniciou (V-006). O digest também foi centralizado em `runtime/trainer/image.env` e incluído no CI; seu rebuild local passou. Sem modelo, treino ou GPU. Etapa segue aberta por Q-28/Q-30 e D-61.

Fedrizzi Contabilidade confirmado como ambiente disponível para homologação e proprietário definido como aprovador de cada módulo (D-72). Faltam apenas acessos/amostras concretos por integração e metas mensuráveis de aceite; etapa 01 continua aberta.

Critérios recomendados foram aprovados e registrados em D-73. Metas de aceite deixam de ser bloqueio; primeira homologação Fedrizzi ainda depende da amostra e do acesso seguro da integração que será exercitada. Etapa 01 segue aberta por D-61.

Validação integral posterior: 742 testes aprovados, 2 ignorados e 8 subtestes em 85,31 s; Django check, migrations dry-run e Ruff aprovados. Correção D-74: inspeção segura do banco confirmou conector Fedrizzi `direct_odbc` e fonte Domínio local `ready`; nenhuma credencial, DSN ou dado empresarial foi exposto. A etapa 01 está concluída como validação técnica local; conexões externas restantes pertencem às próximas etapas. Evidência V-006.

## 18/09/2026 — demonstração NFS-e em ajuste

Pedido “mais bonito”: refinado agrupamento, hierarquia, espaçamento e estados visuais do filtro, mantendo D-69. Inspeção desktop/mobile e evidências no complemento V-005. Sem nova regra de negócio.

Complemento D-69: substituído calendário nativo de emissão por digitação brasileira e atalhos mensais. Validação cliente/servidor e filtragem dos dados antigos da demo corrigidas. Evidências e pesquisa no complemento V-005 de VALIDACOES.md. Etapa 07 continua aberta.

- Revisão visual posterior: CSS específico da carteira, filtros em linha, acumulador com ícone de edição e foco, seleção destacada, adaptação móvel e cache do JS atualizado. Playwright verificou claro/escuro, desktop/mobile, digitar/limpar/Enter e troca exclusiva do período. Evidência detalhada em V-005; nenhuma etapa homologada por esta revisão.

- Carteira demonstrativa passou a usar a emissão da NFS-e, com escolha exclusiva entre competência e intervalo de emissão.
- Download em lote separado em `Emitidas/CÓDIGO -/` ou `Tomadas/CÓDIGO -/`, com manifesto de classificação; acumulador manual, Transitória a 0% e classificadas da demonstração a 97%.
- Corrigido Enter no acumulador: seleciona a nota e avança o foco, sem tentar baixar uma seleção vazia.
- Evidência local, limites e inspeção Playwright em [V-005](../../VALIDACOES.md). Etapa 07 continua aberta.

## 17/09/2026 — etapa 01: estabilização técnica parcial

- Ruff: 66 achados eliminados com formatação mecânica e ordenação de imports nas nove unidades apontadas.
- Segurança de dependência: pypdf passou de 6.9.2 para 6.16.1; lockfile e requisitos foram atualizados. pip check e pip_audit aprovados; o pacote local é ignorado pelo auditor por não estar no PyPI.
- Base Django: check e dry-run de migrations aprovados; suíte completa: **740 aprovados, 1 ignorado e 8 subtestes** em 70,07 s. Testes focados de token/faturamento/IA/fila/conciliação: 66 aprovados.
- Agente Windows: service, configurador e MSI compilados; MSI de 79.285.770 bytes e checksum SHA-256 6ed0a1592fc3f0b5c5277e9dfc3ce8f27c000c6ca493cb3f5c245ac94c23f9b9 gerados em agent-windows/artifacts/.
- Ambiente atualizado em 18/09: Docker Desktop 4.91.0 e WSL 2.7.1 operacionais; PostgreSQL 17 e Redis 7.4 saudáveis por Compose. Migrations dos bancos principal e de conhecimento sem operações pendentes. Worker Celery com pool `solo` consumiu tarefa via Redis; o pool `prefork` apresentou `WinError 5` no Windows, limitação que não representa o worker Linux de produção.
- Correção PostgreSQL: aprovação e exportação de lançamentos usavam `FOR UPDATE` sobre joins opcionais; PostgreSQL rejeitava a consulta. Os locks foram restringidos ao `JournalEntry` principal, e 35 testes de conciliação passaram no banco real. A suíte crítica PostgreSQL fechou com 95 aprovados; uma regressão de quatro chamadas concorrentes com mesma chave confirmou um único evento de consumo.
- Builds: `cica-backend:stage01` e `cica-multimodal:stage01` foram construídas. O MSI do agente continua validado pelo checksum já registrado. A etapa 01 permanece aberta e bloqueada apenas por Q-37: referência LlamaFactory aprovada por digest para construir o runtime de treinamento. D-61 impede o encerramento antes disso. Ver [V-004](../../VALIDACOES.md) e [checklist](etapas/01-base-tecnica.md).

## 17/09/2026 — etapa 00: documentação única na raiz

Escopo limitado pelo responsável a **somente a primeira etapa (00)**. Não iniciadas correções de código ou demais etapas.

- Materializados [PLANO-MESTRE.md](../../PLANO-MESTRE.md), [DECISOES.md](../../DECISOES.md) e [VALIDACOES.md](../../VALIDACOES.md) na raiz, conforme solicitado.
- Registro D-01–D-45 preservado, inclusive distinção entre confirmado e apenas registrado; adicionados D-46–D-60 com fonte e alcance.
- Criados [14 arquivos de etapa com prompts](etapas/README.md), dependências, checklist, testes, aceite e limites; [inventário estático](inventario-conclusao.md) cobre módulos, modelos, rotas/API, tarefas e serviços.
- Q-10 encerrada por D-50/D-51; demais perguntas agrupadas por dono/etapa e vinculadas sem duplicar decisões. Nenhuma decisão comercial nova foi presumida.
- Corrigidas referências concorrentes e contradições documentais: titularidade Serpro, coleta ADN, OAuth por escritório, escopo da Conciliação, disponibilidade Siescon e preparo da IA local.
- Resultados técnicos anteriores à edição: 740 testes aprovados, 1 ignorado, 8 subtestes; Django e migrations dry-run sem pendências; 66 violações Ruff ainda presentes. Ver V-001; não são novos testes de implementação desta etapa.
- Conferência de documentos e conclusão: ver V-003 em VALIDACOES.md. Sem chamada paga, deploy, conexão a ERP, alteração de banco ou treinamento real.

## Histórico anterior — preservar data e limites de cada entrada

Atualizado em 15/09/2026. A meta é concluir cada módulo da CICA pela tarefa real do escritório, homologar dependências externas e só então liberar a oferta. Esta página distingue trabalho local, teste simulado, validação com fornecedor e aceite comercial. Cada linha descreve o estado **naquele marco**; resultados posteriores na mesma data substituem limites antigos. Para a fotografia atual, leia [estado operacional](estado-operacional.md), [decisões](decisoes.md) e [dúvidas](duvidas-abertas.md).

| Data | Área | Mudança ou prova local | Resultado e limite |
| --- | --- | --- | --- |
| 15/09 | Copiloto | Chave central `CICA_CLAUDE_API_KEY` lida do `.env`; política global e por escritório; rota Claude disponível antes do PC local e runtime local configurável para depois | 125 testes focados aprovados; transporte Claude ainda simulado. Chave não estava configurada na última inspeção e nenhuma chamada cobrada foi executada. Modelo completo, cotas, consentimento e egressão permanecem abertos. |
| 15/09 | Triagem | Entrada vendável definida como e-mail; rota principal mostra estado vazio, sem upload manual; provedor Gmail reconhecido no schema; cursor longo cifrado; revisão/download filtrados pelas empresas autorizadas do colaborador | 23 testes de domínio e 3 testes focados de rota aprovados. O serviço manual presente na árvore de trabalho não é o fluxo aprovado; leitores Graph/Gmail/IMAP, quarentena antimalware, classificação, destino Windows e checklist ainda faltam. |
| 15/09 | Oferta | Preço de Triagem removido do catálogo automático enquanto ela não executa a entrada por e-mail e o arquivamento | As três regressões comerciais do primeiro teste completo foram resolvidas. Preço final e franquias continuam decisão do responsável. |
| 15/09 | Suíte completa | `uv run pytest -q` após schema Gmail, escopo de revisão/download e textos de interface | **469 aprovados, 1 ignorado, 1 falha** em 29,45 s. Falta `.github/workflows/deploy-cobalchini.yml`; os testes dependem também de `.github/workflows/ci.yml`. |
| 15/09 | Lint e migrations | Ruff nos arquivos Python alterados; `manage.py check`; `makemigrations --check --dry-run`; `manage.py migrate triage` | Ruff, check e detecção de migrations passaram; a migration 0003 de provedor Gmail/cursor cifrado foi aplicada no banco local. |
| 15/09 | Segurança da Triagem | POST de aprovação e download do protótipo manual bloqueados nas rotas; detalhe informa que o anexo depende de e-mail e verificação de segurança | Testes focados 4/4; nenhum binário não verificado pode ser servido por essas rotas. O serviço interno manual ainda existe em trabalho local e não deve ser tratado como fluxo aprovado. |
| 15/09 | Interface | Estado vazio de e-mail, política Claude e detalhe de arquivo revisados pelas diretrizes web; inspeção Playwright em desktop/mobile, teclado, foco, erro e overflow | [Auditoria de interface](auditoria-ui-2026-09-15.md) registra telas e limites. Nome de arquivo longo e alvos móveis foram corrigidos; OAuth/conexão em carga não pôde ser alcançado. |
| 15/09 | Suíte completa após bloquear o protótipo | `uv run pytest -q`; `manage.py check`; `makemigrations --check --dry-run`; Ruff focado; `git diff --check` | **470 aprovados, 1 ignorado, 1 falha** em 29,22 s. A única falha continua sendo o workflow `.github/workflows/deploy-cobalchini.yml` ausente. Check, migrations, Ruff e whitespace passaram. |
| 15/09 | Contrato HTTP Sonnet | Teste com `urlopen` inteiramente simulado para `/v1/messages`, cabeçalhos Anthropic, `claude-sonnet-5`, limite de saída, esforço baixo e ausência de `temperature` | 1 teste focado aprovado, Ruff passou. Nenhuma chamada externa cobrada foi feita; a chave real, resposta do fornecedor, uso e custo ainda dependem de um piloto autorizado. |
| 15/09 | Suíte completa após contrato Sonnet | `uv run pytest -q` | **471 aprovados, 1 ignorado, 1 falha** em 29,91 s. Permanece somente o workflow Cobalchini ausente. |
| 15/09 | Entrega Cobalchini preparada | Workflows CI e deploy manual protegido; imagem por digest, verificação Cosign, Compose com arquivo de ambiente externo, migration, readiness, rollback e confirmação ao CRMew | `tests/test_deployment_config_django.py`: 7 aprovados. Não houve deploy; Docker não está instalado neste PC, portanto o Compose não foi executado localmente. O host, as variáveis protegidas, a chave pública e a aprovação de ambiente ainda precisam de validação operacional. |
| 15/09 | Suíte completa após automação de entrega | `uv run pytest -q` | **472 aprovados, 1 ignorado, 2 subtests aprovados** em 36,72 s. A ausência do workflow Cobalchini deixou de falhar; o teste de navegador Python é opcional porque a inspeção visual usa Playwright MCP. |
| 15/09 | Webhook Asaas | Endpoint sem CSRF, oculto sem token, valida `asaas-access-token`, JSON e identificador do evento; deduplica pelo ID do Asaas e não altera contrato manual ou ciclo de acesso | 13 testes focados de cobrança passaram; migration 0026 foi aplicada no banco local. Nenhum cliente, cobrança, webhook ou chamada ao Asaas foi criado externamente. |
| 15/09 | Suíte completa após receptor Asaas | `uv run pytest -q` | **475 aprovados, 1 ignorado, 2 subtests aprovados** em 36,96 s. O teste de navegador Python permanece opcional; as telas alteradas foram exercitadas pelo Playwright MCP conforme auditoria registrada. |
| 15/09 | Claude, chave real sem geração | `configure_claude_local_key` e novo `verify_claude_token_endpoint` com texto sintético e endpoint **gratuito** `/v1/messages/count_tokens` | Ambos passaram: chave aceita para `claude-sonnet-5`, 16 tokens contados. Não houve resposta da IA, uso de dado de cliente ou chamada cobrada. Configuração global e cotas ainda precisam de ativação/validação. |
| 15/09 | Claude, teste pago preparado | `verify_claude_messages` usa uma mensagem sintética, 64 tokens de saída no máximo e exige `--cost-approved`; transporte e bloqueio sem aprovação têm teste simulado | Comando sem flag foi recusado antes de qualquer acesso à API. Ainda **não foi executado com a chave real**; estimativa e condição de aprovação constam em [operação da IA](ia-operacao.md). |
| 15/09 | Conexão das caixas | Pesquisa de documentação oficial Microsoft, Google e Exchange; [jornada simples](conexao-caixas-email.md) documentada | A hipótese inicial de app OAuth central foi substituída pelo esclarecimento D-23: cada escritório configura seu próprio aplicativo e consente sua caixa. IMAP genérico usa assistente TLS. Google pessoal requer decisão de verificação do escopo restrito. |
| 15/09 | Suíte completa após a validação da chave | `uv run pytest -q`, Ruff focado, `manage.py check` e `makemigrations --check --dry-run` | **478 aprovados, 1 ignorado, 2 subtests aprovados** em 30,83 s; check/migrations passaram. Esse marco antecede a chamada paga autorizada e o OAuth local registrados abaixo. |
| 15/09 | Claude, geração autorizada | **Uma** chamada sintética a `/v1/messages` com `claude-sonnet-5`, esforço baixo e até 64 tokens de saída, após aprovação específica de custo do responsável | A Anthropic retornou texto, 16 tokens de entrada e 64 de saída; custo calculado US$ 0,000672 antes de câmbio/impostos. Nenhum dado de cliente foi enviado; políticas de cotas e uso do Copiloto por escritório ainda não foram homologados. Não repetir sem nova aprovação específica de custo. |
| 15/09 | OAuth da Triagem, trabalho local | Botões Microsoft/Google, callback com `state`/PKCE, prova de leitura, credential cifrada por escritório e desconexão; fluxo mantém sincronização desligada | 5 testes de OAuth passaram. Sem aplicativos de provedor registrados e sem caixas reais de teste; IMAP e leitura incremental ainda faltam. A autorização da caixa não é a prova de processamento dos anexos. |
| 15/09 | Suíte e interface após OAuth | `uv run pytest -q`, Ruff focado, `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`; Playwright MCP em 1689 × 1005 e 390 × 844 | **483 aprovados, 1 ignorado, 2 subtests aprovados** em 29,61 s; checagens passaram. Estado vazio, caixa autorizada e desconectada, guia, confirmação, teclado, foco, overflow e console foram inspecionados. [Revisão crítica](auditoria-triagem-oauth-2026-09-15.md) delimita estados externos não alcançados. |
| 15/09 | Correção do estado de erro | Um erro da caixa aparecia como “Caixa autorizada” na faixa de status; agora indica erro/recebimento indisponível e passo de reconexão/suporte | Estado reinspecionado em desktop/celular; 6 testes OAuth passaram, incluindo a regressão de status. Suíte completa final: **484 aprovados, 1 ignorado, 2 subtests aprovados** em 31,61 s. |
| 15/09 | Conexão IMAP local | Formulário guiado, DNS público com IP fixado, TLS com certificado/hostname verificados, `select(readonly=True)`/UID, credencial cifrada, throttling e recebimento desligado após conectar | 7 testes IMAP focados passaram, incluindo DNS misto/privado e pinagem do socket. Formulário vazio/erro e espera sintética inspecionados em desktop/mobile; sem servidor real nem anexos. [Revisão crítica](auditoria-triagem-oauth-2026-09-15.md). |
| 15/09 | Suíte após assistente IMAP | `uv run pytest -q`, Ruff focado, format dos arquivos novos, `node --check`, Django check e migrations | **490 aprovados, 1 ignorado, 2 subtests aprovados** em 29,49 s. A suíte antecede somente um novo teste de pinagem de socket, que passou nos 7 testes IMAP focados; não houve alteração do código de produção depois. |
| 15/09 | Renovação OAuth preparatória | Refresh Microsoft/Google com segredo cifrado por escritório e rotação quando o provedor devolve novo refresh token; credencial desconectada/incompatível bloqueada antes do transporte | 8 testes OAuth focados passaram com transporte simulado. Sem app registrado, token real, polling ou persistência de rotação pelo leitor. Fontes oficiais registradas em [conexão de caixas](conexao-caixas-email.md). |
| 15/09 | Suíte após renovação OAuth | `uv run pytest -q`, Ruff/format focados, Django check e migrations | **493 aprovados, 1 ignorado, 2 subtests aprovados** em 33,73 s; nenhum arquivo de migration novo. |
| 15/09 | Padrão Windows por empresa | Função pura `Nome [Domínio código]`, sem escrita, com código exato obrigatório, limpeza de caracteres inválidos no nome e limite de 160 unidades UTF-16 | 5 testes focados e 6 subtests passaram. Falta confirmar fonte do nome/renomeação, raiz no agente, árvore abaixo da empresa, caminho absoluto, colisões case-insensitive, links/junctions e hash. [Padrão](padrao-pastas-windows.md). |
| 15/09 | Suíte e confirmação da desconexão | `uv run pytest -q` após o padrão Windows; confirmação da caixa passou a modal com consequência e ação de manter conexão em primeiro foco. Playwright MCP em desktop/mobile e teclado | **498 aprovados, 1 ignorado, 8 subtestes aprovados** em 42,71 s. Modal, Tab/Enter/Escape, foco de retorno, POST real local, flash, largura móvel e console sem erro foram vistos em caixa sintética. QA removido, aba e servidor fechados. Sem revogação no provedor ou caixa real. [Auditoria](auditoria-triagem-oauth-2026-09-15.md). |

| 15/09 | Fedrizzi e console | Consulta local da organização `fedrizzi-contabilidade`, ordenação dos 8 recentes e Playwright no painel/detalhe | Fedrizzi permanecia ativa; a ordenação alfabética a excluía após QA. Recentes agora ordena por criação. Só a organização QA sintética `qa-operacional-20260915` foi desativada; os dados fiscais protegidos foram preservados. |
| 15/09 | Segundo fator e configuração | Testes de saída com e sem `next`; Playwright em conta sintética: confirmação MFA, saída dos códigos e abertura de `/platform/configuracoes/` | Link de continuar passa a ser rota resolvida; cenário com destino explícito chegou às configurações. A configuração mostra quais quatro variáveis Serpro centrais faltam. Códigos/segredos MFA não foram registrados em evidência. |
| 15/09 | Central Integra e caixa DTE | Escolha DTE/Parcelamentos/DCTFWeb, busca por Domínio e seleção em carteira Fedrizzi de 562 empresas; Playwright desktop/mobile e testes locais | A primeira iteração selecionava as 562. A inspeção de dados revelou 8 sem CNPJ; a versão atual marca só as **554 aptas** com 20 linhas visíveis e mostra a exclusão/cadastro. Busca `Domínio 323` mostrou 1 resultado. O preparo não chamou Serpro. Parcelamentos e consulta DCTFWeb seguem sem implementação externa. |
| 15/09 | Guias/DCTFWeb primeiro uso | Playwright com sessão de suporte Fedrizzi em desktop e 390 × 844, Tab/foco, link da conexão | Estado vazio corrigido aparece com caminho `/app/configuracoes/#dominio`, que abriu no navegador; sem overflow. Dados são obrigações locais Domínio, não declaração Serpro. NFS-e e Conciliação vazias também ganharam próximos passos; estados corrigidos precisam de reinspeção separada. |
| 16/09 | Carteiras operacionais de Guias, NFS-e e Radar | Pesquisa global, filtros de pendência/situação, atalhos para filas e links ao caso exato; formulário compartilhado refeito para largura útil e celular | **611 testes aprovados, 1 ignorado e 8 subtestes aprovados**. Playwright confirmou controles de 44 px e reorganização responsiva em Guias, NFS-e e Radar, sem erros de console nos estados fictícios alcançados. Integrações externas continuam dependendo de homologação real. |
| 16/09 | Certificados e cadastro móvel de empresas | Fila de vencimento/cobertura da carteira, pesquisa por empresa e Domínio, empresa exata como próximo passo; tabelas viram cartões no celular | A demo passou a simular cobertura somente na sessão, sem aceitar PFX/senha nem gravar na organização central. Playwright confirmou desktop, 390 × 844, modal, foco, recarga da sessão, controles de 44 px e zero erro de console. **613 testes aprovados, 1 ignorado e 8 subtestes aprovados** antes do último ajuste apenas estrutural de cartões. |
| 15/09 | Suíte após Central, MFA e estados vazios | `uv run pytest -q`; Ruff Python focado; `manage.py check` | **512 aprovados, 1 ignorado, 8 subtestes aprovados** em 38,15 s; Ruff e Django check passaram. Testes simulados e telas vazias não homologam Serpro, ADN ou escritórios reais. |
| 15/09 | Triagem substitui Jornadas no catálogo e contratos de teste | Migração local; `uv run pytest -q`, `manage.py check`, `makemigrations --check --dry-run`; consulta read-only do banco local | **515 aprovados, 1 ignorado, 8 subtestes aprovados** em 32,16 s; check/migrações passaram. Banco local: 0 jornadas, 0 habilitações Jornadas, 6 habilitações Triagem, 0 contratos/planos com Jornadas. O simulador legado foi removido. Ruff focado passou; Ruff global ainda aponta 9 problemas preexistentes fora desta troca. Sem homologação de caixa real. |
| 15/09 | Tarifação oficial Integra Contador | Playwright no [produto da Loja Serpro](https://loja.serpro.gov.br/integra-contador/product/integracontador), aba “Preço”, e leitura do [catálogo oficial de serviços](https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/catalogo_de_servicos/) | A faixa 1 vigente exibiu R$ 0,24/consulta, R$ 0,32/emissão e R$ 0,40/declaração; faixas 2–8 diminuem. O catálogo classifica lista/detalhe da Caixa, recibo/declaração completa DCTFWeb e consultas de Parcelamentos como **Consultar**, e as guias DCTFWeb/Parcelamentos como **Emitir**. A fatura Mewstack ainda precisa confirmar que o **Tipo** do catálogo determina a categoria faturada, sobretudo para o indicador **Monitorar**. O responsável decidiu usar faixa 1 para pesos. Nenhuma contratação ou chamada paga foi feita. |
| 15/09 | OAuth configurado pelo escritório | Migração `triage.0004` aplicada localmente; Microsoft/Workspace usam app OAuth por escritório com segredo cifrado e vínculo da caixa; Gmail pessoal usa caminho central Mewstack separado, gated por `TRIAGE_GOOGLE_PERSONAL_VERIFIED` | 14 testes OAuth locais passaram, incluindo escolha central quando há app Workspace, rejeição de endereço Workspace no caminho pessoal e rejeição de Gmail pessoal no caminho Workspace. Sem app externo registrado, retorno HTTPS de produção ou caixa real. O guia foi inspecionado em desktop/mobile e o formulário positivo/erro com QA sintético. |
| 15/09 | Suíte após OAuth por escritório e UI de conexão | `uv run pytest -q`, Ruff focado, `manage.py check`, verificações de sintaxe JavaScript | **520 aprovados, 1 ignorado, 8 subtestes aprovados** em 41,92 s. Os fornecedores externos foram simulados; [auditoria renderizada](auditoria-triagem-aplicativos-2026-09-15.md) delimita os estados vistos. |
| 15/09 | Demonstração pública sob controle do usuário | Removido ciclo automático de módulos; corrigido bloco numérico da Triagem; abas acessíveis com seleção por seta/Home/End e URL `?demo=...` | Playwright desktop 1366 × 900 e celular 390 × 844: tab/painel permaneceram iguais após 6 segundos, foco visível, rolagem horizontal ausente e console sem erros na página normal. A demonstração é ilustrativa e não prova operações externas. |
| 15/09 | Verificação final desta rodada | `uv run pytest -q`, Ruff nos arquivos Python alterados, `makemigrations --check --dry-run`, `node --check` dos dois scripts e `git diff --check`; [diretrizes Vercel atuais](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) reaplicadas aos arquivos de interface alterados | **521 aprovados, 1 ignorado e 8 subtestes aprovados** em 40,47 s. Nenhuma nova migração detectada, scripts válidos e sem erros materiais na revisão estática da interface. Playwright desta rodada inspecionou guia OAuth e demonstração em desktop/mobile; estados externos não foram alcançados. Abas Playwright fechadas. Conta/aplicativo/ativação de módulo QA desta rodada removidos; conta de plataforma QA desativada, senha inutilizada e 2 sessões de suporte abertas fechadas. Fedrizzi permaneceu ativa e intocada. |
| 15/09 | Entrada de anexos e leitor IMAP incremental | `triage.0005` aplicada localmente; teste com IMAP sintético, MIME com anexo, data interna antes/depois do marco, SELECT readonly, `BODY.PEEK[]`, UIDVALIDITY/cursor, reenvio e isolamento de dois escritórios | **525 aprovados, 1 ignorado e 8 subtestes aprovados** em 34,73 s. O mesmo arquivo em mensagens distintas gera duas entregas em quarentena até a política Q-20; repetir a mesma mensagem+parte não duplica. Caminho físico `.bin` não usa extensão recebida. Sem caixa real, ativação pelo escritório, agenda, scanner antimalware ou leitores Graph/Gmail; nenhum e-mail externo foi acessado. |
| 15/09 | Veredito antimalware em quarentena | `triage.0006` aplicada localmente; adaptador candidato ClamAV [INSTREAM oficial](https://docs.clamav.net/manual/Usage/ClamdProtocol.html) somente por socket Unix local ou TCP loopback; teste com socket sintético limpo, resposta incompleta, scanner ausente e detecção de ameaça | **528 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,47 s. Ameaça confirmada rejeita o anexo; falha fica em quarentena com veredito persistente; resultado limpo também fica em quarentena até aprovação da política de formatos/assinaturas. Nenhum daemon ClamAV está instalado neste PC, nenhuma varredura real foi homologada e nenhum recurso externo ou custo foi criado. |
| 15/09 | Leitor Microsoft Graph incremental | [Delta e anexos oficiais](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0) lidos; `poll_graph_mailbox` exercitado com duas páginas, arquivo inline, link de outro domínio, reenvio e arquivo acima de 25 MB em transporte sintético | **531 aprovados, 1 ignorado e 8 subtestes aprovados** em 37,55 s. O cursor avançou apenas após a página completa; link externo e anexo grande não avançaram o checkpoint. IDs imutáveis são pedidos em cada chamada. O leitor lista anexos mesmo quando `hasAttachments=false`, conforme a [semântica oficial da mensagem](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0). Sem app registrado/consentimento/caixa real, projeção `$select` e limites de um tenant real ainda requerem piloto; nenhuma chamada Graph externa foi feita. |
| 15/09 | Leitor Gmail/Workspace incremental | [Sincronização e expiração oficiais](https://developers.google.com/workspace/gmail/api/guides/sync), [histórico](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) e [anexos](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get) pesquisados; `poll_gmail_mailbox` testado com snapshot `historyId`, listagem paginada, eventos `messagesAdded`/`labelsAdded`, 404, replay no meio da página e anexo grande com transporte sintético | **535 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,73 s. Checkpoint após todos os anexos da página; 404 reinicia full sync pelo novo snapshot sem perder entregas já recebidas. Nenhuma chamada Gmail externa foi feita; app central pessoal ainda depende de registro/verificação Google e caixas reais de consentimento/piloto. |
| 15/09 | Execução periódica da Triagem | `triage.dispatch_active_mailboxes` incluída no Celery Beat a cada 5 minutos; fila apenas caixas com escritório ativo, caixa ativa/status ativo e data inicial; worker usa lease com token e prazo para impedir sobreposição e permitir recuperação de crash; flag `TRIAGE_EMAIL_POLL_ENABLED=false` é o padrão | **539 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,55 s. Testes cobrem rotina desligada sem chamada ao provedor, seleção de caixas, execução simultânea bloqueada e falha saneada com lease liberada. Não há caixa real ativada nem autorização de custo para ligar a flag. A cadência de 5 min é técnica e configurável antes do piloto; SLA comercial, monitoramento e política de retentativa ainda não foram aprovados. |
| 15/09 | Falhas e retentativas da Triagem | Conforme [Graph](https://learn.microsoft.com/en-us/graph/errors) e [Gmail](https://developers.google.com/workspace/gmail/api/guides/handle-errors), 429/5xx e indisponibilidade de rede recebem estado transitório com backoff exponencial (5 min até 6 h, respeitando `Retry-After` até 24 h); scheduler pula caixa antes de `poll_retry_after`; credencial/contrato/dados inválidos deixam caixa em erro para intervenção. IMAP separa socket/timeout de recusa do provedor. Migration `triage.0008` aplicada localmente | **544 aprovados, 1 ignorado e 8 subtestes aprovados** em 36,97 s. Cursor não avançou em falhas sintéticas e lease foi liberada. A tela então ainda mostrava “recebimento indisponível” para caixa ativa com falha transitória e “precisa reconectar” para qualquer erro permanente, mesmo quando a causa podia ser outra; ver revisão posterior da lista. Nenhuma consulta externa foi feita. |
| 15/09 | Lista operacional das caixas da Triagem | `present_mailbox` separa configuração, leitura, retentativa, erro e desconexão; `triage.html` mostra última/próxima consulta, remédio e estado vazio correto. `ui-ux-pro-max`, `watermelon-ui`, referências SaaSFrame, fonte atual Vercel e Playwright MCP foram consultados; [auditoria dos estados](auditoria-triagem-estados-caixas-2026-09-15.md) registra evidência e limites. | `uv run pytest -q`: **545 aprovados, 1 ignorado, 8 subtestes aprovados** em 36,60 s; Ruff e `manage.py check` passaram. Playwright desktop/mobile/escuro inspecionou somente caixas sintéticas, com console limpo; abas e servidor de QA fechados. Ativação pelo escritório, provedores reais e fila de anexos ainda não foram validados. |
| 15/09 | Fila operacional da Triagem | Lista de anexos recebidos acima da conexão dos provedores, com etapa, segurança, origem, filtro por GET e paginação de 20; administrador vê itens ainda sem empresa e operador apenas suas empresas. Detalhe segue a mesma regra; download não verificado continua bloqueado. [Auditoria das caixas e fila](auditoria-triagem-estados-caixas-2026-09-15.md) registra referências e inspeção. | `uv run pytest -q`: **546 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,36 s; `manage.py check`, Ruff e `diff --check` passaram. Playwright desktop/mobile/claro/escuro testou três anexos sintéticos, filtro, vazio, foco e console sem erros/avisos; aba/servidor de QA fechados. Não houve anexo nem scanner real; classificação, revisão e arquivamento permanecem pendentes. |
| 15/09 | Caixa DTE: separar abertura incerta da fila a abrir | Filtros/contadores excluem `reading`/`unknown` e ciência já observada de “A abrir”; a fila pendente mostra estados específicos, links de acesso, filtro vazio correto e selects/indicadores legíveis no escuro. “Selecionar todas” foi inspecionado sem envio. [Auditoria DTE](auditoria-dte-fila-incerta-2026-09-15.md) registra pesquisa Serpro, referências SaaS e limites. | `uv run pytest -q`: **547 aprovados, 1 ignorado, 8 subtestes aprovados** em 37,35 s; 11 testes focados DTE/ciência, Ruff e `manage.py check` passaram. Playwright desktop/mobile/claro/escuro: quatro mensagens sintéticas, fila, filtro, aviso jurídico, foco, selecionador local; console final 0 erros/avisos, aba/servidor fechados. Contrato e ciência Serpro reais não foram testados. |

| 15/09 | Caixa DTE: continuar páginas por empresa | Ponteiro Serpro salvo por item; operador prepara uma única continuação na própria tabela, que entra na fila para cotação/autorização de consumo individual. Formato de até 24 dígitos pesquisado na documentação oficial; [auditoria da paginação](auditoria-dte-paginacao-2026-09-15.md). | `uv run pytest -q`: **550 aprovados, 1 ignorado, 8 subtestes aprovados** em 36,34 s. Playwright desktop/mobile: ação/foco/estado após POST, sem overflow do documento nem erros/avisos no console; cenário SQLite, aba e servidor encerrados. Nenhuma chamada paga ou resposta Serpro real foi feita. |

| 15/09 | Pesquisa e leitores de Parcelamentos | Cinco serviços PARCSN ordinário pesquisados nas páginas oficiais e registrados no catálogo; parsers locais de pedidos, detalhe, pagamentos, parcelas disponíveis e DAS base64 limitam tamanho, conferem acordo e formato. [Pesquisa Parcelamentos](pesquisa-parcelamentos-integra-2026-09-15.md). | `uv run pytest -q tests/test_integra_parcelamento.py tests/test_integra_client.py`: **23 aprovados**; Ruff passou. Apenas payloads sintéticos: sem fila, autorização, armazenamento, UI, chamada Serpro ou emissão real. Modalidades da versão vendável aguardam escolha do responsável. |

| 15/09 | Carteira técnica de tokens por módulo | `TokenPriceBook`/rates/pesos/medidores/eventos e `token_billing.py` adicionados; reserva local com preço comum, franquia própria, teto global e idempotência. `close_competence` cria uma fatura com linhas por módulo só após flag e tabela ativa; recusa medidor legado misturado. Gravações normais congelam preço, franquia e pesos após aceite. Flag `TOKEN_BILLING_ENABLED=false` no padrão. | `uv run pytest -q`: **559 aprovados, 1 ignorado, 8 subtestes aprovados** em 38,57 s; 5 testes focados de tokens, Ruff e migration check passaram após a mudança final de proteção. Valores e escritórios sintéticos, sem cobrança externa. Ainda não há preços aprovados nem módulos migrados para essa carteira; testar concorrência, QuerySet.update, retry/estorno, UX e fatura real antes de habilitar. |

| 15/09 | Fechamento mensal seguro | Beat diário às 00:05 agora fecha sempre o último mês completo; chamada manual ao mês atual/futuro é recusada. Fatura aguarda eventos/saldos reservados, e cotação/reserva novas são bloqueadas após faturar a competência. Locks por organização alinham reserva, liquidação e fechamento. [Auditoria do fechamento](auditoria-fechamento-competencia-2026-09-15.md). | `uv run pytest -q`: **563 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,51 s; 18 testes focados de billing/token/tasks e Ruff passaram. Sem cobrança externa. Uma reserva pendente ainda interrompe a rodada dos escritórios seguintes; console individual e prova concorrente PostgreSQL faltam. |
| 15/09 | Fechamento parcial por escritório | Rodada diária segue após reserva pendente, registra estado Parcial e quantidade adiada. Adiamento persistido e exibido no console com competência/link do escritório; retentativa resolve registro sem duplicar fatura. [Auditoria atualizada](auditoria-fechamento-competencia-2026-09-15.md). | **565 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,10 s; Ruff, checks Django/schema e Playwright desktop/mobile com escritório sintético passaram. Console final sem erro; servidor/aba fechados. Diagnóstico da reserva, retentativa pelo console e concorrência PostgreSQL faltam. Sem cobrança externa. |
| 15/09 | Triagem: saída da quarentena e biblioteca interna | Verificação de formato após antimalware limpo vinculado ao hash; aprovação humana termina em pronto para arquivar; cópia privada distinta e hash conferido antes de marcar arquivado. Protótipo manual e destino Windows sem agente não são tratados como arquivo entregue. [Auditoria](auditoria-triagem-formato-biblioteca-2026-09-15.md). | **579 aprovados, 1 ignorado, 8 subtestes aprovados** em 45,03 s; Ruff e migrações passaram. Testes usam scanner/arquivo/escritório sintéticos. Classificação, revisão, download e homologação real ainda faltam. |
| 15/09 | Triagem: detalhe e download conferido | Detalhe exibe origem/vereditos/estado, histórico com rótulos legíveis e link somente para biblioteca interna arquivada. Download com empresa permitida, hash da cópia, resposta privada e auditoria; adulteração é recusada. [Auditoria da tela](auditoria-triagem-detalhe-download-2026-09-15.md). | **580 aprovados, 1 ignorado, 8 subtestes aprovados** em 40,97 s; Playwright desktop/mobile com teclado, foco, arquivo baixado, quarentena e console sem erro; abas/servidor fechados. Revisão e classificação na tela ainda faltam. |
| 15/09 | Copiloto: uso Sonnet e auditoria de tentativa | Resposta simulada registra tokens de entrada/saída e cache; auditoria marca respondida/incerta/bloqueada, preservando reserva em timeout. Migração marca permissões antigas sem prova como incertas. [Auditoria](auditoria-copiloto-egress-2026-09-15.md). | **581 aprovados, 1 ignorado, 8 subtestes aprovados** em 39,50 s; Ruff/checks/schema passaram. Nenhuma chamada paga. |
| 15/09 | Copiloto: reserva durável antes da chamada | Mensagem/reserva de uso são confirmadas antes do I/O local; cota, auditoria e hash do payload Claude são confirmados antes da chamada externa, executada sem transação aberta. Resultado e resposta são persistidos depois. Teste transacional inspecionou a reserva dentro do mock do fornecedor. [Auditoria atualizada](auditoria-copiloto-egress-2026-09-15.md). | **582 aprovados, 1 ignorado, 8 subtestes aprovados** em 40,39 s; Ruff, Django e schema passaram. Nenhuma chamada paga. Falta reconciliação de tentativa reservada após morte do worker e retry seguro. |
| 15/09 | Copiloto: identificar tentativa perdida | Auditoria vinculada à mensagem e à reserva; tarefa agendada identifica tentativas Claude antigas e marca resultado incerto sem liberar a cota nem repetir chamada. Teste cobre tentativa perdida, reconciliação idempotente e resposta comprovada tardia. [Auditoria atualizada](auditoria-copiloto-egress-2026-09-15.md). | **582 aprovados, 1 ignorado, 8 subtestes aprovados** em 42,08 s; Ruff, Django e schema passaram. Nenhuma chamada paga. Falta estado de interrupção na conversa, dedupe de POST, decisão de suporte e observabilidade da rotina. |
| 15/09 | Copiloto: envio e recuperação pela conversa | Playwright encontrou POST com empresa vazia em conversa existente; corrigido. Nova conversa ganhou busca/seleção de empresa; mesma chave de envio não duplica resposta/reserva; pergunta sem resposta mostra andamento/incerteza/interrupção e protocolo. [Auditoria da conversa](auditoria-copiloto-conversa-recuperacao-2026-09-15.md). | **585 aprovados, 1 ignorado, 8 subtestes aprovados** em 41,34 s; Ruff, Django e schema passaram. Playwright local isolado desktop/mobile/claro/escuro conferiu erro, vazio, busca, foco, envio e resposta; console dos estados finais 0 erros. Sem API paga. Falta decisão de suporte da reserva e piloto externo. |

| 15/09 | P0: revisão de caso NFS-e e configuração de Triagem | Painel/empresa/fila abrem o caso exato; detalhe exibe evidência, XML original auditado e resultado da decisão. Fila de anexos separada de “Gerenciar caixas”; erro IMAP foi inspecionado em navegador sintético. [Prova e limites](execucao-p0-area-de-trabalho-2026-09-15.md). | `uv run pytest -q`: **588 aprovados, 1 ignorado e 8 subtestes aprovados**; Ruff focado e Django check passaram. Playwright desktop/celular/foco/erro/vazio sem overflow nem erro de console nos estados alcançados; aba/servidor encerrados. Fedrizzi não foi alterada. Sem Serpro, e-mail ou outra chamada paga. Demo isolada e homologação real ainda pendentes. |
| 15/09 | P0: base da demo central e decisões da Triagem | `Organization.is_demo`, MFA dispensado só para membro exclusivo da demo; DTE/guia/Copiloto e caixa de exemplo sem fornecedor; mensagem DTE fictícia aberta com confirmação, protocolo local e sem ciência oficial; anexos fictícios percorridos até aprovação, arquivo íntegro e download. A revisão da Triagem agora ocorre no detalhe com motivo e confirmação para rejeição. [Isolamento e riscos restantes](auditoria-demo-isolamento-2026-09-15.md). | **597 aprovados, 1 ignorado e 8 subtestes aprovados**; Django check passou. Navegador sintético desktop/celular, foco, abertura DTE e arquivamento Triagem, 0 erros de console nos estados alcançados. Ruff foi corrigido após a suíte; repetir na próxima rodada. Ainda faltam isolamento de progresso dos visitantes, travas transversais, Parcelamentos e homologação real; demo não está pública. |
| 16/09 | P0: filas por carteira e painel de próxima ação | Guias, Revisões, Triagem e Conciliação ganharam pesquisa e filtros operacionais; a Visão Geral separa pendências por módulo e abre cada fila já filtrada. Revisões viram cartões no celular, mantendo ação e evidência do caso exato. Referências: `ui-ux-pro-max` (seleção em lote e feedback), Watermelon Astrix (pipeline de revisão), Vercel Web Interface Guidelines e produto existente. | **610 aprovados, 1 ignorado e 8 subtestes aprovados** em 56,17 s; Ruff focado, Django check e migrations passaram. Playwright desktop/mobile confirmou dashboard, filtros, foco, contagem, cartões móveis, ausência de overflow e console limpo. Nenhum fornecedor externo foi chamado. Seleção em lote de emissão continua bloqueada até existir cotação, autorização e atomicidade reais. |

## Próxima prova exigida por área

- **IA:** chave e modelo Sonnet 5 já passaram pela contagem gratuita. Faltam limites globais/por escritório, consentimento e cenário autorizado de teste cobrado. Verificar resposta, erro recuperável, uso, custo e ausência de segredo no navegador/log. O PC local exigirá teste de preferência do runtime e virada controlada.
- **Triagem:** escritório conecta cada tipo de caixa pelo guia interno; primeiro poll respeita corte/cursor; cada anexo passa por proteção, identificação, revisão e destino escolhido; hash de destino e checklist são comprovados. Decisões de taxonomia, formatos, padrão Windows e retenção estão em [dúvidas abertas](duvidas-abertas.md).
- **Serpro, ADN/NFS-e, Domínio e Siescon:** piloto com contrato, credenciais, certificados e amostras autorizados; verificar repetição, falha, cota, escopo e resultado persistido. Não chamar um mock de homologação externa.
- **Asaas e contrato manual:** uma fatura, pagamento e eventos idempotentes; contrato manual imune ao webhook; carência, somente leitura e reativação pela regra confirmada.
- **Produção:** resolver workflow/ambiente de deploy, SMTP/DNS, contatos e termos finais, saúde Celery, backup e restauração. Recursos e APIs cobrados requerem confirmação específica de custo imediatamente antes da ação.
- **Telas:** repetir a auditoria para cada nova tela ou mudança material; para os estados já alcançados, consultar a [prova registrada](auditoria-ui-2026-09-15.md). Conexão OAuth, anexos recebidos por e-mail e seus estados de carga/erro aguardam implementação.

Qualquer nova execução acrescenta uma linha com comando/ambiente, resultado e limitação. Números de teste não devem ficar como promessa permanente no README.
| 16/09 | Guias: carteira real de apurações Domínio | `FOVGUIAINSS` entrou na allowlist ODBC somente leitura, com recorte de 18 meses, valor positivo e projeção mínima. A tela separa 3.022 apurações locais de 241 empresas das guias oficiais, pesquisa a carteira e mostra empresa, competência, vencimento e valor reais sem declarar dívida ou pagamento. [Auditoria Fedrizzi](auditoria-guias-dctfweb-fedrizzi-2026-09-15.md). | 17 testes focados e a suíte completa com **615 aprovados, 1 ignorado e 8 subtestes** passaram; Playwright autenticado na Fedrizzi em desktop/celular validou busca, 30 resultados por página visual, cartões móveis, ação 309 × 44 px, zero overflow e console limpo. Nenhuma linha Domínio e nenhum fornecedor externo foram alterados/chamados. Serpro ainda precisa reconciliar declaração, recibo, saldo e guia oficial. |
| 16/09 | DCTFWeb: contrato correto e prova do PDF | `GERARGUIA31` agora recebe categoria/ano/mês conforme o Serpro; HTTP 200 só conclui após validar o PDF base64. Download oficial reutiliza a evidência cifrada e não cria nova chamada. Apurações importadas entram como `discovered` e não podem ser emitidas antes da reconciliação. | 47 testes focados e a su?te completa com **626 aprovados, 1 ignorado e 8 subtestes** passaram, incluindo payload oficial, competência inválida, resposta sem PDF, documento corrompido, liberação de uso e download sem fornecedor. `CONSDECCOMPLETA33` e `CONSRECIBO32` ainda precisam do fluxo pago de consulta e aceite. |
| 16/09 | DCTFWeb: declaração completa e recibo | A apuração abre cotação separada de `CONSDECCOMPLETA33` e `CONSRECIBO32`; cada confirmação reserva consumo, persiste estado/PDF e impede retentativa em resultado incerto. Downloads reutilizam a evidência cifrada. Demo gera resultado fictício sem fornecedor. | **633 aprovados, 1 ignorado e 8 subtestes**; 21 focados. Nenhuma chamada paga foi feita. Falta configurar as tarifas no contrato Fedrizzi, homologar chamada autorizada e reconciliar a declaração com a apuração antes de promover guia para emissão. Playwright indisponível nesta passagem por transporte MCP encerrado. |
| 16/09 | DCTFWeb: consumo migrado para tokens | Declaração completa, recibo e emissão de DARF reservam e liquidam `TokenUsageEvent` no módulo `integra`. A confirmação mostra peso inteiro, franquia e excedente; tabela/peso ausente bloqueia a operação. O worker ainda concilia eventos legados já enfileirados. | 28 testes focados e suíte completa com **633 aprovados, 1 ignorado e 8 subtestes**. Migration `hub.0030` aplicada. Nenhum peso ou preço foi inventado para a Fedrizzi e nenhuma chamada paga foi feita. Falta a área de proposta/aceite da tabela de tokens para uso sem administração de banco. |
| 16/09 | Tokens: proposta comercial e aceite do escritório | Comercial/Admin da Mewstack monta uma proposta em rascunho com valor único do token, mensalidade/franquia da Central Integra, pesos inteiros DCTFWeb e teto mensal. Dono/Admin revisa todos os termos em Configurações, confirma explicitamente e escolhe vigência futura. Termos aceitos congelam; mudanças exigem nova versão. O consumo ativo substitui a apresentação legada por chamada. | **634 aprovados, 1 ignorado e 8 subtestes**. Configuração local recebeu `TOKEN_BILLING_ENABLED=true`; o padrão seguro do código continua desligado e o `.env.example` documenta a ativação. Nenhuma cobrança ou API externa foi acionada. Playwright continuou indisponível por transporte MCP encerrado. |
| 16/09 | Parcelamentos: área de trabalho da demonstração | A escolha antes indisponível na Central agora abre uma jornada por empresa: consulta fictícia, acordo PARCSN, consolidação, parcelas paga/disponível e emissão fictícia de DAS. O estado fica isolado por sessão e a tela real recusa chamada enquanto tarifa e homologação não existem. | **13 testes de demo aprovados**, incluindo isolamento entre dois navegadores e ausência de mutação compartilhada. Ruff e `manage.py check` passaram. O MCP Playwright permaneceu indisponível (`Transport closed`), portanto esta rodada não declara inspeção visual. Nenhuma chamada Serpro ou cobrança ocorreu. |
| 16/09 | Demo: Conciliação segura por sessão | A tela apresenta OFX e candidatos Domínio sintéticos, permite resolver uma ambiguidade e mantém o resultado apenas na sessão. Upload real fica oculto na demo e o texto afirma que não há escrita no Domínio. | **637 testes aprovados, 1 ignorado e 8 subtestes**; isolamento entre dois visitantes e ausência de `ReconciliationMatch` compartilhado cobertos. Playwright MCP seguiu indisponível (`Transport closed`). |
| 16/09 | Landing: promessa alinhada e acesso à demo | A página pública agora oferece a demo fictícia quando o ambiente está realmente pronto, afirma 14 dias sem cartão e sem cobrança automática e explica ativação gradual. Textos de NFS-e, DCTFWeb, Central e recebimento deixaram de prometer integração antes da configuração/homologação. | **639 testes aprovados, 1 ignorado e 8 subtestes**. `ui-ux-pro-max`, Watermelon e as diretrizes Vercel foram consultados; Watermelon não retornou referência próxima. Playwright MCP permaneceu indisponível (`Transport closed`). |
| 16/09 | Caixa DTE migrada para tokens | Consulta da caixa por empresa e abertura de teor/poss?vel ci?ncia receberam pesos pr?prios na proposta da Central Integra. A autoriza??o mostra tokens, franquia e excedente em reais; cada item persiste o evento que permitiu a chamada. Tabela ativa usa `TokenUsageEvent`; trabalhos antigos ainda liquidam `UsageEvent` sem criar uma segunda cobran?a. | Migration `hub.0031` aplicada; **640 testes aprovados, 1 ignorado e 8 subtestes**, Ruff, Django check e schema limpos. Demo respondeu HTTP 200. Nenhuma chamada Serpro ou cobran?a externa foi feita. Watermelon n?o encontrou refer?ncia pr?xima; Playwright MCP permaneceu indispon?vel (`Transport closed`). |
| 16/09 | Guias Fedrizzi: carteira acess?vel e DCTFWeb em lote | O ciclo local da Fedrizzi saiu de `provisioning` para `active` como piloto interno autorizado, sem contrato, pre?o ou cobran?a. A tela autenticada leu 3.145 linhas ODBC e exibiu 3.022 apura??es de 241 empresas ativas; 30 linhas carregadas podem ser selecionadas de uma vez, com pr?via agregada de tokens e autoriza??o at?mica de declara??o ou recibo. A demo grava o lote somente na sess?o. | Valida??o autenticada retornou HTTP 200, 3.022 itens, 30 seletores e nenhum estado vazio antigo. **642 testes aprovados, 1 ignorado e 8 subtestes**; Ruff, Django check, schema e sintaxe JS limpos. Nenhuma consulta Serpro nem cobran?a foi executada. Playwright MCP permaneceu indispon?vel (`Transport closed`) e Watermelon n?o encontrou bloco semelhante. |
| 16/09 | Triagem: configuração operacional de caixa e destino | Dono ou administrador configura na própria tela a pasta/etiqueta, data inicial, filtros de remetente e assunto e a ativação da leitura. Os três coletores aplicam os filtros antes de baixar anexos. O escritório também escolhe biblioteca interna ou raiz Windows; o padrão da pasta mantém nome da empresa e código Domínio. Enquanto o agente local não validar a raiz Windows, o arquivamento é bloqueado com recuperação explícita, sem gravar no destino errado. | **646 testes aprovados, 1 ignorado e 8 subtestes**; 47 testes focados de Triagem, Ruff, Django check e schema limpos. Render autenticado da Fedrizzi respondeu HTTP 200. Nenhuma caixa real, scanner, agente Windows ou API externa foi acionada. Watermelon não encontrou referência próxima; Playwright MCP permaneceu indisponível (`Transport closed`). |
| 16/09 | Configurações: cobrança apresentada somente em tokens | A área do escritório deixou de exibir franquia e excedente por chamada. Agora mostra somente proposta, valor do token, franquia por módulo, pesos, teto, vigência e consumo. Uma tabela aceita para competência futura aparece como programada e não como vigente; o endpoint legado de política por chamada recusa novas alterações. | **646 testes aprovados, 1 ignorado e 8 subtestes**; 70 testes focados de workspace/contratos, Ruff, Django check e render autenticado da Fedrizzi limpos. Watermelon não encontrou referência próxima. A auditoria Vercel foi aplicada; Playwright MCP permaneceu indisponível (`Transport closed`). |
| 16/09 | Copiloto migrado para a carteira de tokens | O Comercial pode incluir o módulo de IA numa proposta com mensalidade, franquia e peso inteiro por resposta. O dono vê termos de todos os módulos antes do aceite e também após a vigência. Com tabela ativa, `ai.answer` reserva e liquida `TokenUsageEvent`; a auditoria Claude referencia o mesmo evento. Sem termos de IA numa tabela vigente, a operação fica bloqueada pela proteção contra mistura de medidores. | Migration `intelligence.0026` aplicada. **648 testes aprovados, 1 ignorado e 8 subtestes**; testes cobrem proposta incompleta, aceite transparente, resposta Sonnet simulada, liquidação e vínculo de auditoria. Nenhum preço foi inventado e nenhuma chamada Anthropic foi feita. |
| 16/09 | Triagem: arquivamento Windows comprovado pelo agente | A aprovação cria trabalho isolado por escritório. O agente compara a raiz local com a raiz escolhida, recusa escape e reparse points, baixa só o anexo validado, grava temporário, confere tamanho/SHA-256 e renomeia atomicamente. A tela separa fila, cópia, falha recuperável e destino confirmado; `Arquivado` só ocorre após a prova. | **651 testes aprovados, 1 ignorado e 8 subtestes** em 59,34 s; 100 testes focados de Triagem/workspace, Ruff, Django e os dois projetos .NET passaram. Nenhuma pasta real foi alterada. A homologação no PC e compartilhamento Windows do primeiro escritório ainda é obrigatória. Watermelon não encontrou referência próxima; Playwright MCP permaneceu indisponível (`Transport closed`). |

| 16/09 | Parcelamentos PARCSN: operação real preparada | A área de trabalho pesquisa empresa/CNPJ/código Domínio, permite selecionar todas as linhas exibidas ou um lote de até 30, calcula tokens/excedente antes da autorização, persiste cada tentativa e protocolo, consulta pedidos/detalhe/parcelas e emite DAS. O PDF validado é baixado do resultado salvo sem nova chamada. Falha de transporte fica em resultado incerto e não é repetida automaticamente. | **656 testes aprovados, 1 ignorado e 8 subtestes**; 14 testes focados de parser/operação passaram. Django, migrations e Ruff passaram. A migration 0032 foi aplicada no banco local. Nenhuma chamada Serpro ocorreu. O piloto real continua obrigatório e depende de tabela de tokens aceita; Playwright permaneceu indisponível (Transport closed) e os navegadores CUA não estavam disponíveis. |

| 16/09 | Guias/DCTFWeb: agrupamento operacional validado na Fedrizzi | O DSN real retornou 3.145 componentes no recorte; 3.022 pertencem às 562 empresas ativas. A fila agora agrupa duplicidades por empresa/competência em **2.943 competências para 241 empresas**, mostra quantidade de componentes, soma local e intervalo de vencimentos e gera uma única seleção DCTFWeb por competência. | GET autenticado real retornou 200, 30 competências visíveis e nenhum texto antigo de fonte ausente. 15 testes focados passaram. Nenhuma linha ODBC foi alterada e nenhuma chamada Serpro ocorreu. Watermelon não encontrou referência próxima; Playwright permaneceu indisponível (Transport closed). |

| 16/09 | DCTFWeb: reconciliação entre documentos, Domínio e emissão | Depois que declaração completa e recibo ficam disponíveis, a confirmação relê a empresa/competência no ODBC, agrega componentes e cria ou atualiza a guia `ready` com referência técnica hash. Valores do navegador são ignorados; ausência de qualquer PDF ou desaparecimento da apuração bloqueia a promoção. A tela mantém a soma como cálculo Domínio e manda conferir o valor oficial no DARF. | **658 testes aprovados, 1 ignorado e 8 subtestes**. Ruff, Django e migrations passaram. Nenhuma chamada Serpro ocorreu. Playwright continuou indisponível (Transport closed). |
| 16/09 | NFS-e ADN: cliente, checkpoint e área de trabalho | Implementado `GET /contribuintes/DFe/{NSU}` com mTLS A1, CNPJ raiz, limite de 50 documentos, base64/gzip, XML seguro, lote transacional, dedupe por empresa, lease, backoff e espera de uma hora ao alcançar o maior NSU. A tela mostra cobertura, status, erros, frescor e permite ativar/pausar/repetir até 100 empresas exibidas. `NFSE_ADN_SYNC_ENABLED` fica falso até o piloto restrito autorizado. | **670 testes aprovados, 1 ignorado e 8 subtestes** em 61,78 s. Ruff, Django, migrations e `git diff --check` passaram. A Fedrizzi renderizou 100 empresas na carteira. A demo provou progresso isolado por sessão sem alterar o escritório central. Nenhuma chamada ADN ocorreu; Playwright permaneceu indisponível (`Transport closed`). |

## 16/09/2026 ? console de escrit?rios e Concilia??o

- A lista de escrit?rios do console deixou de usar uma coluna estreita de bot?es ?Abrir?: a linha inteira agora ? um link sem?ntico, com foco vis?vel e composi??o m?vel em cart?o.
- A Concilia??o passou a exibir evid?ncia de `AccountingEntry`, comparar candidatos das duas fontes e preservar decis?es manuais na reconstru??o.
- Valida??o local: 671 testes aprovados, 1 ignorado e 8 subtestes; Ruff, `manage.py check` e migrations sem pend?ncias.
- A inspe??o Playwright permaneceu indispon?vel porque o MCP retornou `Transport closed`; a valida??o visual em navegador real ainda precisa ser repetida.

## 16/09/2026 ? cust?dia central do certificado Integra Contador

- O Console Mewstack agora recebe `.pfx`/`.p12` de at? 2 MB, valida senha, chave privada e certificado antes de salvar.
- PKCS#12 e senha ficam cifrados com AES-256-GCM no banco; a tela mostra somente nome, sujeito, validade e os 12 ?ltimos caracteres do SHA-256. N?o existe rota de download.
- O cliente Integra usa primeiro o certificado armazenado; `INTEGRA_CERTIFICATE_PATH` permanece apenas como fallback legado.
- Migration `platform.0032` aplicada localmente; 44 testes focados aprovados.
## 18/09/2026 — Etapa 02 concluída localmente (V-009)

- Fechada a etapa de cadastro, acesso e administração no nível de implementação/teste local. As regras comerciais D-79 estão documentadas; a integração de cobrança pertence à etapa 10.
- APIs, isolamento e demonstração foram executados em banco de testes; 22 testes de autorização/API e 4 testes de isolamento da demo passaram. O browser confirmou MFA, painel autenticado, equipe, empresas, configurações, foco, responsividade e console limpo.
- A massa demo não foi regravada: o comando recusou corretamente usar um slug operacional existente. SMTP/DNS/Brevo ficam para homologação integrada na etapa 12 por D-77/D-78.
## 18/09/2026 — Etapa 03 iniciada: contrato Domínio Fedrizzi (V-010)

- A leitura autorizada do conector existente passou: 4 consultas fixas, 5 objetos, 13.875 linhas e nenhuma coluna obrigatória ausente. A descoberta de 500 objetos/4.733 colunas só confirmou metadados já registrados; não imprimiu ou gravou dados Domínio.
- D-80 fixa o serviço nativo CICA como pacote único. O Python fica somente para diagnóstico/migração até a sincronização nativa v2 estar homologada.
- Implementada a primeira projeção nativa: empresas Domínio em páginas de 500 via API v2 autenticada. O teste do agente passou e o serviço .NET compilou em Release sem aviso; uma página interrompida não desativa empresas ausentes.
- A estação Fedrizzi tem DSN `contabil` SQL Anywhere 17 e permissões/ferramentas para instalação. O MSI foi gerado, mas não instalado: não existe endpoint HTTPS CICA nem CA de agente configurada, portanto instalar agora criaria serviço falho. V-011 registra o procedimento e a dependência sem expor DSN ou dados.

## 18/09/2026 — Dependências de produção centralizadas na etapa 12 (D-87)

- O responsável definiu que toda atividade dependente do site em produção será feita somente na etapa 12.
- As etapas 01–11 permanecem responsáveis por implementação, configuração sem segredos, testes locais/isolados e documentação. Nenhum deploy, credencial externa de produção, chamada real, piloto ou custo foi acionado por este registro.

## 18/09/2026 — Etapa 04 iniciada: descoberta Siescon (V-029)

- A inspeção local de metadados encontrou drivers SQL Anywhere 16/17, mas nenhum DSN, driver ou instalação identificada como Siescon. Não foram lidos dados nem expostos segredos.
- O próximo passo exige o contrato técnico de Q-33 por canal seguro: versão do Siescon, mecanismo de leitura autorizado, acesso de homologação e layout de exportação/importação. Sem isso, um adaptador seria especulativo e não será implementado.

## 18/09/2026 — Etapa 04: base de exportação neutra (V-030)

- `AccountingExport` agora registra destino e versão do adaptador. O layout Domínio continua preservado; Siescon é recusado explicitamente até a revisão de contrato/layout, sem gerar arquivo ou escrever no sistema de origem.
- A fonte Siescon foi modelada e a matriz de capacidades foi registrada. A suíte focada aprovou 36 testes; migrações e Ruff passaram. Não houve conexão ou exportação Siescon.
