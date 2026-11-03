"""Reglas de contacto de la web de la familia: teléfono, horario de atención y limpieza de la ficha que devuelve el modelo.

Son funciones puras (sin Streamlit) para poder probarlas. Lo que escribe la familia o devuelve el modelo es entrada no
fiable: la ficha se valida antes de guardarla en el CRM o de pintarla.
"""
import re
from datetime import datetime

FESTIVOS = {(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)}
SERVICIOS_FICHA = {"Por horas", "Interna", "Fin de semana", "Nocturna"}
_TEXTO = re.compile(r"[^\w .'\-ÁÉÍÓÚÜÑáéíóúüñ]", re.UNICODE)


def normalizar_telefono(texto: str) -> str | None:
    """Acepta «612 345 678», «612-345-678», «+34 612345678» o «0034…»; devuelve 9 cifras o None."""
    cifras = re.sub(r"\D", "", str(texto) if texto is not None else "")
    if cifras.startswith("0034"):
        cifras = cifras[4:]
    elif cifras.startswith("34") and len(cifras) == 11:
        cifras = cifras[2:]
    return cifras if re.fullmatch(r"[6789]\d{8}", cifras) else None


def horario(momento: datetime) -> tuple[bool, str, str]:
    """(¿abierto?, horario del día, cuándo llamamos). Fines de semana y festivos: de 9:00 a 18:00."""
    reducido = momento.weekday() >= 5 or (momento.month, momento.day) in FESTIVOS
    cierre = 18 if reducido else 20
    abierto = 9 <= momento.hour < cierre
    franja = f"9:00–{cierre}:00 ({'fines de semana y festivos' if reducido else 'de lunes a viernes'})"
    if abierto:
        cuando = "en menos de 24 horas, dentro del horario de atención"
    elif momento.hour < 9:
        cuando = "hoy a partir de las 9:00"
    else:
        cuando = "mañana a partir de las 9:00"
    return abierto, franja, cuando


def _texto_corto(valor, largo: int) -> str | None:
    """Solo letras, números, espacios y . ' - ; sin marcas HTML ni de Markdown; recortado."""
    if not isinstance(valor, str):
        return None
    limpio = " ".join(_TEXTO.sub("", valor).split())[:largo]
    return limpio or None


def limpiar_ficha(ficha) -> dict:
    """Ficha del lead tal como la puede aceptar el CRM: campos conocidos, tipos correctos y texto sin marcas.
    El teléfono solo se conserva si es un teléfono español válido."""
    if not isinstance(ficha, dict):
        return {}
    servicio = ficha.get("servicio")
    return {
        "nombre": _texto_corto(ficha.get("nombre"), 60),
        "telefono": normalizar_telefono(ficha["telefono"]) if isinstance(ficha.get("telefono"), (str, int)) and ficha.get("telefono") else None,
        "ciudad": _texto_corto(ficha.get("ciudad"), 40),
        "servicio": servicio if servicio in SERVICIOS_FICHA else None,
        "urgencia": ficha.get("urgencia") is True,
        "menciona_dependencia": ficha.get("menciona_dependencia") is True,
        "escalar": ficha.get("escalar") is True,
        "motivo_escalado": _texto_corto(ficha.get("motivo_escalado"), 200),
        "llamada_agendada": ficha.get("llamada_agendada") is True,
    }
