# Matriz por cliente (A12)

Data da matriz: 21/11/2026. Regra: o guia do dono ([docs/dominio-mcp.md](../../docs/dominio-mcp.md)) só declara compatibilidade com o cliente que tem linha "testado em <data e versão>" abaixo. Os demais ficam "pendente de teste real" e não entram em promessa.

## Resultado

Itens: **inicialização** (conecta, `instructions` chegam), **descoberta** (10 ferramentas com descrição e dica de somente leitura, recursos e roteiros), **execução** (ferramenta devolve resultado), **confirmação** (o cliente pede ou não permissão antes de executar), **resposta truncada** (teto de 12 KB, `truncado` e `proximo_passo`), **reconexão** (novo processo depois de a sessão acabar).

| Cliente | Inicialização | Descoberta | Execução | Confirmação | Resposta truncada | Reconexão | Testado em |
|---|---|---|---|---|---|---|---|
| Cliente do SDK `mcp` 2.3.0, stdio | ok | ok | ok | não se aplica | ok | ok | 21/11/2026, `mcp` 2.3.0 |
| Cliente do SDK `mcp` 1.30.0, stdio | ok | ok | ok | não se aplica | ok | ok | 21/11/2026, `mcp` 1.30.0 |
| Claude Desktop | pendente de teste real | pendente | pendente | pendente | pendente | pendente | não testado |
| Claude Code | pendente de teste real | pendente | pendente | pendente | pendente | pendente | não testado |
| ChatGPT por túnel seguro | pendente de teste real | pendente | pendente | pendente | pendente | pendente | não testado |
| Claude na web e no celular | fora da Fase 1 (gateway da Fase 2) | | | | | | não testado |

"Não se aplica": a confirmação é da interface de cada cliente; um cliente de SDK não tem.

## O que os dois clientes de SDK provam e o que não provam

Provam, com o servidor real do pacote (backend ODBC falso, pack sintético) por stdio de verdade (processo filho, enquadramento JSON-RPC):

- o protocolo `2025-11-25` é negociado entre o servidor com `mcp` 2.3.0 e um cliente `mcp` 1.30.0;
- as 10 ferramentas, os dois recursos e os dois roteiros aparecem, todas as ferramentas com `readOnlyHint: true`, `destructiveHint: false` e `openWorldHint: false`, e os primeiros 512 caracteres de `instructions` já dizem "SOMENTE LEITURA";
- erro de negócio chega como `isError` com `{"erro":{"codigo":...}}` estável (`coluna_bloqueada`);
- um resultado de 120 linhas largas é cortado em 12.233 bytes (teto 12.288) com `truncado: true` e `proximo_passo`;
- uma segunda sessão, com outro processo, inicializa e lista as ferramentas.

Não provam o comportamento de nenhum produto real: confirmação por ferramenta, permissões "sempre permitir", tratamento de resposta longa pelo modelo, reconexão automática do aplicativo, tempo limite do cliente e o primeiro arranque do `uv` dentro do aplicativo.

Como reproduzir:

```powershell
uv run --directory dominio-mcp pytest -q tests/test_e2e_stdio.py tests/test_server_contract.py tests/test_markers_e2e.py
$py = (uv run --directory dominio-mcp python -c "import sys; print(sys.executable)").Trim()
uv run --no-project --with mcp==1.30.0 python dominio-mcp/tests/compat/client_v1.py $py <pasta vazia>
```

O primeiro comando cobre o cliente 2.3.0 (stdio real e em memória). O segundo sobe o servidor real com o Python do pacote e conversa com o SDK 1.30; imprime uma linha por item e termina com `TUDO OK`.

## Roteiro do teste real (um cliente de cada vez)

Pré-requisito: `doctor` limpo e pack gerado (o `build-pack` sem `--aceitar` basta: L0 e as quatro rotinas L1 funcionam; `consulta_estruturada` só alcança coluna depois do aceite).

| Item | Como fazer | O que registrar |
|---|---|---|
| Inicialização | Ligar o servidor como no guia. Perguntar ao modelo o que o servidor `dominio` diz de si. Conferir o stderr do servidor (versão do pack e perfil `remote`). | Aparece conectado? `instructions` chegaram? Tempo até conectar na primeira vez (o `uv` pode baixar dependências). |
| Descoberta | Pedir a lista de ferramentas. | Quantas aparecem; se alguma é tratada como escrita (o ChatGPT trata como escrita a ferramenta sem a dica de somente leitura). |
| Execução | `mapa_do_banco`; `buscar_esquema` com "notas fiscais de saída"; `empresas` com `limite` 3; `movimento_fiscal` de uma empresa em 3 meses. | Cada resposta chegou inteira? O modelo citou `lido_em` e a nota de diagnóstico? |
| Confirmação | Observar o que o cliente pergunta antes de rodar cada ferramenta e as opções de "permitir sempre". | Texto da pergunta, se a dica de somente leitura muda algo, se "permitir sempre" existe. |
| Resposta truncada | `empresas` com `limite` 500; depois do aceite, `consulta_estruturada` com `limite` alto numa tabela larga. | `truncado: true` apareceu? O modelo seguiu `proximo_passo` ou inventou o resto? |
| Reconexão | Encerrar o processo `dominio-mcp` no Gerenciador de Tarefas no meio da conversa; depois fechar e reabrir o cliente. | A próxima chamada reconecta sozinha? Que mensagem o cliente mostra? |

Para cada cliente, anotar também: versão do cliente, sistema operacional, data, e se o `uv` precisou de caminho completo. Só então trocar a linha da tabela por "testado em <data>, <cliente> <versão>" e liberar a menção no guia.

## O que fica de fora

Cliente de terceiros que não seja Claude Desktop, Claude Code ou ChatGPT. Compatibilidade com versões futuras do SDK `mcp`: o pacote fixa `mcp==2.3.0` e só muda de versão com os testes desta matriz rodados de novo.
