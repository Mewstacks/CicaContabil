SELECT
    g.codi_emp,
    g.razao_emp,
    g.cgce_emp,
    g.stat_emp AS situacao
FROM bethadba.geempre g
ORDER BY g.codi_emp
