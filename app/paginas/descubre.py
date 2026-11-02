import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun
import graficos
from comun import es
from motor import metricas

ciudades = comun.selector_ciudades()
PERIODOS = {"Últimos 3 meses": "2026-07", "Últimos 6 meses": "2026-04", "Últimos 12 meses": "2025-10",
            "Todo (desde mayo de 2025)": "2025-05"}
periodo = st.sidebar.radio("Periodo (mes en que piden ayuda)", list(PERIODOS), index=2)
desde = PERIODOS[periodo]
marc = ",".join("?" * len(ciudades))

with comun.conexion() as con:
    eco = metricas.economia_por_canal(con, ciudades, desde)
    sql_att, atrib = comun.ejecutar("2_atribucion.sql", ciudades)
    por_ciudad = pd.read_sql(
        f"""SELECT c.ciudad, COUNT(*) AS leads, COUNT(a.lead_id) AS contratos
            FROM cohorte c LEFT JOIN altas_30d a ON a.lead_id = c.id
            WHERE c.ciudad IN ({marc}) AND substr(c.fecha_entrada, 1, 7) >= ? GROUP BY c.ciudad""",
        con, params=[*ciudades, desde])
    flujos = pd.read_sql(
        f"""SELECT c.canal, COUNT(*) AS leads, COUNT(v.lead_id) AS valoraciones, COUNT(a.lead_id) AS altas
            FROM cohorte c LEFT JOIN valoraciones_30d v ON v.lead_id = c.id LEFT JOIN altas_30d a ON a.lead_id = c.id
            WHERE c.ciudad IN ({marc}) AND substr(c.fecha_entrada, 1, 7) >= ? GROUP BY c.canal""",
        con, params=[*ciudades, desde])
    cruce = pd.read_sql(
        f"""SELECT c.canal, c.ciudad, COUNT(*) AS familias, COUNT(a.lead_id) AS contratos, AVG(a.ingreso_mes) AS ingreso,
                   (SELECT SUM(importe) FROM gasto g WHERE g.canal = c.canal AND g.ciudad = c.ciudad
                      AND g.mes >= ? AND g.mes < '2026-10') AS gasto
            FROM cohorte c LEFT JOIN altas_30d a ON a.lead_id = c.id
            WHERE c.ciudad IN ({marc}) AND substr(c.fecha_entrada, 1, 7) >= ? GROUP BY c.canal, c.ciudad""",
        con, params=[desde, *ciudades, desde])
    curvas = metricas.duraciones(con, ciudades)
sql_embudo = comun.leer_sql("1_embudo_por_canal.sql")

fiables = eco[(eco["contratos"] >= 50) & eco["ltv_cac"].notna()]
if len(fiables) >= 2:
    mejor, peor = fiables.loc[fiables["ltv_cac"].idxmax()], fiables.loc[fiables["ltv_cac"].idxmin()]
    conclusion = (f"{mejor['canal']} devuelve {es(mejor['ltv_cac'])} veces lo que cuesta; "
                  f"{peor['canal']}, {es(peor['ltv_cac'])} veces")
else:
    conclusion = "Canales y ciudades"
comun.cabecera("Canales y ciudades", conclusion, "marketing",
               "Qué canal y qué ciudad traen familias que contratan, cuánto cuesta captarlas y cuánto valen. "
               f"Periodo: {periodo.lower()}.")

# ¿Cada ciudad difiere del resto? Prueba de dos proporciones (z), 95 %.
total_k, total_n = por_ciudad["contratos"].sum(), por_ciudad["leads"].sum()
estados, ics = [], []
for _, f in por_ciudad.iterrows():
    k2, n2 = total_k - f["contratos"], total_n - f["leads"]
    p1, p2, p = f["contratos"] / f["leads"], k2 / n2 if n2 else 0, total_k / total_n
    z = (p1 - p2) / math.sqrt(p * (1 - p) * (1 / f["leads"] + 1 / n2)) if n2 else 0
    estados.append("por encima" if z > 1.96 else "por debajo" if z < -1.96 else "en la media")
    lo, hi = metricas.wilson(int(f["contratos"]), int(f["leads"]))
    ics.append(f"{es(lo)}–{es(hi)} %")
por_ciudad["pct_alta"] = (100 * por_ciudad["contratos"] / por_ciudad["leads"]).round(1)
por_ciudad["estado"], por_ciudad["ic"] = estados, ics


st.divider()
st.subheader("1. ¿Qué canal compensa?")
with st.container():
    st.markdown("**Cuántas veces vuelve lo invertido en cada canal**")
    comun.grafico(graficos.ltv_cac(eco, alto=320))
    with st.container():
        st.markdown("**Rentabilidad por canal**")
        orden = eco.assign(_o=eco["ltv_cac"].fillna(-1)).sort_values("_o", ascending=False)
        euros = lambda v: es(v, 0, " €") if v == v and v else "—"  # noqa: E731
        tabla = pd.DataFrame({
            "canal": [c + (" (pocos datos)" if n < 50 else "") for c, n in zip(orden["canal"], orden["contratos"])],
            "familias": orden["familias"].map(lambda v: es(v, 0)),
            "contratos": orden["contratos"].map(lambda v: es(v, 0)),
            "gasto": orden["gasto_total"].map(euros),
            "€ por familia": orden["coste_por_familia"].map(euros),
            "€ por valoración": orden["coste_por_valoracion"].map(euros),
            "CAC de pago": orden["cac_pago"].map(euros),
            "CAC total": orden["cac_combinado"].map(euros),
            "valor 12 meses": orden["ltv_12m"].map(euros),
            "retorno": orden["ltv_cac"].map(lambda v: es(v, 1, "×") if v == v else "—"),
            "recupera (meses)": orden["payback_meses"].map(lambda v: "—" if v != v or v is None else es(v, 0)),
        })
        st.dataframe(tabla, hide_index=True, width="stretch")
        total = eco["gasto_total"].sum() / max(eco["contratos"].sum(), 1)
        st.caption(f"CAC total de todos los canales en el periodo: **{es(total, 0, ' €')}** por contrato (en la portada, "
                   "el del mes de septiembre). CAC de pago = solo medios; total = medios + equipo y acuerdos. "
                   "«Pocos datos» = menos de 50 contratos: cifra poco fiable (usa la permanencia general). «Teléfono directo» no tiene "
                   "coste asignado. Valor con margen bruto **supuesto** del 30 %.")

st.divider()
st.subheader("2. ¿Cuál convierte?")
with st.container():
    izq, der = st.columns(2)
    with izq:
        st.markdown("**De cada 100 familias, cuántas contratan en 30 días**")
        comun.grafico(graficos.puntos_ic(eco, "% que contrata (punto) e intervalo del 95 % (barra)"))
        st.caption("Si dos intervalos se solapan, la diferencia puede ser azar.")
    with der:
        st.markdown("**Qué pasa con cada 100 familias, por canal**")
        comun.grafico(graficos.destino_por_canal(flujos))

st.divider()
st.subheader("3. Canal × ciudad")
with st.container():
    MODOS = ["Retorno de la inversión", "% que contrata", "Coste por contrato (CAC total)"]
    metrica = st.radio("Mostrar", MODOS, horizontal=True)
    es_pct, es_retorno = metrica == MODOS[1], metrica == MODOS[0]
    c = cruce.copy()
    # Valor de una familia en 12 meses = facturación mensual media × margen bruto (supuesto) × meses que sigue (Kaplan-Meier)
    s_general = metricas._supervivencia(curvas)
    meses_canal = {k: (metricas._supervivencia(g) if len(g) >= 30 else s_general).sum() for k, g in curvas.groupby("canal")}
    c["valor_familia"] = c["ingreso"] * metricas.MARGEN_BRUTO * c["canal"].map(meses_canal).fillna(s_general.sum())
    coste = (c["gasto"] / c["contratos"].where(c["contratos"] > 0)).where(c["gasto"].fillna(0) > 0)
    if es_pct:
        c["valor"] = 100 * c["contratos"] / c["familias"]
    elif es_retorno:
        c["valor"] = c["valor_familia"] / coste
    else:
        c["valor"] = coste
    tabla = c.pivot(index="canal", columns="ciudad", values="valor")
    n = c.pivot(index="canal", columns="ciudad", values="contratos").reindex(tabla.index)
    sin_dato = tabla.index[tabla.isna().all(axis=1)].tolist()  # p. ej. «Teléfono directo» no tiene coste asignado
    tabla, n = tabla.drop(index=sin_dato), n.drop(index=sin_dato)
    orden = tabla.mean(axis=1).sort_values(ascending=es_pct or es_retorno).index  # el mejor arriba
    tabla, n = tabla.loc[orden], n.loc[orden]  # Plotly pinta la primera fila abajo: así el mejor queda arriba
    sufijo = " %" if es_pct else ("×" if es_retorno else " €")
    texto = [[("—" if v != v else es(v, 0 if sufijo == " €" else 1, sufijo)) + ("*" if (v == v and k == k and k < 15) else "")
              for v, k in zip(fila_v, fila_n)] for fila_v, fila_n in zip(tabla.values, n.values)]
    escala = graficos.ESCALA if es_pct else [[0, graficos.ACENTO], [1, "#EFF5F5"]]
    rango = {}
    if es_retorno:  # umbral sano en 3×: por debajo, tono de alerta; por encima, verdes; a partir de 10×, el más oscuro
        escala = [[0, "#f6c9b5"], [0.29, "#fbe7de"], [0.3, "#EFF5F5"], [1, graficos.ACENTO]]
        rango = dict(zmin=0, zmax=10)
    fig = go.Figure(go.Heatmap(z=tabla.values, x=tabla.columns, y=tabla.index, text=texto, texttemplate="%{text}",
                               colorscale=escala, showscale=False, hoverinfo="skip", xgap=2, ygap=2, **rango))
    graficos._limpio(fig, 60 + 44 * len(tabla))
    fig.update_layout(plot_bgcolor="#F1F5F5", xaxis=dict(side="top", showgrid=False), yaxis=dict(showgrid=False))
    comun.grafico(fig)
    nota_sin = f" No se muestra {', '.join(sin_dato)}: no tiene coste asignado." if sin_dato and not es_pct else ""
    explicacion = {MODOS[0]: "Retorno = margen que deja una familia en su primer año (facturación × margen bruto supuesto del 30 % × "
                             "meses que sigue), dividido entre lo que costó captarla. Por encima de 3× es sano (verde); por debajo, naranja. Es la vista para decidir dónde invertir.",
                   MODOS[1]: "Más oscuro = convierte más.",
                   MODOS[2]: "Solo coste: no tiene en cuenta lo que factura ni lo que dura cada familia. Más oscuro = más barato."}[metrica]
    st.caption(f"{explicacion} * = menos de 15 contratos en esa celda: no decidir solo con ella. — = sin contratos.{nota_sin}")

st.divider()
st.subheader("4. ¿Dónde?")
with st.container():
    comun.grafico(graficos.mapa(por_ciudad))
    if (por_ciudad["estado"] == "en la media").all():
        comun.nota("Ninguna ciudad convierte de forma significativamente distinta al resto: las diferencias son azar.",
                   "neutra")
    st.caption("Tamaño = volumen (área). Color = solo si la conversión difiere del resto con un 95 % de confianza. "
               "Cobertura (gris) y anuncios en Meta (anillo): reales, de la web y la Biblioteca de anuncios (2 de noviembre de 2026).")

st.divider()
st.subheader("5. Atribución")
with st.container():
    st.markdown("**Contratos por canal según el modelo de atribución**")
    st.dataframe(atrib.rename(columns={"contratos_ultimo_contacto": "último contacto (el que usamos)",
                                       "contratos_primer_contacto": "primer contacto"}),
                 hide_index=True, width="stretch")
    st.caption("El 8 % de las familias deja sus datos dos veces por canales distintos. Con el primer contacto, Meta y el "
               "contenido ganan peso; con el último, los canales que cierran. La elección se declara, no se esconde.")

with st.expander("Datos y consultas"):
    st.dataframe(eco.drop(columns=["ic_bajo", "ic_alto"]), hide_index=True, width="stretch")
    st.code(sql_embudo, language="sql")
    st.code(sql_att, language="sql")
st.caption(comun.AVISO)
