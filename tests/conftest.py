import os
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "app"))
os.environ.setdefault("QIDA_MODO", "grabado")


@pytest.fixture(scope="session")
def con():
    db = RAIZ / "datos" / "crm.db"
    if not db.exists():
        from datos import generar
        generar.generar()
    conexion = sqlite3.connect(db)
    yield conexion
    conexion.close()
