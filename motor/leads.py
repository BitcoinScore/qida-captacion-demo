"""Leads de la web (formulario y chat): guardado con consentimiento registrado, retención limitada y borrado.

Son datos personales y, en el chat, a veces de salud (RGPD, art. 9). Lo que hace este módulo en la demo:
- registra **qué consintió la familia, cuándo y con qué versión del texto** (cada lead lleva su consentimiento);
- **caduca** a los RETENCION_DIAS (se purga al guardar y al leer; fecha real de creación, no la simulada);
- permite **borrar** un lead concreto o todos los de un teléfono (derecho de supresión).
No hace (y en producción haría falta): cifrado en reposo con una clave gestionada, control de acceso a la base y registro
de quién consulta cada lead.
"""
import json
import sqlite3
from datetime import datetime, timedelta

RETENCION_DIAS = 30
VERSION_CONSENTIMIENTO = "2026-11-02"
COLUMNAS_NUEVAS = {"consentimiento": "TEXT", "creado": "TEXT"}


def asegurar_tabla(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS leads_web (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, canal TEXT, "
                "ficha TEXT, conversacion TEXT)")
    existentes = {f[1] for f in con.execute("PRAGMA table_info(leads_web)")}
    for nombre, tipo in COLUMNAS_NUEVAS.items():
        if nombre not in existentes:
            con.execute(f"ALTER TABLE leads_web ADD COLUMN {nombre} {tipo}")


def purgar(con: sqlite3.Connection, ahora_real: datetime | None = None) -> int:
    """Borra los leads con más de RETENCION_DIAS días. Los anteriores a existir `creado` se consideran recientes."""
    asegurar_tabla(con)
    limite = ((ahora_real or datetime.now()) - timedelta(days=RETENCION_DIAS)).isoformat(timespec="seconds")
    return con.execute("DELETE FROM leads_web WHERE creado IS NOT NULL AND creado < ?", (limite,)).rowcount


def guardar(con: sqlite3.Connection, fecha_demo: datetime, canal: str, ficha: dict, conversacion: list | None,
            texto_consentimiento: str, ahora_real: datetime | None = None) -> int:
    """Guarda un lead y devuelve su id. `fecha_demo` es la hora simulada de la demo; `creado`, la real (para la retención)."""
    asegurar_tabla(con)
    ahora_real = ahora_real or datetime.now()
    purgar(con, ahora_real)
    consentimiento = {"version": VERSION_CONSENTIMIENTO, "texto": texto_consentimiento,
                      "aceptado_en": ahora_real.isoformat(timespec="seconds")}
    cur = con.execute(
        "INSERT INTO leads_web (fecha, canal, ficha, conversacion, consentimiento, creado) VALUES (?,?,?,?,?,?)",
        (fecha_demo.isoformat(timespec="minutes"), canal, json.dumps(ficha, ensure_ascii=False),
         json.dumps(conversacion or [], ensure_ascii=False), json.dumps(consentimiento, ensure_ascii=False),
         ahora_real.isoformat(timespec="seconds")))
    return cur.lastrowid


def borrar(con: sqlite3.Connection, lead_id: int) -> int:
    asegurar_tabla(con)
    return con.execute("DELETE FROM leads_web WHERE id = ?", (lead_id,)).rowcount


def borrar_por_telefono(con: sqlite3.Connection, telefono: str) -> int:
    """Derecho de supresión: borra todos los leads cuya ficha tenga ese teléfono (9 cifras)."""
    asegurar_tabla(con)
    ids = [i for i, ficha in con.execute("SELECT id, ficha FROM leads_web")
           if str((json.loads(ficha or "{}")).get("telefono", "")).replace(" ", "") == telefono]
    con.executemany("DELETE FROM leads_web WHERE id = ?", [(i,) for i in ids])
    return len(ids)
