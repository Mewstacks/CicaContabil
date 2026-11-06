> **Leitura vigente após auditoria de 05/10/2026 (D-275/V-275):** os IDs abaixo permanecem

> **Atualização 10/10/2026 — D-295:** Q-39/PC-03 deixam de bloquear o plano: o responsável confirmou concluída a validação externa de importação NFS-e e pediu aceitar a informação sem solicitar comprovante ou repetir o teste. Textos históricos abaixo que pedem o retorno ficam superados por esta decisão. Não presumir detalhes técnicos não informados.

> **Atualização 15/10/2026 — D-318:** identificado o importador realmente em uso: Importador por conjunto de dados (`Utilitários > Importação > Importador > Importar`), e não a tela `Configuração de Importação > NFS-e Arquivo XML - Padrão Nacional`. A espécie da nota é gravada pelo conjunto na coluna `codi_esp` com valor fixo, hoje 1; o valor correto varia por cliente (39 na base atual). Isso responde a parte "qual importador e onde entra a classificação" de Q-39, mas não a homologação do retorno. A CICA não escreve espécie e não gera conjunto de dados.

> únicos, mas suas partes históricas precisam ser confrontadas com decisões posteriores.
> D-109 substituiu o modelo incompatível de módulos/tokens por capacidade, IA em reais e custo
> efetivo Integra: Q-01–06/D-79 não devem ser reabertas como escolhas nunca respondidas.
> Q-35 tem o ambiente SaaS resolvido (Fly+Neon); a máquina definitiva de IA continua separada.
> Q-38 já tem backup Bianchi usado; pedir somente material adicional necessário.
> Q-13/Q-29 têm domínio do site definido, sem que isso prove OAuth/SMTP/entrega.
> Q-39 já tem evidência de `infNFSe/valores/acum` em D-274; falta a importação conferida e seu
> retorno. Q-30 permanece resolvida por D-73: aplicar métricas, não perguntar de novo.
> Próximos pedidos concretos e trabalho independente estão no [plano mestre](../../PLANO-MESTRE.md).
> Esta nota reconcilia referências; não escolhe valores, políticas ou capacidades ainda ausentes.

# Dúvidas que exigem resposta do responsável

> Registro único de perguntas. Atualização de 18/09/2026: decisões vigentes em [DECISOES.md](../../DECISOES.md), etapas em [PLANO-MESTRE.md](../../PLANO-MESTRE.md). Q-07, Q-10 e Q-37 estão resolvidas; não perguntar novamente. A tabela de responsabilidade ao final indica quem responde e onde cada pendência bloqueia trabalho.

Regra D-75: ao comunicar qualquer item aberto, apresentar decisão/acesso necessário, impacto, recomendação e procedimento prático para o responsável; não limitar a comunicação ao nome do bloqueio.

Atualizado em 15/09/2026. Nenhuma opção abaixo é escolhida por este documento. As perguntas foram deduplicadas dos 16 itens do [plano inicial de triagem](../plano-triagem-documental.md), dos planos CL-01 a CL-04, do plano Codex CX-05, dos reviews CICA e das respostas recentes. Respostas já dadas constam em [decisões](decisoes.md); aqui estão os detalhes ainda insuficientes para especificar, vender ou ativar o comportamento.

## Contrato e cobrança

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-01 | Resolvida por D-79: 7 dias após atraso confirmado; pagamento reativa, estorno/disputa retorna a somente leitura. | Implementar com idempotência de webhook na etapa 10. |
| Q-02 | Resolvida por D-79: consulta, documentos arquivados, auditoria e exportação própria permanecem; novas operações e consumo ficam bloqueados. | Aplicar por operação e testar APIs na etapa 10. |
| Q-03 | Resolvida por D-79: Comercial/Admin Mewstack opera contrato manual, com motivo e comprovante auditáveis. | Implementar fluxo integral na etapa 10. |
| Q-04 | Resolvida por D-79: competência fecha dia 1, vencimento dia 10, primeiro mês proporcional e mudança de plano no ciclo seguinte. | Operacionalizar e homologar na etapa 10. |
| Q-05 | Resolvida por D-76/D-79: a tabela documental de preço, franquias, pesos e tetos é a regra aprovada. | Materializar e homologar o medidor/faturamento na etapa 10; chamadas Serpro continuam sujeitas à autorização de custo. |
| Q-06 | Resolvida por D-79: teste de 14 dias, sem cartão e sem reinício por convite; contrato manual também pode usar teste. | Implementar e homologar junto ao ciclo de cobrança na etapa 10. |
| Q-07 | Resolvida: Triagem substitui Jornadas no produto; sem contratos comerciais antigos. | D-43. O schema legado fica sem rota ou oferta; não publicar preço de Triagem sem decisão. |

## IA e custo

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-08 | Quais tetos por solicitação/dia/mês e franquias por escritório valem para Copiloto e Triagem? Quem pode elevar ou revogar limites? | A chave/modelo e uma geração sintética real foram validados com `claude-sonnet-5`; isso **não** aprova o orçamento comercial nem libera escritórios. O roteador atual exige tetos positivos. |
| Q-09 | Que conteúdo dos anexos/documentos pode sair para Claude, por qual base contratual, com qual mascaramento, retenção e informação ao escritório/cliente? Há tipos que devem permanecer locais? | A decisão provisória cobre anexos da Triagem, mas privacidade, custo e política de egressão precisam ser fechadas antes do uso real. |
| Q-10 | **Resolvida em 17/09/2026:** local como padrão após homologação; API como reserva autorizada. Pipeline preparado e testado basta para o recorte local da venda inicial por API. | D-50 e D-51. Não reabrir a escolha de rota. Métricas e aceite de virada permanecem exclusivamente em Q-30; hardware em Q-35. |
| Q-11 | Qual processo de rotação, teste e alerta para a chave central `CICA_CLAUDE_API_KEY`, sem revelá-la em interface/log? | A chave já está no `.env` e foi aceita na contagem gratuita; isso não define governança de produção. |

## Triagem: entrada, identificação e catálogo

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-12 | A caixa própria conectada lerá caixa inteira, pasta/label dedicada ou filtros? Quem no escritório concede consentimento e revoga? Haverá caixa compartilhada em etapa posterior? | Caixa própria está confirmada; CL-04 assumiu pasta dedicada explicitamente sem confirmação. |
| Q-13 | Qual domínio/redirect HTTPS de produção a Mewstack fornecerá aos aplicativos OAuth dos escritórios? Qual o custo/prazo da verificação e eventual avaliação de segurança do app **Mewstack** para Gmail pessoal com `gmail.readonly`? | D-23 decide app do escritório para Microsoft/Workspace e app verificado Mewstack para Gmail pessoal. Registro/publicação, permissões reais e homologação ainda não ocorreram. [Pesquisa oficial](conexao-caixas-email.md). |
| Q-14 | Qual data de início/corte para mensagens antigas, política de reprocessamento e de exclusão após ingestão? A CICA marca e-mail como lido, move mensagem ou só lê? | Cursor, deduplicação e risco de importar conteúdo histórico dependem da regra. |
| Q-15 | Confere a transcrição das 19 linhas da foto em [catálogo a confirmar](catalogo-triagem-a-confirmar.md)? “Contas recebidas” e “contas a receber” são categorias diferentes? Quais singular/plural/abreviações são oficiais? | Não transformar transcrição de reunião em migration/catalogue aprovado. |
| Q-16 | Qual é a árvore de destino completa por empresa e tipo? Como tratar mensal, anual, intervalo e múltiplas competências? Quais marcadores de banco/instituição/imobiliária/inquilino são usados? | Código Domínio na pasta e `MMYYYY`/`YYYY` não especificam a árvore completa. |
| Q-17 | Qual identificador dentro do documento autoriza vínculo automático além de CNPJ legível? O que fazer com CNPJ de matriz/filial, terceiros, documento sem CNPJ ou dois CNPJs? | CL-04 propõe CNPJ único; faltam casos reais e regra de revisão. |
| Q-18 | Quais campos obrigatórios e evidências prevalecem por tipo quando nome, conteúdo, remetente e pasta divergem? A confiança ≥98% por campo é requisito aprovado e qual precisão medida precisa ser atingida no piloto? | Número emitido pela IA não demonstra qualidade; automatização precisa de amostra de aceite. |
| Q-19 | Quais formatos/tamanhos/páginas/proteções são aceitos? CL-04 propôs 50 MB/PDF até 100 páginas e imagens/TXT; serviço local em andamento aceita upload manual de 25 MB e PDF/CSV/XML/OFX/XLSX. Qual contrato vale para anexo de e-mail? | Os dois contratos divergem e o fluxo manual não é entrada da primeira versão vendável. |
| Q-20 | Qual política para mesmo hash, nomes iguais de conteúdos diferentes, arquivo multi-documento, mais de um período e reenvio pelo cliente? Original é copiado, movido ou descartado? | Até a decisão, cada entrega de e-mail diferente é preservada em quarentena com sua origem, inclusive mesmo hash; a mesma mensagem+parte reapresentada pelo provedor é idempotente. Dedupe de arquivamento, versionamento, revisão e auditoria dependem da regra; CL-04 registra somente parte da política. |
| Q-21 | Quais tipos de empresa esperam quais documentos por mês/ano, com dispensas, exceções e alterações de regra? | Checklist não pode ser inferido apenas das pastas; “recebido” conta após arquivamento confirmado. |

## Triagem: destino, segurança e integrações futuras

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-22 | Quais caminhos reais de entrada/raiz Windows, máquina, conta de serviço e modalidade local/UNC/unidade mapeada serão usados no piloto? Qual agente fará a escrita e como o escritório valida a raiz? | Pasta configurável pelo escritório ainda precisa de allowlist, teste de escape e confirmação de hash. |
| Q-23 | A escolha biblioteca/Windows vale para o escritório inteiro? Pode ser trocada, e o que acontece com arquivos já arquivados e backups? | A decisão confirma duas opções, não migração ou coexistência histórica. |
| Q-24 | Por quanto tempo guardar original, cópia, texto extraído, previsões IA, e-mail de origem e auditoria? Quem visualiza, corrige, baixa, exclui e restaura? | Privacidade, custo de armazenamento e recuperação não estão definidos. |
| Q-25 | Qual antimalware/OCR e política de quarentena/rejeição são exigidos, quem fornece ambiente e como será estimado/aprovado custo? | O candidato ClamAV local usa o protocolo oficial INSTREAM, com configuração desligada por padrão e testes em socket sintético; não há daemon, assinaturas atualizadas ou verificação real neste PC. Pergunta ao responsável enviada nesta conversa para escolher ClamAV local ou serviço contratado. Resultado limpo não libera o arquivo antes da regra aprovada de formatos/assinaturas; produto vendável não pode presumir proteção ou custo. |
| Q-26 | Para BCB/RFB, cliente entregará relatórios obtidos de forma autorizada ou existe outro mecanismo documentado? Quem revisa divergências? Para “Open Files” do Domínio, qual nome/documentação e impedimento exatos? | São frentes auxiliares; o plano inicial não aprovou coleta automática nem inventou API. |
| Q-27 | WhatsApp de pendências terá qual conta/provedor, número, destinatários, consentimento, modelo, janela, cadência, descadastro e teto? | Fora da primeira versão de triagem; envio pago depende de confirmação específica de custo. |

## Lançamento e prova

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-28 | Parcialmente resolvida em 18/09: Fedrizzi Contabilidade está disponível para homologação. Domínio já está conectado por ODBC; quais acessos e amostras são necessários para os demais conectores? | D-72/D-74. Não pedir DSN, driver, servidor ou credenciais Domínio novamente. D-53 já confirma servidor/banco Siescon disponível. Pedir apenas acesso seguro e amostra mínima na etapa do conector correspondente; não pedir credenciais no chat. Asaas, e-mail e infraestrutura continuam a requerer ambiente específico quando chegarem suas etapas. |
| Q-29 | Parcialmente resolvida em 18/09: suporte `suporte@mewstack.com.br` e SMTP Brevo definidos. Qual domínio/remetente final, contato de privacidade e termos finais serão publicados? | D-76/D-78. Configuração Brevo, DNS e teste de entrega pertencem à etapa 12 por D-77; minutas e serviço configurável não equivalem a versão comercial homologada. |
| Q-30 | Resolvida em 18/09: proprietário aprova cada módulo, conforme métricas de liberação registradas. | D-72 define o aprovador; D-73 fixa amostra, precisão, integridade, recuperação, restauração, tempo e conferência de exportação. Aplicar a métrica pertinente a cada módulo e registrar a prova. |
| Q-31 | Para o componente Windows `Nome [Domínio código]`, o nome vem do cadastro CICA ou da razão social Domínio? Quando mudar, renomeia a pasta existente ou mantém o caminho anterior? | Atualização técnica de 17/09: arquivamento pelo agente já existe no código, sem homologação no destino real. A origem do nome e a política de renomeação continuam sem decisão; não mover pastas por inferência. |

As dúvidas nesta lista são independentes de autorização monetária. Quando uma decisão implicar chamada de API paga ou infraestrutura cobrada, apresentar provider, recurso, escopo, custo estimado e reversão para confirmação imediatamente antes da ação.

## Pendências adicionais do plano aprovado em 17/09/2026

| ID | Pergunta que ainda falta | Alcance |
|---|---|---|
| Q-32 | Resolvida por D-80: serviço nativo .NET único para sincronização local, backup Web e arquivamento; Python fica apenas como diagnóstico/migração. | Implementar e homologar na etapa 03; não há SQL remoto nem escrita no Domínio. |
| Q-33 | Qual versão/banco Siescon, mecanismo de acesso autorizado e documentação/layout de exportação serão disponibilizados? Qual identificador de empresa substitui o código Domínio nos fluxos exclusivos de Siescon? | Etapa 04: banco disponível e leitura/exportação revisada já estão decididos em D-53/D-54. Não pedir segredos no chat. **Resolvida em 22/09/2026 por D-290**, com o levantamento do Lucrums como base e o limite de layout inferido. |
| Q-34 | Quem revisa e aprova exemplos, correções e publicações de modelos de cada escritório? | Etapas 05/13: isolamento já decidido em D-49; métricas em Q-30, egressão em Q-09. |
| Q-35 | Qual ambiente já disponível recebe o SaaS/IA central e qual equipamento será usado para a IA definitiva? | Etapas 01/12/13: D-46 confirma centralização, mas não escolhe provedor, máquina, GPU ou modelo. Não contratar recursos por inferência. |
| Q-36 | O recorte inicial de Parcelamentos permanece PARCSN ordinário ou inclui outras modalidades? | Etapa 08: preservar implementação atual até resposta; o plano exige perguntar antes de ampliar modalidades. |
| Q-37 | Resolvida em 18/09: manter LlamaFactory como ferramenta interna de treinamento; referência técnica fixada por digest. | D-71. A imagem foi construída e o binário validado localmente. Nenhum treino, modelo, GPU ou gasto foi autorizado por essa decisão. |

## Rentabilidade por Cliente (etapa 14)

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-41 | De qual fonte sai o honorário mensal por empresa? | Sem receita não há margem, e o levantamento do Lucrums (`docs/DESTRAVAR-DADOS.md`) registra que `efservicos` está vazio no próprio escritório e que os campos `PFT_*` do Siescon estão zerados desde 2018. As alternativas são um evento de Honorários a confirmar, lançamento manual por competência ou importação própria; cada uma muda modelo, tela e ingestão. Enquanto estiver aberta, o módulo calcula custo e horas, mas não margem. |
| Q-42 | Qual cobertura mínima de horas lançadas autoriza apresentar margem como número, e o que a tela deve dizer abaixo disso? | Em 21/09/2026 a cobertura observada era de 11%: 30 de 47 pessoas nunca lançaram hora, o que faz a margem ler alto demais. A fórmula está certa e o dado não está lá. Pela regra de D-98 a D-106, nada pode aparecer silenciosamente incompleto; é preciso definir o limiar e a legenda antes de publicar a tela. |
| Q-43 | Qual o mínimo mensal, o preço e o peso de token do módulo Rentabilidade? | O catálogo comercial e `TokenModuleRate` exigem valor aprovado. Sem resposta, o módulo entra com `TOKEN_BILLING_ENABLED` desligado e sem linha de preço, como os demais não homologados. |
| Q-44 | Resolvida em 22/09/2026 por D-290: o levantamento Siescon do Lucrums é aceito como base técnica, com o limite de que o layout foi inferido e não documentado pelo fornecedor. | O Lucrums já recuperou os layouts Btrieve por perfilamento estrutural e gerou os DDFs que habilitam SELECT por ODBC (`docs/ANALISE-SIESCON.md`, `docs/siescon/layout-v0.sql`). Se o responsável aceitar esse material como base, a etapa 04 deixa de estar bloqueada; se não aceitar, Q-33 continua valendo e o perfil Siescon do conector não é habilitado. |
| Q-45 | Resolvida em 22/09/2026 por D-289: o conector unificado permanece em `net8.0-windows`, e o código do Lucrums é portado para trás. | A CICA está em `net8.0-windows` e o conector do Lucrums em `net10.0-windows`. A escolha precede qualquer movimentação de arquivo, porque define runtime instalado no servidor do escritório, matriz de build e assinatura do pacote. |

## Conciliador do contrato — detalhamento em 27/10/2026

**Continuidade 03/11/2026 — D-308/V-309:** o responsável esclareceu que a
confirmação anterior veio do ODBC/Domínio. Teste .NET com DSN sem substituição
de credenciais passou; corrigido o pacote para usar explicitamente essa
autenticação. Atualização 1.0.1 no PC e teste do configurador confirmados.
Não pedir senha/DSN novamente. Q-28 conserva pareamento/destino/recorte;
endpoint CICA respondeu 503 por ausência da autoridade certificadora do agente.

**Atualização 03/11/2026 — D-308/V-308:** PC de teste já acessível e agente
instalado; configurador detectou DSN/driver existentes, mas o teste recebeu
ODBC 28000 (usuário/senha inválidos). Solicitado preenchimento correto direto
no RDP e novo teste, sem credenciais no chat ou recriação do DSN. Q-28 conserva
o recorte/destino do pareamento e os dados independentes; testes HTTP locais
não equivalem à sincronização do Windows nem resolvem Q-46/Q-47.

**Atualização 03/11/2026 — D-305:** o responsável confirmou que os títulos a
pagar/receber vêm do **Domínio** e que o piloto deve entregar **relatório e
arquivo para importação no Domínio**. Não repetir origem ou tipo de saída.
Q-28/Q-46 ainda exigem amostra/contrato de parcelas e baixas e recorte autorizado;
Q-47 ainda exige layout e importação contábil conferida, sem escrita direta.
Fornecidos PDF e OFX Sicredi para leitura/testes locais; não foi fornecido Razão,
lista de títulos, plano de contas ou acesso ao PC.

**Atualização 02/11/2026 — D-302:** Domínio **local**, agente **no computador da cliente**,
acesso ainda a fornecer e **incluir contas a pagar/receber** confirmados pelo responsável.
Não repetir essas escolhas. Q-28 conserva o acesso/recorte autorizado e a origem dos títulos;
Q-46 conserva campos, chaves, regras e entradas/saídas do DE-PARA; Q-47 conserva a operação
de destino. Inclusão não comprova implementação ou homologação. Correções locais e roteiro
em [V-302](../../VALIDACOES.md) e na [verificação CONTAD](verificacao-conciliador-contad-2026-11-02.md).

Escopo D-301, vinculado à etapa 09/PC-19. Perguntas operacionais no
[roteiro do contrato](levantamento-contrato-conciliador-2026-10-27.md).
Q-28 agora deve distinguir o ambiente da cliente deste contrato do ambiente
Fedrizzi já conhecido por D-74; também reúne fonte de títulos, acesso autorizado,
empresas/contas, volume, material e disponibilidade para implantação.

| ID | Pergunta objetiva | Impacto e responsável |
|---|---|---|
| Q-46 | Para o conciliador do contrato, quais fatos serão comparados, quais faltas devem aparecer, quais regras de correspondência/parcelamento/agrupamento/tolerância valem e quais entradas/saídas compõem o DE-PARA inicial? | Cliente/contadora explica a rotina e fornece exemplos/mapa existente; executor especifica e valida. Sem essas respostas não presumir baixa, vencimento como pagamento, conta por histórico ou tolerância numérica. D-73 mantém critérios técnicos de aceite já decididos. |
| Q-47 | Qual resultado deve voltar ao ERP: só conferência, arquivo para importação ou uma operação específica? Se a rota for fiscal, qual módulo, operação e retorno comprovam o resultado esperado? | Cliente/contadora demonstra o trabalho e o destino; técnico do ERP e executor conferem viabilidade, campos/layout e recuperação. A intenção de alternativa fiscal está em D-301, mas não há equivalência, escrita direta ou baixa automática autorizadas por inferência. O aceite NFS-e Q-39 não resolve esse contrato contábil/fiscal. |

Não reabrir preços, prazo, carga contratada ou treinamento inicial já escritos
no contrato. Apoio de IA ao DE-PARA também já está incluído; Q-08/Q-09 continuam
valendo para custo/egressão quando houver execução real. Perguntas sobre os
outros módulos não bloqueiam esta entrega por inferência.

## Donos, etapas e estado das perguntas

**Detalhamento de Q-28 para PC-19 em 26/10/2026:** o
[diagnóstico do conciliador](diagnostico-conciliador-2026-10-26.md) contém o roteiro
de levantamento de ambiente, Razão, contas, arquivos, período, exceções e material
de comparação. São desdobramentos operacionais de Q-28, não novas perguntas Q.
D-74 já confirma Domínio local/ODBC na Fedrizzi; não pedir configuração ou
credenciais novamente. Só confirmar modalidade local/Web para outra instalação
ou mudança informada. D-73 mantém métricas e aprovador já decididos. D-295
resolve o aceite NFS-e de Q-39; o layout contábil de PC-19 tem aceite próprio.

Cada pergunta tem uma única definição acima. Esta tabela apenas atribui dono e etapa. O responsável pelo projeto responde produto, política, ambiente e autorização; o executor levanta fatos técnicos primeiro. Pedir acesso em meio protegido, nunca conteúdo de credenciais.

| Grupo / IDs | Responsável pela resposta | Etapas afetadas | Estado |
|---|---|---|---|
| Comercial: Q-01–Q-06 | Já decidido | 02, 10 | Resolvido por D-76/D-79; operacionalização e homologação na etapa 10 |
| Catálogo antigo: Q-07 | Já decidido | 06, 11 | Resolvido por D-43 |
| Limites e egressão: Q-08, Q-09 | Responsável pelo projeto | 05, 06, 10 | Aberto |
| Rota futura: Q-10 | Já decidido | 05, 13 | Resolvido por D-50/D-51 |
| Governança da chave: Q-11 | Responsável pelo projeto, com levantamento técnico do executor | 05, 12 | Aberto |
| Caixas e corte: Q-12–Q-14 | Responsável pelo projeto / administrador do ambiente indicado | 06 | Regras e homologação abertas; configuração existente não é aprovação |
| Catálogo e arquivo: Q-15–Q-21 | Responsável pelo projeto / contador indicado | 06 | Aberto; automação em princípio aprovada por D-55, critérios específicos não |
| Destino e retenção: Q-22–Q-25, Q-31 | Responsável pelo projeto / administrador do ambiente indicado | 03, 06, 12 | Aberto |
| Integrações auxiliares: Q-26, Q-27 | Responsável pelo projeto | Futuro; fora do recorte inicial salvo nova decisão | Não bloqueiam os módulos atuais por inferência |
| Ambientes e amostras: Q-28 | Proprietário / administrador Fedrizzi indicado | 01–10, 12 | Parcial: Fedrizzi disponível por D-72; acesso seguro e amostra por integração ainda serão definidos |
| Suporte, e-mail e termos: Q-29 | Responsável pelo projeto / profissional indicado | 02, 12 | Aberto |
| Métricas e aceite: Q-30 | Proprietário do projeto | 01, 04–13 | Resolvido por D-72/D-73; exigir evidência da métrica aplicável antes de liberar |
| Pacote Windows: Q-32 | Já decidido | 03 | Resolvido por D-80; validar implementação e homologação |
| Contrato Siescon: Q-33 | Já decidido | 04 | Resolvido por D-290, com o limite de layout inferido |
| Curadoria: Q-34 | Responsável pelo projeto | 05, 13 | Aberto |
| Infraestrutura: Q-35 | Responsável pelo projeto, após inspeção dos recursos disponíveis | 01, 12, 13 | Aberto |
| Parcelamentos: Q-36 | Responsável pelo projeto | 08 | Aberto antes de ampliar |
| Imagem de treinamento: Q-37 | Já decidido | 01, 05, 13 | Resolvido por D-71; não bloqueia o build do runtime |
| Rentabilidade — receita: Q-41 | Responsável pelo projeto / contador indicado | 14 | Aberto; bloqueia a margem, não o custo |
| Rentabilidade — cobertura e cópia: Q-42 | Responsável pelo projeto | 14, 11 | Aberto antes de publicar a tela |
| Rentabilidade — comercial: Q-43 | Responsável pelo projeto | 14, 10 | Aberto; módulo entra sem preço |
| Rentabilidade — Siescon: Q-44 | Já decidido | 04, 14 | Resolvido por D-290; resolve também Q-33 |
| Rentabilidade — conector: Q-45 | Já decidido | 03, 14 | Resolvido por D-289 |

Não reapresentar toda esta lista a cada etapa. Perguntar apenas o necessário para a ação seguinte que não possa ser resolvido por inspeção nem pelas decisões existentes. Atualizar o ID original quando respondido, com referência ao novo registro D.
| Q-38 | Onde estará o backup Domínio Web `.dom` autorizado para contingência e qual será o canal seguro da chave correspondente? | Etapa 12: D-82 transferiu a homologação do backup para a liberação final. Recomenda-se usar um único backup de teste em pasta temporária e chave por canal seguro; o agente nunca registra nem exibe a chave. |

| Q-39 | Qual importador, layout/versionamento, pasta por empresa/competencia e retorno verificavel da rotina Domínio devem ser homologados para NFS-e e acumuladores? | Etapas 07 e 12: bloqueia transformar o pacote de conferencia em arquivo importavel ou registrar importacao concluida. Enviar somente documentacao tecnica e uma amostra descartavel pelo canal seguro; nao enviar backup, dados de clientes ou credenciais no chat. |
| Q-40 | Na central, o PDF válido conclui somente a atividade Emitir guia, deixando conferência e pagamento separados quando previstos nos modelos, ou a tarefa de emissão exige também conferência humana? | Pergunta enviada ao proprietário em 24/09/2026. Recomendação: separar os três trabalhos; não implementar a conclusão dependente sem resposta. Não altera a definição do adicional de reemissão ainda pendente em D-149. |

## Continuidade Q-28/Q-46/Q-47 — D-309/V-310 (04/11/2026)

O responsável autorizou pesquisar e escolher o recorte na Fedrizzi por leitura.
Foi selecionado candidato de uma empresa/conta bruta, janeiro/2026, com 115 itens
no extrato escolhido; identificadores ficam na evidência privada ignorada.
Não repetir a pergunta pelos identificadores já pesquisados. Ainda confrontar
conta bancária e fechamento; zero itens reais independentes homologados.
O recorte não autoriza envio da carteira ou infere Razão a partir de extrato.

Q-28 mantém pareamento/destino concreto e fonte independente. CA/ingresso
hospedados continuam sem validação: cadastro retorna 503. CLI Mac/Windows não
acessa o app; o responsável confirmou nesta conversa que **ainda não tem esse
acesso Fly**. Não solicitar novamente senha, DSN ou essa sessão nesta rodada.
Preparação local de configuração/retorno está na etapa 12; não houve deploy.
Q-46 mantém exemplos e semântica de parcelas/baixas/parciais/DE-PARA; Q-47 mantém
layout/importação Domínio conferida. Títulos Domínio e relatório + arquivo de
importação já estão decididos; Q-08/Q-09 continuam a reger IA real.

## Atualização Q-28 — D-310/V-311 (04/11/2026)

O responsável dispensou CA privada/certificado de cliente. Pareamento novo
usa HTTPS + HMAC e não exige essa infraestrutura; o certificado HTTPS normal
do servidor continua validado. Não reabrir a escolha ou pedir contratação.
Backend e MSI 1.0.3 preparados/testados; falta sua publicação/instalação real.
O responsável continua sem acesso Fly; não repetir a solicitação nesta rodada.
Destino/recorte/fonte independente e demais condições Q-28/Q-46/Q-47 não mudam.

## Continuidade Q-28/Q-46/Q-47 — D-311/V-312 (05/11/2026)

O responsável esclareceu que os documentos de Razão/títulos/parcelas/baixas
solicitados ainda não existem como arquivos. Não solicitar novamente caminhos
em Downloads. Foi localizado o plano de contas e preparada extração privada,
sem assumir código reduzido/classificação, atividade ou contas lançáveis.
Relatórios bancários não substituem a fonte Domínio.

RDP está acessível; login Domínio realizado diretamente pelo responsável.
Ele autorizou atualização oficial e confirmou backup concluído/recuperável.
O iniciador não encontrou `atualiza.exe` na rede, e o ajuste exigia 10.6A-10
completa. Essa versão foi baixada do fornecedor, assinatura válida conferida e
instalação base concluída, sem extras de nuvem/acesso remoto. Ajuste 2 concluído.
Reabertura pediu nova autenticação, senha vazia: login direto solicitado ao
responsável na janela preparada; não pedir credenciais no chat. Não repetir
pedido de backup/pacote. Desenvolvimento obtém os
relatórios do recorte já autorizado e contadora revisa
campos/chaves/sinais/baixas e exemplos. Não repetir pedido de DSN/credenciais.

Contrato normalizado offline de títulos e DE-PARA determinístico em rascunho
preparados/testados, sem SQL novo/IA externa. Q-46 mantém exemplos/semântica
e alocação real; Q-47 mantém layout/importação conferida. Q-08/Q-09 permanecem
para IA real. Publicação/Fly não foi solicitada novamente ou realizada.

### Continuidade Q-28/Q-46/Q-47 — D-312/V-313

Novo login concluído; não solicitá-lo novamente por esse estado histórico.
Razão do candidato original emitido e PDF observado no Windows. Conta contábil
identificada na consulta de extrato; fechamento exibido 11/2023 e controle de
títulos desmarcado. Transferência/extração e revisão semântica pendentes.
Responsável autorizou procurar outro recorte na Fedrizzi somente leitura.
Alternativa possui menu de títulos e fechamento fiscal 09/2026, porém contábil
11/2014; pesquisa ainda não homologa competência. Não alterar fechamento,
parâmetros ou parcelas. Não repetir DSN, credenciais, backup ou caminhos antigos.
Prévia offline e CLI validam capacidade/escopo, sem resolver regras e fluxo
persistido Q-46 ou importação Q-47. Os mesmos IDs continuam abertos.

A alternativa emitiu A Pagar; PDF conferido no Windows, sem cópia Mac/extração.
Não apresenta chave de baixa, conta bancária ou data efetiva de pagamento na
visão consultada. Cinco consultas limitadas de emissão/recebimento/pagamento/
situação parcial retornaram sem dados, conforme V-313; isso não prova ausência
geral. Desenvolvimento ainda obtém fonte com chaves/baixas e recorte fechado;
contadora revisa componentes/regras. Nenhuma nova pergunta ou autorização de
escrita, transmissão ou homologação foi inferida dessa pesquisa somente leitura.

Publicação D-313/V-314: responsável autorizou enviar código à main, realizado
no commit 4fede1e com SHA remoto conferido. Isso resolve a autorização de
commit/push dessa entrega; não resolve acesso/deploy hospedado, Q-28/Q-46/Q-47,
IA Q-08/Q-09, corpus real ou aceite. Não perguntar novamente essa autorização
de Git para o código e seus registros; não ampliá-la para dados/ERP/implantação.

V-315, Q-28/Q-46/Q-47: os anexos PDF/OFX Sicredi permitem testar a etapa
bancária da CONTAD. Reconferência local: 163 movimentos correspondentes e
saldos coerentes. A ausência de Razão/títulos revisados limita a homologação
contábil completa, não o início desses testes. Não solicitar novamente os
extratos já disponíveis nem contar seus dois formatos como amostras distintas.

D-314/V-316: responsável autorizou prosseguir; percurso bancário local executado
com os anexos e 42 verificações finais aprovadas. Q-28/Q-46/Q-47 continuam para
fontes contábeis/baixas, regras revisadas e importação conferida, sem bloquear
essa prova já concluída da entrada bancária. Nenhuma pergunta repetida de
extratos, login, DSN, backup, CA ou Fly nesta execução.

## Continuidade Q-28/Q-46/Q-47 — D-320/V-322 (06/11/2026)

Não repetir escolhas: serviço único .NET, HTTPS/HMAC, app Fly existente, arquivo
sem importação efetiva e prévia privada não homologada. Acesso Fly agora funciona.
AnyDesk disponibilizado, controle nativo falhou e responsável escolheu testes
guiados. No PC CONTAD informou MSI 1.0.3 íntegro, Running/Automatic e estado
awaiting_configuration. SQL Anywhere 17 é a versão do DSN original x86; faltam
DSN de sistema x64 e credencial de integração somente leitura, que ele confirmou
não possuir. Próximo responsável técnico deve configurá-los diretamente no PC;
não pedir senha no chat, ler segredo do registro ou recriar o DSN original.

CONTAD é escritório distinto de Bianchi/Cobalchini, conforme confirmação. Cadastro
próprio ae13d06f-6461-43a8-a9cc-3e0e0eafde50 provisionado em activation_pending,
sem membros/ativação; futuro login indicado em evidência privada. Não pedir
novamente qual escritório ou e-mail. Q-28 mantém ativação/acesso, recorte de
empresa/conta/competência/IDs autorizados e fonte independente real antes de
parear/enviar; não habilitar carteira inteira. Backup/retorno hospedado ainda não
confirmado: responsável não sabe sua configuração, API Neon sem acesso e storage
não informou versionamento. Não presumir que não há backup externo ou que foi
restaurado. Q-46 mantém exemplos/regras de títulos/baixas/DE-PARA; Q-47 mantém
layout/importação conferida em autorização posterior, sem escrita direta ERP.
