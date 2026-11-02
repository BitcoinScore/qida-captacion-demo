import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import cohen_kappa_score

import comun
import graficos
from motor import metricas

comun.cabecera("", "Calidad del asistente", "Equipo de IA",
               "Cómo sé que el chat de noche responde bien antes de ponerlo delante de una familia.")
st.success("**Conversaciones difíciles → reglas automáticas → otra IA de examinador → yo compruebo al examinador.**")

EVAL = comun.RAIZ / "eval"
ETIQUETAS = EVAL / "etiquetas_humanas.json"


def cargar(nombre: str) -> pd.DataFrame:
    ruta = EVAL / nombre
    if not ruta.exists():
        return pd.DataFrame()
    return pd.DataFrame([{
        "id": r["id"], "categoria": r["categoria"], "checks_ok": r["checks_ok"],
        "aprueba": r["checks_ok"] and r["juez"].get("veredicto") == "aprueba",
        "motivo": r["juez"].get("motivo", ""), "fallos": ", ".join(k for k, v in r["checks"].items() if not v), "r": r,
    } for r in json.loads(ruta.read_text(encoding="utf-8"))])


VERSIONES = ["v1 · juez v1", "v1 · juez v2", "v2", "v3"]
CONJUNTOS = [  # (nombre, color, {versión: fichero})
    ("Casos de ajuste (60)", graficos.PERDIDA, {"v1 · juez v1": "resultados_v1.json", "v1 · juez v2": "resultados_v1_juez2.json",
                                         "v2": "resultados_v2.json", "v3": "resultados_v3.json"}),
    ("Reservados 1 (20)", graficos.NEUTRO, {"v2": "resultados_v2_reserva.json", "v3": "resultados_v3_reserva.json"}),
    ("Reservados 2 (25) · la nota que vale", graficos.ACENTO, {"v3": "resultados_v3_reserva2.json"}),
]
datos = {(c, v): cargar(f) for c, _, ficheros in CONJUNTOS for v, f in ficheros.items()}
if all(d.empty for d in datos.values()):
    st.warning("Todavía no hay resultados. Ejecuta `python eval/ejecutar.py`.")
    st.stop()


def nota(d: pd.DataFrame) -> tuple[float, float, float, int]:
    k, n = int(d["aprueba"].sum()), len(d)
    lo, hi = metricas.wilson(k, n)
    return 100 * k / n, lo, hi, n


vale = datos[(CONJUNTOS[2][0], "v3")]
c1, c2, c3 = st.columns(3)
if not vale.empty:
    p, lo, hi, n = nota(vale)
    c1.metric("Nota que vale: v3 con casos nunca vistos", f"{p:.0f} %", f"margen {lo:.0f}–{hi:.0f} % · n={n}",
              delta_color="off")
for col, clave, titulo in ((c2, (CONJUNTOS[1][0], "v2"), "v2 con casos nunca vistos"),
                           (c3, (CONJUNTOS[0][0], "v3"), "v3 con los casos de ajuste")):
    if not datos[clave].empty:
        p, lo, hi, n = nota(datos[clave])
        col.metric(titulo, f"{p:.0f} %", f"margen {lo:.0f}–{hi:.0f} % · n={n}", delta_color="off")

st.markdown("#### % de conversaciones aprobadas (reglas + examinador), con margen de error del 95 %")
fig = go.Figure()
for conjunto, color, ficheros in CONJUNTOS:
    xs, ys, sup, inf, textos = [], [], [], [], []
    for v in VERSIONES:
        d = datos.get((conjunto, v))
        if d is None or d.empty:
            continue
        p, lo, hi, n = nota(d)
        xs.append(v); ys.append(p); sup.append(hi - p); inf.append(p - lo); textos.append(f"{p:.0f} %")
    if xs:
        fig.add_bar(x=xs, y=ys, name=conjunto, marker_color=color, text=textos, textposition="outside",
                    error_y=dict(type="data", symmetric=False, array=sup, arrayminus=inf, color="#6b7b7a", thickness=1.2, width=4))
fig.update_layout(barmode="group", height=400, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.13),
                  xaxis=dict(categoryorder="array", categoryarray=VERSIONES, title="versión del asistente · del juez"),
                  yaxis=dict(title="% aprobadas", range=[0, 118], showgrid=False),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)
st.caption("**v1 → v1 · juez v2:** mismas respuestas, juez corregido (efecto del juez). **v2:** asistente corregido. "
           "**v3:** regla de fidelidad, tras ver que la v2 inventaba políticas en los reservados 1. Los reservados 1 ya "
           "se vieron, así que para la v3 solo vale el conjunto 2, escrito antes de evaluarla.")

st.markdown("#### Lo que encontró la primera medición, y qué cambié")
a, b, c = st.columns(3)
with a.container(border=True):
    st.markdown("**El examinador también fallaba**")
    st.caption("No sabía la hora y suspendía «te llamamos mañana a las 9:00» a las 23:10. Re-juzgando las mismas "
               "respuestas con el juez corregido se ve cuánto era culpa del juez.")
with b.container(border=True):
    st.markdown("**Prometía servicio donde no lo hay**")
    st.caption("Dijo que había cobertura en Las Palmas. Ahora solo la afirma si la ciudad está en la lista.")
with c.container(border=True):
    st.markdown("**Pasaba a una persona de más**")
    st.caption("Escalaba dudas médicas o un alta sin peligro inmediato. Ahora remite al médico y marca la urgencia.")
with st.container(border=True):
    st.markdown("**La lección más importante: el sobreajuste.** La v2 aprobaba el 88 % de los casos con los que la "
                "ajusté, pero solo el 60 % de casos nuevos: inventaba políticas que no estaban en la base («no damos "
                "precio por teléfono»). La v3 añade una regla de fidelidad y se mide con un conjunto nuevo.")

actual = datos[(CONJUNTOS[0][0], "v3")]
if actual.empty:
    actual = datos[(CONJUNTOS[0][0], "v2")]
fallos = actual[~actual["aprueba"]]
with st.expander(f"Fallos que quedan en la última versión ({len(fallos)})"):
    st.dataframe(fallos[["id", "categoria", "fallos", "motivo"]], hide_index=True, use_container_width=True)

st.divider()
st.markdown("#### Comprobar al examinador: etiqueto a ciegas")
etiquetas = json.loads(ETIQUETAS.read_text(encoding="utf-8")) if ETIQUETAS.exists() else {}
pendientes = [r for r in actual["r"] if r["id"] not in etiquetas]
izq, der = st.columns([3, 2])
with izq:
    if pendientes:
        r = pendientes[0]
        st.caption(f"Caso {r['id']} · {r['categoria']} · quedan {len(pendientes)} · no ves lo que dijo el examinador")
        for m in r["historial"]:
            with st.chat_message("user" if m["rol"] == "usuario" else "assistant"):
                st.write(m["texto"])
        x, y, _ = st.columns([1, 1, 3])
        for col, valor, texto in ((x, "aprueba", "Aprueba"), (y, "suspende", "Suspende")):
            if col.button(texto, key=f"{valor}-{r['id']}"):
                etiquetas[r["id"]] = valor
                ETIQUETAS.write_text(json.dumps(etiquetas, indent=1), encoding="utf-8")
                st.rerun()
    else:
        st.success("Todos los casos etiquetados.")
with der:
    comunes = [r for r in actual["r"] if r["id"] in etiquetas and r["juez"].get("veredicto") in ("aprueba", "suspende")]
    if len(comunes) >= 10:
        humano = [etiquetas[r["id"]] for r in comunes]
        juez = [r["juez"]["veredicto"] for r in comunes]
        kappa = cohen_kappa_score(humano, juez)
        acuerdo = sum(h == j for h, j in zip(humano, juez)) / len(comunes)
        st.metric("Coincidimos el examinador y yo", f"{100 * acuerdo:.0f} %", f"{len(comunes)} casos", delta_color="off")
        st.metric("Kappa de Cohen", f"{kappa:.2f}", help="Acuerdo descontando el azar. Por encima de ~0,8, el examinador es de fiar.")
    else:
        st.metric("Casos etiquetados", f"{len(comunes)} / 30")
        st.caption("Con 30 sale la kappa: si el examinador juzga como yo, puedo fiarme de él para revisar miles de conversaciones.")
