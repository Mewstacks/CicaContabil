SELECT
    s.chave_nfe_sai AS chave_nfe,
    'S'             AS direcao,
    c.sigl_est      AS uf
FROM bethadba.efsaidas s
LEFT JOIN bethadba.efclientes c
       ON c.codi_emp = s.codi_emp
      AND c.codi_cli = s.codi_cli
WHERE s.codi_emp = ?
  AND s.dsai_sai >= ?
  AND s.dsai_sai <= ?
  AND LENGTH(TRIM(s.chave_nfe_sai)) = 44
UNION ALL
SELECT
    e.chave_nfe_ent AS chave_nfe,
    'E'             AS direcao,
    f.sigl_est      AS uf
FROM bethadba.efentradas e
LEFT JOIN bethadba.effornece f
       ON f.codi_emp = e.codi_emp
      AND f.codi_for = e.codi_for
WHERE e.codi_emp = ?
  AND e.dent_ent >= ?
  AND e.dent_ent <= ?
  AND LENGTH(TRIM(e.chave_nfe_ent)) = 44
ORDER BY 2, 1
