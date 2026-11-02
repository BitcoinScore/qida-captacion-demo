from eval import ejecutar
from motor import asistente, llm


def test_separa_texto_y_ficha():
    texto, ficha = asistente.separar('Hola, ¿en qué ciudad?\n###LEAD### {"telefono": null, "escalar": false}')
    assert texto == "Hola, ¿en qué ciudad?" and ficha == {"telefono": None, "escalar": False}


def test_ficha_ausente_no_rompe():
    assert asistente.separar("Hola")[1] == {}


def test_reglas_clave_en_el_prompt():
    for regla in ("asistente virtual con IA", "FIDELIDAD", "112", "Cobertura"):
        assert regla in asistente.SISTEMA


def test_detecta_precio_cerrado():
    caso = {"categoria": "precio", "esperado": {"escalar": False, "pide_telefono": False, "agendar": False}}
    assert not ejecutar.comprobar(caso, "Te sale por 14 euros la hora", {"escalar": False})["sin_precio_cerrado"]
    assert ejecutar.comprobar(caso, "Desde 170 €/mes, presupuesto gratis", {"escalar": False})["sin_precio_cerrado"]


def test_modo_grabado_en_pruebas():
    assert llm.modo() == "grabado"
