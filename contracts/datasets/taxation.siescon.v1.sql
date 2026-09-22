SELECT
    q.codi_emp,
    q.vigencia AS vigencia_par,
    CASE q.enq_federal
        WHEN 'LRE' THEN 1
        WHEN 'SME' THEN 2
        WHEN 'EPP' THEN 4
        WHEN 'LPR' THEN 5
        ELSE 0
    END AS rfed_par
FROM SAEC_ENQ_ARD q
WHERE q.esfera = '01'
  AND q.vigencia = (
      SELECT MAX(q2.vigencia)
      FROM SAEC_ENQ_ARD q2
      WHERE q2.codi_emp = q.codi_emp
        AND q2.esfera = '01'
  )
ORDER BY q.codi_emp
