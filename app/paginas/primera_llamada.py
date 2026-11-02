import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun
import graficos
from comun import es
from motor import scoring

ciudades = comun.selector_ciudades()


@st.cache_resource
def modelo():
    with comun.conexion() as con:
        df = scoring.cargar(con)
    return scoring.entrenar(df)


res = modelo()
test = res["test"][res["test"]["ciudad"].isin(ciudades)]
sql, espera = comun.ejecutar("3_tiempo_primera_llamada.sql", ciudades)
sql_vel, velocidad = comun.ejecutar("4_velocidad_respuesta.sql", ciudades)
gan = scoring.ganancia(test)
cubiertos_30 = gan.loc[gan["pct_llamadas"] == 30, "pct_contratos"].iloc[0]

comun.cabecera("Cola de llamadas", f"Llamando primero al 30 % mejor puntuado se cubre el {es(cubiertos_30, 0)} % de los contratos",
               "asesores/as familiares",
               "Cada mañana: a quién llamar primero y por qué. Urgentes primero; después, por probabilidad de contratar. "
               "Ordena, no descarta: todas las familias reciben su llamada.")

ultimo, previo = velocidad.iloc[-1], velocidad.iloc[-2]
fila = comun.Fila()
k1 = k2 = k3 = fila
comun.kpi(k1, "Llamadas en menos de 1 h", f"{es(ultimo['pct_menos_1h'], 0)} %",
          f"{comun.mes_es(ultimo['mes'])} · objetivo: 50 %", ultimo["pct_menos_1h"] - previo["pct_menos_1h"],
          alerta=ultimo["pct_menos_1h"] < 25, icono="phone_in_talk")
comun.kpi(k2, "Espera media hasta la primera llamada", es(ultimo["horas_media"], 1, " h"),
          "las familias de noche esperan a la mañana", ultimo["horas_media"] - previo["horas_media"],
          mejor_si_sube=False, unidad_tendencia=" h", icono="schedule")
comun.kpi(k3, "Contratos cubiertos con el 30 % mejor puntuado", f"{es(cubiertos_30, 0)} %",
          "frente al 30 % si se llama en orden de llegada", icono="target")
fila.pintar()

# ── La cola de hoy ──────────────────────────────────────────────────────────────────────────────────────────────
NOMBRES = ["Lucía", "Javier", "Carmen", "Antonio", "Marta", "Pablo", "Elena", "Jorge", "Rosa", "Miguel", "Ana", "David",
           "Pilar", "Sergio", "Laura", "Andrés", "Isabel", "Raúl", "Nuria", "Tomás", "Silvia", "Óscar", "Teresa"]
INICIALES = "ABCDFGHLMNPRSTV"
HOY = pd.Timestamp("2026-09-30 09:00")
cola = test[(test["fecha_entrada"] >= HOY - pd.Timedelta(hours=13)) & (test["fecha_entrada"] < HOY)].copy()
cola["familia"] = [f"{NOMBRES[i % len(NOMBRES)]} {INICIALES[(i // len(NOMBRES)) % len(INICIALES)]}." for i in cola["id"]]
cola["entró por"] = cola["canal"]

# Las familias que dejó anoche el asistente (si se ha probado la web) entran en la misma cola
try:
    with comun.conexion() as con:
        chat = pd.read_sql("SELECT fecha, ficha FROM leads_web WHERE canal = 'Chat'", con)
except Exception:
    chat = pd.DataFrame(columns=["fecha", "ficha"])
filas_chat = []
for _, f in chat.tail(3).iterrows():
    ficha = json.loads(f["ficha"])
    if ficha.get("ciudad") not in ciudades:
        continue
    filas_chat.append({"id": -len(filas_chat) - 1, "familia": ficha.get("nombre") or "Familia del chat",
                       "fecha_entrada": HOY - pd.Timedelta(hours=9, minutes=50), "canal": "Chat",
                       "entró por": "Asistente de noche", "ciudad": ficha["ciudad"],
                       "servicio": ficha.get("servicio") or "Por horas", "urgencia": int(bool(ficha.get("urgencia"))),
                       "menciona_dependencia": int(bool(ficha.get("menciona_dependencia"))), "fuera_horario": 1})
if filas_chat:
    extra = pd.DataFrame(filas_chat)
    extra["score"] = scoring.puntuar(res, extra)
    cola = pd.concat([cola, extra], ignore_index=True)

if cola.empty:
    comun.nota("No hay familias en la cola de esta mañana para las ciudades elegidas.", "neutra")
else:
    cola["por qué"] = [scoring.porque(res, f) for _, f in cola.iterrows()]
    cola["espera"] = ((HOY - cola["fecha_entrada"]).dt.total_seconds() / 3600).map(lambda h: es(h, 0, " h"))
    cola["entró"] = cola["fecha_entrada"].dt.strftime("%H:%M")
    cola["urgente"] = cola["urgencia"].map({1: "Sí", 0: ""})
    cola = cola.sort_values(["urgencia", "score"], ascending=[False, False])
    cola["llamada hecha"] = False
    st.markdown(f"#### La cola de esta mañana · {len(cola)} familias que pidieron ayuda desde las 20:00")
    st.data_editor(
        cola[["llamada hecha", "urgente", "familia", "ciudad", "servicio", "entró", "espera", "score", "por qué", "entró por"]],
        hide_index=True, width="stretch",
        disabled=["urgente", "familia", "ciudad", "servicio", "entró", "espera", "score", "por qué", "entró por"],
        column_config={
            "llamada hecha": st.column_config.CheckboxColumn("Hecha", width="small"),
            "urgente": st.column_config.TextColumn("Urgente", width="small"),
            "score": st.column_config.ProgressColumn("Probabilidad de contratar", format="percent", min_value=0,
                                                     max_value=float(max(test["score"].max(), 0.01))),
        },
    )
    st.caption("Nombres ficticios. Urgentes primero (alta hospitalaria o situación urgente); después, por probabilidad.")

# ── Por qué funciona ─────────────────────────────────────────────────────────────────────────────────────────────
izq, der = st.columns(2)
with izq:
    st.markdown("#### La puntuación acierta: curva de ganancia")
    fig = go.Figure()
    fig.add_scatter(x=gan["pct_llamadas"], y=gan["pct_contratos"], mode="lines+markers", name="Llamando por puntuación",
                    line=dict(color=graficos.ACENTO, width=3))
    fig.add_scatter(x=[0, 100], y=[0, 100], mode="lines", name="En orden de llegada",
                    line=dict(color=graficos.GRIS, dash="dash"))
    fig.add_annotation(x=30, y=cubiertos_30, text=f"<b>30 % → {es(cubiertos_30, 0)} %</b>", showarrow=True, arrowhead=0,
                       ax=-60, ay=-35, font=dict(color=comun.VERDE_TEXTO))
    graficos._limpio(fig, 340)
    fig.update_layout(xaxis=dict(title="% de familias llamadas, de más a menos prometedoras", ticksuffix=" %"),
                      yaxis=dict(title="% de los contratos que se cubren", ticksuffix=" %", showgrid=False),
                      legend=dict(orientation="h", y=1.12))
    comun.grafico(fig)
    st.caption("Comprobado con agosto y septiembre de 2026, meses que el modelo no vio. Contrato = en 30 días.")
with der:
    st.markdown("#### Cuanto más esperan, menos contratan")
    comun.grafico(graficos.columnas(espera, "espera", "pct_contrata", "tiempo hasta la primera llamada",
                                      "% que contrata", resaltar="1. < 1 h"))
    st.caption("Es una asociación: las familias de noche también son distintas. Que llamar antes cause más contratos se "
               "prueba con un A/B (asistente sí/no).")

sim = scoring.simular_cola_manana(test) if len(test) else {"mejora_pct": 0}
comun.nota(f"**Ilustración, no resultado:** con los supuestos de la demo, solo reordenar la cola cambia los contratos un "
           f"{es(sim['mejora_pct'], 1, ' %')}. La palanca grande es **llamar antes**; por eso el asistente de noche va primero.",
           "neutra")

with st.expander("Detalle técnico: calibración, pesos, datos y consultas"):
    st.markdown(f"Regresión logística (explicable para el equipo). Área bajo la curva (AUC) en validación: "
                f"**{es(res['auc'], 2)}**.")
    st.markdown("**Calibración:** cuando el modelo dice X %, ¿contrata de verdad ~X %?")
    st.dataframe(scoring.calibracion(test).rename(columns={"predicho": "% predicho", "real": "% real", "n": "familias"}),
                 hide_index=True)
    st.bar_chart(res["pesos"])
    st.dataframe(velocidad, hide_index=True)
    st.code(sql, language="sql")
    st.code(sql_vel, language="sql")
st.caption(comun.AVISO)
