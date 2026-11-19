# CICA × CONTAD — pendências para a conclusão (19/11/2026)

Estado: **uso assistido** (release v105 em produção). Esta lista substitui a tabela
de pendências do comunicado de 18/11 sem reabrir decisões já tomadas. A CONTAD só
será declarada concluída quando os critérios D-73 estiverem cumpridos: 200 itens
revisados pelo proprietário, precisão medida de pelo menos 95% onde houver
classificação automática, zero duplicidade/empresa errada/vazamento, retomada
sem perda em até 15 minutos, restauração conferida em até 4 horas e importação
conferida no Domínio.

Evidências privadas ficam fora do Git, em `.tmp/` das worktrees indicadas em
VALIDACOES (pastas 0700, arquivos 0600). Nenhum valor financeiro ou nome real
aparece neste documento.

## O que mudou nesta rodada (D-377/D-378, fonte isolada, ainda não publicada)

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
| B. Q-47 — formato de importação no Domínio | CONTAD (acesso ao SVAPL02) + responsável CICA | Prints de 18/11 (Domínio 10.6A-10, atualização 08, Sybase 17); adaptador bloqueado (`RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=false`); recibo por hash/partida pronto | 1. No SVAPL02, abrir o Importador e mostrar a lista completa de *Conjunto de dados* (print, sem importar). 2. Abrir *Utilitários → Importação* e mostrar se existe *Importação Padrão / Leiaute Domínio Sistemas com Separador* (print). 3. Enviar os prints ao responsável CICA. 4. CICA ajusta o adaptador ao que foi observado e gera arquivo/prévia/hash de um lote novo, ainda não escriturado. 5. CONTAD aprova lote e procedimento de recuperação, importa e registra o recibo por partida. |
| C. C01/C02 — retenções e juros nos títulos | Grazi (CONTAD) | Sete exemplos privados V-379 íntegros; confronto técnico V-415 (C01: vbru−CRF−IRRF=vlor; C02: tipo 1 já inclui os juros do tipo 2); o sistema não soma componentes sozinho | 1. Abrir *Títulos e baixas* nas empresas dos exemplos. 2. Conferir C01 (retenções) e C02 (juros) contra o Domínio. 3. Dizer se a leitura técnica está correta. 4. Registrar a decisão em cada baixa pela tela. |
| D. DE-PARA | CONTAD | Duas sugestões válidas retidas; zero regras ativas; nenhuma nova chamada de IA | 1. Abrir *Revisão DE-PARA*. 2. Aprovar (ou recusar) as duas contas exigidas. 3. Só então revisar as duas sugestões e ativar manualmente, se for o caso. |
| E1. Amostra D-73 (200 itens) | Grazi como proprietária + responsável CICA | 163 fatos SURIA congelados com ficha sem previsões; comando `select` para os demais | 1. Revisar a ficha dos 163 fatos. 2. Após novos vínculos (item A), CICA roda `select --seed <semente publicada> --size 37` e `prepare` numa segunda conta. 3. Revisar a nova ficha. 4. CICA roda `report` e registra o resultado; precisão automática só é medida se houver regra ativa (item D). |
| E2. Retomada em até 15 min (medição real) | Responsável CICA | Script somente leitura `.tmp/retomada/resume-check.py` (worktree `contad-conclusao-20261119`); leitura em produção recusada pela permissão automática desta sessão | 1. Autorizar a leitura somente leitura em produção (ou executá-la). 2. Rodar `python3 run_remote.py resume-check.py resume-check-web 891e63ef665e58 180`. 3. Comparar os horários de reinício dos deploys v104/v105 com a próxima varredura concluída do agente e confirmar zero jobs presos. |
| F. Restauração e RPO | Responsável CICA (login no console Neon) | Snapshot histórico expirado em 13/11; prefixo Tigris vazio (V-415); nada alterado | 1. Entrar no console Neon. 2. Criar branch de restauração em um ponto no tempo (sem tocar a produção). 3. Conferir contagens dos 15 grupos protegidos e um documento. 4. Medir o tempo total (meta: até 4 h). 5. Excluir a branch de teste. |
| H. Treinamento e aceite formal | CONTAD + CICA | Guia `docs/pt-BR/contad-conciliacao.md` atualizado com o vínculo por OFX | Depois de A–F: 1. Sessão curta com o percurso vínculo → extrato → Razão → conferência → relatório. 2. Revisar com a CONTAD os critérios D-73. 3. Registrar o aceite com a autoria real. |

## Única pergunta pendente para o responsável CICA

**Qual RPO (perda máxima de dados aceitável) devemos usar como critério?**
Recomendação: **até 24 horas**, verificável com o PITR já existente no Neon, sem
alterar retenção, backup ou capacidade (D-375: “não precisa mexer em
infraestrutura agora”).
