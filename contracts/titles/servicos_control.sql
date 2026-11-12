WITH selected_payments AS (
 SELECT p.codi_emp, p.codi_ser, p.parc_serp, p.pgto_serp, p.tipo_serp, p.nropag_serp
 FROM bethadba.efservicospag p WHERE p.codi_emp=? AND p.pgto_serp>=? AND p.pgto_serp<?
), selected_installments AS (
 SELECT i.codi_emp, i.codi_ser, i.parc_serp, i.vcto_serp
 FROM bethadba.efservicospar i
 WHERE i.codi_emp=? AND ((i.vcto_serp>=? AND i.vcto_serp<?) OR EXISTS (
  SELECT 1 FROM selected_payments p WHERE p.codi_emp=i.codi_emp AND p.codi_ser=i.codi_ser AND p.parc_serp=i.parc_serp
 ))
)
SELECT
 (SELECT COUNT(*) FROM selected_installments i WHERE i.vcto_serp>=? AND i.vcto_serp<?),
 (SELECT COUNT(*) FROM selected_payments),
 (SELECT COUNT(*) FROM selected_installments),
 (SELECT COUNT(*) FROM bethadba.efservicospag_lancto x JOIN selected_payments p ON x.fili_lan=p.codi_emp AND x.codi_ser=p.codi_ser AND x.pgto_serp=p.pgto_serp AND x.tipo_serp=p.tipo_serp AND x.parc_serp=p.parc_serp AND x.nropag_serp=p.nropag_serp),
 (SELECT COUNT(*) FROM selected_installments i LEFT JOIN bethadba.efservicos h ON h.codi_emp=i.codi_emp AND h.codi_ser=i.codi_ser WHERE h.codi_emp IS NULL),
 (SELECT COUNT(*) FROM selected_payments p LEFT JOIN bethadba.efservicospar i ON i.codi_emp=p.codi_emp AND i.codi_ser=p.codi_ser AND i.parc_serp=p.parc_serp WHERE i.codi_emp IS NULL)
