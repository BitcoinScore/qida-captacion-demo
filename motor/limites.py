"""Límites de uso de la web de la familia: contra abuso, coste del modelo y bots. Funciones puras, para poder probarlas.

Son límites por sesión del navegador: en producción irían también por IP y por día en el servidor (y, en el formulario, un
captcha o una comprobación de bots gestionada, que no se añade a la demo para no meter otro tercero).
"""
MAX_CARACTERES = 600        # por mensaje del chat
MAX_MENSAJES = 30           # mensajes de la familia por conversación
MAX_ENVIOS_FORMULARIO = 5   # por sesión
ESPERA_MINIMA_FORMULARIO = 3.0  # segundos entre que se pinta el formulario y se envía: una persona no es tan rápida
MENSAJES_RECIENTES = 20     # lo que se manda al modelo: acota el coste y el tamaño del prompt


def validar_mensaje(texto: str, enviados: int) -> tuple[bool, str]:
    """(¿se acepta?, motivo para enseñar a la familia). Nunca se llama al modelo con un mensaje rechazado."""
    if enviados >= MAX_MENSAJES:
        return False, ("Hemos llegado al máximo de mensajes de esta conversación. Déjanos tu teléfono en el formulario o "
                       "llámanos y una persona te atenderá.")
    if not texto or not texto.strip():
        return False, "El mensaje está vacío."
    if len(texto) > MAX_CARACTERES:
        return False, f"El mensaje es demasiado largo (máximo {MAX_CARACTERES} caracteres). Cuéntamelo en varias partes."
    return True, ""


def validar_formulario(envios: int, segundos_desde_que_se_pinto: float) -> tuple[bool, str]:
    if envios >= MAX_ENVIOS_FORMULARIO:
        return False, "Has enviado demasiadas solicitudes seguidas. Llámanos al teléfono de arriba y te atendemos."
    if segundos_desde_que_se_pinto < ESPERA_MINIMA_FORMULARIO:
        return False, "Revisa los datos un momento y vuelve a pulsar el botón."
    return True, ""


def historial_para_el_modelo(historial: list[dict]) -> list[dict]:
    """Solo los últimos mensajes: la conversación de una familia no necesita más y un abuso no encarece cada respuesta."""
    return historial[-MENSAJES_RECIENTES:]
