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

# Conversión y coste solo con familias que ya han tenido 30 días para contratar (la parte madura del periodo)
LIMITE_MADURO = ULTIMO_DATO - timedelta(days=31)  # 30 sep: igual que la vista `cohorte`
maduro_hasta = min(p_hasta, LIMITE_MADURO)
hay_maduro = (maduro_hasta - p_desde).days + 1 >= min(7, duracion)  # al menos una semana madura
# El embudo usa la parte madura del periodo; si no la hay (p. ej. octubre), el último tramo maduro de la misma duración
if hay_maduro:
    e_desde, e_hasta, embudo_propio = p_desde, maduro_hasta, True
else:
    e_desde, e_hasta, embudo_propio = (meses_atras(p_desde, n_meses_periodo) if n_meses_periodo else
                                       LIMITE_MADURO - timedelta(days=duracion - 1)), LIMITE_MADURO, False


def embudo(con, desde: date, hasta: date):
    """Familias que pidieron ayuda entre `desde` y `hasta` y qué hicieron en sus 30 días, total y por franja horaria."""
    rango = (desde.isoformat(), hasta.isoformat())
    base = """FROM cohorte c
           LEFT JOIN llamadas_30d ll    ON ll.lead_id = c.id
           LEFT JOIN valoraciones_30d v ON v.lead_id = c.id
           LEFT JOIN altas_30d a        ON a.lead_id = c.id
           WHERE date(c.fecha_entrada) BETWEEN ? AND ?"""
    total = con.execute(f"SELECT COUNT(*), COUNT(ll.lead_id), COUNT(v.lead_id), COUNT(a.lead_id), SUM(c.contactos) {base}",
                        rango).fetchone()
    franjas = {f: (n, val, alt) for f, n, val, alt in con.execute(
        f"SELECT c.fuera_horario, COUNT(*), COUNT(v.lead_id), COUNT(a.lead_id) {base} GROUP BY c.fuera_horario", rango)}
    return total, franjas


with comun.conexion() as con:
    (familias, contactadas, valoraciones, contratos, contactos), franjas_e = embudo(con, e_desde, e_hasta)
    # El caso de negocio usa todo el histórico maduro: con un mes solo, el tamaño del A/B saldría con mucho ruido
    _, franjas = embudo(con, PRIMER_DATO, LIMITE_MADURO)
    n_meses = (LIMITE_MADURO.year - PRIMER_DATO.year) * 12 + LIMITE_MADURO.month - PRIMER_DATO.month + 1
    km = metricas.kaplan_meier(metricas.duraciones(con)).set_index("mes")["pct_siguen"]
    act = metricas.kpis_periodo(con, p_desde.isoformat(), p_hasta.isoformat())
    ant = metricas.kpis_periodo(con, a_desde.isoformat(), a_hasta.isoformat())
    if hay_maduro:
        act_m = metricas.kpis_periodo(con, p_desde.isoformat(), maduro_hasta.isoformat())
        ant_m = metricas.kpis_periodo(con, a_desde.isoformat(), (a_desde + (maduro_hasta - p_desde)).isoformat())
    eco = metricas.economia_por_canal(con, comun.CIUDADES)
r3, r12 = km[3] / 100, km[12] / 100
ltv_medio = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["contratos"].sum()
ltv_cac = (eco["ltv_12m"] * eco["contratos"]).sum() / eco["gasto_total"].sum()
(n_dia, val_dia, con_dia), (n_noche, val_noche, con_noche) = franjas[0], franjas[1]
pct_noche = 100 * franjas_e.get(1, (0,))[0] / familias if familias else 0  # del tramo del embudo
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
provisional = not hay_maduro          # ninguna familia del periodo ha tenido aún 30 días para contratar
parcial = hay_maduro and maduro_hasta < p_hasta
OBJ_LLAMADAS, OBJ_CONVERSION, OBJ_COSTE = 50, 15, 400  # objetivos de ejemplo


def var(actual, anterior):
    """Variación frente al periodo anterior, o nada si no es comparable."""
    return actual - anterior if comparable else None


def estado(valor, objetivo, mejor_si_sube=True):
    cumple = valor >= objetivo if mejor_si_sube else valor <= objetivo
    return ("bien", "cumple el objetivo") if cumple else ("mal", "por debajo del objetivo" if mejor_si_sube else "por encima del objetivo")


frente = {1: "frente al mes anterior", 12: "frente al año anterior"}.get(n_meses_periodo, "frente al periodo anterior")
fila = comun.Fila()
k = [fila] * 6
comun.kpi(k[0], "Piden ayuda", es(act["familias"], 0), "familias, sin duplicados",
          100 * (act["familias"] / ant["familias"] - 1) if comparable and ant["familias"] else None, unidad_tendencia=" %",
          icono="groups", frente=frente)
comun.kpi(k[1], "De noche", f"{es(act['noche'], 0)} %", "fuera del horario de atención",
          var(act["noche"], ant["noche"]), mejor_si_sube=False, icono="dark_mode", frente=frente)
e = estado(act["rapidas"], OBJ_LLAMADAS)
comun.kpi(k[2], "Llamadas en < 1 h", f"{es(act['rapidas'], 0)} %", f"objetivo: {OBJ_LLAMADAS} %",
          var(act["rapidas"], ant["rapidas"]), alerta=act["rapidas"] < OBJ_LLAMADAS / 2, estado=e[0],
          texto_estado="muy lejos del objetivo" if act["rapidas"] < OBJ_LLAMADAS / 2 else e[1],
          icono="phone_in_talk", frente=frente)
nota_maduro = (f"familias hasta el {maduro_hasta.day} {comun.MESES[maduro_hasta.month - 1][:3]} (las demás aún pueden contratar)"
               if parcial else "en 30 días")
if provisional:
    comun.kpi(k[3], "Contratan", f"{es(act['conversion'])} %", "aún pueden contratar: no se compara", estado="provisional",
              texto_estado="provisional", icono="handshake")
    comun.kpi(k[4], "Coste por familia", es(act["cac"], 0, " €"), "faltan contratos por llegar: no se compara",
              estado="provisional", texto_estado="provisional", icono="euro")
else:
    e = estado(act_m["conversion"], OBJ_CONVERSION)
    comun.kpi(k[3], "Contratan", f"{es(act_m['conversion'])} %", f"{nota_maduro} · objetivo: {OBJ_CONVERSION} %",
              var(act_m["conversion"], ant_m["conversion"]), estado=e[0], texto_estado=e[1], icono="handshake", frente=frente)
    e = estado(act_m["cac"], OBJ_COSTE, mejor_si_sube=False)
    comun.kpi(k[4], "Coste por familia", es(act_m["cac"], 0, " €"), f"CAC total · objetivo: menos de {OBJ_COSTE} €",
              var(act_m["cac"], ant_m["cac"]), mejor_si_sube=False, unidad_tendencia=" €", estado=e[0], texto_estado=e[1],
              icono="euro", frente=frente)
comun.kpi(k[5], "Siguen al año", f"{es(100 * r12, 0)} %", f"histórico · cada euro vuelve ×{es(ltv_cac)}", icono="favorite")
fila.pintar()
st.caption("Objetivos de ejemplo. Color de la cifra: verde = cumple su objetivo; naranja = no lo cumple (con borde, si está muy "
           "lejos); gris = provisional; negro = sin objetivo. Flechas: frente al periodo anterior (verde mejora, naranja empeora). "
           + ("Contratan y coste: solo con las familias que ya han tenido 30 días para contratar. " if parcial else "")
           + "La permanencia es histórica (hacen falta meses para medirla).")

# ── 2. El embudo ───────────────────────────────────────────────────────────────────────────────────────────────
st.markdown(f"#### Dónde se pierden las familias · {e_desde.day} {comun.MESES[e_desde.month - 1][:3]} – "
            f"{e_hasta.day} {comun.MESES[e_hasta.month - 1][:3]} {e_hasta.year}")
fuera = act["familias"] - familias  # familias del periodo que aún no han tenido 30 días para contratar
if not embudo_propio:
    comun.nota(f"Las {es(act['familias'], 0)} familias del periodo elegido aún no han tenido 30 días para contratar, así que "
               f"el embudo enseña el tramo anterior completo: {es(familias, 0)} familias.", "neutra")
elif fuera > 0:
    comun.nota(f"De las {es(act['familias'], 0)} familias que piden ayuda en el periodo, el embudo sigue a las {es(familias, 0)} "
               f"que ya han tenido 30 días para contratar. Las {es(fuera, 0)} que entraron después del {e_hasta.day} "
               f"{comun.MESES[e_hasta.month - 1][:3]} aún están en camino.", "neutra")
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
st.caption("Cada paso cuenta si ocurre en los 30 días siguientes a pedir ayuda. Las dos últimas etapas (trazo discontinuo) "
           "son estimaciones con la curva de permanencia.")

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
st.caption("Con todo el histórico maduro (mayo de 2025 – septiembre de 2026), no con el periodo elegido: un solo mes daría "
           "una estimación con demasiado ruido.")
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
- **Cohorte madura:** el embudo, la conversión y el coste solo cuentan familias que entraron hasta el 30 de septiembre de 2026;
  las posteriores aún no han tenido 30 días para contratar.
- **Caso de negocio:** con todo el histórico maduro (mayo de 2025 – septiembre de 2026), para que el A/B no dependa del periodo elegido.
- **Ventana de conversión:** cada paso cuenta si ocurre en los 30 días siguientes a pedir ayuda.
- **Siguen a 3 y 12 meses (estimado):** contratos × permanencia de Kaplan-Meier ({es(100 * r3, 0)} % y {es(100 * r12, 0)} %).
- **Retorno del conjunto:** valor de 12 meses de todos los contratos ÷ gasto total (margen bruto supuesto del 30 %).
"""
    )
