SELECT
    a.codi_emp,
    a.i_empregados,
    b.nome,
    a.competencia AS ultima_competencia,
    a.novo_salario AS salario_mais_recente
FROM bethadba.foaltesal a
INNER JOIN bethadba.foempregados b
        ON b.codi_emp = a.codi_emp
       AND b.i_empregados = a.i_empregados
WHERE a.codi_emp = ?
  AND a.competencia = (
      SELECT MAX(a2.competencia)
      FROM bethadba.foaltesal a2
      WHERE a2.codi_emp = a.codi_emp
        AND a2.i_empregados = a.i_empregados
  )
ORDER BY a.i_empregados
