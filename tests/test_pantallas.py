"""Prueba de humo: cada pantalla se carga sin excepciones (modo grabado, sin modelo)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGINAS = sorted((Path(__file__).resolve().parent.parent / "app" / "paginas").glob("*.py"))


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.stem)
def test_pantalla_carga(pagina, con):
    at = AppTest.from_file(str(pagina), default_timeout=60).run()
    assert not at.exception, at.exception


def test_chat_abre_en_modo_grabado(con):
    pagina = Path(__file__).resolve().parent.parent / "app" / "paginas" / "web.py"
    at = AppTest.from_file(str(pagina), default_timeout=60).run()
    boton = [b for b in at.button if "Asistente virtual" in b.label]
    assert boton, "no encuentro el botón del asistente"
    boton[0].click().run()
    assert not at.exception, at.exception
    assert any("Modo grabado" in m.value for m in at.markdown)


def test_cola_filtra_por_ciudad(con):
    pagina = Path(__file__).resolve().parent.parent / "app" / "paginas" / "primera_llamada.py"
    at = AppTest.from_file(str(pagina), default_timeout=60).run()
    at.sidebar.multiselect[0].set_value(["Sevilla"]).run()
    assert not at.exception, at.exception
