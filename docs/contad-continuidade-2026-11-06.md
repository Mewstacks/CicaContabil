# CONTAD — resumo e continuidade

Atualizado em 06/11/2026. Registro vigente: **D-321/V-324/V-325**, etapas 03/09/12,
PC-19 e Q-28/Q-46/Q-47. Os registros D-320/V-322/V-323 são etapas anteriores.

**Situação:** deploy, ativação do escritório e integração real do extrato estão
concluídos. O agente está sincronizando o recorte autorizado; o conciliador
completo ainda não foi homologado.

## Entrega concluída

- **Release Fly 73**, fonte `651368c`, CI 42282953292 aprovado. PostgreSQL:
  1.755 testes/163 subtestes aprovados, dois skips declarados. Runtime de
  web/worker, bancos/migrações Neon, health e proteção de acesso conferidos.
  Mesmas máquinas/512 MB, reserva parada, exportação Domínio false e prévia
  privada não homologada limitada à CONTAD.
- **CONTAD ativa**, somente Conciliação e contrato individual existente de
  R$ 200/mês travado, sem iniciar cobrança automática/fatura. O responsável
  escolheu **não enviar convite**. Por solicitação posterior, a conta da Grazi
  foi criada com e-mail já informado e senha inicial validada, como Proprietária
  somente da CONTAD, sem acesso de plataforma. Login HTTPS real e Conciliação
  200/Nova importação conferidos, sem anexar arquivo; sessão de teste encerrada.
  Credencial só no arquivo privado `/Users/pedromachado/Downloads/CICA-Grazi-acesso.txt`.
- **Recorte explicitamente aprovado:** SURIA, Domínio **212**, conta contábil
  **8 — BANCO SICREDI**, **09/2026**, somente cabeçalho da sonda. Identidade da
  conta veio dos arquivos aceitos, e o manifesto está validado no servidor.
  Não pedir novamente empresa/conta/período/ID ou autorização desse recorte.
- **Agente 1.0.3 pareado**, Domínio Local/CICA_CONTAD x64/SQL Anywhere 17,
  credencial EXTERNO digitada somente no PC. Operador comprovou serviço
  **Running / Auto / LocalSystem / ready**, inclusive após reinícios.
- O primeiro pareamento falhou no icacls antes de salvar a configuração.
  Resolvido com configurador como administrador; credencial órfã revogada e
  código substituto consumido. Não reinstalar ou emitir novo código se ready.
- Removidos somente campos de senha do novo CICA_CONTAD x64, sem ler valores;
  operador informou **CampoDeSenhaNoDsn=false / Running / ready** após reinício.
  DSN original preservado; autenticação do agente é explícita, com configuração
  protegida no Windows.
- Backend recebeu **163 movimentos**, conector **healthy**, zero duplicações
  e zero linhas fora do recorte. Datas/valores conferidos com os arquivos
  fornecidos. Os 163 AccountingEntry são espelho do extrato; não são novas
  partidas independentes. 151 vínculos do extrato Domínio não são aceite CICA.
- Conferência repetível OFX/PDF/Razão já implementada em CLI e comando Django:
  163 coincidências, 159 candidatos únicos, dois grupos ambíguos e saldos dos
  PDFs iguais, sem confirmar alocações ou completar contrapartidas ausentes.
- Backup Neon/Tigris e restore isolado comprovados em V-322, válidos até
  **13/11/2026**. V-324 reconferiu só manifesto/metadados dos 53 objetos,
  sem nova cópia/recurso/restore ou alteração de retenção.

## Pendências reais

1. Completar fontes/semântica e adaptadores de partidas e títulos/parcelas/
   baixas, regras e **DE-PARA** Q-28/Q-46/Q-08/Q-09. Não fabricar títulos ou
   contrapartidas, usar plano de outra empresa ou consumir IA paga por inferência.
2. Layout/importação ERP **Q-47**, em autorização própria, treinamento e aceite.
   Prévia privada é não homologada; exportação continua desabilitada.
3. **D-73:** 163 eventos únicos não atingem os 200 independentes. Repetição,
   OFX/PDF, espelhos ou restart não aumentam a amostra. Provas reais de múltiplas
   páginas/falha de rede e recuperação operacional/RPO recorrente seguem abertas.

O responsável informou empresa fechada e arquivos fornecidos para teste:
corpus aceito. **Não perguntar quem importou ou de onde veio o saldo da captura**
para retomar esse teste. Diferença histórica não teve causa presumida; aprovação
posterior do corpus/recorte está registrada. Não alterar saldos/ERP por inferência.

## Como retomar

Leia [PLANO-MESTRE](../PLANO-MESTRE.md), [DECISOES](../DECISOES.md) e
[VALIDACOES](../VALIDACOES.md), nessa ordem; depois etapas 03/09/12 e
[dúvidas abertas](planejamento/duvidas-abertas.md). Operação/retorno:
[roteiro de release](contad-release-2026-11-05.md).

Evidências privadas, fora do Git:

- `.tmp/contad-grazi-access-2026-11-06/`: testes Argon2, recibo de criação,
  conferência HTTPS de login/importação e estado final sem senha nos relatórios.
- `.tmp/contad-deployment-2026-11-06/`: candidata, CI/deploy, ativação,
  manifesto, verificações runtime/HTTP e `agent-final-verification.json`.
- `.tmp/contad-development-2026-11-06/contad-suria-pilot-request.json`:
  fontes, preparação e referências, agora com recorte aprovado.
- `.tmp/contad-ledger-evidence-2026-11-06/conferencia-final.json`:
  confronto OFX/PDF/Razão e hashes. [Uso e limites](conciliacao-razao-normalizado.md).
- Prompt privado em `/Users/pedromachado/Downloads/CONTAD-prompt-continuidade.txt`;
  originais bancários/Razão permanecem nos Downloads.

O operador executa passos guiados no Windows; não retomar controle alternativo
AnyDesk ou repetir instalação/sonda. Senha fica somente no PC. Preservar trabalhos
locais anteriores D-316/D-317/V-318/V-319/etapa 00 fora dos commits desta entrega.
