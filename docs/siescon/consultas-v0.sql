-- Consultas do Siescon — RASCUNHO v0, equivalentes as do Dominio.
--
-- Dependem de `layout-v0.sql` ter sido aplicado (cria os DDFs). Escritas contra
-- o dialeto do Pervasive PSQL v10, que NAO tem funcao de janela: onde o Dominio
-- usa ROW_NUMBER() OVER (...), aqui vai subconsulta correlacionada.
--
-- Os nomes das colunas de saida sao iguais aos do contrato do Dominio de
-- proposito, para o backend processar os dois sistemas com o mesmo codigo.

-- ===========================================================================
-- companies  <- contracts/datasets/companies.v1.sql
-- ===========================================================================
SELECT
    e.codi_emp,
    e.razao_emp,
    e.documento AS cgce_emp
FROM GER_EMPRESA e
ORDER BY e.codi_emp
#

-- ===========================================================================
-- users  <- contracts/datasets/users.v1.sql
--
-- O Dominio filtra `situacao = 1`. Aqui o campo equivalente ainda nao foi
-- confirmado (candidatos @1485 e @1604), entao a consulta traz todos os
-- usuarios e o filtro de ativo fica para quando a semantica for confirmada.
-- ===========================================================================
SELECT
    u.codi_usuario AS i_usuario,
    u.nome
FROM ADM_USUARIO u
ORDER BY u.codi_usuario
#

-- ===========================================================================
-- taxation  <- contracts/datasets/taxation.v1.sql
--
-- Le a esfera federal ('01') e devolve, por empresa, a vigencia mais recente
-- que JA entrou em vigor — mesma regra do Dominio (VIGENCIA_PAR <= CURRENT DATE).
-- `vigencia` e CHAR(8) no formato AAAAMMDD, entao a data de corte entra como
-- parametro string no mesmo formato. O parametro aparece duas vezes: o contrato
-- do agente exige um valor por '?', na ordem.
--
-- Codigos de enq_federal observados: SME (432), EPP (69), LPR (127), LRE (3).
-- Leitura pendente de confirmacao: SME/EPP = Simples Nacional (micro / pequeno
-- porte), LPR = Lucro Presumido, LRE = Lucro Real. O backend converte o codigo
-- para o nome exibido, como ja faz com RFED_PAR do Dominio.
-- ===========================================================================
SELECT
    q.codi_emp,
    q.vigencia,
    q.enq_federal
FROM SAEC_ENQ q
WHERE q.esfera = '01'
  AND q.vigencia <= ?
  AND q.vigencia = (
      SELECT MAX(q2.vigencia)
      FROM SAEC_ENQ q2
      WHERE q2.codi_emp = q.codi_emp
        AND q2.esfera = '01'
        AND q2.vigencia <= ?
  )
ORDER BY q.codi_emp
#

-- ===========================================================================
-- salaries  <- contracts/datasets/salaries.v1.sql
--
-- ATENCAO — diferenca estrutural em relacao ao Dominio:
-- SAEC_COL vive dentro da pasta da empresa (S:\Dados\<NNNN>\SAEC_COL.DAT) e
-- NAO tem coluna codi_emp: a empresa e o diretorio. Como o dataset `salaries`
-- do Dominio ja roda para uma unica empresa-fonte (papel `payroll_source`),
-- aqui vale o mesmo: a tabela SAEC_COL do DDF aponta para a pasta do escritorio,
-- e o codi_emp e constante conhecida da configuracao — nao vem do SELECT.
--
-- O Dominio devolve tambem `ultima_competencia`, vinda do historico de
-- alteracoes salariais. SAEC_COL guarda apenas o salario vigente, entao a
-- competencia precisa vir da configuracao (mes corrente) ou de SAEC_AFA/SAEC_LFA,
-- que ainda nao foram levantadas.
-- ===========================================================================
SELECT
    c.codi_colaborador AS i_empregados,
    c.nome,
    c.salario AS salario_mais_recente,
    c.salario_hora
FROM SAEC_COL c
ORDER BY c.codi_colaborador
