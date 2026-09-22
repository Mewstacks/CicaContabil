SELECT
    u.codi_usuario AS i_usuario,
    1 AS situacao,
    u.nome
FROM ADM_USUARIO_ARD u
ORDER BY u.codi_usuario
