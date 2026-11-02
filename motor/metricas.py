"""Métricas estándar: intervalos de confianza, permanencia (Kaplan-Meier) y economía por canal (CAC, LTV, payback).

Definiciones en docs/auditoria-kpis.md. Las vistas `cohorte` y `*_30d` están en datos/esquema.sql.
"""
import math
import sqlite3

import pandas as pd

CORTE = "2026-11-02"  # «hoy» en la demo: último día con datos
MARGEN_BRUTO = 0.30   # supuesto: la demo no tiene costes de cuidadoras; con el margen real el LTV cambia
MESES_LTV = 12


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza del 95 % para una proporción (Wilson), en %."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (100 * (centro - margen), 100 * (centro + margen))


def con_ic(df: pd.DataFrame, k: str, n: str) -> pd.DataFrame:
    d = df.copy()
    d["pct"] = 100 * d[k] / d[n]
    ic = [wilson(int(a), int(b)) for a, b in zip(d[k], d[n])]
    d["ic_bajo"] = [i[0] for i in ic]
    d["ic_alto"] = [i[1] for i in ic]
    return d


def duraciones(con: sqlite3.Connection, ciudades: list[str] | None = None) -> pd.DataFrame:
    """Una fila por contrato: meses observados y si hubo baja (para Kaplan-Meier)."""
    filtro = f"AND l.ciudad IN ({','.join('?' * len(ciudades))})" if ciudades else ""
    return pd.read_sql(
        f"""SELECT a.lead_id, l.canal, substr(a.fecha_alta, 1, 7) AS cohorte, a.ingreso_mes,
                   (COALESCE(julianday(b.fecha_baja), julianday('{CORTE}')) - julianday(a.fecha_alta)) / 30.4 AS meses,
                   CASE WHEN b.lead_id IS NULL THEN 0 ELSE 1 END AS baja
            FROM altas a JOIN leads l ON l.id = a.lead_id LEFT JOIN bajas b ON b.lead_id = a.lead_id
            WHERE 1 = 1 {filtro}""",
        con, params=ciudades or [],
    )


def kaplan_meier(d: pd.DataFrame, hasta: int = 15) -> pd.DataFrame:
    """Permanencia S(m) mes a mes. Usa a todas las familias, también las recientes (censuradas), sin sesgo."""
    s, filas = 1.0, [{"mes": 0, "pct_siguen": 100.0, "en_riesgo": len(d)}]
    for m in range(1, hasta + 1):
        en_riesgo = (d["meses"] >= m - 1).sum()
        bajas = ((d["meses"] >= m - 1) & (d["meses"] < m) & (d["baja"] == 1)).sum()
        if en_riesgo < 30:
            break
        s *= 1 - bajas / en_riesgo
        filas.append({"mes": m, "pct_siguen": round(100 * s, 1), "en_riesgo": int(en_riesgo)})
    return pd.DataFrame(filas)


def triangulo(d: pd.DataFrame, max_meses: int = 12) -> pd.DataFrame:
    """Triángulo de cohortes: % de cada cohorte de alta que sigue activa a los m meses (vacío si aún no han llegado)."""
    filas = {}
    for coh, g in d.groupby("cohorte"):
        edad = (pd.Timestamp(CORTE) - pd.Timestamp(coh + "-01")).days / 30.4
        filas[coh] = {m: round(100 * (g["meses"] >= m).mean(), 0) if m <= edad - 1 else None
                      for m in range(0, max_meses + 1)}
    return pd.DataFrame(filas).T.sort_index()


def kpis_mes(con: sqlite3.Connection, mes: str) -> dict:
    """KPIs principales de una cohorte mensual (familias que pidieron ayuda ese mes, resultados a 30 días)."""
    familias, contratos, llamadas, rapidas = con.execute(
        """SELECT COUNT(*), COUNT(a.lead_id), COUNT(ll.lead_id),
                  SUM(CASE WHEN (julianday(ll.fecha_primera_llamada) - julianday(c.fecha_entrada)) * 1440 < 60 THEN 1 ELSE 0 END)
           FROM cohorte c LEFT JOIN altas_30d a ON a.lead_id = c.id LEFT JOIN llamadas_30d ll ON ll.lead_id = c.id
           WHERE substr(c.fecha_entrada, 1, 7) = ?""", (mes,)).fetchone()
    gasto = con.execute("SELECT SUM(importe) FROM gasto WHERE mes = ?", (mes,)).fetchone()[0] or 0
    return {
        "familias": familias,
        "conversion": 100 * contratos / familias if familias else 0,
        "cac": gasto / contratos if contratos else 0,
        "rapidas": 100 * (rapidas or 0) / llamadas if llamadas else 0,
        "contratos": contratos,
    }


def kpis_periodo(con: sqlite3.Connection, desde: str, hasta: str) -> dict:
    """KPIs de las familias que pidieron ayuda entre `desde` y `hasta` (AAAA-MM-DD, ambos incluidos).

    `madura` dice si todas han tenido ya 30 días para contratar; si no, conversión y coste por contrato son provisionales.
    El gasto mensual se reparte por días.
    """
    familias, noche, llamadas, rapidas, valoraciones, contratos = con.execute(
        """SELECT COUNT(*), SUM(f.fuera_horario), COUNT(ll.lead_id),
                  SUM(CASE WHEN (julianday(ll.fecha_primera_llamada) - julianday(f.fecha_entrada)) * 1440 < 60 THEN 1 ELSE 0 END),
                  COUNT(v.lead_id), COUNT(a.lead_id)
           FROM familias f
           LEFT JOIN llamadas_30d ll    ON ll.lead_id = f.id
           LEFT JOIN valoraciones_30d v ON v.lead_id = f.id
           LEFT JOIN altas_30d a        ON a.lead_id = f.id
           WHERE date(f.fecha_entrada) BETWEEN ? AND ?""", (desde, hasta)).fetchone()
    d0, d1 = pd.Timestamp(desde), pd.Timestamp(hasta)
    gasto = 0.0
    for mes, importe in con.execute("SELECT mes, SUM(importe) FROM gasto GROUP BY mes"):
        ini = pd.Timestamp(mes + "-01")
        fin = ini + pd.offsets.MonthEnd(0)
        solape = (min(fin, d1) - max(ini, d0)).days + 1
        if solape > 0:
            gasto += importe * solape / ((fin - ini).days + 1)
    return {
        "familias": familias,
        "noche": 100 * (noche or 0) / familias if familias else 0,
        "rapidas": 100 * (rapidas or 0) / llamadas if llamadas else 0,
        "valoracion": 100 * valoraciones / familias if familias else 0,
        "conversion": 100 * contratos / familias if familias else 0,
        "contratos": contratos,
        "cac": gasto / contratos if contratos else float("nan"),
        "madura": (pd.Timestamp(CORTE) - d1).days >= 30,
        "dias": (d1 - d0).days + 1,
    }


def economia_por_canal(con: sqlite3.Connection, ciudades: list[str], desde: str = "2025-05") -> pd.DataFrame:
    """Por canal: familias, contratos, gasto, coste por familia y por valoración, CAC de pago y total, LTV a 12 meses
    (margen supuesto), LTV:CAC y meses para recuperar el CAC. `desde`: primer mes de la cohorte (AAAA-MM).

    Con menos de 30 contratos en un canal, su permanencia propia no es fiable: se usa la general (y se marca).
    """
    marc = ",".join("?" * len(ciudades))
    base = pd.read_sql(
        f"""SELECT c.canal, COUNT(*) AS familias, COUNT(v.lead_id) AS valoraciones, COUNT(a.lead_id) AS contratos,
                   AVG(a.ingreso_mes) AS ingreso_mes
            FROM cohorte c LEFT JOIN valoraciones_30d v ON v.lead_id = c.id LEFT JOIN altas_30d a ON a.lead_id = c.id
            WHERE c.ciudad IN ({marc}) AND substr(c.fecha_entrada, 1, 7) >= ? GROUP BY c.canal""",
        con, params=[*ciudades, desde])
    gasto = pd.read_sql(
        f"""SELECT canal, SUM(CASE WHEN tipo = 'medios' THEN importe ELSE 0 END) AS gasto_medios, SUM(importe) AS gasto_total
            FROM gasto WHERE mes < '2026-10' AND mes >= ? AND ciudad IN ({marc}) GROUP BY canal""",
        con, params=[desde, *ciudades])
    df = base.merge(gasto, on="canal", how="left").fillna({"gasto_medios": 0, "gasto_total": 0})
    curvas = duraciones(con, ciudades)
    s_general = _supervivencia(curvas)
    ltv, payback, fiable = [], [], []
    for _, f in df.iterrows():
        propias = curvas[curvas["canal"] == f["canal"]]
        s = _supervivencia(propias) if len(propias) >= 30 else s_general
        fiable.append(len(propias) >= 30)
        margen_mes = (f["ingreso_mes"] if f["ingreso_mes"] == f["ingreso_mes"] and f["ingreso_mes"] else 0) * MARGEN_BRUTO * s
        ltv.append(margen_mes.sum())
        cac = f["gasto_total"] / f["contratos"] if f["contratos"] else float("nan")
        acumulado = margen_mes.cumsum()
        payback.append(int((acumulado < cac).sum()) + 1 if cac and cac == cac and (acumulado >= cac).any() else None)
    contratos = df["contratos"].where(df["contratos"] > 0)  # sin contratos → sin cociente (nunca «inf»)
    df["ltv_12m"] = ltv
    df["permanencia_propia"] = fiable
    df["coste_por_familia"] = (df["gasto_total"] / df["familias"]).where(df["gasto_total"] > 0)
    df["coste_por_valoracion"] = (df["gasto_total"] / df["valoraciones"].where(df["valoraciones"] > 0)).where(df["gasto_total"] > 0)
    df["cac_pago"] = (df["gasto_medios"] / contratos).where(df["gasto_medios"] > 0)
    df["cac_combinado"] = (df["gasto_total"] / contratos).where(df["gasto_total"] > 0)
    df["ltv_cac"] = df["ltv_12m"] / df["cac_combinado"]
    df["payback_meses"] = payback
    return con_ic(df, "contratos", "familias")


def _supervivencia(d: pd.DataFrame) -> pd.Series:
    """Permanencia mes a mes (0..MESES_LTV-1) con Kaplan-Meier; si la curva se corta por falta de datos, se mantiene."""
    km = kaplan_meier(d, hasta=MESES_LTV)
    return km.set_index("mes")["pct_siguen"].reindex(range(MESES_LTV)).ffill() / 100
