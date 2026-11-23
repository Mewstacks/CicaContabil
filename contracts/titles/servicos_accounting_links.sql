SELECT TOP 50001 x.codi_emp, x.nume_lan, x.fili_lan, x.codi_ser, x.pgto_serp, x.tipo_serp, x.parc_serp, x.nropag_serp, x.grupo, x.tipo, x.contra_partida, x.origem_lan
FROM bethadba.efservicospag_lancto x JOIN bethadba.efservicospag p ON x.fili_lan=p.codi_emp AND x.codi_ser=p.codi_ser AND x.pgto_serp=p.pgto_serp AND x.tipo_serp=p.tipo_serp AND x.parc_serp=p.parc_serp AND x.nropag_serp=p.nropag_serp
WHERE p.codi_emp=? AND p.pgto_serp>=? AND p.pgto_serp<?
ORDER BY x.codi_emp, x.nume_lan, x.fili_lan, x.codi_ser, x.pgto_serp, x.tipo_serp, x.parc_serp, x.nropag_serp, x.grupo
