import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

DB = RAIZ / "datos" / "crm.db"
SQL = RAIZ / "sql"
CIUDADES = ["Barcelona", "Madrid", "Valencia", "Sevilla", "A Coruña"]

AVISO = "Datos **inventados** para la demo, con la forma de un CRM tipo Odoo. No son datos de Qida."
LOGO = Path(__file__).resolve().parent / "assets" / "qida_logo.png"

# Identidad de Qida (qida.es, 02-11-2026)
VERDE, VERDE_MEDIO, VERDE_CLARO, FONDO, BORDE, NARANJA, TEXTO = (
    "#004039", "#338581", "#99C2C0", "#EFF5F5", "#CCE0DF", "#ea6d43", "#333333")
# Tonos para TEXTO que cumplen WCAG AA (≥4,5:1 sobre blanco); los de marca se quedan para barras, bordes y fondos.
VERDE_TEXTO, NARANJA_TEXTO, GRIS_TEXTO = "#2B6E69", "#B4501F", "#5B6B6A"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]

ESTILO = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display&display=swap');
html, body, p, li, label, td, th, input, textarea, button, .stMarkdown {{font-family: 'DM Sans', Arial, sans-serif;}}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded' !important;}}
h1, h2, h3 {{font-family: 'DM Serif Display', Georgia, serif !important; color: {VERDE}; font-weight: 400 !important;
  letter-spacing: -.01em;}}
h4 {{color: {VERDE}; font-weight: 700 !important;}}
/* Aire antes de cada subtítulo, en todas las pantallas (salvo si abre la columna o la página) */
[data-testid="stMarkdownContainer"] h4 {{margin-top: 1.8rem !important; padding-top: 0 !important;}}
[data-testid="stMarkdownContainer"] h3 {{margin-top: 2rem !important;}}
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="stMarkdownContainer"] h4,
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="stMarkdownContainer"] h3
  {{margin-top: 0 !important;}}
[data-testid="stSidebar"] {{background: {FONDO}; border-right: 1px solid {BORDE};}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{color: {GRIS_TEXTO} !important;}}
.kpi {{background: white; border: 1px solid {BORDE}; border-radius: 14px; padding: 14px 16px; height: 100%;
  box-sizing: border-box; display: flex; flex-direction: column;}}
.fila-kpi {{display: grid; gap: 12px; align-items: stretch; margin-bottom: 4px;}}
@media (max-width: 900px) {{.fila-kpi {{grid-template-columns: repeat(2, 1fr) !important;}}}}
.kpi .etiqueta {{min-height: var(--alto-etiqueta, auto); line-height: 1.4; font-size: .82rem; color: {GRIS_TEXTO}; text-transform: uppercase; letter-spacing: .04em;}}
.kpi .valor {{font-size: var(--tam-valor, 2.2rem); font-weight: 700; color: {VERDE}; line-height: 1.1; margin: 6px 0 4px;
  letter-spacing: -.01em;}}
.kpi .sub {{font-size: .82rem; color: {GRIS_TEXTO};}}
.kpi .valor small {{font-size: .4em; font-weight: 600; color: {GRIS_TEXTO}; letter-spacing: 0; margin-left: .25em;}}
.kpi.alerta {{border-color: {NARANJA}; border-width: 2px;}}
.kpi.alerta .valor {{color: {NARANJA_TEXTO};}}
.kpi .bien {{color: {VERDE_TEXTO}; font-weight: 700;}}
.kpi .mal {{color: {NARANJA_TEXTO}; font-weight: 700;}}
.chip {{display: inline-block; background: {FONDO}; border: 1px solid {BORDE}; color: {VERDE}; border-radius: 99px;
  padding: 2px 10px; font-size: .8rem; font-weight: 500;}}
.chip.demo {{background: #fff4ef; border-color: #f4c3b0; color: #a8441f;}}
.chip.real {{background: #e6f2f1; border-color: {VERDE_MEDIO}; color: {VERDE};}}
.nota {{border-radius: 12px; padding: 12px 16px; margin: 6px 0 14px; border: 1px solid {BORDE}; background: {FONDO};
  color: {TEXTO}; line-height: 1.5;}}
.nota.clave {{border-left: 5px solid {VERDE}; background: {FONDO};}}
.nota.alerta {{border-left: 5px solid {NARANJA}; background: #fff7f3; border-color: #f4c3b0;}}
.nota.neutra {{background: white;}}
[data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessageAvatarUser"] {{background: {VERDE} !important;
  color: white !important;}}
[data-testid="stChatMessageAvatarUser"] {{background: {VERDE_CLARO} !important; color: {VERDE} !important;}}
.seccion {{font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; color: {VERDE_TEXTO}; font-weight: 700;
  margin: 18px 0 4px;}}
</style>
"""


def estilo() -> None:
    """Tipografía, colores y componentes comunes. Se llama una vez desde Inicio.py."""
    st.markdown(ESTILO, unsafe_allow_html=True)
    if LOGO.exists():
        st.logo(str(LOGO), size="large")


def es(v: float, dec: int = 1, suf: str = "") -> str:
    """Número en formato español: punto de miles, coma decimal («13,2 %», «1.906», «7,3×»)."""
    if v is None or v != v or v in (float("inf"), float("-inf")):
        return "—"
    texto = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return texto + suf


def mes_es(ym: str) -> str:
    """«2026-09» → «septiembre de 2026»."""
    a, m = ym[:7].split("-")
    return f"{MESES[int(m) - 1]} de {a}"


def nota(texto: str, tipo: str = "clave") -> None:
    """Caja de mensaje con la marca (sustituye a st.success/st.info/st.warning). tipo: clave · alerta · neutra."""
    import re as _re
    html = _re.sub(r"\*\*(.+?)\*\*", r"<b>\g<1></b>", texto)
    st.markdown(f"<div class='nota {tipo}'>{html}</div>", unsafe_allow_html=True)


def kpi(col, etiqueta: str, valor: str, sub: str = "", tendencia: float | None = None, mejor_si_sube: bool = True,
        unidad_tendencia: str = " p. p.", alerta: bool = False) -> None:
    """Tarjeta de KPI: etiqueta, valor grande, variación frente al mes anterior y contexto.

    La variación se colorea según mejore o empeore; `alerta=True` marca la tarjeta entera cuando el valor está lejos del
    objetivo (así una mejora pequeña de un dato malo no se lee como buena noticia).
    """
    flecha = ""
    if tendencia is not None and abs(tendencia) >= 0.05:
        mejora = (tendencia > 0) == mejor_si_sube
        flecha = (f"<span class='{'bien' if mejora else 'mal'}'>{'▲' if tendencia > 0 else '▼'} "
                  f"{es(abs(tendencia))}{unidad_tendencia}</span> frente al mes anterior · ")
    col.markdown(f"<div class='kpi{' alerta' if alerta else ''}'><div class='etiqueta'>{etiqueta}</div>"
                 f"<div class='valor'>{valor}</div><div class='sub'>{flecha}{sub}</div></div>", unsafe_allow_html=True)


def _asegurar_base() -> None:
    """Si falta la base inventada (o quedó vacía), se genera: nunca una traza por un fichero que no existe."""
    if not DB.exists() or DB.stat().st_size == 0:
        DB.unlink(missing_ok=True)
        from datos import generar
        generar.generar(DB)


@contextmanager
def conexion():
    """Conexión de solo uso: se cierra siempre (en Windows, una conexión abierta bloquea el fichero)."""
    _asegurar_base()
    con = sqlite3.connect(DB, check_same_thread=False)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def leer_sql(nombre: str) -> str:
    return (SQL / nombre).read_text(encoding="utf-8")


def ejecutar(nombre: str, ciudades: list[str]) -> tuple[str, pd.DataFrame]:
    texto = leer_sql(nombre)
    marcadores = ",".join("?" * len(ciudades))
    consulta = texto.replace("{ciudades}", marcadores)
    n = texto.count("{ciudades}")
    with conexion() as con:
        df = pd.read_sql(consulta, con, params=ciudades * n)
    return texto, df


def cabecera(pantalla: str, conclusion: str, quien: str, para_que: str, chip: str = "Concepto · datos inventados",
             real: bool = False) -> None:
    """Cabecera de cada pantalla: nombre y destinatario en pequeño, la CONCLUSIÓN como título, y el contexto."""
    st.markdown(f"<div class='seccion'>{pantalla} · para {quien}</div>", unsafe_allow_html=True)
    st.title(conclusion)
    st.markdown(
        f"<div style='display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin:-.5rem 0 1.2rem'>"
        f"<span style='color:{GRIS_TEXTO}'>{para_que}</span>"
        f"<span class='chip {'real' if real else 'demo'}'>{chip}</span></div>",
        unsafe_allow_html=True,
    )


def selector_ciudades() -> list[str]:
    """Filtro de ciudades en la barra lateral. Se recuerda al cambiar de pantalla; vacío = aviso, no «todas» a escondidas."""
    if "_ciudades" not in st.session_state:
        st.session_state["_ciudades"] = list(CIUDADES)

    def guardar():
        st.session_state["_ciudades"] = st.session_state["_selector_ciudades"]

    elegidas = st.sidebar.multiselect("Ciudades", CIUDADES, default=st.session_state["_ciudades"],
                                      key="_selector_ciudades", on_change=guardar)
    if not elegidas:
        nota("Elige al menos una ciudad en la barra lateral.", "alerta")
        st.stop()
    return elegidas


def grafico(fig) -> None:
    """Pinta un gráfico Plotly a todo el ancho y sin la barra de herramientas (zoom, cámara…), que distrae."""
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})


class Fila:
    """Fila de tarjetas KPI que miden lo mismo: se pinta como una sola rejilla HTML (las columnas de Streamlit no se
    estiran entre sí). Uso: `fila = comun.Fila(); comun.kpi(fila, ...); ...; fila.pintar()`."""

    def __init__(self):
        self.tarjetas: list[str] = []

    def markdown(self, html: str, unsafe_allow_html: bool = True) -> None:  # lo llama kpi()
        self.tarjetas.append(html)

    def pintar(self) -> None:
        n = len(self.tarjetas)
        # Cuantas menos tarjetas, más grande la cifra (si no, la caja se queda vacía)
        tam = {1: "3.4rem", 2: "3.2rem", 3: "3rem", 4: "2.7rem", 5: "2.4rem"}.get(n, "2.2rem")
        # La etiqueta reserva dos líneas solo si alguna de la fila no cabe en una
        etiquetas = [re.sub(r"<[^>]+>", "", e) for t in self.tarjetas for e in re.findall(r"class='etiqueta'>(.*?)</div>", t)]
        cabe = 110 / n  # caracteres aproximados por línea a este ancho
        alto = "2.8em" if any(len(e) > cabe for e in etiquetas) else "auto"
        st.markdown(f"<div class='fila-kpi' style='grid-template-columns:repeat({n}, 1fr);--tam-valor:{tam};"
                    f"--alto-etiqueta:{alto}'>" + "".join(self.tarjetas) + "</div>", unsafe_allow_html=True)

