import sqlite3
import sys
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

ESTILO = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display&display=swap');
html, body, p, li, label, td, th, input, textarea, button, .stMarkdown {{font-family: 'DM Sans', Arial, sans-serif;}}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded' !important;}}
h1, h2, h3 {{font-family: 'DM Serif Display', Georgia, serif !important; color: {VERDE}; font-weight: 400 !important;
  letter-spacing: -.01em;}}
h4 {{color: {VERDE}; font-weight: 700 !important;}}
[data-testid="stSidebar"] {{background: {FONDO}; border-right: 1px solid {BORDE};}}
.kpi {{background: white; border: 1px solid {BORDE}; border-radius: 14px; padding: 14px 16px; height: 100%;}}
.kpi .etiqueta {{font-size: .82rem; color: #5b6b6a; text-transform: uppercase; letter-spacing: .04em;}}
.kpi .valor {{font-size: 2rem; font-weight: 700; color: {VERDE}; line-height: 1.15; margin: 4px 0;}}
.kpi .sub {{font-size: .82rem; color: #5b6b6a;}}
.kpi .bien {{color: {VERDE_MEDIO}; font-weight: 700;}}
.kpi .mal {{color: {NARANJA}; font-weight: 700;}}
.chip {{display: inline-block; background: {FONDO}; border: 1px solid {BORDE}; color: {VERDE}; border-radius: 99px;
  padding: 2px 10px; font-size: .8rem; font-weight: 500;}}
.chip.demo {{background: #fff4ef; border-color: #f4c3b0; color: #a8441f;}}
.seccion {{font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; color: {VERDE_MEDIO}; font-weight: 700;
  margin: 18px 0 4px;}}
</style>
"""


def estilo() -> None:
    """Tipografía, colores y componentes comunes. Se llama una vez desde Inicio.py."""
    st.markdown(ESTILO, unsafe_allow_html=True)
    if LOGO.exists():
        st.logo(str(LOGO), size="large")


def kpi(col, etiqueta: str, valor: str, sub: str = "", tendencia: float | None = None, mejor_si_sube: bool = True,
        unidad_tendencia: str = " pts") -> None:
    """Tarjeta de KPI: etiqueta, valor grande, variación coloreada (verde si mejora, naranja si empeora) y contexto."""
    flecha = ""
    if tendencia is not None and abs(tendencia) >= 0.05:
        mejora = (tendencia > 0) == mejor_si_sube
        flecha = (f"<span class='{'bien' if mejora else 'mal'}'>{'▲' if tendencia > 0 else '▼'} "
                  f"{abs(tendencia):.1f}{unidad_tendencia}</span> vs mes anterior · ").replace(".", ",")
    col.markdown(f"<div class='kpi'><div class='etiqueta'>{etiqueta}</div><div class='valor'>{valor}</div>"
                 f"<div class='sub'>{flecha}{sub}</div></div>", unsafe_allow_html=True)


def conexion() -> sqlite3.Connection:
    return sqlite3.connect(DB, check_same_thread=False)


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


def cabecera(icono: str, titulo: str, quien: str, para_que: str) -> None:
    """Título de cada pantalla con quién la usa y para qué. `icono` se mantiene por compatibilidad, no se pinta."""
    st.markdown(f"<div class='seccion'>Panel de captación · {quien}</div>", unsafe_allow_html=True)
    st.title(titulo)
    st.markdown(
        f"<div style='display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin:-.5rem 0 1.2rem'>"
        f"<span style='color:#5b6b6a'>{para_que}</span>"
        f"<span class='chip demo'>Concepto · datos inventados</span></div>",
        unsafe_allow_html=True,
    )


def selector_ciudades() -> list[str]:
    return st.sidebar.multiselect("Ciudades", CIUDADES, default=CIUDADES) or CIUDADES
