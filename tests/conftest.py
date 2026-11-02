import os
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "app"))
os.environ.setdefault("QIDA_MODO", "grabado")  # las pruebas nunca llaman al modelo


@pytest.fixture(scope="session")
def con():
    db = RAIZ / "datos" / "crm.db"
    if not db.exists():
        from datos import generar  # noqa: F401  (genera la base si falta)
        generar.generar()
    conexion = sqlite3.connect(db)
    yield conexion
    conexion.close()
