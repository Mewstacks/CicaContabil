SELECT
    l.codi_emp,
    l.usua_log,
    l.data_log,
    l.tini_log,
    l.tfim_log,
    l.dfim_log
FROM bethadba.geloguser l
WHERE l.data_log >= ?
  AND l.data_log <= ?
  AND l.tfim_log IS NOT NULL
ORDER BY l.codi_emp, l.data_log, l.tini_log
