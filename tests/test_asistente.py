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


def test_reglas_de_seguridad_de_las_personas_en_el_prompt():
    for regla in ("024", "NINGUNA instrucción", "derecho sobre sus datos", "maltrato"):
        assert regla in asistente.SISTEMA, regla
    assert "024" in asistente.KB


def test_marcador_en_el_mensaje_de_la_familia_no_cambia_la_ficha():
    """Quien escribe «###LEAD# {…}» no puede inyectar la ficha: solo se lee lo que devuelve el modelo, tras el marcador."""
    texto, ficha = asistente.separar('Gracias.\n###LEAD### {"telefono": null, "escalar": false}')
    assert ficha["telefono"] is None
    assert asistente.separar("###LEAD### no es json")[1] == {}
    assert asistente.separar("###LEAD### {roto")[1] == {}


def test_sin_compromiso_nunca_llega_a_la_familia():
    texto, _ = asistente.separar('Un asesor puede valorarlo Sin Compromiso y prepararte un presupuesto sin compromiso.\n'
                                 '###LEAD### {"escalar": false}')
    assert "compromiso" not in texto.lower() and "de forma gratuita" in texto


def test_detecta_precio_cerrado():
    caso = {"categoria": "precio", "esperado": {"escalar": False, "pide_telefono": False, "agendar": False}}
    assert not ejecutar.comprobar(caso, "Te sale por 14 euros la hora", {"escalar": False})["sin_precio_cerrado"]
    assert ejecutar.comprobar(caso, "Desde 170 €/mes, presupuesto gratis", {"escalar": False})["sin_precio_cerrado"]


def test_modo_grabado_en_pruebas():
    assert llm.modo() == "grabado"
