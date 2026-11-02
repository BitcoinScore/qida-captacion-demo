"""Prueba de humo: cada pantalla se carga sin excepciones (modo grabado, sin modelo)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGINAS = sorted((Path(__file__).resolve().parent.parent / "app" / "paginas").glob("*.py"))


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.stem)
def test_pantalla_carga(pagina, con):
    at = AppTest.from_file(str(pagina), default_timeout=60).run()
    assert not at.exception, at.exception
