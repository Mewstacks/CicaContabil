# CONTAD — resumo e continuidade

**Estado atual — D-329/V-342, 10/11/2026:** agente integrado à main pelo
[PR 3](https://github.com/Mewstacks/CicaContabil/pull/3); fonte validada 5c20766, main 272f977,
[CI completo 42882756516](https://github.com/Mewstacks/CicaContabil/actions/runs/42882756516) aprovado. Backend consolidado publicado e
conferido na **release 80**. Preservados worker web único, menu Empresas
atendidas, filtros de recuperação NFS-e, recursos e dados CONTAD.
MSI **1.0.5/.NET 10.0.15** de V-338 mantido; não reinstalar por esta integração.
V-340 comprova ODBC interativo no configurador do **SVAPL02**, CICA_CONTAD/
SQL Anywhere 16 x64. Próxima ação: **passo 7, parear como candidato**, usando
o novo arquivo privado **CICA-CONTAD-Codigo-SVAPL02-2026-11-10-163051.txt**, válido até **17:30:50 de 10/11,
Brasília**. Código anterior expirado sem uso; nenhum candidato ou corte criado.
Após parear/reiniciar somente CicaAgent, conferir Running/Auto/LocalSystem e
awaiting_activation. ODBC sob LocalSystem, corte oficial e recepção continuam
pendentes; o anterior permanece ativo e o manifesto permanece o mesmo piloto.
Código não integra Git/ZIP/chat. Registros anteriores abaixo são históricos.

**10/11 — D-326/V-338:** MSI 1.0.5/.NET 10.0.15 da fonte 53b834b validado em
[CI Windows 42863201809](https://github.com/Mewstacks/CicaContabil/actions/runs/42863201809):
62 testes/26 checks aprovados, artefatos e SHA-256 conferidos. Pacote/roteiro
preservados em Downloads, sem assinatura de editor. Backend de substituição
não publicado: aguardar liberação e código novo antes de instalar/parear.
Sem deploy, instalação/corte reais ou aceite. As notas anteriores são históricas.

## Atualização de destino — 09/11/2026, D-324

**Estado de 10/11 — D-325/V-336/V-337:** Windows Server 2022 Standard,
21H2/build 20348.5761, PowerShell x64 e DSN CICA_CONTAD/SQL Anywhere 16 x64.
Teste interativo e limpeza/salvamento confirmados pelo operador. .NET 10 LTS
aprovado e implementado; runtime autocontido 10.0.15 nos três componentes Windows
publicados localmente; 59 testes aprovados e três exclusivos de Windows pendentes.
MSI novo, CI Windows, backend, instalação/LocalSystem e corte ainda não executados.

V-329: código local da substituição concluído; PostgreSQL 1.837/163 aprovados,
um skip; .NET 59 aprovados/um skip Windows e três compilações aprovadas. Sem
publicação, MSI novo ou instalação/corte reais; essa prova anterior usou .NET 8.
Alvo posteriormente revisado em D-325, sem homologação Windows presumida.

Novo agente será instalado no **Windows Server** disponibilizado por AnyDesk,
e se tornará o oficial após provas locais e corte explícito. Plano/prompt
canônico adaptado; [guia técnico](contad-agente-oficial-windows-server.md).
Candidato recebe novo UUID/segredo, herda o manifesto e não coleta até ativação;
corte ativa o novo e revoga o anterior sem apagar dados. Histórico da carteira
continua desde 09/2026; a mudança de máquina não amplia o manifesto.

Nesta sessão, AnyDesk foi encontrado aberto, mas a ferramenta retornou timeout
-10005 ao obter a janela; nenhuma ação no Server. Acesso disponibilizado não
equivale a controle observado. Desenvolvimento local não é instalação/aceite;
release 75/piloto permanecem a última evidência publicada. Os estados anteriores
abaixo são históricos, inclusive a indisponibilidade de operador em 06/11.

**Atualização D-323/V-328, 07/11/2026:** backend na **release 75**, fonte c8b0c50/
CI 42355490505 aprovado. Corrigida retomada após cobertura inconsistente e
adicionado diagnóstico administrativo somente leitura; 1.801 testes/163 subtestes
PostgreSQL local, um skip. 653 hashes runtime, migrações e doze fingerprints
CONTAD conferidos, login Grazi preservado. Sem mudança do agente/MSI/manifesto
real: piloto/163 eventos e zero scan da carteira. Inventário Windows ainda não
recebido; último relato do operador indisponível. Próximo insumo permanece Q-28;
demais fontes/gates, treinamento e aceite continuam abertos. Detalhes em V-328.


**Execução atual D-323/V-327:** backend publicado na **release 74**, fonte
e9311eb/CI 42294764025 aprovado; migrações, 651 hashes runtime, doze fingerprints
de dados e acesso HTTPS Grazi conferidos. Protocolo/recepção retomável de empresas
prontos; manifesto real continua piloto, uma empresa/conta e 163 eventos.
MSI 1.0.4 aprovado/preparado; PC ainda 1.0.3, sem novo ciclo comprovado após o
deploy. Histórico financeiro: **09/2026 em diante**. Operador confirmou que ainda
está indisponível. Próximo insumo: inventário real de metadados/situações do PC.
[Contrato e inventário](contad-carteira-protocolo.md) · [Guia preparado](pt-BR/contad-conciliacao.md).
Fontes completas, IA, Q-46/Q-47, D-73, recuperação recorrente, treinamento/aceite
continuam pendentes; esta publicação não conclui o projeto. O resumo D-322 abaixo
é a base histórica, preservada.


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
