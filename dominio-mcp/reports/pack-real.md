# Pack real — prova no banco do Domínio (A1 e A2, parte do build)

Data: 21/11/2026. Banco: SAP SQL Anywhere 17.0.11.7312, DSN de sistema `contabil` (usuário Externo). Somente leitura. O pack vai para `%LOCALAPPDATA%\dominio-mcp\packs\contabil\`, fora do git.

Comando (sem `--aceitar`: a decisão de aceitar o catálogo é do dono):

```powershell
uv run --directory dominio-mcp python -m dominio_mcp.buildpack
```

Saída (só números, nenhum comentário, nome de coluna bloqueada ou valor de linha):

```
pack f5c4c715b279 publicado (32.8 MB)
versao: f5c4c715b2795f802b51f0104eca5f72430aa06cf13817c4b6cc97885b430550
servidor: 17.0.11.7312 / contabil
tabelas: 4964 | colunas: 58484 | chaves estrangeiras: 6803
colunas por classe: documento 169, nao_classificada 50939, pessoal 5007, segredo 212, texto_livre 2157
colunas aceitas: 0 (novas neste pack: 0)
objetos ilegiveis para este usuario: 18
48560 colunas sem classificacao ficaram BLOQUEADAS; rode com --aceitar para aprovar o catalogo atual
tempo: leitura 2.1 s, legibilidade 17.0 s, geracao 13.9 s, total 32.9 s
```

## Critérios

| Critério | Resultado |
|---|---|
| A2: pack em ≤ 5 min | 32,9 s no total (leitura do catálogo 2,1 s; sonda de legibilidade dos 4.964 objetos 17,0 s; geração 13,9 s) |
| A2: pack em ≤ 100 MB | 32,8 MB |
| Contagens iguais às medidas | 4.964 objetos, 6.803 FKs e 18 objetos ilegíveis, como na evidência 03 e 07 |
| Controle da sonda de legibilidade | `SYS.SYSUSERPERM` foi negado, então a sonda distingue objeto negado |
| Sem aceite, nada abre por engano | 48.560 colunas sem regra ficam `nao_classificada` (bloqueadas); mais 2.379 colunas das 102 views, bloqueadas até a aprovação de cada view |

## Frescor contra o banco real

Com o pack recém-gerado, `FreshnessGuard.check` (re-hash completo do catálogo + sonda de base) levou 2,79 s e **não** acusou desatualização; a sonda barata seguinte levou 36 ms. Os hashes de estrutura, views e comentários do catálogo reextraído batem com os do pack.

## O que esta prova não cobre

- A recusa por objeto no catálogo real com contagem de motivos e a revisão independente de 300 colunas (A7b e A7c) ficam para o marco M7.
- A classificação de colunas é heurística sobre nome e comentário; o que ela não pega é o limite declarado da promessa de privacidade.
- `MAX(last_modified_at)` não entra na sonda de frescor: andou de 14:00 para 18:00 sem mudança de DDL (evidência 13).
