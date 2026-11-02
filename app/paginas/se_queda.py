import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import comun
import graficos
from motor import metricas

comun.cabecera("", "Retención", "Marketing y Referentes Sociales",
               "Cuánto tiempo se quedan las familias captadas, por cohorte y según por dónde llegaron.")
st.success("**Captar rápido no puede ser captar peor.** Una familia contenta se queda y trae a otras.")
ciudades = comun.selector_ciudades()

with comun.conexion() as con:
    d = metricas.duraciones(con, ciudades)
km = metricas.kaplan_meier(d)
tri = metricas.triangulo(d).drop(columns=0).dropna(how="all")  # el mes 0 siempre es 100 %

izq, der = st.columns(2)
with izq:
    st.markdown("#### ¿Cuánto tiempo se quedan? (Kaplan-Meier)")
    fig = px.line(km, x="mes", y="pct_siguen", markers=True, line_shape="hv")
    fig.update_traces(line_color=graficos.ACENTO)
    for mes, texto in ((3, "3 meses"), (12, "1 año")):
        if mes in set(km["mes"]):
            v = km.loc[km["mes"] == mes, "pct_siguen"].iloc[0]
            fig.add_annotation(x=mes, y=v, text=f"<b>{texto}: {v:g} %</b>", showarrow=True, arrowhead=0, ay=-40,
                               font=dict(color=graficos.AVISO, size=14))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="meses desde que contratan",
                      yaxis=dict(title="% que sigue", range=[0, 105], showgrid=False),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Kaplan-Meier usa a todas las familias, también las que llevan poco tiempo, sin sesgar la curva.")

with der:
    st.markdown("#### ¿Siguen a los 3 meses, según por dónde llegaron?")
    filas = []
    for canal, g in d.groupby("canal"):
        s3 = metricas.kaplan_meier(g, hasta=3).set_index("mes")["pct_siguen"].get(3)
        n = int((g["meses"] >= 3).sum() + ((g["meses"] < 3) & (g["baja"] == 1)).sum())
        if s3 is None or n < 30:
            continue
        lo, hi = metricas.wilson(round(n * s3 / 100), n)
        filas.append({"canal": canal, "pct": s3, "ic_bajo": lo, "ic_alto": hi, "familias": n})
    st.plotly_chart(graficos.barras_ic(pd.DataFrame(filas), "% que sigue a los 3 meses", alto=360), use_container_width=True)

st.markdown("#### Triángulo de cohortes: % de cada mes de alta que sigue activo")
fig = go.Figure(go.Heatmap(
    z=tri.values, x=[f"mes {c}" for c in tri.columns], y=tri.index, colorscale=[[0, "#fbe3d9"], [0.5, "#CCE0DF"], [1, graficos.ACENTO]],
    zmin=40, zmax=100, text=tri.map(lambda v: "" if pd.isna(v) else f"{v:.0f}").values, texttemplate="%{text}",
    hovertemplate="Cohorte %{y} · %{x}: %{z:.0f} %<extra></extra>", colorbar=dict(title="%", thickness=10),
))
fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)
st.caption("Cada fila es un mes de alta; cada columna, los meses que han pasado. Si una cohorte reciente empeora, se ve aquí antes que en la media.")

st.markdown("#### Qué haría")
a, b, c = st.columns(3)
a.info("**Alerta:** una nota baja avisa a la Referente Social antes de la baja.")
b.info("**Canal:** pedir la recomendación a las familias contentas.")
c.info("**Coste real:** el LTV de cada canal sale de esta curva; entra en el LTV:CAC de Canales.")

with st.expander("Datos"):
    st.dataframe(km, hide_index=True, use_container_width=True)
    st.dataframe(tri, use_container_width=True)
st.caption(comun.AVISO)
