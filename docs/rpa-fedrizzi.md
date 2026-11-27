# RPA do agente Windows: Folha, FGTS Digital, DET, FAP e Admissões

Porte (26/11/2026) dos blocos RPA do HubFedrizzi para o CICA, como módulos **por escritório**,
desligados por padrão. `provision_office` (Fedrizzi) liga os cinco; nenhum entra no autosserviço.
Decisão registrada em D-430; validações pendentes em V-490.

## Desenho

| Peça | Onde | O que faz |
|---|---|---|
| Fila genérica | `src/apps/rpa` | `RpaJob` org-scoped, idempotente por (escritório, tipo, chave), reserva com `lease_token` que gira a cada reivindicação (só o hash fica no banco), heartbeat com fase, resultado/falha, artefatos com SHA-256, trilha `RpaJobEvent`. |
| Registro de tipos | `rpa/registry.py` | Cada bloco registra tipos: módulo dono, grupo exclusivo (uma só sessão do desktop por escritório), fases **sem volta**, gancho `prepare_claim` (travas reconferidas **na entrega**), `transient_claim` (carga com dado pessoal nunca é gravada), chaves de resultado aceitas. |
| API do agente | `/api/agent/v2/rpa/{next,<id>/heartbeat,<id>/artifacts,<id>/complete,<id>/failure}` | Mesma autenticação do agente (HMAC/mTLS). `RPA_AGENT_ENABLED` desligado ⇒ 404. Agente com recorte (`sync_scope`) é recusado. |
| Agente .NET | `agent-windows/…/RpaJobRunner.cs`, `RpaProcessor.cs` | Pede só os tipos que tem executor **na configuração local** (`RpaExecutors`, DPAPI); mantém o heartbeat; sobe arquivo com hash; texto de exceção nunca sobe (só o tipo); segredo mascarado. Executor = processo filho (ex.: worker Python x86 do Domínio) por stdin/stdout JSON; arquivo só vale dentro de `RpaOutputRoot`, sem ponto de reanálise. |
| Segredo | `rpa/redaction.py` | Carga/resultado com chave de aparência sensível (`senha`, `token`, `certificado`…) são recusados; erro/evento passam por mascaramento (senha, bearer, blob longo, CPF). Credencial do Domínio/portal fica no Cofre do Windows da máquina; nunca no servidor. |

Estados do trabalho: `queued → leased → succeeded | failed | uncertain | cancelled`.
Reserva vencida volta à fila, **exceto** se o agente já estava numa fase sem volta (ex.: `emissao`,
`gravando`): aí vira `uncertain` e só uma pessoa decide. Falha permanente (`validacao`,
`conferencia_divergente`, `bloqueado_por_trava`) nunca repete.

## Blocos

### Folha (`apps.folha`, módulo `folha`)
- **Portado:** ciclos (rascunho/fila/parcial/conferência/aprovação/concluído), tarefas por empresa/item
  com índice único de tarefa ativa, lista autorizada **do escritório** (vazia = nada; `*` recusado),
  confirmação do cálculo (único item que altera o Domínio; nunca anexado), reprocesso, cancelamento,
  catálogo de campos fail-closed + extração do PDF (reprova sem catálogo), conferência/correção com
  justificativa, destinatário fail-closed (`recipients.py`: marcas FOLHA/PAGTO, recusas, ambíguo
  pergunta), rascunho → aprovação → envio idempotente, falha de envio só reconciliável com justificativa,
  anexo com hash conferido na aprovação e no envio, agenda diária 06:00 (celery) que cria só rascunho,
  recuperação de dias perdidos, títulos de relatório (`FolhaTitle`), histórico (telas de ciclo),
  planilha Google Sheets (aba/linha/uma marcação por etapa, nunca sobre célula preenchida, recuo até
  6 h, `final_error` em 20), `folha.contatos` (leitura dos contatos na Domínio pelo agente).
- **De fora:** o motor pywinauto/x86 (fica como executor externo do agente, não vive neste repo);
  retenção de 5 anos/CSV de histórico; edição de títulos pela UI (modelo pronto); envio pelo módulo
  `delivery` da main (hoje usa o transporte Django padrão; trocar quando o fluxo for integrado);
  pasta do cliente/arquivamento (sessão de envio/pastas).
- **Validação pendente:** ver roteiro F1–F6.

### FGTS Digital (`apps.fgts`, módulo `fgts`)
- **Portado:** fonte (`fgts.fonte`, leitura da apuração pelo agente), lote (≤200 grupos, um item vivo
  por raiz/competência), conferência no portal (`fgts.conferir`, **nunca emite**), comparação de valor
  e vencimento **feita pelo servidor**, três travas de emissão (`FGTS_EMISSAO_HABILITADA` global +
  `source_validated` + `emission_enabled` do escritório) reconferidas na entrega ao agente,
  emissão `max_attempts=1`, fase `emissao` sem volta ⇒ `incerto`, resolução humana (com PDF ou
  “sem guia”), PDF validado (assinatura, tamanho), dinheiro em centavos inteiros.
- **De fora:** SQL do Domínio e login/seletores do portal (executor do agente); integração do PDF no
  Fechamento por Recibo (`closing`, outra sessão); reenvio de grupos preparados após retomada.
- **Validação pendente:** G1–G5. **Emissão segue bloqueada** até a fonte ser comparada com guias reais.

### DET (`apps.det`, módulo `det`)
- **Portado:** consulta em pedaços de 10 empresas, seleção congelada (ativa, CNPJ 14 dígitos), carga
  `list_only` obrigatória, resultado só de empresa pedida (código **e** CNPJ), contador do portal =
  linhas lidas senão “consulta inconclusiva” e descarta linhas, `opened_any` vira alerta (nunca
  escondido), reenvio substitui, planilha XLSX (Mensagens/Pendências/Resumo) com neutralização de
  fórmula, aviso “espera uma pessoa” pela fase `atencao`.
- **De fora:** motor Playwright (`robo_det`), login assistido por certificado/captcha, e-mail de atenção.
- **Validação pendente:** D1–D3.

### FAP (`apps.fap`, módulo `fap`)
- **Portado:** lote com teto (3→10→0), cadastro conferido (CNPJ com dígito verificador; alfanumérico
  novo ainda recusado; repetido recusado), uma consulta viva por CNPJ+vigência, travas
  `enabled`/`portal_validated` reconferidas na entrega, PDF validado **pelo servidor** (título e seções
  oficiais, CNPJ rotulado, vigência rotulada), nunca “concluído” sem isso (vai a revisão), pausar/
  retomar, reprocesso com motivo preservando o PDF antigo, download protegido (`no-store`, hash).
- **De fora:** gravar o PDF na pasta do cliente na rede (sessão de envio/pastas), inventário de
  pastas, “existente”/reaproveitamento.
- **Validação pendente:** P1–P3.

### Admissões (`apps.admissions`, módulo `admissions`)
- **Portado:** ficha com revisão humana obrigatória, validação por **nome de campo** (nunca valor),
  CPF/dependentes/vale-transporte, `cpf_hash` (HMAC) único por empresa em pedido vivo, ficha cifrada,
  travas (`execution_enabled`, lista autorizada, empresa de exemplo só com confirmação) reconferidas
  na entrega, ficha **só na resposta ao agente** (`transient_claim`), `max_attempts=1`, fase
  `gravando` sem volta ⇒ `incerto`, conferência divergente ⇒ `incerto`, retenção de 90 dias
  (`expire_admissions` + tarefa diária).
- **De fora:** leitura automática da ficha (texto/OCR/extração), catálogo da empresa na Domínio,
  as 78 verificações SQL (agora devolvidas pelo agente em `divergences`), digitação no Domínio.
- **Validação pendente:** A1–A3.

## Roteiro de validação no servidor da Fedrizzi (nada disto foi possível aqui)

Pré-requisitos: agente instalado; `RPA_AGENT_ENABLED=true`; `RpaExecutors` e `RpaOutputRoot` no
`agent.config` apontando ao worker; credenciais no Cofre do Windows da conta interativa.

1. **F1 smoke da fila:** habilitar só `folha`; autorizar **uma** empresa de teste; criar ciclo `extrato`
   (sem cálculo); ver `reservado → concluido` em `RpaJobEvent` e o PDF em `RpaArtifact`.
2. **F2 cálculo:** só na empresa de teste, com confirmação; conferir que nada é anexado ao e-mail.
3. **F3 desktop único:** disparar folha + admissão juntas; confirmar que o segundo espera o primeiro.
4. **F4 queda:** matar o worker no meio; reserva volta à fila após o prazo (ou `incerto` em fase sem volta).
5. **F5 catálogo:** sessão de mapeamento com PDFs reais; cadastrar `FolhaCatalog`; conferir campos.
6. **F6 planilha:** conta de serviço com acesso de editor; marcar competência/empresa de teste; conferir
   que célula preenchida à mão não é sobrescrita.
7. **G1–G5 FGTS:** comparar a apuração com 2+ competências de guias reais; ligar `source_validated`;
   piloto com 1–3 grupos em ambiente de teste; só então `emission_enabled` + `FGTS_EMISSAO_HABILITADA`.
   Testar queda após o clique (deve cair em `incerto`, nunca repetir).
8. **D1–D3 DET:** conferir seletores; empresa com mensagem não lida: contador igual antes e depois;
   sem procuração e CNPJ não encontrado.
9. **P1–P3 FAP:** seletores observados; uma empresa; PDF aceito pelo servidor; sem permissão.
10. **A1–A3 Admissões:** só na empresa de exemplo com confirmação; conferir `domain_code` e
    divergências; sem CPF em log/eventos.

## Fontes consultadas (26/11/2026)

- FGTS Digital, manuais e documentação técnica (v1.50, 20/03/2026), gov.br:
  <https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica/manual-do-orientacao-do-fgts-digital-versao-1-50-20-03-2026.pdf>
  (só o sumário apareceu na busca; **os passos de emissão por procurador não foram lidos** — hipótese a validar).
- Sistema de Procuração Eletrônica (FGTS Digital e DET por procurador):
  <https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica/manual-do-orientacao-do-spe-v1-1-01-03-2024.pdf>
- DET (gov.br): <https://www.gov.br/domicilio-eletronico-trabalhista-det>. Fontes secundárias divergem
  sobre o marco da ciência (CLT art. 630 §6º, tácita em 15 dias; Portaria MTP 671/2021): por isso a
  regra “nunca abrir mensagem” é mantida.
- FAPWeb v1.3 (vigência, CNPJ raiz, estabelecimento):
  <https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/saude-e-seguranca-do-trabalhador/fap/manuais/V1.3_MANUAL_DE_ACESSO_AO_NOVO_FAP_atualizado_em_02.02.2024.pdf>
- Padrão de fila com reserva: Amazon SQS visibility timeout (entrega ao-menos-uma-vez ⇒ consumidor
  idempotente; heartbeat estende a reserva): <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/AboutVT.html>.
  Cerca por versão/token de reserva (atualização de agente atrasado afeta zero linhas): implementada
  como `lease_token` rotativo. Não pesquisei Temporal (busca não trouxe).
