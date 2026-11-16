# CONTAD — guia de conciliação e roteiro de treinamento

## Buscar títulos e baixas das empresas — D-369, 16/11/2026

Percurso em validação para publicação. A atualização única **1.0.12** do agente
reúne as buscas de **Razão e títulos/baixas**. Ela substitui a atualização1.0.11
ainda pendente: não são duas instalações. A instalação no SVAPL02 e a primeira
coleta real dependem do acesso técnico ao servidor, indisponível hoje.

1. Abra **Contábil → Conciliação bancária → Buscar títulos e baixas**. Localize
   e selecione uma ou várias empresas. Empresas sem conta bancária também podem
   ter suas fontes buscadas; o código da empresa no Domínio deve estar correto.
2. Informe **Competência inicial** e **Competência final**. O intervalo inclui
   os dois meses e aceita períodos históricos, anteriores ao piloto.
3. Use **Conferir lote**. Confira todas as empresas, o intervalo e o número de
   buscas antes de **Solicitar buscas**. Cada empresa e mês gera uma busca.
   As146empresas por12meses cabem em um lote; acima de2.000buscas, divida a seleção.
4. Acompanhe **Buscas e fontes recebidas**. Filtre por empresa e competência;
   navegue pelas páginas para consultar o histórico. O pedido salvo pode ficar
   na fila enquanto o agente aguarda atualização ou conexão. **Solicitação
   entregue ao agente** ainda não significa que a fonte chegou.
5. Quando a fonte chegar, use **Abrir fonte**. Confira as parcelas e os registros
   originais. Isso funciona mesmo sem conta cadastrada. Uma resposta sem
   registros vale somente para a competência solicitada e não comprova saldo zero.
6. Para continuar a revisão financeira, escolha explicitamente uma conta da
   mesma empresa e use **Abrir revisão nesta conta**. Confira cada parcela,
   natureza, principal e componentes da baixa antes de salvar. Depois, em
   **Títulos e baixas**, vincule as baixas ao extrato e obtenha o relatório.

**Revisão necessária** conserva a busca anterior. Corrija o motivo indicado
antes de **Tentar novamente**. Para atualizar uma competência já recebida,
prepare uma nova solicitação. A fonte anterior e as decisões são preservadas.

A fonte mensal não comprova saldo completo, quitação ou conta bancária.
Selecionar uma conta não vincula baixas automaticamente. Uma fonte histórica
continua consultável mesmo quando a fotografia financeira mais recente impede
substituí-la por uma mais antiga. Nesse caso, consulte a fonte e mantenha a
fotografia vigente; a mensagem de revisão indica o que precisa ser conferido.

## Enviar extrato e buscar o Razão — D-368, 16/11/2026

Tela publicada na release97. Para buscar diretamente no Domínio, falta atualizar
o agente existente para1.0.12 no SVAPL02 e comprovar uma coleta real. O responsável
não tem acesso ao servidor hoje; as fontes já carregadas continuam disponíveis.

1. Abra **Contábil → Conciliação bancária → Extrato e Razão**. Escolha a
   empresa, a conta e a competência mensal; confira o período apresentado.
2. Escolha um extrato novo ou um arquivo já recebido. São aceitos
   **OFX, QFX, CSV, XLSX e PDF, até25MiB**. CSV/XLSX podem pedir mapeamento de
   colunas; PDF depende de conteúdo que possa ser extraído e revisado.
   Arquivo ilegível ou formato não aceito precisa ser obtido novamente no banco.
3. Quando solicitado, confira **Vínculo com o Domínio**: empresa do plano,
   filial, conta contábil e lado da entrada bancária. Registre a referência
   usada na conferência e salve. Essa revisão é feita quando o vínculo ainda
   não está comprovado ou mudou; não é necessário informar contagens técnicas.
4. Use **Buscar Razão**. O pedido fica registrado e mostra quando foi entregue
   ao agente e quando os dados chegaram. É possível usar **Enviar extrato**
   separadamente; um extrato aceito permanece disponível se a coleta falhar.
5. Quando aparecer **Razão recebido**, abra **Abrir conferência**. Confira os
   movimentos, registre evidência real para cada decisão e gere o relatório.

**Na fila** significa pedido salvo, ainda sem resultado. **Sem lançamentos
neste período** descreve apenas a resposta daquele vínculo e competência;
não encerra o mês. **Revisão necessária** exige conferir vínculo/fonte no
Domínio. Se a origem mudou, o CICA preserva o histórico e informa a pendência.
Use **Atualizar situação** ou a retomada indicada pela tela após resolver o motivo.

Para atualizar dados do mesmo mês, faça uma nova solicitação. Reenviar o mesmo
pedido não duplica importações; movimentos anteriores confirmados são
preservados. O computador do Domínio deve estar ligado e com o agente conectado.
A atualização pontual do agente conserva o acesso existente; as solicitações
seguintes são feitas pelo site.


## Cadastrar, corrigir e receber o Razão — atualização D-366, 16/11/2026

Atualização disponível no CICA, release95, com publicação conferida em V-405.
Os dados de cada empresa e a conferência da cliente continuam necessários.

Para uma empresa **Sem conta cadastrada**, abra **Conferir configuração**.
Cadastre a conta contábil real em **Plano de contas**, ativa e apta a receber
lançamentos. Depois, em **Contas financeiras**, informe nome, código do banco,
agência/conta e vínculo contábil. Uma conta ativa precisa desses dados completos.
As contas sem candidata também usam esse caminho, com os dados comprovados
pela cliente. Ao voltar à importação, confira a empresa selecionada.

Para corrigir uma conta manual, abra **Corrigir conta** na configuração.
Confira os campos, informe o **Motivo da correção** e escolha **Salvar correção**.
O **Histórico de correções** conserva os dados anteriores, responsável, data
e motivo. Banco, agência/conta e vínculo contábil ficam protegidos quando há
fontes, lançamentos ou coletas associados; nessa situação, o formulário permite
corrigir o nome e controlar novos usos. Se a página informar que outra pessoa
alterou a conta, reabra e confira a versão atual antes de salvar.

Para uma conta originada de **Vínculos de contas**, **Corrigir conta** permite
ativar ou desativar novos usos com motivo e histórico. Nome, banco, agência/conta
e vínculo contábil ficam somente para leitura nessa tela; ativar exige cadastro
completo. A evidência e a revisão do vínculo são preservadas.

Os dados do vínculo são corrigidos no próprio caso.
Use **Corrigir vínculo**, registre motivo e nova evidência e confira novamente
as três verificações. Se já houver fontes, lançamentos ou coletas associados,
o vínculo usado é preservado e exige análise do responsável. Para um caso
marcado **Não utilizar**, use **Reconsiderar decisão** e informe o motivo;
**Reabrir para revisão** devolve o caso às pendências. As revisões anteriores
continuam disponíveis, sem apagar a decisão original.

Como alternativa à busca direta, use o envio de Razão em CSV na carteira. Confira
empresa, conta, origem **Registros contábeis** e finalidade **Razão independente
— CSV de partidas completas**. Use **Baixar modelo do Razão**, substitua os
exemplos fictícios pelos dados reais e inclua todas as partidas de cada
lançamento, com débitos e créditos equilibrados. **Abrir plano de contas**
leva à configuração da empresa selecionada.

O envio confere o formato e as contas antes de guardar o lote. Se indicar
contas ausentes ou indisponíveis, confira os códigos no plano; se indicar
partidas incompletas ou desequilíbrio, revise a fonte original. Depois,
selecione novamente o arquivo corrigido. PDF, XLSX e CSV genérico enviados como
**Arquivos gerais** não preenchem a pendência de Razão independente.
Consulte o [contrato e exemplo do CSV](../conciliacao-razao-normalizado.md).

Concluído o processamento, volte à carteira da competência e abra a
conferência. Cadastro completo e fontes recebidas permitem iniciar o trabalho;
não significam que os movimentos foram conciliados ou que o mês foi encerrado.

## Validar as contas das demais empresas — D-365/V-404

Pré-cadastros publicados na release94, conforme V-404.
Os casos C01–C43 reaproveitam a ficha existente. Empresa, plano e código da
conta já vêm da origem; os dados bancários precisam da sua conferência.

1. Na carteira, abra **Vínculos de contas** ou filtre **Vínculo de conta pendente**
   e escolha **Revisar vínculos** na empresa. Busque por empresa, caso ou código.
2. Abra o caso e confira empresa, conta contábil e empresa do plano. Consulte
   o extrato e o plano reais; informe nome da conta, código do banco, agência
   e conta, lado do Razão para entrada bancária e referência da evidência.
3. Confirme as três verificações somente depois de comprová-las e escolha
   **Vincular conta**. A tela registra responsável, data e prova; cadastros
   incompatíveis precisam de revisão e não são sobrescritos.
4. Se a candidata não deve ser usada, abra **Não utilizar esta conta**, descreva
   o motivo e registre. A origem e a decisão permanecem disponíveis para consulta.
5. Volte à carteira, escolha a competência e siga a pendência de **Importar
   extrato** ou **Buscar Razão**. O vínculo cadastrado não traz movimentos
   de outros meses. Confira a conta e o período antes de enviar cada fonte.

A situação **Vínculo revisado** identifica o cadastro conferido; não significa
que os movimentos do mês já foram conciliados. Se faltarem dados para provar
a associação, mantenha **Vínculo pendente**. Para empresas sem candidata,
use **Conferir configuração** após identificar as contas nas fontes reais.

## Carteira por empresa e relatório — atualização D-364, 16/11/2026

**Carteira e relatório publicados na release93, conforme V-403.**
O percurso do piloto continua disponível; as demais empresas precisam de
contas vinculadas e fontes do período para iniciar a conferência.

1. Em **Contábil → Conciliação bancária**, abra **Conciliação por empresa**.
   Confira o escritório e escolha a **Competência**. Use empresa/código e
   **Situação** para localizar o trabalho; a carteira mostra 25 empresas por
   página. **Ver empresa** permite escolher uma conta daquela empresa.
2. Confira empresa, conta e os arquivos recebidos. **Sem conta cadastrada**,
   **Sem extrato no mês** e **Sem Razão no mês** indicam pendências diferentes.
   Ausência de dados não significa empresa dispensada nem mês sem movimento.
   **Extrato e Razão recebidos** significa disponibilidade para conferência,
   não conciliação concluída. Arquivo em processamento/revisão exige o próximo
   passo indicado; não confirme valores para contornar uma pendência.
3. Abra a conferência da conta. A competência escolhida acompanha a lista,
   o detalhe do movimento, **Voltar à conferência** e o relatório. Confira o
   período no cabeçalho antes de decidir. Um filtro inválido mostra erro;
   corrija-o para consultar o recorte pretendido.
4. Use **Comparar e revisar** apenas quando houver evidência da relação.
   Confira data, histórico, documento e valor e registre uma referência que
   permita reencontrar a prova. Se faltar prova, mantenha o item pendente.
   Consultar a carteira ou abrir um relatório não confirma nenhum movimento.
5. Use **Ver relatório** para ler extrato e Razão com valores em reais,
   alocações, pendências e referências. Confira empresa, conta, competência,
   horário de geração e avisos. **Imprimir ou salvar PDF** abre a impressão
   do navegador; guarde o resultado na pasta privada do escritório.
6. **Baixar CSV técnico** mantém o arquivo compatível com a versão anterior:
   `bank` é extrato, `ledger` é Razão e `12345` centavos significa R$ 123,45.
   Não some os dois lados. Relatório e CSV abrangem todas as páginas do período;
   busca de histórico e situação A conferir/Conferidos não reduzem a saída.
   Depois de confirmar ou desfazer, gere novamente para registrar o estado atual.

**Quando faltarem dados:** use o próximo passo da empresa/conta para abrir
o cadastro ou a importação existentes. O formulário pode trazer empresa,
conta e origem preenchidas; confira tudo antes de escolher/enviar o original.
Abrir esse formulário não importa arquivo. Não crie conta provisória nem
escolha empresa parecida para contornar uma ausência. Peça ao responsável a
revisão do vínculo e da fonte correspondente.

Você vê apenas as empresas para as quais tem acesso ao módulo de conciliação.
Ter acesso à mesma empresa em outro módulo não libera seus arquivos aqui.
O perfil Auditor consulta, sem confirmar ou importar; o suporte mantém o
escopo autorizado. Se um acesso tiver sido removido, solicite revisão ao
responsável, sem compartilhar conta ou tentar outra empresa.

Saldo **não informado** não é zero. Diferença zero não comprova cobertura
integral ou revisão humana. Relatório/PDF/CSV são conferência, não arquivo
homologado de importação no Domínio. Q-47/C01/C02 permanecem adiados.
No treinamento, registrar participante, versão, empresa/conta/competência,
ação realmente executada, referência privada do relatório e pendências;
não antecipar resultado, assinatura, treinamento concluído ou aceite.

Atualizado em 13/11/2026, D-361/PC-19, para a **release 90**. O percurso do
piloto está disponível; o treinamento com a cliente e seu aceite ainda não
foram registrados. A primeira sessão usa o extrato e o Razão já recebidos,
sem esperar a revisão das 43 contas ou importar outro arquivo. A ampliação da
carteira e a homologação integral continuam com critérios próprios.

## Entrar e conferir o contexto

Acesse [CICA](https://cicacontabil.com.br) com sua conta pessoal. Depois do
login, confira o escritório CONTAD e abra **Contábil → Conciliação bancária**.
A conta pessoal da operadora já existe; não é necessário cadastrar outro escritório ou
pedir novo convite. Não compartilhe senha, arquivos ou dados de clientes pelo chat.

Antes de importar, confira empresa, conta financeira e período. Os dados devem
corresponder às fontes conferidas do escritório, recebidas pela integração ou
cadastradas manualmente com comprovação. Se a empresa/conta esperada não aparecer, ou
se houver mais de uma opção compatível, interrompa a importação e informe ao
responsável qual identificação está faltando. Não escolha uma empresa parecida
nem cadastre contas provisórias para contornar uma sincronização incompleta.

## Conferir os arquivos que já estão no sistema

Na página de conciliação, use **Abrir conferência** ou escolha o arquivo em
**Extratos para conferir**. A tela identifica empresa, conta, período e os
registros recebidos do extrato e do Razão. A ficha externa de novas contas não
é requisito para conferir uma conta que já possui fontes vinculadas.

1. Em **A conferir**, localize o histórico e abra **Comparar e revisar**.
2. Compare data, histórico, documento e valor com o registro independente.
   **Consultar evidências dos registros desta página** permite examinar a fonte.
   Data e valor iguais são sugestões; confira qual registro representa o fato.
3. Selecione o registro correto, confira **Valor alocado**, descreva a evidência
   da relação e use **Confirmar conciliação**. Uma relação parcial deixa o valor
   restante disponível; o sistema limita a alocação aos dois registros.
4. Use **Voltar à conferência**. O resumo e os filtros **A conferir** e
   **Conferidos** acompanham as confirmações. Para corrigir uma relação, abra
   **Ver evidências** e use **Desfazer**; o histórico da decisão é preservado.
5. Use **Baixar relatório de conferência** para guardar o resultado e as
   pendências. Leia **Cobertura dos arquivos e saldos**: diferença zero entre
   variações não comprova saldo inicial, cobertura integral ou revisão humana.

Esse caminho compara escrituração já recebida e não exige preencher débito e
crédito de um novo lançamento. Não produz importação no ERP. Novas empresas,
contas ou títulos dependem das fontes e dos vínculos próprios.

## Importar outro extrato

1. Abra **Nova importação** e selecione a empresa e a conta corretas.
2. Escolha a origem bancária e o arquivo original do período. Os formatos
   disponíveis são OFX, PDF, CSV e XLSX, conforme o layout suportado.
3. Confira a identificação da conta e o período apresentados. Para CSV/XLSX,
   confira o mapeamento de data, histórico e valores antes de processar. Se a
   estrutura mudou, revise o mapeamento; não reutilize um layout incompatível.
4. Acompanhe o processamento. Arquivo recusado ou erro de leitura exige
   correção do arquivo/layout ou suporte; não indica ausência de movimentos.
5. Confira a quantidade e os valores contra o original. Conserve os originais.

OFX e PDF do mesmo extrato representam os mesmos fatos. Enviar ambos não
duplica a amostra de conferência. Ao reenviar arquivo já processado, confira o
histórico e o resultado existente antes de tomar uma nova decisão.

Um PDF bancário não é o Razão. O relatório de uma única conta também pode não
conter todas as partidas do lançamento. Fontes contábeis incompletas permanecem
pendentes; nunca complete contrapartidas pelo nome do histórico.

## Revisar as diferenças

Abra o movimento e examine as fontes, datas, valores, conta, documentos e
evidências. Coincidência de data e valor é candidata à conferência. Duas opções
com o mesmo valor exigem identificação adicional; não confirme a primeira por
conveniência. Confira também os fatos sem correspondente em cada fonte.

Parcelas e baixas precisam demonstrar pagamento/recebimento efetivo. Vencimento
não comprova pagamento. Juros, descontos, multas, retenções e estornos precisam
estar representados nas fontes e seguir as regras revisadas do escritório.

Use a confirmação somente depois da conferência humana. Ignorar um item é uma
decisão registrada; só faça isso quando houver motivo operacional correto.
Se precisar corrigir uma decisão, use o fluxo de revisão e preserve a trilha.
Movimentos já conciliados ou vinculados a saída exportada exigem o tratamento
oferecido pelo sistema, evitando criar outra escrituração do mesmo fato.

## Relatório, saída e falhas

Use **Ver relatório** para ler e
**Imprimir ou salvar PDF** para guardar a conferência; **Baixar CSV técnico**
mantém a saída anterior. Confira empresa, conta, período, totais, pendências
e avisos. O período limita as duas saídas; busca, situação e página da tela
não limitam o relatório. Relatório ou prévia privada não comprovam importação no ERP.
A exportação Domínio segue bloqueada até validação do layout e autorização
operacional específica; não tente importar uma prévia como arquivo homologado.

O download da conferência gera `conferencia-banco-razao.csv`, separado por
ponto e vírgula. O arquivo contém os dois lados: `bank` identifica o extrato e
`ledger` identifica o Razão. Os campos `valor_centavos`, `alocado_centavos` e
`pendente_centavos` são valores inteiros em centavos: por exemplo, `12345`
significa R$ 123,45. Não some os dois lados como se fossem movimentos diferentes.
O cabeçalho registra período, data de geração, hash da fonte e avisos; saldos
não disponíveis aparecem como **não informado**. Guarde o CSV na pasta privada
do escritório, junto da referência da empresa e conta conferidas na tela.

O botão baixa o relatório do arquivo e período, incluindo todas as páginas.
Os filtros de histórico e **A conferir/Conferidos** da tela não reduzem o CSV.
Depois de confirmar ou desfazer, faça outro download para registrar o estado
atual; o CSV anterior permanece uma fotografia da geração anterior.

Se houver falha de comunicação ou interrupção, conserve o arquivo original e
a identificação da importação. Confira o estado e o histórico antes de reenviar.
Informe ao responsável o horário, empresa, etapa e mensagem exibida; nunca
envie senha do ERP, chave ou captura contendo credenciais. Não refaça o
pareamento nem reinstale o agente para resolver um item de conciliação.

## Teste acompanhado e registro do treinamento

O responsável acompanha a operadora na primeira sessão abaixo. A operadora
usa sua própria conta e executa as ações. O acompanhante observa, registra
dificuldades e explica os limites; não confirma em nome dela. Comece no arquivo
piloto já disponível. A ausência de novas contas não impede essa sessão.

1. Abra **Abrir conferência** e peça à operadora que identifique escritório,
   empresa, conta, arquivo e período. Registre as quantidades iniciais do extrato,
   do Razão e de movimentos conferidos, além do horário de início.
2. Escolha um movimento cuja relação possa ser comprovada nas fontes. Em
   **Comparar e revisar**, a operadora explica a correspondência, confere
   **Lançamento independente** e **Valor alocado**, preenche **Evidência da
   relação** e usa **Confirmar conciliação**. Sem evidência suficiente, mantenha
   o movimento pendente e registre o que falta.
3. Volte à conferência, escolha **Conferidos** e use **Aplicar filtros**. Abra
   **Ver evidências** e confira a alocação e o **Histórico das decisões**. A
   confirmação deve aparecer vinculada à operadora e à evidência registrada.
4. Examine um item ambíguo ou sem correspondente, se houver. A operadora deve
   explicar qual prova falta e mantê-lo pendente. Não é preciso fabricar uma
   decisão para completar o exercício.
5. Pratique correção em ambiente de ensaio com dados sintéticos: abra a relação,
   use **Desfazer**, confira a capacidade liberada e a decisão preservada, e
   refaça a relação correta com nova evidência. Na operação real, use esse
   caminho somente quando houver uma correção efetiva; não crie erro no piloto
   para treinar. Se a sessão não tiver esse exercício, registre-o como pendente.
6. Baixe **Baixar relatório de conferência**, abra o CSV e confira período,
   quantidades, alocações, valores pendentes e avisos. A operadora explica o que
   foi conferido, o que continua pendente e por que o relatório não é uma
   importação no Domínio. Registre horário final e o local privado da evidência.

Use uma cópia privada da [ficha de treinamento e aceite](contad-treinamento-registro.txt).
O modelo deixa resultados e assinaturas vazios e separa ensaio técnico,
treinamento acompanhado, primeira operação real e aceite da versão. Não grave
a ficha preenchida no Git nem neste guia público. Um exercício só fica
concluído quando a participante o executa e a evidência é registrada.

| Exercício | Resultado esperado | Estado desta entrega |
|---|---|---|
| Acesso e contexto | Identificar CONTAD, empresa, conta e período | A executar no treinamento |
| Conferência do piloto | Abrir extrato e Razão já recebidos | Disponível na release 90; execução humana pendente |
| Revisão simples | Confrontar fontes, confirmar e localizar a decisão | A executar acompanhado |
| Ambiguidade/falta | Manter pendência e localizar evidência adicional | A executar acompanhado |
| Correção | Desfazer e conferir histórico/capacidade; corrigir com evidência | Ensaiar em dados sintéticos; correção real somente se necessária |
| Relatório | Baixar CSV, conferir centavos, abrangência e pendências | A executar acompanhado |

Ampliação da carteira, nova importação, parcelas/baixas, recuperação de falha e
retorno ao ERP são sessões adicionais conforme suas fontes e autorizações.
Não são pré-requisitos para iniciar a conferência do piloto. Q-47, retenções e
juros continuam adiados; esta sessão não os executa nem os aprova.

Registrar data, participantes, versão do site/agente, recorte, referências das
evidências, dificuldades e nova execução necessária. O proprietário revisa a
amostra independente de 200 itens e os critérios D-73; os 163 eventos atuais
não bastam. Precisão, integridade, tempo, recuperação e importação no destino
devem ter medições reais. Treinamento realizado e aceite do módulo são registros
separados, dependentes da participação e aprovação humanas efetivas. A ficha
permite registrar uso assistido limitado ao piloto; isso não aprova a carteira
completa, os 200 fatos, a precisão de 95% ou a liberação integral do módulo.

## Provas para fechar a homologação

Use referências internas às evidências. Mantenha extratos, relatórios com
valores e arquivos de importação no ambiente autorizado do escritório.

| Critério | Evidência a conferir | Quem confere |
|---|---|---|
| Q-28, carteira e contas | Legenda oficial da situação M e exemplo em que a empresa usa plano compartilhado, com a empresa de origem visível no Domínio | Operador CONTAD e responsável técnico |
| Q-46, títulos e baixas | Título em aberto, baixa total, baixa parcial com saldo remanescente e estorno, quando aplicáveis ao fluxo. Em cada exemplo, vincular título, parcela, evento e movimento contábil ou bancário pelos identificadores da origem | Contadora e responsável técnico |
| Q-47, importação Domínio | Layout aceito pelo destino e resultado de uma importação de teste autorizada. Registrar o que entrou, erros e conferência das partidas no destino. Usar um caso que ainda não esteja escriturado | Operador do Domínio e contadora |
| D-73, amostra e precisão | Revisão de 200 fatos distintos pelo proprietário, com decisão registrada para cada item. Medir acertos sobre os casos classificados automaticamente, com mínimo de 95%, e verificar zero duplicidade, empresa incorreta ou vazamento | Proprietário e responsável técnico |
| D-73, tempo por empresa | Medir consultas e processamentos por empresa com limite de 5 minutos. Registrar a dependência externa quando ela impedir essa medição | Responsável técnico |
| D-73, retomada e restauração | Registrar início da interrupção, retomada sem perda em até 15 minutos e restauração isolada conferida em até 4 horas. Verificar banco, documentos privados e reprocessamento sem duplicação | Responsável técnico |

Os 163 movimentos do piloto só entram na amostra depois da revisão humana.
Se todos entrarem, ainda são necessários 37 fatos distintos. OFX, PDF, partidas
e reenvios referentes ao mesmo movimento não acrescentam itens à amostra.

Para Q-47, confirme no destino qual tela e qual leiaute serão usados. O Domínio
documenta a Importação Padrão com Separador e o Importador com Conjunto de
Dados. A prévia atual do CICA gera um CSV de dez colunas. A conferência
precisa fixar a versão e a ordem dos campos, a codificação e a regra para
partidas simples e compostas antes de ensaiar a importação.
[Importação com Separador](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=11916)
· [Importador com Conjunto de Dados](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=6055)


## Operação técnica dos títulos normalizados — D-344/V-367

O comando administrativo `reconcile_titles` permite guardar uma fonte
normalizada e revisar vínculos explícitos com movimentos bancários já
importados. A captura original do Domínio já foi recebida e comparada; sua
tradução em títulos, parcelas e baixas utilizáveis ainda depende da conferência
semântica de Q-46. Não há baixa, escrituração ou confirmação automática de
associação pela igualdade de data/valor.

A fonte usa o contrato `titles-normalized-v1`; na persistência,
`company_key` é o UUID CICA da empresa, e `account_reference` deve coincidir
com a conta selecionada. Parcela, baixa e estorno precisam ter chaves próprias.
Saldo ou cobertura desconhecidos continuam desconhecidos. Use arquivos
privados de até25MiB e lotes de até1000 vínculos, sem dados no Git.

Fluxo do operador técnico, substituindo os identificadores pelos do ambiente:

```sh
python manage.py reconcile_titles --organization ORG_UUID --account CONTA_UUID --actor USUARIO_UUID import --input /caminho/privado/titulos.json --evidence "Referência da conferência"
python manage.py reconcile_titles --organization ORG_UUID --account CONTA_UUID --actor USUARIO_UUID preview --snapshot SNAPSHOT_UUID --requests /caminho/privado/vinculos.json --start 2026-09-01 --end 2026-09-30 --output /caminho/privado/revisao-nova.json
python manage.py reconcile_titles --organization ORG_UUID --account CONTA_UUID --actor USUARIO_UUID confirm --plan /caminho/privado/revisao-nova.json --request-id UUID_DE_REENVIO --evidence "Referência do aceite dos vínculos"
python manage.py reconcile_titles --organization ORG_UUID --account CONTA_UUID --actor USUARIO_UUID undo --allocation VINCULO_UUID --reason "Motivo da revisão"
```

`vinculos.json` contém uma lista com `movement_key` (UUID do movimento CICA),
`title_key`, `installment_key`, `settlement_key` e `cash_cents` inteiro positivo.
Confira o arquivo de revisão antes de confirmar. Diferenças de data exigem
`--accept-date-differences`, sem definir tolerância fiscal. O mesmo UUID de
reenvio só repete o recibo do mesmo conteúdo; não deve ser reutilizado para
outra revisão. O desfazimento libera capacidade e preserva todas as decisões.

A confirmação recusa fotografia antiga, arquivo adulterado, saldo já alocado,
movimento duplicado em OFX sobreposto e acesso/perfil/carteira/contrato revogados.
O recibo preserva a revisão e o comando imprime somente identificadores,
contagens e hashes. O relatório de revisão é privado e criado sem sobrescrita.
Isso não conclui Q-46, importação ERP Q-47, treinamento ou aceite D-73.


## Títulos e baixas

Na Conciliação bancária, abra **Títulos e baixas**, escolha empresa/conta e
período. Em **Conferir fontes recebidas**, selecione a fonte e revise uma
parcela por vez. Confira os campos originais, escolha a natureza e o campo
que representa o principal e informe os componentes de cada evento em reais.
Registre a referência da conferência, abra a prévia e salve somente após
comprovar as decisões. As outras parcelas revisadas são preservadas.

Em **Vincular baixas ao extrato**, selecione a baixa, o movimento e o valor
desta relação. Use **Adicionar vínculo** para parciais/agrupamentos (até20 por
revisão). Confira a prévia, diferenças de datas e evidência antes de confirmar.
Valores já usados são descontados da capacidade. Uma fonte de cobertura
parcial conserva saldo não informado; a tela não registra baixa no Domínio.

**Vínculos e histórico** conserva decisões e permite **Desfazer vínculo** com
motivo. **Ver relatório** permite imprimir e **Baixar CSV** apresenta valores
em reais, componentes e evidências. O relatório de títulos traz as parcelas
da fotografia, as baixas/movimentos do período e o histórico completo dos
vínculos da conta. É diferente do CSV técnico da conferência extrato×Razão,
que continua com seu contrato de centavos e todas as páginas.

## Revisar as sugestões DE-PARA

Abra **Revisar DE-PARA** na conciliação ou configuração. Escolha um lote já
respondido, confira contas de débito/crédito e histórico e selecione as
sugestões aprovadas. **Preparar rascunhos selecionados** não ativa regras.
Depois use **Revisar e ativar regras**; o sistema confere novamente o plano.
Se faltam contas aprovadas, use **Conferir ou cadastrar contas**. Essa tela
não faz novas chamadas de IA e não libera consumo recorrente.
