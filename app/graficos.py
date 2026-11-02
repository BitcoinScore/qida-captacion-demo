"""Gráficos Plotly con un estilo común."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import geo

# Paleta de Qida (qida.es): verde de marca para el dato principal, naranja solo para lo que hay que mirar.
ACENTO = "#004039"     # dato principal / lo que sigue en el embudo
MEDIO = "#338581"      # dato secundario
NEUTRO = "#99C2C0"     # comparación, sin juicio
PERDIDA = "#CCE0DF"    # lo que se pierde (apagado)
AVISO = "#ea6d43"      # lo que hay que mirar
GRIS = "#8A9A99"       # textos secundarios y referencias
ESCALA = [[0, "#EFF5F5"], [1, ACENTO]]


def _limpio(fig: go.Figure, alto: int = 360) -> go.Figure:
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10),
                      font=dict(size=13, family="DM Sans, Arial, sans-serif", color="#333333"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(gridcolor="#E3EEED", zerolinecolor="#CCE0DF"),
                      yaxis=dict(gridcolor="#E3EEED", zerolinecolor="#CCE0DF"))
    return fig


def embudo(etapas: list[str], valores: list[int]) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=etapas, x=valores, textinfo="value+percent previous", textfont=dict(size=15),
        marker=dict(color=[ACENTO, ACENTO, AVISO, ACENTO][: len(valores)]),
        connector=dict(line=dict(color=PERDIDA, width=1)),
    ))
    return _limpio(fig, 380)


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
        fig.add_shape(type="rect", x0=-w, x1=w, y0=y1, y1=y0, line=dict(color=ACENTO, width=2, dash="dot" if estimado else "solid"),
                      fillcolor="rgba(51,133,129,0.15)" if estimado else ACENTO)
        if k + 1 < len(etapas):  # conector hacia la siguiente etapa
            w2 = ancho[k + 1]
            fig.add_shape(type="path", path=f"M {-w} {y1} L {w} {y1} L {w2} {y1 - hueco} L {-w2} {y1 - hueco} Z",
                          fillcolor="rgba(0,64,57,0.06)", line=dict(width=0))
        paso = f"{100 * e['valor'] / etapas[k - 1]['valor']:.0f} % del paso anterior · " if k else ""
        acumulado = f"{100 * e['valor'] / maximo:.1f} % del total".replace(".", ",")
        fig.add_annotation(
            x=-1.05, y=(y0 + y1) / 2, showarrow=False, xanchor="right", align="right",
            text=(f"<b>{e['nombre']}</b>{' <i>(estimado)</i>' if estimado else ''}  "
                  f"<span style='font-size:19px'><b>{e['valor']:,}</b></span>".replace(",", ".")
                  + f"<br><span style='color:#6b7b7a;font-size:12px'>{paso}{acumulado}</span>"),
            font=dict(size=14, color="#004039"))
        if e.get("perdida"):
            yc = y1 - hueco / 2
            col = AVISO if e.get("grave") else "#4d5d5c"
            fig.add_annotation(x=1.05, y=yc + 0.13, xanchor="left", showarrow=False, align="left",
                               text=f"<b>▼ {e['perdida']}</b>", font=dict(size=13, color=col))
            fig.add_annotation(x=1.05, y=yc - 0.13, xanchor="left", showarrow=False, align="left",
                               text=e["arreglo"], font=dict(size=12, color=MEDIO))
    fig.update_xaxes(visible=False, range=[-2.7, 2.75])
    fig.update_yaxes(visible=False, range=[-(len(etapas) * (alto + hueco)) + hueco - 0.1, 0.1])
    return _limpio(fig, 95 * len(etapas) + 40)


def barras_ic(df: pd.DataFrame, etiqueta: str, alto: int = 380) -> go.Figure:
    """Barras horizontales de una proporción (`pct`) con su intervalo de confianza del 95 % (`ic_bajo`, `ic_alto`)."""
    d = df.sort_values("pct")
    fig = go.Figure(go.Bar(
        x=d["pct"], y=d["canal"], orientation="h", marker_color=ACENTO,
        error_x=dict(type="data", symmetric=False, array=d["ic_alto"] - d["pct"], arrayminus=d["pct"] - d["ic_bajo"],
                     color="#6b7b7a", thickness=1.5, width=4),
        text=[f"{p:.1f} %  (n={n:,})".replace(",", ".") for p, n in zip(d["pct"], d["familias"])],
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(xaxis_title=etiqueta, yaxis_title=None, xaxis=dict(showgrid=False))
    return _limpio(fig, alto)


def ltv_cac(df: pd.DataFrame, alto: int = 380) -> go.Figure:
    d = df[(df["ltv_cac"] != float("inf")) & df["ltv_cac"].notna()].sort_values("ltv_cac")
    colores = [PERDIDA if n < 50 else AVISO if v < 3 else ACENTO for v, n in zip(d["ltv_cac"], d["contratos"])]
    etiquetas = [c + (" ⚠️" if n < 50 else "") for c, n in zip(d["canal"], d["contratos"])]
    fig = go.Figure(go.Bar(x=d["ltv_cac"], y=etiquetas, orientation="h", marker_color=colores,
                           text=[f"{v:.1f}×" for v in d["ltv_cac"]], textposition="outside", cliponaxis=False))
    fig.add_vline(x=3, line=dict(color=AVISO, dash="dash"), annotation_text="mínimo sano: 3×",
                  annotation_position="top", annotation_font_color=AVISO)
    fig.update_layout(xaxis_title="LTV a 12 meses ÷ CAC combinado", yaxis_title=None, xaxis=dict(showgrid=False))
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
    # Área proporcional al volumen: el diámetro crece con la raíz cuadrada (si no, el ojo exagera las diferencias)
    tamano = 60 * (d["leads"] / d["leads"].max()) ** 0.5
    con_meta = d["meta"] == "Sí"
    fig.add_trace(go.Scattermap(
        lat=d.loc[con_meta, "lat"], lon=d.loc[con_meta, "lon"], mode="markers", name="Anuncios activos en Meta (real)",
        marker=dict(size=tamano[con_meta] + 16, color=AVISO, opacity=0.35), hoverinfo="skip",
    ))
    colores = {"por encima": ACENTO, "en la media": NEUTRO, "por debajo": AVISO}
    for estado, color in colores.items():
        g = d[d["estado"] == estado]
        if g.empty:
            continue
        fig.add_trace(go.Scattermap(
            lat=g["lat"], lon=g["lon"], mode="markers+text", name=f"Conversión {estado}",
            marker=dict(size=tamano[g.index], color=color, opacity=0.85),
            text=g["ciudad"], textposition="top center", textfont=dict(color="#004039", size=13),
            customdata=g[["leads", "pct_alta", "ic", "meta"]],
            hovertemplate="<b>%{text}</b><br>%{customdata[0]} familias<br>%{customdata[1]} % contrata (IC %{customdata[2]})"
                          "<br>Anuncios en Meta: %{customdata[3]}<extra></extra>",
        ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=40.2, lon=-3.6), zoom=4.3),
                      legend=dict(orientation="h", y=-0.02, x=0))
    return _limpio(fig, 420)


def sankey(flujos: pd.DataFrame) -> go.Figure:
    """flujos: canal, leads, valoraciones, altas."""
    canales = list(flujos["canal"])
    nodos = canales + ["Valoración", "No llegan a valoración", "Contratan", "No contratan"]
    i = {n: k for k, n in enumerate(nodos)}
    origen, destino, valor, color = [], [], [], []
    for _, f in flujos.iterrows():
        for dest, v, c in ((
            "Valoración", f["valoraciones"], "rgba(51,133,129,0.45)"),
            ("No llegan a valoración", f["leads"] - f["valoraciones"], "rgba(153,194,192,0.35)"),
        ):
            origen.append(i[f["canal"]]); destino.append(i[dest]); valor.append(v); color.append(c)
    total_val, total_alt = flujos["valoraciones"].sum(), flujos["altas"].sum()
    for dest, v, c in (("Contratan", total_alt, "rgba(0,64,57,0.75)"),
                       ("No contratan", total_val - total_alt, "rgba(153,194,192,0.35)")):
        origen.append(i["Valoración"]); destino.append(i[dest]); valor.append(v); color.append(c)
    colores_nodo = [MEDIO] * len(canales) + [ACENTO, PERDIDA, ACENTO, PERDIDA]
    fig = go.Figure(go.Sankey(
        node=dict(label=nodos, pad=14, thickness=16, color=colores_nodo, line=dict(width=0)),
        link=dict(source=origen, target=destino, value=valor, color=color),
    ))
    return _limpio(fig, 430)


def barras(df: pd.DataFrame, x: str, y: str, etiqueta_x: str, sufijo: str = " %", alto: int = 360,
           resaltar: str | None = None) -> go.Figure:
    d = df.sort_values(x)
    colores = [AVISO if resaltar and v == resaltar else ACENTO for v in d[y]]
    fig = px.bar(d, x=x, y=y, orientation="h", text=d[x].map(lambda v: f"{v:g}{sufijo}"))
    fig.update_traces(marker_color=colores, textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=etiqueta_x, yaxis_title=None, xaxis=dict(showgrid=False))
    return _limpio(fig, alto)


def columnas(df: pd.DataFrame, x: str, y: str, etiqueta_x: str, etiqueta_y: str, alto: int = 340) -> go.Figure:
    fig = px.bar(df, x=x, y=y, text=df[y].map(lambda v: f"{v:g} %"), color=y, color_continuous_scale=ESCALA)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=etiqueta_x, yaxis_title=etiqueta_y, coloraxis_showscale=False, yaxis=dict(showgrid=False),
                      xaxis=dict(type="category"))
    return _limpio(fig, alto)


def burbujas_coste(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(df, x="coste_por_lead", y="coste_por_alta", size="gasto_eur", text="canal", size_max=60)
    fig.update_traces(marker=dict(color=AVISO, opacity=0.75, line=dict(width=0)), textposition="top center")
    fig.update_layout(xaxis_title="€ por lead (lo que se suele mirar)", yaxis_title="€ por contrato (lo que importa)",
                      xaxis=dict(range=[-5, df["coste_por_lead"].max() * 1.3]),
                      yaxis=dict(range=[0, df["coste_por_alta"].max() * 1.25]))
    return _limpio(fig, 380)
