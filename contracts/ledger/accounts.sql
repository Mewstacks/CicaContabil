WITH relevant_rows AS (
 SELECT l.cdeb_lan, l.ccre_lan FROM bethadba.CTLANCTO l WHERE l.codi_emp = ? AND l.data_lan >= ? AND l.data_lan < ?
  AND EXISTS (SELECT 1 FROM bethadba.CTLANCTO b
    WHERE b.codi_emp = l.codi_emp AND b.codi_lote = l.codi_lote
      AND b.data_lan >= ? AND b.data_lan < ?
      AND (b.cdeb_lan = ? OR b.ccre_lan = ?))
)
SELECT TOP 50001 a.codi_emp, a.codi_cta, a.nome_cta, a.clas_cta,
 a.tipo_cta, a.SITUACAO_CTA, a.DATAINATIVA_CTA
FROM bethadba.CTCONTAS a
WHERE a.codi_emp = ? AND a.codi_cta IN (
 SELECT cdeb_lan FROM relevant_rows UNION SELECT ccre_lan FROM relevant_rows UNION SELECT ?)
ORDER BY a.codi_cta
