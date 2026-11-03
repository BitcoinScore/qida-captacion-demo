import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun
import detalles
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
    conclusion = (f"Con datos de ejemplo, {mejor['canal']} devuelve {es(mejor['ltv_cac'])} veces lo que cuesta; "
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
comun.titulo("1. ¿Qué canal compensa?", serif=True)
with st.container():
    st.markdown("**Cuántas veces vuelve lo invertido en cada canal**")
    comun.grafico(graficos.ltv_cac(eco, alto=320))
    with st.container():
        st.markdown("**Rentabilidad por canal**")
        euros = lambda v: es(v, 0, " €") if v == v and v else "—"  # noqa: E731
        con_coste = eco[eco["cac_combinado"].notna()].sort_values("ltv_cac", ascending=False)
        sin_coste = eco[eco["cac_combinado"].isna()]
        tope = 12  # escala con tope en 12×: por encima, la barra llena (la cifra dice cuánto)
        filas = []
        for _, f in con_coste.iterrows():
            pb = f["payback_meses"]
            meses = "—" if pb != pb or pb is None else f"{es(pb, 0)} {'mes' if pb == 1 else 'meses'}"
            filas.append({"Canal": f["canal"] + (" · pocos datos" if f["contratos"] < 50 else ""),
                          "Familias": es(f["familias"], 0), "Contratos": es(f["contratos"], 0),
                          "Cuesta captarla": euros(f["cac_combinado"]), "Deja en 12 meses": euros(f["ltv_12m"]),
                          "Retorno": float(f["ltv_cac"]), "Se recupera en": meses})
        for _, f in sin_coste.iterrows():
            filas.append({"Canal": f["canal"] + " · sin coste propio", "Familias": es(f["familias"], 0),
                          "Contratos": es(f["contratos"], 0), "Cuesta captarla": "—",
                          "Deja en 12 meses": euros(f["ltv_12m"]), "Retorno": None, "Se recupera en": "—"})
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch", column_config={
            "Canal": st.column_config.TextColumn(width="medium"),
            "Retorno": st.column_config.ProgressColumn("Retorno · veces lo invertido", format="%.1f×", min_value=0, max_value=tope,
                                                       width="large"),
        })
        total = eco["gasto_total"].sum() / max(eco["contratos"].sum(), 1)
        st.caption(f"Coste medio de captar una familia en el periodo: **{es(total, 0, ' €')}** (en la portada, el del último mes). "
                   "«Cuesta captarla» incluye medios, equipo y acuerdos. «Deja en 12 meses» = facturación × margen bruto "
                   "**supuesto** del 30 % × meses que sigue. Retorno por debajo de 3× = no compensa. «Pocos datos» = menos de 50 "
                   "contratos. Sin coste propio: llaman porque ya conocen a Qida (marca, boca a boca, folletos).")
        cc1, cc2 = st.columns([3, 1], vertical_alignment="bottom")
        canal_sel = cc1.selectbox("Abrir la ficha de un canal", list(eco["canal"]), key="canal-ficha")
        if cc2.button("Ver ficha del canal", icon=":material/open_in_new:", width="stretch"):
            detalles.ficha_canal(canal_sel, eco, cruce, curvas, atrib, periodo)
        with st.expander("Ver detalle: gasto, coste por familia y por valoración, coste solo de medios"):
            detalle = eco.sort_values("ltv_cac", ascending=False, na_position="last")
            st.dataframe(pd.DataFrame({
                "canal": detalle["canal"], "gasto": detalle["gasto_total"].map(euros),
                "€ por familia": detalle["coste_por_familia"].map(euros),
                "€ por valoración": detalle["coste_por_valoracion"].map(euros),
                "€ por contrato (solo medios)": detalle["cac_pago"].map(euros),
                "€ por contrato (total)": detalle["cac_combinado"].map(euros),
            }), hide_index=True, width="stretch")

st.divider()
comun.titulo("2. ¿Cuál convierte?", serif=True)
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
comun.titulo("3. Canal × ciudad", serif=True)
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
comun.titulo("4. ¿Dónde?", serif=True)
with st.container():
    comun.grafico(graficos.mapa(por_ciudad))
    cd1, cd2 = st.columns([3, 1], vertical_alignment="bottom")
    ciudad_sel = cd1.selectbox("Abrir la ficha de una ciudad", list(por_ciudad["ciudad"]), key="ciudad-ficha")
    if cd2.button("Ver ficha de la ciudad", icon=":material/open_in_new:", width="stretch"):
        detalles.ficha_ciudad(ciudad_sel, por_ciudad, cruce, periodo)
    if (por_ciudad["estado"] == "en la media").all():
        comun.nota("Ninguna ciudad convierte de forma significativamente distinta al resto: las diferencias son azar.",
                   "neutra")
    st.caption("Tamaño = volumen (área). Color = solo si la conversión difiere del resto con un 95 % de confianza. "
               "Cobertura (gris) y anuncios en Meta (anillo): reales, de la web y la Biblioteca de anuncios (2 de noviembre de 2026).")

st.divider()
comun.titulo("5. Qué canal trae a la familia y cuál la cierra", serif=True)
with st.container():
    a = atrib.rename(columns={"contratos_ultimo_contacto": "ultimo", "contratos_primer_contacto": "primero"})
    a["dif"] = a["primero"] - a["ultimo"]
    a = a.sort_values("dif")
    st.markdown("**Unos canales descubren familias y otros las cierran.** Ejemplo: Carmen descarga el menú semanal el lunes "
                "y el jueves llama por teléfono y contrata. El contrato se apunta al teléfono, pero fue el menú quien la trajo.")
    colores = [graficos.ACENTO if d > 0 else graficos.NEUTRO for d in a["dif"]]
    fig = go.Figure(go.Bar(
        x=a["dif"], y=a["canal"], orientation="h", marker_color=colores,
        text=[f"{'+' if d > 0 else ''}{es(d, 0)} familias" for d in a["dif"]], textposition="outside", cliponaxis=False,
        customdata=list(zip(a["ultimo"], a["primero"])),
        hovertemplate="%{y}: cierra %{customdata[0]} contratos; trajo a %{customdata[1]} familias que contrataron<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=graficos.GRIS, width=1))
    lim = a["dif"].abs().max() * 1.6
    fig.add_annotation(x=lim * 0.55, y=1.08, yref="paper", showarrow=False, text="<b>→ Descubre</b> más familias de las que cierra",
                       font=dict(color=comun.VERDE_TEXTO, size=12))
    fig.add_annotation(x=-lim * 0.55, y=1.08, yref="paper", showarrow=False, text="Cierra familias que trajo otro canal <b>←</b>",
                       font=dict(color=graficos.GRIS, size=12))
    graficos._limpio(fig, 70 + 44 * len(a))
    fig.update_layout(xaxis=dict(range=[-lim, lim], title="familias que trajo el canal menos contratos que cerró", zeroline=False),
                      yaxis_title=None, margin=dict(l=10, r=10, t=40, b=10))
    comun.grafico(fig)
    sube = a.loc[a["dif"].idxmax()]
    comun.nota(f"**Lectura:** {sube['canal']} solo cierra {es(sube['ultimo'], 0)} contratos, pero fue el primer contacto "
               f"de {es(sube['primero'], 0)} familias que acabaron contratando, casi todas por otro canal. Recortarlo por "
               "«no cerrar» haría perder esas familias. En el resto del panel, el contrato se apunta al canal que cierra (último "
               "contacto), y se dice.", "neutra")

with st.expander("Datos y consultas"):
    st.dataframe(eco.drop(columns=["ic_bajo", "ic_alto"]), hide_index=True, width="stretch")
    comun.descarga(eco.drop(columns=["ic_bajo", "ic_alto"]), "economia-por-canal", "Descargar la economía por canal (CSV)")
    comun.descarga(cruce, "canal-por-ciudad", "Descargar canal × ciudad (CSV)")
    st.code(sql_embudo, language="sql")
    st.code(sql_att, language="sql")
st.caption(comun.AVISO)
