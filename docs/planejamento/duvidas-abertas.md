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
| Q-33 | Qual versão/banco Siescon, mecanismo de acesso autorizado e documentação/layout de exportação serão disponibilizados? Qual identificador de empresa substitui o código Domínio nos fluxos exclusivos de Siescon? | Etapa 04: banco disponível e leitura/exportação revisada já estão decididos em D-53/D-54. Não pedir segredos no chat. |
| Q-34 | Quem revisa e aprova exemplos, correções e publicações de modelos de cada escritório? | Etapas 05/13: isolamento já decidido em D-49; métricas em Q-30, egressão em Q-09. |
| Q-35 | Qual ambiente já disponível recebe o SaaS/IA central e qual equipamento será usado para a IA definitiva? | Etapas 01/12/13: D-46 confirma centralização, mas não escolhe provedor, máquina, GPU ou modelo. Não contratar recursos por inferência. |
| Q-36 | O recorte inicial de Parcelamentos permanece PARCSN ordinário ou inclui outras modalidades? | Etapa 08: preservar implementação atual até resposta; o plano exige perguntar antes de ampliar modalidades. |
| Q-37 | Resolvida em 18/09: manter LlamaFactory como ferramenta interna de treinamento; referência técnica fixada por digest. | D-71. A imagem foi construída e o binário validado localmente. Nenhum treino, modelo, GPU ou gasto foi autorizado por essa decisão. |

## Donos, etapas e estado das perguntas

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
| Contrato Siescon: Q-33 | Responsável pelo projeto / técnico do fornecedor indicado | 04 | Aberto |
| Curadoria: Q-34 | Responsável pelo projeto | 05, 13 | Aberto |
| Infraestrutura: Q-35 | Responsável pelo projeto, após inspeção dos recursos disponíveis | 01, 12, 13 | Aberto |
| Parcelamentos: Q-36 | Responsável pelo projeto | 08 | Aberto antes de ampliar |
| Imagem de treinamento: Q-37 | Já decidido | 01, 05, 13 | Resolvido por D-71; não bloqueia o build do runtime |

Não reapresentar toda esta lista a cada etapa. Perguntar apenas o necessário para a ação seguinte que não possa ser resolvido por inspeção nem pelas decisões existentes. Atualizar o ID original quando respondido, com referência ao novo registro D.
| Q-38 | Onde estará o backup Domínio Web `.dom` autorizado para contingência e qual será o canal seguro da chave correspondente? | Etapa 12: D-82 transferiu a homologação do backup para a liberação final. Recomenda-se usar um único backup de teste em pasta temporária e chave por canal seguro; o agente nunca registra nem exibe a chave. |
