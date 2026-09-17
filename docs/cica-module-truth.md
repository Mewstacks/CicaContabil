# CICA — funções verificadas no código

> Registro histórico iniciado em 13/09 com atualizações pontuais posteriores; não usar esta tabela isoladamente como fotografia atual. O [plano mestre](../PLANO-MESTRE.md) e as [validações de 17/09](../VALIDACOES.md) são a referência vigente. Em particular, o novo domínio de Conciliação preserva fontes/layouts/lançamentos ([decisões específicas](reconciliation-module-decisions.md)); a descrição OFX abaixo é do fluxo legado. Triagem já possui leitores e arquivamento no código, sem homologação completa. Preservado como histórico, não como autorização de texto comercial.

Revisão iniciada em 13/09/2026 para impedir que a landing anuncie comportamento que a aplicação ainda não entrega. Este registro descreve o código atual; não equivale a homologação externa nem a aprovação comercial.

| Módulo | O que existe no código | Limite atual | Texto público permitido nesta etapa |
|---|---|---|---|
| NFS-e Inteligente | Cliente de distribuição ADN por NSU, mTLS com A1 por empresa, checkpoint atômico, deduplicação, retentativa, controles em lote, classificação determinística e revisão | Implementação validada com respostas simuladas; `NFSE_ADN_SYNC_ENABLED=false` até o piloto autorizado no ambiente restrito. Certificado, XML e resposta reais ainda não foram homologados | Ativar/pausar empresas, acompanhar a coleta, pesquisar XML recebido, classificar e revisar; anunciar captura externa somente depois do piloto |
| Guias e DCTFWeb | Lista por empresa, competência, vencimento, valor e estado; emissão com confirmação, reserva de consumo, fila e retorno | A emissão externa depende da configuração e homologação do Integra Contador | Organizar vencimentos e emitir guias com confirmação |
| Central Integra Contador | Preparação de consulta DTE para empresas selecionadas, autorização separada de consumo, execução em fila e caixa de mensagens | O contrato e as credenciais são centrais; disponibilidade externa ainda precisa de homologação | Consultar a Caixa Postal DTE em lote e acompanhar retornos |
| Conciliação OFX x Domínio | Importação OFX, descarte do arquivo original após normalização, cruzamento determinístico por empresa/data/valor e confirmação manual de ambiguidades | Depende do espelho de lançamentos do Domínio | Cruzar OFX com o Domínio e revisar divergências |
| Radar da Reforma | Coleta diária de Receita Federal, Ministério da Fazenda e Planalto, filtro de relevância e links para a fonte | Não calcula impacto por cliente | Reunir publicações fiscais relevantes de fontes oficiais |
| Copiloto CICA | Conversa vinculada a uma empresa; análise privada de PDF, imagem, TXT e CSV; consulta a conhecimento aprovado, catálogo, obrigações espelhadas e fila de revisão; sugestão de classificação por regra/histórico; rascunho revisável; evidências, feedback e relatório PDF/XLSX da resposta com fontes | Não responde uma visão geral de todos os clientes nem executa ações no banco externo | Analisar documentos e classificações de uma empresa, conferir fontes e exportar a análise |
| Triagem de Arquivos | Módulo, página vazia, modelos de domínio e grafo de estados; cadastro OAuth Microsoft/Workspace por escritório e caminho separado para Gmail pessoal central, com segredos cifrados; conexão Microsoft/Google e IMAP simulada/testada localmente; trabalho local não commitado contém protótipo manual | Substitui Jornadas. A entrada vendável é somente por e-mail; ainda faltam redirect HTTPS de produção, app Gmail pessoal verificado, homologação de caixas reais, homologação dos leitores incrementais Graph/Gmail/IMAP, proteção/análise e escolha operacional de biblioteca ou Windows. Conectar caixa não inicia recebimento. Não vender como fluxo pronto | Mostrar conexão guiada e declarar leitura/arquivamento em implantação |

## Regras para a landing

- Números e nomes exibidos em demonstrações são exemplos de interface, não resultados de clientes.
- Função parcial deve ser descrita pelo recorte que já funciona, nunca pelo fluxo futuro inteiro.
- Siescon permanece identificado como em homologação até uma validação autorizada.
- Nenhuma prova social é publicada sem texto, nomes e autorização definidos pelo responsável.
- O Copiloto nunca será representado como painel geral do escritório enquanto o serviço exigir uma empresa por conversa.
