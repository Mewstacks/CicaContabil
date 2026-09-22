SELECT
    e.codi_emp,
    e.razao_emp,
    e.cgce_emp,
    a.codi_usu,
    a.data_atv,
    a.hori_atv,
    a.horf_atv,
    a.desc_atv
FROM bethadba.geatividades a
INNER JOIN bethadba.geempre e ON e.codi_emp = a.codi_emp
WHERE a.data_atv >= ?
  AND a.data_atv <= ?
  AND a.hori_atv IS NOT NULL
  AND a.horf_atv IS NOT NULL
ORDER BY e.codi_emp, a.data_atv, a.hori_atv
