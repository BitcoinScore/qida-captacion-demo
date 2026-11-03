"""Diseño del chat del asistente: panel anclado abajo a la derecha, cabecera de marca, burbujas con hora, indicador de escritura,
resumen de lo que ha entendido el asistente y chips de respuesta rápida.

Funciones puras (texto → HTML) para poder probarlas. Todo lo que escribe la familia o el modelo se escapa ANTES de pintarlo: el
único HTML que llega a la pantalla es el que genera este módulo.
"""
import html
import re
from datetime import datetime, timedelta

import comun

VERDE, MENTA, BORDE = comun.VERDE, "#EFF5F5", comun.BORDE
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")


_NUM_EMERGENCIA = re.compile(r"(?<!\d)(?<!\d )(?<!\d-)(?<!\d\.)(112|024)(?!\d)(?! \d)(?!-\d)(?!\.\d)")


def formato(texto: str) -> str:
    """Texto de la familia o del modelo → HTML seguro: se escapa todo y solo se permiten negritas, saltos de línea y enlaces de
    llamada al 112 y al 024 (que genera este módulo, no el texto)."""
    limpio = html.escape(texto or "", quote=True)
    limpio = _NEGRITA.sub(r"<b>\1</b>", limpio)
    limpio = _NUM_EMERGENCIA.sub(r'<a class="q112" href="tel:\1" aria-label="Llamar al \1">\1</a>', limpio)
    return limpio.replace("\n", "<br>")


def hora(base: datetime, indice: int) -> str:
    """Hora que se enseña bajo cada mensaje: la de la demo y un minuto más por cada intercambio."""
    return (base + timedelta(minutes=indice // 2)).strftime("%H:%M")


AVATAR = (
    "<svg class='cara' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg' role='img' aria-label='Ilustración del asistente'>"
    "<defs>"
    "<linearGradient id='qf' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#D3E8E5'/><stop offset='1' stop-color='#F1F7F6'/></linearGradient>"
    "<radialGradient id='qp' cx='.42' cy='.32' r='.85'><stop offset='0' stop-color='#FADDC2'/><stop offset='.55' stop-color='#F0C4A0'/><stop offset='1' stop-color='#DFA77F'/></radialGradient>"
    "<linearGradient id='qc' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#005A52'/><stop offset='1' stop-color='#003D37'/></linearGradient>"
    "<linearGradient id='qh' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#6A4630'/><stop offset='1' stop-color='#3B261A'/></linearGradient>"
    "</defs>"
    "<rect width='100' height='100' fill='url(#qf)'/>"
    "<path d='M5 100 C7 79 26 70 50 70 C74 70 93 79 95 100 Z' fill='url(#qc)'/>"
    "<path d='M36 71 C40 77 45 80 50 80 C55 80 60 77 64 71 C60 70 56 69.5 50 69.5 C44 69.5 40 70 36 71 Z' fill='#E3AC84'/>"
    "<path d='M37 70.5 C41 78 45.5 82 50 82 C54.5 82 59 78 63 70.5 L66 72 C61 82 56 86 50 86 C44 86 39 82 34 72 Z' fill='#F1F7F6'/>"
    "<path d='M42 60 L58 60 L59 71 C55.5 76 44.5 76 41 71 Z' fill='#E7B38B'/>"
    "<ellipse cx='50' cy='68.5' rx='10.5' ry='4' fill='#B97F5D' opacity='.38'/>"
    "<ellipse cx='29.6' cy='47' rx='3.2' ry='5.6' fill='#E9B792'/><ellipse cx='70.4' cy='47' rx='3.2' ry='5.6' fill='#E9B792'/>"
    "<ellipse cx='29.8' cy='47.5' rx='1.4' ry='3' fill='#D79F7B' opacity='.7'/><ellipse cx='70.2' cy='47.5' rx='1.4' ry='3' fill='#D79F7B' opacity='.7'/>"
    "<path d='M30 43 C30 30.5 38.5 22.5 50 22.5 C61.5 22.5 70 30.5 70 43 C70 53 66.5 62.5 60 67.5 C55.5 70.8 44.5 70.8 40 67.5 C33.5 62.5 30 53 30 43 Z' fill='url(#qp)'/>"
    "<path d='M26.5 49 C22 25 33 11.5 50 11.5 C68 11.5 79 26 73.5 49 C73 40 69.5 32 63.5 27.5 C58 31.5 47 33.5 39.5 30.5 C33.5 34 29 41 26.5 49 Z' fill='url(#qh)'/>"
    "<path d='M31 38 C32.5 28 42 21.5 54 22 C63 22.4 69 27.5 70.5 35 C63.5 29.5 51 27.5 39 33.5 C36 35 33.5 36.5 31 38 Z' fill='#4A3022'/>"
    "<path d='M36 30 C42 24.5 52 23.5 60 26' stroke='#7A5439' stroke-width='1.1' fill='none' stroke-linecap='round' opacity='.7'/>"
    "<path d='M33 34 C40 27.5 53 25.5 66 31' stroke='#7A5439' stroke-width='.9' fill='none' stroke-linecap='round' opacity='.5'/>"
    "<path d='M28.5 46 C27.5 38 29 33 32 30' stroke='#2E1C12' stroke-width='1.2' fill='none' stroke-linecap='round' opacity='.6'/>"
    "<path d='M36.2 40.2 Q41.5 36.2 47.4 38.8 Q41.8 38 36.2 40.2 Z' fill='#4A3022'/>"
    "<path d='M52.6 38.8 Q58.5 36.2 63.8 40.2 Q58.2 38 52.6 38.8 Z' fill='#4A3022'/>"
    "<path d='M37.4 45.6 Q42.5 41.4 47.6 45.6 Q42.5 49.2 37.4 45.6 Z' fill='white'/>"
    "<path d='M52.4 45.6 Q57.5 41.4 62.6 45.6 Q57.5 49.2 52.4 45.6 Z' fill='white'/>"
    "<circle cx='42.7' cy='45.4' r='2.7' fill='#6B4429'/><circle cx='57.7' cy='45.4' r='2.7' fill='#6B4429'/>"
    "<circle cx='42.7' cy='45.4' r='1.25' fill='#1A100A'/><circle cx='57.7' cy='45.4' r='1.25' fill='#1A100A'/>"
    "<circle cx='43.5' cy='44.5' r='.75' fill='white'/><circle cx='58.5' cy='44.5' r='.75' fill='white'/>"
    "<path d='M37 45.7 Q42.5 40.6 48 45.7' stroke='#3B261A' stroke-width='1.25' fill='none' stroke-linecap='round'/>"
    "<path d='M52 45.7 Q57.5 40.6 63 45.7' stroke='#3B261A' stroke-width='1.25' fill='none' stroke-linecap='round'/>"
    "<path d='M39.5 48.6 Q42.5 50 45.5 48.6' stroke='#C8916C' stroke-width='.7' fill='none' opacity='.7'/>"
    "<path d='M54.5 48.6 Q57.5 50 60.5 48.6' stroke='#C8916C' stroke-width='.7' fill='none' opacity='.7'/>"
    "<circle cx='36.2' cy='54' r='4.6' fill='#EE8F82' opacity='.3'/><circle cx='63.8' cy='54' r='4.6' fill='#EE8F82' opacity='.3'/>"
    "<path d='M50.2 46.5 Q48.4 52.8 50.2 54.6 Q51.6 55.4 53 54.2' stroke='#CF9570' stroke-width='1.2' fill='none' stroke-linecap='round'/>"
    "<ellipse cx='48.2' cy='55' rx='1' ry='.6' fill='#C28660' opacity='.55'/><ellipse cx='52.4' cy='55' rx='1' ry='.6' fill='#C28660' opacity='.55'/>"
    "<path d='M42.6 59 Q46.4 57.2 50 58.7 Q53.6 57.2 57.4 59 Q50 61 42.6 59 Z' fill='#C8645A'/>"
    "<path d='M43.2 59.2 Q50 66.8 56.8 59.2 Q50 61.2 43.2 59.2 Z' fill='#DB7A6E'/>"
    "<path d='M45 59.6 Q50 62.4 55 59.6 Q50 60.6 45 59.6 Z' fill='white'/>"
    "<path d='M41.2 57.6 Q41.6 59.6 43 60.4' stroke='#C98E6B' stroke-width='.8' fill='none' stroke-linecap='round' opacity='.7'/>"
    "<path d='M58.8 57.6 Q58.4 59.6 57 60.4' stroke='#C98E6B' stroke-width='.8' fill='none' stroke-linecap='round' opacity='.7'/>"
    "<path d='M26.8 48 C23.5 21.5 39 10.5 50 10.5 C61 10.5 76.5 21.5 73.2 48' stroke='#338581' stroke-width='2.8' fill='none' stroke-linecap='round'/>"
    "<rect x='22.6' y='43' width='7.6' height='15' rx='3.8' fill='#338581'/><rect x='69.8' y='43' width='7.6' height='15' rx='3.8' fill='#338581'/>"
    "<rect x='24' y='45' width='3' height='11' rx='1.5' fill='#5BB0AA' opacity='.55'/><rect x='72.9' y='45' width='3' height='11' rx='1.5' fill='#5BB0AA' opacity='.55'/>"
    "<path d='M26.4 57.5 Q28 70.5 43.5 68.2' stroke='#338581' stroke-width='2' fill='none' stroke-linecap='round'/>"
    "<circle cx='45' cy='68' r='2.6' fill='#004039'/><circle cx='44.4' cy='67.3' r='.8' fill='#338581'/>"
    "</svg>"
)


def cabecera(abierto: bool, cuando: str, telefono_enlace: str) -> str:
    estado = ("En línea · te atiende un asistente virtual" if not abierto else "Asistente virtual · un asesor te atiende por teléfono")
    return f"""
<div class="qchat"></div>
<div class="qcab">
  <div class="qav grande">{AVATAR}<i class="punto"></i></div>
  <div class="qtit"><b>Asistente de Qida</b><small>{html.escape(estado)}</small></div>
</div>
<a class="qurg" href="tel:112"><span class="material-symbols-rounded">emergency</span>
  <span><b>¿Urgencia médica?</b> Llama al 112</span><span class="material-symbols-rounded flecha">call</span></a>"""


def bienvenida(cuando: str) -> str:
    return ("Hola, soy el **asistente virtual de Qida**: una IA, no una persona. Cuéntame qué ayuda buscas y dejo preparado que tu "
            f"asesor/a familiar te llame {cuando}.")


def burbujas(historial: list[dict], base: datetime, cuando: str, escribiendo: bool = False, pendiente: str | None = None) -> str:
    """La conversación entera. `pendiente`: mensaje de la familia que se está contestando (aún no está en el historial)."""
    partes = ["<div class='qconv' role='log' aria-live='polite' aria-label='Conversación con el asistente'>",
              f"<div class='qdia'>Hoy · {base:%H:%M}</div>"]

    def burbuja(rol: str, texto: str, i: int) -> None:
        if rol == "asistente":
            partes.append(f"<div class='qfila ia'><div class='qav'>{AVATAR}</div><div><div class='qb'>{formato(texto)}</div>"
                          f"<div class='qhora'>{hora(base, i)}</div></div></div>")
        else:
            partes.append(f"<div class='qfila yo'><div><div class='qb'>{formato(texto)}</div>"
                          f"<div class='qhora'>{hora(base, i)}</div></div></div>")

    burbuja("asistente", bienvenida(cuando), 0)
    for i, m in enumerate(historial, 1):
        burbuja(m["rol"], m["texto"], i)
    if pendiente is not None:
        burbuja("usuario", pendiente, len(historial) + 1)
    if escribiendo:
        partes.append(f"<div class='qfila ia'><div class='qav'>{AVATAR}</div><div class='qb escribiendo' aria-label='El asistente está "
                      "escribiendo'><i></i><i></i><i></i></div></div>")
    partes.append("</div>")
    return "".join(partes)


def resumen(ficha: dict) -> str:
    """Lo que el asistente ya ha entendido, en etiquetas. Es transparencia para la familia y, en la demo, el lead estructurado."""
    etiquetas = []
    if ficha.get("urgencia"):
        etiquetas.append(("alerta", "emergency_home", "Urgente"))
    if ficha.get("ciudad"):
        etiquetas.append(("", "location_on", ficha["ciudad"]))
    if ficha.get("servicio"):
        etiquetas.append(("", "schedule", ficha["servicio"]))
    if ficha.get("telefono"):
        etiquetas.append(("", "call", "Teléfono anotado"))
    if ficha.get("escalar"):
        etiquetas.append(("alerta", "support_agent", "Lo ve una persona"))
    if not etiquetas:
        return ""
    chips = "".join(f"<span class='qetq {c}'><span class='material-symbols-rounded'>{ic}</span>{html.escape(t)}</span>"
                    for c, ic, t in etiquetas)
    return f"<div class='qresumen'><small>Lo que llevo anotado</small><div>{chips}</div></div>"


def equipo_html(ficha: dict, cuando: str) -> str:
    """Tarjeta «Vista del equipo»: lo que llegaría al CRM con esta conversación. Solo para la demo; la familia no la ve."""
    def fila(nombre: str, valor) -> str:
        vacio = valor in (None, "", False)
        return (f"<div class='qeq-f'><small>{html.escape(nombre)}</small>"
                f"<b class='{'vacio' if vacio else ''}'>{html.escape(str(valor)) if not vacio else 'pendiente'}</b></div>")

    avisos = []
    if ficha.get("escalar"):
        avisos.append(f"<div class='qeq-aviso alerta'><b>Pasa a una persona</b>{html.escape(ficha.get('motivo_escalado') or '')}</div>")
    if ficha.get("llamada_agendada"):
        avisos.append(f"<div class='qeq-aviso'><b>Llamada agendada</b>{html.escape(cuando)}</div>")
    campos = "".join((
        fila("Ciudad", ficha.get("ciudad")), fila("Servicio", ficha.get("servicio")), fila("Teléfono", ficha.get("telefono")),
        fila("Nombre", ficha.get("nombre")), fila("Urgente", "Sí" if ficha.get("urgencia") else "No"),
        fila("Dependencia", "La menciona" if ficha.get("menciona_dependencia") else "No")))
    return ("<div class='qeq'><div class='qeq-cab'><span class='material-symbols-rounded'>badge</span><div><b>Vista del equipo</b>"
            "<small>Solo en la demo · la familia no la ve</small></div></div>" + "".join(avisos) +
            f"<div class='qeq-campos'>{campos}</div>"
            "<p class='qeq-pie'>Entra en el CRM como una familia más (canal «Asistente de noche») y aparece en la cola de llamadas.</p></div>")


CSS = f"""
<style>
/* ── Panel anclado (solo cuando el diálogo contiene el chat) ───────────────────────────────────────────── */
div[data-testid="stDialog"]:has(.qchat) {{background: transparent !important; pointer-events: none; align-items: flex-end !important;
  justify-content: flex-end !important; padding: 0 28px 28px 0 !important;}}
div[data-testid="stDialog"]:has(.qchat) > div {{padding: 0 !important; margin: 0 !important; width: auto !important; max-width: none !important;
  align-items: flex-end !important; justify-content: flex-end !important;}}
section[role="dialog"]:has(.qchat) {{pointer-events: auto; width: 420px !important; max-width: calc(100vw - 24px) !important;
  height: min(720px, calc(100dvh - 56px)) !important; padding: 0 !important; border-radius: 26px !important; overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,40,36,.35), 0 0 0 1px rgba(0,64,57,.10) !important; display: flex; flex-direction: column;
  background: white;}}
section[role="dialog"]:has(.qchat) > h2 {{position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); padding: 0;}}
section[role="dialog"]:has(.qchat) > button[aria-label="Close"] {{position: absolute; top: 14px; right: 14px; z-index: 5; color: white;
  background: rgba(255,255,255,.16); border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center;
  justify-content: center;}}
section[role="dialog"]:has(.qchat) > button[aria-label="Close"]:hover {{background: rgba(255,255,255,.3);}}
section[role="dialog"]:has(.qchat) > button[aria-label="Close"] svg {{fill: white;}}
section[role="dialog"]:has(.qchat) > div {{flex: 1 1 auto; min-height: 0; padding: 0 !important; display: flex; flex-direction: column;}}
section[role="dialog"]:has(.qchat) > div > [data-testid="stVerticalBlock"] {{flex: 1 1 auto; min-height: 0; display: flex !important;
  flex-direction: column; gap: 0 !important; height: 100%;}}
/* Streamlit mete un envoltorio (stLayoutWrapper) y otro stVerticalBlock que, sin límite, crecen con el contenido y desbordan el panel:
   la conversación nunca llegaba a tener scroll. Todos los niveles hasta la conversación se limitan al alto del panel. */
section[role="dialog"]:has(.qchat) > div > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {{flex: 1 1 0; min-height: 0;
  display: flex; flex-direction: column; overflow: hidden;}}
section[role="dialog"]:has(.qchat) > div > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {{
  flex: 1 1 0; min-height: 0; height: 100%; display: flex !important; flex-direction: column; gap: 0 !important;}}
section[role="dialog"]:has(.qchat) [data-testid="stElementContainer"] {{width: 100%; margin: 0; flex: 0 0 auto;}}
section[role="dialog"]:has(.qchat) [data-testid="stElementContainer"]:has(.qconv) {{flex: 1 1 auto; min-height: 0; overflow-y: auto;
  display: flex; flex-direction: column-reverse; background: #F4F8F8; scroll-behavior: smooth;}}
body:has(.qchat) .st-key-boton-chat {{display: none;}}
@media (max-width: 640px) {{
  div[data-testid="stDialog"]:has(.qchat) {{padding: 0 !important;}}
  section[role="dialog"]:has(.qchat) {{width: 100vw !important; max-width: 100vw !important; height: 100dvh !important; border-radius: 0 !important;}}
}}
/* ── Cabecera ──────────────────────────────────────────────────────────────────────────────────────────── */
.qcab {{display: flex; align-items: center; gap: .85rem; padding: 1.15rem 3.4rem 1.05rem 1.2rem; color: white;
  background: linear-gradient(135deg, #004039 0%, #00665f 100%);}}
.qav {{flex: none; width: 34px; height: 34px; border-radius: 50%; background: {MENTA}; color: {VERDE}; display: flex; align-items: center;
  justify-content: center; position: relative; margin-top: 2px;}}
.qav .cara, .ql-av .cara {{width: 100%; height: 100%; border-radius: 50%; display: block;}}
.qav {{overflow: visible;}}
.qav.grande {{width: 46px; height: 46px; background: white;}}
.qav.grande {{box-shadow: 0 0 0 2px rgba(255,255,255,.85);}}
.qav .punto {{position: absolute; right: -1px; bottom: -1px; width: 12px; height: 12px; border-radius: 50%; background: #3DDC84;
  border: 2px solid #004039; animation: qpulso 2.4s ease-out infinite;}}
@keyframes qpulso {{0% {{box-shadow: 0 0 0 0 rgba(61,220,132,.6);}} 70% {{box-shadow: 0 0 0 8px rgba(61,220,132,0);}}
  100% {{box-shadow: 0 0 0 0 rgba(61,220,132,0);}}}}
.qtit b {{display: block; font-size: 1.08rem; line-height: 1.2; font-weight: 700;}}
.qtit small {{display: block; opacity: .85; font-size: .8rem; margin-top: 2px; line-height: 1.3;}}
.qurg {{display: flex; align-items: center; gap: .55rem; padding: .5rem 1.2rem; background: #FFF4EF; color: #8A3A16 !important;
  font-size: .85rem; text-decoration: none !important; border-bottom: 1px solid #F4C3B0;}}
.qurg .material-symbols-rounded {{font-size: 1.15rem;}}
.qurg .flecha {{margin-left: auto; background: #B4501F; color: white; border-radius: 50%; padding: 3px; font-size: 1rem;}}
.qurg:hover {{background: #FFE9DF;}}
/* ── Resumen de lo anotado ─────────────────────────────────────────────────────────────────────────────── */
.qresumen {{padding: .55rem 1.1rem .5rem; background: white; border-bottom: 1px solid {BORDE};}}
.qresumen small {{display: block; color: {comun.GRIS_TEXTO}; font-size: .7rem; text-transform: uppercase; letter-spacing: .06em;
  font-weight: 700; margin-bottom: .3rem;}}
.qresumen div {{display: flex; flex-wrap: wrap; gap: .35rem;}}
.qetq {{display: inline-flex; align-items: center; gap: .25rem; background: {MENTA}; color: {VERDE}; border-radius: 99px;
  padding: .12rem .6rem .12rem .4rem; font-size: .78rem; font-weight: 600;}}
.qetq .material-symbols-rounded {{font-size: .95rem;}}
.qetq.alerta {{background: #FFF1EA; color: #8A3A16;}}
/* ── Conversación ──────────────────────────────────────────────────────────────────────────────────────── */
.qconv {{padding: 1rem 1rem .6rem; display: flex; flex-direction: column; gap: .15rem;}}
.qdia {{align-self: center; font-size: .74rem; color: {comun.GRIS_TEXTO}; background: rgba(0,64,57,.07); border-radius: 99px;
  padding: .1rem .7rem; margin-bottom: .6rem;}}
.qfila {{display: flex; gap: .5rem; margin-bottom: .55rem; max-width: 92%;}}
.qfila.yo {{align-self: flex-end; justify-content: flex-end;}}
.qb {{padding: .62rem .9rem; font-size: .94rem; line-height: 1.5; border-radius: 18px; word-wrap: break-word; overflow-wrap: anywhere;}}
.qfila.ia .qb {{background: white; color: #1F2B2A; border: 1px solid #E1ECEB; border-bottom-left-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,64,57,.06);}}
.qfila.yo .qb {{background: {VERDE}; color: white; border-bottom-right-radius: 6px; box-shadow: 0 4px 12px rgba(0,64,57,.25);}}
.qhora {{font-size: .68rem; color: #7d8b8a; margin: 2px .35rem 0; }}
.qfila.yo .qhora {{text-align: right;}}
.qb a.q112 {{font-weight: 800; text-decoration: underline; text-underline-offset: 2px; color: #B4501F; border-radius: 6px; padding: 0 .1rem;}}
.qfila.yo .qb a.q112 {{color: white;}}
.qb a.q112:hover {{background: rgba(180,80,31,.12);}}
.qb.escribiendo {{display: inline-flex; gap: 5px; align-items: center; padding: .85rem 1rem;}}
.qb.escribiendo i {{width: 7px; height: 7px; border-radius: 50%; background: #8fb7b3; animation: qsalto 1.2s infinite ease-in-out;}}
.qb.escribiendo i:nth-child(2) {{animation-delay: .15s;}} .qb.escribiendo i:nth-child(3) {{animation-delay: .3s;}}
@keyframes qsalto {{0%, 60%, 100% {{transform: translateY(0); opacity: .5;}} 30% {{transform: translateY(-5px); opacity: 1;}}}}
@media (prefers-reduced-motion: reduce) {{.qb.escribiendo i, .qav .punto {{animation: none;}}}}
/* ── Vista del equipo: tarjeta junto al chat (solo en la demo) ───────────────────────────────────────────── */
.st-key-equipo-demo {{display: none;}}
@media (min-width: 1000px) {{
  section[role="dialog"]:has(.qchat) .st-key-equipo-demo {{display: block; position: fixed; right: calc(28px + 420px + 16px); bottom: 28px;
    width: 330px; max-height: calc(100dvh - 56px); overflow-y: auto; background: white; border-radius: 22px; padding: 1rem 1.1rem 1.1rem;
    box-shadow: 0 20px 60px rgba(0,40,36,.25), 0 0 0 1px rgba(0,64,57,.08); pointer-events: auto; z-index: 2;}}
}}
.qeq-cab {{display: flex; align-items: center; gap: .7rem; padding-bottom: .7rem; border-bottom: 1px solid {BORDE}; margin-bottom: .7rem;}}
.qeq-cab > .material-symbols-rounded {{flex: none; width: 40px; height: 40px; border-radius: 12px; background: {MENTA}; color: {VERDE};
  display: flex; align-items: center; justify-content: center; font-size: 1.4rem;}}
.qeq-cab b {{display: block; color: {VERDE}; font-size: 1.02rem;}}
.qeq-cab small {{color: {comun.GRIS_TEXTO}; font-size: .76rem;}}
.qeq-campos {{display: grid; grid-template-columns: 1fr 1fr; gap: .55rem .8rem;}}
.qeq-f small {{display: block; color: {comun.GRIS_TEXTO}; font-size: .68rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 700;}}
.qeq-f b {{color: #1F2B2A; font-size: .95rem; overflow-wrap: anywhere;}}
.qeq-f b.vacio {{color: #9aa7a6; font-weight: 500; font-style: italic;}}
.qeq-aviso {{border-radius: 12px; padding: .55rem .75rem; background: {MENTA}; color: {VERDE}; font-size: .84rem; margin-bottom: .55rem; line-height: 1.4;}}
.qeq-aviso b {{display: block; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em;}}
.qeq-aviso.alerta {{background: #FFF1EA; color: #8A3A16;}}
.qeq-pie {{color: {comun.GRIS_TEXTO}; font-size: .78rem; line-height: 1.45; margin: .8rem 0 .2rem !important;}}
.st-key-equipo-demo button {{border-radius: 10px !important; font-size: .84rem !important; margin-top: .4rem;}}
/* ── Respuestas rápidas, campo de texto y pie ──────────────────────────────────────────────────────────── */
[class*="st-key-qchips"] {{padding: .55rem 1rem .15rem; background: #F4F8F8; display: flex; flex-wrap: wrap; gap: .4rem;}}
.st-key-qchips-sigue {{display: none !important;}}
section[role="dialog"]:has(.qfila.yo) .st-key-qchips-inicio {{display: none !important;}}
section[role="dialog"]:has(.qfila.yo) .st-key-qchips-sigue {{display: flex !important;}}
[class*="st-key-qchips"] button {{border: 1.5px solid {VERDE} !important; color: {VERDE} !important; background: white !important;
  border-radius: 99px !important; padding: .28rem .85rem !important; min-height: 0 !important; font-size: .86rem !important;
  font-weight: 600; line-height: 1.3; transition: background .15s;}}
[class*="st-key-qchips"] button:hover {{background: {MENTA} !important;}}
[class*="st-key-qchips"] a {{border: 1.5px solid #B4501F; color: #8A3A16 !important; background: #FFF4EF; border-radius: 99px;
  padding: .28rem .85rem; font-size: .86rem; font-weight: 600; text-decoration: none;}}
section[role="dialog"]:has(.qchat) [data-testid="stChatInput"] {{border-radius: 28px !important; border: 1.5px solid {BORDE} !important;
  background: white !important; margin: .3rem .9rem .2rem; width: calc(100% - 1.8rem); box-shadow: 0 4px 14px rgba(0,64,57,.07);}}
section[role="dialog"]:has(.qchat) [data-testid="stChatInput"]:focus-within {{border-color: {VERDE} !important;}}
section[role="dialog"]:has(.qchat) [data-testid="stChatInputSubmitButton"] {{background: {VERDE} !important; color: white !important;
  border-radius: 50% !important;}}
section[role="dialog"]:has(.qchat) [data-testid="stElementContainer"]:has([data-testid="stChatInput"]) {{background: #F4F8F8; padding-bottom: .15rem;}}
.qaviso {{padding: .55rem 1.1rem; background: white; font-size: .76rem; color: {comun.GRIS_TEXTO}; line-height: 1.4; border-bottom: 1px solid {BORDE};}}
.qpie {{padding: .1rem 1.1rem .45rem; font-size: .68rem !important; background: #F4F8F8; color: {comun.GRIS_TEXTO}; font-size: .72rem; line-height: 1.4; text-align: center;}}
.qpie a {{color: {VERDE}; font-weight: 600;}}
section[role="dialog"]:has(.qchat) [data-testid="stExpander"] {{border: 0; border-top: 1px solid {BORDE}; border-radius: 0; background: white;}}
section[role="dialog"]:has(.qchat) [data-testid="stExpander"] summary {{padding: .45rem 1.1rem; font-size: .8rem; color: {comun.GRIS_TEXTO};}}
section[role="dialog"]:has(.qchat) [data-testid="stSelectbox"] {{padding: .6rem 1rem 0; background: #F4F8F8;}}
</style>
"""


def saludo(abierto: bool, cuando: str, ahora: datetime) -> str:
    if abierto:
        return "¿Buscas ayuda para cuidar a un familiar? Cuéntame qué necesitas y lo orientamos en un minuto."
    return (f"Son las {ahora:%H:%M} y ya no hay nadie al teléfono, pero yo sí estoy. Cuéntame qué necesitas y dejo la llamada "
            f"preparada {cuando}.")


def lanzador(texto_saludo: str) -> str:
    """Avatar con punto de «en línea» e insignia, y un bocadillo que aparece a los 2 s y se puede cerrar. El botón de Streamlit que
    abre el chat se superpone invisible a todo el conjunto: pulsar el avatar o el bocadillo abre el chat. La × queda por encima."""
    return f"""
<div class="ql">
  <input type="checkbox" id="ql-cerrar" class="ql-check" aria-hidden="true" tabindex="-1">
  <div class="ql-boca" role="note">
    <label for="ql-cerrar" class="ql-x" aria-label="Cerrar el saludo">×</label>
    <div class="ql-quien"><b>Asistente de Qida</b><span>IA</span></div>
    <p>{html.escape(texto_saludo)}</p>
    <span class="ql-cta">Escríbeme <span class="material-symbols-rounded">arrow_forward</span></span>
  </div>
  <div class="ql-av">{AVATAR}<i class="punto"></i><em class="ql-ins">1</em></div>
</div>"""


LANZADOR_CSS = f"""
<style>
.st-key-boton-chat {{position: fixed; right: 24px; bottom: 24px; z-index: 999; width: auto !important; max-width: calc(100vw - 32px);}}
.st-key-boton-chat [data-testid="stElementContainer"]:has(.ql) {{position: relative; z-index: 1;}}
/* El botón invisible se posiciona directamente sobre TODO el lanzador (el contenedor fijo), sin depender del ancho de sus envoltorios:
   así pulsar el avatar, el bocadillo o el «Escríbeme» abre el chat. */
.st-key-boton-chat [data-testid="stElementContainer"]:has([data-testid="stButton"]),
.st-key-boton-chat [data-testid="stButton"], .st-key-boton-chat [data-testid="stButton"] > div {{position: static !important; margin: 0 !important;
  width: 0 !important; height: 0 !important; min-height: 0 !important; overflow: visible;}}
.st-key-boton-chat button {{position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; z-index: 3; opacity: 0;
  cursor: pointer; border-radius: 28px; padding: 0 !important; min-height: 0 !important;}}
.ql {{display: flex; flex-direction: column; align-items: flex-end; gap: 12px; position: relative;}}
.ql-check {{position: absolute; opacity: 0; pointer-events: none;}}
.ql-boca {{position: relative; width: min(300px, calc(100vw - 48px)); background: white; border-radius: 20px 20px 6px 20px; padding: .95rem 1.1rem .85rem;
  box-shadow: 0 18px 50px rgba(0,40,36,.28), 0 0 0 1px rgba(0,64,57,.08); opacity: 0; pointer-events: none;
  animation: ql-entra .55s cubic-bezier(.2,.9,.3,1.2) 2.2s both;}}
.ql-boca::after {{content: ""; position: absolute; right: 24px; bottom: -8px; width: 16px; height: 16px; background: white; transform: rotate(45deg);
  border-radius: 0 0 4px 0; box-shadow: 4px 4px 8px rgba(0,40,36,.08);}}
@keyframes ql-entra {{from {{opacity: 0; transform: translateY(14px) scale(.96);}} to {{opacity: 1; transform: none;}}}}
.ql-check:checked ~ .ql-boca {{display: none;}}
.ql-quien {{display: flex; align-items: center; gap: .45rem; margin-bottom: .3rem;}}
.ql-quien b {{font-size: .86rem; color: {VERDE};}}
.ql-quien span {{background: {MENTA}; color: {VERDE}; border-radius: 99px; padding: 0 .45rem; font-size: .68rem; font-weight: 700;}}
.ql-boca p {{margin: 0 !important; color: #1F2B2A; font-size: .93rem; line-height: 1.5;}}
.ql-cta {{display: inline-flex; align-items: center; gap: .2rem; margin-top: .55rem; color: {VERDE}; font-weight: 700; font-size: .88rem;}}
.ql-cta .material-symbols-rounded {{font-size: 1.05rem;}}
.ql-x {{position: absolute; top: -10px; left: -10px; z-index: 6; width: 26px; height: 26px; border-radius: 50%; background: white; color: #5B6B6A;
  display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 1.1rem; line-height: 1; font-weight: 700;
  box-shadow: 0 4px 12px rgba(0,40,36,.25); pointer-events: auto;}}
.ql-x:hover {{background: {MENTA}; color: {VERDE};}}
.ql-av {{position: relative; width: 68px; height: 68px; border-radius: 50%; background: #DCEDEA; color: white; box-sizing: border-box;
  display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 30px rgba(0,64,57,.45); transition: transform .2s;}}
.st-key-boton-chat:hover .ql-av {{transform: scale(1.06);}}
.ql-av {{border: 3px solid white;}}
.ql-av .punto {{position: absolute; right: 2px; bottom: 2px; width: 14px; height: 14px; border-radius: 50%; background: #3DDC84; border: 2.5px solid white;}}
.ql-ins {{position: absolute; top: -4px; right: -4px; min-width: 22px; height: 22px; border-radius: 99px; background: #EA6D43; color: white;
  font-style: normal; font-weight: 700; font-size: .74rem; display: flex; align-items: center; justify-content: center; padding: 0 5px;
  border: 2px solid white; opacity: 0; animation: ql-ins-entra .4s ease-out 2.2s both;}}
@keyframes ql-ins-entra {{from {{opacity: 0; transform: scale(.4);}} to {{opacity: 1; transform: none;}}}}
.ql-check:checked ~ .ql-av .ql-ins {{display: none;}}
@media (prefers-reduced-motion: reduce) {{.ql-boca, .ql-ins {{animation-duration: .01s; animation-delay: 0s;}}}}
@media (max-width: 640px) {{.st-key-boton-chat {{right: 14px; bottom: 14px;}} .ql-av {{width: 58px; height: 58px;}}}}
</style>
"""
