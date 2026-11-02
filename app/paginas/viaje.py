import math
from datetime import date, timedelta

import streamlit as st

import comun
import graficos
from comun import es
from motor import metricas

ULTIMO_DATO = date(2026, 10, 31)  # «hoy» en la demo: último día con datos
def meses_atras(d: date, n: int) -> date:
    """Primer día del mes que está n meses antes del mes de `d`."""
    total = d.year * 12 + d.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


OPCIONES = {"Último mes": 1, "Últimos 3 meses": 3, "Últimos 6 meses": 6, "Último año": 12, "Personalizado": None}
eleccion = st.sidebar.selectbox("Periodo de los indicadores", list(OPCIONES), index=0,
                                help="Se compara con el periodo anterior equivalente (el mes, los 3 o 6 meses o el año antes).")
n_meses_periodo = OPCIONES[eleccion]
if n_meses_periodo:
    p_hasta = ULTIMO_DATO
    p_desde = meses_atras(ULTIMO_DATO, n_meses_periodo - 1)
    a_hasta = p_desde - timedelta(days=1)
    a_desde = meses_atras(p_desde, n_meses_periodo)
else:
    periodo = st.sidebar.date_input("Fechas", value=(ULTIMO_DATO.replace(day=1), ULTIMO_DATO),
                                    min_value=date(2025, 5, 1), max_value=ULTIMO_DATO, format="DD/MM/YYYY")
    if not isinstance(periodo, tuple) or len(periodo) != 2:
        comun.nota("Elige la fecha de inicio y la de fin del periodo en la barra lateral.", "alerta")
        st.stop()
    p_desde, p_hasta = periodo
    a_hasta = p_desde - timedelta(days=1)
    a_desde = a_hasta - timedelta(days=(p_hasta - p_desde).days)
duracion = (p_hasta - p_desde).days + 1
mes_completo = n_meses_periodo == 1
PRIMER_DATO = date(2025, 5, 1)
comparable = a_desde >= PRIMER_DATO  # si el periodo anterior cae antes de los datos, compararlo engañaría

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
    act = metricas.kpis_periodo(con, p_desde.isoformat(), p_hasta.isoformat())
    ant = metricas.kpis_periodo(con, a_desde.isoformat(), a_hasta.isoformat())
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

# ── 1. Lo primero que se mira: seis indicadores del periodo elegido ───────────────────────────────────────────────
def corta(d: date) -> str:
    return f"{d.day} {comun.MESES[d.month - 1][:3]} {d.year}"


if mes_completo:
    titulo = f"{comun.MESES[p_desde.month - 1]} de {p_desde.year} · frente a {comun.MESES[a_desde.month - 1]}"
elif n_meses_periodo:
    titulo = (f"{eleccion.lower()}: {corta(p_desde)} – {corta(p_hasta)} · frente a los {n_meses_periodo} meses anteriores"
              if n_meses_periodo < 12 else f"último año: {corta(p_desde)} – {corta(p_hasta)} · frente al año anterior")
else:
    titulo = f"{corta(p_desde)} – {corta(p_hasta)} · {duracion} días · frente a los {duracion} días anteriores"
if not comparable:  # los datos empiezan en mayo de 2025: no hay periodo anterior completo
    titulo = titulo.split(" · frente")[0] + " · sin periodo anterior completo para comparar (los datos empiezan en mayo de 2025)"
st.markdown(f"<div class='seccion'>{titulo}</div>", unsafe_allow_html=True)
if act["familias"] == 0:
    comun.nota("No hay familias en ese periodo. Elige otras fechas.", "alerta")
    st.stop()
provisional = not act["madura"]


def var(actual, anterior):
    """Variación frente al periodo anterior, o nada si no es comparable."""
    return actual - anterior if comparable else None


frente = {1: "frente al mes anterior", 12: "frente al año anterior"}.get(n_meses_periodo, "frente al periodo anterior")
fila = comun.Fila()
k = [fila] * 6
comun.kpi(k[0], "Piden ayuda", es(act["familias"], 0), "familias, sin duplicados",
          100 * (act["familias"] / ant["familias"] - 1) if comparable and ant["familias"] else None, unidad_tendencia=" %", icono="groups", frente=frente)
comun.kpi(k[1], "De noche", f"{es(act['noche'], 0)} %", "fuera del horario de atención",
          var(act["noche"], ant["noche"]), mejor_si_sube=False, icono="dark_mode", frente=frente)
comun.kpi(k[2], "Llamadas en < 1 h", f"{es(act['rapidas'], 0)} %", "objetivo: 50 %",
          var(act["rapidas"], ant["rapidas"]), alerta=act["rapidas"] < 25, icono="phone_in_talk", frente=frente)
comun.kpi(k[3], "Contratan", f"{es(act['conversion'])} %",
          "provisional: aún pueden contratar" if provisional else "en 30 días · objetivo: 15 %",
          None if provisional else var(act["conversion"], ant["conversion"]), icono="handshake", frente=frente)
comun.kpi(k[4], "Coste por familia", es(act["cac"], 0, " €"),
          "provisional: faltan contratos por llegar" if provisional else "CAC total del periodo",
          None if provisional else var(act["cac"], ant["cac"]), mejor_si_sube=False, unidad_tendencia=" €", icono="euro", frente=frente)
comun.kpi(k[5], "Siguen al año", f"{es(100 * r12, 0)} %", f"histórico · cada euro vuelve ×{es(ltv_cac)}", icono="favorite")
fila.pintar()
st.caption("Objetivos de ejemplo. Verde: mejora; naranja: empeora o está lejos del objetivo. "
           + ("Las familias de los últimos 30 días del periodo aún pueden contratar: conversión y coste son provisionales y no se "
              "comparan. " if provisional else "")
           + "La permanencia es histórica (hacen falta meses para medirla).")

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
comun.grafico(graficos.embudo_viaje(ETAPAS))
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
fila = comun.Fila()
c1 = c2 = c3 = fila
comun.kpi(c1, "Si la noche convirtiera como el día", f"+{es(extra_mes * 12, 0)}<small>familias al año</small>",
          f"de noche contrata el {es(100 * con_noche / n_noche)} %; de día, el {es(100 * con_dia / n_dia)} %", icono="trending_up")
comun.kpi(c2, "Margen que supondría", f"~{es(extra_mes * 12 * ltv_medio / 1000, 0)}<small>mil € al año</small>",
          f"valor medio de una familia en 12 meses: {es(ltv_medio, 0, ' €')} (margen supuesto del 30 %)", icono="payments")
comun.kpi(c3, "Tamaño del A/B", f"{es(n_grupo, 0)}<small>familias por grupo</small>",
          f"para ver la diferencia en llegada a la valoración ({es(100 * tasa_noche, 0)} % → {es(100 * tasa_dia, 0)} %)", icono="science")
fila.pintar()
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
