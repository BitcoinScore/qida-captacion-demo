import plotly.graph_objects as go
import streamlit as st

import comun
import graficos
from motor import scoring

comun.cabecera("", "Cola de llamadas", "Asesores comerciales",
               "A quién llamar primero cada mañana, y por qué. Ordena, no descarta.")
ciudades = comun.selector_ciudades()


@st.cache_resource
def modelo():
    with comun.conexion() as con:
        df = scoring.cargar(con)
    return scoring.entrenar(df)


res = modelo()
test = res["test"]
sql, espera = comun.ejecutar("3_tiempo_primera_llamada.sql", ciudades)
sql_vel, velocidad = comun.ejecutar("4_velocidad_respuesta.sql", ciudades)
gan = scoring.ganancia(test)
cal = scoring.calibracion(test)

ultimo = velocidad.iloc[-1]
k1, k2, k3 = st.columns(3)
k1.metric("Llamadas en menos de 1 hora (sep-2026)", f"{ultimo['pct_menos_1h']:.0f} %",
          f"{ultimo['pct_menos_1h'] - velocidad.iloc[-2]['pct_menos_1h']:+.1f} pts vs mes anterior")
k2.metric("Espera media hasta la primera llamada", f"{ultimo['horas_media']:.1f} h")
k3.metric("Contratos cubiertos llamando primero al 30 % mejor puntuado",
          f"{gan.loc[gan['pct_llamadas'] == 30, 'pct_contratos'].iloc[0]:.0f} %", "frente a 30 % al azar", delta_color="off")

izq, der = st.columns(2)
with izq:
    st.markdown("#### Cuanto más esperan, menos contratan")
    st.plotly_chart(graficos.columnas(espera, "espera", "pct_contrata", "tiempo hasta la primera llamada", "% que contrata"),
                    use_container_width=True)
    st.caption("Es una asociación: las familias de noche también son distintas. Que llamar antes *cause* más contratos "
               "se prueba con un A/B (asistente sí / asistente no).")
with der:
    st.markdown("#### ¿Sirve la puntuación? Curva de ganancia")
    fig = go.Figure()
    fig.add_scatter(x=gan["pct_llamadas"], y=gan["pct_contratos"], mode="lines+markers", name="Por puntuación",
                    line=dict(color=graficos.ACENTO, width=3))
    fig.add_scatter(x=[0, 100], y=[0, 100], mode="lines", name="Al azar", line=dict(color=graficos.GRIS, dash="dash"))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="% de familias llamadas (de más a menos prometedoras)",
                      yaxis_title="% de los contratos que se cubren", legend=dict(orientation="h", y=1.12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Validado con agosto-septiembre de 2026, meses que el modelo no vio. Etiqueta: contrata en ≤30 días.")

st.markdown("#### La cola de esta mañana")
muestra = test.sort_values("fecha_entrada").tail(8).copy()
muestra["probabilidad"] = muestra["score"]
muestra["por qué"] = [scoring.porque(res, f) for _, f in muestra.iterrows()]
st.dataframe(
    muestra.sort_values("score", ascending=False)[["probabilidad", "por qué", "canal", "ciudad", "servicio"]],
    hide_index=True, use_container_width=True,
    column_config={"probabilidad": st.column_config.ProgressColumn("probabilidad de contratar", format="percent",
                                                                   min_value=0, max_value=float(test["score"].max()))},
)
st.caption("Ordena, no descarta: todas las familias reciben su llamada.")

sim = scoring.simular_cola_manana(test)
st.info(f"Ilustración (no es un resultado): con los supuestos de la demo, reordenar la cola de la mañana cambia los contratos "
        f"un **{sim['mejora_pct']:+.1f} %**. La palanca grande es **llamar antes** → el asistente va primero, y se mide con un A/B.")

with st.expander("Detalle técnico: calibración, pesos, datos y SQL"):
    st.markdown(f"Regresión logística (explicable). AUC en validación: **{res['auc']:.2f}**.")
    st.markdown("**Calibración:** ¿cuando el modelo dice X %, contratan de verdad X %?")
    st.dataframe(cal.rename(columns={"predicho": "% predicho", "real": "% real", "n": "familias"}), hide_index=True)
    st.bar_chart(res["pesos"])
    st.dataframe(velocidad, hide_index=True)
    st.code(sql, language="sql")
    st.code(sql_vel, language="sql")
st.caption(comun.AVISO)
