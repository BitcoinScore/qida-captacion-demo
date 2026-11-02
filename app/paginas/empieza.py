"""Pantalla de entrada: de qué va la demo y qué es real y qué es de ejemplo, antes de enseñar ninguna cifra.

La historia que cuenta (y que el resto de pantallas debe respetar): esto es un prototipo del MÉTODO, no un hallazgo sobre Qida.
Las hipótesis salen de lo que Qida publica; las cifras del panel son de ejemplo; para pasar de hipótesis a dato hacen falta tres
datos de Qida.
"""
import streamlit as st

import comun

st.markdown(
    f"""
<style>
.hist {{display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: .4rem 0 1.2rem;}}
.hist .paso {{border: 1px solid {comun.BORDE}; border-radius: 16px; padding: 1.1rem 1.1rem 1rem; background: white;}}
.hist .n {{width: 2rem; height: 2rem; border-radius: 50%; background: {comun.VERDE}; color: white; font-weight: 700;
  display: flex; align-items: center; justify-content: center; margin-bottom: .6rem;}}
.hist b {{display: block; color: {comun.VERDE}; margin-bottom: .3rem; font-size: 1.02rem;}}
.hist span {{color: {comun.GRIS_TEXTO}; font-size: .92rem; line-height: 1.5;}}
.hist .paso.dato {{background: #fff7f3; border-color: #f4c3b0;}}
.hist .paso.dato .n {{background: #B4501F;}}
@media (max-width: 900px) {{.hist {{grid-template-columns: 1fr 1fr;}}}}
@media (max-width: 560px) {{.hist {{grid-template-columns: 1fr;}}}}
.tabla-hip {{width: 100%; border-collapse: separate; border-spacing: 0; font-size: .95rem; margin: .4rem 0 1rem;}}
.tabla-hip th {{text-align: left; padding: .6rem .8rem; background: {comun.FONDO}; color: {comun.VERDE}; font-size: .78rem;
  text-transform: uppercase; letter-spacing: .05em;}}
.tabla-hip td {{padding: .75rem .8rem; border-bottom: 1px solid {comun.BORDE}; vertical-align: top; color: #333;}}
.tabla-hip td:first-child {{font-weight: 600; color: {comun.VERDE}; width: 38%;}}
.etiqueta-real, .etiqueta-ej, .etiqueta-pr {{display: inline-block; border-radius: 99px; padding: 1px 9px; font-size: .74rem; font-weight: 700;
  margin-right: .4rem;}}
.etiqueta-real {{background: #e6f2f1; color: {comun.VERDE_TEXTO};}}
.etiqueta-pr {{background: #EEF3F3; color: {comun.GRIS_TEXTO};}}
.etiqueta-ej {{background: #fff1ea; color: {comun.NARANJA_TEXTO};}}
</style>
""",
    unsafe_allow_html=True,
)

comun.cabecera(
    "Empieza aquí", "Cómo abordaría la captación de Qida: primero medir, luego construir donde se pierden familias",
    "Fernando y Julia",
    "Esto es un prototipo del método, no un hallazgo sobre Qida. Las hipótesis salen de lo que Qida publica; las cifras del "
    "panel son de ejemplo.", chip="Datos de ejemplo · no son de Qida")

comun.notas([
    "**Qué es:** una forma de trabajar hecha herramienta. Cómo mediría el embudo, qué construiría primero y cómo comprobaría que "
    "funciona, con un asistente y una web que funcionan como prototipo.",
    ("**Qué no es:** un resultado sobre Qida. «La noche pierde familias» es **mi hipótesis**; no tengo el dato. Para "
     "confirmarla o descartarla necesito tres datos de Qida (abajo).", "alerta"),
])

comun.titulo("La historia en cuatro pasos")
st.markdown(
    """
<div class="hist">
  <div class="paso"><div class="n">1</div><b>Una hipótesis, de lo público</b>
    <span>Qida atiende por teléfono de 9:00 a 20:00 y promete llamar en menos de 24 h. Quien pide ayuda a las 23:10 espera a la
    mañana: ahí puede perderse una familia. Es una hipótesis.</span></div>
  <div class="paso"><div class="n">2</div><b>Cómo lo mediría</b>
    <span>Embudo por cohortes, tiempo hasta la primera llamada, coste y valor por canal y retención. Pantallas 1, 4 y Retención,
    con cifras de ejemplo.</span></div>
  <div class="paso"><div class="n">3</div><b>Lo que construí primero</b>
    <span>Donde la hipótesis es más barata de comprobar: un asistente para la noche y la cola de llamadas de la mañana.
    Pantallas 2 y 3.</span></div>
  <div class="paso"><div class="n">4</div><b>Cómo sé que funciona</b>
    <span>Lo evalúo con conversaciones difíciles y con casos que no ha visto. Aquí los datos son del modelo, pero con
    una muestra pequeña. Pantalla 5.</span></div>
</div>""",
    unsafe_allow_html=True)

comun.titulo("Qué es real y qué es de ejemplo")
st.markdown(
    """
<table class="tabla-hip">
<tr><th>Tema</th><th>Qué hay</th></tr>
<tr><td>Lo que Qida publica</td><td><span class="etiqueta-pr">Público</span>Horario, servicios, «desde 170 €/mes», cobertura y
  condiciones, tomados de qida.es y de sus anuncios el 2 de noviembre de 2026. <b>No están validados con Qida</b> y pueden haber
  cambiado: ya encontré dos diferencias entre sus anuncios y su web.</td></tr>
<tr><td>El asistente y la web</td><td><span class="etiqueta-pr">Prototipo</span>Con Claude Code instalado, el asistente responde
  en directo con un modelo; si no, reproduce conversaciones reales grabadas. El formulario guarda en una base local y no envía
  nada. No está listo para producción.</td></tr>
<tr><td>La evaluación del asistente</td><td><span class="etiqueta-pr">Muestra pequeña</span>Unos 100 casos de evaluación y 39
  adversarios, escritos por mí y probados con el modelo (pantalla 5), con los fallos que salieron y cómo se corrigieron. El revisor
  automático solo está comprobado en parte por una persona: sirve para detectar problemas, no para certificar.</td></tr>
<tr><td>El código y las pruebas</td><td><span class="etiqueta-pr">Prototipo</span>Repositorio completo y más de cien pruebas
  automáticas. Faltan las cosas de producción: cifrado de la base de leads, límites por IP, pruebas de carga y una revisión de
  seguridad real.</td></tr>
<tr><td>Las cifras del panel</td><td><span class="etiqueta-ej">Ejemplo</span>Familias, conversiones, costes por canal, retención:
  generadas con supuestos explícitos (<code>datos/generar.py</code>).</td></tr>
<tr><td>La puntuación de la cola</td><td><span class="etiqueta-ej">Ejemplo</span>Entrenada sobre datos de ejemplo: enseña cómo
  funcionaría, no qué familias contratan de verdad.</td></tr>
<tr><td>«La noche pierde familias»</td><td><span class="etiqueta-ej">Hipótesis</span>Es el punto de partida, no un resultado.</td></tr>
</table>""",
    unsafe_allow_html=True)

comun.titulo("Qué datos me ayudarían a comprobarlo")
st.markdown("Tres datos, si el CRM de Qida los registra. Cada uno ayuda a decidir algo distinto:")
st.markdown(
    """
<div class="hist">
  <div class="paso dato"><div class="n">1</div><b>A qué hora entran los contactos</b>
    <span>Reparto por franja y día de la semana. <b style="display:inline;color:#B4501F">Ayuda a ver:</b> si de noche entra una
    parte pequeña, el asistente tendría poco recorrido; si es una parte grande (en el ejemplo, 4 de cada 10), tiene sentido probarlo.</span></div>
  <div class="paso dato"><div class="n">2</div><b>Quién recibe la llamada en la primera hora</b>
    <span>Porcentaje de contactos llamados en menos de 1 h, de día y de noche. <b style="display:inline;color:#B4501F">Ayuda a ver:</b>
    si de día tampoco se llama rápido, el problema podría ser la capacidad de llamar más que el horario.</span></div>
  <div class="paso dato"><div class="n">3</div><b>Cuánto convierte la noche frente al día</b>
    <span>Llegada a valoración y a contrato, por franja. <b style="display:inline;color:#B4501F">Ayuda a ver:</b> si no hay
    diferencia, el asistente tiene poco que ganar por esta vía; si la hay, da una idea de cuánto se podría ganar.</span></div>
  <div class="paso dato"><div class="n">→</div><b>Y después</b>
    <span>Con lo que me podáis compartir, sustituiría los datos de ejemplo por los reales y repetiríamos el embudo. Si sale algo
    que merezca la pena, se diseña la prueba (A/B, pantalla 1) con una duración realista.</span></div>
</div>""",
    unsafe_allow_html=True)
st.caption(comun.AVISO)
