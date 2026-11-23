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
SELECT TOP 50001 i.codi_emp, i.codi_sai, i.vcto_saip, i.vlor_saip, i.tipo_saip, i.acrf_saip, i.vcrf_saip, i.vbru_saip, i.origem_reg, i.parc_saip, i.virrf_saip, i.vissr_saip, i.vinss_saip, i.apiscrfop_saip, i.vpiscrfop_saip, i.acofcrfop_saip, i.vcofcrfop_saip, i.acsoccrfop_saip, i.vcsoccrfop_saip, i.airpjcrfop_saip, i.virpjcrfop_saip, i.virrfp_saip, i.vpisret_saip, i.vcofret_saip, i.vcsocret_saip, i.vfunrural_saip, i.valor_presente_juros_saip, i.valor_presente_ndias_saip, i.numero_titulo_saip, i.fethab, i.valor_icms_st
FROM bethadba.efsaidaspar i JOIN selected_installments s ON s.codi_emp=i.codi_emp AND s.codi_sai=i.codi_sai AND s.parc_saip=i.parc_saip
ORDER BY i.codi_emp, i.codi_sai, i.parc_saip
