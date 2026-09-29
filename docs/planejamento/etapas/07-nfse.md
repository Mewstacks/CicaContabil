## V-132 - Acesso exclusivo NFS-e

- [x] Abrir a assinatura NFS-e exclusiva diretamente na central NFS-e.
- [x] Ocultar e bloquear a central de atividades e seus modelos nesse recorte, inclusive por URL direta.
- [ ] Repetir valida??o visual desktop e celular quando o Playwright MCP voltar a responder.

## V-131 - Acumulador manual seguro

- [x] Impedir que acumulador cadastrado sem crit?rio se torne classificador curinga.
- [x] Manter o acumulador manual no cat?logo e no hist?rico, enviando NFS-e sem crit?rio para revis?o humana.


## V-130 - Paginacao de pacotes

- [x] Paginar pacotes de conferencia acima de 100 registros, sem corte silencioso e com URL preservavel.


[Contrato tecnico de backup e importacao](../nfse-dominio-import-contract.md)

## V-128 - Pacote de conferencia ate contrato de importacao

- [x] Distinguir pacote de conferencia de arquivo importavel na tela, no modelo e no fluxo.
- [x] Bloquear confirmacao de importacao enquanto Q-39 nao tiver layout e retorno homologados.
- [ ] Obter importador, layout/versionamento, pasta por empresa/competencia, amostra descartavel e retorno verificavel conforme Q-39.


## V-127 - Historico unico de acumuladores

- [x] Preservar em evento imutavel a fotografia do backup, o cadastro manual e a decisao humana.
- [x] Exibir essas origens em um unico historico paginado por carteira, sem ocultar as fotografias legadas.
- [ ] Repetir validacao visual desktop e celular do historico quando o Playwright MCP estiver disponivel.


## V-126 - Fotografia Dom?nio Web e pacote para rotina

- [x] Registrar catalogo de acumuladores da unica fotografia permitida do backup, vinculado a empresa, fonte, lote e instante.
- [x] Permitir cadastrar acumuladores para classificacoes futuras e preservar decisao humana em evidencia e historico.
- [x] Gerar pacote privado versionado com XML, manifesto, hash e estados separados de download/importacao.
- [x] Recuperar a ausencia do arquivo privado sem registrar um download inexistente.
- [ ] Homologar layout de importacao e retorno automatico com a rotina Dom?nio autorizada; ate la, confirmacao e humana.

# Etapa 07 — Concluir NFS-e, certificados e revisão fiscal

[Plano mestre](../../../PLANO-MESTRE.md) · [Decisões](../../../DECISOES.md) · [Validações](../../../VALIDACOES.md)

**Estado:** A demonstração local de carteira, filtro e download em lote foi implementada e revalidada em V-005/V-035; V-064 tipou a sincronização ADN local e V-068 retestou os contratos locais da view de certificados. V-073 completou a evidência mostrada na revisão e paginou a carteira sem corte silencioso; V-078 estendeu a proteção à cobertura de empresas sem A1 válido. A etapa permanece em andamento para coleta e homologação reais.

**Dependências:** 03 e 05.

**Decisões relacionadas:** D-31, D-55, D-111.

## Escopo e checklist

- [x] Entregar demonstração de download em lote com ZIP fictício por empresa, `Tomadas/CÓDIGO -/` e `Emitidas/CÓDIGO -/` (D-62).
- [x] Permitir baixar toda a carteira e validar acumulador/confiança antes do ZIP: classificação acima de 95%; transitória em 0% (D-63).
- [x] Filtrar carteira por competência de emissão ou intervalo de emissão, mostrando emissão como referência da nota (D-64).
- [x] Permitir download demonstrativo sem bloqueio: transitória a 0%, decisão manual identificada e IA acima de 95% (D-65).
- [x] Oferecer uma escolha exclusiva entre filtro por competência e filtro por emissão na demonstração (D-66).
- [x] Atualizar visualmente a linha da demonstração ao definir acumulador, sem persistir decisão fictícia (D-68).
  - Implementação e inspeções locais registradas em V-005 e V-035. A etapa completa permanece aberta.
- [ ] Homologar coleta ADN, certificados, NSU, retomada e deduplicação.
- [x] Apresentar localmente nota legível, valores, referência pseudonimizada da contraparte, emissão/competência e descrição dos serviços (V-073). A fonte real continua pendente.
- [x] Validar acumuladores contra o catálogo da empresa. V-089 aceita na decisão humana somente regra ativa e vigente ou código já observado da mesma empresa, sem inferir tratamento fiscal.
- [x] Receber catálogo de acumuladores pela fotografia única de backup Domínio Web. V-125 aceita somente a capacidade allowlisted do agente e preserva empresa, lote, fonte e momento da fotografia; extrator real e arquivo autorizado continuam pendentes.
- [x] Exibir o histórico do catálogo por carteira na aba NFS-e Acumuladores, com paginação e estado vazio explícito (V-125).
- [x] Exibir evidência da sugestão e permitir correção local, preservando XML e auditoria da decisão (V-073).
- [x] Garantir acesso local à carteira sem cortes silenciosos: a lista pagina acima de 100 documentos e conserva os filtros (V-073).
- [x] Garantir acesso local à cobertura de empresas sem A1 válido: a lista pagina acima de 20 empresas sem interferir na carteira de certificados (V-078).
- [ ] Documentar cobertura e limitações efetivas da fonte de coleta.

## Bloqueios e responsabilidade

Q-28 e Q-30: certificado/ambiente autorizado, corpus e métricas de aceite.

Regras e autorização externa: responsável pelo projeto. Código, inventário e verificação local: executor da etapa. Os IDs Q apontam ao [registro único de dúvidas](../duvidas-abertas.md); não criar a mesma pergunta em outro documento.

## Testes e aceite

Certificado errado/expirado, retomada NSU, repetição, lote inválido, cobertura da carteira, acumulador inexistente e revisão fundamentada.

**Critério de aceite:** Nota real autorizada é coletada, conferida, classificada e rastreada sem duplicação ou associação à empresa errada.

## Evidências e próximo passo

V-068 incluiu a rota de certificados na regressão local de 119 testes, sem coleta
ADN, certificado ou documento real. V-073 exercitou a revisão normalizada, a
demonstração fictícia e a paginação da carteira em 79 testes e no navegador
interno; a regressão integral fechou com 763 testes, 3 skips e 11 subtestes.
V-078 acrescentou a paginação da cobertura de certificados, com 21 empresas
sintéticas no teste e inspeção no navegador de 25 pendências, inclusive em
390 px. V-079 paginou também o histórico NFS-e na ficha de cada empresa,
preservando o retorno à carteira. V-089 confirmou que código inexistente ou de
outra empresa não resolve uma revisão, enquanto regra vigente e histórico local
da própria empresa continuam selecionáveis. Nenhum A1, ADN ou documento real foi usado.
Nenhuma homologação nova é atribuída a esta etapa. A existência de
código ou testes anteriores não prova conclusão.
Registrar comandos, ambiente, data, resultado e limites em VALIDACOES.md e no
registro de execução. Não incluir segredos ou dados de clientes.

## Prompt de execução

> Execute a etapa 07. Complete e homologue NFS-e e revisão fiscal, da validade do certificado à decisão do contador. Valide o catálogo de acumuladores e a continuidade da coleta. Não confunda dados calculados, documento fiscal oficial e sugestão da IA.

> Leia PLANO-MESTRE.md, DECISOES.md, VALIDACOES.md e o arquivo da etapa antes de trabalhar. Não refaça decisões confirmadas. Pergunte ao responsável somente o que estiver ausente ou em conflito e documente a resposta antes de implementar o comportamento dependente. Preserve alterações existentes. Não incorra em custos sem aprovação específica imediatamente anterior. Ao terminar, atualize os .md com mudanças, testes executados, evidências, limitações, bloqueios e próximo passo. Não marque como homologado o que foi apenas simulado. Respeite o escopo autorizado na solicitação atual; a existência do próximo prompt não autoriza iniciar outra etapa.

### V-171 — Preservação de decisões sucessivas

- [x] D-153: nova resolução de revisão reaberta preserva evidência e acumulador anteriores; referência identifica a decisão exata.
- [x] Repetição da sincronização não duplica evidência; 85 testes correlatos passaram.
- [ ] Homologar o percurso real, exportação/importação e concorrência PostgreSQL; nenhum novo fluxo de reabertura foi criado ou aprovado nesta correção.

### V-202 — Catálogo real do backup e acesso NFS-e isolado

- [x] Isolar a navegação e as rotas do produto NFS-e para assinatura que habilita somente esse módulo; apoios de cadastros, certificados, equipe e configuração permanecem disponíveis.
- [x] Implementar no agente a leitura allowlisted de `bethadba.EFACUMULADOR`, paginada em 500 registros, para a capacidade existente `accumulator_catalog`.
- [x] Abrir tecnicamente o contêiner autorizado 07129, preservar o original e eliminar a extração temporária após o diagnóstico.
- [x] Ler e importar os acumuladores do escritório 07129 por usuário externo somente leitura criado pelo fluxo suportado do Domínio; V-209 confirma 208 empresas e 15.701 acumuladores em produção, sem erros ou duplicação.
- [x] Agregar e importar o histórico mínimo para reconhecer acumuladores por empresa, serviço e contraparte; V-210 confirma 49.199 observações únicas, pseudonimização na origem e zero órfãos.
- [ ] Homologar os acumuladores e o percurso fiscal com o responsável; V-202 não infere tratamento tributário nem declara o módulo fiscalmente homologado.
