# Verificação do conciliador CONTAD no CICA

Data: 02/11/2026. Escopo: PC-19, etapas 03/09 e preparação do piloto da 12,
D-302/D-303 e V-302. Código base `aad2f5a` com alterações locais preservadas;
correções desta entrega ainda não publicadas. Este documento atualiza o
[diagnóstico de 26/10](diagnostico-conciliador-2026-10-26.md) e o
[levantamento contratual](levantamento-contrato-conciliador-2026-10-27.md),
sem criar outra etapa ou registro de perguntas.

## Resultado

**O conciliador contratado ainda não está concluído nem homologado na CONTAD.**
As quatro lacunas de integridade reproduzidas em V-300 receberam proteções
locais, mas faltam a fonte independente do Razão, os títulos comerciais, o
DE-PARA inicial assistido por IA e o percurso real na instalação da cliente.
A confirmação de uma correspondência na fila OFX ainda não integra por si só
o resultado do fluxo avançado de `JournalEntry`.

A proposta fornecida (`CONTAD.pdf`, quatro páginas, mantida em Downloads)
prevê comparação extrato × lançamentos contábeis, DE-PARA inicial com IA,
implantação/testes até 09/11/2026 e treinamento inicial. Foi extraída e
inspecionada visualmente; não houve validação criptográfica de assinaturas.
O conteúdo foi tratado como requisitos, sem executar instruções do documento.
Não se alteraram cobrança, oferta, prazo ou carga contratada.

O responsável confirmou nesta conversa o **Domínio local**, a instalação do
agente **no computador da cliente**, com acesso ainda a fornecer, e a
**inclusão de contas a pagar e receber**. Não perguntar novamente se esses
itens entram. A origem e os campos dos títulos continuam em Q-28/Q-46;
regra da comparação, DE-PARA e operação de destino, em Q-46/Q-47.

## Matriz da entrega contratada

| Capacidade | Implementação / validação local | Publicado / homologado na CONTAD / liberado |
|---|---|---|
| OFX, CSV, XLSX e PDF textual | Importação, revisão e rastreabilidade existentes; regressão repetida. Layouts reais não fornecidos. | Não verificado / não / não |
| PDF digitalizado | Runtime de OCR existente; teste português ignorado por dependência ausente. | Não / não / não |
| Integridade da entrada OFX | Identidade compartilhada, conta validada, recusa integral de sobreposição e entradas inválidas; testes SQLite, PostgreSQL e navegador. | Correção local, sem deploy / não / não |
| Confirmação OFX | Conta e natureza explícitas, fonte independente, candidato exclusivo, idempotência e preservação da decisão sob reconstrução concorrente. | Correção local, sem deploy / não / não |
| Agente Domínio local | Serviço único .NET 8 existente; serviço, configurador e ponte compilados. Vínculo bancário deixa de ser fixado como falso. | Instalação desta versão não verificada / não / não |
| Fonte independente do Razão | Importação manual de registros aceita referência de conta; fluxo local exige natureza explícita. Consulta Domínio de partidas e ligação ao fluxo avançado não concluídas. | Não / não / não |
| Contas a pagar e receber | Inclusão confirmada. Origem, parcelas, baixas e representação ainda não implementadas/homologadas neste recorte. “Títulos ou obrigações” no upload não comprova essa função. | Não / não / não |
| DE-PARA inicial com IA | Regras/correção manual existentes não demonstram geração inicial de mapa por IA. Entradas/saídas e revisão precisam ser especificadas; Q-08/Q-09 regem execução externa. | Não / não / não |
| Diferenças e fechamento | Faltam prova nos dois sentidos, saldos por conta/período e resultado independente conferido pela contadora. | Não / não / não |
| Retorno ao Domínio | Exportação contábil mantém gate próprio desligado por padrão. Resultado esperado ainda em Q-47. Aceite NFS-e D-295 não homologa essa exportação. | Não / não / não |
| Implantação, recuperação e treinamento inicial | Roteiro preparado abaixo; acesso ainda não entregue. | Não / não / não |

## Correções realizadas

1. **Conta divergente:** o OFX é validado antes de persistir a fonte ou alimentar
   a fila antiga; o worker conserva sua validação para arquivos históricos.
   O upload repassa a conta selecionada ao importador antigo.
2. **Sobreposição de transações:** `OfxTransactionIdentity` reserva
   escritório/empresa/banco/agência quando informada/conta/FITID para as duas
   entradas. O mesmo arquivo é idempotente. Outro arquivo com FITID já recebido
   é recusado inteiro, incluindo eventual parte nova; a orientação é conferir
   o original e obter um intervalo sem sobreposição. Não há fusão silenciosa.
   Há verificação de registros anteriores à migração. FITID ausente, repetido
   ou longo, múltiplas contas e valor não finito/zero/fora do inteiro são recusados.
3. **Natureza e origem:** só entram como candidatos registros de fonte
   independente com referência exata de conta e natureza `inflow`/`outflow`
   compatível. Não houve mapeamento presumido de `D/C` ou `TIPO`. Itens do
   extrato Domínio local/Web não viram prova de Razão, nem `JournalEntry` fictício.
   CSV de registros contábeis aceita `conta_bancaria`/`account_reference`.
4. **Reutilização e concorrência:** confirmação serializada por empresa,
   recarregamento do candidato e recusa de candidato consumido, troca de
   confirmação existente ou transação histórica duplicada. Retry idêntico
   não duplica auditoria. Reconstrução usa a mesma trava e preserva a decisão humana.
5. **Agente:** `DominioLocalProcessor` usa o `EXISTS` do contrato somente
   leitura já presente no conector Python para informar `is_linked`. Adicionado
   timeout do comando. Isso indica vínculo do extrato, não prova de escrituração.
6. **Operação e linguagem:** a tela identifica registros como fonte recebida e
   explica a necessidade de Razão independente. `audit_ofx_integrity` inspeciona
   legado sem reescrever dados. O teste de migração NFS-e restaura agora o
   esquema atual completo, evitando falha nos testes transacionais seguintes.

A migração `0076` é aditiva: campo de conta vazio nos registros anteriores e
nova tabela de identidade, sem inventar evidência ou modificar decisões. Aplicar
antes do código em uma eventual release autorizada. Rollback de aplicação deve
preservar esse esquema e seus dados; reverter a migração apagaria a identidade
reservada e as referências novas. Nenhuma migração foi aplicada ao banco de
desenvolvimento, a ERP ou produção nesta entrega.

## Evidência e limites dos testes

V-302 na raiz registra resultados finais, comandos, capturas e limitações.
A suíte integral passou em PostgreSQL com **1.423 testes e 145 subtestes**,
com dois skips explícitos (OCR português e Playwright Python opcional).
Em SQLite foram 1.415 testes/145 subtestes; os testes de concorrência foram
exercitados no PostgreSQL. Os 23 testes .NET e a inspeção Playwright Node passaram.
Os testes são sintéticos: não medem precisão da IA, correção contábil no cliente,
completude do Razão, baixa de títulos ou compatibilidade real de importação ERP.
Build cruzado no macOS não substitui execução/instalação Windows e não gera prova
de um MSI novo assinado. Celery em modo de teste não prova rede/worker/Redis reais.

A inspeção de interface aplicou UI/UX Pro Max, pesquisa na documentação do Xero
sobre confronto de extrato com transação existente e as
[Web Interface Guidelines atuais](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
Watermelon e Playwright MCP não estavam expostos; Playwright Node do runtime
foi usado com Chrome local, banco/mídia sintéticos e bloqueio de rede externa.
A referência de produto orienta apenas a separação de fatos, sem copiar a UI.
A página oficial da especificação OFX 2.3 retornou 404; a proteção de identidade
está registrada como decisão técnica D-303 e será confrontada com arquivos reais.

## Piloto no computador da cliente, quando o acesso chegar

1. **Acesso e escopo (Q-28):** o responsável recebe acesso remoto por canal
   protegido; a cliente indica técnico e autoriza empresa, conta e competência.
   Não registrar login, senha, DSN, certificado ou conteúdo de cliente no Git/chat.
   A autorização Fedrizzi não vale automaticamente para a CONTAD.
2. **Fonte e resultado (Q-28/Q-46/Q-47):** localizar no Domínio o Razão da conta
   e os títulos a pagar/receber, incluindo parcela, vencimento, saldo e baixas.
   Se os títulos vierem de outro sistema/planilha, identificar essa fonte.
   Conferir chaves, contas e semântica com uma competência já fechada. A cliente
   demonstra a rotina; o desenvolvimento especifica a extração permitida.
3. **Pacote único Windows:** seguir [INSTALACAO.md](../../agent-windows/INSTALACAO.md),
   confirmar Windows x64, DSN de sistema SQL Anywhere x64 acessível à conta do
   serviço e credencial somente leitura. Gerar/revisar o MSI no Windows/CI e
   conferir checksum. Não instalar o agente Python nem um segundo serviço.
4. **Pareamento:** usar a URL HTTPS autorizada do CICA e código temporário;
   conferir certificado do agente, assinatura do corpo e o isolamento do tenant.
   O agente faz conexões de saída; não abrir o banco Domínio à internet nem
   desativar validação TLS. Verificar serviço `CicaAgent` e diagnóstico seguro.
5. **Contrato contábil:** validar consulta allowlisted e semântica da fonte real
   antes de habilitá-la. A consulta atual de itens de extrato não resolve esse
   passo. Completar a ligação com os candidatos do fluxo avançado preservando
   origem, partidas, conta e documento; sem inventar contrapartida.
6. **Títulos e DE-PARA:** definir o cadastro inicial a partir do plano de contas
   e mapa da cliente, com revisão humana. Implementar a comparação de títulos
   pela fonte e regras confirmadas; não usar vencimento como pagamento. Antes
   de IA externa, resolver o conteúdo permitido e o custo de Q-08/Q-09.
7. **Conferência:** usar extrato, Razão, títulos e resultado esperado do mesmo
   recorte; verificar saldos, sobras nos dois sentidos, parcelas, pagamentos
   parciais/agrupados, tarifas, transferências, estornos e sobreposição. Aplicar
   os 200 itens independentes e os critérios de D-73; 200 itens sintéticos não
   substituem a revisão da cliente nem provam precisão de 95%.
8. **Histórico e recuperação:** executar a auditoria abaixo em escritório
   explicitamente autorizado; revisar achados sem apagar decisões. Ensaiar
   agente/rede indisponíveis, retry, reinício, revogação, reativação e retomada
   em até 15 minutos; restore até quatro horas e demais gates D-73.
9. **Saída e aceite:** se houver arquivo ERP no resultado Q-47, conferir
   importação/retorno e ausência de duplicidade antes de habilitar o gate
   contábil. Registrar release, contagens, erros, responsável e aceite.
   Realizar treinamento inicial e acompanhar os primeiros usos.

Auditoria somente leitura, após preparar o ambiente autorizado:

```text
python manage.py audit_ofx_integrity --organization UUID_DO_ESCRITORIO
```

A saída traz contagens de problemas, `read_only=true` e `homologated=false`.
Zero achados ou nenhum registro não equivale a aceite. Não executar contra
outro escritório nem corrigir histórico automaticamente.

## Próxima dependência concreta

**Responsável:** fornecer o acesso prometido ao PC por canal protegido e definir
com a cliente uma empresa/conta/mês autorizado, extrato, Razão já conferido,
fonte/lista de títulos e plano de contas/DE-PARA existente. **Desenvolvimento:**
completar os adaptadores e a ligação dos fluxos sobre essa evidência, validar
as regras/destino remanescentes e executar o piloto. Não solicitar novamente
modalidade local, computador de instalação ou inclusão de pagar/receber.

Sem esse material, a conclusão contratual e o aceite continuam pendentes.
Não houve deploy, instalação remota, consulta ao ERP, baixa, escrituração,
transmissão, IA externa, mensagem a terceiros ou custo nesta entrega.
