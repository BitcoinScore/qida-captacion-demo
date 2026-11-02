-- Embudo por canal, por familia (deduplicada) y con ventana de conversión de 30 días.
-- `cohorte` = familias con al menos 31 días de margen hasta el corte de datos (ver datos/esquema.sql).
SELECT
    c.canal,
    COUNT(*)              AS familias,
    COUNT(v.lead_id)      AS valoraciones,
    COUNT(a.lead_id)      AS contratos,
    ROUND(100.0 * COUNT(v.lead_id) / COUNT(*), 1)                     AS pct_a_valoracion,
    ROUND(100.0 * COUNT(a.lead_id) / NULLIF(COUNT(v.lead_id), 0), 1)  AS pct_valoracion_a_contrato,
    ROUND(100.0 * COUNT(a.lead_id) / COUNT(*), 1)                     AS pct_contrata
FROM cohorte c
LEFT JOIN valoraciones_30d v ON v.lead_id = c.id
LEFT JOIN altas_30d a        ON a.lead_id = c.id
WHERE c.ciudad IN ({ciudades})
GROUP BY c.canal
ORDER BY pct_contrata DESC;
