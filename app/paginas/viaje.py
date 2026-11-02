import math

import streamlit as st

import comun
import graficos
from comun import es
from motor import metricas

with comun.conexion() as con:
    familias, contactadas, valoraciones, contratos, contactos, desde, hasta, n_meses = con.execute(
        """SELECT COUNT(*), COUNT(ll.lead_id), COUNT(v.lead_id), COUNT(a.lead_id),
                  (SELECT COUNT(*) FROM leads WHERE fecha_entrada < '2026-10-01'),
                  MIN(c.fecha_entrada), MAX(c.fecha_entrada), COUNT(DISTINCT substr(c.fecha_entrada, 1, 7))
           FROM cohorte c
           LEFT JOIN llamadas_30d ll    ON ll.lead_id = c.id
           LEFT JOIN valoraciones_30d v ON v.lead_id = c.id
           LEFT JOIN altas_30d a        ON a.lead_id = c.id"""
    ).fetchone()
    franjas = {fuera: (n, val, con_) for fuera, n, val, con_ in con.execute(
        """SELECT c.fuera_horario, COUNT(*), COUNT(v.lead_id), COUNT(a.lead_id) FROM cohorte c
           LEFT JOIN valoraciones_30d v ON v.lead_id = c.id LEFT JOIN altas_30d a ON a.lead_id = c.id
           GROUP BY c.fuera_horario""")}
    km = metricas.kaplan_meier(metricas.duraciones(con)).set_index("mes")["pct_siguen"]
    sep, ago = metricas.kpis_mes(con, "2026-09"), metricas.kpis_mes(con, "2026-08")
    eco = metricas.economia_por_canal(con, comun.CIUDADES)
r3, r12 = km[3] / 100, km[12] / 100
ltv_medio = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["contratos"].sum()
ltv_cac = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["gasto_total"].sum()
(n_dia, val_dia, con_dia), (n_noche, val_noche, con_noche) = franjas[0], franjas[1]
pct_noche = 100 * n_noche / familias
tasa_dia, tasa_noche = val_dia / n_dia, val_noche / n_noche  # llegan a valoración

comun.cabecera("Viaje de la familia", "La mayor fuga está entre la primera llamada y la valoración",
               "dirección y marketing",
               f"De cada 100 familias con las que habla un asesor/a familiar, solo {es(100 * valoraciones / contactadas, 0)} "
               "llegan a la valoración. Y casi 4 de cada 10 piden ayuda cuando no hay nadie al teléfono.")

# ── 1. Lo primero que se mira: seis indicadores del último mes completo ───────────────────────────────────────────
st.markdown(f"<div class='seccion'>{comun.mes_es('2026-09').capitalize()} · último mes con 30 días de margen</div>",
            unsafe_allow_html=True)
k = st.columns(6)
comun.kpi(k[0], "Familias que piden ayuda", es(sep["familias"], 0), "sin duplicados",
          100 * (sep["familias"] / ago["familias"] - 1), unidad_tendencia=" %")
comun.kpi(k[1], "Piden ayuda de noche", f"{es(pct_noche, 0)} %", "fuera del horario de atención")
comun.kpi(k[2], "Llamadas en menos de 1 h", f"{es(sep['rapidas'], 0)} %", "objetivo: 50 %",
          sep["rapidas"] - ago["rapidas"], alerta=sep["rapidas"] < 25)
comun.kpi(k[3], "Contratan en 30 días", f"{es(sep['conversion'])} %", "objetivo: 15 %",
          sep["conversion"] - ago["conversion"])
comun.kpi(k[4], "Coste de captar una familia", es(sep["cac"], 0, " €"), "CAC total del mes",
          sep["cac"] - ago["cac"], mejor_si_sube=False, unidad_tendencia=" €")
comun.kpi(k[5], "Siguen con Qida al año", f"{es(100 * r12, 0)} %", f"cada euro invertido vuelve ×{es(ltv_cac)}")
st.caption("Objetivos de ejemplo. Verde: mejora; naranja: empeora o está lejos del objetivo.")

# ── 2. El embudo ───────────────────────────────────────────────────────────────────────────────────────────────
st.markdown("#### Dónde se pierden las familias")
ETAPAS = [
    {"nombre": "Piden ayuda", "valor": familias,
     "perdida": f"{es(familias - contactadas, 0)} nunca llegan a hablar con nadie",
     "arreglo": "→ Que de noche el asistente deje la llamada agendada"},
    {"nombre": "Hablan con su asesor/a", "valor": contactadas,
     "perdida": f"{es(contactadas - valoraciones, 0)} no llegan a la valoración · la gran fuga", "grave": True,
     "arreglo": "→ Llamar antes: asistente de noche y cola priorizada"},
    {"nombre": "Valoración", "valor": valoraciones,
     "perdida": f"{es(valoraciones - contratos, 0)} no firman el presupuesto",
     "arreglo": "→ Expediente de la Dependencia ya preparado"},
    {"nombre": "Contratan", "valor": contratos,
     "perdida": f"~{es(contratos - round(contratos * r3), 0)} se van antes de 3 meses",
     "arreglo": "→ La satisfacción como alerta de baja"},
    {"nombre": "Siguen a los 3 meses", "valor": round(contratos * r3), "estimado": True,
     "perdida": f"~{es(round(contratos * r3) - round(contratos * r12), 0)} se van entre el mes 3 y el 12",
     "arreglo": "→ Seguimiento y pedir que nos recomienden"},
    {"nombre": "Siguen al año", "valor": round(contratos * r12), "estimado": True},
]
st.plotly_chart(graficos.embudo_viaje(ETAPAS), width="stretch", config={"displayModeBar": False})
st.caption(f"Familias que pidieron ayuda de {comun.mes_es(desde)} a {comun.mes_es(hasta)}; cada paso cuenta si ocurre en "
           "los 30 días siguientes. Las dos últimas etapas (trazo discontinuo) son estimaciones con la curva de permanencia.")

# ── 3. El viaje, etapa a etapa (service blueprint) ────────────────────────────────────────────────────────────
st.markdown("#### El viaje, etapa a etapa")
ETAPAS_VIAJE = [
    ("Nos descubre", es(familias, 0),
     "Busca «cuidadora para mi madre» o ve un anuncio en Instagram", "Google Ads, Meta por ciudad, blog y prescriptores",
     "Atribuir cada contrato a su canal", "Coste de captar una familia y lo que vale", "Ve el anuncio de Valencia a las 22:50"),
    ("Pide ayuda", f"{es(pct_noche, 0)} % de noche",
     "Deja sus datos o busca con quién hablar, a menudo de noche", "Formulario de 3 campos; teléfono de 9:00 a 20:00",
     "Asistente de noche que deja la llamada agendada", "Familias de noche que llegan a la valoración",
     "A las 23:10, el asistente le contesta"),
    ("Primera llamada", f"{es(100 * valoraciones / contactadas, 0)} % sigue",
     "Espera la llamada; si tarda, prueba con otra empresa", "Asesor/a familiar, en menos de 24 h",
     "Cola con urgentes primero y después por probabilidad", "Llamadas en menos de 1 h", "Primera llamada del día, a las 9:05"),
    ("Valoración", f"{es(100 * contratos / valoraciones, 0)} % firma",
     "Cuenta el caso y duda si podrá pagarlo", "Valoración gratuita y presupuesto personalizado",
     "Expediente de la Dependencia preparado", "Presupuestos firmados", "Grado II: prestación vinculada"),
    ("Plan y cuidadora", "sin medir",
     "Conoce a la cuidadora propuesta y decide", "Plan de Trabajo Individual (PTI) con la Referente Social",
     "Medir días hasta el primer servicio", "Días hasta el primer servicio", "Elige a su cuidadora"),
    ("Se queda", f"{es(100 * r12, 0)} % al año",
     "Si va bien, sigue y lo cuenta a otras familias", "Seguimiento de la Referente Social",
     "Alerta de baja y petición de recomendación", "Permanencia y recomendaciones", "Sigue a los 3 meses"),
]
FILAS = [("La familia", 2), ("Qida hoy", 3), ("Qué construiría", 4), ("Cómo lo mido", 5), ("Ejemplo: Lucía", 6)]
grave = {2}  # la etapa con la gran fuga (de la llamada a la valoración)
cabecera = "".join(
    f"<th style='border-top:4px solid {comun.NARANJA if i in grave else comun.VERDE}'>"
    f"<div style='font-size:.75rem;color:{comun.GRIS_TEXTO}'>{i + 1}</div>{e[0]}"
    f"<div style='font-size:.85rem;font-weight:700;color:{comun.NARANJA_TEXTO if i in grave else comun.VERDE_TEXTO}'>{e[1]}</div></th>"
    for i, e in enumerate(ETAPAS_VIAJE))
cuerpo = "".join(
    f"<tr><td class='fila'>{nombre}</td>" + "".join(f"<td>{e[idx]}</td>" for e in ETAPAS_VIAJE) + "</tr>"
    for nombre, idx in FILAS)
st.markdown(
    f"""
<style>
.blueprint-envoltorio {{overflow-x:auto}}
.blueprint {{width:100%; min-width:900px; border-collapse:separate; border-spacing:6px; font-size:.86rem; table-layout:fixed}}
.blueprint th {{background:{comun.FONDO}; color:{comun.VERDE}; text-align:left; padding:10px; border-radius:8px; vertical-align:top}}
.blueprint td {{background:white; border:1px solid {comun.BORDE}; border-radius:8px; padding:8px 10px; vertical-align:top;
  hyphens:none; word-break:normal}}
.blueprint td.fila {{background:transparent; border:0; color:{comun.VERDE_TEXTO}; font-weight:700; font-size:.78rem;
  text-transform:uppercase; letter-spacing:.05em; width:9%}}
.blueprint tr:nth-child(4) td:not(.fila) {{background:{comun.FONDO}; color:{comun.VERDE}; font-weight:500}}
.blueprint tr:last-child td:not(.fila) {{color:{comun.GRIS_TEXTO}; font-style:italic}}
</style>
<div class="blueprint-envoltorio"><table class="blueprint">
<tr><th style="background:transparent;border:0"></th>{cabecera}</tr>{cuerpo}</table></div>
""",
    unsafe_allow_html=True,
)

# ── 4. Caso de negocio y cómo se probaría ────────────────────────────────────────────────────────────────────────
st.markdown("#### Qué valdría arreglar la noche, y cómo lo probaría")
noche_mes = n_noche / n_meses
extra_mes = noche_mes * (con_dia / n_dia - con_noche / n_noche)
# Tamaño del A/B: familias de noche por grupo para detectar la diferencia de llegada a valoración (95 %, potencia 80 %)
d = tasa_dia - tasa_noche
n_grupo = math.ceil((1.96 + 0.84) ** 2 * (tasa_dia * (1 - tasa_dia) + tasa_noche * (1 - tasa_noche)) / d ** 2)
c1, c2, c3 = st.columns(3)
comun.kpi(c1, "Si la noche convirtiera como el día", f"+{es(extra_mes * 12, 0)} familias al año",
          f"de noche contrata el {es(100 * con_noche / n_noche)} %; de día, el {es(100 * con_dia / n_dia)} %")
comun.kpi(c2, "Margen que supondría", f"~{es(extra_mes * 12 * ltv_medio / 1000, 0)} mil €/año",
          f"valor medio de una familia en 12 meses: {es(ltv_medio, 0, ' €')} (margen supuesto del 30 %)")
comun.kpi(c3, "Tamaño del A/B", f"{es(n_grupo, 0)} familias por grupo",
          f"para ver la diferencia en llegada a la valoración ({es(100 * tasa_noche, 0)} % → {es(100 * tasa_dia, 0)} %)")
comun.nota("**Cómo lo probaría:** asistente sí/no en semanas alternas en una ciudad. Métrica principal: familias de noche "
           "que llegan a la valoración en 30 días; de control: coste de captar una familia y permanencia a 3 meses. "
           "Es una hipótesis: que la noche convierta peor es una asociación en los datos, no una causa probada.", "neutra")

with st.expander("Cómo se mide (definiciones)"):
    st.markdown(
        f"""
- **Familias, no contactos:** {es(contactos, 0)} contactos del CRM corresponden a {es(familias, 0)} familias; las que entraron por
  dos canales se unen por teléfono. **Atribución:** último contacto antes del resultado.
- **Cohorte madura:** se deja fuera octubre de 2026, porque esas familias aún no han tenido tiempo de contratar.
- **Ventana de conversión:** cada paso cuenta si ocurre en los 30 días siguientes a pedir ayuda.
- **Siguen a 3 y 12 meses (estimado):** contratos × permanencia de Kaplan-Meier ({es(100 * r3, 0)} % y {es(100 * r12, 0)} %).
- **Retorno del conjunto:** valor de 12 meses de todos los contratos ÷ gasto total (margen bruto supuesto del 30 %).
"""
    )
