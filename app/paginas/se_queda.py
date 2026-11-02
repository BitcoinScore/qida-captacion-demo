import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun
import detalles
import graficos
from comun import es
from motor import metricas

ciudades = comun.selector_ciudades()
with comun.conexion() as con:
    d = metricas.duraciones(con, ciudades)
km = metricas.kaplan_meier(d)
tri = metricas.triangulo(d).drop(columns=0).dropna(how="all")  # el mes 0 siempre es 100 %
s = km.set_index("mes")["pct_siguen"]

comun.cabecera("Retención", f"{es(s.get(12, s.iloc[-1]), 0)} de cada 100 familias siguen con Qida al año",
               "marketing y Referentes Sociales",
               f"La mayoría de las bajas llega en los tres primeros meses ({es(100 - s.get(3, 100), 0)} de cada 100). "
               "Captar rápido no puede ser captar peor.")

izq, der = st.columns(2)
with izq:
    comun.titulo("Cuánto tiempo siguen (Kaplan-Meier)")
    fig = go.Figure(go.Scatter(x=km["mes"], y=km["pct_siguen"], mode="lines+markers", line_shape="hv",
                               line=dict(color=graficos.ACENTO, width=3), marker=dict(size=6),
                               hovertemplate="Mes %{x}: siguen el %{y:.1f} %<extra></extra>"))
    for mes, texto in ((3, "3 meses"), (12, "1 año")):
        if mes in s.index:
            fig.add_annotation(x=mes, y=s[mes], text=f"<b>{texto}: {es(s[mes])} %</b>", showarrow=True, arrowhead=0,
                               arrowcolor=comun.VERDE_TEXTO, ax=55, ay=-45, bgcolor="white", borderpad=3,
                               font=dict(color=comun.VERDE_TEXTO, size=14))
    graficos._limpio(fig, 360)
    fig.update_layout(xaxis_title="meses desde que contratan",
                      yaxis=dict(title="% que sigue", range=[0, 105], showgrid=False, ticksuffix=" %"))
    comun.grafico(fig)
    st.caption("Kaplan-Meier usa a todas las familias, también las que llevan poco tiempo, sin sesgar la curva.")

with der:
    comun.titulo("Siguen a los 3 meses, según por dónde llegaron")
    filas = []
    for canal, g in d.groupby("canal"):
        s3 = metricas.kaplan_meier(g, hasta=3).set_index("mes")["pct_siguen"].get(3)
        n = int((g["meses"] >= 3).sum() + ((g["meses"] < 3) & (g["baja"] == 1)).sum())
        if s3 is None or n < 30:
            continue
        lo, hi = metricas.wilson(round(n * s3 / 100), n)
        filas.append({"canal": canal, "pct": s3, "ic_bajo": lo, "ic_alto": hi, "familias": n})
    if filas:
        comun.grafico(graficos.puntos_ic(pd.DataFrame(filas), "% que sigue a los 3 meses", alto=360, rango=(50, 140)))
    else:
        comun.nota("Con las ciudades elegidas aún no hay suficientes familias con tres meses de antigüedad.", "neutra")

comun.titulo("Cada mes de contrato, qué parte sigue (triángulo de cohortes)")
etiquetas_y = [comun.mes_es(c) for c in tri.index]
fig = go.Figure(go.Heatmap(
    z=tri.values, x=[f"mes {c}" for c in tri.columns], y=etiquetas_y,
    colorscale=[[0, "#fbe3d9"], [0.5, "#CCE0DF"], [1, graficos.ACENTO]], zmin=40, zmax=100,
    text=tri.map(lambda v: "" if pd.isna(v) else es(v, 0)).values, texttemplate="%{text}",
    hovertemplate="Contrataron en %{y} · %{x}: siguen el %{z:.0f} %<extra></extra>", colorbar=dict(title="%", thickness=10),
))
graficos._limpio(fig, 460)
fig.update_layout(yaxis=dict(autorange="reversed", type="category"))
comun.grafico(fig)
st.caption("Cada fila es un mes de contrato; cada columna, los meses que han pasado. Si una cohorte reciente empeora, "
           "se ve aquí antes que en la media.")

comun.titulo("Explorar una cohorte o un canal")
e1, e2, e3, e4 = st.columns([2, 1, 2, 1], vertical_alignment="bottom")
cohorte_sel = e1.selectbox("Cohorte (mes de contrato)", list(tri.index[::-1]), format_func=comun.mes_es, key="cohorte-sel")
if e2.button("Ver cohorte", icon=":material/open_in_new:", width="stretch"):
    detalles.ficha_cohorte(cohorte_sel, d, tri)
canal_sel = e3.selectbox("Canal de llegada", sorted(d["canal"].unique()), key="canal-ret-sel")
if e4.button("Ver canal", icon=":material/open_in_new:", width="stretch"):
    detalles.ficha_retencion_canal(canal_sel, d)

comun.titulo("Qué haría")
comun.notas([
    "**Alerta de baja:** una valoración baja de la familia avisa a su Referente Social antes de que se vaya.",
    "**Recomendaciones:** pedirlas a las familias contentas; es el canal que más rinde.",
    "**Coste real:** el valor de cada canal sale de esta curva y entra en su retorno, en Canales y ciudades.",
])

with st.expander("Datos"):
    st.dataframe(km, hide_index=True, width="stretch")
    st.dataframe(tri, width="stretch")
    comun.descarga(km, "permanencia-kaplan-meier", "Descargar la curva (CSV)")
    comun.descarga(tri.rename_axis("cohorte").reset_index(), "triangulo-de-cohortes", "Descargar el triángulo de cohortes (CSV)")
st.caption(comun.AVISO)
