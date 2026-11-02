# Decisiones, límites y siguientes pasos

## Arquitectura (demo)

```
Familia ──► Web + asistente (Streamlit) ──► motor/asistente.py ──► modelo (Claude Haiku vía Claude Code, o modo grabado)
                     │                              │
                     ▼                              ▼
              ficha del lead (JSON) ─────────►  CRM (SQLite con forma de Odoo) ◄── datos/generar.py (inventados)
                                                    │
                       vistas de métricas (esquema.sql) ─► panel: embudo, canales, cola, retención
                                                    │
                       motor/scoring.py ─► cola de llamadas      eval/ ─► calidad del asistente
```

## Decisiones

| Decisión | Por qué | Alternativa descartada |
|---|---|---|
| Medir el embudo antes de construir IA | Decide dónde construir: la fuga mayor está entre llamada y valoración, y el 40 % pide ayuda de noche | Empezar por un modelo |
| Métricas como **vistas SQL** (cohorte madura, ventana de 30 días, deduplicación) | Una sola definición para todo el panel y las pruebas | Calcularlas en cada pantalla |
| Atribución **último contacto, deduplicado por familia** | Es el que más se acerca a quién cierra; se enseña la comparación con primer contacto | Atribución sin deduplicar |
| Regresión logística para la puntuación | Explicable para los asesores y suficiente con estos datos; bien calibrada | Modelos más complejos sin ganancia demostrada |
| La puntuación **ordena, no descarta** | Ninguna familia se queda sin llamada | Filtrar leads |
| Asistente **solo con la base de conocimiento** (regla de fidelidad) | La v2 inventaba políticas con casos nuevos (60 %) | Dejar que el modelo «complete» |
| IA declarada, consentimiento antes de escribir, 112 fijo | Reglamento europeo de IA (art. 50), RGPD (datos de salud, art. 9), seguridad | — |
| El asistente nunca habla con personas mayores, solo con familiares que escriben, y siempre ofrece una persona | Criterio propio: el cuidado es humano | Agente de voz con mayores |
| Evaluación en tres capas: reglas → juez LLM → calibración humana; **casos reservados** | Cada capa es más cara; los reservados detectan el sobreajuste | Probar a mano unas pocas conversaciones |

## Límites conocidos (honestos)

- **Datos inventados.** Las tasas, costes y bajas son supuestos de `datos/generar.py`; el valor está en el método.
- **Margen bruto supuesto del 30 %** para el LTV; con el real cambia el LTV:CAC.
- **Causalidad:** «llamar antes → más contratos» es una asociación; se prueba con un A/B (asistente sí/no por ciudad o semana).
- **El juez no está calibrado todavía:** falta que una persona etiquete ~30 casos para medir el acuerdo (kappa de Cohen).
- **Muestras pequeñas** en evaluación (20-60 casos): por eso se enseñan los intervalos de confianza.
- Pendiente de la auditoría: retención de ingresos (horas), tendencias por mes en todos los KPIs, Sankey por canal hasta contrato.

## Con datos reales de Qida, las primeras 4 semanas

1. **Semana 1:** conectar el CRM (Odoo) y la telefonía en modo lectura; reproducir el embudo por cohortes y la velocidad de
   respuesta con datos reales. Acordar las definiciones con marketing y con el equipo de asesores.
2. **Semana 2:** puntuación con datos reales, validada con meses no vistos; revisarla con 2-3 asesores (¿el «porqué» les sirve?).
3. **Semana 3:** asistente de noche en una ciudad, con base de conocimiento revisada por el equipo, conjunto de evaluación
   con conversaciones reales anonimizadas y calibración humana del juez.
4. **Semana 4:** A/B (ciudad o franja con y sin asistente) midiendo familias de noche que llegan a valoración y coste por
   contrato; decidir si se escala.

## Producción: qué cambiaría

- Modelo vía **API de Anthropic** con la clave en un gestor de secretos; registro de conversaciones con retención limitada.
- Datos en la UE, evaluación de impacto (EIPD) antes de lanzar, política de privacidad real y derecho de supresión.
- Monitorización: muestreo diario de conversaciones revisadas por el juez y por una persona; alertas si baja el aprobado.
- Integración del lead en Odoo (API) en lugar de SQLite; la cola de llamadas, dentro de la herramienta de los asesores.

## Coste orientativo del asistente

Claude Haiku con ~6.000 tokens de entrada (prompt y base de conocimiento) y ~200 de salida por respuesta, con caché de
prompt: del orden de **céntimos por conversación** (verificar con la tarifa vigente); para unas 1.500 conversaciones nocturnas al mes, decenas de euros. A
comparar con el valor de un contrato (LTV de miles de euros en la demo).
