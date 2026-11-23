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
- Estado de cada sistema: ver o relatório final da sessão.

## Pendências e pré-requisitos

- EVENTOSATUALIZACAO (131 a 134) precisa de lote de contribuintes (tipos 3 e 4) no `envelope.Party`; hoje só CPF e CNPJ. Pré-requisito de T10.5.
- 9 leituras antigas seguem sem leitor tipado (usam leitura própria no hub): `procuracao.obter`, `dte.situacao`, `caixapostal.indicador`, `caixapostal.mensagens`, `dctfweb.xml`, `dctfweb.recibo`, `dctfweb.declaracao_completa`, `pgmei.divida`, `sitfis.protocolo`.
- Teste do gate `test_account_discovery_archive.py::test_stage_permissions...` falha no Windows (espera `0o700`, o sistema devolve `0o777`); não vem deste trabalho.
- `test_legacy_contract`, `test_migration_safety` e `test_tenant_isolation_matrix` só existem na branch local do produto; a sessão pai roda na integração.
