"""Ventanas de detalle del Viaje de la familia: al pulsar una tarjeta o una etapa del embudo, el porqué de la cifra
(desgloses) y el listado de las familias que hay detrás. Mismo periodo y misma definición que la pantalla."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun
import graficos
from comun import es

NOMBRES = ["Lucía", "Javier", "Carmen", "Antonio", "Marta", "Pablo", "Elena", "Jorge", "Rosa", "Miguel", "Ana", "David",
           "Pilar", "Sergio", "Laura", "Andrés", "Isabel", "Raúl", "Nuria", "Tomás", "Silvia", "Óscar", "Teresa"]
INICIALES = "ABCDFGHLMNPRSTV"
HOY = date(2026, 11, 2)  # «hoy» en la demo
OBJ_LLAMADAS, OBJ_COSTE = 50, 400


def nombre_ficticio(i: int) -> str:
    return f"{NOMBRES[i % len(NOMBRES)]} {INICIALES[(i // len(NOMBRES)) % len(INICIALES)]}."


@st.cache_data(show_spinner=False)
def familias(desde: date, hasta: date) -> pd.DataFrame:
    """Una fila por familia que pidió ayuda en el periodo, con lo que ha hecho en sus 30 primeros días (hasta hoy)."""
    with comun.conexion() as con:
        df = pd.read_sql(
            """SELECT f.id, f.fecha_entrada, f.canal, f.ciudad, f.servicio, f.urgencia, f.fuera_horario,
                      ll.fecha_primera_llamada AS llamada, v.fecha AS valoracion, a.fecha_alta AS alta, a.ingreso_mes
               FROM familias f
               LEFT JOIN llamadas_30d ll    ON ll.lead_id = f.id
               LEFT JOIN valoraciones_30d v ON v.lead_id = f.id
               LEFT JOIN altas_30d a        ON a.lead_id = f.id
               WHERE date(f.fecha_entrada) BETWEEN ? AND ?""", con, params=[desde.isoformat(), hasta.isoformat()])
    for c in ("fecha_entrada", "llamada", "valoracion", "alta"):
        df[c] = pd.to_datetime(df[c])
    df["familia"] = df["id"].map(nombre_ficticio)
    df["franja"] = df["fuera_horario"].map({1: "Noche", 0: "Día"})
    df["espera_h"] = (df["llamada"] - df["fecha_entrada"]).dt.total_seconds() / 3600
    df["en_plazo"] = (pd.Timestamp(HOY) - df["fecha_entrada"].dt.normalize()).dt.days < 30

    def estado(f) -> str:
        if pd.notna(f["alta"]):
            return "Contrata"
        if pd.notna(f["valoracion"]):
            return "Valoración, sin firmar aún" if f["en_plazo"] else "Valoración, no firma"
        if pd.notna(f["llamada"]):
            return "Habló, sin valoración aún" if f["en_plazo"] else "Habló, sin valoración"
        return "Sin hablar todavía" if f["en_plazo"] else "Nunca se le localizó"

    df["estado"] = df.apply(estado, axis=1)
    return df.sort_values("fecha_entrada", ascending=False)


def listado(df: pd.DataFrame, titulo: str, columnas: list[str] | None = None) -> None:
    """Las familias que hay detrás de la cifra, con buscador y orden (nombres ficticios)."""
    st.markdown(f"##### {titulo} · {es(len(df), 0)} familias")
    if df.empty:
        st.caption("Ninguna en este periodo.")
        return
    vista = pd.DataFrame({
        "Familia": df["familia"], "Entró": df["fecha_entrada"], "Canal": df["canal"], "Ciudad": df["ciudad"],
        "Servicio": df["servicio"], "Franja": df["franja"], "Urgente": df["urgencia"].map({1: "Sí", 0: ""}),
        "Espera": df["espera_h"], "Estado": df["estado"], "€/mes": df["ingreso_mes"],
    })
    if columnas:
        vista = vista[columnas]
    # Formato español sin perder el orden numérico: el Styler solo cambia cómo se ve
    formato = {"Entró": lambda d: d.strftime("%d/%m/%Y %H:%M"),
               "Espera": lambda v: "" if pd.isna(v) else es(v, 1, " h"),
               "€/mes": lambda v: "" if pd.isna(v) else es(v, 0, " €")}
    st.dataframe(vista.style.format({k: f for k, f in formato.items() if k in vista.columns}, na_rep=""), hide_index=True,
                 width="stretch", height=min(38 + 35 * len(vista), 320))
    st.caption("Nombres ficticios. Pulsa la cabecera de una columna para ordenar; la lupa de la tabla busca.")


def barras_h(etiquetas, valores, textos, alto=None, color=None, referencia=None, sufijo=" %") -> go.Figure:
    fig = go.Figure(go.Bar(y=list(etiquetas), x=list(valores), orientation="h", text=list(textos), textposition="outside",
                           cliponaxis=False, marker_color=color or graficos.ACENTO, hoverinfo="skip"))
    if referencia is not None:
        fig.add_vline(x=referencia, line=dict(color=graficos.AVISO, dash="dash", width=2), layer="below")
    fig.update_layout(showlegend=False, xaxis=dict(visible=False, range=[0, max(list(valores) + [referencia or 0, 1]) * 1.35]),
                      yaxis=dict(autorange="reversed"), bargap=0.35)
    return graficos._limpio(fig, alto or 50 + 34 * len(list(etiquetas)))


def tasa_por(df: pd.DataFrame, grupo: str, paso: pd.Series) -> pd.DataFrame:
    t = df.assign(paso=paso).groupby(grupo).agg(n=("id", "size"), si=("paso", "sum")).reset_index()
    t["pct"] = 100 * t["si"] / t["n"]
    return t.sort_values("pct", ascending=False)


def periodo_txt(desde: date, hasta: date) -> str:
    c = lambda d: f"{d.day} {comun.MESES[d.month - 1][:3]} {d.year}"
    return c(desde) if desde == hasta else f"{c(desde)} – {c(hasta)}"


# ── Piden ayuda ────────────────────────────────────────────────────────────────────────────────────────────────
@st.dialog("Piden ayuda", width="large")
def piden_ayuda(desde: date, hasta: date, a_desde: date, a_hasta: date) -> None:
    df, ant = familias(desde, hasta), familias(a_desde, a_hasta)
    st.caption(f"{periodo_txt(desde, hasta)} · familias sin duplicados (dos contactos con el mismo teléfono son una familia)")
    if (hasta - desde).days <= 1:  # un día: por horas
        actual = df.groupby(df["fecha_entrada"].dt.hour).size().reindex(range(24), fill_value=0)
        previo = ant.groupby(ant["fecha_entrada"].dt.hour).size().reindex(range(24), fill_value=0)
        eje, titulo_eje = [f"{h}:00" for h in range(24)], "hora"
    else:
        dias = pd.date_range(desde, hasta)
        actual = df.groupby(df["fecha_entrada"].dt.normalize()).size().reindex(dias, fill_value=0)
        previo = ant.groupby(ant["fecha_entrada"].dt.normalize()).size()
        previo = previo.reindex(pd.date_range(a_desde, a_hasta), fill_value=0).iloc[:len(dias)]
        eje, titulo_eje = [f"{d.day}/{d.month}" for d in dias], "día"
    fig = go.Figure()
    fig.add_bar(x=eje, y=actual.values, name="Este periodo", marker_color=graficos.ACENTO)
    fig.add_scatter(x=eje[:len(previo)], y=previo.values, name="Periodo anterior", mode="lines",
                    line=dict(color=graficos.NEUTRO, width=2, dash="dot"))
    fig.update_layout(legend=dict(orientation="h", y=1.12), xaxis=dict(type="category", title=None),
                      yaxis=dict(title=f"familias por {titulo_eje}"))
    st.markdown("##### Cuándo llegan")
    comun.grafico(graficos._limpio(fig, 280))
    por = df.groupby("canal").size().rename("n").to_frame().join(ant.groupby("canal").size().rename("ant")).fillna(0)
    por = por.sort_values("n", ascending=False)
    textos = [f"{es(n, 0)}" + (f"  ({'▲' if n >= a else '▼'} {es(abs(100 * (n / a - 1)), 0)} %)" if a else "")
              for n, a in zip(por["n"], por["ant"])]
    st.markdown("##### Por qué canal llegan (y cambio frente al periodo anterior)")
    comun.grafico(barras_h(por.index, por["n"], textos, sufijo=""))
    listado(df, "Todas las familias del periodo")


# ── Llamadas en menos de 1 h ──────────────────────────────────────────────────────────────────────────────────
@st.dialog("Llamadas en menos de 1 h", width="large")
def llamadas(desde: date, hasta: date) -> None:
    df = familias(desde, hasta)
    con_llamada = df[df["llamada"].notna()]
    st.caption(f"{periodo_txt(desde, hasta)} · de las familias a las que ya se ha llamado, cuántas recibieron la llamada en "
               f"menos de una hora · objetivo: {OBJ_LLAMADAS} %")
    if con_llamada.empty:
        comun.nota("Aún no se ha llamado a ninguna familia de este periodo.", "neutra")
        return
    rap = lambda d: 100 * (d["espera_h"] < 1).mean() if len(d) else 0
    dia, noche = con_llamada[con_llamada["franja"] == "Día"], con_llamada[con_llamada["franja"] == "Noche"]
    fila = comun.Fila()
    comun.kpi(fila, "De día", f"{es(rap(dia), 0)} %", f"{es(len(dia), 0)} familias llamadas", icono="light_mode")
    comun.kpi(fila, "De noche", f"{es(rap(noche), 0)} %", f"{es(len(noche), 0)} familias llamadas", icono="dark_mode",
              alerta=rap(noche) < OBJ_LLAMADAS / 2)
    comun.kpi(fila, "Espera mediana de noche", es(noche["espera_h"].median() if len(noche) else 0, 1, " h"),
              f"de día: {es(dia['espera_h'].median() if len(dia) else 0, 1, ' h')}", icono="schedule")
    fila.pintar()
    por_hora = con_llamada.groupby(con_llamada["fecha_entrada"].dt.hour).apply(rap).reindex(range(24))
    fig = go.Figure(go.Bar(x=[f"{h}:00" for h in range(24)], y=por_hora.values,
                           marker_color=[graficos.ACENTO if 9 <= h < 20 else graficos.AVISO for h in range(24)],
                           hovertemplate="%{x}: %{y:.0f} %<extra></extra>"))
    fig.add_hline(y=OBJ_LLAMADAS, line=dict(color=graficos.GRIS, dash="dash"), annotation_text="objetivo 50 %",
                  annotation_position="top left")
    fig.update_layout(xaxis=dict(type="category"), yaxis=dict(range=[0, 100], ticksuffix=" %", title=None))
    st.markdown("##### Según la hora a la que piden ayuda (naranja: fuera de horario)")
    comun.grafico(graficos._limpio(fig, 260))
    comun.nota("Quien escribe fuera de horario espera a la mañana: ahí se pierde la cifra. El asistente de noche y la cola "
               "priorizada atacan justo esa franja.")
    st.page_link("paginas/primera_llamada.py", label="Ver la cola de llamadas de esta mañana", icon=":material/call:")
    listado(con_llamada.sort_values("espera_h", ascending=False), "Familias llamadas, de más a menos espera",
            ["Familia", "Entró", "Franja", "Espera", "Canal", "Ciudad", "Urgente", "Estado"])


# ── Contratan ───────────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def curva_maduracion() -> pd.Series:
    """% acumulado de familias que contratan según los días desde que piden ayuda (histórico maduro, 6 meses)."""
    with comun.conexion() as con:
        d = pd.read_sql("""SELECT julianday(a.fecha_alta) - julianday(c.fecha_entrada) AS dias FROM cohorte c
                           LEFT JOIN altas_30d a ON a.lead_id = c.id WHERE c.fecha_entrada >= '2026-04-01'""", con)["dias"]
    return pd.Series([100 * (d <= x).sum() / len(d) for x in range(31)], index=range(31))


@st.dialog("Contratan", width="large")
def contratan(desde: date, hasta: date) -> None:
    df = familias(desde, hasta)
    conv = 100 * df["alta"].notna().mean() if len(df) else 0
    en_plazo = int(df["en_plazo"].sum())
    st.caption(f"{periodo_txt(desde, hasta)} · familias que contratan en sus 30 primeros días: {es(conv)} % "
               f"({es(int(df['alta'].notna().sum()), 0)} de {es(len(df), 0)})")
    t = tasa_por(df, "canal", df["alta"].notna())
    st.markdown("##### Por canal")
    comun.grafico(barras_h(t["canal"], t["pct"], [f"{es(p)} %  ({es(s, 0)} de {es(n, 0)})" for p, s, n in
                                                     zip(t["pct"], t["si"], t["n"])]))
    curva = curva_maduracion()
    fig = go.Figure(go.Scatter(x=curva.index, y=curva.values, mode="lines", line=dict(color=graficos.ACENTO, width=3),
                               hovertemplate="día %{x}: %{y:.1f} %<extra></extra>"))
    if en_plazo:
        edad = int(((pd.Timestamp(HOY) - df["fecha_entrada"].dt.normalize()).dt.days.clip(upper=30)).mean())
        visto = 100 * curva[edad] / curva[30]
        fig.add_vline(x=edad, line=dict(color=graficos.AVISO, dash="dash"),
                      annotation_text=f"este periodo: {edad} días de media", annotation_position="top right")
        comun.nota(f"**En curso:** {es(en_plazo, 0)} familias aún no han cumplido 30 días. A los {edad} días de media se suele "
                   f"haber visto el {es(visto, 0)} % de los contratos que llegarán: la cifra aún subirá.", "neutra")
    fig.update_layout(xaxis=dict(title="días desde que piden ayuda"), yaxis=dict(title="contratan (acumulado)", ticksuffix=" %"))
    st.markdown("##### Cuándo llegan los contratos (histórico de los últimos 6 meses cerrados)")
    comun.grafico(graficos._limpio(fig, 260))
    listado(df[df["alta"].notna()].sort_values("alta", ascending=False), "Familias que contratan",
            ["Familia", "Entró", "Canal", "Ciudad", "Servicio", "Urgente", "€/mes"])


# ── Coste por contrato ─────────────────────────────────────────────────────────────────────────────────────────
@st.dialog("Coste por contrato", width="large")
def coste(desde: date, hasta: date) -> None:
    df = familias(desde, hasta)
    with comun.conexion() as con:
        g = pd.read_sql("SELECT mes, canal, SUM(importe) AS importe FROM gasto GROUP BY mes, canal", con)
    d0, d1 = pd.Timestamp(desde), pd.Timestamp(hasta)
    ini = pd.to_datetime(g["mes"] + "-01")
    fin = ini + pd.offsets.MonthEnd(0)
    solape = (pd.concat([fin, pd.Series(d1, index=g.index)], axis=1).min(axis=1)
              - pd.concat([ini, pd.Series(d0, index=g.index)], axis=1).max(axis=1)).dt.days + 1
    g["gasto"] = g["importe"] * solape.clip(lower=0) / ((fin - ini).dt.days + 1)
    t = g.groupby("canal")["gasto"].sum().to_frame().join(df[df["alta"].notna()].groupby("canal").size().rename("contratos"))
    t = t.fillna(0)
    t = t[t["gasto"] > 0]
    t["coste"] = t["gasto"] / t["contratos"].where(t["contratos"] > 0)
    st.caption(f"{periodo_txt(desde, hasta)} · gasto del periodo (medios, equipo y acuerdos, repartido por días) ÷ contratos "
               f"de sus familias · objetivo: menos de {OBJ_COSTE} €")
    con_coste = t.dropna(subset=["coste"]).sort_values("coste")
    if not con_coste.empty:
        st.markdown("##### Por canal")
        colores = [graficos.ACENTO if c <= OBJ_COSTE else graficos.AVISO for c in con_coste["coste"]]
        comun.grafico(barras_h(con_coste.index, con_coste["coste"],
                               [f"{es(c, 0)} €  ({es(n, 0)} contratos)" for c, n in zip(con_coste["coste"], con_coste["contratos"])],
                               color=colores, referencia=OBJ_COSTE))
    sin = t[t["contratos"] == 0]
    if not sin.empty:
        st.caption("Sin contratos aún (gasto sin repartir): " + ", ".join(f"{c} ({es(v, 0)} €)" for c, v in sin["gasto"].items()))
    tabla = t.assign(Gasto=t["gasto"].round(0), Contratos=t["contratos"].astype(int), Coste=t["coste"].round(0))
    tabla = tabla[["Gasto", "Contratos", "Coste"]].rename(columns={"Coste": "Coste por contrato"})
    tabla = tabla.rename_axis("Canal").sort_values("Gasto", ascending=False)
    euros = lambda v: "—" if pd.isna(v) else es(v, 0, " €")
    st.dataframe(tabla.style.format({"Gasto": euros, "Coste por contrato": euros}), width="stretch")
    st.page_link("paginas/descubre.py", label="Ver qué canal compensa (con lo que vale cada contrato)", icon=":material/campaign:")
    listado(df[df["alta"].notna()].sort_values("alta", ascending=False), "Contratos del periodo",
            ["Familia", "Entró", "Canal", "Ciudad", "Servicio", "€/mes"])


# ── Etapas del embudo ───────────────────────────────────────────────────────────────────────────────────────────
PASOS = [  # (etapa pulsada, siguiente, columna que marca haber llegado a la siguiente, columna de inicio del tiempo)
    ("Piden ayuda", "Hablan con su asesor/a", "llamada", "fecha_entrada"),
    ("Hablan con su asesor/a", "Valoración", "valoracion", "llamada"),
    ("Valoración", "Contratan", "alta", "valoracion"),
]


@st.dialog("Etapa del embudo", width="large")
def etapa(k: int, desde: date, hasta: date) -> None:
    df = familias(desde, hasta)
    if k >= len(PASOS):
        st.markdown("#### Contratan → siguen a los 3 y 12 meses")
        comun.nota("La permanencia se estima con la curva histórica (Kaplan-Meier): hacen falta meses para medirla en un "
                   "periodo concreto. El detalle por canal está en Retención.", "neutra")
        st.page_link("paginas/se_queda.py", label="Ver Retención", icon=":material/favorite:")
        listado(df[df["alta"].notna()], "Familias que contratan", ["Familia", "Entró", "Canal", "Ciudad", "Servicio", "€/mes"])
        return
    origen, destino, col, inicio = PASOS[k]
    base = df if k == 0 else df[df[PASOS[k - 1][2]].notna()]
    llega = base[col].notna()
    st.markdown(f"#### {origen} → {destino}")
    st.caption(f"{periodo_txt(desde, hasta)} · de {es(len(base), 0)} familias, {es(int(llega.sum()), 0)} pasan "
               f"({es(100 * llega.mean() if len(base) else 0)} %) y {es(int((~llega).sum()), 0)} se quedan aquí")
    if base.empty:
        return
    tiempo = (base.loc[llega, col] - base.loc[llega, inicio]).dt.total_seconds()
    if len(tiempo):
        mediana = tiempo.median()
        st.markdown(f"Tiempo mediano hasta {destino.lower()}: **{es(mediana / 3600, 1, ' h') if mediana < 172800 else es(mediana / 86400, 1, ' días')}**")
    pestañas = st.tabs(["Por canal", "Por ciudad", "De día o de noche", "Por servicio"])
    for pestaña, grupo in zip(pestañas, ["canal", "ciudad", "franja", "servicio"]):
        with pestaña:
            t = tasa_por(base, grupo, llega)
            comun.grafico(barras_h(t[grupo], t["pct"], [f"{es(p)} %  ({es(s, 0)} de {es(n, 0)})"
                                                        for p, s, n in zip(t["pct"], t["si"], t["n"])]))
    perdidas = base[~llega]
    if perdidas["en_plazo"].any():
        st.caption(f"{es(int(perdidas['en_plazo'].sum()), 0)} de las que se quedan aquí aún están en plazo y pueden avanzar.")
    listado(perdidas, f"Familias que se quedan en «{origen.lower()}»")


# ── Piden ayuda de noche ───────────────────────────────────────────────────────────────────────────────────────
@st.dialog("Piden ayuda de noche", width="large")
def noche(desde: date, hasta: date) -> None:
    df = familias(desde, hasta)
    st.caption(f"{periodo_txt(desde, hasta)} · familias que piden ayuda fuera del horario de atención (de 20:00 a 9:00, y "
               "fines de semana y festivos a partir de las 18:00)")
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    t = df.assign(dia=df["fecha_entrada"].dt.weekday).groupby("dia").agg(n=("id", "size"), si=("fuera_horario", "sum"))
    t = t.reindex(range(7), fill_value=0)
    pct = (100 * t["si"] / t["n"].where(t["n"] > 0)).fillna(0)
    st.markdown("##### Según el día de la semana")
    comun.grafico(barras_h([dias[i] for i in t.index], pct, [f"{es(p, 0)} %  ({es(s, 0)} de {es(n, 0)})"
                                                            for p, s, n in zip(pct, t["si"], t["n"])]))
    c = tasa_por(df, "canal", df["fuera_horario"] == 1)
    st.markdown("##### Según el canal")
    comun.grafico(barras_h(c["canal"], c["pct"], [f"{es(p, 0)} %  ({es(s, 0)} de {es(n, 0)})"
                                                  for p, s, n in zip(c["pct"], c["si"], c["n"])]))
    comun.nota("Son las familias que hoy esperan a la mañana: las que atendería el asistente de noche.")
    st.page_link("paginas/web.py", label="Ver la web con el asistente de noche", icon=":material/language:")
    listado(df[df["fuera_horario"] == 1], "Familias que piden ayuda de noche",
            ["Familia", "Entró", "Canal", "Ciudad", "Servicio", "Urgente", "Espera", "Estado"])


# ── Siguen al año ──────────────────────────────────────────────────────────────────────────────────────────────
@st.dialog("Siguen al año", width="large")
def siguen() -> None:
    from motor import metricas
    with comun.conexion() as con:
        km = metricas.kaplan_meier(metricas.duraciones(con))
    st.caption("Histórico: de cada 100 familias que contratan, cuántas siguen con el servicio mes a mes (Kaplan-Meier; "
               "cuenta también a las que aún no han cumplido un año)")
    fig = go.Figure(go.Scatter(x=km["mes"], y=km["pct_siguen"], mode="lines", line=dict(color=graficos.ACENTO, width=3, shape="hv"),
                               hovertemplate="mes %{x}: %{y:.0f} %<extra></extra>"))
    fig.update_layout(xaxis=dict(title="meses desde que contratan", range=[0, 12.5]),
                      yaxis=dict(title="siguen", ticksuffix=" %", range=[0, 102]))
    comun.grafico(graficos._limpio(fig, 280))
    comun.nota("La mayoría de bajas llega en los tres primeros meses: ahí está la palanca (seguimiento de la Referente Social "
               "y satisfacción como alerta temprana).")
    st.page_link("paginas/se_queda.py", label="Ver Retención por canal", icon=":material/favorite:")
