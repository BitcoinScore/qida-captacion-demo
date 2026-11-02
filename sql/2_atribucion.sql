-- ¿Cambia el reparto de contratos según el modelo de atribución? Último contacto frente a primer contacto.
SELECT
    c.canal                                              AS canal,
    COUNT(*)                                             AS contratos_ultimo_contacto,
    (SELECT COUNT(*) FROM cohorte c2
       JOIN altas_30d a2 ON a2.lead_id = c2.id
       JOIN primer_contacto p2 ON p2.familia_id = c2.familia_id
      WHERE p2.canal_primer_contacto = c.canal AND c2.ciudad IN ({ciudades})) AS contratos_primer_contacto
FROM cohorte c
JOIN altas_30d a ON a.lead_id = c.id
WHERE c.ciudad IN ({ciudades})
GROUP BY c.canal
ORDER BY contratos_ultimo_contacto DESC;
