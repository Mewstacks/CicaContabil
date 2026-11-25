# Estudo — valor gerado por colaborador (módulo Rentabilidade)

**Data:** 25/11/2026. **Estado:** implementado localmente em 25/11/2026 (tela `/rentabilidade/valor/`, motor `calc.valor_por_colaborador`, `valor.py`, migração `0004`). Sem commit, sem deploy, sem inspeção visual em navegador.
**Relaciona:** [etapa 14](etapas/14-rentabilidade.md), Q-41 e Q-42 em [duvidas-abertas.md](duvidas-abertas.md).

## Problema

O cálculo atual (`profitability`, herdado do Lucrums/ProjetoARD) é `resultado = honorário − horas × custo/hora`. As horas vêm só do Domínio (automáticas e F9). Trabalho feito fora do Domínio não entra, e a cobertura medida em 21/09/2026 era de 11% (Q-42). A margem por cliente lê alto demais e não responde quanto cada pessoa traz.

## Mudança de abordagem (decisão do dono, 25/11/2026)

Não depender de tempo apontado. Pergunta nova: **quanto cada colaborador gera de valor para o escritório**, partindo da receita da carteira dele e do peso do departamento.

## Pesquisa

| Método | Onde aparece | Limite para este caso |
|---|---|---|
| Rateio do custo do setor pelo faturamento do cliente | Estudos de caso brasileiros (Anais do Congresso Brasileiro de Custos) | Cliente grande sempre parece caro |
| ABC / TDABC: custo × tempo por atividade | Kaplan e Anderson (HBS); caso de escritório com 19 clientes (2025) | Exige tempo apontado |
| Lucro do cliente = receita − (custo direto + overhead + baixas + tempo não faturável) | Intuit, Karbon, Canopy | Depende de horas |
| Crédito de receita por papel (originador, responsável, executor) | Escritórios de advocacia (LeanLaw, National Law Review) | Regra útil: os três créditos usam a mesma base de medida e a soma fecha com a receita |

Não há ferramenta de mercado nem repositório open source que atribua a receita de cada empresa aos departamentos por capacidade. O desenho é próprio e usa dois princípios emprestados: conservação (a soma dos créditos fecha com a receita, do crédito por papel) e driver de capacidade (do TDABC, sem o apontamento).

Fontes: karbonhq.com e capterra.com (comparativos), intuit.com/enterprise/blog/professional-services/client-profitability, leanlaw.co/blog/leanlaw-originating-responsible-working-attorney, library.hbs.edu/working-knowledge/adding-time-to-activity-based-costing, anaiscbc.emnuvens.com.br (rateio por faturamento), ideas.repec.org/a/kab/journl/y2025i1p34-33.html (TDABC em escritório contábil).

## Modelo

Para a competência `m`:

1. `F(c)` = mensalidade da empresa `c`.
2. `A(c)` = áreas que atendem `c` (as que têm responsável em `CompanyAreaResponsible`).
3. `cap(d)` = capacidade do departamento `d` = soma, sobre as pessoas do depto, de horas produtivas do mês (a mesma capacidade que o custo/hora já usa). Peso `w(d) = cap(d) ÷ Σ cap` .
4. Peso da área na empresa: `w(d | c) = w(d) ÷ Σ_{k ∈ A(c)} w(k)`. Área que a empresa não usa sai e os pesos se renormalizam.
5. Crédito da pessoa `p` (responsável da área `d` na empresa `c`): `F(c) × w(d | c)`.
6. `valor(p) = Σ créditos`. `margem(p) = valor(p) − custo(p)`, com `custo(p)` o custo do período já calculado pelo módulo.

Propriedade a testar: `Σ_p valor(p) = Σ_c F(c)` para toda empresa que tenha ao menos uma área com responsável.

## Decisões tomadas

| Decisão | Resposta |
|---|---|
| Fonte do tempo fora da Domínio | Nenhuma. Sem apontamento; o peso vem da capacidade do departamento |
| Peso do departamento | Capacidade (pessoas × horas produtivas), não folha, para o depto caro não "gerar" mais por ganhar mais |
| Complexidade da empresa (regime, tipo societário, nº de funcionários) | Não altera o peso. Só conta quais departamentos atendem |
| Áreas | Criar Societário e Outros ao lado de Contábil, Fiscal, Folha e Geral |

## Abertas

- Empresa sem responsável em nenhuma área: o honorário fica sem dono e deve aparecer como "sem responsável", não sumir.
- Duas pessoas no mesmo departamento atendendo a mesma empresa: hoje `CompanyAreaResponsible` guarda um responsável por empresa e área. Dividir igual é o padrão proposto.
- Q-41: de onde vem a mensalidade (o modelo `Mensalidade` existe; falta a fonte).
- Pessoa sem departamento definido: precisa de campo no colaborador para entrar na capacidade.

## Onde entra no código

- `profitability.models`: enum `Departamento` (Contábil, Fiscal, Folha, Societário, Outros), `Colaborador.departamento` e `Colaborador.usuario`, modelo `AtribuicaoDepartamento` (empresa × departamento × colaborador). Migração `0004`, só adições, dependente do hub 0039 como a 0003 (o teste de migração do NFS-e quebra com dependência mais nova).
- **Desvio da decisão sobre áreas:** Societário e Outros vivem em `profitability.Departamento` e não em `hub.ActivityTemplate.Area`. Acrescentar valor ao `choices` do hub é `AlterField` em tabela de produção, e `test_migration_safety` barra. As áreas do hub entram pelo mapa `DEPARTAMENTO_DA_AREA` (Geral cai em Outros). Mover para o hub exige OK do dono.
- `calc.valor_por_colaborador`: conta pura; testes em `tests/test_profitability_valor_calc.py`, incluindo a conservação (soma dos valores + sem responsável = receita).
- `valor.py`: monta a entrada (capacidade por departamento, mensalidade efetiva, atendimento) e confronta valor com custo mensal (custo anual ÷ 12 para CLT, nota para PJ).
- Atendimento: `AtribuicaoDepartamento` vence; na falta, o responsável de área da carteira (`CompanyAreaResponsible`) via `Colaborador.usuario`.
- Tela `profitability:value`, só administrador; define departamento da pessoa e atribui empresa sem responsável.
