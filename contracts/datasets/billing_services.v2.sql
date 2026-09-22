SELECT
    s.codi_emp AS codi_emp_origem,
    s.codi_cli,
    c.nome_cli,
    c.cgce_cli AS documento_cli,
    YEAR(s.dser_ser) AS ano_servico,
    MONTH(s.dser_ser) AS mes_servico,
    SUM(s.vcon_ser) AS valor
FROM bethadba.efservicos s
INNER JOIN bethadba.efclientes c
        ON c.codi_emp = s.codi_emp
       AND c.codi_cli = s.codi_cli
WHERE s.codi_emp = ?
  AND s.dser_ser >= ?
  AND s.dser_ser <= ?
GROUP BY
    s.codi_emp,
    s.codi_cli,
    c.nome_cli,
    c.cgce_cli,
    YEAR(s.dser_ser),
    MONTH(s.dser_ser)
ORDER BY s.codi_cli, ano_servico, mes_servico
