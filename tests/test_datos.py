"""Datos y definiciones de métricas (vistas de datos/esquema.sql)."""


def test_familias_deduplicadas(con):
    contactos, familias = con.execute("SELECT (SELECT COUNT(*) FROM leads), (SELECT COUNT(*) FROM familias)").fetchone()
    assert familias == 15000
    assert contactos > familias  # hay familias que entraron por dos canales


def test_cohorte_excluye_el_mes_sin_madurar(con):
    assert con.execute("SELECT MAX(fecha_entrada) FROM cohorte").fetchone()[0] < "2026-10-01"


def test_ventana_de_30_dias(con):
    fuera = con.execute(
        """SELECT COUNT(*) FROM altas_30d a JOIN leads l ON l.id = a.lead_id
           WHERE julianday(a.fecha_alta) - julianday(l.fecha_entrada) > 30""").fetchone()[0]
    assert fuera == 0


def test_resultado_solo_en_el_ultimo_contacto(con):
    # El primer contacto de una familia duplicada nunca tiene resultado asociado (atribución al último contacto)
    con_resultado = con.execute(
        """SELECT COUNT(*) FROM leads l JOIN altas a ON a.lead_id = l.id
           WHERE l.id NOT IN (SELECT id FROM familias)""").fetchone()[0]
    assert con_resultado == 0


def test_todas_las_consultas_sql_funcionan(con):
    from comun import CIUDADES, SQL
    for fichero in sorted(SQL.glob("*.sql")):
        texto = fichero.read_text(encoding="utf-8")
        consulta = texto.replace("{ciudades}", ",".join("?" * len(CIUDADES)))
        filas = con.execute(consulta, CIUDADES * texto.count("{ciudades}")).fetchall()
        assert filas, fichero.name
