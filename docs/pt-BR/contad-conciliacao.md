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

## Importar o extrato

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
