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
SELECT TOP 50001 i.codi_emp, i.codi_ent, i.vcto_entp, i.vlor_entp, i.tipo_entp, i.acrf_entp, i.vcrf_entp, i.virrf_entp, i.vissr_entp, i.vbru_entp, i.vinss_entp, i.vfunrural_entp, i.origem_reg, i.parc_entp, i.vpisret_entp, i.vcofret_entp, i.vcsocret_entp, i.virrfpf_entp, i.valor_presente_juros_entp, i.valor_presente_ndias_entp, i.icms_antecipado, i.fethab, i.fundesa, i.apiscrfop_entp, i.vpiscrfop_entp, i.acofcrfop_entp, i.vcofcrfop_entp, i.acsoccrfop_entp, i.vcsoccrfop_entp, i.airpjcrfop_entp, i.virpjcrfop_entp, i.go_fundepec, i.numero_titulo_entp, i.base_irrf_entp, i.tipo_isencao
FROM bethadba.efentradaspar i JOIN selected_installments s ON s.codi_emp=i.codi_emp AND s.codi_ent=i.codi_ent AND s.parc_entp=i.parc_entp
ORDER BY i.codi_emp, i.codi_ent, i.parc_entp
