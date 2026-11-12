SELECT TOP 50001 x.codi_emp, x.nume_lan, x.fili_lan, x.codi_ent, x.pgto_entp, x.tipo_entp, x.parc_entp, x.nropag_entp, x.grupo, x.tipo, x.contra_partida, x.origem_lan
FROM bethadba.efentradaspag_lancto x JOIN bethadba.efentradaspag p ON x.fili_lan=p.codi_emp AND x.codi_ent=p.codi_ent AND x.pgto_entp=p.pgto_entp AND x.tipo_entp=p.tipo_entp AND x.parc_entp=p.parc_entp AND x.nropag_entp=p.nropag_entp
WHERE p.codi_emp=? AND p.pgto_entp>=? AND p.pgto_entp<?
ORDER BY x.codi_emp, x.nume_lan, x.fili_lan, x.codi_ent, x.pgto_entp, x.tipo_entp, x.parc_entp, x.nropag_entp, x.grupo
