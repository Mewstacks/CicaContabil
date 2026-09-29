# Roteiro do responsável para liberar o CICA

Atualizado em 23/09/2026. Este é o roteiro de ação para transformar o que já foi implementado e validado localmente em operação real. Ele separa o que depende de você, do fornecedor e do desenvolvimento. Não autoriza enviar credenciais pelo chat, contratar, publicar ou fazer chamadas cobradas.

Use junto do [manual de homologação externa](manual-homologacao-externa.md): aquele explica como homologar; este lista o material, decisões e responsáveis necessários para cada homologação acontecer.

## Faça primeiro: cinco ações que destravam o produto

1. **Siescon:** indique o contato técnico e entregue por canal seguro versão, meio autorizado de leitura, ambiente de homologação, identificador de empresa e layout de exportação/importação. Sem isso, Q-33 impede um adaptador real.
2. **Domínio Web / NFS-e:** separe backup completo descartável, entregue a chave por canal seguro e obtenha documentação/amostra da rotina automática de importação NFS-e. A leitura será uma fotografia única; backup e chave nunca entram em Git ou chat.
3. **Comercial:** aprove tabela de pacotes, usuários ativos, raízes de CNPJ, franquia de IA em reais, adicional, teto mensal e migração de contratos antigos. Sem esses valores, não se ativa cobrança ou migração de tokens.
4. **Piloto:** escolha duas empresas autorizadas e um responsável contábil e técnico. Uma deve ter contábil, fiscal e folha; a outra deve exercitar filial, exceção ou falta de dado.
5. **Governança:** nomeie dono de privacidade/IA, dono de e-mail/OAuth e quem aprova cada módulo para venda.

## Regra de entrega de material

- Segredos, certificados, backups e dados reais: cofre ou canal seguro do escritório. Nunca chat, Git ou ticket aberto.
- Prefira empresas descartáveis e documentos anonimizados. Para dado real indispensável, registre finalidade, autorização, retenção e pessoas que terão acesso.
- Para cada integração, entregue versão, ambiente, contato técnico, um caso de sucesso e um caso de erro. Isso evita implementação por suposição.

## 1. Produto, dados e operação

**Você decide:** responsável por dados, privacidade, suporte e aprovação; retenção de documentos, e-mails, texto extraído, auditoria e backups; quem pode baixar, corrigir, excluir e restaurar; política de IA e seus tipos bloqueados/mascarados; modelos reais de fechamento e dispensas; termos, política de privacidade, remetente e domínio de suporte.

**Entregue ao dev:** ata ou documento datado com regra, vigência e dono. Orientação verbal não cria configuração auditável.

**O dev faz:** configura modelos e políticas explicitamente, mantendo motivo, autor e evidência para exceções. Dados sem autorização não seguem para IA.

**Aceite:** cada modelo de fechamento corresponde à operação do escritório; uma exceção não apaga histórico; as políticas podem ser revisadas por escritório.

## 2. Domínio Local: operação, folha e DRE

**Você providencia:** servidor Windows de homologação, DSN somente leitura, operador, duas empresas conhecidas e janela sem alteração durante a comparação.

**TI/Domínio confirma:** versão, permissão de leitura, campos/objetos autorizados e como revogar o pareamento.

**O dev faz:** pareia o agente, lê incrementalmente apenas o permitido, registra origem e compara empresa, competência, saldo, folha e obrigação. Não há escrita no Domínio.

**Você valida:** os totais contra a tela do Domínio; fonte indisponível mantém última leitura marcada como desatualizada; revogação bloqueia nova sincronização.

**Aceite:** leitura sem escrita, amostras reconciliadas, auditoria e recuperação. DRE só é liberada quando plano de contas, saldos e mapeamento forem conferidos.

## 3. Domínio Web e NFS-e: fotografia única e histórico perfeito

**Você providencia:** backup completo descartável autorizado, chave entregue fora do repositório, duas empresas, XMLs NFS-e de teste e manual/arquivo aceito pela rotina automática do Domínio.

**Você obtém do Domínio (Q-39):** formato/versão do backup, abertura autorizada, origem/código/situação dos acumuladores, layout do importador, regra por empresa e competência, duplicidade e retorno consultável.

**O dev faz:** lê uma única fotografia no agente; envia somente acumuladores normalizados autorizados; vincula cada item à empresa, lote e fonte; preserva o livro imutável. Acumuladores cadastrados pela tela entram no mesmo histórico, com origem manual ou decisão humana.

**Você confere:** reprocessamento não duplica; códigos iguais em empresas distintas não se misturam; NFS-e sem regra explícita vai para revisão; baixar ZIP não marca importação.

**Aceite:** a rotina automática importa em homologação, devolve identificador/status/erro verificável e só então o CICA marca importação confirmada. Até isso, o ZIP é pacote de conferência, não arquivo importável.

## 4. Siescon

**Você pede ao contato técnico:** versão instalada, banco/mecanismo permitido, usuário somente leitura, ambiente de homologação, identificador estável de empresa, cursor/incremental e layout de exportação/importação.

**Não envie:** dump de banco ou senha. O contrato precisa dizer exatamente que dado pode ser lido e exportado.

**O dev faz depois do contrato:** cria apenas capacidades documentadas, mapeia cada entidade para o modelo CICA e mantém origem e versão. Dados que o Siescon não oferecer continuam indisponíveis, sem simulação.

**Você valida:** amostra contábil, fiscal e folha; resposta parcial, timeout, revogação e mudança de versão. Reprocessar leitura não pode duplicar atividades.

**Aceite:** dados conferem, empresa e cursor são estáveis, e exportação importada na homologação confere. Sem isso, a integração permanece bloqueada.

## 5. Serpro / Integra Contador

**Você providencia:** contrato habilitado, catálogo/versões, procurações de homologação, certificado sob cadeia de custódia, empresas de teste, tabela efetiva de custos e política do fornecedor para timeout/retry.

**Você decide:** recorte inicial de Parcelamentos (Q-36), transmissões do piloto e quem trata divergência de custo. A regra já aprovada é confirmação humana pelo usuário autorizado; não há segundo aprovador obrigatório.

**O dev faz:** registra serviço, versão, tarifa, efeito legal, procuração e idempotência; fixa conteúdo; pede aprovação; executa uma vez; guarda protocolo; trata timeout como resultado incerto até nova consulta.

**Você valida:** duplo clique, conteúdo alterado depois da aprovação, permissão expirada, timeout, retorno tardio e fatura do Serpro. Monitoramento jamais causa ciência oficial silenciosa.

**Aceite:** protocolo recuperável, sem repetição cega, custo por escritório sem margem CICA e demonstração das operações habilitadas pelo contrato.

## 6. E-mail, OAuth e Triagem

**Você decide:** caixa/pasta/label lida, data de corte, marcação/movimentação de e-mails, formatos e tamanhos, árvore de destino e retenção. São Q-12 a Q-25.

**Você providencia:** domínio HTTPS, administradores Google/Microsoft, caixa de teste, aplicativo OAuth por escritório quando aplicável, escopos mínimos e anexos de teste limpo, duplicado, multipágina e malicioso.

**Pesquisa confirmada:** o Google pode exigir verificação de escopos sensíveis/restritos e avaliação anual se dados restritos passam por servidor; use menor escopo necessário. No Microsoft Entra, permissões app-only/alto privilégio exigem administrador e o tenant pode restringir consentimento. Consulte [Google OAuth](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) e [Microsoft Entra](https://learn.microsoft.com/en-us/entra/identity-platform/permissions-consent-overview).

**O dev faz:** consentimento, isolamento por escritório, deduplicação, quarentena, eventos e revisão antes do arquivamento.

**Aceite:** revogação e falha de consentimento funcionam; arquivo inválido não entra na fila; anexo só conclui após destino confirmado; logs não expõem segredos ou conteúdo desnecessário.

## 7. Folha: dados necessários para ferramentas que ajudam de verdade

**Já implementado localmente:** fotografia agregada por empresa, competência e fonte; comparação explicável entre duas fontes; métricas ausentes; atividade de tratamento. Não calcula folha, não consulta eSocial/FGTS sozinho e não expõe trabalhador individual.

**Você entrega ao dev:** contrato de dados de cada origem: empresa, competência, totais de proventos, descontos, encargos, líquido, bases e rubricas agregadas, centro de custo se houver, fonte e instante de leitura. Para cada campo, informe significado, unidade, sinal e ausência.

**Você valida com DP/contador:** regras de variação, tolerâncias, calendário de férias/contratos, instrumentos coletivos e exceções aceitáveis. Crédito do Trabalhador usa resultados do Domínio e gera fila de exceções; não se reconstrói cálculo sem contrato de dados.

**Aceite:** alerta mostra regra, período, fontes, valores e caminho de tratamento; falso positivo pode ser justificado sem apagar histórico.

## 8. Relatórios JavaScript, DRE, caixa e reforma tributária

**Você providencia:** plano de contas, DRE de referência, mapa inicial conta-grupo-sinal, dois períodos autorizados, regras de ajuste gerencial e contador para conferir.

**O dev faz:** cálculo determinístico e apresentação Node/TypeScript com ECharts, Puppeteer e ExcelJS sobre fotografia versionada; não há fallback de saída financeira em Python.

**Você valida:** origem versus PDF/XLSX; conta sem mapa, estorno, sinal, competência e ajuste. Relatório incompleto sai preliminar, com fonte, atualização e pendências.

**Para caixa/reforma, você fornece:** saldo inicial datado, contas a receber/pagar, parcelas, tarifas, antecipações, devoluções, estornos, folha/provisões e retenções estimadas/comprovadas. Define também dono e frequência de atualização.

**Aceite:** simulação, projeção e realizado ficam separados; retenção não é deduzida duas vezes; crédito tributário não vira caixa antes de realizado; 13 semanas conferem com planilha de referência.

## 9. Comercial, IA e Asaas

**Você aprova antes de cobrar:** pacote e valor, usuários ativos, raízes de CNPJ, franquia de IA em reais, preço adicional, teto padrão/máximo, tratamento de contratos legados e vigência.

**Já implementado localmente:** capacidade por usuários ativos e raízes de CNPJ ativas; filial sem segunda unidade; preservação de histórico e consumo auditável. Tokens legados permanecem por compatibilidade até regra de migração aprovada; não se converte por equivalência inventada.

**Você providencia para Asaas:** sandbox, webhook assinado, contratos de teste e política de inadimplência. Qualquer custo exige sua aprovação específica quando houver preço/escopo conhecido.

**Aceite:** Pix, boleto, cartão, atraso, estorno, webhook repetido/fora de ordem e contrato manual passam; capacidade não causa cobrança surpresa; IA reserva antes de rodar e respeita teto.

## 10. Infraestrutura, segurança e piloto

**Você escolhe/aprova:** ambiente, domínio/HTTPS, armazenamento privado, banco, Redis/Celery, observabilidade, backup, dono de incidente, suporte e revogação de segredos.

**Você disponibiliza:** ambiente de ensaio sem produção, depois as duas empresas de piloto, linha de base do processo atual e agenda de teste.

**O dev faz:** deploy somente após aprovação de custo; ativa por escritório; mede erros, recuperação e desempenho; preserva evidências; permite desligar uma integração isoladamente.

**Você aprova no piloto:** tempo para identificar fechamentos, consultas evitadas, pendências antecipadas, retrabalho por divergência, tempo de DRE/caixa e alertas úteis. Metas comerciais só são definidas depois da linha de base.

**Aceite de venda:** tudo que for anunciado tem fluxo homologado, suporte e recuperação definidos, e limitações explícitas quando a fonte não estiver configurada.

## Ordem prática

| Ordem | Sua ação | Próximo responsável | Prova de saída |
| --- | --- | --- | --- |
| 1 | Nomear donos, políticas e piloto | Produto, DP e TI | Ata/política e contatos |
| 2 | Entregar Q-33 do Siescon | Técnico Siescon + dev | Adaptador e amostra conferida |
| 3 | Entregar backup Web e Q-39 NFS-e | Domínio + dev | Importação teste com retorno |
| 4 | Preparar Domínio Local e DRE | TI/contador + dev | Saldos e DRE reconciliados |
| 5 | Habilitar Serpro homologação | Serpro/contador + dev | Protocolos e custos conciliados |
| 6 | Configurar OAuth de teste | TI + dev | Consentimento/revogação e triagem |
| 7 | Aprovar pacotes e migração | Comercial/financeiro + dev | Tabela versionada e fatura simulada |
| 8 | Abrir sandbox Asaas e aprovar ambiente | Financeiro/TI + dev | Ciclo de cobrança de teste |
| 9 | Entregar folha e caixa agregados | DP/financeiro + dev | Alertas e projeções conferidos |
| 10 | Executar piloto e liberar módulos | Equipe do escritório | Registro de aceite e rollout |

## Como me acionar em cada marco

Envie somente o item deste roteiro, fornecedor/ambiente, versão da documentação e contato técnico. Para segredos ou dados, diga que foram depositados no canal seguro e onde o desenvolvedor autorizado os encontra. Assim eu implemento e valido a próxima parte sem você repetir contexto.

## Fontes internas

- [Dúvidas abertas e donos](duvidas-abertas.md): Q-08, Q-09, Q-11 a Q-25, Q-29, Q-33 a Q-36, Q-38 e Q-39.
- [Contrato NFS-e / Domínio Web](nfse-dominio-import-contract.md).
- [Siescon](etapas/04-siescon.md), [Integra Contador](etapas/08-integra-contador.md), [Cobrança](etapas/10-contratacao-cobranca.md) e [Homologação e venda](etapas/12-homologacao-venda.md).
