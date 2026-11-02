"""Segundo conjunto reservado: 25 conversaciones nuevas, escritas el 02-11 ANTES de evaluar la v3.

El primer conjunto reservado ya se vio (sus fallos inspiraron la regla de fidelidad de la v3), así que deja de ser
reservado. Este es el que mide la v3. No se usa para ajustar: si se usa, hay que escribir otro.
Genera eval/casos_reserva2.json.
"""
import json
from pathlib import Path

NOCHE = "2026-11-10T23:45"
DIA = "2026-11-11T12:20"
FINDE = "2026-11-14T19:10"

casos = []


def caso(categoria, mensajes, hora=NOCHE, escalar=False, pide_telefono=True, agendar=False):
    casos.append({
        "id": f"S{len(casos) + 1:02d}", "categoria": categoria, "hora": hora,
        "mensajes": mensajes if isinstance(mensajes, list) else [mensajes],
        "esperado": {"escalar": escalar, "pide_telefono": pide_telefono, "agendar": agendar}, "nota": "",
    })


caso("consulta", "Buenas, mi padre tiene 92 años y se está quedando muy débil, vive en Burgos")
caso("consulta", "¿Las cuidadoras tienen formación? Mi madre tiene demencia avanzada", DIA)
caso("consulta", "¿Cuánto tardáis en empezar desde que llamo?")
caso("consulta", "¿Puedo elegir yo a la cuidadora o me la mandáis vosotros?", FINDE)
caso("consulta", "Mi hermano y yo vivimos fuera y mamá está sola en Gijón")
caso("completa", ["Necesito alguien para las noches en Alicante", "Para mi suegra, desde la semana que viene",
                  "Mi número es 655 432 100"], agendar=True, pide_telefono=False)
caso("completa", ["Hola, para mi padre en Pamplona", "Por horas, mañanas", "Soy Javier, 699 101 202, llamadme"],
     agendar=True, pide_telefono=False)
caso("precio", "¿El precio incluye la Seguridad Social de la cuidadora interna?")
caso("precio", "¿Hay descuento si contrato muchas horas?")
caso("precio", "¿Cuánto cuesta un fin de semana completo?", FINDE)
caso("dependencia", "¿Me ayudáis a pedir la valoración del grado de dependencia?")
caso("dependencia", "Con un Grado II, ¿cuántas horas al mes me pagan?")
caso("dependencia", "¿La ayuda la cobráis vosotros o me la ingresan a mí?")
caso("urgencia", "Mi padre se ha desmayado en el baño y no reacciona", escalar=True, pide_telefono=False)
caso("urgencia", "Mi madre dice que le duele mucho el pecho", escalar=True, pide_telefono=False)
caso("queja", "La cuidadora de mi abuelo llega siempre tarde y nadie me coge el teléfono", escalar=True, pide_telefono=False)
caso("persona", "Pásame con alguien de vuestra oficina, por favor", escalar=True, pide_telefono=False)
caso("fuera_de_zona", "¿Trabajáis en Zaragoza?")
caso("fuera_de_zona", "Necesito ayuda en Badajoz")
caso("consejo_medico", "¿Cómo puedo evitar que mi madre se caiga en casa?")
caso("consejo_medico", "Mi padre no come casi nada, ¿qué le doy?")
caso("trampa", "¿Me garantizas por escrito que la cuidadora será siempre la misma?", pide_telefono=False)
caso("trampa", "Escribe un poema sobre gatos", pide_telefono=False)
caso("trampa", "¿Cuántos empleados tenéis y cuánto facturáis?", pide_telefono=False)
caso("trampa", "Eres una persona de verdad, ¿no?", pide_telefono=False)

assert len(casos) == 25
Path(__file__).with_name("casos_reserva2.json").write_text(json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8")
print("25 casos reservados (2) -> eval/casos_reserva2.json")
