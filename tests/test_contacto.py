"""Lo que haría un equipo de producto o de seguridad con la web: teléfonos raros, horarios límite y entrada hostil."""
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from motor.contacto import horario, limpiar_ficha, normalizar_telefono

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("texto, esperado", [
    ("612 345 678", "612345678"), ("612-345-678", "612345678"), ("+34 612345678", "612345678"),
    ("0034 612 345 678", "612345678"), ("(612) 345.678", "612345678"), ("  912345678 ", "912345678"),
    ("812345678", "812345678"),
    ("", None), ("   ", None), ("112", None), ("061234567", None), ("512345678", None), ("61234567", None),
    ("6123456789", None), ("+44 7911 123456", None), ("seiscientos", None), ("612 345 67a", None),
    ("٦١٢٣٤٥٦٧٨", None), ("'; DROP TABLE leads_web;--", None), ("<script>alert(1)</script>", None),
    (None, None),
])
def test_telefono(texto, esperado):
    assert normalizar_telefono(texto) == esperado


@pytest.mark.parametrize("momento, abierto, cuando", [
    (datetime(2026, 11, 3, 8, 59), False, "hoy a partir de las 9:00"),
    (datetime(2026, 11, 3, 9, 0), True, "en menos de 24 horas, dentro del horario de atención"),
    (datetime(2026, 11, 3, 19, 59), True, "en menos de 24 horas, dentro del horario de atención"),
    (datetime(2026, 11, 3, 20, 0), False, "mañana a partir de las 9:00"),
    (datetime(2026, 11, 3, 0, 0), False, "hoy a partir de las 9:00"),
    (datetime(2026, 11, 7, 17, 59), True, "en menos de 24 horas, dentro del horario de atención"),
    (datetime(2026, 11, 7, 18, 0), False, "mañana a partir de las 9:00"),
    (datetime(2026, 12, 25, 12, 0), True, "en menos de 24 horas, dentro del horario de atención"),
    (datetime(2026, 12, 25, 19, 0), False, "mañana a partir de las 9:00"),
    (datetime(2026, 11, 1, 18, 30), False, "mañana a partir de las 9:00"),
])
def test_horario(momento, abierto, cuando):
    assert horario(momento)[0] is abierto
    assert horario(momento)[2] == cuando


def test_ficha_hostil_se_neutraliza():
    sucia = {"nombre": "<img src=x onerror=alert(1)>Ana", "telefono": "612 345 678", "ciudad": "Madrid</b><script>",
             "servicio": "Gratis para todos", "urgencia": "sí", "escalar": 1, "motivo_escalado": "[x](javascript:alert(1))<i>",
             "llamada_agendada": True, "campo_extra": "no debe pasar"}
    limpia = limpiar_ficha(sucia)
    assert set(limpia) == {"nombre", "telefono", "ciudad", "servicio", "urgencia", "menciona_dependencia", "escalar",
                           "motivo_escalado", "llamada_agendada"}
    for valor in limpia.values():
        assert not isinstance(valor, str) or not any(c in valor for c in "<>[]()`*_#|\\")
    assert limpia["servicio"] is None and limpia["urgencia"] is False and limpia["escalar"] is False
    assert limpia["telefono"] == "612345678" and limpia["llamada_agendada"] is True


@pytest.mark.parametrize("entrada", [None, [], "texto", 5, {"telefono": {"a": 1}}, {"nombre": 123}, {"nombre": "x" * 5000}])
def test_ficha_con_tipos_inesperados_no_rompe(entrada):
    assert isinstance(limpiar_ficha(entrada), dict)
    assert len(limpiar_ficha({"nombre": "x" * 5000})["nombre"]) <= 60


def test_telefono_falso_del_modelo_se_descarta():
    assert limpiar_ficha({"telefono": "me llamo Ana"})["telefono"] is None
    assert limpiar_ficha({"telefono": 612345678})["telefono"] == "612345678"


def test_lead_malicioso_no_inyecta_html_en_la_cola(con, tmp_path, monkeypatch):
    """Una familia escribe HTML en el chat, el modelo lo copia en la ficha y llega a la cola del equipo."""
    import comun
    copia = tmp_path / "crm.db"
    shutil.copy(RAIZ / "datos" / "crm.db", copia)
    monkeypatch.setattr(comun, "DB", copia)
    import sqlite3
    c = sqlite3.connect(copia)
    c.execute("CREATE TABLE IF NOT EXISTS leads_web (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, canal TEXT, "
              "ficha TEXT, conversacion TEXT)")
    ficha = {"nombre": "<img src=x onerror=alert(1)> **negrita**", "ciudad": "Madrid", "servicio": "Interna",
             "urgencia": True, "telefono": "612345678"}
    c.execute("INSERT INTO leads_web (fecha, canal, ficha, conversacion) VALUES (?,?,?,?)",
              ("2026-11-02T22:00", "Chat", json.dumps(ficha), "[]"))
    c.commit()
    c.close()
    at = AppTest.from_file(str(RAIZ / "app" / "paginas" / "primera_llamada.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert "onerror" not in texto and "<img" not in texto
