# CICA × CONTAD — pendências para a conclusão (19/11/2026)

Estado: **uso assistido** (release v107 em produção desde 19/11, V-419). Esta lista substitui a tabela
de pendências do comunicado de 18/11 sem reabrir decisões já tomadas. A CONTAD só
será declarada concluída quando os critérios D-73 estiverem cumpridos: 200 itens
revisados pelo proprietário, precisão medida de pelo menos 95% onde houver
classificação automática, zero duplicidade/empresa errada/vazamento, retomada
sem perda em até 15 minutos e importação
conferida no Domínio.

Evidências privadas ficam fora do Git, em `.tmp/` das worktrees indicadas em
VALIDACOES (pastas 0700, arquivos 0600). Nenhum valor financeiro ou nome real
aparece neste documento.

## O que mudou nesta rodada (D-377/D-378, publicado na release v106)

- **Vínculo pelo OFX:** em *Contas do Domínio → Conferir vínculo*, o OFX da conta
  preenche banco e agência/conta no formato que a importação exige. Antes, uma
  referência digitada naturalmente (por exemplo “0101 12345-6”) seria aceita no
  vínculo e o primeiro OFX dessa conta seria recusado. A pessoa continua
  escolhendo o lado no Razão, a filial e as confirmações.
- **Amostra D-73 reprodutível:** `reconciliation_acceptance select` escolhe, com
  semente registrada, fatos bancários ainda não congelados de uma conta, prontos
  para `prepare` e para a ficha do proprietário.

## Pendências de terceiros

| Item | Responsável | Evidência pronta | Roteiro (até 5 passos) |
|---|---|---|---|
| A. Vínculos bancários (132 empresas com plano) | CONTAD (quem gerencia a conciliação) | Catálogo de 146 empresas/217.891 contas em produção; leitura do OFX validada em navegador (V-417) | 1. Escolher 5–10 empresas de setembro/2026. 2. *Contas do Domínio* → empresa → conta do banco → *Conferir vínculo*. 3. Anexar o OFX e *Ler banco e conta do extrato*. 4. Conferir o quadro lido, escolher o lado e marcar as verificações. 5. *Confirmar vínculo* e enviar o mesmo OFX em *Extrato e Razão*. |
| B. Q-47 — exportação para o Domínio | CONTAD (teste no Domínio) + CICA (liberação) | **Implementado na v107 (D-380/V-419):** arquivo .txt no leiaute oficial do Importador (conjunto 19), contas pelo plano do Domínio, prévia liberada para a CONTAD | 1. Num movimento ainda não escriturado, informar as contas (código reduzido), gerar e aprovar o lançamento. 2. *Arquivos e histórico → Prévia para conferência* e baixar a prévia. 3. No Domínio: *Utilitários → Importação → Importador*, Tipo TXT, conjunto “Lançamentos Contábeis em Lote (Leiaute Domínio Sistemas)”; importar e conferir. 4. Avisar a CICA. 5. CICA registra a liberação (`record_dominio_homologation --apply`) e a exportação definitiva passa a funcionar. Roteiro da chamada: [contad-teste-importacao-dominio.md](contad-teste-importacao-dominio.md). |
| C. C01/C02 — retenções e juros nos títulos | Grazi (CONTAD) | Sete exemplos privados V-379 íntegros; confronto técnico V-415 (C01: vbru−CRF−IRRF=vlor; C02: tipo 1 já inclui os juros do tipo 2); o sistema não soma componentes sozinho | 1. Abrir *Títulos e baixas* nas empresas dos exemplos. 2. Conferir C01 (retenções) e C02 (juros) contra o Domínio. 3. Dizer se a leitura técnica está correta. 4. Registrar a decisão em cada baixa pela tela. |
| D. DE-PARA | CONTAD | Duas sugestões válidas retidas; zero regras ativas; nenhuma nova chamada de IA | 1. Abrir *Revisão DE-PARA*. 2. Aprovar (ou recusar) as duas contas exigidas. 3. Só então revisar as duas sugestões e ativar manualmente, se for o caso. |
| E1. Amostra D-73 (200 itens) | Grazi como proprietária + responsável CICA | 163 fatos SURIA congelados com ficha sem previsões; comando `select` para os demais | 1. Revisar a ficha dos 163 fatos. 2. Após novos vínculos (item A), CICA roda `select --seed <semente publicada> --size 37` e `prepare` numa segunda conta. 3. Revisar a nova ficha. 4. CICA roda `report` e registra o resultado; precisão automática só é medida se houver regra ativa (item D). |
| E2. Retomada em até 15 min (medição real) | Responsável CICA | **Medida em 19/11 (V-418):** após os reinícios reais das releases v105 e v106 o agente voltou em ~62 s; 72 h com 4.071 varreduras, zero perdas e zero jobs presos | Concluído tecnicamente para o canal do agente e a fila. Ainda não provado: interrupção no meio de uma coleta longa; restauração (F) segue aberta. |
| H. Treinamento e aceite formal | CONTAD + CICA | Guia `docs/pt-BR/contad-conciliacao.md` atualizado com o vínculo por OFX | Depois de A–F: 1. Sessão curta com o percurso vínculo → extrato → Razão → conferência → relatório. 2. Revisar com a CONTAD os critérios D-73. 3. Registrar o aceite com a autoria real. |

## Restauração e RPO

Dispensados pelo responsável em 19/11 (D-379: “nao precisa disso, so tem que fazer
funcionar”). Backup e PITR existentes continuam como estão; restauração não foi
provada e não é critério de conclusão.
