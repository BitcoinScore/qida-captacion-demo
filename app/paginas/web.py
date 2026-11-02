"""Lo que ve la familia: concepto de la web de Qida con el asistente de noche en un botón flotante.

Auditada en docs/auditoria-web-familia.md: IA declarada, privacidad antes de recoger datos, 112 visible, formulario que
funciona, teléfono y horario, señales de confianza, coherencia con el anuncio, respuestas rápidas y salida a una persona.
Marca, teléfono, servicios y cifras públicas tomados de qida.es (02-11-2026). No es la web oficial.
"""
import base64
import json
import re
from datetime import datetime, time

import streamlit as st

import comun
from motor import asistente
from motor import llm
from motor.llm import ErrorModelo

TELEFONO = "635 704 124"  # el que publica qida.es
PRIVACIDAD = ("Usaremos tus datos solo para llamarte y preparar tu presupuesto. No hace falta que nos cuentes detalles "
              "médicos. Puedes pedir que los borremos cuando quieras. [Política de privacidad](#)")
LOGO_B64 = base64.b64encode(comun.LOGO.read_bytes()).decode() if comun.LOGO.exists() else ""
# El logotipo no va en el repositorio (marca de terceros): sin él, el nombre en la tipografía de los títulos.
MARCA = (f"<img src='data:image/png;base64,{LOGO_B64}' height='38' alt='Qida'>" if LOGO_B64 else
         f"<span style='font-family:DM Serif Display,Georgia,serif;font-size:2rem;color:{comun.VERDE}'>Qida</span>")

st.markdown(
    f"""
<style>
.st-key-boton-chat {{position: fixed; right: 28px; bottom: 28px; z-index: 999; width: auto !important;}}
.st-key-boton-chat button {{border-radius: 2rem !important; padding: .75rem 1.3rem; background: {comun.VERDE} !important;
  color: white !important; border: 0; box-shadow: 0 8px 24px rgba(0,64,57,.28); font-weight: 600;}}
.cab {{display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.8rem; padding:.2rem 0 .9rem;
  border-bottom:1px solid {comun.BORDE}; margin-bottom:1rem}}
.cab .tel {{color:{comun.VERDE}; font-weight:700}}
.cab .estado {{font-size:.85rem; padding:2px 10px; border-radius:99px}}
.hero {{background:{comun.FONDO}; border-radius:24px; padding:2.4rem 2.6rem; margin-bottom:1rem}}
.hero h1 {{margin:0 0 .5rem; font-size:2.6rem; line-height:1.1}}
.hero .bajada {{font-size:1.15rem; color:#4d5d5c}}
.precio {{display:inline-block; margin-top:1rem; background:{comun.VERDE}; color:white; font-weight:700; border-radius:99px;
  padding:.4rem 1rem}}
.confianza {{display:flex; gap:1rem; flex-wrap:wrap; justify-content:space-between; margin:.2rem 0 1.4rem}}
.confianza div {{flex:1; min-width:150px; border:1px solid {comun.BORDE}; border-radius:14px; padding:.7rem 1rem; color:#4d5d5c}}
.confianza b {{display:block; font-size:1.5rem; color:{comun.VERDE}}}
.servicio {{border:1px solid {comun.BORDE}; border-radius:16px; padding:1rem; height:100%}}
.servicio b {{color:{comun.VERDE}; font-size:1.05rem}}
.paso {{text-align:center; padding:.6rem}}
.paso .n {{display:inline-block; width:2.1rem; height:2.1rem; line-height:2.1rem; border-radius:99px; background:{comun.VERDE};
  color:white; font-weight:700}}
.aviso-noche {{background:#fff4ef; border:1px solid #f4c3b0; color:#7a3418; border-radius:14px; padding:.8rem 1rem;}}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Control de la demo** · simular cuándo entra la familia")
    dia = st.date_input("Día", datetime(2026, 11, 3))
    hora = st.time_input("Hora", time(23, 10))
ahora = datetime.combine(dia, hora)
finde = ahora.weekday() >= 5
abierto = (9 <= ahora.hour < (18 if finde else 20))
horario = "9:00–18:00" if finde else "9:00–20:00"
cuando_llamamos = "hoy, en menos de 24 h" if abierto else (
    "mañana a partir de las 9:00" if ahora.hour >= 9 else "hoy a partir de las 9:00")


def guardar_lead(canal: str, ficha: dict, conversacion: list | None = None) -> None:
    with comun.conexion() as con:
        con.execute("CREATE TABLE IF NOT EXISTS leads_web (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, canal TEXT, "
                    "ficha TEXT, conversacion TEXT)")
        con.execute("INSERT INTO leads_web (fecha, canal, ficha, conversacion) VALUES (?,?,?,?)",
                    (ahora.isoformat(timespec="minutes"), canal, json.dumps(ficha, ensure_ascii=False),
                     json.dumps(conversacion or [], ensure_ascii=False)))


st.markdown("<span class='chip demo'>Concepto para la entrevista · no es la web oficial de Qida</span>",
            unsafe_allow_html=True)
estado = (f"<span class='estado' style='background:#e6f2f1;color:{comun.VERDE}'>● Abierto ahora</span>" if abierto else
          "<span class='estado' style='background:#fff4ef;color:#a8441f'>● Ahora cerrado · te atiende el asistente virtual</span>")
st.markdown(
    f"<div class='cab'>{MARCA}"
    f"<div>Llámanos sin compromiso <span class='tel'>{TELEFONO}</span> · {horario} "
    f"({'fines de semana y festivos' if finde else 'lunes a viernes'}) &nbsp;{estado}</div></div>",
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="hero">
  <h1>Cuidamos a los tuyos en casa</h1>
  <div class="bajada">Cuidadoras profesionales desde 2 horas a la semana, sin permanencia y con una Referente Social
  que os acompaña de principio a fin.</div>
  <span class="precio">Desde 170 €/mes · presupuesto gratis</span>
</div>
<div class="confianza">
  <div><b>4,8/5</b>calidad del servicio</div>
  <div><b>+25.000</b>familias atendidas</div>
  <div><b>Acreditada</b>empresa de atención domiciliaria</div>
  <div><b>0 €</b>hasta valorar tu caso</div>
</div>
""",
    unsafe_allow_html=True,
)

izq, der = st.columns([3, 2], gap="large")
with izq:
    st.markdown("#### Nuestros servicios")
    for col, (titulo, texto) in zip(st.columns(3), [
        ("Cuidadoras por horas", "Desde 2 horas a la semana, cuando lo necesitéis."),
        ("Cuidadora interna", "Acompañamiento 24 horas, viviendo en casa."),
        ("Fines de semana y noches", "Para que tú también puedas descansar."),
    ]):
        col.markdown(f"<div class='servicio'><b>{titulo}</b><br><span style='color:#4d5d5c'>{texto}</span></div>",
                     unsafe_allow_html=True)
    st.markdown("#### Cómo funciona")
    PASOS = ["Nos cuentas tu caso", "Tu asesor/a familiar te llama", "Valoramos sin coste y preparamos tu plan",
             "Te proponemos la cuidadora que mejor encaja y tú decides"]
    for col, (n, texto) in zip(st.columns(4), enumerate(PASOS, 1)):
        col.markdown(f"<div class='paso'><span class='n'>{n}</span><br>{texto}</div>", unsafe_allow_html=True)

with der:
    with st.form("formulario", border=True):
        st.markdown("#### Déjanos tus datos y te llamamos")
        servicio = st.selectbox("¿Qué necesitas?", ["Cuidadora por horas", "Interna", "Fin de semana", "Noche"])
        telefono = st.text_input("Teléfono", placeholder="600 000 000")
        cp = st.text_input("Código postal", placeholder="28001")
        acepto = st.checkbox("Acepto que tratéis mis datos para llamarme. " + PRIVACIDAD)
        enviado = st.form_submit_button("Solicitar llamada", type="primary", use_container_width=True)
    if enviado:
        errores = []
        if not re.fullmatch(r"[6789]\d{8}", telefono.replace(" ", "")):
            errores.append("el teléfono (9 cifras)")
        if not re.fullmatch(r"\d{5}", cp.strip()):
            errores.append("el código postal (5 cifras)")
        if not acepto:
            errores.append("aceptar el tratamiento de datos")
        if errores:
            st.error("Revisa " + ", ".join(errores) + ".")
        else:
            guardar_lead("Formulario", {"servicio": servicio, "telefono": telefono, "cp": cp})
            st.success(f"¡Recibido! Te llamamos **{cuando_llamamos}** al {telefono}.")
    if not abierto:
        st.markdown(f"<div class='aviso-noche'>Son las {ahora:%H:%M}. Ahora no hay nadie al teléfono: deja tus datos o "
                    f"habla con el asistente virtual y te llamamos {cuando_llamamos}.</div>", unsafe_allow_html=True)


def vista_equipo(ficha: dict) -> None:
    with st.expander("Vista del equipo · solo en la demo, la familia no la ve", icon=":material/badge:"):
        if ficha.get("escalar"):
            st.error(f"Pasa a una persona: {ficha.get('motivo_escalado') or ''}")
        if ficha.get("llamada_agendada"):
            st.success(f"Llamada agendada: {cuando_llamamos}")
        campos = [
            ("Ciudad", ficha.get("ciudad")), ("Servicio", ficha.get("servicio")),
            ("Teléfono", ficha.get("telefono")), ("Nombre", ficha.get("nombre")),
            ("Urgente", "Sí" if ficha.get("urgencia") else "No"),
            ("Dependencia", "La menciona" if ficha.get("menciona_dependencia") else "No"),
        ]
        for col, (k, v) in zip(st.columns(3) * 2, campos):
            col.metric(k, v or "pendiente")
        st.caption("Entra en el CRM como un lead más (canal «Chat») y pasa por la cola de llamadas.")


def conversaciones_grabadas() -> list[dict]:
    """Conversaciones reales del asistente v3 con casos que no había visto (y algunas de ajuste), aprobadas por la evaluación."""
    salida = []
    for fichero in ("resultados_v3_reserva2.json", "resultados_v3.json"):
        ruta = comun.RAIZ / "eval" / fichero
        if ruta.exists():
            for r in json.loads(ruta.read_text(encoding="utf-8")):
                if r["checks_ok"] and r["juez"].get("veredicto") == "aprueba":
                    salida.append(r)
    return salida


def chat_grabado() -> None:
    st.info("**Modo grabado:** no hay modelo conectado en este ordenador, así que el chat reproduce conversaciones "
            "**reales** del asistente en la evaluación (versión 3). Para chatear en directo hace falta Claude Code.",
            icon=":material/play_circle:")
    grabadas = conversaciones_grabadas()
    if not grabadas:
        st.warning("No hay conversaciones grabadas. Ejecuta la evaluación (`python eval/ejecutar.py`).")
        return
    etiquetas = {f"{r['categoria'].replace('_', ' ').capitalize()} · «{r['historial'][0]['texto'][:60]}»": r for r in grabadas}
    elegida = etiquetas[st.selectbox("Elige una conversación", list(etiquetas))]
    with st.container(height=320):
        st.chat_message("assistant").write("Hola, soy un **asistente virtual con IA**, no una persona. ¿Qué necesitáis?")
        for m in elegida["historial"]:
            st.chat_message("user" if m["rol"] == "usuario" else "assistant").write(m["texto"])
    vista_equipo(elegida["ficha"])


@st.dialog("Asistente virtual de Qida", width="large")
def chat():
    historial = st.session_state.setdefault("historial", [])
    ficha = st.session_state.setdefault("ficha", {})
    st.error("**¿Es una urgencia médica?** Llama ahora al **112**.", icon=":material/emergency:")
    if llm.modo() == "grabado":
        chat_grabado()
        return
    acepto = st.checkbox("Acepto que tratéis lo que escriba, incluidos datos de salud que yo cuente, para llamarme. "
                         + PRIVACIDAD, key="acepto_chat")

    caja = st.container(height=320)
    with caja:
        st.chat_message("assistant").write(
            "Hola, soy un **asistente virtual con IA**, no una persona. Te ayudo a que un asesor te llame "
            f"{cuando_llamamos}. ¿Qué necesitáis?")
        for m in historial:
            st.chat_message("user" if m["rol"] == "usuario" else "assistant").write(m["texto"])

    pregunta = None
    if acepto:
        if not historial:
            r1, r2, r3 = st.columns(3)
            for col, texto in ((r1, "Necesito ayuda urgente en casa"), (r2, "Quiero saber precios"),
                               (r3, "Tengo dudas con la Dependencia")):
                if col.button(texto, use_container_width=True):
                    pregunta = texto
        if st.button("Prefiero que me llame una persona", icon=":material/support_agent:", use_container_width=True):
            pregunta = "Prefiero que me llame una persona"
    pregunta = st.chat_input("Escribe aquí…", disabled=not acepto) or pregunta
    if not acepto:
        st.caption("Para escribir, acepta el tratamiento de datos.")

    if pregunta:
        historial.append({"rol": "usuario", "texto": pregunta})
        with caja:
            st.chat_message("user").write(pregunta)
            with st.chat_message("assistant"), st.spinner("Escribiendo… (unos segundos)"):
                try:
                    texto, nueva = asistente.responder(historial, ahora)
                except ErrorModelo as e:
                    st.error(f"No he podido llamar al modelo: {e}. Si no tienes Claude Code, arranca con QIDA_MODO=grabado.")
                    historial.pop()
                    return
                st.write(texto)
        historial.append({"rol": "asistente", "texto": texto})
        st.session_state["ficha"] = ficha = nueva or ficha
        if ficha.get("telefono") and not st.session_state.get("guardado"):
            guardar_lead("Chat", ficha, historial)
            st.session_state["guardado"] = True

    vista_equipo(ficha)
    if st.button("Empezar de nuevo"):
        for k in ("historial", "ficha", "guardado"):
            st.session_state.pop(k, None)
        st.rerun()


with st.container(key="boton-chat"):
    if st.button("¿Hablamos? Asistente virtual", icon=":material/chat:"):
        chat()
