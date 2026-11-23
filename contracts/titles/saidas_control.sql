WITH selected_payments AS (
 SELECT p.codi_emp, p.codi_sai, p.parc_saip, p.pgto_saip, p.tipo_saip, p.nropag_saip
 FROM bethadba.efsaidaspag p WHERE p.codi_emp=? AND p.pgto_saip>=? AND p.pgto_saip<?
), selected_installments AS (
 SELECT i.codi_emp, i.codi_sai, i.parc_saip, i.vcto_saip
 FROM bethadba.efsaidaspar i
 WHERE i.codi_emp=? AND ((i.vcto_saip>=? AND i.vcto_saip<?) OR EXISTS (
  SELECT 1 FROM selected_payments p WHERE p.codi_emp=i.codi_emp AND p.codi_sai=i.codi_sai AND p.parc_saip=i.parc_saip
 ))
)
SELECT
 (SELECT COUNT(*) FROM selected_installments i WHERE i.vcto_saip>=? AND i.vcto_saip<?),
 (SELECT COUNT(*) FROM selected_payments),
 (SELECT COUNT(*) FROM selected_installments),
 (SELECT COUNT(*) FROM bethadba.efsaidaspag_lancto x JOIN selected_payments p ON x.fili_lan=p.codi_emp AND x.codi_sai=p.codi_sai AND x.pgto_saip=p.pgto_saip AND x.tipo_saip=p.tipo_saip AND x.parc_saip=p.parc_saip AND x.nropag_saip=p.nropag_saip),
 (SELECT COUNT(*) FROM selected_installments i LEFT JOIN bethadba.efsaidas h ON h.codi_emp=i.codi_emp AND h.codi_sai=i.codi_sai WHERE h.codi_emp IS NULL),
 (SELECT COUNT(*) FROM selected_payments p LEFT JOIN bethadba.efsaidaspar i ON i.codi_emp=p.codi_emp AND i.codi_sai=p.codi_sai AND i.parc_saip=p.parc_saip WHERE i.codi_emp IS NULL)
