# Dúvidas que exigem resposta do responsável

Atualizado em 15/09/2026. Nenhuma opção abaixo é escolhida por este documento. As perguntas foram deduplicadas dos 16 itens do [plano inicial de triagem](../plano-triagem-documental.md), dos planos CL-01 a CL-04, do plano Codex CX-05, dos reviews CICA e das respostas recentes. Respostas já dadas constam em [decisões](decisoes.md); aqui estão os detalhes ainda insuficientes para especificar, vender ou ativar o comportamento.

## Contrato e cobrança

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-01 | Qual é a duração exata da carência Asaas e qual evento inicia sua contagem: vencimento, evento de atraso confirmado pelo provedor ou outro marco? Como pagamento tardio, estorno e disputa reativam ou voltam a suspender? | Define máquina de estados, tratamento de webhooks repetidos e política de acesso. Confirmado apenas “somente leitura após prazo de carência a definir”. |
| Q-02 | Em modo somente leitura, quais consultas e downloads continuam disponíveis, por quanto tempo e para quais papéis? Exportação, IA e emissão Serpro ficam bloqueadas? | “Somente leitura” exige fronteira por operação e preservação de dados; não pode ser deduzido do status atual da UI. |
| Q-03 | Para contrato manual com preço diferenciado, quem autoriza, altera e registra preço, período, desconto, forma e comprovante de pagamento? Quem decide e registra suspensão/reativação? | Separação manual/Asaas está confirmada, mas ainda não há processo completo e auditável. |
| Q-04 | Mantêm-se fechamento da competência dia 1, vencimento dia 10 e uma fatura com mensalidade + excedentes do mês anterior para todas as modalidades? Como funciona o primeiro mês parcial e mudança de plano? | O plano CX-05 registrou esses valores; a decisão Asaas/manual posterior não respondeu esses detalhes. |
| Q-05 | Quais preços publicados, franquias e tetos valem por módulo, empresa e serviço Serpro? Quando se pode autorizar excedente, e qual teto nunca pode ser ultrapassado? | `pricing.py` contém valores de código, não aprovação comercial; tarifas, cotas e aceite precisam ser congelados no contrato. |
| Q-06 | O teste de 14 dias continua sem cartão e com suíte completa sob Asaas? O cadastro manual também pode ter teste? | Condições registradas em documentação anterior, ainda sem fluxo de pagamento atual validado. |
| Q-07 | Jornadas deve permanecer como benefício incluído, ou função/telas/dados devem sair do produto? Como tratar contratos existentes que já incluem o módulo? | O responsável decidiu retirar Jornadas da oferta como módulo pago, mas deixou aberta a permanência funcional. O código ainda exibe preço e função. |

## IA e custo

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-08 | Quais tetos por solicitação/dia/mês e franquias por escritório valem para Copiloto e Triagem? Quem pode elevar ou revogar limites? | A chave/modelo e uma geração sintética real foram validados com `claude-sonnet-5`; isso **não** aprova o orçamento comercial nem libera escritórios. O roteador atual exige tetos positivos. |
| Q-09 | Que conteúdo dos anexos/documentos pode sair para Claude, por qual base contratual, com qual mascaramento, retenção e informação ao escritório/cliente? Há tipos que devem permanecer locais? | A decisão provisória cobre anexos da Triagem, mas privacidade, custo e política de egressão precisam ser fechadas antes do uso real. |
| Q-10 | Quando o PC local chegar, o modelo local substitui Claude como padrão? Claude fica fallback técnico, professor offline, ambos ou é removido? Quais critérios autorizam a virada? | Os planos mais antigos descrevem fallback/curadoria; a etapa atual mudou a rota primária. |
| Q-11 | Qual processo de rotação, teste e alerta para a chave central `CICA_CLAUDE_API_KEY`, sem revelá-la em interface/log? | A chave já está no `.env` e foi aceita na contagem gratuita; isso não define governança de produção. |

## Triagem: entrada, identificação e catálogo

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-12 | A caixa própria conectada lerá caixa inteira, pasta/label dedicada ou filtros? Quem no escritório concede consentimento e revoga? Haverá caixa compartilhada em etapa posterior? | Caixa própria está confirmada; CL-04 assumiu pasta dedicada explicitamente sem confirmação. |
| Q-13 | Quem na Mewstack registrará os apps OAuth centrais Microsoft/Google, qual domínio/redirect de produção será usado e quem conduzirá a verificação e eventual avaliação de segurança para `gmail.readonly`? | O mecanismo mais simples foi escolhido em [pesquisa oficial](conexao-caixas-email.md); registro/publicação, permissões reais e homologação ainda não ocorreram. |
| Q-14 | Qual data de início/corte para mensagens antigas, política de reprocessamento e de exclusão após ingestão? A CICA marca e-mail como lido, move mensagem ou só lê? | Cursor, deduplicação e risco de importar conteúdo histórico dependem da regra. |
| Q-15 | Confere a transcrição das 19 linhas da foto em [catálogo a confirmar](catalogo-triagem-a-confirmar.md)? “Contas recebidas” e “contas a receber” são categorias diferentes? Quais singular/plural/abreviações são oficiais? | Não transformar transcrição de reunião em migration/catalogue aprovado. |
| Q-16 | Qual é a árvore de destino completa por empresa e tipo? Como tratar mensal, anual, intervalo e múltiplas competências? Quais marcadores de banco/instituição/imobiliária/inquilino são usados? | Código Domínio na pasta e `MMYYYY`/`YYYY` não especificam a árvore completa. |
| Q-17 | Qual identificador dentro do documento autoriza vínculo automático além de CNPJ legível? O que fazer com CNPJ de matriz/filial, terceiros, documento sem CNPJ ou dois CNPJs? | CL-04 propõe CNPJ único; faltam casos reais e regra de revisão. |
| Q-18 | Quais campos obrigatórios e evidências prevalecem por tipo quando nome, conteúdo, remetente e pasta divergem? A confiança ≥98% por campo é requisito aprovado e qual precisão medida precisa ser atingida no piloto? | Número emitido pela IA não demonstra qualidade; automatização precisa de amostra de aceite. |
| Q-19 | Quais formatos/tamanhos/páginas/proteções são aceitos? CL-04 propôs 50 MB/PDF até 100 páginas e imagens/TXT; serviço local em andamento aceita upload manual de 25 MB e PDF/CSV/XML/OFX/XLSX. Qual contrato vale para anexo de e-mail? | Os dois contratos divergem e o fluxo manual não é entrada da primeira versão vendável. |
| Q-20 | Qual política para mesmo hash, nomes iguais de conteúdos diferentes, arquivo multi-documento, mais de um período e reenvio pelo cliente? Original é copiado, movido ou descartado? | Dedupe, versionamento, revisão e auditoria dependem disso; CL-04 registra somente parte da política. |
| Q-21 | Quais tipos de empresa esperam quais documentos por mês/ano, com dispensas, exceções e alterações de regra? | Checklist não pode ser inferido apenas das pastas; “recebido” conta após arquivamento confirmado. |

## Triagem: destino, segurança e integrações futuras

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-22 | Quais caminhos reais de entrada/raiz Windows, máquina, conta de serviço e modalidade local/UNC/unidade mapeada serão usados no piloto? Qual agente fará a escrita e como o escritório valida a raiz? | Pasta configurável pelo escritório ainda precisa de allowlist, teste de escape e confirmação de hash. |
| Q-23 | A escolha biblioteca/Windows vale para o escritório inteiro? Pode ser trocada, e o que acontece com arquivos já arquivados e backups? | A decisão confirma duas opções, não migração ou coexistência histórica. |
| Q-24 | Por quanto tempo guardar original, cópia, texto extraído, previsões IA, e-mail de origem e auditoria? Quem visualiza, corrige, baixa, exclui e restaura? | Privacidade, custo de armazenamento e recuperação não estão definidos. |
| Q-25 | Qual antimalware/OCR e política de quarentena/rejeição são exigidos, quem fornece ambiente e como será estimado/aprovado custo? | CL-04 descreve ganchos opcionais; produto vendável não pode presumir proteção ou custo. |
| Q-26 | Para BCB/RFB, cliente entregará relatórios obtidos de forma autorizada ou existe outro mecanismo documentado? Quem revisa divergências? Para “Open Files” do Domínio, qual nome/documentação e impedimento exatos? | São frentes auxiliares; o plano inicial não aprovou coleta automática nem inventou API. |
| Q-27 | WhatsApp de pendências terá qual conta/provedor, número, destinatários, consentimento, modelo, janela, cadência, descadastro e teto? | Fora da primeira versão de triagem; envio pago depende de confirmação específica de custo. |

## Lançamento e prova

| ID | Pergunta objetiva | Por que altera a implementação |
| --- | --- | --- |
| Q-28 | Qual ambiente e amostra autorizada serão usados para homologar Serpro, NFS-e ADN, Domínio local/Web e Siescon? Quais contratos/licenças estão disponíveis? | Testes simulados não provam autorização nem comportamento externo. |
| Q-29 | Quais contatos reais de suporte/privacidade, provedor SMTP, domínio/DNS de envio e termos finais serão aprovados? | Minutas e serviço de e-mail não equivalem a versão comercial homologada. |
| Q-30 | Quais metas operacionais autorizam liberar cada módulo: precisão, tempo de processamento, tolerância a falha, recuperação, restauração, carteira piloto e pessoa que dá aceite? | “Funciona” precisa de critérios observáveis antes de preço ou anúncio. |
| Q-31 | Para o componente Windows `Nome [Domínio código]`, o nome vem do cadastro CICA ou da razão social Domínio? Quando mudar, renomeia a pasta existente ou mantém o caminho anterior? | O componente seguro foi implementado sem escrever arquivos; usar automaticamente um nome de fonte errada ou mover uma pasta pode quebrar localização, histórico e backup. Pergunta enviada ao responsável em 15/09. |

As dúvidas nesta lista são independentes de autorização monetária. Quando uma decisão implicar chamada de API paga ou infraestrutura cobrada, apresentar provider, recurso, escopo, custo estimado e reversão para confirmação imediatamente antes da ação.
