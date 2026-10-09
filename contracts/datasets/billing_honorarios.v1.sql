SELECT
    f.CODI_EMP           AS codi_emp_origem,
    c.I_CLIENTE_FIXO     AS codi_cli,
    c.NOME               AS nome_cli,
    c.INSCRICAO           AS documento_cli,
    YEAR(f.COMPETENCIA)  AS ano_servico,
    MONTH(f.COMPETENCIA) AS mes_servico,
    SUM(i.VALOR)         AS valor
FROM bethadba.HRFATURAMENTO_PARCELA_ITEM i
INNER JOIN bethadba.HRFATURAMENTO_PARCELA p
        ON p.CODI_EMP      = i.CODI_EMP
       AND p.I_FATURAMENTO = i.I_FATURAMENTO
       AND p.I_PARCELA     = i.I_PARCELA
INNER JOIN bethadba.HRFATURAMENTO f
        ON f.CODI_EMP      = p.CODI_EMP
       AND f.I_FATURAMENTO = p.I_FATURAMENTO
INNER JOIN bethadba.HRCLIENTE c
        ON c.CODI_EMP  = f.CODI_EMP
       AND c.I_CLIENTE = f.I_CLIENTE
WHERE f.CODI_EMP    = ?
  AND i.I_EVENTO    = ?
  AND f.COMPETENCIA >= ?
  AND f.COMPETENCIA <= ?
GROUP BY
    f.CODI_EMP,
    c.I_CLIENTE_FIXO,
    c.NOME,
    c.INSCRICAO,
    YEAR(f.COMPETENCIA),
    MONTH(f.COMPETENCIA)
ORDER BY codi_cli, ano_servico, mes_servico
