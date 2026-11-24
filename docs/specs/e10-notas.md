# E10 — Serpro completo: notas de T10.1 e T10.2 (23/11/2026)

Registro de decisões do worktree `claude/e10-serpro-catalogo-0fdab1`. Sem entradas em `DECISOES.md` e `VALIDACOES.md` de propósito: a numeração do `origin/main` (D-396, V-447) colide com a da branch local do produto. Quem integrar numera.

Fontes: catálogo oficial de 15/10/2026 e a página de cada serviço, https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/ (lidas em 23/11/2026, só documentação, nenhuma chamada ao gateway); `docs/pesquisa/serpro-integra-contador-mcp.md` (apêndice A) e `docs/specs/cica-venda-v2.md` da branch `feat/produto-vendavel`.

## T10.1 — registro dirigido por tabela

- `integra/catalog_table.py` guarda os 99 serviços em produção (uma linha cada; parcelamento gerado de `MODALIDADES` × `OPERACOES`). `integra/catalog.py` deriva o resto e recusa linha contraditória na importação.
- As 19 chaves antigas mantêm chave, ids, verbo, label e `billable`. A `versaoSistema` de três delas mudou (ver abaixo).
- Classes: A 68, B 1, C 4, D 18, E 1, F 6, G 1 (soma 99). A conta da spec (56 leituras e 16 emissões faltando) está deslocada em um: o catálogo dá 55 e 17 (soma 80 igual). O "56" fecha contando o `DETPAGTOPARC165` do PARCSN, que não tinha leitor.
- `copilot_allowed`: classe A inteira (68) mais `SITFIS RELATORIOSITFIS92`, que a pesquisa manda liberar. Os outros três "opcionais" (`PAGTOWEB 72`, `CCMEI 121`, `PNRCONTADOR 264`) ficam desligados até decisão do dono. Total 69.
- `needs_confirmation = not copilot_allowed`: o que o copiloto não chama sozinho exige confirmação humana. `MSGDETALHAMENTO62` (ciência da intimação) é bloqueado e exige confirmação.
- `billable`: falso em Apoiar e Monitorar (9 serviços), verdadeiro nos outros 90.
- `versaoSistema` conferida por serviço: tudo `1.0`, exceto SITFIS 91 e 92 = `2.0`, SICALC 51 a 54 = `2.9`, EPROCESSO = `2.0`, PROCURACOES = `1`. SITFIS e PROCURACOES (3 chaves antigas) mandavam `1.0`: aplicado o valor oficial, **muda o envelope dessas 3 chamadas; validar no trial antes da produção**. CCMEI 121 e PGMEI 21 não trazem versão em lugar nenhum da doc: usam `1.0` e ficam com `versao_confirmada=False`.
- `integra_catalog_check` (`--file` offline, `--strict` falha em divergência) compara o registro com a página oficial; só usa a rede sem `--file`, nunca em teste. Também lista páginas de serviço do menu sem registro (hoje: Caixa Postal 64 a 66, e-Processo 272 a 274, DASN-SIMEI).
- `integra_smoke` recusa classes E e F ao executar e pede `--confirm-effect` para ciência da intimação em produção. O pedido de confirmação de custo mantém o lugar e o fluxo dos guias não muda.
- Efeito fora do pacote: `platform/forms.py` monta a lista de tarifa com `SERVICES` faturáveis; passa de 15 para 90 opções. Não toquei no arquivo (fora do escopo).

## T10.2 — leitores tipados

- Motor em `integra/typed/base.py`: modelos como dataclass com `Annotated[T, J("campoJson", fmt=...)]`, leitura estrita e limitada, PDF/XML só decodificados e validados (PDF com assinatura e EOF; XML sem DTD nem entidade), erros que nomeiam o caminho e nunca o valor. Requisições validam formato e intervalo, CNPJ numérico ou alfanumérico por `normalize_cnpj`.
- Fixtures em `tests/fixtures/integra/serpro/`: exemplos oficiais com a página de origem e a nota de cada correção. Os exemplos oficiais costumam trazer vírgulas faltando ou caracteres perdidos; só entram os que são JSON válido ou que a tabela da doc reconstrói sem inventar valor.
- Parcelamento: lista de pedidos, parcelas disponíveis e detalhe de pagamento têm os mesmos campos nas 8 modalidades (conferido tabela a tabela), então um leitor serve todas e o registro tipado (32 consultas) sai da tabela de modalidades. Só o bloco de consolidação do detalhe do parcelamento muda por modalidade; é lido quando traz os nomes do PARCSN e fica vazio nas outras.
- Correção em leitor existente: `parcelamento.detalhe()` exigia o envelope `parcelamento`, mas todo exemplo oficial válido responde o parcelamento direto. Passou a ler as duas formas; `numero_esperado` virou opcional.
- Estado: 59 leituras tipadas em `integra/typed_registry.py` (27 serviços de 10 sistemas + 32 consultas de parcelamento); as 9 leituras antigas sem leitor tipado estão listadas em `LEGACY_UNTYPED_READS` e o teste de cobertura exige que seja só essas.
- Divergências doc × exemplo (campos com duas grafias, `textoResolucao` do regime que vem em texto puro, status `"200"` em texto no e-Processo, exemplos com valores perdidos reconstruídos da tabela) estão registradas em `notes` de cada fixture e nas docstrings dos módulos. Palpites: DEFIS 142 (ano e tipo de dois itens) e a fixture 202 do EVENTOS 133.

## Pendências e pré-requisitos

- EVENTOSATUALIZACAO (131 a 134) precisa de lote de contribuintes (tipos 3 e 4) no `envelope.Party`; hoje só CPF e CNPJ. Pré-requisito de T10.5.
- 9 leituras antigas seguem sem leitor tipado (usam leitura própria no hub): `procuracao.obter`, `dte.situacao`, `caixapostal.indicador`, `caixapostal.mensagens`, `dctfweb.xml`, `dctfweb.recibo`, `dctfweb.declaracao_completa`, `pgmei.divida`, `sitfis.protocolo`.
- Teste do gate `test_account_discovery_archive.py::test_stage_permissions...` falha no Windows (espera `0o700`, o sistema devolve `0o777`); não vem deste trabalho.
- `test_legacy_contract`, `test_migration_safety` e `test_tenant_isolation_matrix` só existem na branch local do produto; a sessão pai roda na integração.

## T10.3 a T10.4 e tools (fase 2, sem chamada ao Serpro)

- **Termo de Autorização** (`integra/termo.py`): XMLDSig enveloped, RSA-SHA256, C14N 1.0, só o certificado final, documento escrito já em forma canônica (atributos ordenados, sem tag vazia, sem indentação nem Unicode oculto). `sign_termo` recusa certificado que não é do autor; `verify_termo` confere digest e assinatura por C14N independente. O token (`autenticar_procurador_token`) é comprado em `AUTENTICAPROCURADOR/ENVIOXMLASSINADO81` (caminho `/Apoiar`, não cobrado) e fica em cache até a meia-noite seguinte de Brasília ou a expiração informada, o que vier antes. `IntegraClient.call` aceita `autenticar_procurador_token` e `request_tag` (`X-Request-Tag`, até 32 caracteres).
- **Modos por escritório** (`integra/identity.py`, `OfficeSerproIdentity`): `default` (comportamento de antes), `platform_termo` (contrato da plataforma + Termo assinado com o e-CNPJ do escritório) e `own_contract` (consumer key e secret do escritório, mTLS com o e-CNPJ A1 dele, escritório como contratante e autor). Flag `INTEGRA_OFFICE_IDENTITY_ENABLED`, lida com `getattr(settings, ..., False)`: **ainda não existe em `settings/base.py`** (fora do escopo desta sessão); desligada por padrão. O nome da plataforma no Termo vem de `INTEGRA_CONTRATANTE_NAME` (padrão "CONTRATANTE"): configurar antes de ligar.
- **Governador** (`integra/governor.py`, `IntegraCall`): reserva o custo sob trava da linha da organização antes de enviar (achado da revisão de segurança automática) e acerta depois; 200, 202 e 403 contam nos caminhos pagos, Apoiar e Monitorar e os demais status não. Preço de referência é o da 1ª faixa (R$ 0,24 / 0,32 / 0,40), teto, não o preço real. Limites padrão: R$ 50 por mês e R$ 5 por conversa por escritório (`OfficeSerproIdentity`), 20 chamadas por conversa. Pré-checagem de procuração (OBTERPROCURACAO41, cache de 10 min se ok e 5 min se ausente) antes de qualquer chamada paga; ela própria é uma Consulta e entra na conta. Nada usa o governador ainda: os chamadores atuais do hub seguem como estavam.
- **Migração**: `integra/0001_initial` (duas tabelas novas, aditiva). O app `integra` ganhou `apps.py` e `models.py`.
- **`integra/tools.py`**: 59 ferramentas `serpro_<chave>` (leituras tipadas com `copilot_allowed`), com schema, custo, validação de argumentos, auditoria sem o número do contribuinte e retorno sem documento (PDF e XML viram tipo, tamanho e hash). É dado do Serpro: fora de LLM externo até a resposta do Serpro (pergunta 3 de `perguntas-serpro.md`).

## T10.5 e T10.6 (fase 3, sem chamada ao Serpro)

- **Radar** (`integra/radar.py`, modelos `RadarRequest` e `RadarSignal`, migração `integra/0002`, depende só de `hub/0001`): pede E0301, E0601 e E0701 em lote de até 1.000 CNPJs (`BatchParty`, tipo 4, em `envelope.py`), espera o tempo médio que o gateway informa, coleta uma vez (a entrega é única) e grava um sinal por empresa e evento: data do último evento ou "sem procuração" (`x`). Gratuito (`/Monitorar`); nunca abre mensagem da Caixa Postal. Só lê.
- **Tarefa** `integra.radar_tick` (`integra/tasks.py`): no-op com a flag desligada e só visita escritório que tem linha em `OfficeSerproIdentity`; falha de um escritório não para os outros. **Sem entrada no beat**: agendar no deploy que ligar a flag.
- **Telas** (`integra/views.py`, templates em `integra/templates/integra/`): `/app/serpro/` (modo, estado do Termo, custo por mês e % do limite, só dono e administrador) e `/app/serpro/radar/` (empresa × DCTFWeb, Caixa Postal, Pagamentos). Sem entrada no menu: acesso por URL até a decisão. Molde do módulo de procurações (classes e estados existentes), sem CSS novo, sem parágrafo explicativo; **não verificado em navegador a 375 px**.
- **Flags novas, todas desligadas por padrão e lidas com `getattr(settings, ..., False)`** (ainda não declaradas em `settings/base.py`): `INTEGRA_OFFICE_IDENTITY_ENABLED`, `INTEGRA_RADAR_ENABLED`, `INTEGRA_SCREENS_ENABLED`; mais `INTEGRA_CONTRATANTE_NAME` (texto).
- **Rotas novas**: `hub:serpro` e `hub:serpro-radar` (duas linhas em `hub/urls.py`).

## Não feito nesta fase

- **Agregador de situação por empresa** (SITFIS, DTE, parcelamentos, pagamentos, índice PGDAS-D `dasPago`/`malha`) e a tela "o que fazer hoje": o radar só traz os três eventos; o agregador consulta serviços pagos e depende do governador ligado nos chamadores.
- **T10.6, telas de operação** (demais parcelamentos, MIT, PGDAS-D, DEFIS, CCMEI, SICALC, comprovante) com cotação, confirmação humana e PDF persistido: não começadas. Pedem o pipeline de UI do CLAUDE.md (referência de mercado, 375 px, contraste).
- Ligar o governador e os modos nos chamadores atuais do hub, e a flag em `settings/base.py`.
