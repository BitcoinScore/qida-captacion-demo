"""Genera un CRM inventado (tipo Odoo) para la demo de captación.

TODOS LOS DATOS SON INVENTADOS. Las proporciones son supuestos razonables, no datos de Qida.
Uso: python datos/generar.py  ->  datos/crm.db
"""
import math
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SEMILLA = 42
N_LEADS = 15000
INICIO = datetime(2025, 5, 1)  # 18 meses: hace falta historia para medir quién sigue al año
FIN = datetime(2026, 10, 31)
DB = Path(__file__).parent / "crm.db"

# Canal: (peso en el volumen, prob. base de alta, efecto en retención a 3 meses, coste por lead €)
CANALES = {
    "Google Search":       (0.30, 0.16, 0.00, 65),
    "Meta":                (0.18, 0.07, -0.10, 32),
    "SEO / blog":          (0.14, 0.11, 0.00, 0),
    "Menú descargable":    (0.08, 0.03, -0.05, 12),
    "Prescriptor":         (0.10, 0.30, 0.08, 0),
    "Aseguradora":         (0.05, 0.26, 0.05, 0),
    "Recomendación":       (0.05, 0.38, 0.12, 0),
    "Teléfono directo":    (0.10, 0.24, 0.03, 0),
}
# Supuesto: coste mensual que no es de medios (equipo de contenido y SEO, acuerdos con prescriptores y aseguradoras,
# incentivo por recomendación). Hace falta para el CAC combinado.
COSTE_FIJO_MES = {"SEO / blog": 9000, "Prescriptor": 6000, "Aseguradora": 4000, "Recomendación": 1200}
CIUDADES = {"Barcelona": 0.25, "Madrid": 0.25, "Valencia": 0.18, "Sevilla": 0.16, "A Coruña": 0.16}
SERVICIOS = {  # (peso, multiplicador de conversión, horas/mes medias, €/hora)
    "Por horas":       (0.55, 1.00, 40, 17),
    "Interna":         (0.20, 0.85, 0, 0),
    "Fin de semana":   (0.15, 0.90, 32, 18),
    "Nocturna":        (0.10, 0.80, 60, 19),
}
CUOTA_INTERNA = 2100  # €/mes, supuesto


def elegir(rng, dic, idx=0):
    claves = list(dic)
    pesos = [v[idx] if isinstance(v, tuple) else v for v in dic.values()]
    return rng.choices(claves, weights=pesos)[0]


def hora_entrada(rng):
    # Más leads por la mañana y por la noche (cuando los hijos buscan tras el trabajo)
    franjas = [(0, 7, 0.06), (7, 9, 0.08), (9, 14, 0.34), (14, 20, 0.30), (20, 24, 0.22)]
    a, b, _ = rng.choices(franjas, weights=[f[2] for f in franjas])[0]
    return rng.uniform(a, b)


def fuera_de_horario(dt):
    h = dt.hour + dt.minute / 60
    if dt.weekday() < 5:
        return not (9 <= h < 20)
    return not (9 <= h < 18)


def minutos_hasta_llamada(rng, dt):
    """Supuesto: en horario se llama en 1-6 h; fuera de horario, al abrir (más cola)."""
    if not fuera_de_horario(dt):
        return rng.uniform(20, 360)
    # hasta la siguiente apertura + cola de la mañana
    siguiente = dt
    while fuera_de_horario(siguiente):
        siguiente += timedelta(minutes=15)
    return (siguiente - dt).total_seconds() / 60 + rng.uniform(30, 240)


def decaimiento(minutos):
    """Supuesto: cuanto más se tarda en llamar, menos familias llegan a valoración."""
    return 0.55 + 0.45 * math.exp(-minutos / 600)


def generar(db: Path = DB):
    rng = random.Random(SEMILLA)
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))

    dias = (FIN - INICIO).days + 1
    lead_id = 0
    for familia_id in range(1, N_LEADS + 1):
        dia = INICIO + timedelta(days=rng.randrange(dias))
        h = hora_entrada(rng)
        entrada = dia + timedelta(hours=h)
        canal = elegir(rng, CANALES)
        ciudad = elegir(rng, CIUDADES)
        servicio = elegir(rng, SERVICIOS)
        urgencia = rng.random() < (0.22 if canal == "Prescriptor" else 0.10)
        dependencia = rng.random() < 0.30

        # Supuesto: el 8 % de las familias ya había dejado sus datos antes por otro canal (mismo teléfono).
        # Ese primer contacto queda en el CRM como un lead más; el resultado se asocia al último contacto.
        if rng.random() < 0.08:
            antes = entrada - timedelta(days=rng.uniform(1, 10), hours=rng.uniform(0, 6))
            if antes >= INICIO:
                previo = rng.choice([c for c in ("Meta", "Google Search", "SEO / blog", "Menú descargable") if c != canal])
                lead_id += 1
                con.execute("INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?)",
                            (lead_id, familia_id, antes.isoformat(timespec="minutes"), previo, ciudad, servicio,
                             0, int(dependencia), int(fuera_de_horario(antes))))

        lead_id += 1
        fuera = fuera_de_horario(entrada)
        con.execute(
            "INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?)",
            (lead_id, familia_id, entrada.isoformat(timespec="minutes"), canal, ciudad, servicio,
             int(urgencia), int(dependencia), int(fuera)),
        )

        # Contacto
        if rng.random() > (0.93 if canal != "Menú descargable" else 0.70):
            continue  # nunca se le consiguió hablar
        espera = minutos_hasta_llamada(rng, entrada)
        llamada = entrada + timedelta(minutes=espera)
        con.execute("INSERT INTO llamadas VALUES (?,?)", (lead_id, llamada.isoformat(timespec="minutes")))

        # Probabilidad real de alta (oculta al modelo)
        _, p_base, ret_canal, _ = CANALES[canal]
        p = p_base * SERVICIOS[servicio][1] * decaimiento(espera)
        p *= 1.6 if urgencia else 1.0
        p *= 1.25 if dependencia else 1.0
        p *= {"A Coruña": 0.9, "Sevilla": 0.95}.get(ciudad, 1.0)
        p_valoracion = min(0.95, p * 2.6)
        if rng.random() > p_valoracion:
            continue
        valoracion = llamada + timedelta(days=rng.uniform(1, 6))
        con.execute("INSERT INTO valoraciones VALUES (?,?)", (lead_id, valoracion.isoformat(timespec="minutes")))

        if rng.random() > min(0.95, p / p_valoracion):
            continue
        alta = valoracion + timedelta(days=rng.uniform(1, 10) + (12 if dependencia else 0))
        if alta > FIN:
            continue
        if servicio == "Interna":
            horas, ingreso = 0, CUOTA_INTERNA
        else:
            horas = max(8, round(rng.gauss(SERVICIOS[servicio][2], 10)))
            ingreso = horas * SERVICIOS[servicio][3]
        vinculada = int(dependencia and rng.random() < 0.6)
        con.execute(
            "INSERT INTO altas VALUES (?,?,?,?,?)",
            (lead_id, alta.isoformat(timespec="minutes"), horas, ingreso, vinculada),
        )

        # Bajas (por cualquier motivo). Supuesto: muchas en los 3 primeros meses (~22 % de base, según canal)
        # y después un goteo de ~2,7 % al mes, algo menor si la familia paga con la prestación vinculada.
        p_baja_3m = max(0.05, 0.22 - ret_canal - (0.05 if vinculada else 0))
        if rng.random() < p_baja_3m:
            dias_baja = rng.uniform(10, 90)
        else:
            media = 1000 * (1.3 if vinculada else 1.0) * (1 + ret_canal * 2)
            dias_baja = 90 + rng.expovariate(1 / media)
        baja = alta + timedelta(days=dias_baja)
        if baja <= FIN:
            con.execute("INSERT INTO bajas VALUES (?,?)", (lead_id, baja.isoformat(timespec="minutes")))

    # Gasto mensual por canal de pago (coste por lead supuesto × leads del mes)
    for canal, (_, _, _, cpl) in CANALES.items():
        if not cpl:
            continue
        filas = con.execute(
            "SELECT substr(fecha_entrada,1,7), ciudad, COUNT(*) FROM leads WHERE canal=? GROUP BY 1,2", (canal,)
        ).fetchall()
        for mes, ciudad, n in filas:
            con.execute("INSERT INTO gasto VALUES (?,?,?,?,?)",
                        (mes, canal, ciudad, "medios", round(n * cpl * rng.uniform(0.85, 1.15), 2)))

    # Costes que no son de medios: los canales «gratis» no lo son (supuestos mensuales, repartidos por ciudad según leads)
    for canal, mensual in COSTE_FIJO_MES.items():
        filas = con.execute(
            "SELECT substr(fecha_entrada,1,7) AS mes, ciudad, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY substr(fecha_entrada,1,7)) "
            "FROM leads WHERE canal=? GROUP BY 1,2", (canal,)
        ).fetchall()
        for mes, ciudad, cuota in filas:
            con.execute("INSERT INTO gasto VALUES (?,?,?,?,?)", (mes, canal, ciudad, "equipo y acuerdos", round(mensual * cuota, 2)))

    con.commit()
    resumen = con.execute(
        "SELECT (SELECT COUNT(*) FROM leads),(SELECT COUNT(*) FROM valoraciones),(SELECT COUNT(*) FROM altas),(SELECT COUNT(*) FROM bajas)"
    ).fetchone()
    con.close()
    print(f"leads={resumen[0]} valoraciones={resumen[1]} altas={resumen[2]} bajas={resumen[3]} -> {db}")


if __name__ == "__main__":
    generar()
