import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import cohen_kappa_score

import comun
import graficos
from comun import es
from motor import metricas

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


VERSIONES = ["v1 (revisor v1)", "v1 (revisor v2)", "v2", "v3"]
CONJUNTOS = [  # (nombre, color, {versión: fichero})
    ("Casos de ajuste (60)", graficos.PERDIDA, {"v1 (revisor v1)": "resultados_v1.json",
                                               "v1 (revisor v2)": "resultados_v1_juez2.json",
                                               "v2": "resultados_v2.json", "v3": "resultados_v3.json"}),
    ("Casos nuevos, 1.ª tanda (20)", graficos.NEUTRO, {"v2": "resultados_v2_reserva.json", "v3": "resultados_v3_reserva.json"}),
    ("Casos nuevos, 2.ª tanda (25)", graficos.ACENTO, {"v3": "resultados_v3_reserva2.json"}),
]
datos = {(c, v): cargar(f) for c, _, ficheros in CONJUNTOS for v, f in ficheros.items()}


def nota_de(d: pd.DataFrame) -> tuple[float, float, float, int]:
    k, n = int(d["aprueba"].sum()), len(d)
    lo, hi = metricas.wilson(k, n)
    return 100 * k / n, lo, hi, n


vale = datos[(CONJUNTOS[2][0], "v3")]
v2_nuevos = datos[(CONJUNTOS[1][0], "v2")]
conclusion = (f"Con casos que no había visto, el asistente pasó del {es(nota_de(v2_nuevos)[0], 0)} % al "
              f"{es(nota_de(vale)[0], 0)} % de respuestas correctas") if not vale.empty and not v2_nuevos.empty \
    else "Calidad del asistente"
total_conv = sum(len(d) for d in datos.values())
comun.cabecera("Calidad del asistente", conclusion, "el equipo de IA",
               "Conversaciones difíciles → reglas automáticas → otra IA como revisor automático → una persona comprueba al "
               "revisor. Así sé si el asistente responde bien antes de ponerlo delante de una familia.",
               chip=f"Evaluación real · {es(total_conv, 0)} conversaciones con el modelo", real=True)

if all(d.empty for d in datos.values()):
    comun.nota("Todavía no hay resultados. Ejecuta `python eval/ejecutar.py`.", "alerta")
    st.stop()

fila = comun.Fila()
c1 = c2 = c3 = fila
for col, (clave, titulo, sub) in zip((c1, c2, c3), (
        ((CONJUNTOS[2][0], "v3"), "v3 con casos nuevos", "la nota que cuenta"),
        ((CONJUNTOS[1][0], "v2"), "v2 con casos nuevos", "antes de la regla de fidelidad"),
        ((CONJUNTOS[0][0], "v3"), "v3 con los casos de ajuste", "inflada: con ellos se ajustó"))):
    if not datos[clave].empty:
        p, lo, hi, n = nota_de(datos[clave])
        comun.kpi(col, titulo, f"{es(p, 0)} %", f"{sub} · intervalo del 95 %: {es(lo, 0)}–{es(hi, 0)} % · "
                                               f"{n} conversaciones")

fila.pintar()
st.markdown("#### Respuestas correctas por versión (reglas + revisor automático), con intervalo del 95 %")
CORTO = {CONJUNTOS[0][0]: "casos de ajuste", CONJUNTOS[1][0]: "casos nuevos 1", CONJUNTOS[2][0]: "casos nuevos 2"}
fig = go.Figure()
orden = []
for v in VERSIONES:  # una categoría por barra, en orden de versión: sin huecos
    for conjunto, _, _ in CONJUNTOS:
        if not datos.get((conjunto, v), pd.DataFrame()).empty:
            orden.append(f"<b>{v}</b><br>{CORTO[conjunto]}")
for conjunto, color, ficheros in CONJUNTOS:
    xs, ys, sup, inf, textos = [], [], [], [], []
    for v in VERSIONES:
        d = datos.get((conjunto, v))
        if d is None or d.empty:
            continue
        p, lo, hi, n = nota_de(d)
        xs.append(f"<b>{v}</b><br>{CORTO[conjunto]}"); ys.append(p); sup.append(hi - p); inf.append(p - lo)
        textos.append(f"<b>{es(p, 0)} %</b>")
    if ys:
        fig.add_bar(x=xs, y=ys, name=conjunto, marker_color=color, text=textos, textposition="inside",
                    insidetextanchor="start", textfont=dict(color="white" if color == graficos.ACENTO else "#333333"),
                    error_y=dict(type="data", symmetric=False, array=sup, arrayminus=inf, color=graficos.GRIS,
                                 thickness=1.2, width=4))
graficos._limpio(fig, 420)
fig.update_layout(barmode="overlay", bargap=0.35, legend=dict(orientation="h", y=1.12),
                  xaxis=dict(title=None, type="category", categoryorder="array", categoryarray=orden, tickfont=dict(size=12)),
                  yaxis=dict(title="% de respuestas correctas", range=[0, 105], showgrid=False, ticksuffix=" %"))
comun.grafico(fig)
st.caption("**v1 → v1 (revisor v2):** mismas respuestas, revisor corregido: el salto era del revisor. **v2:** asistente "
           "corregido. **v3:** regla de fidelidad, tras ver que la v2 inventaba políticas con casos nuevos. La 1.ª tanda "
           "de casos nuevos ya se vio al diseñar la v3; por eso la que cuenta es la 2.ª, escrita antes de evaluarla.")

st.markdown("#### Qué encontré y qué cambié")
a, b, c, d = st.columns(4)
with a:
    comun.nota("**El revisor también fallaba.** No sabía la hora y suspendía «te llamamos mañana a las 9:00» a las 23:10.")
with b:
    comun.nota("**Prometía servicio donde no lo hay** (Las Palmas). Ahora solo lo afirma si la zona está en la lista.")
with c:
    comun.nota("**Pasaba a una persona de más** (dudas médicas, altas sin peligro). Ahora remite al médico y marca la urgencia.")
with d:
    comun.nota("**Sobreajuste:** 88 % con los casos de ajuste, 60 % con casos nuevos. La regla de fidelidad lo corrigió.",
               "alerta")

actual = datos[(CONJUNTOS[0][0], "v3")]
if actual.empty:
    actual = datos[(CONJUNTOS[0][0], "v2")]
if not actual.empty:
    fallos = actual[~actual["aprueba"]]
    with st.expander(f"Fallos que quedan en la última versión ({len(fallos)})"):
        st.dataframe(fallos[["id", "categoria", "fallos", "motivo"]], hide_index=True, width="stretch")

    st.divider()
    st.markdown("#### Comprobar al revisor automático: una persona etiqueta a ciegas")
    etiquetas = json.loads(ETIQUETAS.read_text(encoding="utf-8")) if ETIQUETAS.exists() else {}
    pendientes = [r for r in actual["r"] if r["id"] not in etiquetas]
    izq, der = st.columns([3, 2])
    with izq:
        if pendientes:
            r = pendientes[0]
            st.caption(f"Caso {r['id']} · {r['categoria'].replace('_', ' ')} · quedan {len(pendientes)} · "
                       "no ves lo que dijo el revisor")
            for m in r["historial"]:
                with st.chat_message("user" if m["rol"] == "usuario" else "assistant"):
                    st.write(m["texto"])
            x, y, _ = st.columns([1, 1, 3])
            for col, valor, texto in ((x, "aprueba", "Correcta"), (y, "suspende", "Incorrecta")):
                if col.button(texto, key=f"{valor}-{r['id']}"):
                    etiquetas[r["id"]] = valor
                    ETIQUETAS.write_text(json.dumps(etiquetas, indent=1), encoding="utf-8")
                    st.rerun()
        else:
            comun.nota("Todos los casos etiquetados.")
    with der:
        comunes = [r for r in actual["r"] if r["id"] in etiquetas and r["juez"].get("veredicto") in ("aprueba", "suspende")]
        if len(comunes) >= 10:
            humano = [etiquetas[r["id"]] for r in comunes]
            revisor = [r["juez"]["veredicto"] for r in comunes]
            kappa = cohen_kappa_score(humano, revisor)
            acuerdo = sum(h == j for h, j in zip(humano, revisor)) / len(comunes)
            comun.kpi(st, "Coincidencia persona-revisor", f"{es(100 * acuerdo, 0)} %",
                      f"{len(comunes)} casos · kappa de Cohen {es(kappa, 2)} (fiable por encima de ~0,8)")
        else:
            comun.kpi(st, "Calibración humana en curso", f"{len(comunes)} de 30",
                      "con 30 casos sale la kappa de Cohen: si el revisor juzga como una persona, sirve para revisar "
                      "miles de conversaciones")
