-- Velocidad de respuesta y conversión. Es una asociación: que cause el efecto se prueba con un A/B.
SELECT
    CASE
        WHEN e.minutos < 60   THEN '1. < 1 h'
        WHEN e.minutos < 240  THEN '2. 1-4 h'
        WHEN e.minutos < 720  THEN '3. 4-12 h'
        ELSE                       '4. > 12 h'
    END                                            AS espera,
    COUNT(*)                                       AS familias,
    SUM(e.fuera_horario)                           AS de_noche_o_finde,
    COUNT(a.lead_id)                               AS contratos,
    ROUND(100.0 * COUNT(a.lead_id) / COUNT(*), 1)  AS pct_contrata
FROM (
    SELECT c.id, c.fuera_horario,
           (julianday(ll.fecha_primera_llamada) - julianday(c.fecha_entrada)) * 24 * 60 AS minutos
    FROM cohorte c
    JOIN llamadas_30d ll ON ll.lead_id = c.id
    WHERE c.ciudad IN ({ciudades})
) AS e
LEFT JOIN altas_30d a ON a.lead_id = e.id
GROUP BY espera
ORDER BY espera;
