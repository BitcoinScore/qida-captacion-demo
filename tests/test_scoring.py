from motor import scoring


def test_scoring_valida_sin_censura(con):
    res = scoring.entrenar(scoring.cargar(con))
    test = res["test"]
    assert res["auc"] > 0.62
    assert test["fecha_entrada"].max() < scoring.pd.Timestamp("2026-10-01")
    gan = scoring.ganancia(test)
    assert gan["pct_contratos"].is_monotonic_increasing and round(gan["pct_contratos"].iloc[-1]) == 100
    cal = scoring.calibracion(test)
    assert (abs(cal["predicho"] - cal["real"]) < 10).all()


def test_porque_es_legible(con):
    res = scoring.entrenar(scoring.cargar(con))
    texto = scoring.porque(res, res["test"].iloc[0])
    assert "fuera_horario" not in texto and "canal:" not in texto
