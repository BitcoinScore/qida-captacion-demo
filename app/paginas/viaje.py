import math
from datetime import date, timedelta

import streamlit as st

import comun
import detalles
import graficos
from comun import es
from motor import metricas

ULTIMO_DATO = date(2026, 11, 2)  # «hoy» en la demo: último día con datos
def meses_atras(d: date, n: int) -> date:
    """Primer día del mes que está n meses antes del mes de `d`."""
    total = d.year * 12 + d.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


# Días sueltos y semana: hasta hoy. Meses: meses naturales completos (el último, octubre); «Este mes», del 1 a hoy.
OPCIONES = {"Hoy": "hoy", "Ayer": "ayer", "Última semana": "semana", "Este mes": "mes_en_curso", "Último mes": 1,
            "Últimos 3 meses": 3, "Últimos 6 meses": 6, "Último año": 12, "Personalizado": None}
eleccion = st.sidebar.selectbox("Periodo de los indicadores", list(OPCIONES), index=list(OPCIONES).index("Último mes"),
                                help="Se compara con el periodo anterior equivalente: el día, la semana, los mismos días del "
                                     "mes anterior, o los meses anteriores.")
opcion = OPCIONES[eleccion]
n_meses_periodo = opcion if isinstance(opcion, int) else None
ultimo_mes_cerrado = ULTIMO_DATO.replace(day=1) - timedelta(days=1)
if opcion in ("hoy", "ayer", "semana"):
    p_hasta = ULTIMO_DATO - timedelta(days=1 if opcion == "ayer" else 0)
    p_desde = p_hasta - timedelta(days=6 if opcion == "semana" else 0)
    a_hasta = p_desde - timedelta(days=1)
    a_desde = a_hasta - (p_hasta - p_desde)
elif opcion == "mes_en_curso":
    p_desde, p_hasta = ULTIMO_DATO.replace(day=1), ULTIMO_DATO
    a_desde = meses_atras(p_desde, 1)
    a_hasta = a_desde + (p_hasta - p_desde)
elif n_meses_periodo:
    p_hasta = ultimo_mes_cerrado
    p_desde = meses_atras(p_hasta, n_meses_periodo - 1)
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

LIMITE_MADURO = date(2026, 9, 30)  # histórico maduro: meses completos con 30 días de margen (vista `cohorte`)
# Una sola definición en toda la pantalla: lo que hicieron las familias del periodo en sus 30 primeros días, contado hasta
# hoy. Si alguna entró hace menos de 30 días, el periodo está «en curso» (aún puede contratar) y se compara con el periodo
# anterior visto con la misma antigüedad (mismos días transcurridos desde su final).
corte_ant = ULTIMO_DATO - (p_desde - a_desde)
madura = (ULTIMO_DATO - p_hasta).days >= 30
inicio_plazo = ULTIMO_DATO - timedelta(days=29)  # quien entró desde este día aún no ha cumplido sus 30 días


def historico(con):
    """Todo el histórico maduro, por franja horaria, para el caso de negocio (un periodo corto daría un A/B con ruido)."""
    return {f: (n, val, alt) for f, n, val, alt in con.execute(
        """SELECT c.fuera_horario, COUNT(*), COUNT(v.lead_id), COUNT(a.lead_id) FROM cohorte c
           LEFT JOIN valoraciones_30d v ON v.lead_id = c.id LEFT JOIN altas_30d a ON a.lead_id = c.id
           GROUP BY c.fuera_horario""")}


@st.cache_data(show_spinner=False)
def calcular(p_desde, p_hasta, a_desde, a_hasta, corte_ant, inicio_plazo, madura, version_datos):
    """Todo lo que sale de la base para esta pantalla. En caché: pulsar una tarjeta no debe repetir las consultas ni los
    cálculos (`version_datos` invalida la caché si se regenera la base)."""
    with comun.conexion() as con:
        act = metricas.kpis_periodo(con, p_desde.isoformat(), p_hasta.isoformat())
        ant = metricas.kpis_periodo(con, a_desde.isoformat(), a_hasta.isoformat(), corte=corte_ant.isoformat())
        en_plazo = 0 if madura else metricas.kpis_periodo(con, max(p_desde, inicio_plazo).isoformat(), p_hasta.isoformat())["familias"]
        contactos = con.execute("SELECT COUNT(*) FROM leads WHERE date(fecha_entrada) BETWEEN ? AND ?",
                                (p_desde.isoformat(), p_hasta.isoformat())).fetchone()[0]
        franjas = historico(con)
        km = metricas.kaplan_meier(metricas.duraciones(con)).set_index("mes")["pct_siguen"]
        eco = metricas.economia_por_canal(con, comun.CIUDADES)
    return act, ant, en_plazo, contactos, franjas, km, eco


act, ant, en_plazo, contactos, franjas, km, eco = calcular(
    p_desde, p_hasta, a_desde, a_hasta, corte_ant, inicio_plazo, madura, comun.DB.stat().st_mtime)
n_meses = (LIMITE_MADURO.year - PRIMER_DATO.year) * 12 + LIMITE_MADURO.month - PRIMER_DATO.month + 1
for _desde, _hasta in ((p_desde, p_hasta), (a_desde, a_hasta)):  # precalienta las ventanas de detalle (en caché)
    detalles.familias(_desde, _hasta)  # ojo: una expresión suelta aquí la pintaría Streamlit en pantalla («magic»)
familias, contactadas, valoraciones, contratos = act["familias"], act["contactadas"], act["valoraciones"], act["contratos"]


def pct(a, b):
    return 100 * a / b if b else 0


r3, r12 = km[3] / 100, km[12] / 100
ltv_medio = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["contratos"].sum()
ltv_cac = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["gasto_total"].sum()
(n_dia, val_dia, con_dia), (n_noche, val_noche, con_noche) = franjas[0], franjas[1]
pct_noche = act["noche"]
tasa_dia, tasa_noche = val_dia / n_dia, val_noche / n_noche  # llegan a valoración

comun.cabecera("Viaje de la familia", "Con datos de ejemplo, la mayor fuga está entre la primera llamada y la valoración",
               "dirección y marketing",
               f"De cada 100 familias con las que habla un asesor/a familiar, solo {es(pct(valoraciones, contactadas), 0)} "
               f"llegan a la valoración. Y el {es(pct_noche, 0)} % pide ayuda cuando no hay nadie al teléfono.")

# ── 1. Lo primero que se mira: seis indicadores del periodo elegido ───────────────────────────────────────────────
def corta(d: date) -> str:
    return f"{d.day} {comun.MESES[d.month - 1][:3]} {d.year}"


DIA_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
if opcion in ("hoy", "ayer"):
    titulo = f"{eleccion.lower()}, {DIA_SEMANA[p_desde.weekday()]} {corta(p_desde)} · frente al día anterior"
elif opcion == "semana":
    titulo = f"última semana: {corta(p_desde)} – {corta(p_hasta)} · frente a los 7 días anteriores"
elif opcion == "mes_en_curso":
    titulo = (f"{comun.MESES[p_desde.month - 1]} hasta hoy: {corta(p_desde)} – {corta(p_hasta)} · frente a los mismos días "
              f"de {comun.MESES[a_desde.month - 1]}")
elif mes_completo:
    titulo = f"{comun.MESES[p_desde.month - 1]} de {p_desde.year} · frente a {comun.MESES[a_desde.month - 1]}"
elif n_meses_periodo:
    titulo = (f"{eleccion.lower()}: {corta(p_desde)} – {corta(p_hasta)} · frente a los {n_meses_periodo} meses anteriores"
              if n_meses_periodo < 12 else f"último año: {corta(p_desde)} – {corta(p_hasta)} · frente al año anterior")
else:  # periodo personalizado
    titulo = f"{corta(p_desde)} – {corta(p_hasta)} · frente al periodo anterior de la misma duración"
if not comparable:  # los datos empiezan en mayo de 2025: no hay periodo anterior completo
    titulo = titulo.split(" · frente")[0] + " · sin periodo anterior completo para comparar (los datos empiezan en mayo de 2025)"
st.markdown(f"<div class='seccion'>{titulo}</div>", unsafe_allow_html=True)
if act["familias"] == 0:
    comun.nota("No hay familias en ese periodo. Elige otras fechas.", "alerta")
    st.stop()
OBJ_LLAMADAS, OBJ_CONVERSION, OBJ_COSTE = 50, 15, 400  # objetivos de ejemplo


def var(actual, anterior):
    """Variación frente al periodo anterior, o nada si no es comparable."""
    return actual - anterior if comparable else None


def estado(valor, objetivo, mejor_si_sube=True):
    cumple = valor >= objetivo if mejor_si_sube else valor <= objetivo
    return ("bien", "cumple el objetivo") if cumple else ("mal", "por debajo del objetivo" if mejor_si_sube else "por encima del objetivo")


frente = {"hoy": "frente a ayer", "ayer": "frente al día anterior", "semana": "frente a la semana anterior",
          "mes_en_curso": "frente a los mismos días del mes anterior", 1: "frente al mes anterior",
          12: "frente al año anterior"}.get(opcion, "frente al periodo anterior")
fila = comun.Fila("viaje")
k = [fila] * 6
comun.kpi(k[0], "Piden ayuda", es(act["familias"], 0), "familias, sin duplicados",
          100 * (act["familias"] / ant["familias"] - 1) if comparable and ant["familias"] else None, unidad_tendencia=" %",
          icono="groups", frente=frente, detalle=lambda: detalles.piden_ayuda(p_desde, p_hasta, a_desde, a_hasta))
comun.kpi(k[1], "Piden ayuda de noche", f"{es(act['noche'], 0)} %", "fuera del horario de atención",
          var(act["noche"], ant["noche"]), mejor_si_sube=False, icono="dark_mode", frente=frente,
          detalle=lambda: detalles.noche(p_desde, p_hasta))
lejos = act["rapidas"] < OBJ_LLAMADAS / 2
e = estado(act["rapidas"], OBJ_LLAMADAS)
comun.kpi(k[2], "Llamadas en < 1 h", f"{es(act['rapidas'], 0)} %", f"objetivo: {OBJ_LLAMADAS} %",
          var(act["rapidas"], ant["rapidas"]), alerta=lejos, estado=e[0],
          texto_estado="muy lejos del objetivo" if lejos else e[1], icono="phone_in_talk", frente=frente,
          detalle=lambda: detalles.llamadas(p_desde, p_hasta))
# Contratan y coste: con el periodo en curso no se juzgan contra el objetivo (aún faltan contratos), pero se enseñan y se
# comparan con el periodo anterior a la misma altura
e = estado(act["conversion"], OBJ_CONVERSION) if madura else ("curso", "en curso")
comun.kpi(k[3], "Contratan", f"{es(act['conversion'])} %",
          f"{es(contratos, 0)} contratos · objetivo: {OBJ_CONVERSION} %" if madura else
          f"{es(contratos, 0)} contratos hasta hoy · {es(en_plazo, 0)} familias aún en plazo",
          var(act["conversion"], ant["conversion"]), estado=e[0], texto_estado=e[1], icono="handshake", frente=frente,
          detalle=lambda: detalles.contratan(p_desde, p_hasta))
hay_cac = contratos > 0 and not math.isnan(act["cac"])
if not hay_cac:
    e = (None, "")
elif madura:
    e = estado(act["cac"], OBJ_COSTE, mejor_si_sube=False)
else:
    e = ("curso", "en curso")
comun.kpi(k[4], "Coste por contrato", es(act["cac"], 0, " €") if hay_cac else "—",
          f"gasto ÷ contratos · objetivo: < {OBJ_COSTE} €" if hay_cac else "aún sin contratos en el periodo",
          var(act["cac"], ant["cac"]) if hay_cac and ant["contratos"] else None, mejor_si_sube=False, unidad_tendencia=" €",
          estado=e[0], texto_estado=e[1], icono="euro", frente=frente, detalle=lambda: detalles.coste(p_desde, p_hasta))
comun.kpi(k[5], "Siguen al año", f"{es(100 * r12, 0)} %", f"histórico · cada euro vuelve ×{es(ltv_cac)}", icono="favorite",
          detalle=detalles.siguen)
fila.pintar()
st.caption("Objetivos de ejemplo. Verde: cumple su objetivo; naranja: no lo cumple (con borde, si está muy lejos); negro: sin "
           "objetivo o «en curso», es decir, con familias que entraron hace menos de 30 días y aún pueden contratar. Las "
           "flechas comparan con el periodo anterior visto con la misma antigüedad, así un periodo reciente no sale peor solo "
           "por ser reciente. La permanencia es histórica.")

# ── 2. El embudo ───────────────────────────────────────────────────────────────────────────────────────────────
rango = corta(p_desde) if duracion == 1 else f"{corta(p_desde)} – {corta(p_hasta)}"
comun.titulo(f"Dónde se pierden las familias · {rango}")
if not madura:
    comun.nota(f"Las mismas {es(familias, 0)} familias de las tarjetas. {es(en_plazo, 0)} entraron hace menos de 30 días: el "
               "embudo cuenta lo que han hecho hasta hoy y aún crecerá.", "neutra")
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
# Cada etapa se puede pulsar: abre quién se queda en ella y por qué (la clave cambia tras abrir, para que no se reabra sola)
n_clic = st.session_state.setdefault("embudo_clic", 0)


@st.cache_data(show_spinner=False)
def embudo_en_cache(etapas):
    return graficos.embudo_viaje(etapas)


evento = st.plotly_chart(embudo_en_cache(ETAPAS), width="stretch", on_select="rerun", selection_mode="points",
                         key=f"embudo-{n_clic}", config={"displayModeBar": False, "scrollZoom": False})
puntos = evento.selection.points if evento and evento.selection else []
if puntos:
    st.session_state["embudo_clic"] = n_clic + 1
    detalles.etapa(int(puntos[0]["point_index"]), p_desde, p_hasta)
st.caption("Pulsa una etapa para ver quién se queda en ella y por qué. Cada paso cuenta si ocurre en los 30 días siguientes a "
           "pedir ayuda (o hasta hoy, si aún no han pasado). Las dos "
           "últimas etapas (trazo discontinuo) son estimaciones con la curva de permanencia histórica.")

# ── 3. El viaje, etapa a etapa (service blueprint) ────────────────────────────────────────────────────────────
comun.titulo("El viaje, etapa a etapa")
ETAPAS_VIAJE = [
    ("Nos descubre", es(familias, 0),
     "Busca «cuidadora para mi madre» o ve un anuncio en Instagram", "Google Ads, Meta por ciudad, blog y prescriptores",
     "Atribuir cada contrato a su canal", "Coste de captar una familia y lo que vale", "Ve el anuncio de Valencia a las 22:50"),
    ("Pide ayuda", f"{es(pct_noche, 0)} % de noche",
     "Deja sus datos o busca con quién hablar, a menudo de noche", "Formulario de 3 campos; teléfono de 9:00 a 20:00",
     "Asistente de noche que deja la llamada agendada", "Familias de noche que llegan a la valoración",
     "A las 23:10, el asistente le contesta"),
    ("Primera llamada", f"{es(pct(valoraciones, contactadas), 0)} % sigue",
     "Espera la llamada; si tarda, prueba con otra empresa", "Asesor/a familiar, en menos de 24 h",
     "Cola con urgentes primero y después por probabilidad", "Llamadas en menos de 1 h", "Primera llamada del día, a las 9:05"),
    ("Valoración", f"{es(pct(contratos, valoraciones), 0)} % firma",
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
<tr><th style="background:transparent;border:0"><span style="position:absolute;left:-9999px">Fila</span></th>{cabecera}</tr>{cuerpo}</table></div>
""",
    unsafe_allow_html=True,
)

# ── 4. Caso de negocio y cómo se probaría ────────────────────────────────────────────────────────────────────────
comun.titulo("Qué valdría arreglar la noche, y cómo lo probaría")
st.caption("Con todo el histórico maduro (mayo de 2025 – septiembre de 2026), no con el periodo elegido: un solo mes daría "
           "una estimación con demasiado ruido.")
noche_mes = n_noche / n_meses
extra_mes = noche_mes * (con_dia / n_dia - con_noche / n_noche)
# Tamaño del A/B: familias de noche por grupo para detectar la diferencia de llegada a valoración (95 %, potencia 80 %)
d = tasa_dia - tasa_noche
n_grupo = math.ceil((1.959964 + 0.841621) ** 2 * (tasa_dia * (1 - tasa_dia) + tasa_noche * (1 - tasa_noche)) / d ** 2)
fila = comun.Fila()
c1 = c2 = c3 = fila
comun.kpi(c1, "Si la noche convirtiera como el día", f"+{es(extra_mes * 12, 0)}<small>familias al año</small>",
          f"de noche contrata el {es(100 * con_noche / n_noche)} %; de día, el {es(100 * con_dia / n_dia)} %", icono="trending_up",
          detalle=lambda: detalles.negocio_extra(noche_mes, con_noche / n_noche, con_dia / n_dia))
comun.kpi(c2, "Margen que supondría", f"~{es(extra_mes * 12 * ltv_medio / 1000, 0)}<small>mil € al año</small>",
          f"valor medio de una familia en 12 meses: {es(ltv_medio, 0, ' €')} (margen supuesto del 30 %)", icono="payments",
          detalle=lambda: detalles.negocio_margen(extra_mes, ltv_medio))
comun.kpi(c3, "Tamaño del A/B", f"{es(n_grupo, 0)}<small>familias por grupo</small>",
          f"para ver la diferencia en llegada a la valoración ({es(100 * tasa_noche, 0)} % → {es(100 * tasa_dia, 0)} %): "
          f"unos {es(2 * n_grupo / noche_mes, 0)} meses con todas las ciudades", icono="science",
          detalle=lambda: detalles.negocio_ab(tasa_noche, tasa_dia, noche_mes))
fila.pintar()
comun.nota("**Cómo lo probaría, en dos pasos:** (1) **¿funciona el mecanismo?** Entre las familias de noche, casi ninguna recibe "
           "llamada en la primera hora; con el asistente debería recibirla la mayoría. Basta con unas decenas de familias por "
           "grupo, en días. (2) **¿cambia el resultado?** Asistente sí/no por semanas alternas con **todas las ciudades** "
           "(una sola ciudad tardaría años). Detectar la mejora completa (de noche como de día) exige miles de familias; una "
           "mejora de 8 puntos, unos 3-4 meses. Métrica principal: llegada a la valoración en 30 días; de control: coste de "
           "captar una familia y permanencia a 3 meses. Es una hipótesis: que la noche convierta peor es una asociación en los "
           "datos, no una causa probada.", "neutra")

with st.expander("Cómo se mide (definiciones)"):
    st.markdown(
        f"""
- **Familias, no contactos:** {es(contactos, 0)} contactos del CRM corresponden a {es(familias, 0)} familias; las que entraron por
  dos canales se unen por teléfono. **Atribución:** último contacto antes del resultado.
- **Periodo en curso:** si alguna familia del periodo entró hace menos de 30 días, aún puede avanzar. Tarjetas y embudo cuentan
  lo ocurrido hasta hoy y se comparan con el periodo anterior visto con la misma antigüedad; el objetivo se juzga al cerrar.
- **Caso de negocio:** con todo el histórico maduro (mayo de 2025 – septiembre de 2026), para que el A/B no dependa del periodo elegido.
- **Ventana de conversión:** cada paso cuenta si ocurre en los 30 días siguientes a pedir ayuda.
- **Siguen a 3 y 12 meses (estimado):** contratos × permanencia de Kaplan-Meier ({es(100 * r3, 0)} % y {es(100 * r12, 0)} %).
- **Retorno del conjunto:** valor de 12 meses de todos los contratos ÷ gasto total (margen bruto supuesto del 30 %).
"""
    )
