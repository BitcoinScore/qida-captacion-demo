"""Gráficos Plotly con un estilo común (paleta de Qida, formato español, accesibles)."""
import pandas as pd
import plotly.graph_objects as go

import geo
from comun import GRIS_TEXTO, NARANJA_TEXTO, VERDE_TEXTO, es

# Paleta de Qida (qida.es): verde de marca para el dato principal, naranja SOLO para lo que hay que mirar.
ACENTO = "#004039"     # dato principal / lo que sigue en el embudo
MEDIO = "#338581"      # dato secundario (relleno; para texto, VERDE_TEXTO)
NEUTRO = "#99C2C0"     # comparación, sin juicio
PERDIDA = "#CCE0DF"    # lo que se pierde (apagado)
AVISO = "#ea6d43"      # alerta (relleno; para texto, NARANJA_TEXTO)
GRIS = GRIS_TEXTO      # textos secundarios y referencias (contraste AA)
ESCALA = [[0, "#EFF5F5"], [1, ACENTO]]


def _limpio(fig: go.Figure, alto: int = 360) -> go.Figure:
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10), separators=",.",
                      font=dict(size=13, family="DM Sans, Arial, sans-serif", color="#333333"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(gridcolor="#E3EEED", zerolinecolor="#CCE0DF", tickfont=dict(color=GRIS)),
                      yaxis=dict(gridcolor="#E3EEED", zerolinecolor="#CCE0DF", tickfont=dict(color="#333333")))
    return fig


def embudo_viaje(etapas: list[dict]) -> go.Figure:
    """Embudo honesto: cada barra mide exactamente lo que representa (ancho ∝ valor), con conectores entre etapas.

    A la izquierda, la etapa, el número, la tasa del paso y la acumulada. A la derecha, lo que se pierde y qué lo arregla.
    etapas: [{'nombre', 'valor', 'perdida', 'arreglo', 'grave' (bool), 'estimado' (bool)}]
    """
    fig = go.Figure()
    maximo = etapas[0]["valor"]
    ancho = [e["valor"] / maximo for e in etapas]
    alto, hueco = 0.62, 0.5
    for k, e in enumerate(etapas):
        y0 = -(k * (alto + hueco))
        y1 = y0 - alto
        w = ancho[k]
        estimado = e.get("estimado", False)
        fig.add_shape(type="rect", x0=-w, x1=w, y0=y1, y1=y0,
                      line=dict(color=ACENTO, width=2, dash="dot" if estimado else "solid"),
                      fillcolor="rgba(51,133,129,0.15)" if estimado else ACENTO)
        if k + 1 < len(etapas):  # conector hacia la siguiente etapa
            w2 = ancho[k + 1]
            fig.add_shape(type="path", path=f"M {-w} {y1} L {w} {y1} L {w2} {y1 - hueco} L {-w2} {y1 - hueco} Z",
                          fillcolor="rgba(0,64,57,0.06)", line=dict(width=0))
        paso = f"{es(100 * e['valor'] / etapas[k - 1]['valor'], 0)} % del paso anterior · " if k else ""
        acumulado = f"{es(100 * e['valor'] / maximo)} % del total"
        fig.add_annotation(
            x=-1.05, y=(y0 + y1) / 2, showarrow=False, xanchor="right", align="right",
            text=(f"<b>{e['nombre']}</b>{' <i>(estimado)</i>' if estimado else ''}  "
                  f"<span style='font-size:19px'><b>{es(e['valor'], 0)}</b></span>"
                  f"<br><span style='color:{GRIS};font-size:12px'>{paso}{acumulado}</span>"),
            font=dict(size=14, color=ACENTO))
        if e.get("perdida"):
            yc = y1 - hueco / 2
            col = NARANJA_TEXTO if e.get("grave") else "#4d5d5c"
            fig.add_annotation(x=1.05, y=yc + 0.13, xanchor="left", showarrow=False, align="left",
                               text=f"<b>▼ {e['perdida']}</b>", font=dict(size=13, color=col))
            fig.add_annotation(x=1.05, y=yc - 0.13, xanchor="left", showarrow=False, align="left",
                               text=e["arreglo"], font=dict(size=12, color=VERDE_TEXTO))
    fig.update_xaxes(visible=False, range=[-2.7, 2.75])
    fig.update_yaxes(visible=False, range=[-(len(etapas) * (alto + hueco)) + hueco - 0.1, 0.1])
    return _limpio(fig, 95 * len(etapas) + 40)


def puntos_ic(df: pd.DataFrame, etiqueta: str, alto: int = 380, rango: tuple[float, float] | None = None) -> go.Figure:
    """Proporción por canal (`pct`) con su intervalo del 95 % (`ic_bajo`, `ic_alto`) como gráfico de puntos.

    La etiqueta va a la derecha del intervalo, así nunca la tacha el bigote ni se corta.
    """
    d = df.sort_values("pct")
    fig = go.Figure()
    fig.add_trace(go.Scatter(  # intervalo
        x=list(d["ic_bajo"]) + [None], y=list(d["canal"]) + [None], mode="markers", showlegend=False,
        marker=dict(size=1, color="rgba(0,0,0,0)"), hoverinfo="skip"))
    for _, f in d.iterrows():
        fig.add_shape(type="line", x0=f["ic_bajo"], x1=f["ic_alto"], y0=f["canal"], y1=f["canal"],
                      line=dict(color=NEUTRO, width=6))
    fig.add_trace(go.Scatter(
        x=d["pct"], y=d["canal"], mode="markers", marker=dict(size=13, color=ACENTO), showlegend=False,
        customdata=list(zip(d["ic_bajo"].map(es), d["ic_alto"].map(es), d["familias"].map(lambda n: es(n, 0)))),
        hovertemplate="%{y}: %{x:.1f} % (intervalo %{customdata[0]}–%{customdata[1]} %, %{customdata[2]} familias)<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=d["ic_alto"], y=d["canal"], mode="text", showlegend=False, textposition="middle right", hoverinfo="skip",
        text=[f"  <b>{es(p)} %</b> <span style='color:{GRIS}'>· {es(n, 0)} familias</span>"
              for p, n in zip(d["pct"], d["familias"])]))
    maximo = rango[1] if rango else d["ic_alto"].max() * 1.9
    fig.update_layout(xaxis=dict(title=etiqueta, range=[rango[0] if rango else 0, maximo], ticksuffix=" %", showgrid=True,
                                 tickvals=[t for t in range(0, 101, 20) if t >= (rango[0] if rango else 0)]),
                      yaxis=dict(title=None, showgrid=False))
    return _limpio(fig, alto)


def ltv_cac(df: pd.DataFrame, alto: int = 380) -> go.Figure:
    d = df[df["ltv_cac"].notna() & (df["ltv_cac"] != float("inf")) & (df["ltv_cac"] > 0)].sort_values("ltv_cac")
    colores = [PERDIDA if n < 50 else AVISO if v < 3 else ACENTO for v, n in zip(d["ltv_cac"], d["contratos"])]
    etiquetas = [c + (" (pocos datos)" if n < 50 else "") for c, n in zip(d["canal"], d["contratos"])]
    fig = go.Figure(go.Bar(x=d["ltv_cac"], y=etiquetas, orientation="h", marker_color=colores,
                           text=[es(v, 1, "×") for v in d["ltv_cac"]], textposition="outside", cliponaxis=False))
    fig.add_vline(x=3, line=dict(color=GRIS, dash="dot", width=1), layer="below", annotation_text="mínimo sano: 3×",
                  annotation_position="top", annotation_font_color=GRIS)
    fig.update_layout(xaxis=dict(title="veces que el valor de una familia en 12 meses cubre lo que costó captarla",
                                 range=[0, d["ltv_cac"].max() * 1.18 if len(d) else 10], showgrid=False),
                      yaxis_title=None)
    return _limpio(fig, alto)


def mapa(por_ciudad: pd.DataFrame) -> go.Figure:
    """por_ciudad: ciudad, leads, pct_alta, estado. Puntos grises = cobertura real; burbujas = ciudades de la demo.

    El tamaño (área) es el volumen. El color solo marca una ciudad si su conversión difiere de forma significativa del resto.
    """
    cobertura = pd.DataFrame(
        [(c, *xy) for c, xy in geo.COORDENADAS.items() if c not in set(por_ciudad["ciudad"])],
        columns=["ciudad", "lat", "lon"],
    )
    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=cobertura["lat"], lon=cobertura["lon"], mode="markers", name="Otras ciudades con servicio",
        marker=dict(size=7, color=GRIS, opacity=0.6), text=cobertura["ciudad"], hoverinfo="text",
    ))
    d = por_ciudad.copy()
    d["lat"] = d["ciudad"].map(lambda c: geo.COORDENADAS[c][0])
    d["lon"] = d["ciudad"].map(lambda c: geo.COORDENADAS[c][1])
    d["meta"] = d["ciudad"].isin(geo.CIUDADES_META).map({True: "Sí", False: "No"})
    d["pct_txt"] = d["pct_alta"].map(es)
    # Área proporcional al volumen: el diámetro crece con la raíz cuadrada (si no, el ojo exagera las diferencias)
    tamano = 60 * (d["leads"] / d["leads"].max()) ** 0.5
    con_meta = d["meta"] == "Sí"
    fig.add_trace(go.Scattermap(
        lat=d.loc[con_meta, "lat"], lon=d.loc[con_meta, "lon"], mode="markers", name="Anuncios activos en Meta (real)",
        marker=dict(size=tamano[con_meta] + 16, color=MEDIO, opacity=0.25), hoverinfo="skip",
    ))
    colores = {"por encima": ACENTO, "en la media": NEUTRO, "por debajo": AVISO}
    for estado, color in colores.items():
        g = d[d["estado"] == estado]
        if g.empty:
            continue
        fig.add_trace(go.Scattermap(
            lat=g["lat"], lon=g["lon"], mode="markers+text", name=f"Conversión {estado}",
            marker=dict(size=tamano[g.index], color=color, opacity=0.85),
            text=g["ciudad"], textposition="top center", textfont=dict(color=ACENTO, size=13),
            customdata=g[["leads", "pct_txt", "ic", "meta"]],
            hovertemplate="<b>%{text}</b><br>%{customdata[0]} familias<br>%{customdata[1]} % contrata "
                          "(intervalo %{customdata[2]})<br>Anuncios en Meta: %{customdata[3]}<extra></extra>",
        ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=40.2, lon=-3.6), zoom=4.3),
                      legend=dict(orientation="h", y=-0.02, x=0))
    return _limpio(fig, 420)


def destino_por_canal(flujos: pd.DataFrame, alto: int = 380) -> go.Figure:
    """Barras apiladas al 100 % por canal: qué fue de cada 100 familias (contratan, valoración sin contrato, se pierden antes).

    Sustituye al Sankey, que sugería un reparto por canal tras la valoración que no estaba calculado.
    """
    d = flujos.copy()
    d["Contratan"] = 100 * d["altas"] / d["leads"]
    d["Valoración sin contrato"] = 100 * (d["valoraciones"] - d["altas"]) / d["leads"]
    d["Se pierden antes de la valoración"] = 100 * (d["leads"] - d["valoraciones"]) / d["leads"]
    d = d.sort_values("Contratan")
    fig = go.Figure()
    for nombre, color, texto in (("Contratan", ACENTO, "white"), ("Valoración sin contrato", NEUTRO, ACENTO),
                                 ("Se pierden antes de la valoración", "#E9EFEE", GRIS)):
        fig.add_bar(y=d["canal"], x=d[nombre], name=nombre, orientation="h", marker_color=color,
                    text=d[nombre].map(lambda v: es(v, 0) + " %" if v >= 6 else ""), textposition="inside",
                    insidetextanchor="middle", textfont=dict(color=texto))
    _limpio(fig, alto)
    fig.update_layout(barmode="stack", xaxis=dict(title="de cada 100 familias que llegan por ese canal", range=[0, 100],
                                                  ticksuffix=" %", showgrid=False, dtick=20),
                      yaxis_title=None, legend=dict(orientation="h", y=-0.28, x=0, traceorder="normal"),
                      margin=dict(l=10, r=10, t=10, b=90))
    return fig


def columnas(df: pd.DataFrame, x: str, y: str, etiqueta_x: str, etiqueta_y: str, alto: int = 340,
             resaltar: str | None = None) -> go.Figure:
    colores = [ACENTO if v == resaltar or resaltar is None else NEUTRO for v in df[x]]
    fig = go.Figure(go.Bar(x=df[x], y=df[y], marker_color=colores, text=df[y].map(lambda v: es(v) + " %"),
                           textposition="outside", cliponaxis=False))
    fig.update_layout(xaxis=dict(title=etiqueta_x, type="category"),
                      yaxis=dict(title=etiqueta_y, showgrid=False, range=[0, df[y].max() * 1.2], ticksuffix=" %"))
    return _limpio(fig, alto)
