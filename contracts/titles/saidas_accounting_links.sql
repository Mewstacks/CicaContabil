SELECT TOP 50001 x.codi_emp, x.nume_lan, x.fili_lan, x.codi_sai, x.pgto_saip, x.tipo_saip, x.parc_saip, x.nropag_saip, x.grupo, x.tipo, x.contra_partida, x.origem_lan
FROM bethadba.efsaidaspag_lancto x JOIN bethadba.efsaidaspag p ON x.fili_lan=p.codi_emp AND x.codi_sai=p.codi_sai AND x.pgto_saip=p.pgto_saip AND x.tipo_saip=p.tipo_saip AND x.parc_saip=p.parc_saip AND x.nropag_saip=p.nropag_saip
WHERE p.codi_emp=? AND p.pgto_saip>=? AND p.pgto_saip<?
ORDER BY x.codi_emp, x.nume_lan, x.fili_lan, x.codi_sai, x.pgto_saip, x.tipo_saip, x.parc_saip, x.nropag_saip, x.grupo
