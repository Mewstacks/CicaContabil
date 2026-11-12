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
SELECT TOP 50001 i.codi_emp, i.codi_ser, i.vcto_serp, i.vlor_serp, i.tipo_serp, i.acrf_serp, i.vcrf_serp, i.virrf_serp, i.vissr_serp, i.vbru_serp, i.vinss_serp, i.origem_reg, i.parc_serp, i.apiscrfop_serp, i.vpiscrfop_serp, i.acofcrfop_serp, i.vcofcrfop_serp, i.acsoccrfop_serp, i.vcsoccrfop_serp, i.airpjcrfop_serp, i.virpjcrfop_serp, i.virrfp_serp, i.vpisret_serp, i.vcofret_serp, i.vcsocret_serp, i.valor_presente_juros_serp, i.valor_presente_ndias_serp, i.numero_titulo_serp
FROM bethadba.efservicospar i JOIN selected_installments s ON s.codi_emp=i.codi_emp AND s.codi_ser=i.codi_ser AND s.parc_serp=i.parc_serp
ORDER BY i.codi_emp, i.codi_ser, i.parc_serp
