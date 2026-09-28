SELECT
    c.codi_colaborador AS i_empregados,
    c.nome,
    c.salario AS salario_mais_recente
FROM SAEC_COL_ESCRITORIO c
ORDER BY c.codi_colaborador
