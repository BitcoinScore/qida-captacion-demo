import streamlit as st

import comun
import graficos
from motor import metricas

comun.cabecera("", "Viaje de la familia", "Dirección y marketing",
               "Cuántas familias pasan cada paso, dónde se pierden y qué construiría en cada uno.")

with comun.conexion() as con:
    familias, contactadas, valoraciones, contratos, contactos, desde, hasta = con.execute(
        """SELECT COUNT(*), COUNT(ll.lead_id), COUNT(v.lead_id), COUNT(a.lead_id),
                  (SELECT COUNT(*) FROM leads WHERE fecha_entrada < '2026-10-01'),
                  MIN(c.fecha_entrada), MAX(c.fecha_entrada)
           FROM cohorte c
           LEFT JOIN llamadas_30d ll    ON ll.lead_id = c.id
           LEFT JOIN valoraciones_30d v ON v.lead_id = c.id
           LEFT JOIN altas_30d a        ON a.lead_id = c.id"""
    ).fetchone()
    km = metricas.kaplan_meier(metricas.duraciones(con)).set_index("mes")["pct_siguen"]
    sep, ago = metricas.kpis_mes(con, "2026-09"), metricas.kpis_mes(con, "2026-08")
    eco = metricas.economia_por_canal(con, comun.CIUDADES)
r3, r12 = km[3] / 100, km[12] / 100
ltv_cac = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["gasto_total"].sum()

# ── 1. Lo primero que se mira: cinco KPIs del último mes completo ───────────────────────────────────────────────
st.markdown("<div class='seccion'>Septiembre de 2026 · último mes con 30 días de margen</div>", unsafe_allow_html=True)
k = st.columns(5)
comun.kpi(k[0], "Familias que piden ayuda", f"{sep['familias']:,}".replace(",", "."),
          "deduplicadas", 100 * (sep["familias"] / ago["familias"] - 1), unidad_tendencia=" %")
comun.kpi(k[1], "Conversión a contrato", f"{sep['conversion']:.1f} %".replace(".", ","),
          "en 30 días · objetivo 15 %", sep["conversion"] - ago["conversion"])
comun.kpi(k[2], "CAC combinado", f"{sep['cac']:,.0f} €".replace(",", "."),
          "todos los costes", sep["cac"] - ago["cac"], mejor_si_sube=False, unidad_tendencia=" €")
comun.kpi(k[3], "Llamadas en < 1 h", f"{sep['rapidas']:.0f} %",
          "objetivo 50 %", sep["rapidas"] - ago["rapidas"])
comun.kpi(k[4], "Siguen al año", f"{100 * r12:.0f} %", f"LTV:CAC {ltv_cac:.1f}× · Kaplan-Meier")
st.caption("Objetivos de ejemplo para la demo. Verde = mejora; naranja = empeora.")

# ── 2. El embudo ───────────────────────────────────────────────────────────────────────────────────────────────
st.markdown("#### Dónde se pierden las familias")
ETAPAS = [
    {"nombre": "Piden ayuda", "valor": familias,
     "perdida": f"{familias - contactadas:,} nunca llegan a hablar con nadie".replace(",", "."),
     "arreglo": "→ Asistente de noche que deja la llamada agendada"},
    {"nombre": "Hablan con un asesor", "valor": contactadas,
     "perdida": f"{contactadas - valoraciones:,} no llegan a la valoración · la gran fuga".replace(",", "."), "grave": True,
     "arreglo": "→ Llamar antes, y primero a quien más lo necesita"},
    {"nombre": "Valoración", "valor": valoraciones,
     "perdida": f"{valoraciones - contratos:,} no firman el presupuesto".replace(",", "."),
     "arreglo": "→ Expediente de Dependencia ya preparado"},
    {"nombre": "Contratan", "valor": contratos,
     "perdida": f"~{contratos - round(contratos * r3)} se van antes de 3 meses", "arreglo": "→ Satisfacción como alerta de baja"},
    {"nombre": "Siguen a los 3 meses", "valor": round(contratos * r3), "estimado": True,
     "perdida": f"~{round(contratos * r3) - round(contratos * r12)} se van entre el mes 3 y el 12",
     "arreglo": "→ Seguimiento y pedirles que nos recomienden"},
    {"nombre": "Siguen al año", "valor": round(contratos * r12), "estimado": True},
]
st.plotly_chart(graficos.embudo_viaje(ETAPAS), use_container_width=True, config={"displayModeBar": False})
st.caption(f"Familias que pidieron ayuda entre {desde[:7]} y {hasta[:7]}; cada paso, en los 30 días siguientes. "
           "Las dos últimas etapas (trazo discontinuo) son estimaciones con la curva de permanencia.")

# ── 3. El viaje, etapa a etapa (service blueprint) ────────────────────────────────────────────────────────────
st.markdown("#### El viaje, etapa a etapa")
ETAPAS_VIAJE = [
    ("Nos descubre", f"{familias:,}".replace(",", "."),
     "Busca «cuidadora para mi madre» o ve un anuncio en Instagram", "Google Ads, Meta por ciudad, blog y prescriptores",
     "Atribuir cada contrato a su canal", "CAC y LTV:CAC", "Ve el anuncio de Valencia a las 22:50"),
    ("Pide ayuda", f"{100 * (1 - contactadas / familias):.0f} % se pierde",
     "Deja sus datos o busca con quién hablar, a menudo de noche", "Formulario de 3 campos; teléfono de 9 a 20 h",
     "Asistente virtual que agenda la llamada", "Familias de noche que llegan a valoración", "23:10, el asistente le contesta"),
    ("Primera llamada", f"{100 * valoraciones / contactadas:.0f} % sigue",
     "Espera la llamada; si tarda, prueba con otra empresa", "Asesor/a familiar, en menos de 24 h",
     "Cola ordenada por probabilidad y urgencia", "Llamadas en < 1 h", "Primera llamada del día, 9:05"),
    ("Valoración", f"{100 * contratos / valoraciones:.0f} % firma",
     "Cuenta el caso y duda si podrá pagarlo", "Valoración sin coste y presupuesto personalizado",
     "Expediente de Dependencia preparado", "Presupuestos firmados", "Grado II: prestación vinculada"),
    ("Plan y cuidadora", "sin medir",
     "Conoce a la cuidadora propuesta y decide", "PTI con la Referente Social; propuesta de cuidadora",
     "Medir días hasta el primer servicio", "Días hasta el primer servicio", "Elige a su cuidadora"),
    ("Se queda", f"{100 * r12:.0f} % al año",
     "Si va bien, sigue y lo cuenta a otras familias", "Seguimiento de la Referente Social",
     "Alerta de baja y petición de recomendación", "Permanencia y recomendaciones", "Sigue a los 3 meses"),
]
FILAS = [("La familia", 2), ("Qida hoy", 3), ("Qué construiría", 4), ("Cómo lo mido", 5), ("Ejemplo: Lucía", 6)]
grave = {2}  # índice de la etapa con la gran fuga (de la llamada a la valoración)
cabecera = "".join(
    f"<th style='border-top:4px solid {comun.NARANJA if i in grave else comun.VERDE}'>"
    f"<div style='font-size:.75rem;color:#6b7b7a'>{i + 1}</div>{e[0]}"
    f"<div style='font-size:.85rem;font-weight:700;color:{comun.NARANJA if i in grave else comun.VERDE_MEDIO}'>{e[1]}</div></th>"
    for i, e in enumerate(ETAPAS_VIAJE))
cuerpo = "".join(
    f"<tr><td class='fila'>{nombre}</td>" + "".join(f"<td>{e[idx]}</td>" for e in ETAPAS_VIAJE) + "</tr>"
    for nombre, idx in FILAS)
st.markdown(
    f"""
<style>
.blueprint {{width:100%; border-collapse:separate; border-spacing:6px; font-size:.86rem; table-layout:fixed}}
.blueprint th {{background:{comun.FONDO}; color:{comun.VERDE}; text-align:left; padding:10px; border-radius:8px; vertical-align:top}}
.blueprint td {{background:white; border:1px solid {comun.BORDE}; border-radius:8px; padding:8px 10px; vertical-align:top}}
.blueprint td.fila {{background:transparent; border:0; color:{comun.VERDE_MEDIO}; font-weight:700; font-size:.78rem;
  text-transform:uppercase; letter-spacing:.05em; width:9%}}
.blueprint tr:nth-child(3) td:not(.fila) {{background:{comun.FONDO}; color:{comun.VERDE}; font-weight:500}}
.blueprint tr:last-child td:not(.fila) {{color:#6b7b7a; font-style:italic}}
</style>
<table class="blueprint"><tr><th style="background:transparent;border:0"></th>{cabecera}</tr>{cuerpo}</table>
""",
    unsafe_allow_html=True,
)

with st.expander("Cómo se mide (definiciones)"):
    st.markdown(
        f"""
- **Familias, no contactos:** {contactos:,} contactos del CRM corresponden a {familias:,} familias; las que entraron por dos
  canales se fusionan por teléfono. **Atribución:** último contacto antes del resultado.
- **Cohorte madura:** se excluye octubre de 2026 porque esas familias aún no han tenido tiempo de contratar.
- **Ventana de conversión:** cada paso cuenta si ocurre en los 30 días siguientes a pedir ayuda.
- **Siguen a 3 y 12 meses (estimado):** contratos × permanencia de Kaplan-Meier ({100 * r3:.0f} % y {100 * r12:.0f} %).
- **LTV:CAC del conjunto:** margen a 12 meses de todos los contratos ÷ gasto total (margen bruto supuesto del 30 %).
""".replace(",", ".")
    )
