# Teste único de importação no Domínio — roteiro da chamada

Para liberar o envio definitivo de lançamentos da CICA para o Domínio (Q-47, D-380),
a CONTAD precisa importar **uma vez** um arquivo de teste no próprio Domínio e
conferir o resultado. A CICA não tem acesso ao servidor da CONTAD e não grava nada
direto no Domínio: o teste é feito por alguém da CONTAD, com a equipe CICA
acompanhando por chamada de vídeo com a tela compartilhada.

- **Quem:** uma pessoa da CONTAD com acesso ao Domínio e à CICA (perfil que pode
  gerenciar a conciliação) + responsável CICA.
- **Duração:** cerca de 20 minutos.
- **Resultado:** a exportação passa a funcionar para a CONTAD, sem novo deploy.

## Antes da chamada (CONTAD, 5 minutos)

1. Escolha **de 1 a 3 movimentos do extrato que ainda não estão no Domínio** — por
   exemplo, de um mês em que a conta ainda não foi lançada. Devem ser lançamentos
   que a CONTAD faria de qualquer forma; eles entrarão de verdade na contabilidade.
   O extrato desse mês precisa já estar importado na CICA, com a conta vinculada.
2. Para cada movimento, tenha em mãos a **conta de débito** e a **de crédito** pelo
   código reduzido do Domínio (o número que aparece em *Contas do Domínio*).
3. Anote a versão do Domínio em uso, por exemplo “Contábil 10.6A-10,
   atualização 08” (a observada no SVAPL02 em 18/11).

Movimentos que já têm par no Razão do Domínio **não geram lançamento**: a CICA
recusa, para não duplicar o que já está escriturado.

## Durante a chamada

### 1. Na CICA — gerar e aprovar os lançamentos

Para cada movimento escolhido, em *Conciliação → Movimentos normalizados*:

1. Abra o movimento.
2. Em **Dados para o lançamento**, preencha **Conta de débito**, **Conta de crédito**
   e **Histórico contábil** e clique em **Salvar revisão**.
3. Clique em **Gerar lançamento rascunho**, confira as partidas e clique em
   **Validar e aprovar lançamento**.

### 2. Na CICA — gerar a prévia

1. Em *Conciliação → Arquivos e histórico*, clique em **Prévia para conferência**
   (abre *Preparar arquivo de conferência*).
2. Escolha a empresa/conta e o período que contém os movimentos e clique em
   **Gerar prévia para conferência**.
3. Em **Prévias preservadas**, clique em **Baixar prévia não homologada**. O arquivo
   é um `.txt`. **Não abra nem salve o arquivo em editor de texto** antes de importar:
   o leiaute tem tamanho fixo e qualquer alteração invalida o teste.
4. Diga à equipe CICA a empresa, o período e o horário da prévia, para ela
   identificar o arquivo do lado de cá.

### 3. No Domínio — importar

1. *Utilitários → Importação → Importador*.
2. **Tipo:** TXT. **Conjunto de dados:** “Lançamentos Contábeis em Lote (Leiaute
   Domínio Sistemas)” — código 19.
   Se esse conjunto não aparecer na lista, pare aqui: a Domínio disponibiliza o
   leiaute na solução 7584 da central de atendimento; avise a CICA.
3. Selecione o arquivo baixado e importe **uma única vez**.
4. Tire um print da mensagem final do importador (sucesso ou erros).

### 4. No Domínio — conferir

Para cada lançamento importado, compare com a tela da CICA:

| Conferir | Esperado |
|---|---|
| Empresa | a mesma da prévia |
| Data | a data do movimento no extrato |
| Conta débito / crédito | os códigos reduzidos informados no passo 1 |
| Valor | igual ao do movimento, com centavos |
| Histórico | o texto do passo 1 (acentos preservados) |
| Filial | a própria empresa |

Tire um print de cada lançamento importado (ou do Razão da conta no período).

### 5. Na CICA — registrar a liberação (equipe CICA)

Só depois de a CONTAD dizer que o resultado está correto:

1. Simulação, sem gravar nada:
   `record_dominio_homologation --organization <escritório> --preview <prévia>
   --importer-version "<versão do passo 3 de Antes da chamada>"
   --decision "<quem conferiu na CONTAD>, <data>, prints em <local privado>"`
2. Conferir no resultado o hash do arquivo, a prévia e `homologated_before: false`.
3. Repetir com `--apply` e conferir `homologated_after: true`.
4. Guardar os prints em pasta privada fora do Git (0700/0600) e registrar a
   validação em VALIDACOES.md com a autoria real de quem conferiu.

A partir daí, *Arquivos e histórico* passa a gerar os arquivos definitivos para a CONTAD,
com o recibo de conferência por lançamento.

## Se algo der errado

| O que aconteceu | O que fazer |
|---|---|
| O Importador recusou o arquivo | Print da mensagem exata (com a linha, se houver). Nada foi importado; não tente de novo editando o arquivo. |
| Importou com algum campo errado | Print do lançamento. Exclua no Domínio os lançamentos desse teste, pelo procedimento usual da CONTAD, antes de qualquer nova tentativa. |
| Importou parte dos lançamentos | Prints da mensagem e do que entrou. Exclua o que entrou antes de nova tentativa. |
| Conjunto 19 não aparece | Pare e avise a CICA (solução 7584 da Domínio). |

Pontos que a CICA ainda não viu o Importador confirmar e que podem aparecer numa
mensagem de erro: usuário do lote gravado como “CICA”; CNPJ do cabeçalho em branco
quando o cadastro da empresa não tem 14 dígitos; código de histórico padrão zerado;
filial igual ao código da empresa. Com a mensagem exata em mãos, a CICA ajusta o
arquivo, gera outra prévia e repete o teste.

## Não fazer

- Não importar o mesmo arquivo duas vezes: o Domínio duplicaria os lançamentos.
- Não editar o `.txt` à mão.
- Não usar movimentos que já estão no Domínio (a CICA também recusa).
- Não registrar a liberação sem a importação conferida pela CONTAD.
