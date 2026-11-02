"""Diseño del chat: lo que se pinta es seguro y el 112 siempre se puede pulsar."""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import chat_ui  # noqa: E402

BASE = datetime(2026, 11, 3, 23, 10)


def test_nada_de_html_de_la_familia_ni_del_modelo_llega_a_la_pantalla():
    html = chat_ui.burbujas([{"rol": "usuario", "texto": "<img src=x onerror=alert(1)> <script>alert(2)</script>"},
                             {"rol": "asistente", "texto": "[clic](javascript:alert(3)) <b onmouseover=x>hola</b>"}], BASE, "mañana a las 9:00")
    assert "<script" not in html and "<img" not in html and "onerror=" not in html.replace("&lt;img src=x onerror=", "")
    assert "&lt;script&gt;" in html and "&lt;img" in html
    assert "<b onmouseover" not in html


def test_negrita_y_saltos_de_linea_si_se_permiten():
    assert chat_ui.formato("**Hola**\nadiós") == "<b>Hola</b><br>adiós"


def test_el_112_y_el_024_son_enlaces_que_marcan():
    for texto, numero in (("Llama al 112 ahora", "112"), ("si corre peligro, llama al 112.", "112"), ("la línea 024 es gratuita", "024"),
                          ("**112**", "112")):
        assert f'href="tel:{numero}"' in chat_ui.formato(texto), texto


def test_un_112_dentro_de_un_telefono_o_de_una_cifra_no_se_convierte_en_enlace():
    for texto in ("Llámame al 656 112 233", "mi número 600 112", "código 1120", "655-112-3", "tel 91 112.4"):
        assert "tel:" not in chat_ui.formato(texto), texto


def test_la_cabecera_tiene_el_112_pulsable_siempre():
    assert 'href="tel:112"' in chat_ui.cabecera(False, "mañana a las 9:00", "tel:+34656726469")
    assert 'href="tel:112"' in chat_ui.cabecera(True, "en menos de 24 horas", "tel:+34656726469")


def test_la_ia_se_declara_en_la_cabecera_y_en_la_bienvenida():
    assert "asistente virtual" in chat_ui.cabecera(False, "", "").lower()
    assert "IA, no una persona" in chat_ui.bienvenida("mañana")


def test_el_resumen_enseña_lo_anotado_y_no_el_numero_de_telefono():
    html = chat_ui.resumen({"ciudad": "Sevilla", "urgencia": True, "telefono": "655111222", "escalar": True})
    assert "Sevilla" in html and "Urgente" in html and "Teléfono anotado" in html and "Lo ve una persona" in html
    assert "655111222" not in html
    assert chat_ui.resumen({}) == ""


def test_el_resumen_escapa_el_texto_de_la_ficha():
    assert "<script" not in chat_ui.resumen({"ciudad": "<script>alert(1)</script>"})


def test_el_indicador_de_escritura_y_el_mensaje_pendiente():
    html = chat_ui.burbujas([], BASE, "mañana", escribiendo=True, pendiente="Hola")
    assert "escribiendo" in html and "Hola" in html and html.index("Hola") < html.index("escribiendo")


def test_las_horas_avanzan_un_minuto_por_intercambio():
    assert chat_ui.hora(BASE, 0) == "23:10" and chat_ui.hora(BASE, 2) == "23:11" and chat_ui.hora(BASE, 5) == "23:12"


def test_el_lanzador_saluda_segun_la_hora_y_se_puede_cerrar():
    cerrado = chat_ui.lanzador(chat_ui.saludo(False, "mañana a partir de las 9:00", BASE))
    assert "23:10" in cerrado and "ya no hay nadie al teléfono" in cerrado and "ql-cerrar" in cerrado
    abierto = chat_ui.lanzador(chat_ui.saludo(True, "en menos de 24 horas", BASE))
    assert "cuidar a un familiar" in abierto
    assert not re.search(r"<script", cerrado + abierto)


def test_la_tarjeta_del_equipo_enseña_la_ficha_y_escapa_el_texto():
    html = chat_ui.equipo_html({"ciudad": "Sevilla", "telefono": "655111222", "urgencia": True, "escalar": True,
                                "motivo_escalado": "<img src=x onerror=alert(1)>", "llamada_agendada": True}, "mañana a las 9:00")
    assert "Sevilla" in html and "655111222" in html and "Pasa a una persona" in html and "Llamada agendada" in html
    assert "<img" not in html and "&lt;img" in html
    vacia = chat_ui.equipo_html({}, "mañana")
    assert vacia.count("pendiente") >= 4 and "Pasa a una persona" not in vacia
