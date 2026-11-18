# CONTAD — guia de conciliação e testes da cliente

Atualizado em **18/11/2026**. A **release 100** continua publicada; a ampliação da carteira e o recibo de importação estão em validação para a próxima versão.

Comece pela conferência da **SURIA, empresa 212 no Domínio, conta contábil 8,
competência setembro/2026**. O extrato e o Razão já estão disponíveis. Reserve
**30–45 minutos** para a sessão inicial; é uma estimativa de uso do roteiro,
não um prazo para concluir a revisão de todos os movimentos.

## Roteiro para hoje

| Etapa | Tempo sugerido | Resultado a observar |
|---|---|---|
| Abrir o piloto | 5 min | Escritório, empresa, conta e competência corretos |
| Comparar e consultar evidências | 10–15 min | Entender uma relação e manter sem confirmação o que não tiver prova |
| Consultar histórico | 5 min | Identificar decisão, autoria e evidência preservadas |
| Abrir e baixar relatório | 5–10 min | Guardar a conferência e explicar o que representam seus números |
| Registrar resultados | 5–10 min | Distinguir funcionamento, dado ausente e decisão pendente |

### 1. Abrir a conta e o mês corretos

1. Entre com sua conta pessoal na [carteira de conciliação](https://cicacontabil.com.br/app/conciliacao/carteira/).
   Confira o escritório **CONTAD**. Pelo menu, o caminho é **Contábil →
   Conciliação bancária → Conciliação por empresa**.
2. Em **Competência**, escolha **setembro/2026**. Em **Empresa ou código Domínio**,
   procure **SURIA** ou **212** e use **Aplicar filtros**.
3. Confira a empresa e a conta correspondente à **conta contábil 8**; o nome
   da conta financeira aparece na carteira. Abra **Abrir conferência**.
4. Confira o período **01/09/2026 a 30/09/2026** e o resumo da página.

A referência observada em 17/11 às 16:52 era: **163 movimentos do extrato,
163 registros do Razão, 1 movimento conferido e 162 com valor a confirmar**.
Decisões legítimas posteriores alteram as últimas contagens; registre o estado
que encontrar. Se empresa, conta, mês ou fontes divergirem, confira os filtros
antes de prosseguir.

Há **dois grupos com mais de uma correspondência possível**. A diferença entre
as variações é zero, mas os saldos e a cobertura integral ainda não estão
confirmados. Abra **Cobertura dos arquivos e saldos** para ler os avisos.
Saldo não informado não é saldo zero; o resumo não encerra a competência.

O teste de hoje usa os dados existentes. Não é necessário enviar outro extrato,
acionar **Buscar Razão**, solicitar títulos ou concluir as 43 fichas para começar.

### 2. Comparar com evidência

1. Mantenha **Conferência: A conferir** e use **Aplicar filtros**. Se precisar,
   localize um movimento em **Histórico do extrato**.
2. Abra **Comparar e revisar**. Confira data, entrada/saída, valor e histórico
   contra os documentos ou registros independentes disponíveis.
3. Em **Consultar evidências dos registros desta página**, examine os documentos
   e a origem. A seção **Evidência de origem** identifica o arquivo e a localização.
4. Quando a relação estiver comprovada, a própria cliente escolhe o
   **Lançamento independente**, confere o **Valor alocado** e preenche
   **Evidência da relação** com uma referência que permita reencontrar a prova,
   como documento e número. Só então usa **Confirmar conciliação**.
5. Sem evidência suficiente, volte por **Voltar à conferência** e deixe o item
   pendente. Isso é um resultado válido do teste.

Uma sugestão única também exige conferência. Nos grupos ambíguos, compare as
alternativas e procure identificação adicional; não escolha somente por data
ou valor. Não confirme um movimento apenas para exercitar o botão. O saldo
**Disponível** limita a alocação aos valores ainda livres nos dois registros.

### 3. Consultar o histórico

1. Volte à conferência, escolha **Conferidos** e use **Aplicar filtros**.
2. Abra **Ver evidências**. Confira **Alocações da conciliação** e
   **Histórico das decisões**, incluindo responsável, data e prova registrada.
3. Use **Consultar evidência preservada**, quando disponível, para examinar a
   referência da decisão.

**Desfazer** corrige uma relação efetivamente errada. O histórico deve permanecer
visível após a correção. Para conhecer o fluxo sem erro real a corrigir, consulte
as decisões existentes; exercícios de alteração devem usar dados de treinamento.
Se a evidência de uma decisão antiga for genérica, registre a necessidade de
complementá-la e mantenha a autoria da revisão humana.

### 4. Abrir e guardar o relatório

1. Na conferência, use **Ver relatório**. Confira empresa, conta, período,
   horário, quantidades, pendências e avisos de saldo/cobertura.
2. Use **Imprimir ou salvar PDF** para abrir a impressão do navegador e salvar
   uma cópia na pasta privada do escritório. Esse PDF é a impressão da página.
3. Use **Baixar CSV técnico** e abra o arquivo salvo. Confira sua identificação
   e explique a diferença entre as duas fontes usando a orientação abaixo.
4. Após uma decisão nova ou correção, abra/baixe novamente para guardar o estado
   atualizado. Registre a localização privada do relatório usado no teste.

O relatório abrange **todas as páginas do período selecionado**. A busca de
histórico e os filtros **A conferir/Conferidos** não reduzem seu conteúdo.
Extrato e Razão são os dois lados da comparação: não some os
163 de cada lado como 326 movimentos distintos.

O CSV técnico usa `bank` para extrato e `ledger` para Razão; `inflow` indica
entrada e `outflow`, saída. Valores, alocações e pendências das linhas são
magnitudes positivas em **centavos**: `12345` corresponde a **R$ 123,45**.
A direção informa o sinal. Os resumos líquidos podem ser negativos. O arquivo
não contém histórico/documento nas linhas; consulte o relatório legível para
esses detalhes. CSV, página e PDF são conferência, sem importação contábil
homologada no Domínio.

### 5. Registrar o que aconteceu

Preencha um registro privado da sessão. Não antecipe aprovação ou assinatura.

| Campo | O que registrar |
|---|---|
| Contexto | Data/hora, pessoa que executou, release 100, empresa, conta e competência |
| Cenário | Acesso, comparação, ambiguidade, histórico, relatório ou revisão complementar |
| Resultado | Funcionou, pendência de dados, decisão necessária, falha observada ou não executado |
| Evidência | Referência privada da tela/documento/relatório; estado anterior e posterior quando houve decisão real |
| Próximo passo | Quem deve conferir e qual informação ou correção falta |

Classifique cada dificuldade antes de tratá-la:

- **Dado ausente:** falta extrato, saldo, documento ou vínculo comprovado.
  Registre qual fonte falta; não complete com estimativa.
- **Decisão contábil:** a fonte existe, mas é necessário interpretar uma baixa,
  escolher uma correspondência ou aprovar uma regra. A contadora registra a prova.
- **Possível defeito:** a tela falha, perde um contexto válido ou apresenta
  resultado incompatível com a fonte. Registre passos, horário, esperado,
  observado e mensagem exata para o responsável pela implantação.

A sessão estará registrada quando os percursos executados e as pendências
estiverem descritos. Teste realizado, treinamento autônomo e aceite integral
são resultados diferentes.

## Revisões complementares com as fontes existentes

Estas revisões não são pré-requisito para usar o piloto. Faça apenas o que tiver
fonte suficiente e registre as demais pendências para continuidade.

### Fichas e vínculos de contas

Há **43 fichas de 11 empresas**, com nomes e classificações consultados no Domínio.
Elas não são 43 contas operacionais. Na verificação de 17/11, somente o piloto
tinha conta operacional; as demais 145 empresas ainda não estavam prontas para
a conferência bancária completa.

1. Na carteira, abra **Vínculos de contas**, localize a empresa e abra o caso.
2. Confira conta contábil, empresa do plano e **Dados consultados no Domínio**.
   Os fatos já recebidos e o nome inicial estão apresentados; revise-os com a fonte.
3. Em **Validar o vínculo bancário**, complete somente dados comprovados de banco,
   agência/conta, direção no Razão e referência da evidência. A consulta cadastral
   não trouxe referências bancárias; o nome da conta não prova a associação.
4. Marque as três verificações apenas depois de comprová-las e use **Vincular conta**.
   Se faltar evidência, deixe a ficha pendente. **Vínculo revisado** não significa
   que os movimentos do mês foram conciliados.
5. **Não utilizar esta conta** exige motivo real; **Reconsiderar decisão** permite
   reabrir uma decisão anterior com justificativa. **Corrigir vínculo** preserva
   as revisões anteriores e os vínculos já utilizados ficam protegidos.

Para contas manuais, **Corrigir conta** exige **Motivo da correção** e
**Salvar correção**. O **Histórico de correções** preserva a alteração. A identidade
bancária/contábil já usada em fontes, lançamentos ou coletas não pode ser trocada
silenciosamente. Contas originadas de um vínculo têm identidade preservada;
a tela controla novos usos e exige cadastro completo para ativar.

### Títulos e baixas

1. Abra **Títulos e baixas**, selecione SURIA e a conta em **Empresa e conta**,
   e use **Consultar**. Na página da conta, confira ou ajuste o período e consulte
   novamente. Depois, abra **Conferir fontes recebidas** para consultar a fonte
   já disponível, inclusive quando não há títulos revisados.
2. Abra a fonte e examine parcelas e componentes originais. Escolher uma conta
   para revisão não associa automaticamente pagamentos ao extrato.
3. Quando houver documentação suficiente, revise uma parcela: natureza a pagar
   ou receber, campo do principal e componentes dos eventos. Use **Conferir prévia**
   e, somente após validar o resultado e a confirmação exibida, **Salvar parcela revisada**.
   As demais parcelas e as versões anteriores são preservadas.
4. Em **Vincular baixas ao extrato**, selecione baixa, movimento e valor comprovados.
   **Adicionar vínculo** permite parciais/agrupamentos; use **Revisar vínculos**
   para conferir capacidade, datas e evidência antes de confirmar a quantidade exibida.
5. Consulte **Vínculos e histórico**. **Desfazer vínculo** exige motivo.
   **Ver relatório**, **Imprimir ou salvar PDF** e **Baixar CSV** mostram o resultado.

Vencimento não comprova pagamento. Juros, descontos, retenções, multas e estornos
precisam de interpretação e prova; ausência na fonte não equivale automaticamente
a zero, parcela em aberto ou quitação. Cobertura parcial mantém saldo desconhecido.
O sistema registra a revisão na CICA, sem dar baixa ou escriturar no Domínio.
As conferências já adiadas não são exigidas nesta sessão.

O CSV de títulos apresenta valores **em reais**, componentes e evidências; é
diferente do CSV técnico do extrato×Razão, em centavos. O relatório de títulos
inclui as parcelas da fotografia, baixas/movimentos do período e histórico dos
vínculos da conta. Na referência de 17/11 ainda não havia títulos normalizados
nem alocações de títulos: uma consulta de fonte bruta não é revisão financeira.

### Sugestões DE-PARA

Em **Conciliação bancária**, abra **Revisar DE-PARA** e **Conferir lote**.
Existem duas sugestões reais retidas. Confira contas de débito/crédito e histórico
contra o plano e selecione apenas sugestões aprovadas pela contadora.
**Preparar rascunhos selecionados** não ativa regras. **Conferir ou cadastrar contas**
trata contas lançáveis ausentes; **Revisar e ativar regras** é uma decisão humana
posterior, com revalidação do plano. Se faltar prova ou conta aprovada, registre
a pendência. A tela reaproveita sugestões existentes e não faz nova chamada de IA.

## Referência para outras contas e competências

Os percursos abaixo explicam funções já publicadas. A sessão inicial de hoje
usa fontes existentes e não solicita novas coletas ao Domínio. A carteira
completa ainda depende dos vínculos e da preparação técnica em andamento.

### Importar um extrato e receber o Razão

Em **Extrato e Razão**, selecione empresa, conta e competência; use
**Continuar** ou **Atualizar seleção**, conforme a tela. Extratos aceitos:
**OFX, QFX, CSV, XLSX e PDF, até 25 MiB**, dentro dos layouts suportados.
CSV/XLSX podem exigir mapeamento; PDF precisa ter conteúdo extraível e revisável.
Arquivo recusado não significa ausência de movimento. Conserve o original e
confira a importação existente antes de reenviar; PDF e OFX do mesmo extrato
não constituem fatos novos.

**Enviar extrato** processa o arquivo selecionado. **Buscar Razão** registra
uma solicitação distinta ao agente, para o vínculo e mês selecionados. O
**Vínculo com o Domínio** apresenta empresa do plano, filial, conta contábil e
lado da entrada bancária; **Revisar vínculo/Salvar vínculo** dependem de evidência.
Não são exigidas contagens técnicas digitadas pela cliente.

**Solicitações** e **Extratos recebidos** possuem histórico paginado.
**Na fila** é pedido salvo; **Razão recebido** permite **Abrir conferência**.
**Sem lançamentos neste período** descreve somente aquele recorte.
**Revisão necessária** exige tratar a causa informada. **Atualizar situação**
apenas atualiza o acompanhamento; **Tentar novamente** retoma uma solicitação
quando disponível, após a causa resolvida. Uma interrupção não justifica pedidos
repetidos sem conferir o histórico.

O agente 1.0.13 já foi instalado e uma nova coleta real do piloto foi comprovada
em 17/11. Não há reinstalação ou pareamento a fazer para este teste. Uma coleta
futura precisa do computador do Domínio e agente disponíveis, vínculo válido e
escopo definido. Esta prova do piloto não comprova toda empresa/competência.

### Razão independente por arquivo

A carteira oferece **Importar Razão**. Confira empresa, conta, origem
**Registros contábeis** e finalidade **Razão independente — CSV de partidas completas**.
Use **Baixar modelo do Razão** e substitua exemplos fictícios por dados reais,
com todas as partidas de cada lançamento e débitos/créditos equilibrados.
**Abrir plano de contas** permite conferir os códigos da empresa.

O lote é validado antes de gravar. Contas ausentes, partidas incompletas ou
valores desequilibrados exigem corrigir a fonte. **Arquivos gerais** em PDF,
XLSX ou CSV genérico não substituem o Razão independente. Um PDF bancário também
não é Razão. [Formato e exemplo de partidas](../conciliacao-razao-normalizado.md).

Para empresa sem conta e sem candidata, **Conferir configuração** leva ao
**Plano de contas** e às **Contas financeiras**. Cadastre somente conta real
completa e comprovada. O cadastro manual não deve substituir a descoberta
automática ainda em preparação nem criar conta provisória para contornar ausência.

### Solicitações de títulos e baixas

**Buscar títulos e baixas** permite selecionar empresas e competência inicial
e final, inclusive empresas ainda sem conta bancária. **Conferir lote** mostra
empresas, intervalo e quantidade; o botão seguinte exibe **Solicitar N buscas**
(ou **Solicitar 1 busca**). Cada empresa/mês representa uma solicitação.
O limite técnico é 2.000 buscas por lote, sem promessa de prazo para toda a carteira.

Em **Buscas e fontes recebidas**, filtre empresa/competência, use **Atualizar buscas**
e consulte as páginas. **Solicitação entregue ao agente** não significa fonte
recebida. **Abrir fonte** permite consultar os registros; **Abrir revisão nesta conta**
exige selecionar uma conta da mesma empresa para continuar a revisão financeira.
**Tentar novamente** deve ocorrer somente depois de resolver o motivo indicado.
Fontes anteriores e decisões permanecem preservadas.

O código e o agente são compatíveis com esse fluxo ampliado, mas em 17/11 às
16:51 ainda não havia solicitação de títulos por empresa concluída em produção.
A fonte anterior permanece disponível; não confundir essa captura com prova de
nova recepção do fluxo ampliado. Este roteiro não pede uma coleta nova hoje.

## Acesso, problemas e continuidade

Cada pessoa usa sua própria conta e as empresas/módulos autorizados. Perfis de
consulta não confirmam nem importam. Se uma ação esperada estiver indisponível,
registre a tela e peça ao responsável que confira o acesso; não use outra conta
ou empresa para contornar a restrição.

Ao reportar problema, informe cenário, data/hora, empresa/conta/mês, passos,
mensagem exata e resultado esperado/observado. Guarde relatórios, originais e
capturas com dados financeiros no local privado do escritório. Não inclua senhas,
chaves ou credenciais. Encaminhe o registro ao responsável pela implantação pelo
canal habitual; este guia não envia mensagem nem registra aceite automaticamente.

## Referências técnicas e critérios de conclusão

Esta seção apoia o responsável pela implantação e fica fora da sessão inicial.

- A release 100 e o piloto foram reconferidos em V-413. A descoberta ampliada ainda
  não foi importada/publicada; o recibo de extração não substitui o arquivo real.
  O acesso ao SVAPL02 está indisponível hoje conforme D-373; não pedir novamente
  execução ou transferência dependente desse acesso.
- Q-28/PC-19: vínculos, fontes, competências e cobertura reais; Q-46: interpretação
  de títulos, componentes, relações bancárias e regras. Q-47/C01/C02 permanecem
  adiados e não são parte do roteiro de hoje.
- D-73: 200 fatos distintos por fluxo aplicável e precisão mínima de 95% onde
  aplicável; zero duplicidade/associação errada/vazamento; retomada sem perda em
  até 15 minutos; restauração em até quatro horas; processamento por empresa em
  até cinco minutos, ressalvada dependência externa documentada. RPO e provas
  operacionais permanecem próprios. Backup está fora da prioridade inicial.
- Os 163 fatos do piloto só compõem a amostra revisada com prova humana. Mesmo
  revisados integralmente, faltam ao menos 37 fatos distintos. Releituras, PDFs,
  partidas ou fontes diferentes do mesmo movimento não aumentam a amostra.
- O treinamento inicial não precisa ser refeito como inexistente. Seus complementos
  são referência auditável, download autônomo e compreensão do relatório pela cliente.
  O aceite integral depende da comprovação dos critérios e da aprovação humana.
- CSV técnico: UTF-8 com BOM, separador `;`, colunas
  `fonte;referência;data;direção;valor_centavos;alocado_centavos;pendente_centavos`.
  Os resumos líquidos são assinados; a direção fornece o sinal das linhas.
- A CLI administrativa `reconcile_titles` e o contrato `titles-normalized-v1`
  permanecem recursos técnicos. O percurso publicado pela tela substitui a edição
  manual de JSON para a cliente. Importações técnicas exigem escopo, autoria e
  evidência próprios; não usar identidade da cliente nem confirmar por inferência.

Documentação relacionada: [parecer e pendências vigentes](../planejamento/pendencias-conclusao-2026-11-02.md),
[fontes de títulos e baixas](../conciliacao-fontes-titulos.md),
[formato do Razão](../conciliacao-razao-normalizado.md) e [validações](../../VALIDACOES.md).

## Conferir o resultado da importação no Domínio

Este percurso ficará disponível na nova versão, após a validação do importador
utilizado pela CONTAD. A geração ou o download de um arquivo não comprovam sua
importação. Use somente um lote novo, aprovado especificamente para a base real,
com arquivo, hash, efeitos esperados e recuperação previamente conferidos. O
Razão SURIA/setembro já escriturado não deve entrar nesse lote.

1. Em **Arquivos exportados**, abra **Conferir importação**. Confira empresa,
   período e identificação do arquivo. Os detalhes mostram o destino, as versões
   e o SHA-256 para comparar com o arquivo efetivamente utilizado.
2. Localize os lançamentos no Domínio e compare data, histórico, valores e contas.
   Cada página contém até 25 lançamentos. Registre **Aceito**, **Rejeitado** ou
   **Incerto** conforme a evidência observada.
3. Para um item aceito, informe sua identificação no Domínio e a evidência da
   conferência. Para um rejeitado, identifique o retorno que prova a rejeição.
   Mantenha como incerto tudo que ainda não puder confirmar.
4. Identifique o retorno ou relatório consultado, confira a versão do importador
   e marque a declaração somente depois de realizar a conferência. Use
   **Registrar resultado desta página**. As outras páginas preservam o último
   resultado; itens ainda não conferidos permanecem incertos.
5. Consulte os totais e o histórico de recibos. A importação só aparece como
   integralmente conferida quando todos os itens estiverem aceitos. Itens já
   aceitos e suas evidências permanecem preservados.

A evidência digitada é uma declaração de conferência, identificada dessa forma
no recibo. Se aparecer conflito, reabra o resultado atual antes de continuar.
Em resultado incerto, consulte primeiro o ERP; não repita a importação por
suposição. Em rejeição parcial, trate somente os itens comprovadamente não
importados. O download do mesmo arquivo não autoriza reenviar itens já aceitos.

## Situação da ampliação em 18/11

Foram recebidas e verificadas fontes de títulos da empresa 30 em setembro e da
empresa 25 em setembro e outubro, sem exigir conta bancária. Fonte recebida não
comprova quitação, saldo completo ou vínculo bancário. Novembro é uma competência
em andamento. A matriz das 146 empresas distingue cadastro, fontes disponíveis,
contas e pendências; o cadastro, isoladamente, não comprova operação validada.

O confronto técnico de C01/retenções e C02/juros foi delegado ao executor pelo
responsável. Atribua cada registro ao autor que efetivamente realizou a revisão;
aceite da cliente e aprovação do lote real têm registros próprios.
