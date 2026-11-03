"""Datos de salud y abuso: consentimiento registrado, retención, borrado y límites de uso."""
import json
import sqlite3
from datetime import datetime, timedelta

import pytest

from motor import leads, limites

AHORA = datetime(2026, 11, 3, 23, 10)


@pytest.fixture
def bd():
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


def test_cada_lead_guarda_que_consintio_y_cuando(bd):
    lead_id = leads.guardar(bd, AHORA, "Chat", {"telefono": "612345678"}, [{"rol": "usuario", "texto": "hola"}], "Acepto X")
    consentimiento = json.loads(bd.execute("SELECT consentimiento FROM leads_web WHERE id=?", (lead_id,)).fetchone()[0])
    assert consentimiento["texto"] == "Acepto X" and consentimiento["version"] == leads.VERSION_CONSENTIMIENTO
    assert consentimiento["aceptado_en"]


def test_los_leads_caducan_a_los_30_dias(bd):
    ahora_real = datetime(2026, 11, 3, 12, 0)
    viejo = leads.guardar(bd, AHORA, "Formulario", {"telefono": "611111111"}, None, "c", ahora_real - timedelta(days=31))
    reciente = leads.guardar(bd, AHORA, "Formulario", {"telefono": "622222222"}, None, "c", ahora_real - timedelta(days=29))
    assert leads.purgar(bd, ahora_real) == 1
    ids = {i for (i,) in bd.execute("SELECT id FROM leads_web")}
    assert ids == {reciente} and viejo not in ids


def test_guardar_purga_los_caducados(bd):
    ahora_real = datetime(2026, 11, 3, 12, 0)
    leads.guardar(bd, AHORA, "Chat", {}, None, "c", ahora_real - timedelta(days=40))
    leads.guardar(bd, AHORA, "Chat", {}, None, "c", ahora_real)
    assert bd.execute("SELECT COUNT(*) FROM leads_web").fetchone()[0] == 1


def test_borrado_por_id_y_por_telefono(bd):
    a = leads.guardar(bd, AHORA, "Chat", {"telefono": "612345678"}, None, "c")
    leads.guardar(bd, AHORA, "Formulario", {"telefono": "612345678"}, None, "c")
    otro = leads.guardar(bd, AHORA, "Formulario", {"telefono": "699999999"}, None, "c")
    assert leads.borrar(bd, a) == 1
    assert leads.borrar_por_telefono(bd, "612345678") == 1
    assert [i for (i,) in bd.execute("SELECT id FROM leads_web")] == [otro]


def test_bases_antiguas_sin_columnas_de_consentimiento_se_actualizan(bd):
    bd.execute("CREATE TABLE leads_web (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, canal TEXT, ficha TEXT, conversacion TEXT)")
    bd.execute("INSERT INTO leads_web (fecha, canal, ficha, conversacion) VALUES ('x','Chat','{}','[]')")
    assert leads.purgar(bd) == 0
    leads.guardar(bd, AHORA, "Chat", {}, None, "c")
    assert bd.execute("SELECT COUNT(*) FROM leads_web").fetchone()[0] == 2


@pytest.mark.parametrize("texto, enviados, ok", [
    ("Hola", 0, True), ("a" * limites.MAX_CARACTERES, 0, True), ("a" * (limites.MAX_CARACTERES + 1), 0, False),
    ("", 0, False), ("   \n ", 0, False), ("Hola", limites.MAX_MENSAJES - 1, True), ("Hola", limites.MAX_MENSAJES, False),
])
def test_limites_del_chat(texto, enviados, ok):
    assert limites.validar_mensaje(texto, enviados)[0] is ok


def test_limites_del_formulario():
    assert limites.validar_formulario(0, 10)[0] is True
    assert limites.validar_formulario(0, 0.5)[0] is False
    assert limites.validar_formulario(limites.MAX_ENVIOS_FORMULARIO, 60)[0] is False


def test_el_modelo_solo_recibe_los_ultimos_mensajes():
    historial = [{"rol": "usuario", "texto": str(i)} for i in range(100)]
    assert len(limites.historial_para_el_modelo(historial)) == limites.MENSAJES_RECIENTES
    assert limites.historial_para_el_modelo(historial)[-1]["texto"] == "99"


from motor import conversacion


def test_turno_guarda_pregunta_y_respuesta_juntas():
    historial = []
    texto, ficha = conversacion.turno(historial, "Hola", lambda h, a: ("Respuesta", {"ciudad": "Madrid"}), AHORA, "600000000")
    assert texto == "Respuesta" and ficha == {"ciudad": "Madrid"}
    assert [m["rol"] for m in historial] == ["usuario", "asistente"]


def test_si_la_ejecucion_se_cancela_el_historial_no_cambia():
    """Streamlit cancela la ejecución (excepción que no es `Exception`) si se pulsa otro botón mientras responde el modelo."""
    class Cancelada(BaseException):
        pass

    def responder_cancelado(h, a):
        raise Cancelada

    historial = [{"rol": "usuario", "texto": "antes"}, {"rol": "asistente", "texto": "respuesta"}]
    with pytest.raises(Cancelada):
        conversacion.turno(historial, "pregunta cancelada", responder_cancelado, AHORA, "600000000")
    assert len(historial) == 2, "no puede quedar una pregunta sin contestar"


def test_si_el_modelo_falla_la_familia_recibe_un_respaldo_y_el_telefono():
    def falla(h, a):
        raise RuntimeError("sin red")
    historial = []
    texto, ficha = conversacion.turno(historial, "Hola", falla, AHORA, "656 726 469")
    assert "656 726 469" in texto and ficha == {} and len(historial) == 2
