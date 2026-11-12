SELECT TOP 50001 p.codi_emp, p.codi_sai, p.pgto_saip, p.tipo_saip, p.vpag_saip, p.nlan_saip, p.origempg_saip, p.origem_reg, p.parc_saip, p.nropag_saip, p.numero_titulo_saip, p.codi_ent, p.i_nota_devolvida
FROM bethadba.efsaidaspag p WHERE p.codi_emp=? AND p.pgto_saip>=? AND p.pgto_saip<?
ORDER BY p.codi_emp, p.codi_sai, p.pgto_saip, p.tipo_saip, p.parc_saip, p.nropag_saip
