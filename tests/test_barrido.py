"""Barrido de controles: cada pantalla con cada periodo, cada ciudad sola y con la selección vacía, como haría un QA."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGINAS = Path(__file__).resolve().parent.parent / "app" / "paginas"
CIUDADES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "A Coruña"]


def abrir(nombre: str) -> AppTest:
    at = AppTest.from_file(str(PAGINAS / f"{nombre}.py"), default_timeout=90).run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("pagina", ["viaje", "web"])
def test_no_se_cuelan_tablas_sueltas(pagina, con):
    """Streamlit pinta cualquier expresión suelta del script («magic»): una línea mal puesta vuelca tablas en pantalla."""
    assert len(abrir(pagina).dataframe) == 0


def test_viaje_con_cada_periodo(con):
    at = abrir("viaje")
    selector = next(s for s in at.sidebar.selectbox)
    for opcion in selector.options:
        selector.set_value(opcion).run()
        assert not at.exception, f"periodo «{opcion}»: {at.exception}"
        selector = next(s for s in at.sidebar.selectbox)


@pytest.mark.parametrize("pagina", ["viaje", "primera_llamada", "descubre", "se_queda"])
@pytest.mark.parametrize("ciudades", [[c] for c in CIUDADES] + [[]], ids=lambda c: "+".join(c) or "ninguna")
def test_ciudades(pagina, ciudades, con):
    at = abrir(pagina)
    if not at.sidebar.multiselect:
        pytest.skip("la pantalla no filtra por ciudad")
    at.sidebar.multiselect[0].set_value(ciudades).run()
    assert not at.exception, at.exception


def test_descubre_con_cada_periodo(con):
    at = abrir("descubre")
    radio = at.sidebar.radio[0]
    for opcion in radio.options:
        radio.set_value(opcion).run()
        assert not at.exception, f"periodo «{opcion}»: {at.exception}"
        radio = at.sidebar.radio[0]


def test_descubre_con_cada_metrica_del_mapa_de_calor(con):
    at = abrir("descubre")
    radio = next(r for r in at.radio if r.label == "Mostrar")
    for opcion in radio.options:
        radio.set_value(opcion).run()
        assert not at.exception, f"métrica «{opcion}»: {at.exception}"
        radio = next(r for r in at.radio if r.label == "Mostrar")


def test_web_a_cualquier_hora_y_dia(con):
    """Formulario y cabecera en los horarios límite: no se rompe y siempre hay teléfono y 112 visibles."""
    from datetime import date, time
    at = abrir("web")
    for dia in (date(2026, 11, 1), date(2026, 11, 7), date(2026, 12, 25), date(2027, 2, 29 - 1)):
        for hora in (time(0, 0), time(8, 59), time(9, 0), time(19, 59), time(23, 59)):
            at.sidebar.date_input[0].set_value(dia)
            at.sidebar.time_input[0].set_value(hora).run()
            assert not at.exception, f"{dia} {hora}: {at.exception}"
            assert "656 726 469" in " ".join(m.value for m in at.markdown)


def test_formulario_valida_y_confirma(con, tmp_path, monkeypatch):
    import shutil

    import comun
    copia = tmp_path / "crm.db"
    shutil.copy(PAGINAS.parent.parent / "datos" / "crm.db", copia)
    monkeypatch.setattr(comun, "DB", copia)
    import sqlite3

    def guardados() -> int:
        c = sqlite3.connect(copia)
        try:
            return c.execute("SELECT COUNT(*) FROM leads_web WHERE canal='Formulario'").fetchone()[0]
        except sqlite3.OperationalError:
            return 0
        finally:
            c.close()

    antes = guardados()
    at = abrir("web")

    def rellenar(tel, cp, acepto):
        at.text_input(key="telefono-pagina").set_value(tel)
        at.text_input(key="cp-pagina").set_value(cp)
        at.checkbox(key="acepto-pagina").set_value(acepto)
        next(b for b in at.button if b.label == "Quiero que me llaméis").click().run()

    rellenar("abc", "28001", True)
    assert "teléfono de 9 cifras" in " ".join(m.value for m in at.markdown)
    rellenar("612345678", "2800", True)
    assert "código postal de 5 cifras" in " ".join(m.value for m in at.markdown)
    rellenar("612345678", "28001", False)
    assert "casilla" in " ".join(m.value for m in at.markdown)
    rellenar("612345678", "28001", True)
    assert "Revisa los datos" in " ".join(m.value for m in at.markdown) and guardados() == antes
    from motor import limites
    monkeypatch.setattr(limites, "ESPERA_MINIMA_FORMULARIO", 0)
    rellenar("612345678", "28001", True)
    assert "Recibido" in " ".join(m.value for m in at.markdown)
    assert guardados() - antes == 1, "el lead debe guardarse una sola vez"
    rellenar("612 345 678", "28001", True)
    assert guardados() - antes == 1, "el mismo teléfono no debe duplicar el lead"
    rellenar("699 111 222", "41001", True)
    assert guardados() - antes == 2
    assert "699 111 222" in " ".join(m.value for m in at.markdown), "la confirmación debe mostrar el último teléfono"


def test_web_estructura_de_una_pagina_de_scroll(con):
    """Un solo h1, los enlaces del menú llevan a secciones que existen y el teléfono, el 112 y las preguntas están."""
    import re
    texto = " ".join(m.value for m in abrir("web").markdown)
    assert len(re.findall(r"<h1[ >]", texto)) == 1
    enlaces = set(re.findall(r'href="#([\w-]+)"', texto))
    ids = set(re.findall(r"id=['\"]([\w-]+)['\"]", texto))
    assert enlaces and enlaces <= ids, f"enlaces sin destino: {enlaces - ids}"
    assert "112" in texto and "656 726 469" in texto and "desde 170" in texto.lower()


def test_el_chat_no_exige_casilla_para_escribir(con, monkeypatch):
    """En una urgencia nadie debe tener que marcar nada para pedir ayuda: se informa y se puede escribir ya."""
    from motor import llm
    monkeypatch.setattr(llm, "modo", lambda: "vivo")
    at = abrir("web")
    next(b for b in at.button if "Asistente virtual" in b.label).click().run()
    assert not at.exception, at.exception
    assert not any("acepto" in (c.key or "") for c in at.checkbox if (c.key or "").endswith("chat"))
    assert at.chat_input and not at.chat_input[0].disabled
    assert any("Prefiero que me llame" in b.label for b in at.button)
    assert any("aceptas que Qida use lo que cuentes" in m.value for m in at.markdown)
    assert any('href="tel:112"' in m.value for m in at.markdown), "el 112 debe poder pulsarse dentro del chat"
