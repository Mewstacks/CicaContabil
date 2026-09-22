SELECT
    u.i_usuario,
    u.situacao,
    u.nome
FROM bethadba.usConfUsuario u
WHERE u.situacao = 1
ORDER BY u.i_usuario
