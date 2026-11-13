# CONTAD — guia de conciliação e roteiro de treinamento

Preparado em 06/11/2026, D-323/PC-19. **Treinamento ainda não realizado.**
A carteira completa e as fontes contábeis estão em implantação. O piloto
SURIA não representa a entrega de todas as empresas. Este guia acompanha o
treinamento e não substitui a conferência contábil.

## Entrar e conferir o contexto

Acesse [CICA](https://cicacontabil.com.br) com sua conta pessoal. Depois do
login, confira o escritório CONTAD e abra **Contábil → Conciliação bancária**.
A conta da Grazi já existe; não é necessário cadastrar outro escritório ou
pedir novo convite. Não compartilhe senha, arquivos ou dados de clientes pelo chat.

Antes de importar, confira empresa, conta financeira e período. Os dados devem
vir da integração do escritório. Se a empresa/conta esperada não aparecer, ou
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

Use **Baixar conferência**, quando disponível no arquivo bancário processado,
para guardar o relatório do período. Confira o cabeçalho, conta, período,
totais e pendências. Relatório ou prévia privada não comprovam importação no ERP.
A exportação Domínio segue bloqueada até validação do layout e autorização
operacional específica; não tente importar uma prévia como arquivo homologado.

Se houver falha de comunicação ou interrupção, conserve o arquivo original e
a identificação da importação. Confira o estado e o histórico antes de reenviar.
Informe ao responsável o horário, empresa, etapa e mensagem exibida; nunca
envie senha do ERP, chave ou captura contendo credenciais. Não refaça o
pareamento nem reinstale o agente para resolver um item de conciliação.

## Teste acompanhado e registro do treinamento

O responsável acompanha Grazi ou o operador indicado na execução abaixo.
Cada resultado deve ser registrado com referência da tela/arquivo, sem dados
financeiros ou pessoais neste documento público. Não assinar antecipadamente.

| Exercício | Resultado esperado | Estado desta entrega |
|---|---|---|
| Acesso e contexto | Identificar CONTAD, empresa, conta e período | A executar no treinamento |
| Carteira integrada | Localizar empresas/contas sem cadastro manual por teste | Ampliação pendente de prova real |
| Importação | Enviar original, conferir identificação e quantidade | A executar acompanhado |
| Revisão simples | Confrontar fontes e explicar motivo da decisão | A executar acompanhado |
| Ambiguidade/falta | Manter pendência e localizar evidência adicional | A executar acompanhado |
| Parcelas/baixas | Separar vencimento de pagamento e conferir componentes | Fonte real/regras pendentes |
| Recuperação | Retomar após interrupção e conferir que nada duplicou | Prova operacional pendente |
| Relatório/saída | Baixar conferência e distinguir saída ERP homologada | Q-47 permanece aberto |

Registrar data, participantes, versão do site/agente, recorte, referências das
evidências, dificuldades e nova execução necessária. O proprietário revisa a
amostra independente de 200 itens e os critérios D-73; os 163 eventos atuais
não bastam. Precisão, integridade, tempo, recuperação e importação no destino
devem ter medições reais. Treinamento realizado e aceite do módulo são registros
separados, dependentes da participação e aprovação humanas efetivas.

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
importados. A coleta direta do Domínio ainda depende do complemento de
estrutura e da conferência de Q-46. Não há baixa, escrituração ou confirmação
automática de associação pela igualdade de data/valor.

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
