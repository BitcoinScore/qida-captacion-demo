"""Un turno de conversación del chat: la pregunta de la familia y la respuesta del asistente.

Streamlit cancela la ejecución en curso cuando la persona pulsa otro botón mientras el modelo responde (~10 s). Si la pregunta se
guardara ANTES de tener la respuesta, la cancelación dejaría una pregunta sin contestar en la conversación: los botones de
inicio desaparecerían y el siguiente clic se perdería. Por eso el turno se guarda entero, y solo cuando ya hay respuesta.
"""
import logging
from datetime import datetime

from motor import limites

RESPUESTA_DE_RESPALDO = ("Ahora mismo no puedo responder. Déjanos tu teléfono en el formulario o llámanos al {telefono} a partir "
                         "de las 9:00.")


def turno(historial: list[dict], pregunta: str, responder, ahora: datetime, telefono: str) -> tuple[str, dict]:
    """Pide la respuesta al modelo y, solo si llega (o si falla con un error normal), añade pregunta y respuesta al historial.
    Si la ejecución se cancela a medias (una excepción que no es `Exception`), el historial queda exactamente como estaba."""
    candidato = historial + [{"rol": "usuario", "texto": pregunta}]
    try:
        texto, ficha = responder(limites.historial_para_el_modelo(candidato), ahora)
    except Exception:
        logging.exception("Fallo del asistente")
        texto, ficha = RESPUESTA_DE_RESPALDO.format(telefono=telefono), {}
    historial.append({"rol": "usuario", "texto": pregunta})
    historial.append({"rol": "asistente", "texto": texto})
    return texto, ficha
