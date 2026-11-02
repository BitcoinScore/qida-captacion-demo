# Qida · Captación de familias con IA (concepto)

Concepto de Máximo Fernández Catalán para el puesto de **AI Product Builder (marketing y growth)** en Qida, noviembre de 2026.
Es una demo de trabajo, no una herramienta oficial de Qida.

> **Datos:** las cifras del panel son **inventadas** (generadas con supuestos explícitos en `datos/generar.py`). La marca,
> los servicios, las condiciones y las cifras públicas de la web («desde 170 €/mes», 4,8/5, +25.000 familias) salen de
> qida.es y de sus anuncios públicos en Meta, consultados el 02-11-2026. El logotipo no se incluye en el repositorio.

## Qué hay dentro

La idea: **antes de construir IA, medir el embudo**; y construir solo donde se pierden familias.

| Pantalla | Para quién | Qué responde |
|---|---|---|
| **Web con asistente de noche** | La familia | Concepto de web con un asistente virtual (IA declarada) que, fuera de horario, entiende el caso, deja la llamada agendada y pasa a una persona si hace falta |
| **Viaje de la familia** | Dirección y marketing | 5 KPIs del mes, el embudo completo hasta «siguen al año» y el mapa del viaje (service blueprint) con qué construiría en cada etapa |
| **Canales y ciudades** | Marketing | CAC de pago y combinado, LTV a 12 meses, LTV:CAC y payback por canal; conversión con intervalos de confianza; mapa; atribución |
| **Cola de llamadas** | Asesores familiares | A quién llamar primero (puntuación explicable), velocidad de respuesta, curva de ganancia y calibración |
| **Retención** | Marketing y Referentes Sociales | Permanencia (Kaplan-Meier), triángulo de cohortes y permanencia por canal |
| **Calidad del asistente** | Equipo de IA | Evaluación en tres capas y su evolución v1 → v3, con casos reservados |

### Resultados que importan

- **El embudo:** la mayor fuga está entre la primera llamada y la valoración; y casi 4 de cada 10 familias piden ayuda fuera
  de horario. De ahí el asistente de noche y la cola priorizada.
- **La puntuación:** llamando primero al 30 % mejor puntuado se cubre el ~55 % de los contratos (validado con meses que el
  modelo no vio). Reordenar la cola aporta poco por sí solo: la palanca es **llamar antes**.
- **El asistente:** la v2 aprobaba el 88 % de los casos con los que se ajustó, pero solo el **60 %** de casos nuevos
  (inventaba políticas). La v3 añade una regla de fidelidad y aprueba el **88 %** (IC 70–96 %) de un conjunto nuevo
  escrito antes de evaluarla. Detalle en la pantalla de calidad.

## Cómo ejecutarlo

Requisitos: Python 3.11 o superior.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # en macOS/Linux: .venv/bin/pip
.venv/Scripts/python datos/generar.py               # crea datos/crm.db (inventado, reproducible: semilla 42)
.venv/Scripts/streamlit run app/Inicio.py
```

**El chat tiene dos modos** (`QIDA_MODO`, automático por defecto):
- **grabado** (si no hay Claude Code): reproduce conversaciones **reales** del asistente v3 en la evaluación. Es lo que verá
  quien clone el repositorio.
- **vivo**: con [Claude Code](https://claude.com/claude-code) instalado y con sesión iniciada, el chat responde en directo
  (Claude Haiku) y la evaluación se puede volver a ejecutar (`python eval/ejecutar.py`, ~120 llamadas al modelo).

Pruebas:

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/pytest -q
```

## Estructura

```
app/            Streamlit: Inicio.py (navegación), paginas/ (una por pantalla), comun.py (estilo y utilidades), graficos.py
motor/          asistente.py (prompt y ficha del lead), kb.md (base de conocimiento), llm.py (modos), scoring.py, metricas.py
datos/          esquema.sql (tablas tipo CRM y definiciones de métricas como vistas), generar.py (datos inventados)
sql/            consultas que se enseñan en el panel
eval/           conjuntos de casos (ajuste y reservados), ejecutar.py (reglas + juez + re-juzgar) y resultados por versión
docs/           decisiones.md, auditoria-kpis.md, auditoria-web-familia.md
tests/          pruebas (datos, métricas, scoring, asistente y carga de cada pantalla)
```

## Documentación

- [`docs/decisiones.md`](docs/decisiones.md) — arquitectura, decisiones, límites conocidos, qué haría con datos reales y coste.
- [`docs/auditoria-kpis.md`](docs/auditoria-kpis.md) — auditoría de las métricas frente a estándares, y qué se corrigió.
- [`docs/auditoria-web-familia.md`](docs/auditoria-web-familia.md) — auditoría de la web y el chat (RGPD, transparencia de la IA, conversión).
