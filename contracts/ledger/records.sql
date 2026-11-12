SELECT TOP 50001 l.codi_emp, l.CODI_EMP_PLANO, l.codi_lote, l.nume_lan,
 l.fili_lan, l.data_lan, l.cdeb_lan, l.ccre_lan, l.vlor_lan,
 l.chis_lan, l.ndoc_lan, l.codi_his
FROM bethadba.CTLANCTO l
WHERE l.codi_emp = ? AND l.data_lan >= ? AND l.data_lan < ?
  AND EXISTS (SELECT 1 FROM bethadba.CTLANCTO b
    WHERE b.codi_emp = l.codi_emp AND b.codi_lote = l.codi_lote
      AND b.data_lan >= ? AND b.data_lan < ?
      AND (b.cdeb_lan = ? OR b.ccre_lan = ?))
ORDER BY l.nume_lan
