"""Lo que ve la familia: concepto de la web de Qida con el asistente de noche en un botón flotante.

Auditada en docs/auditoria-web-familia.md: IA declarada, privacidad antes de recoger datos, 112 visible, formulario que
funciona, teléfono y horario, señales de confianza, coherencia con el anuncio, respuestas rápidas y salida a una persona.
Marca, teléfono, servicios y cifras públicas tomados de qida.es (2 de noviembre de 2026). No es la web oficial.
"""
import base64
import json
import logging
import re
from datetime import datetime, time

import streamlit as st

import comun
from motor import asistente, llm

TELEFONO = "635 704 124"  # el que publica qida.es
SERVICIOS = ["Cuidadora por horas", "Cuidadora interna", "Fines de semana", "Cuidadora nocturna", "Aún no lo sé"]
CASILLA = "Acepto que Qida use mis datos para llamarme y preparar el presupuesto."
PRIVACIDAD = ("No hace falta que nos cuentes detalles médicos. Puedes pedir que borremos tus datos cuando quieras. "
              "Política de privacidad (en la web real).")
# Festivos nacionales de referencia (cada comunidad tiene los suyos; los locales no están)
FESTIVOS = {(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)}
LOGO_B64 = base64.b64encode(comun.LOGO.read_bytes()).decode() if comun.LOGO.exists() else ""
# El logotipo no va en el repositorio (marca de terceros): sin él, el nombre en la tipografía de los títulos.
MARCA = (f"<img src='data:image/png;base64,{LOGO_B64}' height='38' alt='Qida'>" if LOGO_B64 else
         f"<span style='font-family:DM Serif Display,Georgia,serif;font-size:2rem;color:{comun.VERDE}'>Qida</span>")

st.markdown(
    f"""
<style>
.block-container {{padding-bottom: 6rem;}}
.st-key-boton-chat {{position: fixed; right: 28px; bottom: 28px; z-index: 999; width: auto !important;}}
.st-key-boton-chat button {{border-radius: 2rem !important; padding: .75rem 1.3rem; background: {comun.VERDE} !important;
  color: white !important; border: 0; box-shadow: 0 8px 24px rgba(0,64,57,.28); font-weight: 600;}}
.cab {{display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.8rem; padding:.2rem 0 .9rem;
  border-bottom:1px solid {comun.BORDE}; margin-bottom:1rem}}
.cab a.tel {{color:{comun.VERDE}; font-weight:700; text-decoration:none}}
.cab .estado {{font-size:.85rem; padding:2px 10px; border-radius:99px}}
.st-key-hero {{background:{comun.FONDO}; border-radius:24px; padding:2.4rem 2.6rem; margin-bottom:1rem; gap:0}}
.hero h1 {{margin:0 0 .5rem; font-size:2.6rem; line-height:1.1}}
.hero .bajada {{font-size:1.15rem; color:#4d5d5c}}
.st-key-hero .st-key-acciones {{margin-top:1.6rem !important; gap:.6rem}}
.st-key-acciones a, .st-key-acciones button {{border-radius:99px !important; padding:.5rem 1.1rem !important; min-height:0 !important}}
.st-key-acciones a p, .st-key-acciones button p {{font-weight:700 !important; font-size:1rem}}
.st-key-acciones button {{background:white !important; border:2px solid {comun.VERDE} !important; color:{comun.VERDE} !important}}
.st-key-acciones .st-key-llamar button {{background:{comun.VERDE} !important; color:white !important}}
.telefono-grande {{display:block; text-align:center; font-size:2.2rem; font-weight:700; color:{comun.VERDE} !important;
  text-decoration:none !important; border:2px solid {comun.BORDE}; border-radius:16px; padding:.8rem; margin:.4rem 0 .8rem}}
.precio {{display:inline-block; margin:.9rem 0 .4rem; color:{comun.VERDE}; font-weight:700}}
.confianza {{display:flex; gap:1rem; flex-wrap:wrap; justify-content:space-between; margin:.2rem 0 1.4rem}}
.confianza div {{flex:1; min-width:150px; border:1px solid {comun.BORDE}; border-radius:14px; padding:.7rem 1rem; color:#4d5d5c}}
.confianza b {{display:block; font-size:1.5rem; color:{comun.VERDE}}}
.servicio {{border:1px solid {comun.BORDE}; border-radius:16px; padding:1rem; height:100%}}
.servicio b {{color:{comun.VERDE}; font-size:1.05rem}}
.pasos {{display:grid; grid-template-columns:repeat(4, 1fr); gap:0; margin:.4rem 0 1rem}}
.paso {{display:flex; flex-direction:column; gap:.3rem; padding-right:1rem}}
.paso .linea {{display:flex; align-items:center; margin-bottom:.5rem}}
.paso .linea::after {{content:""; flex:1; height:2px; background:{comun.BORDE}; margin-left:.5rem}}
.paso:last-child .linea::after {{display:none}}
.paso .n {{flex:none; display:inline-flex; align-items:center; justify-content:center; width:2.3rem; height:2.3rem;
  border-radius:99px; background:{comun.VERDE}; color:white; font-weight:700; font-size:1.05rem}}
.paso b {{color:{comun.VERDE}; font-size:1.02rem; line-height:1.3}}
.paso > span {{color:#4d5d5c; font-size:.92rem; line-height:1.45}}
.aviso-noche {{background:#fff4ef; border:1px solid #f4c3b0; color:#7a3418; border-radius:14px; padding:.8rem 1rem;}}
@media (max-width: 640px) {{
  .st-key-hero {{padding:1.4rem 1.3rem}} .hero h1 {{font-size:2rem}}
  .cab img, .cab .marca-texto {{display:none}}  /* en móvil el logotipo ya está en la barra superior */
  .st-key-boton-chat {{right:14px; bottom:14px}}
  .pasos {{grid-template-columns:1fr 1fr; row-gap:1.2rem}} .paso:nth-child(2) .linea::after {{display:none}}
}}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Control de la demo** · simular cuándo entra la familia")
    dia = st.date_input("Día", datetime(2026, 11, 3), format="DD/MM/YYYY")
    hora = st.time_input("Hora", time(23, 10))


def horario(momento: datetime) -> tuple[bool, str, str]:
    """(¿abierto?, horario del día, cuándo llamamos). Fines de semana y festivos: de 9:00 a 18:00."""
    reducido = momento.weekday() >= 5 or (momento.month, momento.day) in FESTIVOS
    cierre = 18 if reducido else 20
    abierto = 9 <= momento.hour < cierre
    franja = f"9:00–{cierre}:00 ({'fines de semana y festivos' if reducido else 'de lunes a viernes'})"
    if abierto:
        cuando = "en menos de 24 horas, dentro del horario de atención"
    elif momento.hour < 9:
        cuando = "hoy a partir de las 9:00"
    else:
        cuando = "mañana a partir de las 9:00"
    return abierto, franja, cuando


ahora = datetime.combine(dia, hora)
abierto, franja, cuando_llamamos = horario(ahora)


def guardar_lead(canal: str, ficha: dict, conversacion: list | None = None) -> None:
    with comun.conexion() as con:
        con.execute("CREATE TABLE IF NOT EXISTS leads_web (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, canal TEXT, "
                    "ficha TEXT, conversacion TEXT)")
        con.execute("INSERT INTO leads_web (fecha, canal, ficha, conversacion) VALUES (?,?,?,?)",
                    (ahora.isoformat(timespec="minutes"), canal, json.dumps(ficha, ensure_ascii=False),
                     json.dumps(conversacion or [], ensure_ascii=False)))


def normalizar_telefono(texto: str) -> str | None:
    """Acepta «612 345 678», «612-345-678», «+34 612345678» o «0034…»; devuelve 9 cifras o None."""
    cifras = re.sub(r"\D", "", texto)
    if cifras.startswith("0034"):
        cifras = cifras[4:]
    elif cifras.startswith("34") and len(cifras) == 11:
        cifras = cifras[2:]
    return cifras if re.fullmatch(r"[6789]\d{8}", cifras) else None


st.markdown("<span class='chip demo'>Concepto para la entrevista · no es la web oficial de Qida</span>",
            unsafe_allow_html=True)
estado = (f"<span class='estado' style='background:#e6f2f1;color:{comun.VERDE}'>● Abierto ahora</span>" if abierto else
          "<span class='estado' style='background:#fff4ef;color:#a8441f'>● Ahora cerrado · te atiende el asistente virtual</span>")
st.markdown(
    f"<div class='cab'>{MARCA}"
    f"<div>Llámanos: <a class='tel' href='tel:+34{TELEFONO.replace(' ', '')}'>{TELEFONO}</a> · {franja} &nbsp;{estado}</div></div>",
    unsafe_allow_html=True,
)
with st.container(key="hero"):
    st.markdown(
        """
<div class="hero">
  <h1>Cuidamos a los tuyos en casa</h1>
  <div class="bajada">Cuidadoras profesionales desde 2 horas a la semana, sin permanencia y con una Referente Social
  que te acompaña de principio a fin.</div>
  <div class="precio">Desde 170 €/mes · presupuesto gratis</div>
</div>""",
        unsafe_allow_html=True,
    )
    with st.container(horizontal=True, key="acciones"):
        pide_telefono = st.button("Llamar ahora", key="llamar", icon=":material/call:")
        pide_llamada = st.button("Prefiero que me llaméis", key="abrir-formulario")
st.markdown(
    f"""
<div class="confianza">
  <div><b>4,8/5</b>calidad del servicio</div>
  <div><b>+25.000</b>familias atendidas</div>
  <div><b>Acreditada</b>empresa de atención domiciliaria</div>
  <div><b>0 €</b>hasta valorar tu caso</div>
</div>
""",
    unsafe_allow_html=True,
)

def formulario(clave: str, con_titulo: bool = True) -> None:
    """Formulario de «te llamamos». `clave` distingue el de la página del de la ventana (no pueden repetir claves)."""
    with st.form(f"formulario-{clave}", border=con_titulo):  # en la ventana, sin doble marco
        if con_titulo:
            st.markdown("#### Déjanos tus datos y te llamamos")
        servicio = st.selectbox("¿Qué necesitas?", SERVICIOS, key=f"servicio-{clave}")
        telefono = st.text_input("Teléfono", placeholder="600 000 000", key=f"telefono-{clave}")
        cp = st.text_input("Código postal", placeholder="28001", key=f"cp-{clave}")
        acepto = st.checkbox(CASILLA, key=f"acepto-{clave}")
        st.caption(PRIVACIDAD)
        enviado = st.form_submit_button("Quiero que me llaméis", type="primary", width="stretch")
    if enviado and not st.session_state.get("formulario_enviado"):
        tel = normalizar_telefono(telefono)
        errores = []
        if not tel:
            errores.append("Escribe un teléfono de 9 cifras (puedes poner +34 delante).")
        if not re.fullmatch(r"\d{5}", cp.strip()):
            errores.append("Escribe un código postal de 5 cifras.")
        if not acepto:
            errores.append("Marca la casilla para que podamos llamarte.")
        if errores:
            comun.nota("<br>".join(errores), "alerta")
        else:
            guardar_lead("Formulario", {"servicio": servicio, "telefono": tel, "cp": cp.strip()})
            st.session_state["formulario_enviado"] = tel
    if st.session_state.get("formulario_enviado"):
        tel = st.session_state["formulario_enviado"]
        comun.nota(f"**¡Recibido!** Tu asesor/a familiar te llamará al {tel[:3]} {tel[3:6]} {tel[6:]} {cuando_llamamos}.")


@st.dialog("Déjanos tus datos y te llamamos")
def formulario_ventana() -> None:
    formulario("ventana", con_titulo=False)


@st.dialog("Llámanos")
def llamar_ventana() -> None:
    enlace = f"tel:+34{TELEFONO.replace(' ', '')}"
    if abierto:
        comun.nota(f"**Abierto ahora** · {franja}. Te atiende tu asesor/a familiar.")
        st.markdown(f"<a class='telefono-grande' href='{enlace}'>{TELEFONO}</a>", unsafe_allow_html=True)
        st.caption("En el móvil, pulsa el número para llamar. La valoración de tu caso es gratuita.")
    else:
        comun.nota(f"**Ahora estamos cerrados.** Son las {ahora:%H:%M} y atendemos de {franja}. Déjanos tu teléfono y "
                   f"te llamamos {cuando_llamamos}.", "neutra")
        formulario("telefono", con_titulo=False)
        st.caption(f"O llámanos en horario de atención al {TELEFONO}. Si es una urgencia médica, llama al 112.")


if pide_llamada:
    formulario_ventana()
if pide_telefono:
    llamar_ventana()

izq, der = st.columns([3, 2], gap="large")
with izq:
    st.markdown("#### Nuestros servicios")
    for col, (titulo, texto) in zip(st.columns(3), [
        ("Cuidadora por horas", "Desde 2 horas a la semana, cuando lo necesites."),
        ("Cuidadora interna", "Acompañamiento las 24 horas, viviendo en casa."),
        ("Fines de semana y noches", "Para que tú también puedas descansar."),
    ]):
        col.markdown(f"<div class='servicio'><b>{titulo}</b><br><span style='color:#4d5d5c'>{texto}</span></div>",
                     unsafe_allow_html=True)
    st.markdown("#### Cómo funciona")
    PASOS = [("Nos cuentas tu caso", "Por teléfono, en el formulario o con el asistente."),
             ("Te llama tu asesor/a", "Entiende qué necesitas y te explica el servicio."),
             ("Valoración gratuita", "Preparamos tu plan con una Referente Social."),
             ("Eliges a tu cuidadora", "Te proponemos la que mejor encaja; tú decides.")]
    st.markdown("<div class='pasos'>" + "".join(
        f"<div class='paso'><div class='linea'><span class='n'>{n}</span></div><b>{titulo}</b><span>{texto}</span></div>"
        for n, (titulo, texto) in enumerate(PASOS, 1)) + "</div>", unsafe_allow_html=True)

with der:
    formulario("pagina")
    if not abierto:
        st.markdown(f"<div class='aviso-noche'>Son las {ahora:%H:%M} y ahora no podemos atenderte por teléfono. Déjanos tus "
                    f"datos o habla con el asistente virtual: te llamamos {cuando_llamamos}.</div>", unsafe_allow_html=True)


def vista_equipo(ficha: dict, cuando: str) -> None:
    with st.expander("Vista del equipo · solo en la demo, la familia no la ve", icon=":material/badge:"):
        if ficha.get("escalar"):
            comun.nota(f"**Pasa a una persona:** {ficha.get('motivo_escalado') or ''}", "alerta")
        if ficha.get("llamada_agendada"):
            comun.nota(f"**Llamada agendada:** {cuando}.")
        campos = [
            ("Ciudad", ficha.get("ciudad")), ("Servicio", ficha.get("servicio")),
            ("Teléfono", ficha.get("telefono")), ("Nombre", ficha.get("nombre")),
            ("Urgente", "Sí" if ficha.get("urgencia") else "No"),
            ("Dependencia", "La menciona" if ficha.get("menciona_dependencia") else "No"),
        ]
        for col, (k, v) in zip(st.columns(3) * 2, campos):
            comun.kpi(col, k, v or "pendiente")
        st.caption("Entra en el CRM como una familia más (canal «Asistente de noche») y aparece en la cola de llamadas.")


def conversaciones_grabadas() -> list[dict]:
    """Conversaciones reales del asistente v3 (casos nuevos y de ajuste) que pasaron la evaluación."""
    salida = []
    for fichero in ("resultados_v3_reserva2.json", "resultados_v3.json"):
        ruta = comun.RAIZ / "eval" / fichero
        if ruta.exists():
            salida += [r for r in json.loads(ruta.read_text(encoding="utf-8"))
                       if r["checks_ok"] and r["juez"].get("veredicto") == "aprueba"]
    return salida


def chat_grabado() -> None:
    comun.nota("**Modo grabado:** este ordenador no tiene el modelo conectado, así que el asistente reproduce conversaciones "
               "**reales** de la evaluación (versión 3). Cada una conserva la hora a la que se hizo.", "neutra")
    grabadas = conversaciones_grabadas()
    if not grabadas:
        comun.nota("No hay conversaciones grabadas. Ejecuta la evaluación (`python eval/ejecutar.py`).", "alerta")
        return
    casos = {c["id"]: c for f in ("casos_reserva2.json", "casos.json")
             if (comun.RAIZ / "eval" / f).exists()
             for c in json.loads((comun.RAIZ / "eval" / f).read_text(encoding="utf-8"))}
    etiquetas = {f"{r['categoria'].replace('_', ' ').capitalize()} · «{r['historial'][0]['texto'][:60]}»": r for r in grabadas}
    elegida = etiquetas[st.selectbox("Elige una conversación", list(etiquetas))]
    momento = datetime.fromisoformat(casos[elegida["id"]]["hora"]) if elegida["id"] in casos else ahora
    _, _, cuando = horario(momento)
    st.caption(f"Conversación grabada a las {momento:%H:%M} de un día {['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'][momento.weekday()]}.")
    with st.container(height=320):
        st.chat_message("assistant").write("Hola, soy el **asistente virtual de Qida**: una IA, no una persona. "
                                           "Cuéntame qué ayuda buscas.")
        for m in elegida["historial"]:
            st.chat_message("user" if m["rol"] == "usuario" else "assistant").write(m["texto"])
    vista_equipo(elegida["ficha"], cuando)


@st.dialog("Asistente virtual de Qida", width="large")
def chat():
    historial = st.session_state.setdefault("historial", [])
    ficha = st.session_state.setdefault("ficha", {})
    comun.nota("**¿Es una urgencia médica?** Llama ahora al **112**.", "alerta")
    if llm.modo() == "grabado":
        chat_grabado()
        return
    acepto = st.checkbox("Acepto que Qida use lo que escriba, incluidos los datos de salud que cuente, para llamarme.",
                         key="acepto_chat")
    st.caption(PRIVACIDAD)

    caja = st.container(height=320)
    with caja:
        st.chat_message("assistant").write(
            "Hola, soy el **asistente virtual de Qida**: una IA, no una persona. Cuéntame qué ayuda buscas y dejo "
            f"preparado que tu asesor/a familiar te llame {cuando_llamamos}.")
        for m in historial:
            st.chat_message("user" if m["rol"] == "usuario" else "assistant").write(m["texto"])

    pregunta = None
    if acepto:
        if not historial:
            r1, r2, r3 = st.columns(3)
            for col, texto in ((r1, "Necesito ayuda urgente en casa"), (r2, "Quiero saber precios"),
                               (r3, "Tengo dudas con la Dependencia")):
                if col.button(texto, width="stretch"):
                    pregunta = texto
        if st.button("Prefiero que me llame una persona", icon=":material/support_agent:", width="stretch"):
            pregunta = "Prefiero que me llame una persona"
    pregunta = st.chat_input("Escribe aquí…", disabled=not acepto) or pregunta
    if not acepto:
        st.caption("Para escribir, marca la casilla.")

    if pregunta:
        historial.append({"rol": "usuario", "texto": pregunta})
        with caja:
            st.chat_message("user").write(pregunta)
            with st.chat_message("assistant"), st.spinner("Escribiendo… (unos segundos)"):
                try:
                    texto, nueva = asistente.responder(historial, ahora)
                except Exception:  # noqa: BLE001 · la familia nunca ve un error técnico; el detalle va al registro
                    logging.exception("Fallo del asistente")
                    texto, nueva = (f"Ahora mismo no puedo responder. Déjanos tu teléfono en el formulario o llámanos al "
                                    f"{TELEFONO} a partir de las 9:00."), {}
                st.write(texto)
        historial.append({"rol": "asistente", "texto": texto})
        st.session_state["ficha"] = ficha = nueva or ficha
        if ficha.get("telefono") and not st.session_state.get("guardado"):
            guardar_lead("Chat", ficha, historial)
            st.session_state["guardado"] = True

    vista_equipo(ficha, cuando_llamamos)
    if st.button("Empezar de nuevo"):
        for k in ("historial", "ficha", "guardado"):
            st.session_state.pop(k, None)
        st.rerun()


with st.container(key="boton-chat"):
    if st.button("¿Hablamos? Asistente virtual", icon=":material/chat:"):
        chat()
