-- Velocidad de respuesta (speed-to-lead) por mes: mediana aproximada y % llamadas en menos de 1 hora.
WITH esperas AS (
    SELECT substr(c.fecha_entrada, 1, 7) AS mes,
           (julianday(ll.fecha_primera_llamada) - julianday(c.fecha_entrada)) * 24 * 60 AS minutos
    FROM cohorte c JOIN llamadas_30d ll ON ll.lead_id = c.id
    WHERE c.ciudad IN ({ciudades})
)
SELECT mes,
       COUNT(*)                                                         AS familias_llamadas,
       ROUND(100.0 * SUM(CASE WHEN minutos < 60 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_menos_1h,
       ROUND(AVG(minutos) / 60, 1)                                      AS horas_media
FROM esperas
GROUP BY mes
ORDER BY mes;
