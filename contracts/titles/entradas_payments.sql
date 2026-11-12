SELECT TOP 50001 p.codi_emp, p.codi_ent, p.pgto_entp, p.tipo_entp, p.vpag_entp, p.nlan_entp, p.origempg_entp, p.origem_reg, p.parc_entp, p.nropag_entp, p.codigo_recolhimento, p.i_recolhimento, p.codi_sai, p.i_nota_devolvida, p.numero_titulo_entp, p.base_irrf_entp, p.tipo_isencao
FROM bethadba.efentradaspag p WHERE p.codi_emp=? AND p.pgto_entp>=? AND p.pgto_entp<?
ORDER BY p.codi_emp, p.codi_ent, p.pgto_entp, p.tipo_entp, p.parc_entp, p.nropag_entp
