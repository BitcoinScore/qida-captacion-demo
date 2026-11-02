"""Lead scoring explicable: probabilidad de que un lead acabe en alta, con lo que se sabe al entrar.

Regresión logística a propósito: pocos datos y comercial tiene que entender el porqué de cada puntuación.
Etiqueta: la familia contrata en los 30 días siguientes (solo cohortes maduras, sin censura).
Entrena hasta julio de 2026 y valida con agosto-septiembre (validación temporal, como sería en producción).
"""
import math
import sqlite3

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

CORTE = "2026-08-01"
CATEGORICAS = ["canal", "ciudad", "servicio"]
BINARIAS = ["urgencia", "menciona_dependencia", "fuera_horario"]


def cargar(con: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        """SELECT c.*, CASE WHEN a.lead_id IS NULL THEN 0 ELSE 1 END AS alta
           FROM cohorte c LEFT JOIN altas_30d a ON a.lead_id = c.id""",
        con,
    )
    df["fecha_entrada"] = pd.to_datetime(df["fecha_entrada"])
    return df


def _matriz(df: pd.DataFrame, columnas: list[str] | None = None) -> pd.DataFrame:
    X = pd.get_dummies(df[CATEGORICAS], prefix=CATEGORICAS, prefix_sep=": ").astype(float)
    for b in BINARIAS:
        X[b] = df[b].astype(float)
    if columnas is not None:
        X = X.reindex(columns=columnas, fill_value=0.0)
    return X


def entrenar(df: pd.DataFrame) -> dict:
    train = df[df["fecha_entrada"] < CORTE]
    test = df[df["fecha_entrada"] >= CORTE].copy()
    X_train = _matriz(train)
    modelo = LogisticRegression(max_iter=2000, C=1.0)
    modelo.fit(X_train, train["alta"])
    X_test = _matriz(test, list(X_train.columns))
    test["score"] = modelo.predict_proba(X_test)[:, 1]
    pesos = pd.Series(modelo.coef_[0], index=X_train.columns).sort_values()
    return {
        "modelo": modelo,
        "columnas": list(X_train.columns),
        "test": test,
        "auc": roc_auc_score(test["alta"], test["score"]),
        "pesos": pesos,
        "n_train": len(train),
    }


def puntuar(res: dict, df: pd.DataFrame) -> np.ndarray:
    return res["modelo"].predict_proba(_matriz(df, res["columnas"]))[:, 1]


def porque(res: dict, fila: pd.Series, n: int = 3) -> str:
    """Las n variables que más suben o bajan la puntuación de este lead."""
    X = _matriz(fila.to_frame().T, res["columnas"]).iloc[0]
    contrib = (X * res["pesos"].reindex(res["columnas"])).loc[lambda s: s != 0]
    top = contrib.reindex(contrib.abs().sort_values(ascending=False).index)[:n]
    return " · ".join(f"{'▲' if v > 0 else '▼'} {_legible(k)}" for k, v in top.items())


def _legible(variable: str) -> str:
    nombres = {"fuera_horario": "de noche", "menciona_dependencia": "menciona Dependencia", "urgencia": "urgente"}
    return nombres.get(variable, variable.split(": ", 1)[-1])



def ganancia(test: pd.DataFrame) -> pd.DataFrame:
    """Curva de ganancia: llamando al X % mejor puntuado, ¿qué % de todos los contratos se cubre?"""
    t = test.sort_values("score", ascending=False).reset_index(drop=True)
    total = t["alta"].sum()
    puntos = []
    for pct in range(0, 101, 5):
        n = round(len(t) * pct / 100)
        puntos.append({"pct_llamadas": pct, "pct_contratos": 100 * t["alta"].iloc[:n].sum() / total if total else 0})
    return pd.DataFrame(puntos)


def calibracion(test: pd.DataFrame, grupos: int = 8) -> pd.DataFrame:
    """¿Cuando el modelo dice 20 %, contratan de verdad ~20 %? Probabilidad media predicha frente a tasa real, por grupos."""
    t = test.copy()
    t["grupo"] = pd.qcut(t["score"].rank(method="first"), grupos, labels=False)
    c = t.groupby("grupo").agg(predicho=("score", "mean"), real=("alta", "mean"), n=("alta", "size"))
    return (c * [100, 100, 1]).round(1).reset_index(drop=True)


def decaimiento(minutos: float) -> float:
    """Mismo supuesto que el generador: cuanto más se tarda en llamar, menos familias siguen interesadas."""
    return 0.55 + 0.45 * math.exp(-minutos / 600)


def simular_cola_manana(test: pd.DataFrame, llamadas_por_hora: int = 6) -> dict:
    """Leads que entran fuera de horario se acumulan para la mañana. ¿Llamar por orden de llegada o por score?

    Simulación con supuestos: altas esperadas = score × efecto de la espera (relativo a una espera de 0).
    """
    cola = test[test["fuera_horario"] == 1].copy()
    # hora de apertura: el siguiente día laborable/festivo a las 9:00
    apertura = cola["fecha_entrada"].dt.normalize() + pd.Timedelta(hours=9)
    apertura = apertura.where(cola["fecha_entrada"].dt.hour < 9, apertura + pd.Timedelta(days=1))
    cola["apertura"] = apertura
    resultado = {}
    for criterio in ("llegada", "score"):
        total = 0.0
        for _, grupo in cola.groupby("apertura"):
            orden = grupo.sort_values("fecha_entrada" if criterio == "llegada" else "score", ascending=criterio == "llegada")
            for i, (_, f) in enumerate(orden.iterrows()):
                espera = (f["apertura"] - f["fecha_entrada"]).total_seconds() / 60 + 60 * i / llamadas_por_hora
                total += f["score"] * decaimiento(espera)
        resultado[criterio] = total
    resultado["leads"] = len(cola)
    resultado["mejora_pct"] = 100 * (resultado["score"] / resultado["llegada"] - 1)
    return resultado
