import math

import pandas as pd
import streamlit as st

import comun
import graficos
from motor import metricas

comun.cabecera("", "Canales y ciudades", "Marketing",
               "Qué canal y qué ciudad traen familias que contratan, cuánto cuestan y cuánto valen.")
ciudades = comun.selector_ciudades()
marc = ",".join("?" * len(ciudades))

with comun.conexion() as con:
    eco = metricas.economia_por_canal(con, ciudades)
    sql_att, atrib = comun.ejecutar("2_atribucion.sql", ciudades)
    por_ciudad = pd.read_sql(
        f"""SELECT c.ciudad, COUNT(*) AS leads, COUNT(a.lead_id) AS contratos
            FROM cohorte c LEFT JOIN altas_30d a ON a.lead_id = c.id WHERE c.ciudad IN ({marc}) GROUP BY c.ciudad""",
        con, params=ciudades)
    flujos = pd.read_sql(
        f"""SELECT c.canal, COUNT(*) AS leads, COUNT(v.lead_id) AS valoraciones, COUNT(a.lead_id) AS altas
            FROM cohorte c LEFT JOIN valoraciones_30d v ON v.lead_id = c.id LEFT JOIN altas_30d a ON a.lead_id = c.id
            WHERE c.ciudad IN ({marc}) GROUP BY c.canal ORDER BY leads DESC""", con, params=ciudades)
sql_embudo = comun.leer_sql("1_embudo_por_canal.sql")

# ¿Cada ciudad difiere del resto? Prueba de dos proporciones (z), 95 %.
total_k, total_n = por_ciudad["contratos"].sum(), por_ciudad["leads"].sum()
estados, ics = [], []
for _, f in por_ciudad.iterrows():
    k2, n2 = total_k - f["contratos"], total_n - f["leads"]
    p1, p2, p = f["contratos"] / f["leads"], k2 / n2 if n2 else 0, total_k / total_n
    z = (p1 - p2) / math.sqrt(p * (1 - p) * (1 / f["leads"] + 1 / n2)) if n2 else 0
    estados.append("por encima" if z > 1.96 else "por debajo" if z < -1.96 else "en la media")
    lo, hi = metricas.wilson(int(f["contratos"]), int(f["leads"]))
    ics.append(f"{lo:.1f}–{hi:.1f} %")
por_ciudad["pct_alta"] = (100 * por_ciudad["contratos"] / por_ciudad["leads"]).round(1)
por_ciudad["estado"], por_ciudad["ic"] = estados, ics

tab1, tab2, tab3, tab4 = st.tabs([":material/euro: ¿Qué canal compensa?", ":material/target: ¿Cuál convierte?", ":material/map: ¿Dónde?", ":material/alt_route: Atribución"])

with tab1:
    izq, der = st.columns([2, 3])
    with izq:
        st.markdown("**Retorno de cada canal: LTV:CAC**")
        st.plotly_chart(graficos.ltv_cac(eco), use_container_width=True)
    with der:
        st.markdown("**Unidad económica por canal**")
        def euros(v):
            return "—" if pd.isna(v) or v == 0 else f"{v:,.0f} €".replace(",", ".")

        orden = eco.assign(_o=eco["ltv_cac"].replace([float("inf")], -1)).sort_values("_o", ascending=False)
        tabla = pd.DataFrame({
            "canal": [c + (" ⚠️" if n < 50 else "") for c, n in zip(orden["canal"], orden["contratos"])],
            "contratos": orden["contratos"],
            "CAC de pago": orden["cac_pago"].map(euros),
            "CAC combinado": orden["cac_combinado"].map(euros),
            "LTV 12 m": orden["ltv_12m"].map(euros),
            "LTV:CAC": orden["ltv_cac"].map(lambda v: "—" if pd.isna(v) or v == float("inf") else f"{v:.1f}×"),
            "payback (meses)": orden["payback_meses"].map(lambda v: "—" if pd.isna(v) else f"{int(v)}"),
        })
        st.dataframe(tabla, hide_index=True, use_container_width=True)
        mezcla = eco["gasto_total"].sum() / eco["contratos"].sum()
        st.caption(f"CAC combinado de todos los canales: **{mezcla:.0f} €** por contrato. CAC de pago = solo medios; "
                   f"combinado = medios + equipo y acuerdos. ⚠️ = menos de 50 contratos: cifra poco fiable. "
                   f"«Teléfono directo» no tiene coste asignado (marca). LTV con margen bruto **supuesto** del "
                   f"{metricas.MARGEN_BRUTO:.0%}: con el margen real cambia.")

with tab2:
    st.markdown("**% de familias que contratan en 30 días, con margen de error (95 %)**")
    st.plotly_chart(graficos.barras_ic(eco, "% que contrata"), use_container_width=True)
    st.caption("Si dos barras se solapan en su margen de error, la diferencia puede ser azar.")
    st.plotly_chart(graficos.sankey(flujos), use_container_width=True)

with tab3:
    st.plotly_chart(graficos.mapa(por_ciudad), use_container_width=True)
    if (por_ciudad["estado"] == "en la media").all():
        st.info("Ninguna ciudad convierte de forma significativamente distinta al resto: las diferencias son azar.")
    st.caption("Tamaño = volumen (área). Color = solo si la conversión difiere del resto con un 95 % de confianza. "
               "Cobertura (gris) y anuncios en Meta (anillo naranja): reales (web y Biblioteca de anuncios, 02-11).")

with tab4:
    st.markdown("**Contratos por canal según el modelo de atribución**")
    st.dataframe(atrib.rename(columns={"contratos_ultimo_contacto": "último contacto (el que usamos)",
                                       "contratos_primer_contacto": "primer contacto"}),
                 hide_index=True, use_container_width=True)
    st.caption("El 8 % de las familias deja sus datos dos veces por canales distintos. Con el primer contacto, Meta y el "
               "contenido ganan peso; con el último, los canales que cierran. La elección se declara, no se esconde.")

with st.expander("Datos y SQL"):
    st.dataframe(eco.drop(columns=["ic_bajo", "ic_alto"]), hide_index=True, use_container_width=True)
    st.code(sql_embudo, language="sql")
    st.code(sql_att, language="sql")
st.caption(comun.AVISO)
