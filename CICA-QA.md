# CICA — guia funcional e roteiro de QA

**Atualizado em 09/10/2026.** Este documento orienta a exploração e o registro de defeitos do CICA. Descreve as funções encontradas no repositório e as decisões vigentes; não é certificado de homologação, manual fiscal nem promessa comercial. Antes de testar uma release, confira o [plano mestre](PLANO-MESTRE.md), as [decisões](DECISOES.md), as [validações](VALIDACOES.md) e a [etapa pertinente](docs/planejamento/etapas/README.md). Uma tela existente, uma demo e um teste local não provam uma integração real.

## 1. O que é o sistema

CICA é a central de trabalho de escritórios contábeis da Mewstack. O objeto principal é o **escritório**; dentro dele, pessoas trabalham em uma **carteira de empresas**, por **competência**, área, responsável, prazo e evidência. A operação reúne atividades e fechamentos, documentos fiscais, guias, DTE, parcelamentos, conciliação, Triagem, Radar, Copiloto e, sob habilitação específica, Rentabilidade por Cliente. O console `/platform/` pertence à Mewstack e administra escritórios e configuração central; `/app/` é a área do escritório.

O SaaS usa Django; tarefas assíncronas usam Celery; produção usa Fly para aplicação/worker e Neon para bancos principal e `knowledge`. O agente único `.NET 8` no Windows lê fontes locais autorizadas (Domínio e base técnica Siescon), transmite pelo protocolo autenticado e pode apoiar destinos locais. APIs ficam sob `/api/v1/` e `/api/agent/v2/`. A arquitetura e os limites de segurança estão em [arquitetura](docs/pt-BR/arquitetura.md), [segurança](docs/pt-BR/seguranca.md) e [agente Windows](agent-windows/README.md).

### Vocabulário que muda o resultado esperado

| Termo | Leitura para QA |
|---|---|
| Competência | Mês a que o trabalho ou dado pertence. Não confundir com vencimento; um trabalho da competência M pode vencer em M+k (D-277). |
| Carteira | Empresas a que a pessoa tem acesso. Alterar URL, filtro, job ou download não deve ampliar esse conjunto. |
| Evidência | Documento, observação ou decisão ligada ao trabalho, com origem e histórico. Uma tela “concluída” precisa da prova exigida pela sua regra. |
| Fonte | ERP, fornecedor, caixa, documento ou ação humana que sustenta um estado. Fonte ausente ou atrasada não pode parecer confirmação. |
| Demo | Dados e ações fictícios isolados por sessão. PDF/XML da demo devem ser identificáveis como fictícios. |
| Implementado / validado / publicado / homologado / liberado | Estados distintos. Use a matriz do plano mestre e um ID V da release exata; não derive um do outro. |

## 2. Ambientes, acesso e dados de teste

Para subir localmente, siga o [README](README.md#iniciar-no-pc-local). Ele usa `uv`, migrations nos bancos `default` e `knowledge`, `runserver` e, opcionalmente, `seed_demo`/`seed_personas` **somente com DEBUG**. O ambiente SQLite permite navegação e testes locais; rotinas com concorrência, fila, integração ou restauração exigem ambiente equivalente ao de produção e autorização própria. Não use credenciais, certificados, XMLs, documentos ou dados de cliente em fixtures, screenshots ou tickets sem autorização específica. Nunca copie segredos para o relatório.

Entradas úteis: `/` página pública, `/demo/` demonstração, `/entrar/` login, `/comecar/` cadastro, `/app/` visão geral, `/platform/` console, `/api/docs/` documentação de API quando habilitada. A demo não substitui um escritório real; a Fedrizzi é parceira interna de homologação sem contrato comercial (D-170), mas essa condição não libera automaticamente IA, Serpro, transmissão ou cobrança.

Antes de cada rodada, anote: commit/tag e release publicada, banco/ambiente, escritório, perfil, módulos habilitados, empresa, competência, modo demo/real, fontes e flags ativas, worker/Beat/agente e permissões de suporte. Rode integrações externas somente no ambiente autorizado, com dados e custo aprovados.

## 3. Perfis e fronteiras de acesso

O modelo de membro do escritório contém **Dono, Administrador, Gestor, Operador, Membro, Financeiro e Auditor**. Há papéis próprios no console e sessões de suporte com escopo, prazo e modo somente leitura ou escrita autorizada. A função visível depende do papel, módulo contratado/habilitado, vínculo com a empresa e estado do escritório. Dono/administrador têm visão local ampla; colaborador precisa de atribuição ativa à empresa; auditor deve conseguir consultar sem controles de alteração. O suporte somente leitura pode consultar acervo já autorizado, mas não classificar nem produzir exportação derivada (D-276). Confirme permissões no servidor, incluindo POST, API, downloads e tarefas em fila; esconder botão não é teste suficiente.

Para cada função abaixo, repetir ao menos: usuário permitido, papel consultivo, colaborador sem vínculo, vínculo revogado durante a operação, empresa de outro escritório, módulo desligado e sessão de suporte somente leitura. Resultado esperado: nenhuma leitura ou mutação fora do escopo; erro sem revelar a existência do recurso alheio (D-226).

## 4. Funções e casos essenciais

### 4.1 Cadastro, entrada e equipe

**Onde:** `/comecar/`, `/entrar/`, `/mfa/`, `/app/equipe/`, `/app/configuracao/`, `/app/configuracoes/`, `/platform/`.

- Cadastro do escritório, confirmação de e-mail, convite/ativação, login, recuperação de senha, MFA e códigos de recuperação. Teste token válido, expirado e reutilizado; tentativa repetida, bloqueio de login, troca de escritório e retorno à página correta. O transporte real por Brevo/DNS ainda exige prova de entrega e recuperação administrativa.
- Equipe: convidar, reenviar/revogar convite, atribuir/revogar acesso a empresas, alterar papel e desativar. Conferir carteira extensa, homônimos, busca/paginação, ações concorrentes e revogação imediata em telas e jobs.
- Console: estado dos escritórios, módulos, configurações centrais, suporte auditado e parceiro interno. Contrato manual, suporte e ativação não podem conceder acesso externo ou consumo por inferência.
- Configuração inicial e conectores: passos só ficam concluídos quando o predicado real foi atendido. Uma fonte reativada volta a “não configurada”, preservando histórico, sem disparar consulta (D-160).

### 4.2 Visão geral, busca, avisos e trabalho diário

**Onde:** `/app/`, `/app/busca/`, `/app/avisos/`, `/app/atividades/`, `/app/atividades/modelos/`, `/app/atividades/<id>/`.

- A Visão geral mostra pauta e prioridades; cartões de prazo e exceção filtram a fila. Conferir se contagens, lista, competência e link usam o mesmo recorte; zero não deve parecer alerta. “Meu trabalho”, carteira/gestão e fechamentos por competência não são o mesmo conjunto.
- Busca global e avisos internos respeitam carteira e módulos, deduplicam eventos e conduzem ao item certo. Não esperar e-mail ou WhatsApp desta função (D-277).
- Atividades: filtros na URL, prioridade, prazo interno/legal, responsável, situação, origem, próxima ação, notas, evidências, impedimento, assumir, reagendar e concluir. Entrada inválida deve preservar campos; concluídas aparecem mediante filtro explícito. A conclusão exige condições e revisão, e o histórico não é apagado.
- Lote: atribuir, alterar prazo interno ou concluir até **50 itens**, com motivo; revalidar permissão e pré-condições item a item e devolver itens pulados com causa. Na demo, a ação vale apenas na sessão (D-277).
- Modelos/recorrência: criação, pausa/retomada, atribuição, geração mensal idempotente e competência × vencimento. Modelos reais, responsáveis, prazos e cobertura ainda precisam de aprovação do escritório. Ausência de modelo não é fechamento completo.
- Fechamentos: empresa × competência × área; diferenciar exceção, pendência, requisitos comprovados e cobertura não configurada. Tarefa concluída ou guia emitida não equivale, isoladamente, a obrigação aceita ou pagamento.

### 4.3 Empresas, certificados e agente

**Onde:** `/app/empresas/`, ficha da empresa, `/app/certificados/`, configurações do Domínio e agente Windows.

- Empresas: cadastrar, pesquisar, filtrar, abrir ficha, editar dados locais (regime, IE, IM, contato e responsável por área), verificar código Domínio, vínculo e estado pausado. Filtro inválido devolve vazio com recuperação; erro do cadastro preserva valores. Empresa pausada conserva histórico NFS-e consultável (D-225).
- Ficha: próximos passos, atividades, evidências, notas, guias, fontes e módulos permitidos. Teste empresa com e sem fonte, homônimos, matriz/filial, documento repetido e empresa de outro escritório.
- Certificados A1: importação por metadados, lote e fila de não reconhecidos; arquivo ou senha inválidos não são guardados como certificado ativo. Ter A1 válido prepara a coleta; não comprova consulta ADN ou autorização para outra empresa.
- Agente: instalação, pareamento mTLS, catálogo de consultas por hash, leitura allowlisted, checkpoints, revogação, rede indisponível, atualização **manual** e conferência do destino/arquivo por hash. Domínio Local/Web/backup têm capacidades diferentes. Siescon usa layout inferido e ponte ODBC x86; leitura e exportação reais seguem sem homologação completa. O agente não escreve no ERP.

### 4.4 NFS-e e revisão fiscal

**Onde:** `/app/nfse/`, fila, `/app/revisoes/`, detalhe de revisão e histórico de pacotes.

Percurso: A1 autorizado → coleta ADN por NSU e empresa → XML original imutável → classificação por regra/backup ou revisão humana → acumulador efetivo → seleção → pacote de conferência → importação e retorno do Domínio quando homologados. A coleta real já opera em produção, com checkpoint, deduplicação e fila por empresa; isso não encerra o piloto fiscal nem Q-39.

- Teste competência, empresa, busca, classificação, paginação, indicadores, relatórios e links no **mesmo recorte**. Estado sem notas deve explicar como recuperar sem sugerir coleta quando o filtro apenas zerou o resultado.
- Verifique número fiscal, contraparte, original, sugestão, decisão humana, confiança e trilha append-only. Reprocessar backup não pode trocar decisão humana; segunda execução idempotente não cria registros.
- O **ZIP de XMLs originais** usa o filtro e não injeta acumulador. O **pacote classificado** usa a seleção declarada (nota, página, empresa ou todos do filtro) e a cópia derivada leva uma única tag `infNFSe/valores/acum`, sem `ACU`. Os arquivos têm nomes e propósitos distintos. Confira hash do original, quantidade, empresa e conteúdo do ZIP.
- Download do pacote, confirmação de importação, rejeições e protocolo devem preservar vínculo. Até Q-39 ter importação real conferida no destino, rotule o ZIP como **pacote de conferência**, nunca importação homologada.
- Falhas: A1 ausente/expirado, pausa, NSU repetido, timeout, worker/rede indisponível, classificação ambígua, acum inválido, seleção escondida em grupos recolhidos e lote parcialmente importado.

### 4.5 Central Integra Contador: DTE, DCTFWeb, guias e parcelamentos

**Onde:** `/app/integra-contador/`, `/app/integra-contador/dte/`, `/app/integra-contador/parcelamentos/`, `/app/guias/`.

- **DTE:** selecionar empresas, preparar consulta e custo, acompanhar fila/páginas, abrir resumo local e detalhe. O resumo não produz ciência; abertura oficial que pode produzi-la exige consentimento e trilha distintos. Resultado incerto não deve ser repetido cegamente.
- **DCTFWeb e guias:** empresa/competência, apurações da folha, preparo, consulta, declaração, recibo, emissão, histórico de tentativas, documento/PDF e download. Separar consulta, transmissão, aceite, emissão e pagamento; nenhuma dessas ações implica automaticamente as demais.
- **Parcelamentos PARCSN:** empresa → acordo → parcela → DAS. Conferir cotação/autorização de consumo, execução individual/lote, estado do fornecedor, PDF persistido e histórico. PDF demo deve ser inequivocamente fictício. Modalidades além do PARCSN ordinário dependem de Q-36.
- Serpro, credenciais, contrato, tarifa e operação real ainda requerem homologação por serviço; D-149/Q-40 bloqueiam a interpretação automática de resultados incertos. Testar permissão, custo, repetição, timeout, retorno fora de ordem e revogação antes da fila executar.

### 4.6 Triagem de arquivos

**Onde:** `/app/triagem/`, conexões de caixa, detalhe, prévia, destino e histórico.

Percurso pretendido: e-mail autorizado → anexo recebido → quarentena/scan → extração e classificação → correção humana de empresa/tipo/competência/destino → arquivo confirmado em biblioteca ou Windows → checklist. O código tem leitores IMAP/Graph/Gmail, política de arquivo, fila, revisão e arquivamento validados localmente; o encadeamento completo com caixa, scanner, regras e destino reais continua aberto (PC-15/16).

- Conectar caixa não inicia leitura automaticamente. Teste consentimento, revogação, cursor, mensagem repetida, parte repetida, anexos com mesmo hash, conta sem permissão e caixa indisponível.
- Antes de veredito seguro, binário fica em quarentena; prévia/download não podem servir arquivo inseguro. Campos ambíguos ou empresa desconhecida exigem correção, sem associação automática arriscada.
- Destino Windows exige raiz permitida, caminho seguro, confirmação de tamanho/hash e recuperação do agente offline. Checklist “recebido” só após arquivamento confirmado; arquivo rejeitado ou ainda em quarentena não fecha atividade.
- Catálogo, formatos, retenção, OCR/antimalware e pasta real dependem das Q-12–25/31. Reporte comportamentos atuais sem inventar a regra ausente.

### 4.7 Conciliação, folha, DRE, caixa e Radar

**Onde:** `/app/conciliacao/`, importação, mapeamento, auditoria, `/app/configuracao/mapa-dre/`, ficha da empresa e `/app/radar-reforma/`.

- **Conciliação:** importar arquivo, pré-validar linhas, revisar mapa, acompanhar execução, confrontar movimentos, resolver exceções, confirmar/desfazer, exportar e confirmar importação no ERP. Erro na entrada não grava lote parcial como concluído; duplicata concluída volta ao histórico. Exportar arquivo não é entrega conferida. Verifique trilha sem payload sensível bruto.
- **Folha:** importar fotografia, escolher competência, comparar totais (pessoas, bruto, descontos, encargos e líquido) de fontes compatíveis e explicar diferença a mais/menos. Comparação é leitura, sem cálculo de trabalhador ou conclusão automática. Layouts reais dependem de homologação.
- **DRE/caixa e relatórios:** mapa versionado, fonte/competência, comparação de períodos, fotografia, fila de PDF/XLSX e download ligado à fotografia. Sem dado ou renderizador, exibir indisponibilidade honesta; cenário não pode virar realizado.
- **Radar:** publicações oficiais como fila de triagem; filtrar fonte/tema/data, abrir fonte, analisar impacto e vincular empresa/motivo por decisão humana. Falha de coleta ou fonte desatualizada não deve parecer “nenhuma mudança”; não calcular impacto fiscal automaticamente.

### 4.8 Copiloto e aprendizado

**Onde:** `/app/ia/`, relatórios da conversa e `/app/ia/aprendizado/`.

- Conversa por empresa: pergunta/anexo → resposta com fontes e limites → feedback → relatório PDF/XLSX. Conferir isolamento de empresa/escritório, fonte verificável, resposta insuficiente, anexos maliciosos, pedido repetido, limite/custo e chamada com resultado incerto.
- Runtime local tem prioridade quando configurado; fallback externo exige opt-in e cotas. Chave central e uma geração sintética não homologam uso real. Copiloto fica oculto até política e limites permitirem; não acionar API paga em QA sem autorização aplicável.
- Aprendizado separa fonte operacional, candidato corrigido, aprovação humana, conjunto treino/avaliação, artefato, publicação e rollback. Feedback não deve virar exemplo aprovado ou modelo ativo sozinho. Q-08/09/11/34 e corpus real continuam abertos.

### 4.9 Contratos, cobrança e Rentabilidade

- **Contratação/cobrança:** console, contrato manual ou Asaas, medidor, fatura, tentativas, webhook e acesso. D-109 substitui a leitura comercial antiga de tokens por capacidade/usuários/raízes, IA em reais e custo efetivo Integra; consulte a decisão antes de afirmar valores. Teste emissão única, evento repetido/fora de ordem, pagamento, carência, estorno/disputa, suspensão somente leitura e reativação. Contrato manual não recebe efeito de webhook Asaas. Fluxo completo pagamento → acesso ainda requer homologação.
- **Rentabilidade por Cliente** (`/app/rentabilidade/`): visão geral, ficha analítica, colaboradores/custo, horas, análises e configuração. O cálculo segue contrato versionado; sem honorário, margem/resultado são ausentes, não zero. Com cobertura parcial de horas, não afirme lucro da carteira. O módulo não entra no cadastro nem na demo por padrão (D-288); console pode habilitá-lo caso a caso. Q-41–43, cobertura global de testes e ERP real impedem oferta/homologação.

### 4.10 Página pública, API, privacidade e operação

- **Página pública e entrada:** conferir links, proposta, cadastro, login, termos e indicação inequívoca de demonstração fictícia. Texto comercial deve acompanhar a capacidade liberada; não tomar a presença de uma função na landing como aceite do módulo.
- **API e agente:** repetir os casos de autorização e isolamento por endpoints, inclusive paginação, downloads e respostas de erro. `/api/docs/` descreve o contrato quando habilitado; verificar também autenticação, expiração/revogação, idempotência e limites. O agente não deve despachar consulta cujo código/hash diverge do catálogo ou cujo conector da origem está desligado (D-294).
- **Privacidade:** testar acesso, exportação, retenção, exclusão e restauração por artefato somente após política aprovada. Q-24/29 e PC-28 ainda exigem definição/execução; não apagar dado sujeito a obrigação de guarda por suposição. Tickets e logs devem usar identificadores seguros, sem segredo, dado fiscal bruto ou contato pessoal desnecessário.
- **Operação e suporte:** conferir liveness/readiness, worker/Beat, filas, alertas, logs higienizados, backup de bancos e documentos, restauração medida e rollback da release. Um deploy saudável da web não prova processamento, relatório, conexão Windows ou recuperação. O [runbook de incidentes](docs/pt-BR/runbooks/resposta-incidentes.md) e o [runbook de backup](docs/pt-BR/runbooks/backup-restauracao.md) guiam o ensaio.

## 5. Matriz transversal obrigatória

Aplicar a cada jornada modificada, além dos casos da seção 4:

| Dimensão | Verificações mínimas |
|---|---|
| Dados | Escritório vazio/pequeno/extenso; empresa pausada; nomes iguais; matriz/filial; competência anterior/seguinte; registros incompletos. |
| Estados | Inicial, carregando, vazio, parcial, erro, indisponível, incerto, concluído; recuperação e nova tentativa sem duplicar. |
| Acesso | Papéis da seção 3; módulo desligado; suporte somente leitura; vínculo revogado durante job/download; outro escritório. |
| Integridade | Idempotência, concorrência, paginação sem corte silencioso, hash, trilha, protocolo, resultado no destino, reversão e auditoria. |
| Interface | Desktop, celular, paisagem, zoom, tema claro/escuro, teclado, foco visível, Escape, movimento reduzido, sem rolagem horizontal e console sem erro. |
| Operação | Worker/Beat/rede/agente fora, retomada, alerta, rollback, backup e restauração. Não inferir sucesso de um HTTP 200 isolado. |
| Custo | Escopo e consumo antes da ação, autorização registrada, retry sem dupla cobrança e recibo/histórico coerente. |

Para a liberação, D-73 pede amostra de **200 itens por fluxo automatizado**, precisão mínima de **95% onde aplicável**, zero duplicidade/associação errada/vazamento, retomada sem perda em até **15 minutos**, restauração de banco e documentos em até **4 horas** e processamento por empresa em até **5 minutos**, salvo dependência externa registrada. Cobertura e precisão são métricas separadas. Exportação requer importação **e conferência** no destino. Registre a versão e a amostra; não aplique percentuais a fluxo que ainda não tenha definição de medida.

## 6. Como registrar um caso de QA

Use um registro por comportamento observável:

```text
ID / título:
Ambiente, commit/release e data:
Escritório, perfil, módulo, empresa e competência (identificadores fictícios ou seguros):
Fonte e modo: demo, simulado, local ou integração real autorizada:
Pré-condições e configuração relevante (sem segredos):
Passos reproduzíveis:
Resultado esperado e decisão D/critério correspondente:
Resultado observado:
Evidência: captura, log higienizado, protocolo/hash, request ID, teste e horário:
Impacto: bloqueio de tarefa, dado incorreto, acesso, custo, recuperação ou apresentação:
Estado: aberto, corrigido, retestado ou bloqueado por dependência; responsável e próximo passo:
```

Defeito de segurança, associação entre empresas, duplicidade fiscal/financeira, falsa conclusão, perda de dado ou operação externa incerta merece prioridade crítica e preservação de evidência. “Não testado” e “bloqueado” nunca viram “aprovado”. Ao retestar, usar a **release exata** e percorrer a jornada afetada até o resultado final, incluindo o destino externo quando aplicável.

## 7. Fonte de verdade e limites deste guia

- [Plano mestre](PLANO-MESTRE.md): estado reconciliado, pacotes PC, critérios e matriz de liberação.
- [Decisões](DECISOES.md) e [dúvidas únicas](docs/planejamento/duvidas-abertas.md): regras aprovadas e dependências; não criar uma resposta no ticket.
- [Validações](VALIDACOES.md): o que foi realmente exercitado, em qual ambiente e com quais limites.
- [Manual de homologação externa](docs/planejamento/manual-homologacao-externa.md): roteiros por fornecedor e destino.
- [Etapas](docs/planejamento/etapas/README.md) e [auditoria de produto](docs/planejamento/auditoria-produto-2026-10-05.md): escopo restante e cenários de uso.
- [Rotas Django](src/apps/hub/urls.py), [IA](src/apps/intelligence/urls.py) e [Rentabilidade](src/apps/profitability/urls.py): inventário de entradas; autorização real está nas views/serviços e deve ser testada.

Este guia foi preparado por leitura documental e inventário de rotas em 09/10/2026. **Nenhuma jornada foi executada nesta elaboração**. O estado de produção pode divergir de alterações locais; reconcilie release e V correspondente antes de assinar um caso. Dúvidas Q abertas e planos PC não são funções homologadas.
