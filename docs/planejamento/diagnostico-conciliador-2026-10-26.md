# Conciliador: diagnóstico e levantamento com a cliente

**Complemento de 27/10/2026 — D-301:** o responsável forneceu o contrato e
esclareceu contas a pagar/receber e possível retorno pelo fiscal. O
[roteiro contratual](levantamento-contrato-conciliador-2026-10-27.md) passa a
orientar a entrevista. A cliente do contrato é de outro ambiente; D-74 não
comprova sua modalidade local/Web nem seus acessos. As lacunas técnicas abaixo
permanecem, mas a comparação precisa também distinguir títulos, movimento
bancário e registro no ERP. Não limitar o levantamento a extrato × Razão.

Data: 26/10/2026. Código analisado: `aad2f5a`, após pull de 59 commits sobre
`d501fbe`. Escopo D-300; evidência V-300. Detalhamento da etapa 09/PC-19 e de
Q-28, sem plano concorrente, nova regra contábil ou autorização de dados reais.

## Conclusão

**O conciliador funciona parcialmente em testes locais, mas ainda não está pronto
para comprovar a comparação completa do extrato bancário com o Razão contábil.**
Há importação, sugestões, revisão e confirmação humana, além de um fluxo mais novo
de classificação, partidas, alocação e exportação protegida. Entretanto, a fonte
Domínio atual é de itens de extrato bancário; existem dois fluxos com controles
diferentes e foram reproduzidas quatro lacunas na fila OFX. Passar nos testes
existentes não cobre essas lacunas nem constitui homologação da cliente.

## O que já funciona localmente

| Capacidade | Evidência e limite |
|---|---|
| Entrada única de OFX, CSV, XLSX e PDF | Fonte privada, hash, execução persistida e revisão. Reenvio dos mesmos bytes é idempotente; arquivos diferentes com transações sobrepostas ainda podem duplicar movimentos. |
| Mapeamento de CSV/XLSX | Layout versionado, validação de colunas e recusa quando a estrutura muda. Não é importador completo de partidas contábeis do ERP. |
| Fila OFX × Domínio | Busca candidatos por empresa, mesma data e mesmo valor absoluto; confirmação humana persiste após sincronização. Não valida conta/natureza/capacidade do candidato. |
| Fluxo novo de movimentos | Classificação/regras, revisão, geração e aprovação de rascunho equilibrado, alocação parcial, desfazimento e histórico de decisões. Usa `JournalEntry`, separado do espelho `AccountingEntry`. |
| Alocação no fluxo novo | Exige evidência, empresa comum e limites disponíveis; recusa usar o lançamento gerado pelo próprio movimento como evidência independente. Essa proteção não se estende à fila OFX. |
| Processamentos | Fila persistida, recuperação de execução interrompida e orientação de mapeamento/conta/OCR/falha. Worker e recuperação reais não foram exercitados nesta auditoria. |
| Exportação contábil | Arquivo/hash, auditoria, download e confirmação separados. Domínio depende de `RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED`, falso por padrão. Siescon não tem adaptador contábil registrado. |

Limites de entrada observados: 20 arquivos por envio, 25 MiB por arquivo, até
100 mil linhas tabulares, 500 páginas PDF e 10 mil transações por OFX. São limites
do código, não medições de capacidade. OCR local português indisponível nesta máquina.

## O que falta para o objetivo solicitado

As prioridades abaixo orientam as correções dentro de PC-19, sem iniciar implementação.

| Prioridade | Lacuna observada | Consequência e fechamento necessário |
|---|---|---|
| Crítica | **Fonte contábil independente incompleta.** Agente local e backup leem `CTEXTRATO_BANCARIO_LANCAMENTO_ITEM`. O backend copia esses itens para `DominioBankEntry` e `AccountingEntry`; o nome do modelo não muda a origem. `CTLANCTOFCONT` está documentada com consulta/espelho pendentes. | Comparar dois extratos não prova escrituração no Razão. Identificar e validar com a contadora a fonte efetiva dos lançamentos, suas partidas, contas, documento, vínculo e competência. Não escolher outra tabela ou habilitar leitura por inferência. |
| Alta | **Espelho do ERP e fluxo novo separados.** A sincronização/importação de registros alimenta `AccountingEntry`; a conciliação avançada procura `JournalEntry`. A criação de `JournalEntry` encontrada no código é a geração de rascunho a partir de movimento. | Um lançamento sincronizado não vira automaticamente candidato no detalhe avançado. Falta ligação rastreável da fonte contábil independente e coerência entre as duas filas. Marcar um CSV como “Registros contábeis” não resolve essa ligação. |
| Crítica | **Reutilização de candidato na fila OFX.** Dois débitos de R$ 12,34 puderam ser confirmados contra o mesmo registro de R$ 12,34. | Pode apresentar duas conciliações consumindo um único lançamento. Aplicar controle de capacidade/exclusividade e concorrência também nesse fluxo; verificar históricos existentes antes de liberar. |
| Alta | **Natureza não validada na fila OFX.** O serviço verifica empresa/data/valor absoluto, sem usar `direction`. | Entradas/saídas ou estornos podem ser associados inadequadamente. Confirmar o significado dos códigos da fonte e a perspectiva banco × conta contábil; depois validar a compatibilidade. Não presumir que “D/C” do extrato tenha o mesmo significado do Razão. |
| Crítica | **Bloqueio de conta não alcança os dois fluxos.** Upload com OFX `001:123` e conta selecionada `001:999` permaneceu em revisão no fluxo novo, mas criou registro confirmável na fila OFX. | O mesmo arquivo fica bloqueado em um caminho e conciliável no outro. Unificar validação e vínculo de empresa/banco/agência/conta antes de permitir confirmação. |
| Alta | **Deduplicação somente do arquivo.** O mesmo FITID em dois arquivos que diferem apenas por uma quebra de linha criou duas transações. | Extratos mensais e por intervalo podem sobrepor períodos. Definir identidade transacional por origem/empresa/conta e tratar colisões/correções sem apagar evidência. A restrição atual é FITID por arquivo. |
| Alta | **Fotografia incompleta da situação no Domínio pelo agente nativo.** O envio local fixa `is_linked = false`; a consulta Python direta calcula a existência de vínculo. | O backend suporta o estado real, mas o agente nativo não o obtém nessa consulta. Não interpretar `false` como prova de que não foi escriturado. Confrontar vínculo real e semântica antes de gerar novos lançamentos. |
| Alta | **Fechamento bancário completo não comprovado.** O parser OFX conserva conta e transações, sem saldo inicial/final. A fila parte das transações bancárias, sem uma fila própria de lançamentos contábeis sobrantes. | Além de correspondências, falta demonstrar saldo do extrato × saldo contábil, pendências nos dois sentidos e diferenças explicadas por conta/período. Totais de valores absolutos da tela não são saldo conciliado. |
| Alta | **Corpus, volume e destino contábil ainda sem aceite.** Testes sintéticos não validam layouts reais, OCR, carga ou importação contábil no ERP. A consulta direta Python ainda tem teto de 10 mil itens, sinalizado como possível truncamento; o agente nativo usa páginas de 500. | Validar completude da rota usada, períodos, retomada e dados reais autorizados. D-73 exige 200 itens revisados, integridade e tempos aplicáveis. Importar e conferir a exportação contábil antes de habilitar seu gate. |

**NFS-e é um aceite distinto:** D-295 aceita a homologação externa de NFS-e e
encerra seu bloqueio PC-03/Q-39. Isso não comprova a importação do arquivo
contábil produzido por `render_dominio_csv`; não pedir que a cliente repita a
homologação NFS-e para resolver PC-19.

## O que levantar com a cliente

Estas são pautas da entrevista vinculada a Q-28 e PC-19. Respostas comerciais,
semântica e autorização devem voltar ao registro canônico antes de implementação.

### Ambiente e origem dos dados

- **Qual escritório/instalação será usado?** Se for a Fedrizzi já registrada,
  D-74 confirma Domínio local com ODBC: não pedir novamente DSN, driver,
  servidor ou credencial. Confirmar somente eventual mudança de ambiente.
- **Se for outra instalação: Domínio local, servidor acessado remotamente ou
  Domínio Web/Onvio?** Qual versão/módulo e quem é o técnico responsável?
  A resposta define onde pode ocorrer a leitura autorizada. “Abre pela internet”
  não basta para distinguir servidor remoto de Domínio Web.
- **De onde vêm os lançamentos já escriturados?** Pedir que a contadora mostre
  o Razão da conta bancária e o caminho usado para exportá-lo, junto do extrato
  que deseja comparar. Confirmar se a rotina usa Contabilidade, Escrita Fiscal
  ou apenas extratos importados no Domínio.
- **Se a fonte for Web: como obter uma fotografia atual dos lançamentos?**
  O código atual não demonstra leitura de Razão pela API oficial. Avaliar um
  relatório/exportação autorizado ou backup compatível e atualizado; o backup
  único de acumuladores NFS-e não garante atualização contábil mensal.

### Bancos, período e identificação

- **Quais empresas e contas entram primeiro?** Relacionar código da empresa,
  banco/agência/conta e conta contábil correspondente. Separar corrente,
  aplicações, cartões e contas transitórias; informar moedas além de BRL se existirem.
- **Quais arquivos o banco fornece?** Preferir OFX para o piloto se disponível;
  levantar CSV/XLSX e PDF textual ou digitalizado quando necessários. Qual o
  volume mensal por conta? Os períodos dos arquivos costumam se sobrepor?
- **Qual data representa o confronto?** Movimento/compensação no banco ou
  lançamento contábil? Há diferença de dias, valor líquido/bruto ou arredondamento?
  Solicitar exemplos e a regra usada pela contadora, sem pressupor tolerâncias.

### Exceções e resultado esperado

- **Como tratam agrupamentos e divisões?** Um pagamento quita vários títulos?
  Um recebimento tem tarifa/desconto? Há PIX de mesmo valor, transferências
  entre contas, aplicação/resgate, juros, estorno ou lançamento duplicado?
- **O que deve acontecer quando não houver par?** Só apontar divergência,
  sugerir classificação ou preparar um novo lançamento para revisão? Qual prova
  permite concluir cada caso e quem confere? Gerar um lançamento não significa
  que o lançamento já existente foi conciliado.
- **Qual é a prova de encerramento usada hoje?** Pedir um mês já conciliado,
  com saldo inicial/final, Razão, relação de diferenças e tratamento aplicado.
  Isso fornece o resultado esperado independente do algoritmo.
- **Se houver devolução ao ERP:** qual rotina e layout de importação contábil,
  plano de contas/códigos reduzidos, históricos, centros de custo e períodos
  bloqueados? Quem confere o arquivo importado e como evita duplicação?
- **Quem autoriza o piloto e revisa os dados?** Indicar contadora e contato
  técnico, empresas/período permitidos e canal protegido. Não solicitar senha,
  certificado ou backup no chat. D-72/D-73 já definem o proprietário como
  aprovador do módulo e as métricas; a cliente fornece o contexto operacional.

### Material mínimo para destravar a próxima execução

Recomenda-se começar com **uma empresa, uma conta e um mês já fechado**, contendo
extrato original, Razão do mesmo recorte, saldos inicial/final, identificação da
conta contábil e uma lista revisada de correspondências/divergências. Incluir
casos de mesmo valor, diferença de data, tarifa/estorno e arquivo sobreposto se
existirem. Esse recorte inicial orienta a correção; o aceite de automação mantém
os **200 itens independentes de D-73**, sem reduzir a amostra por inferência.

Primeiro confirmar a fonte e corrigir integridade/ligação das filas; depois
validar a comparação nesse material autorizado. Exportação contábil só entra na
homologação quando fizer parte do resultado desejado. Não há necessidade de IA
externa ou conexão bancária nova para demonstrar essa primeira comparação.

## Evidências, reprodução e limites

- Pull por fast-forward: `d501fbe → aad2f5a`, 59 commits, sem alterações locais
  anteriores. `HEAD...origin/main = 0/0` após atualização.
- `.venv/bin/python -m pytest tests/test_reconciliation.py tests/test_reconciliation_module.py tests/test_intelligence_sync_django.py tests/test_module_activities.py -q`:
  **94 aprovados, 24 subtestes aprovados, 1 skip** de OCR português, em 30,84 s.
- Quatro sondas sintéticas adicionais em
  `.tmp/auditoria-conciliador-2026-10-26/test_diagnostico.py`:
  **4 reproduções confirmadas em 15,47 s**. Elas afirmam o comportamento atual
  inadequado, não a correção dele, e ficam fora da suíte de aceite. Executar com
  `.venv/bin/python -m pytest -c pyproject.toml .tmp/auditoria-conciliador-2026-10-26/test_diagnostico.py -q`.
- Django check sem problemas e dry-run de migrações sem alterações, usando
  `config.settings.test`. Não foram aplicadas migrações no banco de desenvolvimento.
- Nenhuma mudança na aplicação, regra, UI, produção ou dados reais. Não houve
  novo ensaio visual, build/instalação Windows, ODBC, OCR real, worker externo,
  PostgreSQL, importação de ERP, chamada paga ou deploy. A análise não prova o
  estado atual do servidor publicado nem da instalação da cliente.

## Referências verificadas no repositório

- `src/apps/hub/reconciliation.py`: `parse_ofx`, `import_ofx`,
  `rebuild_reconciliation_matches` e `confirm_reconciliation_match`.
- `src/apps/hub/reconciliation_service.py`: `process_run`,
  `auto_reconcile_unique_movement`, `confirm_reconciliation`,
  `create_journal_entry_from_movement` e `create_export`.
- `src/apps/hub/views.py`: `reconciliation_upload`,
  `confirm_reconciliation` e `reconciliation_movement_detail`.
- `src/apps/intelligence/sync.py`: `sync_bank_entries`;
  `src/apps/intelligence/connectors.py`: consulta `bank_entries`.
- `src/apps/hub/imports.py`: ramo `ImportBatch.Kind.ACCOUNTING`.
- `agent-windows/src/Cica.Agent.Service/DominioLocalProcessor.cs` e
  `BackupProcessor.cs`: envio de itens do extrato.
- `agent-windows/CONTRATOS-DOMINIO.md`, D-73/D-74/D-228/D-295,
  etapa 09 e PC-19 do plano mestre.
