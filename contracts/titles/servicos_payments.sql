SELECT TOP 50001 p.codi_emp, p.codi_ser, p.pgto_serp, p.tipo_serp, p.vpag_serp, p.nlan_serp, p.origempg_serp, p.origem_reg, p.parc_serp, p.nropag_serp, p.numero_titulo_serp
FROM bethadba.efservicospag p WHERE p.codi_emp=? AND p.pgto_serp>=? AND p.pgto_serp<?
ORDER BY p.codi_emp, p.codi_ser, p.pgto_serp, p.tipo_serp, p.parc_serp, p.nropag_serp
