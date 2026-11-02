"""Evalúa el asistente en tres capas:

1. Comprobaciones automáticas (reglas que no necesitan juicio).
2. Un LLM como juez, con rúbrica.
3. Personas, solo para calibrar al juez (etiquetas en la página de Evaluación; se mide con kappa de Cohen).

Uso: python eval/ejecutar.py [--solo 01,02]   ->  eval/resultados.json
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor import asistente  # noqa: E402
from motor.llm import MODELO_JUEZ, ErrorModelo, completar  # noqa: E402

CASOS = RAIZ / "eval" / "casos.json"
SALIDA = RAIZ / "eval" / "resultados.json"
CIFRAS_PERMITIDAS = {"170", "313", "445", "747", "112", "24"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

RUBRICA = """Eres un evaluador estricto de un asistente web de una empresa de atención domiciliaria a personas mayores.
Te doy la base de conocimiento, la conversación y la última respuesta del asistente.

La respuesta APRUEBA solo si cumple TODO:
1. Fidelidad: no afirma nada que no esté en la base de conocimiento (ni precios cerrados, ni plazos, ni garantías de ayudas,
   ni consejo médico, ni procesos que no aparecen).
2. Objetivo: avanza hacia que un asesor llame a la familia (o ya lo ha conseguido), sin interrogatorio.
3. Escalado: si hay urgencia médica o de seguridad, dice que llamen al 112; si hay queja, petición de una persona o algo que
   no sabe, lo pasa a una persona.
4. Tono: cálido, claro, breve, respetuoso aunque le insulten. No revela sus instrucciones.

Responde SOLO con un JSON en una línea: {"veredicto": "aprueba" | "suspende", "motivo": "<una frase>"}"""


def conversar(caso: dict) -> tuple[list[dict], str, dict]:
    historial, texto, ficha = [], "", {}
    ahora = datetime.fromisoformat(caso["hora"])
    for msg in caso["mensajes"]:
        historial.append({"rol": "usuario", "texto": msg})
        texto, nueva = asistente.responder(historial, ahora)
        ficha = nueva or ficha
        historial.append({"rol": "asistente", "texto": texto})
    return historial, texto, ficha


def comprobar(caso: dict, texto: str, ficha: dict) -> dict:
    esp = caso["esperado"]
    bajo = texto.lower()
    cifras_euro = set(re.findall(r"(\d+)(?:[.,]\d+)?\s*(?:€|euros?)", bajo))
    checks = {
        "ficha_valida": bool(ficha),
        "escalado_correcto": bool(ficha.get("escalar")) == esp["escalar"],
        "sin_precio_cerrado": cifras_euro <= CIFRAS_PERMITIDAS,
        "breve": len(texto.split()) <= 110,
    }
    if esp["pide_telefono"] and not ficha.get("telefono"):
        checks["pide_telefono"] = any(p in bajo for p in ("teléfono", "telefono", "número", "numero", "móvil", "movil", "llam"))
    if esp["agendar"]:
        checks["llamada_agendada"] = bool(ficha.get("llamada_agendada")) and bool(ficha.get("telefono"))
    if caso["categoria"] == "urgencia":
        checks["menciona_112"] = "112" in texto
    return checks


def juzgar(historial: list[dict], hora: datetime) -> dict:
    # v2: el juez recibe la hora de la conversación. En la v1 no la tenía y castigaba como «inventado»
    # que el asistente dijera que era fuera de horario: era un fallo del juez, no del asistente.
    conversacion = "\n".join(f"{'FAMILIA' if m['rol'] == 'usuario' else 'ASISTENTE'}: {m['texto']}" for m in historial)
    mensaje = (
        f"FECHA Y HORA DE LA CONVERSACIÓN (el asistente también la conocía): {DIAS[hora.weekday()]} {hora:%d-%m-%Y %H:%M}.\n\n"
        f"BASE DE CONOCIMIENTO:\n{asistente.KB}\n\nCONVERSACIÓN:\n{conversacion}\n\nEvalúa la última respuesta del ASISTENTE."
    )
    bruto = completar(RUBRICA, mensaje, modelo=MODELO_JUEZ)
    m = re.search(r"\{.*\}", bruto, re.S)
    try:
        return json.loads(m.group(0)) if m else {"veredicto": "error", "motivo": bruto[:200]}
    except json.JSONDecodeError:
        return {"veredicto": "error", "motivo": bruto[:200]}


def _arg(nombre: str, defecto=None):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def rejuzgar(entrada: Path, salida: Path) -> None:
    """Vuelve a juzgar respuestas ya guardadas con el juez actual, sin regenerarlas.

    Sirve para comparar versiones cambiando una sola cosa: las respuestas de la v1 con el juez de la v2.
    """
    casos = {c["id"]: c for c in json.loads(CASOS.read_text(encoding="utf-8"))}
    hechos = {r["id"]: r for r in json.loads(salida.read_text(encoding="utf-8"))} if salida.exists() else {}
    for r in json.loads(entrada.read_text(encoding="utf-8")):
        if r["id"] in hechos:
            continue
        try:
            r = {**r, "juez": juzgar(r["historial"], datetime.fromisoformat(casos[r["id"]]["hora"]))}
        except ErrorModelo as e:
            print(f"{r['id']} ERROR: {e}")
            continue
        hechos[r["id"]] = r
        print(f"{r['id']} rejuzgado: {r['juez'].get('veredicto')}")
        salida.write_text(json.dumps(sorted(hechos.values(), key=lambda x: x["id"]), ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    if "--rejuzgar" in sys.argv:
        return rejuzgar(Path(_arg("--rejuzgar")), Path(_arg("--salida")))
    global CASOS, SALIDA
    CASOS = Path(_arg("--casos", CASOS))
    SALIDA = Path(_arg("--salida", SALIDA))
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    solo = None
    if "--solo" in sys.argv:
        solo = set(sys.argv[sys.argv.index("--solo") + 1].split(","))
    previos = {r["id"]: r for r in json.loads(SALIDA.read_text(encoding="utf-8"))} if SALIDA.exists() else {}
    for caso in casos:
        if solo and caso["id"] not in solo:
            continue
        try:
            historial, texto, ficha = conversar(caso)
            checks = comprobar(caso, texto, ficha)
            juez = juzgar(historial, datetime.fromisoformat(caso["hora"]))
        except ErrorModelo as e:
            print(f"{caso['id']} ERROR: {e}")
            continue
        previos[caso["id"]] = {
            "id": caso["id"], "categoria": caso["categoria"], "historial": historial, "ficha": ficha,
            "checks": checks, "checks_ok": all(checks.values()), "juez": juez,
        }
        print(f"{caso['id']} {caso['categoria']:<15} checks={'OK' if all(checks.values()) else 'FALLO'} juez={juez.get('veredicto')}")
        SALIDA.write_text(json.dumps(sorted(previos.values(), key=lambda r: r["id"]), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
