# CICA — funções verificadas no código

Revisão iniciada em 13/09/2026 para impedir que a landing anuncie comportamento que a aplicação ainda não entrega. Este registro descreve o código atual; não equivale a homologação externa nem a aprovação comercial.

| Módulo | O que existe no código | Limite atual | Texto público permitido nesta etapa |
|---|---|---|---|
| NFS-e Inteligente | Classificação determinística de NFS-e já disponibilizadas à CICA, fila de baixa confiança e registro da decisão | Não há serviço ou tarefa de coleta externa; `NfseSync` ainda não é criado nem executado | Organizar, classificar, acompanhar e revisar NFS-e recebidas pela integração homologada |
| Guias e DCTFWeb | Lista por empresa, competência, vencimento, valor e estado; emissão com confirmação, reserva de consumo, fila e retorno | A emissão externa depende da configuração e homologação do Integra Contador | Organizar vencimentos e emitir guias com confirmação |
| Central Integra Contador | Preparação de consulta DTE para empresas selecionadas, autorização separada de consumo, execução em fila e caixa de mensagens | O contrato e as credenciais são centrais; disponibilidade externa ainda precisa de homologação | Consultar a Caixa Postal DTE em lote e acompanhar retornos |
| Conciliação OFX x Domínio | Importação OFX, descarte do arquivo original após normalização, cruzamento determinístico por empresa/data/valor e confirmação manual de ambiguidades | Depende do espelho de lançamentos do Domínio | Cruzar OFX com o Domínio e revisar divergências |
| Radar da Reforma | Coleta diária de Receita Federal, Ministério da Fazenda e Planalto, filtro de relevância e links para a fonte | Não calcula impacto por cliente | Reunir publicações fiscais relevantes de fontes oficiais |
| Jornadas | Criação de jornada com empresa, responsável, prazo, etapas e pendências persistidas | A CICA é de uso interno do escritório; não há acesso externo de clientes | Criar e acompanhar jornadas por empresa, responsável e prazo |
| Copiloto CICA | Conversa vinculada a uma empresa; análise privada de PDF, imagem, TXT e CSV; consulta a conhecimento aprovado, catálogo, obrigações espelhadas e fila de revisão; sugestão de classificação por regra/histórico; rascunho revisável; evidências, feedback e relatório PDF/XLSX da resposta com fontes | Não responde uma visão geral de todos os clientes nem executa ações no banco externo | Analisar documentos e classificações de uma empresa, conferir fontes e exportar a análise |
| Triagem de Arquivos | Módulo, página vazia, modelos de domínio e grafo de estados; trabalho local não commitado contém upload manual, revisão, storage privado e arquivamento interno | A entrada vendável confirmada é somente por e-mail; não há leitores Graph/Gmail/IMAP, proteção/análise e escolha operacional de biblioteca ou Windows. O schema foi aplicado no banco local até 0003. Não habilitar/vender como fluxo pronto | Nenhum texto público até o fluxo de e-mail e destino ser entregue |

## Regras para a landing

- Números e nomes exibidos em demonstrações são exemplos de interface, não resultados de clientes.
- Função parcial deve ser descrita pelo recorte que já funciona, nunca pelo fluxo futuro inteiro.
- Siescon permanece identificado como em homologação até uma validação autorizada.
- Nenhuma prova social é publicada sem texto, nomes e autorização definidos pelo responsável.
- O Copiloto nunca será representado como painel geral do escritório enquanto o serviço exigir uma empresa por conversa.
