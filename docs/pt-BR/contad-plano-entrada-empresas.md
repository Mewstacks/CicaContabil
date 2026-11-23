# CICA × CONTAD — plano de entrada das empresas em lotes (23/11/2026)

**Situação:** proposta, aguardando aprovação do responsável. Quando aprovada, vira decisão própria
em `DECISOES.md` antes de o primeiro lote começar (AGENTS.md).

**Ponto de partida (V-450, release v122):** a CONTAD está em uso direto (D-393), mas só a SURIA
(Domínio 212) tem conta financeira. As outras 145 empresas entram quando a CONTAD importa o OFX de
cada conta: o vínculo nasce na própria importação (D-385) e o resto acontece sozinho (D-386/D-388/
D-392/D-393/D-397). Ou seja, a entrada de cada empresa depende do OFX dela, não de programação nova.

**Fonte da distribuição:** catálogo real dos planos lido do Domínio em 17/11/2026 (ZIP SHA-256
`7bbbd36b…cf35`, D-373), conferido de novo localmente nesta data, e a matriz de cobertura de 18/11
(V-415). Os números batem com V-432: 129 empresas com conta de banco no plano, 14 sem plano,
3 com plano e sem conta de banco, e 6 matrizes com filiais (D-381). Só códigos aparecem aqui,
sem nomes ou valores. "Contas de banco no plano" conta as contas analíticas do grupo bancário do
plano, pela mesma regra do código (`account_discovery_suggest.py`). Nem todas devem ter OFX.

## Regras que valem para todos os lotes

1. **Um OFX por conta, de 01/09/2026 até a data da importação.** A CICA confirma o vínculo e pede o
   Razão de cada mês coberto pelo arquivo (D-396). Não é preciso mandar um arquivo por mês.
2. **Na Nova importação, escolha a conta marcada "vincula pelo OFX".** Se o OFX for de uma conta já
   usada em outra empresa, a CICA recusa e mostra qual é a empresa (D-397). Pare e avise a equipe.
3. **Até o lote 0 passar, nenhum arquivo da CICA é importado no Domínio.** A CONTAD continua lançando
   como hoje. Quando o Razão novo mostrar o que o escritório já lançou, a CICA retira o lançamento
   dela que ainda não foi enviado (D-397).
4. **O próximo lote só começa depois de o anterior passar na conferência técnica** (abaixo). A
   conferência é feita pela equipe CICA; não se pede revisão à cliente (D-393).
5. **Cada leitura em produção pela equipe CICA precisa de autorização na sessão**, sempre somente
   leitura, como em V-450.

## Antes do lote 1 (equipe CICA)

- [ ] Abrir as telas da v122 com a sessão do escritório (carteira, importação, conferência,
      exportações, títulos). Esse passo ficou pendente em V-449.
- [ ] Definir o que fazer com a chave da IA, que vence em **13/12/2026** (D-395): renovar ou deixar a
      IA parar. Sem ela, as regras pelo Razão continuam funcionando.
- [ ] Confirmar com a CONTAD quem junta os OFX e como chegam (internet banking de cada empresa).

## Lote 0 — teste do arquivo no Domínio (SURIA, 212)

O arquivo lote 19 nunca foi importado de verdade no Domínio (D-380/V-428). É o maior risco de
ampliar: um erro de leiaute se repetiria em todas as empresas.

1. CONTAD importa o OFX da SURIA de 01/10 até hoje. A CICA pede os Razões de outubro e novembro.
2. Se a CICA gerar lançamentos (movimentos com regra e fora do Razão), clicar em *Atualizar Razão*
   e, depois, em *Exportações → Validar e gerar arquivo*, num período curto (1 ou 2 lançamentos).
3. No Domínio: *Utilitários → Importação → Importador*, Tipo TXT, "Lançamentos Contábeis em Lote
   (Leiaute Domínio Sistemas)", com "Importar somente registros inexistentes" marcado.
   Detalhes em [contad-teste-importacao-dominio.md](contad-teste-importacao-dominio.md).
4. **Passa se:** o Importador aceita o arquivo; conta, data, valor e histórico aparecem certos;
   reimportar o mesmo arquivo não duplica; no Razão relido, a CICA reconhece o lançamento como
   conferido e não gera outro.
5. **Se falhar:** guarde a mensagem do Importador e o arquivo. A equipe CICA corrige o leiaute antes
   de qualquer outro arquivo ir ao Domínio. **Os lotes 1 a 4 podem seguir mesmo assim**: a
   conferência funciona sem exportação.

Se não houver lançamento da CICA na SURIA (outubro e novembro todo conferido com o Razão), use a
primeira empresa do lote 1 que tiver um.

## Lotes de entrada

| Lote | Empresas | Contas de banco no plano | Lançamentos no Razão set+out | Critério |
|---|---:|---:|---:|---|
| Pronta | 1 | 5 | 1.985 | SURIA, já em uso |
| 1 — piloto | 8 | 10 | 4.465 | Filial única, 1 ou 2 contas de banco, volume médio; 3 delas (265, 341, 427) com fichas de conta preparadas |
| 2A | 27 | 42 | 10.049 | Filial única, 1 ou 2 contas, mais movimento |
| 2B | 28 | 37 | 1.311 | Filial única, 1 ou 2 contas, pouco movimento |
| 3 | 33 | 110 | 20.793 | Filial única, 3 ou 4 contas |
| 4 | 9 | 57 | 11.121 | Filial única, 5 ou mais contas |
| 5 — grupos com filiais | 18 | 95 | 47.215 | 6 matrizes e 12 filiais; só depois da checagem abaixo |
| 6 — sem movimento | 6 | 11 | 0 | Plano com banco, mas nenhum lançamento em set/out |
| 7 — sem conta de banco | 16 | 0 | 79 | Sem plano ou sem banco no plano; extrato sem Razão |
| **Total** | **146** | | | |

**Códigos das empresas (Domínio):**

- **Lote 1:** 2, 30, 139, 149, 265, 341, 351, 427.
- **Lote 2A:** 49, 51, 114, 121, 146, 204, 211, 254, 275, 277, 278, 281, 331, 332, 343, 349, 368, 394,
  425, 444, 445, 458, 459, 461, 467, 482, 485.
- **Lote 2B:** 83, 133, 255, 353, 358, 361, 363, 375, 384, 385, 413, 415, 428, 440, 450, 452, 455, 457,
  462, 465, 474, 475, 477, 483, 484, 492, 494, 495.
- **Lote 3:** 10, 54, 66, 84, 117, 128, 136, 166, 195, 214, 227, 236, 260, 279, 283, 295, 329, 345,
  377, 399, 410, 414, 416, 426, 431, 437, 448, 451, 466, 469, 478, 479, 486. A 283 usa o plano da
  279; entram juntas.
- **Lote 4:** 21, 22, 48, 111, 138, 182, 213, 490, 10000.
- **Lote 5:** matrizes 25 (filial 1002), 42 (355), 129 (359), 147 (220), 280 (191, 192, 333, 362) e
  293 (471, 472, 487, 491).
- **Lote 6:** 453, 470, 476, 493, 5000, 5001. A 476 usa o plano da 394.
- **Lote 7:** com plano e sem banco: 55, 252, 264. Sem plano: 372, 378, 379, 382, 430, 436, 439,
  460, 463, 464, 481, 488, 489. A 220 também não tem plano, mas está no lote 5 por ser filial da 147.

## Conferência técnica ao fim de cada lote (equipe CICA)

Leitura somente leitura em produção, mais a abertura das telas. O lote passa se:

1. **Cobertura:** cada empresa do lote tem ao menos uma conta com OFX importado, ou o motivo está
   anotado (por exemplo, "conta encerrada" ou "sem OFX ainda").
2. **Razão:** todo pedido de Razão do lote chegou. Registrar o tempo do pedido à chegada (mediana e
   máximo) e o tamanho da fila do agente. **Pare se** algum pedido falhar ou ficar parado mais de
   30 minutos sem explicação. Até agora só foram medidas coletas de Razão da SURIA e de títulos de 3
   empresas; o lote 1 é a primeira medida real de capacidade com várias empresas ao mesmo tempo.
3. **Conta certa:** nenhuma conta bancária em duas empresas. Em 2 empresas do lote, a conta do Domínio
   vinculada corresponde ao banco do OFX.
4. **Sem dobra:** nenhum lançamento da CICA que também esteja no Razão relido. Amostra de até 10
   lançamentos da CICA conferidos contra o Razão pela equipe.
5. **Sistema:** sem erro novo nos registros do web e do worker; carteira e conferência abrem em tempo
   razoável com o volume do lote; IA dentro do teto (US$ 1/dia, US$ 5/mês). Se estourar, a IA só
   para, e isso não reprova o lote.

Resultado registrado em `VALIDACOES.md`, um item por lote, com o que passou e o que ficou.

## Lote 5 — antes de importar (equipe CICA)

Nas 6 matrizes, os lançamentos das filiais ficam na própria matriz, com o código da filial (D-381).
O vínculo automático usa a filial da própria empresa e, se ela não aparecer, a primeira filial
observada (`account_auto_link.py:181`). O pedido do Razão leva essa filial. Antes de importar:

- [ ] Confirmar no código do agente e num teste com a matriz 42 (pouco movimento, 3 contas) se o
      Razão pedido pela matriz traz os lançamentos das filiais.
- [ ] Combinar com a CONTAD em qual empresa entra o OFX de cada conta: matriz ou filial. Importar na
      filial pode trazer um Razão vazio e fazer a CICA lançar o que a matriz já escriturou. **Não
      importar OFX em empresa filial** até essa checagem.
- [ ] Se for preciso, rodar no SVAPL02 o leitor `inspect-contad-branch-accounts.ps1` (V-420, nunca
      executado) para saber a filial de cada conta de banco.

## Lote 6 — perguntar antes

Seis empresas têm conta de banco no plano, mas nenhum lançamento em setembro e outubro. Perguntar à
CONTAD se têm movimento bancário. As que tiverem entram no próximo lote aberto; as outras ficam como
estão.

## Lote 7 — extrato sem Razão

Funciona hoje: na importação, escolher **"Conta do extrato, lida do OFX (sem Razão)"** (D-393 item 6).
O extrato aparece, mas não há conferência com o Razão nem lançamento para o Domínio. Para entrarem no
fluxo completo:

- **55, 252, 264:** a CONTAD cria a conta do banco no plano do Domínio (hoje só há Caixa, V-432).
- **14 sem plano:** a CONTAD precisa cadastrar o plano no Domínio.
- Nos dois casos, a CICA tem de reler os planos: uma nova descoberta no SVAPL02 (D-373), executada
  pelo responsável. Não existe atualização automática do catálogo; o atual é de 17/11/2026.

## Quem faz o quê

| Quem | O quê |
|---|---|
| CONTAD | Juntar e importar os OFX de cada lote; teste do arquivo no Domínio (lote 0); responder sobre o lote 6; criar contas e planos no Domínio (lote 7) |
| Responsável CICA | Aprovar este plano; autorizar as leituras em produção; executar a descoberta no SVAPL02, quando necessária; decidir sobre a chave da IA |
| Equipe CICA (executor) | Conferência técnica de cada lote; checagem das filiais (lote 5); correção do leiaute se o lote 0 falhar; registros em VALIDACOES e no registro de execução |

## Fora deste plano

Aceite formal D-73 (deixou de ser condição de uso, D-393); restauração do banco (dispensada, D-379);
interpretação de títulos de Serviços e vínculo baixa × extrato (D-394); demais módulos da suíte.
