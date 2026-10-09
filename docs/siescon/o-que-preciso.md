# Siescon — o que preciso receber

Checklist para destravar os datasets de **empresa, usuários, folha e tributação**.
Horas e honorários ficaram para depois, por decisão do dia 16/09/2026.

---

## 0. Ficou mais urgente: `SAEC_ENQ` está vazio

Conferido em 16/09/2026: `S:\Dados\SAEC_ENQ.DAT` tem **0 registros**. Era ele que
guardaria o histórico de enquadramento tributário, e a análise anterior dizia que
tinha 1197 linhas — não tem.

Com isso, o regime tributário do Siescon **só pode sair do campo categórico de
`GER_EMPRESA`**, e a confirmação das 6 empresas abaixo deixou de ser "bônus": é o
único caminho. Sem ela, o Siescon entrega empresa e usuário, e nada de regime.

## 1. Confirmação na tela do Siescon (o item que destrava tudo)

Isolei os campos categóricos do cadastro, mas não consigo saber o que os códigos
significam sem ver a tela. Escolhi as empresas que separam as hipóteses — são
**6 empresas**, todas já selecionadas para cobrir todos os casos.

Para cada código abaixo, preciso de duas informações: **regime tributário** e
**situação** (ativa / inativa / paralisada).

| Código | Por que esta empresa |
|---|---|
| `0025` | representa o grupo maior (100 empresas com o mesmo perfil) |
| `0002` | segundo código de regime |
| `0022` | terceiro código de regime |
| `0182` | quarto código de regime (só 20 empresas têm) |
| `0026` | mesmo perfil da 0025, mas com a situação diferente |
| `0241` | terceira situação possível |

Formato da resposta — pode ser texto corrido mesmo:

```
0025 = Simples Nacional, ativa
0002 = Lucro Presumido, ativa
...
```

### Bônus (30 segundos, confirma um campo a mais)

Tenho um campo com os valores `S` (385 empresas), `C` (118), `I` (39) e vazio (137).
Minha leitura é **ramo: Serviço / Comércio / Indústria**. Se você me disser o ramo
dessas mesmas 6 empresas, confirmo de graça.

---

## 2. Usuários — uma contagem

Na tela de usuários do Siescon, **quantos aparecem como ativos?**

- Se for **20**, o campo certo é o `@1485`.
- Se for **15**, é o `@1604`.
- Se não for nem um nem outro, me diga o número e eu procuro de novo.

(O cadastro tem 51 usuários no total.)

---

## 3. Autorização para criar os DDFs

Para o Siescon aceitar `SELECT`, preciso rodar um DDL que cria três arquivos novos
(`FILE.DDF`, `FIELD.DDF`, `INDEX.DDF`) dentro de `S:\Dados`, que é **produção**.

O DDL só cria o dicionário — **não altera nenhum arquivo de dados** e não mexe no
Siescon. Ainda assim é escrita no share de produção, então preciso do seu OK
explícito, e de preferência:

- [ ] OK para criar os DDFs em `S:\Dados`
- [ ] Uma janela combinada (fora do horário de movimento, se preferir)
- [ ] Confirmação de que existe backup recente do share

Se preferir zero risco, dá para fazer antes num **cópia de uma pasta de empresa**
e só depois aplicar em produção. É mais lento, mas é reversível.

---

## 4. Decisões de arquitetura

### 4.1 Empresas: 688 diretórios

O Domínio tem `codi_emp` como coluna de uma tabela só. O Siescon tem uma pasta por
empresa (`S:\Dados\0001`, `0002`, ...), e a folha mora dentro dela. Preciso saber
qual caminho seguir:

- [ ] **(a)** Um banco Pervasive por empresa — mais fiel, porém 688 bancos para manter.
- [ ] **(b)** O agente itera os diretórios e roda a mesma consulta em cada um —
      menos objetos para administrar, mas muda o modelo de execução dos jobs.

Minha recomendação é **(b)**, porque mantém um DSN só e o conector já faz streaming
por lote. Mas é decisão sua.

### 4.2 Escopo das empresas

- [ ] Vamos trazer as **679** empresas ou só as **ativas**?
- [ ] Alguma carteira/divisão específica, ou o escritório inteiro?

### 4.3 Folha

- [ ] O `SAEC_COL` guarda o salário **atual** do colaborador. O Domínio traz
      "salário mais recente + competência". Serve usarmos a competência corrente,
      ou você precisa do histórico de alterações salariais?

---

## 5. Ambiente

- [ ] O agente vai rodar **nesta máquina** ou no `servidor`?
- [ ] O Pervasive instalado é **Workgroup** (não Server). Quantas conexões
      simultâneas a licença permite? Se o agente consumir uma, isso atrapalha
      alguém do escritório no horário comercial?
- [ ] O share `\\servidor\siescon` fica acessível 24h, ou tem janela de backup
      em que ele cai?

---

## 6. Atalho que dispensa metade desta lista

O Siescon exporta tabelas em texto de largura fixa — tem um exemplo pronto em
`S:\Util\SAEC_CXE.TXT`. **Uma exportação do cadastro de empresas** com o cabeçalho
das colunas resolve de uma vez os itens 1 e 2, e ainda me dá os campos que eu nem
sei que existem.

Se você souber por qual menu se faz essa exportação, é o caminho mais curto.
