# Auditoría de KPIs y visualización · demo de captación

2026-11-02. Revisa qué se mide y cómo se enseña, frente a prácticas estándar de analítica de producto y growth
(embudos por cohorte, CAC/LTV, retención por cohortes, evaluación de modelos y de LLMs, y honestidad visual).
Las cifras de la demo son inventadas, pero los errores de método serían igual de reales con datos de Odoo.

## Resumen

| # | Severidad | Dónde | Problema | Estándar |
|---|---|---|---|---|
| 1 | 🔴 Crítico | Embudo, canales, scoring | **Censura por la derecha**: las familias de octubre aún no han tenido tiempo de contratar (7,3 % frente a ~13 %) y bajan todas las tasas | Embudo **por cohorte con ventana de conversión** (p. ej. «contrata en ≤30 días»), solo con cohortes maduras |
| 2 | 🔴 Crítico | Embudo del viaje | **El dibujo miente**: contratan el 12,7 %, pero el trapecio mide el 41,7 % (factor de mentira ≈3,3) | Anchos proporcionales al dato; si no caben, embudo de barras o escala rota *declarada* |
| 3 | 🔴 Crítico | Embudo del viaje | Mezcla **conteos reales** (piden ayuda → contratan) con **estimaciones** (siguen a 3 y 12 meses = contratos × tasa) sin distinguirlos | Separar lo medido de lo estimado (otro color o trazo discontinuo y nota) |
| 4 | 🟠 Alto | Canales | **Coste por contrato sin valor del cliente**: no hay LTV, ni LTV:CAC, ni meses de recuperación | Para un servicio recurrente: CAC, LTV (con margen), LTV:CAC (objetivo ≥3) y *payback* |
| 5 | 🟠 Alto | Canales | **Modelo de atribución no declarado** (implícitamente último contacto, un canal por familia) y sin deduplicar familias que llegan por dos canales | Declarar el modelo; deduplicar por familia (teléfono) |
| 6 | 🟠 Alto | Canales | Solo **CAC de pago**: SEO, prescriptores y recomendaciones salen «gratis» y no lo son (equipo de contenido, acuerdos) | CAC de pago **y** CAC combinado (*blended*) con todos los costes |
| 7 | 🟠 Alto | Mapa, canales, retención | **Diferencias pequeñas sin margen de error**: el mapa colorea 11,5 % frente a 13,3 % con ±1,3 pts de error | Intervalos de confianza o n visible; no colorear diferencias no significativas |
| 8 | 🟠 Alto | Retención | Curva con denominadores que cambian cada mes (no es Kaplan-Meier) y **sin tabla de cohortes** | Triángulo de cohortes (mes de alta × meses desde el alta) y/o curva de Kaplan-Meier |
| 9 | 🟠 Alto | Calidad del asistente | **Comparación v1 → v2 confundida**: cambiaron a la vez el asistente y el juez; la mejora no se puede atribuir | Cambiar una cosa cada vez: re-juzgar las respuestas v1 con el juez v2 |
| 10 | 🟠 Alto | Calidad del asistente | **Se ajusta y se evalúa con los mismos 60 casos** (riesgo de sobreajuste) y sin intervalo de confianza (60 casos ≈ ±12 pts) | Conjunto de desarrollo y conjunto reservado; IC del % de aprobados |
| 11 | 🟡 Medio | Cola de llamadas | La validación del scoring hereda la censura (test 9,8 % frente a train 13 %) y solo muestra AUC + deciles | Etiqueta con ventana fija; **curva de ganancia/lift**, **calibración** y precisión en el top-k frente a una línea base |
| 12 | 🟡 Medio | Cola de llamadas | La simulación usa la puntuación del modelo como verdad (circular) y «tiempo de espera → conversión» se presenta como causa | Presentarla como ilustración; la causalidad se prueba con un A/B (velocidad de respuesta) |
| 13 | 🟡 Medio | Cola de llamadas | Falta el KPI operativo estándar: **velocidad de respuesta** (mediana de minutos hasta el primer contacto y % en <5 min / <1 h) | *Speed-to-lead* como métrica de nivel de servicio |
| 14 | 🟡 Medio | Mapa | Tamaño de burbuja por **diámetro** (el ojo lee el área → exagera) | `sizemode="area"` |
| 15 | 🟡 Medio | Retención | Solo retención de **familias**; falta la de **ingresos/horas** (familias que amplían horas) | Retención de clientes **y** de ingresos (NRR) |
| 16 | 🟡 Medio | Todo el panel | **Sin tendencia, sin objetivo y sin comparación** (semana contra semana): son fotos, no un panel | Cada KPI con tendencia, objetivo y variación |
| 17 | 🟡 Medio | Todo el panel | El **árbol de KPIs** que fijamos (altas netas y coste por alta arriba; embudo y retención debajo) no aparece como fila de cabecera | Fila de KPIs principales arriba, métricas de entrada debajo |
| 18 | 🟢 Bajo | Todo | **Sin diccionario de métricas**: definición, fórmula, ventana, fuente y responsable de cada KPI | Capa de métricas documentada (una tabla basta) |
| 19 | 🟢 Bajo | Sankey | Tras la valoración se juntan todos los canales y se pierde la atribución | Mantener el canal hasta el contrato |
| 20 | 🟢 Bajo | Calidad | El LTV usaría ingreso, no margen; la demo no tiene margen | Decirlo: «con margen bruto real cambiaría» |

## Detalle por área

### Embudo del viaje
- **Qué se enseña:** todas las familias de 18 meses en un embudo, con «% del paso anterior».
- **Fallos:** 1 (censura), 2 (anchos), 3 (mezcla medido/estimado). Además solo da la tasa de cada paso y no la acumulada
  (de cada 100 que piden ayuda, ¿cuántas contratan?). Las dos son estándar.
- **Corrección:** cohortes con al menos 60 días de madurez y conversión en ≤30 días, anchos proporcionales (un embudo
  real, aunque las etapas finales sean estrechas, con la cifra fuera), tasa del paso y acumulada, y los tramos de
  permanencia en otro color con «estimado con cohortes maduras».

### Canales y ciudades
- **Qué se enseña:** % que contrata por canal, € por lead frente a € por contrato, mapa y Sankey.
- **Fallos:** 4, 5, 6, 7, 14, 19.
- **Corrección:** tabla de unidad económica por canal (CAC de pago, CAC combinado, LTV a 12 meses con la curva de
  permanencia, LTV:CAC, *payback* en meses), con IC en las tasas; atribución «último contacto, deduplicado por
  teléfono» escrita en la pantalla; el mapa pinta volumen y solo resalta las ciudades con diferencia significativa.

### Cola de llamadas
- **Qué se enseña:** conversión por tiempo de espera, cola puntuada, deciles y simulación.
- **Fallos:** 11, 12, 13.
- **Corrección:** KPI de velocidad de respuesta en cabecera; validación con ventana fija, curva de ganancia («llamando al
  20 % mejor puntuado se cubre el X % de los contratos») y calibración; la simulación, rotulada como ilustración, y el
  A/B propuesto como siguiente paso.

### Retención
- **Qué se enseña:** curva de permanencia y retención a 3 meses por canal.
- **Fallos:** 7, 8, 15.
- **Corrección:** triángulo de cohortes en mapa de calor (el estándar del sector), Kaplan-Meier y retención de horas.

### Calidad del asistente
- **Qué se enseña:** % aprobado v1 frente a v2 por categoría, reglas, juez y kappa.
- **Fallos:** 9, 10.
- **Corrección:** re-juzgar las respuestas v1 con el juez v2 para separar «mejoró el juez» de «mejoró el asistente»; IC
  del % de aprobados; reservar ~20 casos nuevos que no se usen para ajustar.

### Transversal
- **Fallos:** 16, 17, 18.
- **Corrección:** fila de cabecera con 5 KPIs (altas netas al mes, CAC combinado, LTV:CAC, velocidad de respuesta,
  permanencia a 12 meses), cada uno con tendencia mensual, objetivo de ejemplo y variación; un diccionario de métricas
  en una pantalla «Definiciones».

## Diccionario de métricas propuesto

| KPI | Definición | Fórmula | Ventana | Fuente |
|---|---|---|---|---|
| Altas netas | Contratos nuevos menos bajas | altas(mes) − bajas(mes) | Mes natural | CRM (Odoo) |
| Conversión lead → contrato | Familias que contratan de las que piden ayuda | contratos en ≤30 días ÷ leads de la cohorte | Cohortes con ≥60 días | CRM |
| Velocidad de respuesta | Tiempo hasta el primer contacto | mediana(min. primera llamada − entrada); % <1 h | Semana | Telefonía + CRM |
| CAC de pago | Coste de captar un contrato con pago | gasto en medios ÷ contratos atribuidos | Mes, por canal | Google/Meta + CRM |
| CAC combinado | Igual, con todos los costes | (medios + equipo de marketing + acuerdos) ÷ todos los contratos | Mes | Contabilidad + CRM |
| LTV (12 meses) | Valor de un contrato en su primer año | Σ ingreso mensual × permanencia(mes) × margen | Cohortes maduras | Facturación + CRM |
| LTV:CAC | Retorno de la captación | LTV ÷ CAC | Trimestre | — |
| Permanencia a 3 y 12 meses | % que sigue | Kaplan-Meier o cohortes con ≥3/12 meses | Cohorte de alta | CRM |
| Aprobado del asistente | % de conversaciones de prueba aprobadas | aprobadas ÷ casos (con IC 95 %) | Por versión | Evaluación |


## Estado de las correcciones (2026-11-02, noche)

| # | Estado | Cómo |
|---|---|---|
| 1 | ✅ | Vistas `cohorte` (familias con ≥31 días de margen) y `*_30d` (ventana de 30 días) en `datos/esquema.sql`; las usan el embudo, los canales y el scoring |
| 2 | ✅ | Barras de ancho proporcional al dato con conectores; etiquetas fuera |
| 3 | ✅ | Etapas de permanencia con trazo discontinuo y «(estimado)»; definiciones en un desplegable |
| 4 | ✅ | `motor/metricas.py`: LTV a 12 meses con Kaplan-Meier por canal y margen supuesto del 30 %, LTV:CAC y payback |
| 5 | ✅ | `familia_id` en el CRM (8 % de familias por dos canales), deduplicación y pestaña de atribución último/primer contacto |
| 6 | ✅ | Costes que no son de medios (equipo SEO, acuerdos, incentivo de recomendación) en `gasto`; CAC de pago y combinado |
| 7 | ✅ | Intervalos de Wilson en conversión y retención por canal; el mapa solo colorea diferencias significativas (prueba z) |
| 8 | ✅ | Kaplan-Meier y triángulo de cohortes en mapa de calor |
| 9 | ✅ | `eval/ejecutar.py --rejuzgar`: respuestas v1 re-juzgadas con el juez v2 |
| 10 | ✅ | 20 casos reservados (`eval/casos_reserva.py`) e IC en el % de aprobados |
| 11 | ✅ | Scoring con etiqueta a 30 días sobre cohortes maduras; curva de ganancia y calibración |
| 12, 13, 14 | ✅ | Simulación rotulada como ilustración y causalidad remitida a un A/B; velocidad de respuesta en cabecera; burbujas por área |
| 15–20 | Pendiente | Retención de ingresos, tendencias y objetivos, fila de KPIs, diccionario en la app, Sankey por canal hasta contrato |

Supuestos revisados al corregir: coste por lead de Google 65 €, Meta 32 €, menú 12 € (antes 38/14/4, demasiado bajos:
daban LTV:CAC de 8-45×).
