SELECT TOP 50001 l.codi_lote, COUNT(*), h.tipo
FROM bethadba.CTLANCTO l
LEFT JOIN bethadba.CTLANCTOLOTE h ON h.codi_emp = l.codi_emp AND h.codi_lote = l.codi_lote
WHERE l.codi_emp = ? AND EXISTS (
  SELECT 1 FROM bethadba.CTLANCTO b WHERE b.codi_emp = l.codi_emp
    AND b.codi_lote = l.codi_lote AND b.data_lan >= ? AND b.data_lan < ?
    AND (b.cdeb_lan = ? OR b.ccre_lan = ?))
GROUP BY l.codi_lote, h.tipo
ORDER BY l.codi_lote
