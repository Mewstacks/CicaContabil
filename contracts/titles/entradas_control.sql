WITH selected_payments AS (
 SELECT p.codi_emp, p.codi_ent, p.parc_entp, p.pgto_entp, p.tipo_entp, p.nropag_entp
 FROM bethadba.efentradaspag p WHERE p.codi_emp=? AND p.pgto_entp>=? AND p.pgto_entp<?
), selected_installments AS (
 SELECT i.codi_emp, i.codi_ent, i.parc_entp, i.vcto_entp
 FROM bethadba.efentradaspar i
 WHERE i.codi_emp=? AND ((i.vcto_entp>=? AND i.vcto_entp<?) OR EXISTS (
  SELECT 1 FROM selected_payments p WHERE p.codi_emp=i.codi_emp AND p.codi_ent=i.codi_ent AND p.parc_entp=i.parc_entp
 ))
)
SELECT
 (SELECT COUNT(*) FROM selected_installments i WHERE i.vcto_entp>=? AND i.vcto_entp<?),
 (SELECT COUNT(*) FROM selected_payments),
 (SELECT COUNT(*) FROM selected_installments),
 (SELECT COUNT(*) FROM bethadba.efentradaspag_lancto x JOIN selected_payments p ON x.fili_lan=p.codi_emp AND x.codi_ent=p.codi_ent AND x.pgto_entp=p.pgto_entp AND x.tipo_entp=p.tipo_entp AND x.parc_entp=p.parc_entp AND x.nropag_entp=p.nropag_entp),
 (SELECT COUNT(*) FROM selected_installments i LEFT JOIN bethadba.efentradas h ON h.codi_emp=i.codi_emp AND h.codi_ent=i.codi_ent WHERE h.codi_emp IS NULL),
 (SELECT COUNT(*) FROM selected_payments p LEFT JOIN bethadba.efentradaspar i ON i.codi_emp=p.codi_emp AND i.codi_ent=p.codi_ent AND i.parc_entp=p.parc_entp WHERE i.codi_emp IS NULL)
