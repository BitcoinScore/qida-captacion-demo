"""Llamada al modelo.

Dos modos (variable de entorno QIDA_MODO; por defecto, automático):
- «vivo»: Claude Code en local (`claude -p`) con la sesión del usuario; no necesita clave de API.
- «grabado»: sin modelo; el chat reproduce conversaciones reales de la última evaluación (eval/resultados_v3*.json).
  Es el modo de quien clona el repo sin Claude Code.
Para producción, `completar` pasaría a la API de Anthropic (`client.messages.create`) con la clave en un gestor de secretos.
"""
import json
import os
import shutil
import subprocess

MODELO_ASISTENTE = "haiku"   # rápido y barato para conversar
MODELO_JUEZ = "sonnet"       # más criterio para evaluar


class ErrorModelo(RuntimeError):
    pass


def modo() -> str:
    """«vivo» si hay Claude Code (o QIDA_MODO=vivo); si no, «grabado»."""
    forzado = os.environ.get("QIDA_MODO", "").strip().lower()
    if forzado in ("vivo", "grabado"):
        return forzado
    return "vivo" if shutil.which("claude") else "grabado"


def completar(sistema: str, mensaje: str, modelo: str = MODELO_ASISTENTE, timeout: int = 120) -> str:
    ejecutable = shutil.which("claude")
    if not ejecutable:
        raise ErrorModelo("No encuentro el comando `claude`. ¿Está instalado Claude Code?")
    cmd = [
        ejecutable, "-p",
        "--model", modelo,
        "--system-prompt", sistema,
        "--tools", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format", "json",
    ]
    proc = subprocess.run(cmd, input=mensaje, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    salida = proc.stdout.strip()
    try:
        datos = json.loads(salida)
    except json.JSONDecodeError:
        raise ErrorModelo((proc.stderr or salida or "sin respuesta").strip()[:500]) from None
    if datos.get("is_error"):
        raise ErrorModelo(str(datos.get("result", datos))[:500])
    return datos.get("result", "").strip()
