"""Lo que ve la familia: concepto de la web de Qida, de una sola columna y con scroll, con el asistente de noche en un botón flotante.

Estructura: cabecera con teléfono → portada con foto → confianza → servicios (con fotos) → el asistente de noche con una
conversación real → cómo funciona (línea de tiempo) → contacto (formulario) → pie. Solo lo que enseña la demo: lo que ya cuenta
qida.es (preguntas frecuentes, cobertura, tareas) no se repite.
Auditada en docs/auditoria-web-familia.md y docs/pruebas-calidad.md: IA declarada, privacidad antes de recoger datos, 112
visible, formulario que funciona y con límites, teléfono y horario, señales de confianza y coherencia con el anuncio.
Marca, servicios y cifras públicas tomados de qida.es (2 de noviembre de 2026). No es la web oficial. Las fotografías (app/static/fotos) son de
qida.es, propiedad de Qida, y se usan solo en esta demo privada.
"""
import base64
import json
import logging
import re
import time as reloj
from datetime import datetime, time

import streamlit as st

import comun
from motor import asistente, leads, limites, llm
from motor.contacto import horario, limpiar_ficha, normalizar_telefono

TELEFONO = "656 726 469"  # el que publica qida.es (comprobado el 2026-11-02; antes la demo llevaba 635 704 124)
SERVICIOS = ["Cuidadora por horas", "Cuidadora interna", "Fines de semana", "Cuidadora nocturna", "Aún no lo sé"]
CASILLA = "Acepto que Qida use mis datos para llamarme y preparar el presupuesto."
CASILLA_CHAT = "Acepto que Qida use lo que escriba, incluidos los datos de salud que cuente, para llamarme."
PRIVACIDAD = ("No hace falta que nos cuentes detalles médicos. Puedes pedir que borremos tus datos cuando quieras. "
              "Política de privacidad (en la web real).")
LOGO_B64 = base64.b64encode(comun.LOGO.read_bytes()).decode() if comun.LOGO.exists() else ""
# El logotipo no va en el repositorio (marca de terceros): sin él, el nombre en la tipografía de los títulos.
MARCA = (f"<img src='data:image/png;base64,{LOGO_B64}' height='34' alt='Qida'>" if LOGO_B64 else
         "<span class='marca-texto'>Qida</span>")
ENLACE_TEL = f"tel:+34{TELEFONO.replace(' ', '')}"
VERDE, MENTA, BORDE, TEXTO, GRIS = comun.VERDE, "#EFF5F5", "#CCE0DF", "#1F2B2A", comun.GRIS_TEXTO

st.markdown(
    f"""
<style>
:root {{--v: {VERDE}; --vm: {comun.VERDE_MEDIO}; --menta: {MENTA}; --borde: {BORDE}; --texto: {TEXTO}; --gris: {GRIS};}}
html {{scroll-behavior: smooth;}}
[data-testid="stMain"] {{scroll-behavior: smooth;}}
header[data-testid="stHeader"] {{display: none;}}
.block-container {{max-width: 1120px !important; padding: 0 1.5rem 7rem !important;}}
.block-container > div > [data-testid="stVerticalBlock"] {{gap: 0 !important;}}
[data-testid="stMarkdownContainer"] a {{text-decoration: none;}}
/* Bandas de color a todo el ancho de la pantalla, sin provocar scroll horizontal */
[class*="st-key-banda-"] {{position: relative; clip-path: inset(0 -100vmax);}}
.st-key-banda-menta {{background: var(--menta); box-shadow: 0 0 0 100vmax var(--menta);}}
.st-key-banda-verde {{background: var(--v); box-shadow: 0 0 0 100vmax var(--v); color: white;}}
.st-key-banda-pie {{background: #00302a; box-shadow: 0 0 0 100vmax #00302a; color: #CFE3E1;}}
.tx-c {{text-align: center;}}
.seccion-web {{padding: 4.2rem 0 1rem;}}
.seccion-web h2 {{font-family: 'DM Sans', Arial, sans-serif !important; font-weight: 400 !important; color: var(--texto);
  font-size: clamp(1.7rem, 3.4vw, 2.3rem); line-height: 1.2; text-align: center; margin: 0 0 .7rem; letter-spacing: -.01em;}}
.seccion-web h2 b {{font-weight: 600; color: var(--v);}}
.seccion-web .sub {{text-align: center; color: var(--gris); max-width: 640px; margin: 0 auto 2.2rem; font-size: 1.05rem; line-height: 1.55;}}
/* Cabecera */
.franja-demo {{display: flex; justify-content: center; gap: .6rem; flex-wrap: wrap; font-size: .78rem; padding: .55rem 0;
  color: var(--gris); border-bottom: 1px solid var(--borde);}}
.franja-demo .chip-demo {{background: #fff4ef; border: 1px solid #f4c3b0; color: #a8441f; border-radius: 99px; padding: 1px 10px;}}
.nav-web {{display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1.1rem 0; flex-wrap: wrap;}}
.nav-web .marca-texto {{font-family: 'DM Serif Display', Georgia, serif; font-size: 2rem; color: var(--v); line-height: 1;}}
.nav-web nav {{display: flex; gap: 1.6rem; flex-wrap: wrap;}}
.nav-web nav a {{color: var(--texto) !important; font-size: .95rem; font-weight: 500;}}
.nav-web nav a:hover {{color: var(--vm) !important;}}
.nav-web .acc {{display: flex; gap: .6rem; align-items: center; flex-wrap: wrap;}}
.btn-w, .btn-o {{display: inline-flex; align-items: center; gap: .45rem; border-radius: 10px; padding: .6rem 1.15rem; font-weight: 600;
  font-size: .95rem; line-height: 1.2; transition: background .15s, color .15s, transform .15s;}}
.btn-w {{background: var(--v); color: white !important; border: 2px solid var(--v);}}
.btn-w:hover {{background: #00302a; border-color: #00302a; transform: translateY(-1px);}}
.btn-o {{background: transparent; color: var(--v) !important; border: 2px solid var(--v);}}
.btn-o:hover {{background: var(--menta);}}
.btn-w.grande, .btn-o.grande {{padding: .85rem 1.6rem; font-size: 1.05rem; border-radius: 12px;}}
.btn-w.blanco {{background: white; color: var(--v) !important; border-color: white;}}
.btn-w.blanco:hover {{background: var(--menta);}}
.material-symbols-rounded.i {{font-size: 1.25em; vertical-align: -.2em;}}
@media (max-width: 760px) {{.nav-web nav {{display: none;}} .nav-web {{justify-content: center;}}}}
/* Portada */
.hero-web {{padding: 4.6rem 0 3.4rem; text-align: center; position: relative;}}
@media (max-width: 760px) {{.hero-web {{overflow: hidden;}}}}
.hero-web::before, .hero-web::after {{content: ""; position: absolute; border-radius: 50%; z-index: 0; pointer-events: none;}}
.hero-web::before {{width: 380px; height: 380px; left: -140px; top: -40px; background: radial-gradient(circle, #CCE0DF 0%, rgba(204,224,223,0) 70%);}}
.hero-web::after {{width: 420px; height: 420px; right: -150px; bottom: -80px; background: radial-gradient(circle, #DDEBEA 0%, rgba(221,235,234,0) 70%);}}
.hero-web > * {{position: relative; z-index: 1;}}
.estado-web {{display: inline-flex; align-items: center; gap: .5rem; font-size: .88rem; font-weight: 600; border-radius: 99px;
  padding: .35rem .95rem; margin-bottom: 1.4rem;}}
.estado-web.abierto {{background: #fff; color: var(--v); border: 1px solid var(--borde);}}
.estado-web.cerrado {{background: #fff4ef; color: #8a3a16; border: 1px solid #f4c3b0;}}
.estado-web .punto {{width: .55rem; height: .55rem; border-radius: 50%; background: currentColor;}}
.hero-web h1 {{font-family: 'DM Sans', Arial, sans-serif !important; font-weight: 300 !important; color: var(--texto);
  font-size: clamp(2.3rem, 5.4vw, 3.8rem); line-height: 1.08; letter-spacing: -.02em; margin: 0 auto 1.2rem; max-width: 860px;}}
.hero-web h1 b {{font-weight: 500; color: var(--v);}}
.hero-web .bajada {{font-size: 1.2rem; line-height: 1.55; color: #3f4f4e; max-width: 680px; margin: 0 auto 1.8rem;}}
.hero-web .ctas {{display: flex; gap: .8rem; justify-content: center; flex-wrap: wrap;}}
.hero-web .precio-web {{margin-top: 1.4rem; color: var(--v); font-weight: 600; font-size: 1rem;}}
/* Confianza */
.confianza-web {{display: grid; grid-template-columns: repeat(4, 1fr); padding: 1.8rem 0 2.2rem;}}
.confianza-web div {{text-align: center; padding: .3rem 1rem; border-left: 1px solid var(--borde); color: var(--gris); font-size: .92rem;}}
.confianza-web div:first-child {{border-left: 0;}}
.confianza-web b {{display: block; font-size: 1.9rem; font-weight: 500; color: var(--v); letter-spacing: -.01em; line-height: 1.15;}}
@media (max-width: 760px) {{.confianza-web {{grid-template-columns: 1fr 1fr; row-gap: 1.2rem;}}
  .confianza-web div:nth-child(3) {{border-left: 0;}}}}
/* Servicios */
.svc {{border: 1px solid var(--borde); border-radius: 20px; background: white; min-height: 400px;
  box-shadow: 0 8px 28px rgba(0,64,57,.06);}}
.svc .foto {{border-radius: 19px 19px 0 0; position: relative; height: 200px; background: var(--menta);}}
.svc .foto img {{width: 100%; height: 100%; object-fit: cover; display: block; border-radius: 19px 19px 0 0;}}
.svc .ic {{position: absolute; left: 1.2rem; bottom: -26px; width: 54px; height: 54px; border-radius: 16px; background: white; color: var(--v);
  display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 20px rgba(0,64,57,.18);}}
.svc .ic span {{font-size: 1.7rem;}}
.svc .cuerpo {{padding: 2.2rem 1.4rem 1.2rem;}}
.svc h3 {{font-family: 'DM Sans', Arial, sans-serif !important; font-weight: 700 !important; color: var(--v); font-size: 1.2rem;
  margin: 0 0 .5rem; padding: 0;}}
.svc p {{color: var(--gris); line-height: 1.55; margin: 0; font-size: .98rem;}}
.st-key-servicios button {{border-radius: 10px !important; border: 2px solid var(--v) !important; color: var(--v) !important;
  background: white !important; font-weight: 600; margin-top: .8rem;}}
.st-key-servicios button:hover {{background: var(--menta) !important;}}
/* Cómo funciona */
.pasos-web {{display: grid; grid-template-columns: repeat(5, 1fr); gap: 0; margin: .5rem 0 1.2rem;}}
.pasos-web .p {{padding: 0 .9rem 0 0; display: flex; flex-direction: column; gap: .4rem;}}
.pasos-web .tx {{display: flex; flex-direction: column; gap: .35rem;}}
.pasos-web .linea {{display: flex; align-items: center; margin-bottom: .6rem;}}
.pasos-web .linea::after {{content: ""; flex: 1; height: 2px; background: var(--borde); margin-left: .6rem;}}
.pasos-web .p:last-child .linea::after {{display: none;}}
.pasos-web .n {{width: 2.6rem; height: 2.6rem; border-radius: 50%; background: var(--v); color: white; font-weight: 600; display: flex;
  align-items: center; justify-content: center; flex: none;}}
.pasos-web b {{color: var(--v); font-size: 1.05rem;}}
.pasos-web span.t {{color: var(--gris); font-size: .94rem; line-height: 1.5;}}
@media (max-width: 860px) {{.pasos-web {{grid-template-columns: 1fr; row-gap: 1.4rem;}} .pasos-web .linea::after {{display: none;}}
  .pasos-web .p {{flex-direction: row; gap: 1rem; align-items: flex-start;}} .pasos-web .linea {{margin: 0;}}}}
/* Foto de portada */
.hero-foto {{max-width: 920px; margin: 2.2rem auto 0; border-radius: 28px; overflow: hidden; box-shadow: 0 24px 60px rgba(0,64,57,.18);
  aspect-ratio: 21 / 9; background: var(--menta);}}
.hero-foto img {{width: 100%; height: 100%; object-fit: cover; object-position: center 30%; display: block;}}
@media (max-width: 760px) {{.hero-foto {{aspect-ratio: 4 / 3; border-radius: 20px;}}}}
/* Asistente de noche: conversación real */
.movil {{max-width: 560px; margin: 0 auto; background: white; border-radius: 28px; padding: 1rem 1.1rem 1.2rem;
  box-shadow: 0 24px 60px rgba(0,64,57,.16); border: 1px solid var(--borde);}}
.movil .cab-chat {{display: flex; align-items: center; gap: .7rem; padding: .3rem .2rem .9rem; border-bottom: 1px solid var(--borde);
  margin-bottom: .9rem;}}
.movil .avatar {{width: 38px; height: 38px; border-radius: 50%; background: var(--v); color: white; display: flex; align-items: center;
  justify-content: center;}}
.movil .avatar span {{font-size: 1.3rem;}}
.movil .cab-chat b {{display: block; color: var(--texto); font-size: .98rem; line-height: 1.2;}}
.movil .cab-chat small {{color: var(--gris); font-size: .78rem;}}
.movil .hora {{margin-left: auto; color: var(--gris); font-size: .8rem; font-weight: 600;}}
.burbuja {{max-width: 86%; padding: .65rem .95rem; border-radius: 18px; margin: 0 0 .6rem; font-size: .95rem; line-height: 1.5;}}
.burbuja.ia {{background: var(--menta); color: var(--texto); border-bottom-left-radius: 6px;}}
.burbuja.yo {{background: var(--v); color: white; margin-left: auto; border-bottom-right-radius: 6px;}}
.resultado {{display: flex; gap: .5rem; flex-wrap: wrap; justify-content: center; margin: 1.1rem 0 .4rem;}}
.resultado span {{background: white; border: 1px solid var(--borde); color: var(--v); border-radius: 99px; padding: .3rem .85rem;
  font-size: .86rem; font-weight: 600;}}
.resultado span.alerta {{background: #fff4ef; border-color: #f4c3b0; color: #8a3a16;}}
.st-key-prueba {{padding-bottom: 3.6rem;}}
.st-key-prueba button {{background: var(--v); color: white; border: 0; border-radius: 12px; font-weight: 600; padding: .75rem 1.4rem;}}
.st-key-prueba button:hover {{background: #00302a;}}
/* Línea de tiempo (cómo funciona) */
.tl {{position: relative; max-width: 900px; margin: 1rem auto 1rem; padding: .5rem 0;}}
.tl::before {{content: ""; position: absolute; left: 50%; top: 1.6rem; bottom: 1.6rem; width: 3px; transform: translateX(-50%);
  background: linear-gradient(180deg, var(--borde), var(--vm) 50%, var(--borde)); border-radius: 3px;}}
.tl .it {{display: grid; grid-template-columns: 1fr 76px 1fr; align-items: center; margin: 0 0 1.6rem;}}
.tl .it .tx {{padding: 0 1.4rem;}}
.tl .it.izq .tx {{grid-column: 1; grid-row: 1; text-align: right;}}
.tl .it.der .tx {{grid-column: 3; grid-row: 1; text-align: left;}}
.tl .nodo {{grid-column: 2; grid-row: 1; position: relative; width: 64px; height: 64px; margin: 0 auto; border-radius: 50%; background: white;
  border: 3px solid var(--v); color: var(--v); display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 22px rgba(0,64,57,.16);}}
.tl .nodo span.material-symbols-rounded {{font-size: 1.9rem;}}
.tl .nodo em {{position: absolute; top: -8px; right: -8px; width: 26px; height: 26px; border-radius: 50%; background: var(--v); color: white;
  font-style: normal; font-weight: 700; font-size: .8rem; display: flex; align-items: center; justify-content: center;}}
.tl .tx b {{display: block; font-size: 1.25rem; color: var(--v); margin-bottom: .3rem; font-weight: 700;}}
.tl .tx p {{margin: 0 !important; color: var(--gris); line-height: 1.55; font-size: 1rem;}}
@media (max-width: 760px) {{
  .tl::before {{left: 32px;}}
  .tl .it {{grid-template-columns: 76px 1fr;}}
  .tl .it .nodo {{grid-column: 1; margin: 0;}}
  .tl .it.izq .tx, .tl .it.der .tx {{grid-column: 2; grid-row: 1; text-align: left; padding: 0 0 0 .6rem;}}
}}
/* Contacto (banda verde) */
.contacto-cab {{text-align: center; padding: 4rem 0 1.4rem; color: white;}}
.contacto-cab h2 {{font-family: 'DM Sans', Arial, sans-serif !important; font-weight: 300 !important; color: white !important;
  font-size: clamp(1.9rem, 4vw, 2.8rem); letter-spacing: -.01em; margin: 0 0 .8rem;}}
.contacto-cab p {{color: #CFE3E1; max-width: 560px; margin: 0 auto 1.2rem !important; line-height: 1.55;}}
.pildoras {{display: flex; gap: .6rem; justify-content: center; flex-wrap: wrap; margin-bottom: 1.2rem;}}
.pildoras span {{background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25); color: white; border-radius: 99px;
  padding: .3rem .9rem; font-size: .88rem;}}
.tel-grande {{display: inline-block; color: white !important; font-size: 2.1rem; font-weight: 500; letter-spacing: -.01em;}}
.tel-et {{color: #CFE3E1; font-size: .9rem; margin-bottom: .1rem;}}
.st-key-contacto {{padding-bottom: 4.2rem;}}
.st-key-contacto [data-testid="stForm"] {{max-width: 600px; margin: 1.2rem auto 0; background: white; border: 0; border-radius: 24px;
  padding: 1.8rem 1.8rem 1.4rem; box-shadow: 0 20px 50px rgba(0,0,0,.25);}}
.st-key-contacto [data-testid="stForm"] label p {{color: var(--texto); font-weight: 500;}}
.st-key-contacto [data-testid="stForm"] input {{border-radius: 10px;}}
.st-key-contacto [data-testid="stFormSubmitButton"] button {{background: var(--v); color: white; border: 0; border-radius: 12px;
  font-weight: 600; padding: .7rem 1rem;}}
.st-key-contacto [data-testid="stFormSubmitButton"] button:hover {{background: #00302a;}}
.st-key-contacto [data-testid="stForm"] .stCaptionContainer, .st-key-contacto [data-testid="stForm"] [data-testid="stCaptionContainer"] p
  {{color: var(--gris) !important;}}
.aviso-noche {{background: #fff4ef; border: 1px solid #f4c3b0; color: #7a3418; border-radius: 14px; padding: .8rem 1rem;
  max-width: 600px; margin: 1.2rem auto 0;}}
.tit-form {{font-family: 'DM Sans', Arial, sans-serif !important; font-weight: 700 !important; color: var(--v); font-size: 1.35rem;
  margin: 0 0 .8rem !important; padding: 0 !important;}}
/* Preguntas frecuentes */
/* Pie */
.pie-web {{display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 2rem; padding: 2.8rem 0 1.4rem; font-size: .92rem; line-height: 1.6;}}
.pie-web .marca-texto {{font-family: 'DM Serif Display', Georgia, serif; font-size: 1.9rem; color: white;}}
.pie-web h3 {{font-family: 'DM Sans', Arial, sans-serif !important; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase;
  color: #8fb7b3 !important; font-weight: 600 !important; margin: 0 0 .5rem; padding: 0;}}
.pie-web a {{color: white !important;}}
.pie-web .urg {{color: #ffd9c9;}}
.legal-web {{border-top: 1px solid rgba(255,255,255,.15); padding: 1rem 0 1.6rem; font-size: .82rem; color: #9fc2bf;}}
@media (max-width: 760px) {{.pie-web {{grid-template-columns: 1fr;}}}}
/* Chat flotante y ventanas */
.st-key-boton-chat {{position: fixed; right: 28px; bottom: 28px; z-index: 999; width: auto !important;}}
.st-key-boton-chat button {{border-radius: 2rem !important; padding: .75rem 1.3rem; background: {VERDE} !important;
  color: white !important; border: 2px solid white !important; box-shadow: 0 8px 24px rgba(0,0,0,.35); font-weight: 600;}}
@media (max-width: 640px) {{.st-key-boton-chat {{right: 14px; bottom: 14px;}}}}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("**Control de la demo** · simular cuándo entra la familia")
    dia = st.date_input("Día", datetime(2026, 11, 3), format="DD/MM/YYYY")
    hora = st.time_input("Hora", time(23, 10))

ahora = datetime.combine(dia, hora)
abierto, franja, cuando_llamamos = horario(ahora)


def guardar_lead(canal: str, ficha: dict, conversacion: list | None = None) -> int:
    """Guarda el lead con el texto exacto que la familia aceptó (formulario o chat) y devuelve su id."""
    with comun.conexion() as con:
        return leads.guardar(con, ahora, canal, ficha, conversacion, CASILLA if canal == "Formulario" else CASILLA_CHAT)


st.session_state.setdefault("form_pintado_en", reloj.time())  # para el tiempo mínimo antes de enviar el formulario


def icono(nombre: str) -> str:
    return f"<span class='material-symbols-rounded'>{nombre}</span>"


# ── Formularios y ventanas ────────────────────────────────────────────────────────────────────────────────────────────────────
def formulario(clave: str, con_titulo: bool = True) -> None:
    """Formulario de «te llamamos». `clave` distingue el de la página del de la ventana (no pueden repetir claves)."""
    with st.form(f"formulario-{clave}", border=con_titulo):  # en la ventana, sin doble marco
        if con_titulo:
            st.markdown("<h3 class='tit-form'>Déjanos tus datos y te llamamos</h3>", unsafe_allow_html=True)
        servicio = st.selectbox("¿Qué necesitas?", SERVICIOS, key=f"servicio-{clave}")
        telefono = st.text_input("Teléfono", placeholder="600 000 000", key=f"telefono-{clave}", max_chars=20)
        cp = st.text_input("Código postal", placeholder="28001", key=f"cp-{clave}", max_chars=5)
        acepto = st.checkbox(CASILLA, key=f"acepto-{clave}")
        st.caption(PRIVACIDAD)
        enviado = st.form_submit_button("Quiero que me llaméis", type="primary", width="stretch")
    if enviado:  # un doble clic con el mismo teléfono no duplica el lead; otro teléfono es otra familia
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
        elif st.session_state.get("formulario_enviado") != tel:
            ok, motivo = limites.validar_formulario(st.session_state.get("form_envios", 0),
                                                    reloj.time() - st.session_state["form_pintado_en"])
            if not ok:
                comun.nota(motivo, "neutra")
            else:
                guardar_lead("Formulario", {"servicio": servicio, "telefono": tel, "cp": cp.strip()})
                st.session_state["formulario_enviado"] = tel
                st.session_state["form_envios"] = st.session_state.get("form_envios", 0) + 1
    if st.session_state.get("formulario_enviado"):
        tel = st.session_state["formulario_enviado"]
        comun.nota(f"**¡Recibido!** Tu asesor/a familiar te llamará al {tel[:3]} {tel[3:6]} {tel[6:]} {cuando_llamamos}.")


@st.dialog("Déjanos tus datos y te llamamos")
def formulario_ventana() -> None:
    formulario("ventana", con_titulo=False)


# ── Asistente virtual ────────────────────────────────────────────────────────────────────────────────────────────────────
def vista_equipo(ficha: dict, cuando: str) -> None:
    ficha = limpiar_ficha(ficha)  # defensa en profundidad: nunca se pinta HTML que venga del modelo
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
    acepto = st.checkbox(CASILLA_CHAT, key="acepto_chat")
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
    pregunta = st.chat_input("Escribe aquí…", disabled=not acepto, max_chars=limites.MAX_CARACTERES) or pregunta
    if not acepto:
        st.caption("Para escribir, marca la casilla.")
    if pregunta:  # límites antes de llamar al modelo (coste y abuso): un mensaje rechazado nunca llega a él
        admitido, motivo = limites.validar_mensaje(pregunta, sum(m["rol"] == "usuario" for m in historial))
        if not admitido:
            comun.nota(motivo, "neutra")
            pregunta = None

    if pregunta:
        historial.append({"rol": "usuario", "texto": pregunta})
        with caja:
            st.chat_message("user").write(pregunta)
            with st.chat_message("assistant"), st.spinner("Escribiendo… (unos segundos)"):
                try:
                    texto, nueva = asistente.responder(limites.historial_para_el_modelo(historial), ahora)
                except Exception:  # noqa: BLE001 · la familia nunca ve un error técnico; el detalle va al registro
                    logging.exception("Fallo del asistente")
                    texto, nueva = (f"Ahora mismo no puedo responder. Déjanos tu teléfono en el formulario o llámanos al "
                                    f"{TELEFONO} a partir de las 9:00."), {}
                st.write(texto)
        historial.append({"rol": "asistente", "texto": texto})
        # La ficha la escribe el modelo a partir de lo que dice la familia: se valida antes de guardarla o pintarla
        st.session_state["ficha"] = ficha = limpiar_ficha(nueva) if nueva else ficha
        # Se guarda con teléfono, o sin él si hay que pasarlo a una persona (si no, «te dejo anotada la petición» sería falso)
        marca = ficha.get("telefono") or ("escalar" if ficha.get("escalar") else None)
        if marca and st.session_state.get("guardado") != marca:
            st.session_state.setdefault("lead_ids", []).append(guardar_lead("Chat", ficha, historial))
            st.session_state["guardado"] = marca

    vista_equipo(ficha, cuando_llamamos)
    if st.session_state.get("lead_ids"):  # lo que haría el equipo ante «borrad mis datos» (derecho de supresión)
        if st.button("Vista del equipo: atender la petición de borrado", icon=":material/delete:"):
            with comun.conexion() as con:
                borrados = sum(leads.borrar(con, i) for i in st.session_state.pop("lead_ids"))
            for k in ("historial", "ficha", "guardado"):
                st.session_state.pop(k, None)
            comun.nota(f"Borrados {borrados} registros de esta conversación (ficha, conversación y consentimiento).", "neutra")
    if st.button("Empezar de nuevo"):
        for k in ("historial", "ficha", "guardado", "lead_ids"):
            st.session_state.pop(k, None)
        st.rerun()


# ── Cabecera ────────────────────────────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="franja-demo"><span class="chip-demo">Concepto para la entrevista</span><span>No es la web oficial de Qida</span></div>
<div class="nav-web">
  <div>{MARCA}</div>
  <nav aria-label="Principal"><a href="#servicios">Servicios</a><a href="#asistente">Asistente de noche</a>
    <a href="#como-funciona">Cómo funciona</a><a href="#contacto">Contacto</a></nav>
  <div class="acc"><a class="btn-o" href="{ENLACE_TEL}">{icono('call')} {TELEFONO}</a>
    <a class="btn-w" href="#contacto">Solicita información</a></div>
</div>""",
    unsafe_allow_html=True,
)

# ── Portada ────────────────────────────────────────────────────────────────────────────────────────────────────
estado = (f"<span class='estado-web abierto'><span class='punto'></span>Abierto ahora · {franja}</span>" if abierto else
          "<span class='estado-web cerrado'><span class='punto'></span>Ahora cerrado · te atiende el asistente virtual</span>")
st.markdown(
    f"""
<section class="hero-web" aria-labelledby="titulo-portada">
  {estado}
  <h1 id="titulo-portada">Cuidado de personas mayores a domicilio, <b>con seguimiento profesional real</b></h1>
  <p class="bajada">Una cuidadora con experiencia, una Referente Social que acompaña a tu familia y un equipo sociosanitario
  detrás. Desde 1 hora a la semana y sin permanencia.</p>
  <div class="ctas"><a class="btn-w grande" href="#contacto">Solicitar información</a>
    <a class="btn-o grande" href="{ENLACE_TEL}">{icono('call')} Llamar ahora</a></div>
  <div class="precio-web">Desde 170 €/mes · presupuesto gratis</div>
  <div class="hero-foto"><img src="app/static/fotos/portada.webp" alt="Una cuidadora abraza a una mujer mayor en su casa"></div>
</section>
<div class="confianza-web">
  <div><b>4,8/5</b>calidad del servicio</div>
  <div><b>+25.000</b>familias atendidas</div>
  <div><b>Acreditada</b>empresa de atención domiciliaria</div>
  <div><b>0 €</b>hasta valorar tu caso</div>
</div>""",
    unsafe_allow_html=True,
)


# ── Servicios ────────────────────────────────────────────────────────────────────────────────────────────────────
st.markdown("<div id='servicios'></div>", unsafe_allow_html=True)
st.markdown("<section class='seccion-web'><h2>Servicios de <b>cuidadoras a domicilio</b></h2>"
            "<p class='sub'>Cuidado flexible, desde 1 hora a la semana. Elige el que mejor encaja con tu familia.</p></section>",
            unsafe_allow_html=True)
with st.container(key="servicios"):
    for col, (icono_svc, titulo, texto, opcion, foto) in zip(st.columns(3, gap="medium"), [
        ("schedule", "Cuidadoras por horas", "Desde 1 hora a la semana hasta 40, con turnos de día, de noche o de fin de semana. "
                                               "A la medida de vuestra situación.", "Cuidadora por horas", "horas"),
        ("home_health", "Cuidadoras internas 24 h", "Cuidado permanente: una cuidadora que vive en casa, con presencia de día "
                                                    "y de noche.", "Cuidadora interna", "interna"),
        ("weekend", "Cuidadoras de fin de semana", "Un respiro para la familia. La cuidadora se ocupa de higiene, medicación, "
                                                   "comidas y compañía.", "Fines de semana", "finde"),
    ]):
        col.markdown(f"<div class='svc'><div class='foto'><img src='app/static/fotos/{foto}.webp' alt='{titulo}'>"
                     f"<div class='ic'>{icono(icono_svc)}</div></div>"
                     f"<div class='cuerpo'><h3>{titulo}</h3><p>{texto}</p></div></div>", unsafe_allow_html=True)
        if col.button("Pedir información", key=f"servicio-btn-{opcion}", width="stretch"):
            st.session_state["servicio-ventana"] = opcion  # el formulario se abre con este servicio ya elegido
            formulario_ventana()

# ── Asistente de noche ────────────────────────────────────────────────────────────────────────────────────────────────────
st.markdown("<div id='asistente'></div>", unsafe_allow_html=True)
with st.container(key="banda-menta"):
    st.markdown(
        f"""
<section class="seccion-web"><h2>A las 23:10, <b>alguien te contesta</b></h2>
<p class="sub">Fuera de horario no hay nadie al teléfono. El asistente virtual escucha, marca la urgencia y deja la llamada
agendada para la mañana. Esta es una conversación real de la evaluación del asistente.</p>
<div class="movil">
  <div class="cab-chat"><div class="avatar">{icono('smart_toy')}</div><div><b>Asistente virtual de Qida</b>
    <small>Una IA, no una persona</small></div><span class="hora">23:10</span></div>
  <div class="burbuja yo">Hola, para mi padre en Sevilla, le han dado el alta hoy</div>
  <div class="burbuja ia">Lo siento mucho, sé que es un momento difícil. Trabajamos en Sevilla. Como ya es de noche, un asesor familiar
    llamará mañana a partir de las 9:00. ¿Qué tipo de ayuda necesita tu padre al volver a casa, y a qué teléfono te podemos llamar?</div>
  <div class="burbuja yo">Es urgente, no puede quedarse solo</div>
  <div class="burbuja ia">Entiendo, es una situación delicada y la marcamos como urgente. Si tu padre corre peligro en algún momento,
    llama al 112. ¿Necesita compañía de día, de noche o las 24 horas? Y dime un teléfono para que el asesor os llame.</div>
</div>
<div class="resultado"><span class="alerta">Marcada como urgente</span><span>Teléfono recogido</span>
  <span>Llamada agendada, mañana a las 9:00</span><span>Entra la primera en la cola de llamadas</span></div></section>""",
        unsafe_allow_html=True)
    with st.container(key="prueba"):
        _, centro, _ = st.columns([1, 1, 1])
        if centro.button("Probar el asistente", icon=":material/chat:", width="stretch", key="probar-asistente"):
            chat()

# ── Cómo funciona ────────────────────────────────────────────────────────────────────────────────────────────────────
PASOS = [("hearing", "Escuchamos", "Por teléfono, en el formulario o, de noche, con el asistente virtual. Entendemos tu situación."),
         ("support_agent", "Asesoramos", "Un asesor/a familiar te llama en menos de 24 h (a las 9:00 si escribes de noche)."),
         ("assignment_turned_in", "Valoramos", "Valoración del caso y Plan de Trabajo Individual con tu Referente Social."),
         ("diversity_1", "Seleccionamos", "Te proponemos a la cuidadora que mejor encaja. La conoces y decides tú."),
         ("home", "Iniciamos", "Empieza el servicio, con seguimiento para que todo vaya bien.")]
st.markdown("<div id='como-funciona'></div>", unsafe_allow_html=True)
st.markdown(
    "<section class='seccion-web'><h2>Empieza con Qida en <b>solo 5 pasos</b></h2>"
    "<p class='sub'>Del primer contacto al primer día de servicio, acompañado en cada paso.</p>"
    "<div class='tl'>" + "".join(
        f"<div class='it {'izq' if n % 2 else 'der'}'><div class='nodo'>{icono(ic)}<em>{n}</em></div>"
        f"<div class='tx'><b>{t}</b><p>{d}</p></div></div>" for n, (ic, t, d) in enumerate(PASOS, 1)) +
    "</div></section>", unsafe_allow_html=True)

# ── Contacto ────────────────────────────────────────────────────────────────────────────────────────────────────
st.markdown("<div id='contacto'></div>", unsafe_allow_html=True)
with st.container(key="banda-verde"):
    st.markdown(
        f"""
<section class="contacto-cab"><h2>Te llamamos en menos de 24 h</h2>
<p>Un asesor familiar responde a tus dudas para entender la situación de la persona a cuidar. Te atendemos de {franja}.</p>
<div class="pildoras"><span>Sin coste</span><span>Respuesta rápida</span><span>Valoración antes de pagar</span></div>
<div class="tel-et">¿Prefieres llamar ahora?</div><a class="tel-grande" href="{ENLACE_TEL}">{TELEFONO}</a></section>""",
        unsafe_allow_html=True)
    with st.container(key="contacto"):
        formulario("pagina")
        if not abierto:
            st.markdown(f"<div class='aviso-noche'>Son las {ahora:%H:%M} y ahora no podemos atenderte por teléfono. Déjanos tus "
                        f"datos o habla con el asistente virtual: te llamamos {cuando_llamamos}.</div>", unsafe_allow_html=True)

# ── Pie ────────────────────────────────────────────────────────────────────────────────────────────────────
with st.container(key="banda-pie"):
    st.markdown(
        f"""
<div class="pie-web">
  <div><span class="marca-texto">Qida</span><p>Cuidado de personas mayores a domicilio, con seguimiento profesional real.</p></div>
  <div><h3>Contacto</h3><a href="{ENLACE_TEL}">{TELEFONO}</a><br>{franja}</div>
  <div><h3>Si es una urgencia</h3><span class="urg">Llama al <b>112</b>. Este asistente y este formulario no atienden urgencias.</span></div>
</div>
<div class="legal-web">Concepto de Máximo Fernández Catalán para su candidatura de AI Product Builder en Qida. No es la web oficial: marca,
servicios y cifras públicas tomados de qida.es (2 de noviembre de 2026). El asistente es una IA, no una persona.</div>""",
        unsafe_allow_html=True)



with st.container(key="boton-chat"):
    if st.button("¿Hablamos? Asistente virtual", icon=":material/chat:"):
        chat()
