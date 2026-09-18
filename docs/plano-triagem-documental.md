# Plano de triagem documental

Status: rascunho para confirmação. Este documento transforma a reunião de 11/09/2026 às
16:10 e a fotografia recebida em um plano técnico. Ele não aprova taxonomia, caminhos,
integrações, regras de descarte, envio de mensagens ou uso de IA externa.

## Objetivo

Receber um arquivo, tratá-lo como conteúdo não confiável, identificar com evidências a empresa,
o tipo documental, o período e os demais metadados exigidos pela nomenclatura, apresentar a
decisão quando houver ambiguidade e, somente depois dos critérios aprovados, arquivá-lo no destino
correto.

O mesmo fluxo deverá admitir dois destinos intercambiáveis:

- biblioteca documental administrada pelo sistema, com pastas lógicas e arquivo privado; ou
- estrutura de pastas Windows já usada pelo escritório, operada pelo agente Windows dentro de
  raízes previamente autorizadas.

A escolha entre os destinos não está feita. O plano propõe um contrato único de armazenamento
para que a classificação não dependa do local físico do arquivo.

## O que já existe no repositório

- `ClientCompany` já representa a empresa dentro do escritório e possui código Domínio, chave
  externa e isolamento por organização (`src/apps/hub/models.py`).
- `ChatAttachment` já guarda anexos cifrados e isolados por organização, mas é entrada do
  Copiloto, não um acervo documental permanente (`src/apps/intelligence/models.py`).
- O serviço atual aceita PDF, JPEG, PNG, WebP, TXT e CSV, limita cada anexo a 10 MB e pode usar o
  modelo multimodal local (`src/apps/intelligence/services.py`). Esses formatos e limites não são
  automaticamente os da triagem; precisam ser confirmados.
- `ImportBatch` é auditável, mas declara que arquivos brutos são descartados após o processamento.
  Portanto, não deve ser reaproveitado como documento arquivado sem alterar explicitamente o seu
  contrato (`src/apps/hub/models.py`).
- O agente Windows atual já trabalha com autenticação mTLS/HMAC e saída HTTPS, mas processa backup
  Domínio. Ele ainda não observa nem grava a árvore documental do escritório
  (`agent-windows/src/CICA.Agent.Service`).

## Escopo funcional proposto para confirmação

1. Entrada recebe um ou vários arquivos e registra origem, remetente/operador, horário, tamanho,
   hash e nome original.
2. Quarentena valida extensão permitida, tipo real do conteúdo, assinatura do arquivo, limite de
   tamanho, arquivo íntegro e resultado antimalware antes de OCR ou abertura.
3. Extração obtém texto e campos verificáveis. Texto encontrado dentro do documento nunca é
   tratado como instrução para a IA.
4. Identificação da empresa produz candidatos a partir de identificadores aprovados. Nenhum nome
   aproximado autoriza arquivamento automático por si só.
5. Classificação escolhe apenas entre tipos documentais ativos no catálogo do escritório e guarda
   confiança e evidências por campo.
6. Período é extraído segundo a regra do tipo documental, sem presumir que data de emissão,
   competência, intervalo do extrato e data de pagamento são equivalentes.
7. Prévia mostra empresa, tipo, período, instituição/contraparte, nome final e destino.
8. Regra de decisão envia o item para arquivamento automático ou para revisão humana.
9. Arquivamento grava sem sobrescrever silenciosamente, confirma o hash no destino e registra
   trilha de auditoria.
10. O checklist de documentos recebidos é atualizado apenas após o arquivamento confirmado. As
    pendências poderão alimentar a futura cobrança por WhatsApp.

## Estados do item

```text
recebido
  -> em_quarentena
  -> rejeitado | aguardando_extracao
  -> em_extracao
  -> aguardando_revisao | pronto_para_arquivar | falha
  -> arquivando
  -> arquivado | falha_de_arquivamento
```

Um item duplicado, um arquivo que reúne documentos de empresas diferentes e um documento com
mais de um período precisam de regras próprias; os três casos permanecem em confirmação.

## Metadados mínimos propostos

Cada documento terá, conceitualmente, os seguintes dados. Os nomes de modelos, tabelas e campos só
serão definidos na implementação, depois da confirmação.

- escritório e empresa;
- tipo documental e revisão da taxonomia usada;
- período, com natureza do período (competência, intervalo, data de pagamento ou anual);
- instituição financeira, imobiliária, inquilino ou outra contraparte quando a regra exigir;
- nome original, nome final e destino lógico/físico;
- hash, tamanho, tipo declarado e tipo detectado;
- origem e responsável pelo envio;
- estado de segurança, extração, revisão e arquivamento;
- valores sugeridos pela IA, confiança por campo e trechos/páginas que sustentam cada valor;
- correções humanas, responsável e data;
- identificador da cópia física e confirmação do hash após a gravação.

Pastas são uma apresentação do acervo; empresa, tipo e período devem continuar pesquisáveis como
metadados. Essa separação segue o padrão de bibliotecas documentais, nas quais o tipo de conteúdo
define os metadados extraídos e pesquisáveis, sem tornar o caminho a única fonte de verdade.

## Leitura provisória da fotografia

A tabela abaixo é transcrição para conferência, não catálogo aprovado. `0000`, `BANCO`,
`INSTITUICAO`, `IMOBILIARIA`, `INQUILINO` e `062026` são marcadores cujo significado precisa ser
confirmado.

| Descrição na foto | Modelo lido na foto |
|---|---|
| Extratos conta corrente | `0000_EXTRATO_BANCO_062026` |
| Extratos Aplicações | `0000_EXTRATO_APLIC_BANCO_062026` |
| Comprovantes Pagamentos | `0000_COMPROVANTES_PGTO_BANCO_062026` |
| contas recebidas | `0000_RELATORIO_CONTAS_RECEBIDAS_062026` |
| Relatório pix | `0000_RELATORIO_PIX_BANCO_062026` |
| Cota capital | `0000_EXTRATO_COTA_CAPITAL_BANCO_062026` |
| Caixa Físico | `0000_RELATORIO_CAIXA_062026` |
| Contas a pagar | `0000_RELATORIO_CONTAS_A_PAGAR_062026` |
| Contas a receber | `0000_RELATORIO_CONTAS_A_RECEBER_062026` |
| Distribuição de lucros | `0000_RELATORIO_DISTRIBUICAO_062026` |
| Estoque | `0000_ESTOQUE_062026` |
| Cartão de crédito | `0000_FATURA_CARTAO_BANCO_062026` |
| Cartões recebíveis | `0000_RELATORIO_CARTAO_INSTITUICAO_062026` |
| Aluguéis recebido (IMOBILIÁRIA) | `0000_DEMONSTRATIVO_ALUGUEL_IMOBILIARIA_062026` |
| Aluguéis recebido (DIRETO - SEM IMOBILIÁRIA) | `0000_RECIBO_ALUGUEL_INQUILINO_062026` |
| Fluxo de caixa | `0000_RELATORIO_FLUXO_CAIXA_062026` |
| Pagamento aluguel | `0000_COMPROVANTE_ALUGUEL_IMOBILIARIA_062026` |
| Cupom fiscal | `0000_RELATORIO_CUPOM_FISCAL_062026` |
| Informe de rendimento (Caixa, Banrisul - Anual não precisa) | `0000_INFORME_RENDIMENTO_BANCO_062026` |

Pontos que a fotografia não resolve:

- se `0000` é código Domínio, outro código da empresa ou texto literal;
- se o mês/ano é sempre `MMYYYY` e como nomear documentos anuais;
- quais instituições devem preencher cada marcador e qual cadastro normaliza seus nomes;
- se “contas recebidas” é um tipo distinto de “contas a receber”;
- se singular/plural e abreviações da foto são obrigatórios;
- onde cada tipo fica na árvore de pastas;
- como nomear mais de um arquivo do mesmo tipo, empresa, instituição e período;
- se o arquivo original deve ser preservado com o nome recebido além da cópia renomeada.

## Identificação e decisão da IA

A IA deve devolver dados estruturados, não apenas uma resposta em linguagem natural. Para cada
campo, o resultado deve conter valor sugerido, confiança, origem da evidência e motivo objetivo de
eventual rejeição. Regras determinísticas validam a resposta antes de qualquer gravação.

Ordem candidata, ainda sujeita à confirmação:

1. identificador exato dentro do documento, como CNPJ ou código aprovado;
2. vínculo explícito informado pelo canal de entrada;
3. instituição, razão social e outros sinais apenas para formar candidatos;
4. revisão humana quando houver empate, ausência, divergência ou identificador pertencente a
   outro escritório.

Os limiares de confiança não foram definidos. O piloto deverá usar amostras reais mascaradas ou
formalmente autorizadas, medir acerto separadamente para empresa, tipo e período e manter
arquivamento automático desligado até atingir critérios aprovados.

Classificadores documentais de mercado separam classificação de extração e admitem revisão dos
metadados. Como referência, o Azure Document Intelligence exige ao menos cinco documentos por
classe para iniciar um classificador personalizado e consegue classificar por página; isso é uma
referência de formato de trabalho, não uma escolha de fornecedor nem uma amostra suficiente para
produção.

## Destino administrado pelo sistema

Proposta a confirmar:

- binário privado fora do diretório público da aplicação;
- registro documental no banco como catálogo e fonte da trilha;
- “pastas” lógicas derivadas das regras aprovadas;
- download sempre autenticado, autorizado por escritório/empresa e entregue como anexo;
- versionamento ou política de colisão explícita, sem sobrescrita silenciosa;
- retenção, descarte, restauração e cópia de segurança definidos antes de produção.

O backend físico ainda não foi escolhido. O `FileSystemStorage` local atual não deve ser declarado
adequado para produção sem decisão de implantação, backup e recuperação.

## Destino em pastas Windows existentes

Proposta a confirmar:

- ampliar o agente Windows já existente, mantendo conexão iniciada de dentro do escritório;
- configurar raízes de entrada e saída por caminho local ou UNC, nunca por texto sugerido pela IA;
- validar com caminho canônico que toda leitura e gravação permanece dentro das raízes
  autorizadas;
- executar com conta de serviço e permissões mínimas;
- esperar o arquivo terminar de ser copiado antes da leitura;
- escrever primeiro um arquivo temporário no mesmo volume, validar tamanho/hash e então renomear
  de forma atômica;
- nunca substituir arquivo existente sem a política de colisão confirmada;
- manter fila local recuperável e repetir operações por chave idempotente;
- combinar observação de eventos com varredura periódica, porque o mecanismo de notificação do
  Windows usa um buffer que pode perder eventos em sobrecarga;
- respeitar caracteres reservados, nomes reservados e limites de caminho do Windows.

O Hub não deve receber acesso de rede direto ao compartilhamento Windows. O agente devolve apenas
estado, evidência operacional e identificadores necessários ao catálogo, salvo se for aprovada uma
cópia do conteúdo para o armazenamento interno.

## Checklist e cobrança de documentos

O checklist precisa ser uma regra própria, não uma inferência improvisada a partir da pasta. Para
cada empresa e período, deve informar quais tipos são esperados, opcionais, dispensados ou não
aplicáveis. Um item só conta como recebido depois de arquivado e associado sem ambiguidade.

A mensagem “Recebemos X documentos, faltam: [lista]” será composta com itens do checklist e
passará por prévia ou automação conforme política ainda não definida. Antes dessa frente é preciso
confirmar número remetente, provedor, destinatários, consentimento, descadastro, janela/horário,
cadência, modelo aprovado, escalonamento humano e custo. Mensagens iniciadas pela empresa no
WhatsApp usam modelos aprovados e estão sujeitas à cobrança do provedor; nenhuma chamada paga está
autorizada por este plano.

## Banco Central e Receita Federal como validação auxiliar

Não existe neste plano uma integração automática aprovada.

- O relatório CCS/Registrato pode confirmar instituições com as quais a pessoa ou empresa mantém
  relacionamento e datas de início/fim. O próprio Banco Central informa que ele não contém agência,
  número da conta, saldo ou movimentação.
- O acesso ao Registrato requer conta gov.br apropriada, verificação em duas etapas ou autorização
  concedida pelo titular. O modo juridicamente e tecnicamente permitido de obtenção ainda precisa
  ser definido.
- As páginas públicas consultadas não demonstram uma API pública que autorize este produto a
  enumerar automaticamente as contas de cada cliente.
- Informações da Receita ou da declaração pré-preenchida podem omitir itens ou exigir conferência
  com comprovantes. Não substituem o checklist nem o documento emitido pela instituição.

Assim, a frente candidata é importar um relatório obtido de forma autorizada, extrair somente
indícios de instituições e comparar esses indícios com documentos recebidos. Divergência gera
pendência para revisão, nunca criação automática de uma conta ou conclusão de ausência.

## Domínio para clientes maiores

Esta frente fica fora do caminho crítico da triagem. O repositório já contém integração Domínio
somente leitura e agente local, mas a reunião cita um “módulo Open Files” e um impedimento não
identificado. Antes de planejar implementação é necessário confirmar o nome oficial do produto ou
módulo, documentação, modalidade do Domínio usada pelos clientes, tipo de acesso, limite, custo,
licença e se o impedimento ainda existe. Nada disso foi inferido.

## Segurança e proteção de dados

- lista permitida de formatos, validação por conteúdo/assinatura e antimalware antes do processamento;
- quarentena separada do conteúdo disponível para download;
- criptografia em trânsito e repouso, controle por escritório/empresa e privilégio mínimo;
- nomes físicos não previsíveis no armazenamento administrado; nome contábil preservado como
  metadado e no download/destino quando aprovado;
- conteúdo do documento isolado de instruções do sistema para reduzir injeção de prompt;
- logs sem conteúdo, CNPJ, CPF, dados bancários ou caminho completo desnecessário;
- auditoria de entrada, leitura, correção, arquivamento, download, reprocessamento e descarte;
- retenção mínima necessária, cópia de segurança e teste de restauração;
- sem envio a provedor externo de IA antes de decisão de fornecedor, base legal, contrato,
  localização, retenção e custo.

Esses controles seguem a orientação da OWASP para upload (lista permitida, validação do tipo real,
assinatura, antimalware e armazenamento segregado) e a orientação da ANPD sobre minimização,
controle de acesso, criptografia e backup seguro.

## Entregas em frentes separadas

Cada item abaixo deve ser implementado e validado em um commit próprio. Não há número de card,
versão ou prazo porque esses dados não foram fornecidos.

- registrar decisões e catálogo documental aprovado;
- criar o domínio de triagem e sua máquina de estados;
- criar o contrato de armazenamento e o destino administrado pelo sistema;
- criar a entrada segura e a quarentena;
- criar extração estruturada e validações determinísticas;
- criar identificação da empresa, tipo e período com evidências;
- criar fila de revisão e correção humana;
- criar arquivamento idempotente e política de duplicidade/colisão;
- ampliar o agente para entrada e destino Windows;
- criar checklist de recebidos e pendentes;
- criar cobrança por WhatsApp após autorizações e confirmação de custo;
- criar importação autorizada de relatórios BCB/RFB como validação auxiliar;
- investigar o módulo Domínio citado e só então planejar sua integração.

Mudança de modelo e migração, regra de negócio, tarefa assíncrona, interface, agente Windows e
integração externa não devem ser misturados no mesmo commit apenas para reduzir a quantidade de
commits.

## Estratégia de testes

- unidade: normalização de cada marcador, período, nome Windows, hash, confiança e transições de
  estado;
- contrato: a mesma suíte para armazenamento administrado e Windows;
- segurança: extensão falsa, MIME falso, assinatura inválida, arquivo grande, arquivo malicioso,
  ZIP bomb se ZIP for aprovado, path traversal, symlink/reparse point e acesso entre escritórios;
- classificação: matriz aprovada com verdade conhecida por empresa, tipo e período, incluindo
  negativos e documentos parecidos;
- revisão: nenhum item ambíguo é arquivado sem ação autorizada;
- idempotência: reenvio, repetição de evento Windows, queda durante cópia e retomada não duplicam
  nem sobrescrevem;
- integração: arquivo entra, é extraído, revisado quando necessário, chega ao destino esperado e
  atualiza o checklist;
- recuperação: indisponibilidade do modelo, fila, Hub, agente ou compartilhamento mantém o item
  recuperável;
- aceitação: executar com cópias controladas de arquivos reais e conferir nome, conteúdo, hash,
  empresa, período, destino e auditoria.

Os comandos exatos só poderão ser definidos quando existirem os arquivos e testes de cada frente.

## Critérios para liberar arquivamento automático

- catálogo, nomenclatura, árvore e política de colisão aprovados;
- amostra de validação separada da amostra usada para configurar o classificador;
- metas de precisão aprovadas e atingidas por campo e por tipo documental;
- zero arquivamento em empresa errada no conjunto de aceitação aprovado;
- teste de isolamento entre escritórios e de fuga da raiz Windows aprovado;
- revisão humana obrigatória para todo caso fora dos critérios;
- trilha de auditoria e restauração testadas;
- piloto reversível com grupo de empresas definido pelo escritório.

## Confirme antes de mudar

Estas perguntas são decisões do responsável; o plano não as responde:

1. Qual é o caminho da pasta de entrada e qual é a raiz de destino das empresas? Informe se são
   caminhos locais, unidades mapeadas ou UNC e em qual máquina ficam.
2. A escolha “armazenamento do sistema” ou “pastas Windows” vale para o escritório inteiro, para
   cada empresa ou para cada tipo documental? Os dois modos podem coexistir?
3. O arquivo deve entrar por tela, pasta monitorada, e-mail, WhatsApp ou outro canal? Quais canais
   entram no primeiro recorte?
4. `0000` é qual identificador? Ele corresponde a `ClientCompany.dominio_code`? Qual identificador
   dentro do documento autoriza vincular automaticamente uma empresa?
5. A transcrição da foto está correta? Confirme também se “contas recebidas” e “contas a receber”
   são categorias diferentes.
6. Qual é a árvore completa de destino de uma empresa e qual é a regra para documentos mensais,
   anuais, com intervalo ou com mais de uma competência?
7. Como resolver dois arquivos com o mesmo nome final: bloquear, pedir revisão, criar sequência ou
   versionar? O original é movido ou copiado?
8. Quais formatos, tamanhos, quantidade de páginas, arquivos protegidos por senha e arquivos
   compactados devem ser aceitos?
9. Quais campos são obrigatórios por tipo e quais evidências prevalecem quando nome do arquivo,
   conteúdo e pasta de origem divergem?
10. Quais casos podem ser automáticos e quais exigem sempre revisão? Quais metas mínimas de acerto
    aprovam o piloto?
11. Quais documentos cada perfil de empresa deve entregar por mês/ano e quais exceções existem?
12. Qual é a retenção do original, da cópia arquivada, do texto extraído, das previsões da IA e da
    auditoria? Quem pode visualizar, corrigir, baixar e excluir?
13. A IA precisa permanecer integralmente local? Se serviço externo for aceitável, qual fornecedor
    e quais limites jurídicos, técnicos e financeiros já foram aprovados?
14. Para BCB/RFB, o cliente enviará relatórios exportados ou existe autorização/documentação de
    outro meio de acesso? Quem revisa divergências?
15. Para WhatsApp, já existem conta/provedor, consentimentos e modelos aprovados? Nenhum envio pago
    será feito sem confirmação específica de preço e escopo.
16. Qual é o nome/documentação exatos do módulo “Open Files” do Domínio e qual era o impedimento
    citado na reunião?

## Referências consultadas

- Banco Central — Relatório de Contas e Relacionamentos (CCS):
  <https://www.bcb.gov.br/meubc/faqs/s/relatorio-de-contas-e-relacionamentos-em-bancos-ccs1>
- Banco Central — Registrato e autorizações:
  <https://www.bcb.gov.br/meubc/registrato/1000/https%3A/www3.bcb.gov.br/sgspub>
- Microsoft — modelos de processamento documental e metadados:
  <https://learn.microsoft.com/en-us/microsoft-365/documentprocessing/model-types-overview>
- Microsoft — classificador personalizado do Document Intelligence:
  <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/how-to-guides/build-a-custom-classifier>
- Microsoft — `FileSystemWatcher`:
  <https://learn.microsoft.com/en-us/dotnet/api/system.io.filesystemwatcher>
- Microsoft — regras de nomes e caminhos Windows:
  <https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>
- OWASP — File Upload Cheat Sheet:
  <https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html>
- ANPD — materiais e guia de segurança da informação:
  <https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes>
- WhatsApp Business — Política de Mensagens:
  <https://business.whatsapp.com/policy/preview?lang=pt_BR>
