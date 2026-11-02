import math

import pandas as pd

from motor import metricas


def test_wilson_contiene_la_proporcion():
    lo, hi = metricas.wilson(12, 100)
    assert lo < 12 < hi
    assert math.isclose(lo, 7.0, abs_tol=0.3) and math.isclose(hi, 19.8, abs_tol=0.3)


def test_kaplan_meier_sin_bajas_es_100():
    d = pd.DataFrame({"meses": [20.0] * 50, "baja": [0] * 50})
    assert (metricas.kaplan_meier(d, hasta=12)["pct_siguen"] == 100).all()


def test_kaplan_meier_no_sesga_con_censura():
    # 100 familias; la mitad se da de baja en el mes 1; la otra mitad lleva 0,5 meses (censuradas, no son bajas)
    d = pd.DataFrame({"meses": [0.5] * 50 + [0.7] * 50, "baja": [0] * 50 + [1] * 50})
    km = metricas.kaplan_meier(d, hasta=1).set_index("mes")["pct_siguen"]
    assert km[1] == 50.0


def test_permanencia_plausible(con):
    km = metricas.kaplan_meier(metricas.duraciones(con)).set_index("mes")["pct_siguen"]
    assert 70 < km[3] < 95 and 50 < km[12] < km[3]


def test_economia_por_canal(con):
    from comun import CIUDADES
    eco = metricas.economia_por_canal(con, CIUDADES)
    pago = eco[eco["gasto_medios"] > 0]
    assert (pago["cac_pago"] > 0).all()
    ambos = eco.dropna(subset=["cac_combinado", "cac_pago"])
    assert (ambos["cac_combinado"] >= ambos["cac_pago"]).all()
    assert not eco[["cac_combinado", "ltv_cac"]].isin([float("inf")]).any().any()  # nunca «inf»
    assert (eco["ic_bajo"] <= eco["pct"]).all() and (eco["pct"] <= eco["ic_alto"]).all()


def test_kpis_mes(con):
    k = metricas.kpis_mes(con, "2026-09")
    assert k["familias"] > 0 and 0 < k["conversion"] < 50 and k["cac"] > 0
