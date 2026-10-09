SELECT
    e.codi_emp,
    e.razao_emp,
    e.documento AS cgce_emp,
    e.situacao
FROM GER_EMPRESA_ARD e
ORDER BY e.codi_emp
