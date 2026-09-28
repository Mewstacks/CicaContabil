SELECT
    f.CODI_EMP           AS codi_emp_origem,
    i.I_EVENTO           AS i_evento,
    YEAR(f.COMPETENCIA)  AS ano_servico,
    MONTH(f.COMPETENCIA) AS mes_servico,
    COUNT(*)             AS lancamentos,
    SUM(i.VALOR)         AS total
FROM bethadba.HRFATURAMENTO_PARCELA_ITEM i
INNER JOIN bethadba.HRFATURAMENTO f
        ON f.CODI_EMP      = i.CODI_EMP
       AND f.I_FATURAMENTO = i.I_FATURAMENTO
WHERE f.CODI_EMP    = ?
  AND f.COMPETENCIA >= ?
  AND f.COMPETENCIA <= ?
GROUP BY
    f.CODI_EMP,
    i.I_EVENTO,
    YEAR(f.COMPETENCIA),
    MONTH(f.COMPETENCIA)
ORDER BY ano_servico, mes_servico, total DESC
