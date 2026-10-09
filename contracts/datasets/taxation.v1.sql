SELECT
    vigente.CODI_EMP AS codi_emp,
    vigente.VIGENCIA_PAR AS vigencia_par,
    vigente.RFED_PAR AS rfed_par
FROM (
    SELECT
        parametro.CODI_EMP,
        parametro.VIGENCIA_PAR,
        parametro.RFED_PAR,
        ROW_NUMBER() OVER (
            PARTITION BY parametro.CODI_EMP
            ORDER BY parametro.VIGENCIA_PAR DESC
        ) AS ordem_vigencia
    FROM bethadba.EFPARAMETRO_VIGENCIA parametro
    WHERE parametro.VIGENCIA_PAR <= CURRENT DATE
) vigente
WHERE vigente.ordem_vigencia = 1
ORDER BY vigente.CODI_EMP
