-- CRM inventado, con la forma de un CRM tipo Odoo. Datos de demo, no de Qida.
CREATE TABLE leads (
    id                   INTEGER PRIMARY KEY,
    familia_id           INTEGER NOT NULL,  -- misma familia (mismo teléfono) aunque entre por dos canales
    fecha_entrada        TEXT NOT NULL,     -- ISO, hora local
    canal                TEXT NOT NULL,
    ciudad               TEXT NOT NULL,
    servicio             TEXT NOT NULL,     -- Por horas | Interna | Fin de semana | Nocturna
    urgencia             INTEGER NOT NULL,  -- 1 = alta hospitalaria o situación urgente
    menciona_dependencia INTEGER NOT NULL,
    fuera_horario        INTEGER NOT NULL   -- entró cuando no había nadie al teléfono
);
CREATE TABLE llamadas     (lead_id INTEGER PRIMARY KEY REFERENCES leads(id), fecha_primera_llamada TEXT NOT NULL);
CREATE TABLE valoraciones (lead_id INTEGER PRIMARY KEY REFERENCES leads(id), fecha TEXT NOT NULL);
CREATE TABLE altas (
    lead_id              INTEGER PRIMARY KEY REFERENCES leads(id),
    fecha_alta           TEXT NOT NULL,
    horas_mes            INTEGER NOT NULL,  -- 0 en internas
    ingreso_mes          REAL NOT NULL,
    prestacion_vinculada INTEGER NOT NULL
);
CREATE TABLE bajas (lead_id INTEGER PRIMARY KEY REFERENCES altas(lead_id), fecha_baja TEXT NOT NULL);
CREATE TABLE gasto (mes TEXT NOT NULL, canal TEXT NOT NULL, ciudad TEXT NOT NULL, tipo TEXT NOT NULL, importe REAL NOT NULL);

-- ── Definiciones de métricas (ver docs/auditoria-kpis.md) ──────────────────────────────────────────────
-- Atribución: último contacto antes del resultado, deduplicado por familia (teléfono).
CREATE VIEW familias AS
SELECT * FROM (
    SELECT l.*, ROW_NUMBER() OVER (PARTITION BY familia_id ORDER BY fecha_entrada DESC) AS orden,
           COUNT(*) OVER (PARTITION BY familia_id) AS contactos
    FROM leads l
) WHERE orden = 1;

-- Primer contacto de cada familia, para comparar modelos de atribución.
CREATE VIEW primer_contacto AS
SELECT familia_id, canal AS canal_primer_contacto FROM (
    SELECT familia_id, canal, ROW_NUMBER() OVER (PARTITION BY familia_id ORDER BY fecha_entrada) AS orden FROM leads
) WHERE orden = 1;

-- Cohorte madura: familias con al menos 31 días de margen hasta el corte de datos (31-10-2026).
CREATE VIEW cohorte AS SELECT * FROM familias WHERE fecha_entrada < '2026-10-01';

-- Resultados dentro de la ventana de conversión de 30 días desde que la familia pide ayuda.
CREATE VIEW llamadas_30d AS
SELECT ll.* FROM llamadas ll JOIN leads l ON l.id = ll.lead_id
WHERE julianday(ll.fecha_primera_llamada) - julianday(l.fecha_entrada) <= 30;
CREATE VIEW valoraciones_30d AS
SELECT v.* FROM valoraciones v JOIN leads l ON l.id = v.lead_id
WHERE julianday(v.fecha) - julianday(l.fecha_entrada) <= 30;
CREATE VIEW altas_30d AS
SELECT a.* FROM altas a JOIN leads l ON l.id = a.lead_id
WHERE julianday(a.fecha_alta) - julianday(l.fecha_entrada) <= 30;
